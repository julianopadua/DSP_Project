"""Variantes de pre-processamento usadas nas ablacões do paper."""

from __future__ import annotations

import numpy as np

from src.preprocessing.fir_filters import (
    apply_filtfilt,
    design_bandstop,
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
    notch_low_hz: float = 59.0,
    notch_high_hz: float = 61.0,
    lowpass_hz: float = 40.0,
) -> np.ndarray:
    """Aplica cadeia FIR HP -> notch -> LP com fase zero."""
    y = remove_mean(x)
    hp = design_highpass(fs, highpass_hz)
    bs = design_bandstop(fs, notch_low_hz, notch_high_hz)
    lp = design_lowpass(fs, lowpass_hz)
    for h in (hp, bs, lp):
        y = apply_filtfilt(h, y)
    return y
