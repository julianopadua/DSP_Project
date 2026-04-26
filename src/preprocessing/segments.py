# src/preprocessing/segments.py
"""Seleção de segmentos de ECG real contendo símbolos de anotação de interesse.

Funções para extrair janelas de duração fixa que (i) contenham pelo menos
uma anotação de um símbolo-alvo e (ii) maximizem um indicador heurístico de
ruído, de modo a evidenciar trechos onde a filtragem é útil.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal as sp_signal


@dataclass
class Segment:
    record_id: str
    target_symbol: str
    channel: int
    start_sample: int
    end_sample: int
    fs: float
    x: np.ndarray
    annotations_samples: np.ndarray
    annotations_symbols: np.ndarray
    target_indices: np.ndarray
    noise_score: float

    @property
    def t(self) -> np.ndarray:
        return np.arange(len(self.x)) / self.fs

    @property
    def annotations_time(self) -> np.ndarray:
        return (self.annotations_samples - self.start_sample) / self.fs


def _noise_score(x: np.ndarray, fs: float) -> float:
    """Razão potência fora-da-banda (BW + EMG + PLI) sobre potência útil (1–30 Hz).

    Heurística simples para destacar janelas problemáticas: quanto maior a
    razão, mais ruído domina relativamente ao conteúdo do ECG.
    """
    nperseg = min(len(x), 1024)
    f, pxx = sp_signal.welch(x, fs=fs, nperseg=nperseg)
    bw = np.trapezoid(pxx[(f >= 0.05) & (f <= 0.8)], f[(f >= 0.05) & (f <= 0.8)])
    emg = np.trapezoid(pxx[(f >= 40.0) & (f <= min(90.0, fs / 2 - 1))],
                       f[(f >= 40.0) & (f <= min(90.0, fs / 2 - 1))])
    pli = np.trapezoid(pxx[(f >= 58.0) & (f <= 62.0)], f[(f >= 58.0) & (f <= 62.0)])
    useful = np.trapezoid(pxx[(f >= 1.0) & (f <= 30.0)], f[(f >= 1.0) & (f <= 30.0)])
    if useful < 1e-20:
        return float("inf")
    return float((bw + emg + pli) / useful)


def find_worst_window_with_symbol(
    x: np.ndarray,
    fs: float,
    annotations_samples: np.ndarray,
    annotations_symbols: np.ndarray,
    target_symbol: str,
    duration_sec: float,
) -> tuple[int, int, float]:
    """Encontra a janela de duração fixa que contém o símbolo-alvo e maximiza ruído.

    Para cada anotação com símbolo igual a ``target_symbol``, centra uma
    janela de ``duration_sec`` segundos sobre ela e calcula um indicador
    heurístico de ruído. Retorna a janela de pior pontuação.

    Retorna
    -------
    (start_sample, end_sample, noise_score)
    """
    n = int(round(duration_sec * fs))
    target_mask = np.asarray(annotations_symbols) == target_symbol
    target_samples = np.asarray(annotations_samples)[target_mask]
    if len(target_samples) == 0:
        raise ValueError(f"Símbolo {target_symbol!r} não está presente nas anotações.")

    best = (0, n, -np.inf)
    for s0 in target_samples:
        start = int(s0) - n // 2
        end = start + n
        if start < 0 or end > len(x):
            continue
        score = _noise_score(x[start:end], fs)
        if score > best[2]:
            best = (start, end, score)

    if not np.isfinite(best[2]):
        s0 = int(target_samples[0])
        start = max(0, s0 - n // 2)
        end = min(len(x), start + n)
        start = max(0, end - n)
        score = _noise_score(x[start:end], fs)
        return (start, end, score)
    return best


def extract_segment(
    record_id: str,
    x_full: np.ndarray,
    fs: float,
    annotations_samples: np.ndarray,
    annotations_symbols: np.ndarray,
    target_symbol: str,
    duration_sec: float,
    channel: int = 0,
) -> Segment:
    """Extrai um Segment fechado a partir de um sinal e suas anotações."""
    start, end, score = find_worst_window_with_symbol(
        x_full, fs, annotations_samples, annotations_symbols,
        target_symbol, duration_sec,
    )
    in_window = (annotations_samples >= start) & (annotations_samples < end)
    seg_samples = annotations_samples[in_window]
    seg_symbols = annotations_symbols[in_window]
    target_idx = np.where(seg_symbols == target_symbol)[0]
    return Segment(
        record_id=record_id,
        target_symbol=target_symbol,
        channel=channel,
        start_sample=start,
        end_sample=end,
        fs=fs,
        x=np.asarray(x_full[start:end], dtype=float),
        annotations_samples=seg_samples,
        annotations_symbols=seg_symbols,
        target_indices=target_idx,
        noise_score=score,
    )
