"""Helpers de figuras do paper, sem depender de notebooks."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.config import PAPER_FIGURES_DIR, ensure_paper_dirs


def save_current_figure(name: str, *, dpi: int = 180) -> Path:
    """Salva a figura atual na pasta padrao do artigo."""
    ensure_paper_dirs()
    path = PAPER_FIGURES_DIR / name
    plt.savefig(path, dpi=dpi, bbox_inches="tight")
    return path


def plot_raw_filtered_overlay(t_s: np.ndarray, raw: np.ndarray, filtered: np.ndarray):
    """Figura base para comparar ECG bruto e filtrado."""
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(t_s, raw, lw=0.8, alpha=0.65, label="bruto")
    ax.plot(t_s, filtered, lw=1.0, label="filtrado")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig
