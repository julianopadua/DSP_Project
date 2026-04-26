# src/preprocessing/metrics.py
"""Métricas padronizadas para avaliação de denoising em sinais reais de ECG.

Trabalhamos sem sinal limpo de referência (ground truth), portanto todas as
métricas são baseadas em propriedades espectrais e temporais do próprio
sinal observado:

- redução de potência na banda alvo (BW, PLI, EMG) em dB;
- variação de potência na banda passante (1–30 Hz) em dB;
- estabilidade temporal de picos R (deslocamento médio em ms).
"""

from __future__ import annotations

import numpy as np
from scipy import signal


def band_power(
    x: np.ndarray,
    fs: float,
    low_hz: float,
    high_hz: float,
    nperseg: int | None = None,
) -> float:
    """Potência integrada (Welch) na banda [low_hz, high_hz]."""
    nperseg = nperseg if nperseg is not None else min(len(x), 2048)
    f, pxx = signal.welch(x, fs=fs, nperseg=nperseg)
    mask = (f >= low_hz) & (f <= high_hz)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(pxx[mask], f[mask]))


def power_reduction_db(
    x_before: np.ndarray,
    x_after: np.ndarray,
    fs: float,
    low_hz: float,
    high_hz: float,
) -> float:
    """Redução em dB na banda alvo (positivo = atenuação)."""
    p_b = band_power(x_before, fs, low_hz, high_hz)
    p_a = band_power(x_after, fs, low_hz, high_hz)
    if p_a < 1e-20:
        return float("inf")
    if p_b < 1e-20:
        return 0.0
    return 10.0 * np.log10(p_b / p_a)


def passband_change_db(
    x_before: np.ndarray,
    x_after: np.ndarray,
    fs: float,
    low_hz: float = 1.0,
    high_hz: float = 30.0,
) -> float:
    """Variação na banda passante. ~0 dB indica preservação adequada."""
    p_b = band_power(x_before, fs, low_hz, high_hz)
    p_a = band_power(x_after, fs, low_hz, high_hz)
    if p_b < 1e-20:
        return 0.0
    return 10.0 * np.log10(p_a / p_b)


def r_peak_shift_ms(
    annotations_samples: np.ndarray,
    x_filtered: np.ndarray,
    fs: float,
    search_ms: float = 50.0,
) -> dict[str, float]:
    """Deslocamento de picos R: para cada anotação, busca o extremo absoluto local.

    Sem sinal limpo de referência, comparamos a posição da anotação WFDB
    com a posição do extremo absoluto numa janela de ±search_ms no sinal
    filtrado. Espera-se valores pequenos (< 5 ms) para FIR de fase linear
    aplicado com filtfilt.
    """
    half = int(round(search_ms * 1e-3 * fs))
    shifts: list[float] = []
    for s0 in np.asarray(annotations_samples).ravel():
        s0 = int(s0)
        lo = max(0, s0 - half)
        hi = min(len(x_filtered), s0 + half + 1)
        if hi - lo < 3:
            continue
        local = x_filtered[lo:hi]
        peak = lo + int(np.argmax(np.abs(local - np.mean(local))))
        shifts.append((peak - s0) / fs * 1000.0)
    if not shifts:
        return {"n": 0, "median_ms": float("nan"), "rms_ms": float("nan"), "max_ms": float("nan")}
    arr = np.asarray(shifts, dtype=float)
    return {
        "n": int(arr.size),
        "median_ms": float(np.median(arr)),
        "rms_ms": float(np.sqrt(np.mean(arr ** 2))),
        "max_ms": float(np.max(np.abs(arr))),
    }


def evaluate_denoising(
    name: str,
    raw: np.ndarray,
    filtered: np.ndarray,
    fs: float,
    target_band: tuple[float, float],
    *,
    passband: tuple[float, float] = (1.0, 30.0),
    annotations: np.ndarray | None = None,
) -> dict[str, float | str | int]:
    """Linha consolidada de métricas para um par (método, ruído).

    Compara o sinal real bruto (``raw``) com a saída filtrada (``filtered``)
    em três eixos: redução na banda alvo, variação na banda passante e
    estabilidade temporal dos picos R (se as anotações estiverem presentes).
    """
    out: dict[str, float | str | int] = {"método": name}
    out["redução_alvo_dB"] = power_reduction_db(
        raw, filtered, fs, target_band[0], target_band[1]
    )
    out["preservação_passband_dB"] = passband_change_db(
        raw, filtered, fs, passband[0], passband[1]
    )
    if annotations is not None and len(annotations) > 0:
        sh = r_peak_shift_ms(annotations, filtered, fs)
        out["picos_R_RMS_ms"] = sh["rms_ms"]
        out["picos_R_max_ms"] = sh["max_ms"]
        out["picos_R_n"] = sh["n"]
    return out
