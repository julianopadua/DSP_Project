# src/preprocessing/fir_filters.py
"""Projeto e aplicação de filtros FIR de fase linear para denoising de ECG.

Inclui projeto pelo método da janela (Hamming por omissão), aplicação em
modo causal com compensação de atraso e em modo de fase zero (filtfilt e
convolução rápida via FFT).
"""

from __future__ import annotations

import numpy as np
from scipy import signal


def hamming_numtaps(fs: float, transition_hz: float) -> int:
    """Número (ímpar) de coeficientes para janela Hamming dada a largura de transição.

    Aproximação clássica: N ≈ 3.3 · fs / Δf. Garante N ímpar para FIR Tipo I
    (passa-baixa simétrico) e Tipo III (rejeita-faixa simétrico) com fase linear.
    """
    n = int(np.ceil(3.3 * fs / transition_hz))
    return n + 1 if n % 2 == 0 else n


def design_highpass(
    fs: float,
    cutoff_hz: float,
    transition_hz: float = 1.0,
    window: str = "hamming",
) -> np.ndarray:
    """FIR passa-alta com fase linear (Tipo I, simétrico)."""
    n = hamming_numtaps(fs, transition_hz)
    return signal.firwin(n, cutoff_hz, fs=fs, window=window, pass_zero=False)


def design_lowpass(
    fs: float,
    cutoff_hz: float,
    transition_hz: float = 8.0,
    window: str = "hamming",
) -> np.ndarray:
    """FIR passa-baixa com fase linear (Tipo I, simétrico)."""
    n = hamming_numtaps(fs, transition_hz)
    return signal.firwin(n, cutoff_hz, fs=fs, window=window, pass_zero=True)


def design_bandstop(
    fs: float,
    low_hz: float,
    high_hz: float,
    transition_hz: float = 1.0,
    window: str = "hamming",
) -> np.ndarray:
    """FIR rejeita-faixa com fase linear (notch FIR para PLI)."""
    n = hamming_numtaps(fs, transition_hz)
    return signal.firwin(n, [low_hz, high_hz], fs=fs, window=window, pass_zero=True)


def apply_filtfilt(h: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Filtragem em fase zero (forward-backward). Magnitude ao quadrado e atraso nulo."""
    return signal.filtfilt(h, [1.0], x)


def apply_lfilter_compensated(h: np.ndarray, x: np.ndarray) -> np.ndarray:
    """FIR causal com compensação de atraso de grupo (M-1)/2."""
    y = signal.lfilter(h, [1.0], x)
    delay = (len(h) - 1) // 2
    if delay <= 0:
        return y
    return np.concatenate([y[delay:], np.full(delay, y[-1])])


def apply_fft(h: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Convolução rápida via FFT (overlap-save interno do scipy).

    Para h simétrico, ``mode='same'`` devolve a saída alinhada com a entrada
    (compensa automaticamente o atraso de fase linear).
    """
    return signal.fftconvolve(x, h, mode="same")
