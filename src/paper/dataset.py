"""Utilitarios de dataset para os experimentos do paper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

from src.config import mitdb_record_dir
from src.paper.constants import (
    ABLATION_STAGES,
    DS1_RECORDS,
    DS2_RECORDS,
    NORMAL_SYMBOL,
    PACED_HEAVY_RECORDS,
    VALID_BEAT_SYMBOLS,
)
from src.paper.features import extract_feature_groups
from src.paper.preprocessing import denoise_fir_chain


@dataclass(frozen=True)
class BeatWindow:
    """Janela de batimento alinhada a uma anotacao."""

    record: str
    sample: int
    symbol: str
    fs: float
    signal: np.ndarray
    start_sample: int
    end_sample: int
    rr_prev_s: float | None = None
    rr_next_s: float | None = None

    @property
    def label_binary(self) -> int:
        """0 para normal, 1 para anomalia."""
        return symbol_to_binary_label(self.symbol)


def is_valid_beat_symbol(symbol: str) -> bool:
    """Retorna se o simbolo WFDB representa batimento avaliavel no v1."""
    return symbol in VALID_BEAT_SYMBOLS


def symbol_to_binary_label(symbol: str) -> int:
    """Mapeia anotacao MIT-BIH para rotulo binario de avaliacao."""
    if symbol == NORMAL_SYMBOL:
        return 0
    if is_valid_beat_symbol(symbol):
        return 1
    raise ValueError(f"Simbolo de batimento invalido para o paper: {symbol!r}")


def beat_bounds(
    center_sample: int,
    fs: float,
    n_samples: int,
    pre_s: float = 0.25,
    post_s: float = 0.45,
) -> tuple[int, int]:
    """Calcula limites seguros da janela centrada na anotacao."""
    pre = int(round(pre_s * fs))
    post = int(round(post_s * fs))
    start = max(0, int(center_sample) - pre)
    end = min(n_samples, int(center_sample) + post)
    return start, end


def full_beat_bounds(
    center_sample: int,
    fs: float,
    n_samples: int,
    pre_s: float = 0.25,
    post_s: float = 0.45,
) -> tuple[int, int] | None:
    """Limites de janela completa, ou None se a janela encostar na borda."""
    pre = int(round(pre_s * fs))
    post = int(round(post_s * fs))
    start = int(center_sample) - pre
    end = int(center_sample) + post
    if start < 0 or end > n_samples:
        return None
    return start, end


def segment_beat(
    x: np.ndarray,
    fs: float,
    sample: int,
    *,
    pre_s: float = 0.25,
    post_s: float = 0.45,
) -> tuple[np.ndarray, int, int]:
    """Extrai janela de batimento e devolve janela, inicio e fim no registro."""
    start, end = beat_bounds(sample, fs, len(x), pre_s=pre_s, post_s=post_s)
    return np.asarray(x[start:end], dtype=float), start, end


def rr_context(samples: np.ndarray, fs: float, index: int) -> tuple[float | None, float | None]:
    """Intervalos RR anterior e posterior em segundos."""
    prev_rr = None
    next_rr = None
    if index > 0:
        prev_rr = float((samples[index] - samples[index - 1]) / fs)
    if index + 1 < len(samples):
        next_rr = float((samples[index + 1] - samples[index]) / fs)
    return prev_rr, next_rr


def interpatient_record_split() -> dict[str, tuple[str, ...]]:
    """Registros de treino/teste excluindo os paced-heavy definidos no protocolo."""
    train = tuple(r for r in DS1_RECORDS if r not in PACED_HEAVY_RECORDS)
    test = tuple(r for r in DS2_RECORDS if r not in PACED_HEAVY_RECORDS)
    return {"train": train, "test": test}


def selected_records(split: str = "all") -> tuple[str, ...]:
    """Registros do protocolo para treino, teste ou ambos."""
    groups = interpatient_record_split()
    if split == "train":
        return groups["train"]
    if split == "test":
        return groups["test"]
    if split == "all":
        return groups["train"] + groups["test"]
    raise ValueError(f"Split desconhecido: {split!r}")


def select_mlii_channel(record: wfdb.Record) -> tuple[int, str]:
    """Seleciona MLII quando presente; caso contrario, usa o primeiro canal."""
    names = list(record.sig_name or [])
    upper = [str(name).upper() for name in names]
    if "MLII" in upper:
        idx = upper.index("MLII")
        return idx, names[idx]
    return 0, names[0] if names else "ch0"


def load_record_signal(record_id: str, base_dir: Path | None = None) -> tuple[np.ndarray, float, str]:
    """Carrega o sinal preferencial MLII de um registro MIT-BIH."""
    base = base_dir or mitdb_record_dir()
    rec = wfdb.rdrecord((base / record_id).as_posix())
    channel_idx, channel_name = select_mlii_channel(rec)
    signal = np.asarray(rec.p_signal[:, channel_idx], dtype=float)
    return signal, float(rec.fs), channel_name


def load_record_annotations(record_id: str, base_dir: Path | None = None):
    """Carrega anotacoes `atr` de um registro MIT-BIH."""
    base = base_dir or mitdb_record_dir()
    return wfdb.rdann((base / record_id).as_posix(), "atr")


def build_stage_feature_frames(
    *,
    records: tuple[str, ...] | None = None,
    split_name_by_record: dict[str, str] | None = None,
    base_dir: Path | None = None,
    pre_s: float = 0.25,
    post_s: float = 0.45,
    max_beats_per_record: int | None = None,
) -> dict[str, pd.DataFrame]:
    """Monta dataframes de features A0-A3 preservando as mesmas chaves de batimento."""
    base = base_dir or mitdb_record_dir()
    groups = interpatient_record_split()
    split_lookup = split_name_by_record or {
        **{record: "train" for record in groups["train"]},
        **{record: "test" for record in groups["test"]},
    }
    stage_rows: dict[str, list[dict[str, float | int | str]]] = {
        stage.key: [] for stage in ABLATION_STAGES
    }
    chosen_records = records or selected_records("all")

    for record_id in chosen_records:
        raw, fs, channel_name = load_record_signal(record_id, base)
        filtered = denoise_fir_chain(raw, fs)
        ann = load_record_annotations(record_id, base)
        samples = np.asarray(ann.sample, dtype=int)
        symbols = np.asarray(ann.symbol, dtype=str)

        kept = 0
        for idx, (sample, symbol) in enumerate(zip(samples, symbols, strict=False)):
            if not is_valid_beat_symbol(str(symbol)):
                continue
            bounds = full_beat_bounds(int(sample), fs, len(raw), pre_s=pre_s, post_s=post_s)
            if bounds is None:
                continue
            start, end = bounds
            rr_prev, rr_next = rr_context(samples, fs, idx)
            beat_id = f"{record_id}:{int(sample)}:{symbol}"
            metadata: dict[str, float | int | str] = {
                "beat_id": beat_id,
                "record": record_id,
                "split": split_lookup.get(record_id, "unknown"),
                "sample": int(sample),
                "time_s": float(sample / fs),
                "ann_symbol": str(symbol),
                "label_binary": symbol_to_binary_label(str(symbol)),
                "channel": channel_name,
                "fs_hz": float(fs),
                "start_sample": int(start),
                "end_sample": int(end),
                "rr_prev_s": np.nan if rr_prev is None else float(rr_prev),
                "rr_next_s": np.nan if rr_next is None else float(rr_next),
            }
            raw_beat = raw[start:end]
            filtered_beat = filtered[start:end]
            for stage in ABLATION_STAGES:
                signal_variant = raw_beat if stage.signal_variant == "raw" else filtered_beat
                features = extract_feature_groups(
                    signal_variant,
                    fs,
                    stage.feature_groups,
                    rr_prev_s=rr_prev,
                    rr_next_s=rr_next,
                )
                stage_rows[stage.key].append(
                    {
                        **metadata,
                        "stage": stage.key,
                        "stage_label": stage.label,
                        **features,
                    }
                )
            kept += 1
            if max_beats_per_record is not None and kept >= max_beats_per_record:
                break

    return {stage: pd.DataFrame(rows) for stage, rows in stage_rows.items()}


def assert_same_beat_population(stage_frames: dict[str, pd.DataFrame]) -> None:
    """Garante que todos os estagios usam os mesmos batimentos na mesma ordem."""
    expected: list[str] | None = None
    for stage, frame in stage_frames.items():
        beat_ids = frame["beat_id"].astype(str).tolist()
        if expected is None:
            expected = beat_ids
            continue
        if beat_ids != expected:
            raise AssertionError(f"Populacao de batimentos difere no estagio {stage}.")
