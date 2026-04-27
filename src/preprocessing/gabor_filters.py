# src/preprocessing/gabor_filters.py
"""Filtros de Gabor 1D para analise tempo-frequencia de ECG.

Um filtro de Gabor 1D e uma onda senoidal modulada por uma gaussiana.
Sua resposta ao impulso e:

    g(t, f0, sigma) = exp(-t^2 / (2*sigma^2)) * cos(2*pi*f0*t)   [parte real]
    g(t, f0, sigma) = exp(-t^2 / (2*sigma^2)) * sin(2*pi*f0*t)   [parte imaginaria]

A convolucao do sinal com g_real e g_imag produz a amplitude instantanea
(envelope) em torno de f0, permitindo construir uma representacao
tempo-frequencia: o escalograma de Gabor.

sigma controla o compromisso tempo-frequencia (incerteza de Heisenberg):
sigma pequeno -> boa resolucao temporal, pobre em frequencia;
sigma grande  -> boa resolucao em frequencia, pobre no tempo.

Usamos sigma = n_cycles / (2*pi*f0), o que fixa o numero de ciclos dentro
do envelope e mantem resolucao relativa constante (banco de filtros Q-constante).
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal


def gabor_kernel(
    f0: float,
    fs: float,
    n_cycles: float = 3.0,
    n_sigma: float = 4.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Kernels real e imaginario de um filtro de Gabor 1D centrado em f0 Hz.

    Parametros
    ----------
    f0      : frequencia central (Hz).
    fs      : frequencia de amostragem (Hz).
    n_cycles: numero de ciclos dentro do envelope gaussiano; controla sigma.
    n_sigma : extensao temporal do kernel em multiplos de sigma.

    Retorna
    -------
    t      : eixo temporal do kernel (s), simetrico em torno de 0.
    h_real : parte real (cosseno modulado por gaussiana).
    h_imag : parte imaginaria (seno modulado por gaussiana).
    """
    sigma = n_cycles / (2.0 * np.pi * f0)
    half = int(np.ceil(n_sigma * sigma * fs))
    t = np.arange(-half, half + 1) / fs
    envelope = np.exp(-(t ** 2) / (2.0 * sigma ** 2))
    h_real = envelope * np.cos(2.0 * np.pi * f0 * t)
    h_imag = envelope * np.sin(2.0 * np.pi * f0 * t)
    # normaliza pela energia do envelope para amplitude 1 na frequencia central
    norm = np.sum(envelope ** 2) / fs
    h_real = h_real / (norm * fs)
    h_imag = h_imag / (norm * fs)
    return t, h_real, h_imag


def gabor_energy(
    x: np.ndarray,
    f0: float,
    fs: float,
    n_cycles: float = 3.0,
) -> np.ndarray:
    """Energia instantanea do sinal em torno de f0 (quadrado da amplitude de Gabor)."""
    _, h_real, h_imag = gabor_kernel(f0, fs, n_cycles=n_cycles)
    yr = sp_signal.fftconvolve(x, h_real, mode="same")
    yi = sp_signal.fftconvolve(x, h_imag, mode="same")
    return yr ** 2 + yi ** 2


def gabor_scalogram(
    x: np.ndarray,
    fs: float,
    freqs: np.ndarray,
    n_cycles: float = 3.0,
) -> np.ndarray:
    """Escalograma de Gabor: matriz (len(freqs), len(x)) de energia instantanea.

    Cada linha e a energia de Gabor do sinal em torno da frequencia freqs[i].
    """
    scalogram = np.zeros((len(freqs), len(x)), dtype=float)
    for i, f0 in enumerate(freqs):
        scalogram[i, :] = gabor_energy(x, f0, fs, n_cycles=n_cycles)
    return scalogram


def stft_spectrogram(
    x: np.ndarray,
    fs: float,
    window_sec: float = 0.5,
    overlap: float = 0.9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Espectrograma via STFT (Transformada de Fourier de Curta Duracao).

    Parametros
    ----------
    x          : sinal 1-D.
    fs         : frequencia de amostragem (Hz).
    window_sec : duracao da janela de analise (s).
    overlap    : fracao de sobreposicao entre janelas consecutivas [0, 1).

    Retorna
    -------
    f   : frequencias (Hz).
    t   : instantes de tempo (s).
    Sxx : espectro de potencia (dB/Hz), shape (len(f), len(t)).
    """
    nperseg = int(round(window_sec * fs))
    nperseg = max(nperseg, 16)
    noverlap = int(round(overlap * nperseg))
    f, t, Sxx = sp_signal.spectrogram(
        x, fs=fs, window="hann", nperseg=nperseg, noverlap=noverlap, scaling="density"
    )
    Sxx_db = 10.0 * np.log10(Sxx + 1e-20)
    return f, t, Sxx_db
