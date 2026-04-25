# src/preprocessing/simple_filters.py
"""Filtros simples: média móvel e filtragem direta no domínio da frequência.

Estes métodos são propositadamente menos sofisticados que o FIR janelado.
São incluídos para comparação didática (vantagens, limitações e artefatos).
"""

from __future__ import annotations

import numpy as np
from scipy import signal


def moving_average(x: np.ndarray, n: int) -> np.ndarray:
    """Média móvel centrada de comprimento ``n`` (convolução com pulso unitário/N)."""
    n = int(n)
    if n < 1:
        raise ValueError("n deve ser >= 1")
    h = np.ones(n) / n
    return signal.fftconvolve(x, h, mode="same")


def baseline_via_ma(x: np.ndarray, n: int) -> np.ndarray:
    """Estimativa de baseline por MA longa. Subtraia de x para remover BW."""
    return moving_average(x, n)


def remove_baseline_ma(x: np.ndarray, n: int) -> np.ndarray:
    """Remove BW subtraindo a média móvel longa: comportamento passa-alta aproximado."""
    return x - moving_average(x, n)


def pli_notch_via_ma(x: np.ndarray, period_samples: int) -> np.ndarray:
    """Notch via média móvel cujo comprimento é exatamente o período da PLI.

    A MA de N amostras tem zeros em fs/N e seus múltiplos. Em fs=360 Hz e PLI=60 Hz,
    N=6 zera 60, 120 e 180 Hz, atuando como pente de notches.
    """
    return moving_average(x, period_samples)


def freq_domain_filter(
    x: np.ndarray,
    fs: float,
    zero_below_hz: float | None = None,
    zero_above_hz: float | None = None,
    notch_band_hz: tuple[float, float] | None = None,
) -> np.ndarray:
    """Filtragem ideal por zeragem direta de bins na FFT (rectangular brick-wall).

    Útil para demonstrar limitações: introduz oscilações de Gibbs e
    transientes de borda quando o sinal não é periódico no bloco.
    """
    n = len(x)
    spectrum = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    mask = np.ones_like(freqs, dtype=bool)
    if zero_below_hz is not None:
        mask &= ~(freqs < zero_below_hz)
    if zero_above_hz is not None:
        mask &= ~(freqs > zero_above_hz)
    if notch_band_hz is not None:
        lo, hi = notch_band_hz
        mask &= ~((freqs >= lo) & (freqs <= hi))
    return np.fft.irfft(spectrum * mask, n=n)
