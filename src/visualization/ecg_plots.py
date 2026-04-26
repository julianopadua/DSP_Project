# src/visualization/ecg_plots.py
"""Funções utilitárias de visualização para ECG e respostas de filtros."""

from __future__ import annotations

import numpy as np
from scipy import signal


def plot_overlay(
    ax,
    t: np.ndarray,
    raw: np.ndarray,
    filtered: np.ndarray,
    *,
    title: str = "",
    raw_label: str = "cru",
    filt_label: str = "filtrado",
    raw_color: str = "#bcbcbc",
    filt_color: str = "#1f77b4",
    ylabel: str = "amplitude (mV)",
):
    """Plota o sinal cru atrás (cinza) e o filtrado à frente (cor) para comparação visual."""
    ax.plot(t, raw, color=raw_color, alpha=0.95, lw=0.7, label=raw_label)
    ax.plot(t, filtered, color=filt_color, lw=0.9, label=filt_label)
    ax.set_xlabel("tempo (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    return ax


def plot_psd(
    ax,
    signals: dict,
    fs: float,
    *,
    title: str = "Espectro de potência (Welch)",
    xlim=None,
    db: bool = True,
):
    """Sobrepõe PSDs (Welch) para cada série em ``signals`` (label -> array)."""
    for label, x in signals.items():
        nperseg = min(len(x), 2048)
        f, pxx = signal.welch(x, fs=fs, nperseg=nperseg)
        y = 10 * np.log10(pxx + 1e-20) if db else pxx
        ax.plot(f, y, lw=0.9, label=label)
    ax.set_xlabel("frequência (Hz)")
    ax.set_ylabel("PSD (dB/Hz)" if db else "PSD")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    if xlim is not None:
        ax.set_xlim(xlim)
    return ax


def plot_filter_response(
    ax,
    fs: float,
    *,
    h: np.ndarray | None = None,
    sos: np.ndarray | None = None,
    ba: tuple[np.ndarray, np.ndarray] | None = None,
    title: str = "Resposta em frequência",
    xlim=None,
    db: bool = True,
    color: str = "#d62728",
):
    """Magnitude da resposta em frequência. Aceita FIR (h), SOS ou (b, a)."""
    if sos is not None:
        w, hh = signal.sosfreqz(sos, worN=8192, fs=fs)
    elif ba is not None:
        b, a = ba
        w, hh = signal.freqz(b, a, worN=8192, fs=fs)
    elif h is not None:
        w, hh = signal.freqz(h, worN=8192, fs=fs)
    else:
        raise ValueError("Forneça h, sos ou ba.")
    mag = np.abs(hh)
    y = 20 * np.log10(mag + 1e-12) if db else mag
    ax.plot(w, y, color=color, lw=0.9)
    ax.set_xlabel("frequência (Hz)")
    ax.set_ylabel("|H(f)| (dB)" if db else "|H(f)|")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    if xlim is not None:
        ax.set_xlim(xlim)
    return ax
