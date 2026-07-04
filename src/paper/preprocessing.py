"""Variantes de pre-processamento usadas nas ablacões do paper."""

from __future__ import annotations

import numpy as np

from src.preprocessing.fir_filters import (
    apply_filtfilt,
    design_highpass,
    design_lowpass,
)


def remove_mean(x: np.ndarray) -> np.ndarray:
    """Remove nivel DC da janela/registro."""
    arr = np.asarray(x, dtype=float)
    return arr - np.nanmean(arr)


def denoise_fir_chain(
    x: np.ndarray,
    fs: float,
    *,
    highpass_hz: float = 0.5,
    lowpass_hz: float = 40.0,
) -> np.ndarray:
    """Aplica cadeia FIR passa-faixa 0,5-40 Hz com fase zero."""
    y = remove_mean(x)
    hp = design_highpass(fs, highpass_hz)
    lp = design_lowpass(fs, lowpass_hz)
    for h in (hp, lp):
        y = apply_filtfilt(h, y)
    return y
