# src/preprocessing/iir_filters.py
"""Filtros IIR Butterworth como técnica alternativa de comparação.

A aplicação em fase zero via ``sosfiltfilt`` cancela a distorção de fase
não-linear inerente aos IIR, ao custo de não ser causal (offline).
"""

from __future__ import annotations

import numpy as np
from scipy import signal


def design_highpass_sos(fs: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
    return signal.butter(order, cutoff_hz, btype="highpass", fs=fs, output="sos")


def design_lowpass_sos(fs: float, cutoff_hz: float, order: int = 4) -> np.ndarray:
    return signal.butter(order, cutoff_hz, btype="lowpass", fs=fs, output="sos")


def design_bandstop_sos(
    fs: float, low_hz: float, high_hz: float, order: int = 4
) -> np.ndarray:
    return signal.butter(order, [low_hz, high_hz], btype="bandstop", fs=fs, output="sos")


def design_iirnotch(fs: float, freq_hz: float, q: float = 30.0):
    """Notch IIR de segunda ordem (b, a). Q controla a estreiteza."""
    b, a = signal.iirnotch(freq_hz, q, fs=fs)
    return b, a


def apply_sosfiltfilt(sos: np.ndarray, x: np.ndarray) -> np.ndarray:
    return signal.sosfiltfilt(sos, x)


def apply_filtfilt_ba(b: np.ndarray, a: np.ndarray, x: np.ndarray) -> np.ndarray:
    return signal.filtfilt(b, a, x)
