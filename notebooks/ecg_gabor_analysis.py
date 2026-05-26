"""
ecg_gabor_analysis.py
=====================
Módulo completo de detecção de ondas ECG por filtros de Gabor 1D.

Fluxo:
  1. Gabor PAR  (φ=0, cosseno) → detecta picos siméticos  → R
  2. Gabor ÍMPAR (φ=π/2, seno) → detecta transições         → borda Q / borda S
  3. Energia combinada E = par² + ímpar²  → localização de fase independente
  4. Gabor P  (f0 baixa, σ amplo, janela pré-R)  → onda P
  5. Gabor T  (f0 muito baixa, σ maior, janela pós-R) → onda T
  6. Extração de Q e S por mínimo local ao redor do R
  7. Cálculo dos intervalos PR, QRS, RR, ST, QT com propagação de erro

Incerteza:
  - Erro de amostragem:    δt_s = 1/fs  (≈ 2,78 ms para fs=360 Hz)
  - Erro de localização Gabor: δt_g ≈ 1/(4π·f0)  (princípio incerteza T-F)
  - Erro combinado:        δt = √(δt_s² + δt_g²)
  - Erro de intervalo (2 pontos): δI = √2 · δt

Intervalos clínicos normais de referência (adultos):
  PR:  120 – 200 ms
  QRS:  60 – 120 ms
  QT:  350 – 450 ms  (não corrigido pela FC)
  RR:  600 – 1000 ms (60 – 100 bpm)
  ST:   80 – 120 ms  (início do segmento ST ao pico T)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.signal as sp_signal


# ──────────────────────────────────────────────────────────────────────────────
# 1. ESTRUTURAS DE DADOS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class WavePoint:
    """Posição de uma onda detectada com estimativa de incerteza."""
    sample: int                  # índice de amostra
    time_s: float                # tempo em segundos
    amplitude: float             # amplitude no sinal filtrado
    uncertainty_ms: float        # ± ms (1σ)
    energy_ratio: float = 1.0   # confiança relativa [0,1]

    def __repr__(self):
        return (f"WavePoint(t={self.time_s*1000:.1f}ms, "
                f"amp={self.amplitude:.4f}mV, ±{self.uncertainty_ms:.1f}ms)")


@dataclass
class BeatFeatures:
    """Todas as ondas e intervalos de um único batimento cardíaco."""
    beat_index: int
    R:  Optional[WavePoint] = None
    P:  Optional[WavePoint] = None
    Q:  Optional[WavePoint] = None
    S:  Optional[WavePoint] = None
    T:  Optional[WavePoint] = None

    # Intervalos [ms]
    RR_ms:  Optional[float] = None
    PR_ms:  Optional[float] = None   # P-peak → R-peak  (aprox. PQ onset)
    QRS_ms: Optional[float] = None   # Q mínimo → S mínimo
    ST_ms:  Optional[float] = None   # S → T pico
    QT_ms:  Optional[float] = None   # Q → T pico

    # Erros ±1σ [ms]
    RR_err:  Optional[float] = None
    PR_err:  Optional[float] = None
    QRS_err: Optional[float] = None
    ST_err:  Optional[float] = None
    QT_err:  Optional[float] = None

    # Flags clínicas
    flags: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# 2. GERAÇÃO DOS KERNELS DE GABOR
# ──────────────────────────────────────────────────────────────────────────────

def make_gabor_kernel(
    fs: float,
    f0: float,
    sigma: float,
    phi: float = 0.0,
    n_sigma: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Gera kernel de Gabor 1D normalizado pela energia.

    Equação:
        g(t) = exp(-t² / 2σ²) · cos(2π·f0·t + φ)

    φ = 0      → Gabor PAR   (simétrico, detecta picos)
    φ = π/2    → Gabor ÍMPAR (antissimétrico, detecta bordas)

    Retorna (t, g) onde t é o vetor de tempo em segundos.
    """
    t_max = n_sigma * sigma
    t = np.arange(-t_max, t_max + 1 / fs, 1 / fs)
    envelope = np.exp(-(t ** 2) / (2 * sigma ** 2))
    carrier  = np.cos(2 * np.pi * f0 * t + phi)
    g = envelope * carrier

    # Normalização pela norma L2 para amplitude comparável entre kernels
    norm = np.sqrt(np.sum(g ** 2))
    if norm > 0:
        g /= norm
    return t, g


def gabor_energy(
    x: np.ndarray,
    fs: float,
    f0: float,
    sigma: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcula a energia combinada par² + ímpar² (independente de fase).

    Retorna (response_even, response_odd, energy).
    A energia E(t) dá um envelope suave alinhado ao evento morfológico.
    """
    _, g_even = make_gabor_kernel(fs, f0, sigma, phi=0.0)
    _, g_odd  = make_gabor_kernel(fs, f0, sigma, phi=math.pi / 2)

    r_even = np.convolve(x, g_even, mode='same')
    r_odd  = np.convolve(x, g_odd,  mode='same')
    energy = r_even ** 2 + r_odd ** 2
    return r_even, r_odd, energy


# ──────────────────────────────────────────────────────────────────────────────
# 3. INCERTEZA DE LOCALIZAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def _gabor_uncertainty_ms(fs: float, f0: float) -> float:
    """
    Incerteza combinada de um único ponto detectado por Gabor.

    δt_s = 1/fs             (resolução de amostragem)
    δt_g = 1/(4π·f0)        (limite Heisenberg tempo-frequência)
    δt   = √(δt_s² + δt_g²)

    Retorna δt em milissegundos.
    """
    dt_s = 1.0 / fs
    dt_g = 1.0 / (4.0 * math.pi * f0)
    return math.sqrt(dt_s ** 2 + dt_g ** 2) * 1000.0


def _interval_uncertainty_ms(err1_ms: float, err2_ms: float) -> float:
    """Propagação de erro para intervalo = t2 - t1."""
    return math.sqrt(err1_ms ** 2 + err2_ms ** 2)


# ──────────────────────────────────────────────────────────────────────────────
# 4. DETECÇÃO DO COMPLEXO QRS (R, Q, S)
# ──────────────────────────────────────────────────────────────────────────────

# Parâmetros recomendados para o QRS no MIT-BIH (fs=360 Hz)
QRS_F0    = 15.0   # Hz — energia dominante do complexo QRS
QRS_SIGMA = 0.04   # s  — ≈ metade da largura típica do QRS (80–120 ms)

# Janela de busca para Q e S ao redor do R
Q_SEARCH_MS = 60.0  # ms antes do R
S_SEARCH_MS = 60.0  # ms após o R


def detect_R_peaks(
    x: np.ndarray,
    fs: float,
    ann_samples: np.ndarray,
    f0: float = QRS_F0,
    sigma: float = QRS_SIGMA,
    search_window_ms: float = 80.0,
) -> list[WavePoint]:
    """
    Refina as posições do pico R usando a energia combinada Gabor (par² + ímpar²).

    Para cada anotação de referência, busca o máximo de energia na janela
    ±search_window_ms e retorna um WavePoint com a incerteza estimada.
    """
    _, _, energy = gabor_energy(x, fs, f0, sigma)
    unc_ms = _gabor_uncertainty_ms(fs, f0)
    hw = int(search_window_ms / 1000.0 * fs)

    points: list[WavePoint] = []
    e_max_global = np.max(energy)

    for idx in ann_samples:
        lo = max(0, idx - hw)
        hi = min(len(energy), idx + hw)
        local_max = lo + int(np.argmax(energy[lo:hi]))
        ratio = float(energy[local_max] / e_max_global) if e_max_global > 0 else 0.0

        points.append(WavePoint(
            sample=local_max,
            time_s=local_max / fs,
            amplitude=float(x[local_max]),
            uncertainty_ms=unc_ms,
            energy_ratio=ratio,
        ))
    return points


def _find_local_min(x: np.ndarray, center: int, half_win: int) -> int:
    """Índice do mínimo local num segmento."""
    lo = max(0, center - half_win)
    hi = min(len(x), center + half_win)
    return lo + int(np.argmin(x[lo:hi]))


def detect_QS_waves(
    x: np.ndarray,
    fs: float,
    r_points: list[WavePoint],
    q_search_ms: float = Q_SEARCH_MS,
    s_search_ms: float = S_SEARCH_MS,
) -> tuple[list[Optional[WavePoint]], list[Optional[WavePoint]]]:
    """
    Detecta Q e S como mínimos locais imediatamente antes/após o R.

    Q: mínimo no intervalo [R - q_search_ms, R]
    S: mínimo no intervalo [R, R + s_search_ms]

    Incerteza:  ±1 amostra (resolução do sinal, sem Gabor) + erro de amostragem.
    """
    hw_q = int(q_search_ms / 1000.0 * fs)
    hw_s = int(s_search_ms / 1000.0 * fs)
    dt_ms = (1.0 / fs) * 1000.0  # ≈ 2.78 ms

    q_list: list[Optional[WavePoint]] = []
    s_list: list[Optional[WavePoint]] = []

    for rp in r_points:
        ri = rp.sample

        # --- Q ---
        lo_q = max(0, ri - hw_q)
        qi   = _find_local_min(x, (lo_q + ri) // 2, hw_q // 2)
        # garante que Q está antes do R
        if qi >= ri:
            qi = lo_q + int(np.argmin(x[lo_q:ri]))
        q_list.append(WavePoint(
            sample=qi, time_s=qi / fs, amplitude=float(x[qi]),
            uncertainty_ms=dt_ms * math.sqrt(2),  # 2 amostras de incerteza
        ))

        # --- S ---
        hi_s = min(len(x), ri + hw_s)
        si   = _find_local_min(x, (ri + hi_s) // 2, hw_s // 2)
        if si <= ri:
            si = ri + int(np.argmin(x[ri:hi_s]))
        s_list.append(WavePoint(
            sample=si, time_s=si / fs, amplitude=float(x[si]),
            uncertainty_ms=dt_ms * math.sqrt(2),
        ))

    return q_list, s_list


# ──────────────────────────────────────────────────────────────────────────────
# 5. DETECÇÃO DA ONDA P
# ──────────────────────────────────────────────────────────────────────────────

# Parâmetros para onda P
P_F0    = 6.0    # Hz — P é lenta, 0.5–10 Hz
P_SIGMA = 0.06   # s  — envoltória mais larga (onda mais longa)

# Janela de busca relativa ao R  [ms]
P_WIN_BEFORE_R = 280.0  # início da janela (ms antes do R)
P_WIN_AFTER_R  =  80.0  # fim da janela   (ms antes do R)


def detect_P_waves(
    x: np.ndarray,
    fs: float,
    r_points: list[WavePoint],
    f0: float = P_F0,
    sigma: float = P_SIGMA,
    win_before_ms: float = P_WIN_BEFORE_R,
    win_after_ms:  float = P_WIN_AFTER_R,
) -> list[Optional[WavePoint]]:
    """
    Detecta o pico da onda P usando energia Gabor de baixa frequência.

    Janela de busca: [R - win_before_ms, R - win_after_ms]
    Raciocínio fisiológico: intervalo PR normal é 120–200 ms;
    A busca começa antes para capturar casos limítrofes (até 280 ms).
    """
    _, _, energy = gabor_energy(x, fs, f0, sigma)
    unc_ms = _gabor_uncertainty_ms(fs, f0)
    e_max  = np.max(energy)

    hw_before = int(win_before_ms / 1000.0 * fs)
    hw_after  = int(win_after_ms  / 1000.0 * fs)

    p_list: list[Optional[WavePoint]] = []

    for rp in r_points:
        ri = rp.sample
        lo = max(0, ri - hw_before)
        hi = max(lo + 1, ri - hw_after)

        if hi - lo < 3:
            p_list.append(None)
            continue

        pi   = lo + int(np.argmax(energy[lo:hi]))
        ratio = float(energy[pi] / e_max) if e_max > 0 else 0.0

        p_list.append(WavePoint(
            sample=pi, time_s=pi / fs, amplitude=float(x[pi]),
            uncertainty_ms=unc_ms, energy_ratio=ratio,
        ))

    return p_list


# ──────────────────────────────────────────────────────────────────────────────
# 6. DETECÇÃO DA ONDA T
# ──────────────────────────────────────────────────────────────────────────────

# Parâmetros para onda T
T_F0    = 4.0    # Hz — T é ainda mais lenta que P
T_SIGMA = 0.10   # s  — envoltória bem larga

# Janela de busca relativa ao R [ms]
T_WIN_START = 120.0  # ms após R (após a refratariedade do QRS)
T_WIN_END   = 500.0  # ms após R (limite típico do QT)


def detect_T_waves(
    x: np.ndarray,
    fs: float,
    r_points: list[WavePoint],
    f0: float = T_F0,
    sigma: float = T_SIGMA,
    win_start_ms: float = T_WIN_START,
    win_end_ms:   float = T_WIN_END,
) -> list[Optional[WavePoint]]:
    """
    Detecta o pico da onda T usando energia Gabor de frequência muito baixa.

    Janela de busca: [R + win_start_ms, R + win_end_ms]
    """
    _, _, energy = gabor_energy(x, fs, f0, sigma)
    unc_ms = _gabor_uncertainty_ms(fs, f0)
    e_max  = np.max(energy)

    hw_start = int(win_start_ms / 1000.0 * fs)
    hw_end   = int(win_end_ms   / 1000.0 * fs)

    t_list: list[Optional[WavePoint]] = []

    for rp in r_points:
        ri = rp.sample
        lo = min(len(x) - 1, ri + hw_start)
        hi = min(len(x),     ri + hw_end)

        if hi - lo < 3:
            t_list.append(None)
            continue

        ti   = lo + int(np.argmax(energy[lo:hi]))
        ratio = float(energy[ti] / e_max) if e_max > 0 else 0.0

        t_list.append(WavePoint(
            sample=ti, time_s=ti / fs, amplitude=float(x[ti]),
            uncertainty_ms=unc_ms, energy_ratio=ratio,
        ))

    return t_list


# ──────────────────────────────────────────────────────────────────────────────
# 7. MONTAGEM DOS BATIMENTOS E CÁLCULO DE INTERVALOS
# ──────────────────────────────────────────────────────────────────────────────

# Limites clínicos normais [ms]
CLINICAL_RANGES = {
    "PR_ms":  (120.0, 200.0),
    "QRS_ms": ( 60.0, 120.0),
    "QT_ms":  (350.0, 450.0),
    "RR_ms":  (600.0, 1000.0),
    "ST_ms":  ( 80.0, 200.0),
}


def build_beat_features(
    x: np.ndarray,
    fs: float,
    ann_samples: np.ndarray,
    qrs_f0:   float = QRS_F0,
    qrs_sigma:float = QRS_SIGMA,
    p_f0:     float = P_F0,
    p_sigma:  float = P_SIGMA,
    t_f0:     float = T_F0,
    t_sigma:  float = T_SIGMA,
) -> list[BeatFeatures]:
    """
    Pipeline completo: detecta todas as ondas e calcula intervalos.
    Retorna lista de BeatFeatures, uma por batimento.
    """
    r_pts = detect_R_peaks(x, fs, ann_samples, qrs_f0, qrs_sigma)
    q_pts, s_pts = detect_QS_waves(x, fs, r_pts)
    p_pts = detect_P_waves(x, fs, r_pts, p_f0, p_sigma)
    t_pts = detect_T_waves(x, fs, r_pts, t_f0, t_sigma)

    beats: list[BeatFeatures] = []

    for i, (rp, qp, sp, pp, tp) in enumerate(
        zip(r_pts, q_pts, s_pts, p_pts, t_pts)
    ):
        bf = BeatFeatures(beat_index=i + 1, R=rp, P=pp, Q=qp, S=sp, T=tp)

        # ── RR ──
        if i > 0 and beats[i - 1].R is not None:
            rr = (rp.time_s - beats[i - 1].R.time_s) * 1000.0
            bf.RR_ms  = rr
            bf.RR_err = _interval_uncertainty_ms(rp.uncertainty_ms,
                                                  beats[i - 1].R.uncertainty_ms)

        # ── PR ──
        if pp is not None:
            pr = (rp.time_s - pp.time_s) * 1000.0
            if pr > 0:
                bf.PR_ms  = pr
                bf.PR_err = _interval_uncertainty_ms(rp.uncertainty_ms,
                                                      pp.uncertainty_ms)

        # ── QRS ──
        if qp is not None and sp is not None:
            qrs = (sp.time_s - qp.time_s) * 1000.0
            if qrs > 0:
                bf.QRS_ms  = qrs
                bf.QRS_err = _interval_uncertainty_ms(qp.uncertainty_ms,
                                                       sp.uncertainty_ms)

        # ── ST ──
        if sp is not None and tp is not None:
            st = (tp.time_s - sp.time_s) * 1000.0
            if st > 0:
                bf.ST_ms  = st
                bf.ST_err = _interval_uncertainty_ms(sp.uncertainty_ms,
                                                      tp.uncertainty_ms)

        # ── QT ──
        if qp is not None and tp is not None:
            qt = (tp.time_s - qp.time_s) * 1000.0
            if qt > 0:
                bf.QT_ms  = qt
                bf.QT_err = _interval_uncertainty_ms(qp.uncertainty_ms,
                                                      tp.uncertainty_ms)

        # ── Flags clínicas ──
        for key, (lo, hi) in CLINICAL_RANGES.items():
            val = getattr(bf, key)
            if val is not None and not (lo <= val <= hi):
                bf.flags.append(f"{key}={val:.0f}ms (ref {lo:.0f}–{hi:.0f})")

        beats.append(bf)

    return beats


# ──────────────────────────────────────────────────────────────────────────────
# 8. EXPORTAÇÃO PARA DATAFRAME
# ──────────────────────────────────────────────────────────────────────────────

def beats_to_dataframe(beats: list[BeatFeatures]) -> pd.DataFrame:
    """Converte lista de BeatFeatures para DataFrame tabulado."""
    rows = []
    for b in beats:
        rows.append({
            "Batimento":     b.beat_index,
            "R (s)":         round(b.R.time_s, 4) if b.R else None,
            "R amp (mV)":    round(b.R.amplitude, 4) if b.R else None,
            "P (s)":         round(b.P.time_s, 4) if b.P else None,
            "Q (s)":         round(b.Q.time_s, 4) if b.Q else None,
            "S (s)":         round(b.S.time_s, 4) if b.S else None,
            "T (s)":         round(b.T.time_s, 4) if b.T else None,
            "RR (ms)":       round(b.RR_ms,  1) if b.RR_ms  is not None else None,
            "±RR (ms)":      round(b.RR_err, 1) if b.RR_err is not None else None,
            "PR (ms)":       round(b.PR_ms,  1) if b.PR_ms  is not None else None,
            "±PR (ms)":      round(b.PR_err, 1) if b.PR_err is not None else None,
            "QRS (ms)":      round(b.QRS_ms, 1) if b.QRS_ms is not None else None,
            "±QRS (ms)":     round(b.QRS_err,1) if b.QRS_err is not None else None,
            "ST (ms)":       round(b.ST_ms,  1) if b.ST_ms  is not None else None,
            "±ST (ms)":      round(b.ST_err, 1) if b.ST_err is not None else None,
            "QT (ms)":       round(b.QT_ms,  1) if b.QT_ms  is not None else None,
            "±QT (ms)":      round(b.QT_err, 1) if b.QT_err is not None else None,
            "Flags":         "; ".join(b.flags) if b.flags else "",
        })
    return pd.DataFrame(rows)


def beats_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Estatísticas descritivas dos intervalos (média ± dp)."""
    cols = ["RR (ms)", "PR (ms)", "QRS (ms)", "ST (ms)", "QT (ms)"]
    stats = df[cols].agg(["mean", "std", "min", "max"]).T
    stats.columns = ["Média (ms)", "DP (ms)", "Mín (ms)", "Máx (ms)"]
    stats = stats.round(1)

    # Referências
    ref = {
        "RR (ms)":  "600 – 1000",
        "PR (ms)":  "120 – 200",
        "QRS (ms)": "60 – 120",
        "ST (ms)":  "80 – 200",
        "QT (ms)":  "350 – 450",
    }
    stats["Ref. Normal (ms)"] = stats.index.map(ref)
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# 9. VISUALIZAÇÕES
# ──────────────────────────────────────────────────────────────────────────────

def plot_gabor_kernels(fs: float = 360.0):
    """
    Painel comparativo: kernels par, ímpar e energia dos três filtros
    (QRS, P, T) com seus espectros de magnitude.
    """
    configs = [
        {"label": "QRS",  "f0": QRS_F0, "sigma": QRS_SIGMA, "color": "tab:blue"},
        {"label": "Onda P", "f0": P_F0, "sigma": P_SIGMA,   "color": "tab:green"},
        {"label": "Onda T", "f0": T_F0, "sigma": T_SIGMA,   "color": "tab:red"},
    ]

    fig, axes = plt.subplots(len(configs), 3, figsize=(14, 9))
    fig.suptitle("Kernels de Gabor: Par (φ=0), Ímpar (φ=π/2) e Espectro",
                 fontweight="bold", fontsize=13)

    for row, cfg in enumerate(configs):
        f0, sigma, color, label = cfg["f0"], cfg["sigma"], cfg["color"], cfg["label"]

        t_k, g_even = make_gabor_kernel(fs, f0, sigma, phi=0.0)
        _,   g_odd  = make_gabor_kernel(fs, f0, sigma, phi=math.pi / 2)

        # Coluna 0: Par (cosseno)
        ax = axes[row, 0]
        ax.plot(t_k * 1000, g_even, color=color, lw=1.5)
        ax.fill_between(t_k * 1000, g_even, alpha=0.15, color=color)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{label} — Gabor PAR (φ=0)", fontweight="bold")
        ax.set_xlabel("Tempo (ms)")
        ax.set_ylabel("Amplitude norm.")
        ax.grid(True, alpha=0.3)

        # Coluna 1: Ímpar (seno)
        ax = axes[row, 1]
        ax.plot(t_k * 1000, g_odd, color=color, lw=1.5, linestyle="--")
        ax.fill_between(t_k * 1000, g_odd, alpha=0.15, color=color)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{label} — Gabor ÍMPAR (φ=π/2)", fontweight="bold")
        ax.set_xlabel("Tempo (ms)")
        ax.set_ylabel("Amplitude norm.")
        ax.grid(True, alpha=0.3)

        # Coluna 2: Espectro de magnitude (FFT)
        ax = axes[row, 2]
        N_fft = max(4096, len(g_even) * 8)
        freqs = np.fft.rfftfreq(N_fft, d=1 / fs)
        mag_even = np.abs(np.fft.rfft(g_even, n=N_fft))
        mag_odd  = np.abs(np.fft.rfft(g_odd,  n=N_fft))
        mag_even /= np.max(mag_even)
        mag_odd  /= np.max(mag_odd)

        ax.plot(freqs, mag_even, color=color, lw=1.5, label="Par")
        ax.plot(freqs, mag_odd,  color=color, lw=1.5, linestyle="--", label="Ímpar")
        ax.axvline(f0, color="k", linestyle=":", alpha=0.6, label=f"f₀={f0} Hz")
        ax.set_xlim(0, min(80, fs / 2))
        ax.set_title(f"{label} — Espectro de Magnitude", fontweight="bold")
        ax.set_xlabel("Frequência (Hz)")
        ax.set_ylabel("|H(f)| norm.")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    plt.show()


def plot_all_waves(
    t_sig: np.ndarray,
    x: np.ndarray,
    beats: list[BeatFeatures],
    fs: float,
    title: str = "Detecção de Ondas ECG",
):
    """
    Sobrepõe as ondas detectadas (P, Q, R, S, T) sobre o sinal ECG
    e marca os intervalos com barras de erro para o 3º batimento central.
    """
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(t_sig, x, color="#555", lw=0.9, alpha=0.85, label="ECG (MLII)")

    # Cores por onda
    wave_cfg = {
        "P": ("tab:green",  "^", 8,  "Onda P"),
        "Q": ("tab:purple", "v", 8,  "Onda Q"),
        "R": ("tab:red",    "*", 11, "Pico R"),
        "S": ("tab:orange", "v", 8,  "Onda S"),
        "T": ("tab:blue",   "^", 8,  "Onda T"),
    }

    plotted = set()
    for b in beats:
        for wname, (color, marker, size, wlabel) in wave_cfg.items():
            wp: Optional[WavePoint] = getattr(b, wname)
            if wp is None:
                continue
            lbl = wlabel if wname not in plotted else None
            ax.scatter(wp.time_s, wp.amplitude, marker=marker,
                       color=color, s=size ** 2, zorder=5,
                       label=lbl, edgecolors="white", linewidths=0.5)
            plotted.add(wname)

    # Ilustra erros para o 3º batimento (central na janela de 10s)
    b_demo = beats[2] if len(beats) > 2 else beats[0]
    y_err_base = np.min(x) * 1.15
    bar_kwargs = dict(capsize=5, lw=1.5, fmt="none")

    interval_demo = [
        (b_demo.P, b_demo.R,  b_demo.PR_err,  "PR",  "tab:green"),
        (b_demo.Q, b_demo.S,  b_demo.QRS_err, "QRS", "tab:purple"),
        (b_demo.S, b_demo.T,  b_demo.ST_err,  "ST",  "tab:orange"),
        (b_demo.Q, b_demo.T,  b_demo.QT_err,  "QT",  "tab:blue"),
    ]

    y_offsets = np.linspace(y_err_base, y_err_base * 1.55, len(interval_demo))

    for (wa, wb, err_ms, name, color), y_off in zip(interval_demo, y_offsets):
        if wa is None or wb is None or err_ms is None:
            continue
        t_a, t_b = wa.time_s, wb.time_s
        err_s = err_ms / 1000.0
        t_mid = (t_a + t_b) / 2

        ax.annotate("", xy=(t_b, y_off), xytext=(t_a, y_off),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.5))
        ax.errorbar([t_a, t_b], [y_off, y_off], xerr=err_s,
                    color=color, **bar_kwargs)
        ax.text(t_mid, y_off * 1.02, name, color=color,
                ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Amplitude (mV)")
    ax.set_xlim(t_sig[0], t_sig[-1])
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9, ncol=3)
    fig.tight_layout()
    plt.show()


def plot_interval_timeseries(
    beats: list[BeatFeatures],
    title: str = "Evolução dos Intervalos ECG",
):
    """
    Série temporal de RR, PR, QRS, ST e QT com banda de erro ±1σ.
    Traça também as faixas de referência clínica.
    """
    df = beats_to_dataframe(beats)

    intervals = [
        ("RR (ms)",  "±RR (ms)",  "tab:blue",   CLINICAL_RANGES["RR_ms"]),
        ("PR (ms)",  "±PR (ms)",  "tab:green",  CLINICAL_RANGES["PR_ms"]),
        ("QRS (ms)", "±QRS (ms)", "tab:purple", CLINICAL_RANGES["QRS_ms"]),
        ("ST (ms)",  "±ST (ms)",  "tab:orange", CLINICAL_RANGES["ST_ms"]),
        ("QT (ms)",  "±QT (ms)",  "tab:red",    CLINICAL_RANGES["QT_ms"]),
    ]

    fig, axes = plt.subplots(len(intervals), 1,
                             figsize=(12, 14), sharex=True)
    fig.suptitle(title, fontweight="bold", fontsize=13)

    x_idx = df["Batimento"].values

    for ax, (col, err_col, color, (ref_lo, ref_hi)) in zip(axes, intervals):
        vals = df[col].values.astype(float)
        errs = df[err_col].values.astype(float)

        ax.plot(x_idx, vals, color=color, lw=1.5, marker="o",
                markersize=4, label=col)
        ax.fill_between(x_idx, vals - errs, vals + errs,
                        alpha=0.2, color=color, label="±1σ erro")

        ax.axhspan(ref_lo, ref_hi, alpha=0.08, color="gray",
                   label=f"Ref normal ({ref_lo:.0f}–{ref_hi:.0f} ms)")
        ax.axhline(ref_lo, color="gray", linestyle="--", alpha=0.5, lw=1)
        ax.axhline(ref_hi, color="gray", linestyle="--", alpha=0.5, lw=1)

        ax.set_ylabel(col)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Índice do Batimento")
    fig.tight_layout()
    plt.show()


def plot_gabor_responses_ecg(
    t_sig: np.ndarray,
    x: np.ndarray,
    fs: float,
    ann_samples: np.ndarray,
):
    """
    Painel mostrando as respostas Gabor par, ímpar e energia para QRS, P e T
    sobrepostas ao sinal — útil para depurar a qualidade da detecção.
    """
    configs = [
        ("QRS",   QRS_F0, QRS_SIGMA, "tab:blue"),
        ("Onda P", P_F0,  P_SIGMA,   "tab:green"),
        ("Onda T", T_F0,  T_SIGMA,   "tab:red"),
    ]

    fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True)
    fig.suptitle("Respostas Gabor sobre o Sinal ECG", fontweight="bold")

    ax_ecg = axes[0]
    ax_ecg.plot(t_sig, x, color="#555", lw=0.9, label="ECG bruto")
    ax_ecg.scatter(ann_samples / fs,
                   np.full(len(ann_samples), np.max(x) * 1.05),
                   marker="v", color="tab:red", s=25, label="Picos R ref.")
    ax_ecg.set_ylabel("mV")
    ax_ecg.set_title("Sinal ECG Original")
    ax_ecg.legend(fontsize=9)
    ax_ecg.grid(True, alpha=0.25)

    for ax, (label, f0, sigma, color) in zip(axes[1:], configs):
        r_even, r_odd, energy = gabor_energy(x, fs, f0, sigma)

        energy_norm = energy / np.max(energy)
        ax.plot(t_sig, r_even, color=color, lw=0.9, alpha=0.7,
                label=f"{label} — Par (φ=0)")
        ax.plot(t_sig, r_odd,  color=color, lw=0.9, alpha=0.4,
                linestyle="--", label=f"{label} — Ímpar (φ=π/2)")
        ax.plot(t_sig, energy_norm * np.max(np.abs(r_even)),
                color="black", lw=1.3, label=f"{label} — Energia")

        for s in ann_samples:
            ax.axvline(s / fs, color="tab:red", alpha=0.25, lw=0.8)

        ax.set_ylabel("Resp. norm.")
        ax.set_title(f"Filtro Gabor — {label}  (f₀={f0} Hz, σ={sigma} s)")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("Tempo (s)")
    fig.tight_layout()
    plt.show()
