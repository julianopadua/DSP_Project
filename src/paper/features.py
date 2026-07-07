"""Extracao de features por batimento para o paper."""

from __future__ import annotations

import numpy as np
from scipy import signal

from src.preprocessing.metrics import band_power

GABOR_BANK = {
    "p": {
        "f0_hz": 8.0,
        "sigma_s": 0.110,
        "component": "even",
        "window_s": (-0.28, -0.07),
        "label": "P 8 Hz",
        "color": "#1f77b4",
    },
    "qrs": {
        "f0_hz": 15.0,
        "sigma_s": 0.020,
        "component": "magnitude",
        "window_s": (-0.07, 0.07),
        "label": "QRS 15 Hz",
        "color": "#2ca02c",
    },
    "t": {
        "f0_hz": 6.0,
        "sigma_s": 0.110,
        "component": "even",
        "window_s": (0.18, 0.45),
        "label": "T 6 Hz",
        "color": "#d62728",
    },
}

PHYSIO_WINDOWS_S = {
    name: cfg["window_s"] for name, cfg in GABOR_BANK.items()
}


def _anchor_index(beat: np.ndarray, r_index: int | None) -> int:
    if r_index is None:
        return beat.size // 2
    return int(np.clip(r_index, 0, beat.size - 1))


def window_slice_by_seconds(
    values: np.ndarray,
    fs: float,
    start_s: float,
    end_s: float,
    *,
    center_index: int | None = None,
) -> np.ndarray:
    center = _anchor_index(values, center_index)
    lo = max(0, center + int(round(start_s * fs)))
    hi = min(values.size, center + int(round(end_s * fs)))
    if hi <= lo:
        return np.asarray([], dtype=float)
    return np.asarray(values[lo:hi], dtype=float)


def gabor_kernel_sigma(
    fs: float,
    f0_hz: float,
    sigma_s: float,
    *,
    phase: float = 0.0,
    n_sigma: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    half = int(np.ceil(n_sigma * sigma_s * fs))
    t = np.arange(-half, half + 1) / fs
    envelope = np.exp(-(t**2) / (2.0 * sigma_s**2))
    h = envelope * np.cos(2.0 * np.pi * f0_hz * t + phase)
    h = h - np.mean(h)
    norm = np.sqrt(np.sum(h**2))
    if norm > 0:
        h = h / norm
    return t, h


def gabor_component_response(
    x: np.ndarray,
    fs: float,
    f0_hz: float,
    sigma_s: float,
    component: str = "magnitude",
) -> np.ndarray:
    _, even_kernel = gabor_kernel_sigma(fs, f0_hz, sigma_s, phase=0.0)
    even = signal.fftconvolve(np.asarray(x, dtype=float), even_kernel, mode="same")
    if component == "even":
        return even
    _, odd_kernel = gabor_kernel_sigma(fs, f0_hz, sigma_s, phase=np.pi / 2.0)
    odd = signal.fftconvolve(np.asarray(x, dtype=float), odd_kernel, mode="same")
    if component == "odd":
        return odd
    if component == "magnitude":
        return np.sqrt(even**2 + odd**2)
    raise ValueError("component deve ser 'even', 'odd' ou 'magnitude'")


def morphology_features(
    beat: np.ndarray,
    fs: float,
    *,
    r_index: int | None = None,
) -> dict[str, float]:
    """Features morfologicas compactas alinhadas ao sinal filtrado."""
    x = np.asarray(beat, dtype=float)
    if x.size == 0:
        raise ValueError("Janela de batimento vazia.")
    anchor = _anchor_index(x, r_index)
    diff = np.diff(x)
    return {
        "r_amp": float(x[anchor]),
        "beat_peak_to_peak": float(np.ptp(x)),
        "beat_energy": float(np.sum(x**2)),
        "beat_abs_area": float(np.sum(np.abs(x)) / fs),
        "max_abs_slope": float(np.max(np.abs(diff)) * fs) if diff.size else 0.0,
        "beat_std": float(np.std(x)),
    }


def rr_features(rr_prev_s: float | None, rr_next_s: float | None) -> dict[str, float]:
    """Features de ritmo local."""
    prev = np.nan if rr_prev_s is None else float(rr_prev_s)
    nxt = np.nan if rr_next_s is None else float(rr_next_s)
    ratio = np.nan if not np.isfinite(prev) or not np.isfinite(nxt) or nxt == 0 else prev / nxt
    return {"rr_prev_s": prev, "rr_next_s": nxt, "rr_ratio": ratio}


def spectral_features(beat: np.ndarray, fs: float) -> dict[str, float]:
    """Descritores espectrais compactos da janela filtrada."""
    x = np.asarray(beat, dtype=float)
    nperseg = min(len(x), 256)
    freqs, pxx = signal.welch(x, fs=fs, nperseg=nperseg)
    power_sum = float(np.sum(pxx))
    if power_sum <= 1e-20:
        centroid = 0.0
        bandwidth = 0.0
    else:
        weights = pxx / power_sum
        centroid = float(np.sum(freqs * weights))
        bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * weights)))
    return {
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "band_power_8_20": band_power(x, fs, 8.0, 20.0, nperseg=nperseg),
        "band_power_20_40": band_power(x, fs, 20.0, 40.0, nperseg=nperseg),
    }


def gabor_features(
    beat: np.ndarray,
    fs: float,
    *,
    bank: dict[str, dict[str, float | str | tuple[float, float]]] | None = None,
    r_index: int | None = None,
) -> dict[str, float]:
    """Features Gabor reproduzindo o banco final escolhido no notebook."""
    x = np.asarray(beat, dtype=float)
    anchor = _anchor_index(x, r_index)
    features: dict[str, float] = {}
    configs = bank or GABOR_BANK
    for name, cfg in configs.items():
        response = gabor_component_response(
            x,
            fs,
            float(cfg["f0_hz"]),
            float(cfg["sigma_s"]),
            str(cfg["component"]),
        )
        start_s, end_s = cfg["window_s"]
        segment = window_slice_by_seconds(
            response,
            fs,
            float(start_s),
            float(end_s),
            center_index=anchor,
        )
        features[f"{name}_gabor_energy"] = float(np.sum(segment**2)) if segment.size else 0.0
        if name != "qrs":
            continue
        features["qrs_gabor_max"] = float(np.max(np.abs(segment))) if segment.size else 0.0
        if segment.size:
            lo = max(0, anchor + int(round(float(start_s) * fs)))
            peak_index = lo + int(np.argmax(np.abs(segment)))
            features["qrs_gabor_peak_offset_ms"] = float((peak_index - anchor) / fs * 1000.0)
        else:
            features["qrs_gabor_peak_offset_ms"] = 0.0
    return features


def extract_feature_groups(
    beat: np.ndarray,
    fs: float,
    feature_groups: tuple[str, ...],
    *,
    rr_prev_s: float | None = None,
    rr_next_s: float | None = None,
    r_index: int | None = None,
) -> dict[str, float]:
    """Extrai grupos de features na ordem definida pela ablação."""
    features: dict[str, float] = {}
    if "morphology" in feature_groups:
        features.update(morphology_features(beat, fs, r_index=r_index))
    if "rr" in feature_groups:
        features.update(rr_features(rr_prev_s, rr_next_s))
    if "spectral" in feature_groups:
        features.update(spectral_features(beat, fs))
    if "gabor" in feature_groups:
        features.update(gabor_features(beat, fs, r_index=r_index))
    return features
