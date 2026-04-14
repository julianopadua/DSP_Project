# src/data/summarize_mitdb_records.py
"""Inventário tabular de todos os registos WFDB MIT-BIH locais (metadados, atr, ruído)."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
import wfdb
from scipy import signal

from src.config import PROCESSED_DATA_DIR, ensure_data_dirs, mitdb_record_dir

logger = logging.getLogger(__name__)

# Símbolos de anotação de batida / marcador (WFDB / MIT-BIH). Ordem fixa = ordem das colunas no CSV.
CANONICAL_ANN_SYMBOLS: Final[tuple[str, ...]] = (
    "N",
    "L",
    "R",
    "B",
    "A",
    "a",
    "J",
    "S",
    "V",
    "r",
    "F",
    "e",
    "j",
    "E",
    "/",
    "f",
    "x",
    "Q",
    "|",
    "+",
    "~",
    "[",
    "]",
    "!",
)

# (substring em aux_note normalizado, sufixo seguro para nome de coluna)
# Ordem: substrings mais longas primeiro, para não confundir (ex.) "(N" com "(NOD".
RHYTHM_AUX_SUBSTRINGS: Final[tuple[tuple[str, str], ...]] = tuple(
    sorted(
        (
            ("(AB", "AB"),
            ("(AFIB", "AFIB"),
            ("(AFL", "AFL"),
            ("(ASMI", "ASMI"),
            ("(BII", "BII"),
            ("(BIGU", "BIGU"),
            ("(HGEA", "HGEA"),
            ("(IVR", "IVR"),
            ("(NOD", "NOD"),
            ("(PREX", "PREX"),
            ("(SBR", "SBR"),
            ("(SVTA", "SVTA"),
            ("(VFL", "VFL"),
            ("(VT", "VT"),
            ("(PM", "PM"),
            ("(B", "B"),
            ("(N", "N"),
            ("(P", "P"),
            ("(T", "T"),
        ),
        key=lambda t: len(t[0]),
        reverse=True,
    )
)

SYMBOL_TO_COL_SUFFIX: Final[dict[str, str]] = {
    "/": "SLASH",
    "|": "PIPE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    "!": "EXCLAIM",
    "+": "PLUS",
    "~": "TILDE",
}


def ann_sym_column_name(symbol: str) -> str:
    suf = SYMBOL_TO_COL_SUFFIX.get(symbol, symbol)
    return f"ann_sym_{suf}"


def normalize_aux_note(raw: str | bytes | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        text = raw.decode("latin-1", errors="replace")
    else:
        text = str(raw)
    return text.replace("\x00", "").strip()


def list_record_ids(base_dir: Path) -> list[str]:
    return sorted({p.stem for p in base_dir.glob("*.hea")})


def triplet_paths(base_dir: Path, stem: str) -> tuple[Path, Path, Path]:
    return (
        base_dir / f"{stem}.hea",
        base_dir / f"{stem}.dat",
        base_dir / f"{stem}.atr",
    )


def channel_field(record: wfdb.Record, name: str, ch: int) -> Any:
    val = getattr(record, name, None)
    if val is None:
        return None
    if isinstance(val, (list, tuple, np.ndarray)):
        if ch >= len(val):
            return None
        return val[ch]
    if ch == 0:
        return val
    return None


def parse_header_row(record_prefix: str) -> tuple[dict[str, Any], str | None]:
    out: dict[str, Any] = {}
    err: str | None = None
    try:
        rec = wfdb.rdheader(record_prefix)
    except Exception as exc:  # noqa: BLE001
        return out, f"rdheader:{exc!s}"[:500]

    out["fs_hz"] = float(rec.fs) if rec.fs is not None else np.nan
    out["n_sig"] = int(rec.n_sig) if rec.n_sig is not None else np.nan
    out["sig_len_samples"] = int(rec.sig_len) if rec.sig_len is not None else np.nan
    if rec.fs and rec.sig_len:
        out["duration_s"] = float(rec.sig_len) / float(rec.fs)
    else:
        out["duration_s"] = np.nan

    names = rec.sig_name
    if isinstance(names, (list, tuple)):
        out["sig_names"] = "|".join(str(x) for x in names)
    elif names is not None:
        out["sig_names"] = str(names)
    else:
        out["sig_names"] = ""

    out["base_date"] = rec.base_date or ""
    out["base_time"] = rec.base_time or ""

    comments = rec.comments
    if isinstance(comments, (list, tuple)):
        out["n_comments"] = len(comments)
        joined = " | ".join(str(c) for c in comments)
        out["comments_concat"] = joined[:2000]
    elif comments:
        out["n_comments"] = 1
        out["comments_concat"] = str(comments)[:2000]
    else:
        out["n_comments"] = 0
        out["comments_concat"] = ""

    n_sig = int(rec.n_sig) if rec.n_sig else 0
    for ch in (0, 1):
        prefix = f"sig_{ch}_"
        if ch >= n_sig:
            for key in (
                "file",
                "fmt",
                "units",
                "adc_gain",
                "baseline",
                "init_val",
                "adc_res",
                "samps_per_frame",
            ):
                out[prefix + key] = np.nan if key in ("adc_gain", "baseline", "init_val", "adc_res", "samps_per_frame") else ""
            continue
        out[prefix + "file"] = channel_field(rec, "file_name", ch) or ""
        out[prefix + "fmt"] = channel_field(rec, "fmt", ch) or ""
        out[prefix + "units"] = channel_field(rec, "units", ch) or ""
        for key, rec_attr in (
            ("adc_gain", "adc_gain"),
            ("baseline", "baseline"),
            ("init_val", "init_value"),
            ("adc_res", "adc_res"),
            ("samps_per_frame", "samps_per_frame"),
        ):
            v = channel_field(rec, rec_attr, ch)
            try:
                out[prefix + key] = float(v) if v is not None else np.nan
            except (TypeError, ValueError):
                out[prefix + key] = np.nan

    return out, err


def ann_fields_template() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for s in CANONICAL_ANN_SYMBOLS:
        out[ann_sym_column_name(s)] = 0
    for _, slug in RHYTHM_AUX_SUBSTRINGS:
        out[f"aux_rhy_{slug}"] = 0
    out["n_aux_note_nonempty"] = 0
    out["aux_note_unique_truncated"] = ""
    out["n_annotations"] = 0
    out["ann_first_sample"] = np.nan
    out["ann_last_sample"] = np.nan
    out["ann_sym_other_count"] = 0
    out["ann_sym_unlisted"] = ""
    return out


def parse_ann_row(record_prefix: str) -> tuple[dict[str, Any], str | None]:
    out = ann_fields_template()
    err: str | None = None
    canonical = set(CANONICAL_ANN_SYMBOLS)

    try:
        ann = wfdb.rdann(record_prefix, "atr")
    except Exception as exc:  # noqa: BLE001
        return ann_fields_template(), f"rdann:{exc!s}"[:500]

    samples = np.asarray(ann.sample).ravel()
    out["n_annotations"] = int(samples.size)
    if samples.size:
        out["ann_first_sample"] = int(samples[0])
        out["ann_last_sample"] = int(samples[-1])
    else:
        out["ann_first_sample"] = np.nan
        out["ann_last_sample"] = np.nan

    symbols = ann.symbol
    if symbols is None:
        symbols = []
    sym_counter: Counter[str] = Counter()
    for sym in symbols:
        if sym is None:
            continue
        s = sym if isinstance(sym, str) else str(sym)
        if len(s) != 1:
            sym_counter[s] += 1
        else:
            sym_counter[s] += 1

    other = 0
    unlisted: set[str] = set()
    for s, c in sym_counter.items():
        if s in canonical:
            out[ann_sym_column_name(s)] = int(c)
        else:
            other += int(c)
            unlisted.add(s)
    out["ann_sym_other_count"] = int(other)
    out["ann_sym_unlisted"] = "|".join(sorted(unlisted))

    aux_list = list(ann.aux_note) if ann.aux_note is not None else []
    nonempty = [normalize_aux_note(a) for a in aux_list if normalize_aux_note(a)]
    out["n_aux_note_nonempty"] = len(nonempty)

    substr_to_slug = dict(RHYTHM_AUX_SUBSTRINGS)
    for note in nonempty:
        matched_subs = [s for s in substr_to_slug if s in note]
        kept: set[str] = set()
        for s in sorted(matched_subs, key=len, reverse=True):
            if any(
                len(t) > len(s) and s in t and s != t
                for t in matched_subs
            ):
                continue
            kept.add(s)
        for s in kept:
            slug = substr_to_slug[s]
            out[f"aux_rhy_{slug}"] = int(out[f"aux_rhy_{slug}"]) + 1

    uniq = sorted(set(nonempty))[:40]
    out["aux_note_unique_truncated"] = " || ".join(uniq)[:4000]

    return out, err


def _band_power(f: np.ndarray, pxx: np.ndarray, lo: float, hi: float) -> float:
    m = (f >= lo) & (f <= hi)
    if not np.any(m):
        return 0.0
    return float(np.trapezoid(pxx[m], f[m]))


def _empty_noise_row(
    error: str,
    *,
    policy: str = "",
    user_skip_noise: bool = False,
) -> dict[str, Any]:
    if user_skip_noise:
        err = "skipped"
        pol = "skip-noise"
    else:
        err = error
        pol = policy
    return {
        "noise_analysis_ok": False,
        "noise_analysis_error": err,
        "noise_score_bw": np.nan,
        "noise_score_pli": np.nan,
        "noise_score_emg": np.nan,
        "noise_score_motion": np.nan,
        "noise_flag_bw": False,
        "noise_flag_pli": False,
        "noise_flag_emg": False,
        "noise_flag_motion": False,
        "noise_primary_label": "",
        "noise_windowing_policy": pol,
    }


def noise_metrics_window(
    x: np.ndarray,
    fs: float,
    pli_hz: float,
) -> dict[str, float]:
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 64:
        return {"bw": 0.0, "pli": 0.0, "emg": 0.0, "motion": 0.0}

    x = x - np.mean(x)
    nperseg = min(len(x), 2048)
    f, pxx = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2, scaling="density")

    p_low = _band_power(f, pxx, 0.05, 0.8)
    p_qrs = _band_power(f, pxx, 5.0, 40.0)
    bw_ratio = p_low / (p_qrs + 1e-20)
    bw_score = float(np.tanh(np.log1p(bw_ratio) / 3.0))

    nyq = fs / 2.0
    if pli_hz < nyq - 2:
        p_line = _band_power(f, pxx, pli_hz - 1.0, pli_hz + 1.0)
        p_ref_lo = _band_power(f, pxx, max(2.0, pli_hz - 8), pli_hz - 2)
        p_ref_hi = _band_power(f, pxx, pli_hz + 2, min(nyq - 1, pli_hz + 12))
        p_ref = (p_ref_lo + p_ref_hi) / 2.0 + 1e-20
        pli_ratio = p_line / p_ref
        pli_score = float(np.tanh(np.log1p(pli_ratio) / 2.5))
    else:
        pli_score = 0.0

    hi_lo = min(90.0, nyq - 1.0)
    if hi_lo > 40:
        p_hf = _band_power(f, pxx, 40.0, hi_lo)
        emg_ratio = p_hf / (p_qrs + 1e-20)
        emg_score = float(np.tanh(np.log1p(emg_ratio) / 3.0))
    else:
        emg_score = 0.0

    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med))) + 1e-12
    clip = med + 5.0 * 1.4826 * mad
    frac = float(np.mean(np.abs(x - med) > clip))
    d = np.abs(np.diff(x))
    d99 = float(np.percentile(d, 99)) if d.size else 0.0
    d50 = float(np.median(d)) + 1e-12
    spike = d99 / d50
    motion_score = float(
        np.tanh(np.log1p(spike) / 4.0) * 0.7 + np.tanh(frac * 50.0) * 0.3
    )

    return {
        "bw": min(1.0, max(0.0, bw_score)),
        "pli": min(1.0, max(0.0, pli_score)),
        "emg": min(1.0, max(0.0, emg_score)),
        "motion": min(1.0, max(0.0, motion_score)),
    }


def analyze_record_noise(
    record_prefix: str,
    sig_len: int,
    fs: float,
    n_sig: int,
    *,
    skip: bool,
    full_record: bool,
    window_sec: float,
    max_windows: int,
    pli_hz: float,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "noise_analysis_ok": False,
        "noise_analysis_error": "",
        "noise_score_bw": np.nan,
        "noise_score_pli": np.nan,
        "noise_score_emg": np.nan,
        "noise_score_motion": np.nan,
        "noise_flag_bw": False,
        "noise_flag_pli": False,
        "noise_flag_emg": False,
        "noise_flag_motion": False,
        "noise_primary_label": "",
        "noise_windowing_policy": "",
    }
    if skip or not np.isfinite(fs) or fs <= 0 or sig_len <= 0 or n_sig <= 0:
        if skip:
            out["noise_analysis_error"] = "skipped"
            out["noise_windowing_policy"] = "skip-noise"
        else:
            out["noise_analysis_error"] = "invalid_fs_or_len"
        return out

    window_samples = max(256, int(fs * window_sec))
    window_samples = min(window_samples, sig_len)

    if full_record:
        starts = [0]
        policy = f"full_record;samples={sig_len}"
        sampto = sig_len
    else:
        n_win = min(max_windows, max(1, sig_len // max(1, window_samples)))
        if n_win <= 1:
            starts = [0]
        else:
            max_start = max(0, sig_len - window_samples)
            starts = [int(round(i)) for i in np.linspace(0, max_start, n_win, dtype=float)]
        policy = f"windows={len(starts)};each={window_samples}_samples;pli_hz={pli_hz}"

    agg_bw: list[float] = []
    agg_pli: list[float] = []
    agg_emg: list[float] = []
    agg_motion: list[float] = []

    try:
        for start in starts:
            end = min(sig_len, start + window_samples)
            if end - start < 64:
                continue
            segment = wfdb.rdrecord(
                record_prefix,
                sampfrom=start,
                sampto=end,
                channels=None,
            )
            ps = segment.p_signal
            if ps is None or ps.size == 0:
                continue
            for ch in range(min(n_sig, ps.shape[1])):
                m = noise_metrics_window(ps[:, ch], fs, pli_hz)
                agg_bw.append(m["bw"])
                agg_pli.append(m["pli"])
                agg_emg.append(m["emg"])
                agg_motion.append(m["motion"])
    except Exception as exc:  # noqa: BLE001
        out["noise_analysis_error"] = f"noise:{exc!s}"[:500]
        out["noise_windowing_policy"] = policy
        return out

    if not agg_bw:
        out["noise_analysis_error"] = "no_windows"
        out["noise_windowing_policy"] = policy
        return out

    out["noise_analysis_ok"] = True
    out["noise_windowing_policy"] = policy
    bw = float(np.max(agg_bw))
    pli = float(np.max(agg_pli))
    emg = float(np.max(agg_emg))
    motion = float(np.max(agg_motion))
    out["noise_score_bw"] = bw
    out["noise_score_pli"] = pli
    out["noise_score_emg"] = emg
    out["noise_score_motion"] = motion

    out["noise_flag_bw"] = bw > 0.35
    out["noise_flag_pli"] = pli > 0.25
    out["noise_flag_emg"] = emg > 0.22
    out["noise_flag_motion"] = motion > 0.35

    scores = {"bw": bw, "pli": pli, "emg": emg, "motion": motion}
    best_k, best_v = max(scores.items(), key=lambda kv: kv[1])
    second = sorted(scores.values(), reverse=True)
    if best_v < 0.08:
        out["noise_primary_label"] = "none"
    elif len(second) > 1 and second[1] >= 0.85 * best_v:
        out["noise_primary_label"] = "mixed"
    else:
        out["noise_primary_label"] = best_k

    return out


def build_row(
    base_dir: Path,
    stem: str,
    *,
    skip_noise: bool,
    noise_full_record: bool,
    noise_window_sec: float,
    noise_max_windows: int,
    pli_hz: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {"record_id": stem}
    record_prefix = (base_dir / stem).as_posix()
    row["record_prefix_posix"] = record_prefix

    p_hea, p_dat, p_atr = triplet_paths(base_dir, stem)
    row["has_hea"] = p_hea.is_file()
    row["has_dat"] = p_dat.is_file()
    row["has_atr"] = p_atr.is_file()
    row["triplet_complete"] = bool(row["has_hea"] and row["has_dat"] and row["has_atr"])

    for key, path in (("bytes_hea", p_hea), ("bytes_dat", p_dat), ("bytes_atr", p_atr)):
        row[key] = path.stat().st_size if path.is_file() else np.nan

    row["header_ok"] = False
    row["ann_ok"] = False
    row["parse_error"] = ""

    if not row["triplet_complete"]:
        row["parse_error"] = "missing_triplet_file"
        row.update(ann_fields_template())
        row.update(_empty_noise_row("triplet_incomplete", user_skip_noise=False))
        return row

    hrow, herr = parse_header_row(record_prefix)
    row.update(hrow)
    if herr:
        row["parse_error"] = herr
    else:
        row["header_ok"] = True

    arow, aerr = parse_ann_row(record_prefix)
    row.update(arow)
    if aerr:
        row["parse_error"] = (row["parse_error"] + ";" + aerr).strip(";") if row["parse_error"] else aerr
    else:
        row["ann_ok"] = True

    sig_len = int(row.get("sig_len_samples") or 0)
    fs = float(row.get("fs_hz") or 0.0)
    n_sig = int(row.get("n_sig") or 0)

    if skip_noise:
        row.update(_empty_noise_row("", user_skip_noise=True))
    elif not row["header_ok"] or not np.isfinite(fs) or fs <= 0 or sig_len <= 0:
        row.update(_empty_noise_row("header_missing_or_invalid_fs", user_skip_noise=False))
    else:
        row.update(
            analyze_record_noise(
                record_prefix,
                sig_len,
                fs,
                n_sig,
                skip=False,
                full_record=noise_full_record,
                window_sec=noise_window_sec,
                max_windows=noise_max_windows,
                pli_hz=pli_hz,
            )
        )

    return row


def column_order() -> list[str]:
    first = [
        "record_id",
        "record_prefix_posix",
        "has_hea",
        "has_dat",
        "has_atr",
        "triplet_complete",
        "bytes_hea",
        "bytes_dat",
        "bytes_atr",
        "header_ok",
        "ann_ok",
        "parse_error",
        "fs_hz",
        "n_sig",
        "sig_len_samples",
        "duration_s",
        "sig_names",
        "base_date",
        "base_time",
        "n_comments",
        "comments_concat",
        "sig_0_file",
        "sig_0_fmt",
        "sig_0_units",
        "sig_0_adc_gain",
        "sig_0_baseline",
        "sig_0_init_val",
        "sig_0_adc_res",
        "sig_0_samps_per_frame",
        "sig_1_file",
        "sig_1_fmt",
        "sig_1_units",
        "sig_1_adc_gain",
        "sig_1_baseline",
        "sig_1_init_val",
        "sig_1_adc_res",
        "sig_1_samps_per_frame",
        "n_annotations",
        "ann_first_sample",
        "ann_last_sample",
    ]
    ann_cols = [ann_sym_column_name(s) for s in CANONICAL_ANN_SYMBOLS]
    mid = (
        first
        + ann_cols
        + ["ann_sym_other_count", "ann_sym_unlisted", "n_aux_note_nonempty"]
    )
    aux_cols = [f"aux_rhy_{slug}" for _, slug in RHYTHM_AUX_SUBSTRINGS]
    noise = [
        "noise_analysis_ok",
        "noise_analysis_error",
        "noise_score_bw",
        "noise_score_pli",
        "noise_score_emg",
        "noise_score_motion",
        "noise_flag_bw",
        "noise_flag_pli",
        "noise_flag_emg",
        "noise_flag_motion",
        "noise_primary_label",
        "noise_windowing_policy",
    ]
    return mid + ["aux_note_unique_truncated"] + aux_cols + noise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Gera inventário CSV de todos os registos MIT-BIH WFDB em data/raw (via mitdb_record_dir).",
    )
    p.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help=f"Caminho do CSV (por omissão: {PROCESSED_DATA_DIR}/mitdb_record_inventory.csv).",
    )
    p.add_argument("--fail-fast", action="store_true", help="Aborta no primeiro erro inesperado.")
    p.add_argument("--skip-noise", action="store_true", help="Não carrega forma de onda nem calcula métricas de ruído.")
    p.add_argument(
        "--noise-full-record",
        action="store_true",
        help="Analisa o registo completo num único segmento (mais lento, mais memória).",
    )
    p.add_argument(
        "--noise-window-sec",
        type=float,
        default=10.0,
        help="Duração de cada janela para análise de ruído (por omissão: 10 s).",
    )
    p.add_argument(
        "--noise-max-windows",
        type=int,
        default=12,
        help="Número máximo de janelas uniformemente espaçadas (por omissão: 12).",
    )
    p.add_argument(
        "--pli-hz",
        type=float,
        default=60.0,
        help="Frequência nominal da rede para deteção de PLI (por omissão: 60 Hz).",
    )
    return p.parse_args(argv)


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging()
    ensure_data_dirs()

    try:
        base_dir = mitdb_record_dir().resolve()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    stems = list_record_ids(base_dir)
    if not stems:
        logger.error("Nenhum ficheiro .hea encontrado em %s", base_dir)
        return 1

    out_path = args.output_csv or (PROCESSED_DATA_DIR / "mitdb_record_inventory.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for stem in stems:
        try:
            row = build_row(
                base_dir,
                stem,
                skip_noise=args.skip_noise,
                noise_full_record=args.noise_full_record,
                noise_window_sec=args.noise_window_sec,
                noise_max_windows=args.noise_max_windows,
                pli_hz=args.pli_hz,
            )
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha inesperada no registo %s", stem)
            if args.fail_fast:
                return 1

    cols = column_order()
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    df = df[cols]
    df.to_csv(out_path, index=False, encoding="utf-8")
    logger.info("Escrito %s (%s registos).", out_path, len(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
