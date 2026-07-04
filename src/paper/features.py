"""Extracao de features por batimento para o paper."""

from __future__ import annotations

import numpy as np
from scipy import signal

from src.preprocessing.gabor_filters import gabor_energy
from src.preprocessing.metrics import band_power

PHYSIO_WINDOWS_S = {
    "p": (-0.22, -0.08),
    "qrs": (-0.06, 0.08),
    "t": (0.12, 0.36),
}

GABOR_WAVE_FREQUENCIES_HZ = {
    "p": (7.0, 15.0, 25.0),
    "qrs": (10.0, 15.0, 20.0),
    "t": (3.0, 5.0, 7.0),
}
GABOR_BANK_HZ = tuple(
    f0 for frequencies in GABOR_WAVE_FREQUENCIES_HZ.values() for f0 in frequencies
)
GABOR_N_CYCLES = 3.0


def _anchor_index(beat: np.ndarray, r_index: int | None) -> int:
    if r_index is None:
        return beat.size // 2
    return int(np.clip(r_index, 0, beat.size - 1))


def _safe_segment(
    beat: np.ndarray,
    fs: float,
    start_s: float,
    end_s: float,
    *,
    r_index: int | None = None,
) -> np.ndarray:
    anchor = _anchor_index(beat, r_index)
    lo = max(0, anchor + int(round(start_s * fs)))
    hi = min(beat.size, anchor + int(round(end_s * fs)))
    if hi <= lo:
        return np.asarray([], dtype=float)
    return beat[lo:hi]


def _safe_stats(prefix: str, values: np.ndarray, fs: float) -> dict[str, float]:
    if values.size == 0:
        return {
            f"{prefix}_mean": np.nan,
            f"{prefix}_std": np.nan,
            f"{prefix}_energy": np.nan,
            f"{prefix}_abs_area": np.nan,
            f"{prefix}_max_abs": np.nan,
        }
    return {
        f"{prefix}_mean": float(np.mean(values)),
        f"{prefix}_std": float(np.std(values)),
        f"{prefix}_energy": float(np.sum(values**2)),
        f"{prefix}_abs_area": float(np.sum(np.abs(values)) / fs),
        f"{prefix}_max_abs": float(np.max(np.abs(values))),
    }


def morphology_features(
    beat: np.ndarray,
    fs: float,
    *,
    r_index: int | None = None,
) -> dict[str, float]:
    """Features simples no dominio do tempo."""
    x = np.asarray(beat, dtype=float)
    if x.size == 0:
        raise ValueError("Janela de batimento vazia.")
    anchor = _anchor_index(x, r_index)
    diff = np.diff(x)
    features = {
        "r_amp": float(x[anchor]),
        "beat_max": float(np.max(x)),
        "beat_min": float(np.min(x)),
        "beat_peak_to_peak": float(np.ptp(x)),
        "beat_mean": float(np.mean(x)),
        "beat_median": float(np.median(x)),
        "beat_std": float(np.std(x)),
        "beat_rms": float(np.sqrt(np.mean(x**2))),
        "beat_energy": float(np.sum(x**2)),
        "beat_abs_area": float(np.sum(np.abs(x)) / fs),
        "max_slope": float(np.max(diff) * fs) if diff.size else 0.0,
        "max_abs_slope": float(np.max(np.abs(diff)) * fs) if diff.size else 0.0,
    }
    for name, (start_s, end_s) in PHYSIO_WINDOWS_S.items():
        segment = _safe_segment(x, fs, start_s, end_s, r_index=anchor)
        features.update(_safe_stats(f"{name}_window", segment, fs))
    return features


def rr_features(rr_prev_s: float | None, rr_next_s: float | None) -> dict[str, float]:
    """Features de ritmo local."""
    prev = np.nan if rr_prev_s is None else float(rr_prev_s)
    nxt = np.nan if rr_next_s is None else float(rr_next_s)
    ratio = np.nan if not np.isfinite(prev) or not np.isfinite(nxt) or nxt == 0 else prev / nxt
    return {"rr_prev_s": prev, "rr_next_s": nxt, "rr_ratio": ratio}


def spectral_features(beat: np.ndarray, fs: float) -> dict[str, float]:
    """Descritores espectrais compactos de uma janela de batimento."""
    x = np.asarray(beat, dtype=float)
    nperseg = min(len(x), 256)
    freqs, pxx = signal.welch(x, fs=fs, nperseg=nperseg)
    total = float(np.trapezoid(pxx, freqs))
    power_sum = float(np.sum(pxx))
    if total <= 1e-20:
        centroid = 0.0
        bandwidth = 0.0
        dominant = 0.0
        entropy = 0.0
    else:
        weights = pxx / np.sum(pxx)
        centroid = float(np.sum(freqs * weights))
        bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * weights)))
        dominant = float(freqs[int(np.argmax(pxx))])
        prob = pxx / max(power_sum, 1e-20)
        entropy = float(-np.sum(prob * np.log2(prob + 1e-20)) / np.log2(len(prob)))
    bands = {
        "band_power_0p5_4": band_power(x, fs, 0.5, 4.0, nperseg=nperseg),
        "band_power_4_8": band_power(x, fs, 4.0, 8.0, nperseg=nperseg),
        "band_power_8_20": band_power(x, fs, 8.0, 20.0, nperseg=nperseg),
        "band_power_20_40": band_power(x, fs, 20.0, 40.0, nperseg=nperseg),
    }
    stft_nperseg = min(len(x), max(32, int(round(0.16 * fs))))
    noverlap = min(stft_nperseg - 1, int(round(0.75 * stft_nperseg)))
    _, _, zxx = signal.stft(
        x,
        fs=fs,
        window="hann",
        nperseg=stft_nperseg,
        noverlap=noverlap,
        boundary=None,
        padded=False,
    )
    mag = np.abs(zxx)
    features = {
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "spectral_dominant_hz": dominant,
        "spectral_entropy": entropy,
        "total_power_0_40": band_power(x, fs, 0.0, 40.0, nperseg=nperseg),
        "stft_mean_magnitude": float(np.mean(mag)) if mag.size else 0.0,
        "stft_std_magnitude": float(np.std(mag)) if mag.size else 0.0,
        "stft_max_magnitude": float(np.max(mag)) if mag.size else 0.0,
        "stft_energy": float(np.sum(mag**2)) if mag.size else 0.0,
    }
    total_0_40 = max(features["total_power_0_40"], 1e-20)
    features.update(bands)
    for key, value in bands.items():
        features[f"rel_{key}"] = float(value / total_0_40)
    return features


def _window_response_stats(
    values: np.ndarray,
    fs: float,
    start_s: float,
    end_s: float,
    *,
    r_index: int | None = None,
) -> dict[str, float]:
    anchor = _anchor_index(values, r_index)
    lo = max(0, anchor + int(round(start_s * fs)))
    hi = min(values.size, anchor + int(round(end_s * fs)))
    if hi <= lo:
        return {"energy": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "peak_offset_ms": 0.0}
    segment = np.asarray(values[lo:hi], dtype=float)
    local_max_idx = lo + int(np.argmax(np.abs(segment)))
    return {
        "energy": float(np.sum(segment**2)),
        "max": float(np.max(np.abs(segment))),
        "mean": float(np.mean(np.abs(segment))),
        "std": float(np.std(segment)),
        "peak_offset_ms": float((local_max_idx - anchor) / fs * 1000.0),
    }


def gabor_features(
    beat: np.ndarray,
    fs: float,
    *,
    wave_frequencies_hz: dict[str, tuple[float, ...]] | None = None,
    n_cycles: float = GABOR_N_CYCLES,
    r_index: int | None = None,
) -> dict[str, float]:
    """Features baseadas em respostas Gabor nas janelas P, QRS e T."""
    x = np.asarray(beat, dtype=float)
    anchor = _anchor_index(x, r_index)
    features: dict[str, float] = {}
    window_energy_totals = {name: 0.0 for name in PHYSIO_WINDOWS_S}
    configs = wave_frequencies_hz or GABOR_WAVE_FREQUENCIES_HZ
    for window_name, frequencies in configs.items():
        start_s, end_s = PHYSIO_WINDOWS_S[window_name]
        for f0 in frequencies:
            response = np.sqrt(gabor_energy(x, f0, fs, n_cycles=n_cycles))
            f_slug = str(f0).replace(".", "p")
            stats = _window_response_stats(response, fs, start_s, end_s, r_index=anchor)
            window_energy_totals[window_name] += stats["energy"]
            for stat_name, value in stats.items():
                features[f"gabor_{window_name}_{f_slug}hz_{stat_name}"] = value
    qrs_total = max(window_energy_totals["qrs"], 1e-20)
    features["gabor_p_to_qrs_energy_ratio"] = float(window_energy_totals["p"] / qrs_total)
    features["gabor_t_to_qrs_energy_ratio"] = float(window_energy_totals["t"] / qrs_total)
    features["gabor_total_window_energy"] = float(sum(window_energy_totals.values()))
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
