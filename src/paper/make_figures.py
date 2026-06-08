"""Gera figuras padronizadas para o manuscrito do paper."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle
from sklearn.metrics import average_precision_score, precision_recall_curve

from src.config import PAPER_FIGURES_DIR, PAPER_PROCESSED_DIR, ensure_paper_dirs
from src.paper.constants import ABLATION_STAGES, DETECTOR_NAMES
from src.paper.dataset import (
    full_beat_bounds,
    is_valid_beat_symbol,
    load_record_annotations,
    load_record_signal,
    selected_records,
    symbol_to_binary_label,
)
from src.paper.features import GABOR_BANK_HZ, PHYSIO_WINDOWS_S
from src.paper.preprocessing import denoise_fir_chain
from src.preprocessing.gabor_filters import gabor_energy, gabor_kernel

logger = logging.getLogger(__name__)

COLORS = {
    "raw": "#7f7f7f",
    "filtered": "#1f77b4",
    "one_class_svm": "#1f77b4",
    "isolation_forest": "#2ca02c",
    "lof": "#d62728",
    "A0": "#8c8c8c",
    "A1": "#1f77b4",
    "A2": "#2ca02c",
    "A3": "#d62728",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 300,
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(fig: plt.Figure, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura salva: %s", path)
    return path


def synthetic_ecg(t: np.ndarray) -> np.ndarray:
    return (
        0.12 * np.exp(-((t + 0.18) / 0.035) ** 2)
        - 0.20 * np.exp(-((t + 0.035) / 0.012) ** 2)
        + 1.05 * np.exp(-(t / 0.014) ** 2)
        - 0.32 * np.exp(-((t - 0.035) / 0.016) ** 2)
        + 0.32 * np.exp(-((t - 0.26) / 0.08) ** 2)
    )


def figure_ecg_waves_schema(output_dir: Path) -> Path:
    t = np.linspace(-0.32, 0.48, 900)
    y = synthetic_ecg(t)
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    for name, (start, end) in PHYSIO_WINDOWS_S.items():
        ax.axvspan(start, end, color="#d9e8f5", alpha=0.6)
    ax.plot(t, y, color="#202020", lw=1.4)
    ax.axvline(0, color="#d62728", lw=1.0, ls="--")
    ax.text(0.018, 1.03, "R-peak", color="#d62728", va="bottom", ha="left")
    for label, x0, y0 in (("P", -0.18, 0.18), ("QRS", -0.038, 1.13), ("T", 0.26, 0.38)):
        ax.text(x0, y0, label, ha="center", va="bottom")
    ax.set_xlabel("Tempo relativo ao R-peak (s)")
    ax.set_ylabel("Amplitude normalizada")
    ax.set_xlim(t.min(), t.max())
    ax.set_ylim(-0.7, 1.25)
    ax.grid(alpha=0.2)
    return save_figure(fig, output_dir, "fig_ecg_waves_schema.pdf")


def find_example_beat(label_binary: int = 0) -> tuple[str, int, str, np.ndarray, np.ndarray, float]:
    for record_id in selected_records("test"):
        raw, fs, _ = load_record_signal(record_id)
        filtered = denoise_fir_chain(raw, fs)
        ann = load_record_annotations(record_id)
        for sample, symbol in zip(ann.sample, ann.symbol, strict=False):
            if not is_valid_beat_symbol(str(symbol)):
                continue
            if symbol_to_binary_label(str(symbol)) != label_binary:
                continue
            bounds = full_beat_bounds(int(sample), fs, len(raw))
            if bounds is None:
                continue
            start, end = bounds
            return record_id, int(sample), str(symbol), raw[start:end], filtered[start:end], fs
    raise RuntimeError(f"Nenhum batimento com label {label_binary} encontrado.")


def figure_raw_vs_filtered(output_dir: Path) -> Path:
    record_id, sample, symbol, raw, filtered, fs = find_example_beat(label_binary=0)
    t = (np.arange(len(raw)) - len(raw) // 2) / fs
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    ax.plot(t, raw, color=COLORS["raw"], lw=0.9, alpha=0.8, label="bruto")
    ax.plot(t, filtered, color=COLORS["filtered"], lw=1.0, label="filtrado")
    ax.axvline(0, color="#d62728", lw=0.8, ls="--")
    ax.set_xlabel("Tempo relativo ao R-peak (s)")
    ax.set_ylabel("Amplitude (mV)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.22)
    ax.text(
        0.99,
        0.04,
        f"registro {record_id}, amostra {sample}, símbolo {symbol}",
        ha="right",
        va="bottom",
        transform=ax.transAxes,
        fontsize=7,
    )
    return save_figure(fig, output_dir, "fig_raw_vs_filtered_beat.pdf")


def figure_gabor_filter_bank(output_dir: Path, fs: float = 360.0) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    offset = 0.0
    for f0 in GABOR_BANK_HZ:
        t, h_real, _ = gabor_kernel(f0, fs)
        normalized = h_real / max(np.max(np.abs(h_real)), 1e-12)
        ax.plot(t * 1000.0, normalized + offset, lw=1.0, label=f"{f0:g} Hz")
        offset += 1.35
    ax.set_xlabel("Tempo (ms)")
    ax.set_ylabel("Kernel normalizado")
    ax.set_yticks([])
    ax.legend(ncol=3, frameon=False, loc="upper right")
    ax.grid(axis="x", alpha=0.2)
    return save_figure(fig, output_dir, "fig_gabor_filter_bank.pdf")


def figure_gabor_response_examples(output_dir: Path) -> Path:
    normal = find_example_beat(label_binary=0)
    anomaly = find_example_beat(label_binary=1)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True)
    for ax, (record_id, sample, symbol, _, filtered, fs), label in (
        (axes[0], normal, "normal"),
        (axes[1], anomaly, "anomalo"),
    ):
        t = (np.arange(len(filtered)) - len(filtered) // 2) / fs
        ax.plot(t, filtered, color="#202020", lw=0.9, label="ECG filtrado")
        for f0, color in ((7.0, "#1f77b4"), (15.0, "#2ca02c"), (30.0, "#d62728")):
            response = np.sqrt(gabor_energy(filtered, f0, fs))
            response = response / max(np.max(response), 1e-12)
            response = response * 0.35 + np.min(filtered)
            ax.plot(t, response, lw=0.8, color=color, label=f"Gabor {f0:g} Hz")
        for start, end in PHYSIO_WINDOWS_S.values():
            ax.axvspan(start, end, color="#efefef", alpha=0.55)
        ax.axvline(0, color="#d62728", lw=0.8, ls="--")
        ax.set_ylabel("Amplitude")
        ax.text(
            0.99,
            0.08,
            f"{label} reg. {record_id}, amostra {sample}, símbolo {symbol}",
            ha="right",
            va="bottom",
            transform=ax.transAxes,
            fontsize=7,
        )
        ax.grid(alpha=0.2)
    axes[1].set_xlabel("Tempo relativo ao R-peak (s)")
    axes[0].legend(ncol=4, frameon=False, loc="upper left")
    return save_figure(fig, output_dir, "fig_gabor_response_examples.pdf")


def figure_pipeline(output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.axis("off")
    boxes = [
        ("MIT-BIH\nWFDB/MLII", 0.04, 0.58),
        ("Segmentação\npor R-peak", 0.22, 0.58),
        ("Split\ninter-paciente", 0.40, 0.58),
        ("A0 raw\nA1 filtered\nA2 spectral\nA3 gabor", 0.58, 0.58),
        ("OC-SVM\nIForest\nLOF", 0.78, 0.58),
        ("PR-AUC\nROC-AUC\nF1/CM", 0.78, 0.18),
    ]
    for text, x, y in boxes:
        rect = Rectangle((x, y), 0.14, 0.22, linewidth=0.9, edgecolor="#404040", facecolor="#f7f7f7")
        ax.add_patch(rect)
        ax.text(x + 0.07, y + 0.11, text, ha="center", va="center", fontsize=8)
    arrows = [
        ((0.18, 0.69), (0.22, 0.69)),
        ((0.36, 0.69), (0.40, 0.69)),
        ((0.54, 0.69), (0.58, 0.69)),
        ((0.72, 0.69), (0.78, 0.69)),
        ((0.85, 0.58), (0.85, 0.40)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=10, lw=0.9))
    return save_figure(fig, output_dir, "fig_pipeline_ablation.pdf")


def figure_pr_auc_ablation(metrics: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    stages = [stage.key for stage in ABLATION_STAGES]
    x = np.arange(len(stages))
    width = 0.24
    for i, detector in enumerate(DETECTOR_NAMES):
        values = []
        for stage in stages:
            row = metrics[(metrics["stage"] == stage) & (metrics["detector"] == detector)]
            values.append(float(row["pr_auc"].iloc[0]) if not row.empty else np.nan)
        ax.bar(
            x + (i - 1) * width,
            values,
            width=width,
            label=detector.replace("_", " "),
            color=COLORS.get(detector),
        )
    ax.set_xticks(x)
    ax.set_xticklabels(stages)
    ax.set_xlabel("Estágio de ablação")
    ax.set_ylabel("PR-AUC")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    ax.grid(axis="y", alpha=0.25)
    return save_figure(fig, output_dir, "fig_pr_auc_ablation.pdf")


def figure_precision_recall_curves(predictions: pd.DataFrame, output_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True)
    for ax, detector in zip(axes, DETECTOR_NAMES, strict=False):
        subset_detector = predictions[predictions["detector"] == detector]
        for stage in [stage.key for stage in ABLATION_STAGES]:
            subset = subset_detector[subset_detector["stage"] == stage]
            if subset.empty:
                continue
            y_true = subset["y_true"].astype(int).to_numpy()
            scores = subset["score_anomaly"].to_numpy()
            precision, recall, _ = precision_recall_curve(y_true, scores)
            ap = average_precision_score(y_true, scores)
            ax.plot(recall, precision, lw=1.0, color=COLORS.get(stage), label=f"{stage} ({ap:.2f})")
        ax.set_xlabel("Recall")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.25)
        ax.text(0.05, 0.08, detector.replace("_", " "), transform=ax.transAxes, fontsize=8)
    axes[0].set_ylabel("Precision")
    axes[-1].legend(frameon=False, fontsize=7, loc="lower left")
    return save_figure(fig, output_dir, "fig_precision_recall_curves.pdf")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera figuras do paper DSP/ECG.")
    parser.add_argument("--processed-dir", type=Path, default=PAPER_PROCESSED_DIR)
    parser.add_argument("--output-dir", type=Path, default=PAPER_FIGURES_DIR)
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_paper_dirs()
    configure_style()
    try:
        figure_ecg_waves_schema(args.output_dir)
        figure_raw_vs_filtered(args.output_dir)
        figure_gabor_filter_bank(args.output_dir)
        figure_gabor_response_examples(args.output_dir)
        figure_pipeline(args.output_dir)
        metrics_path = args.processed_dir / "metrics_ablation.csv"
        predictions_path = args.processed_dir / "predictions_ablation.csv"
        if metrics_path.is_file():
            figure_pr_auc_ablation(pd.read_csv(metrics_path), args.output_dir)
        else:
            logger.warning("Metricas ausentes, pulando PR-AUC por ablação.")
        if predictions_path.is_file():
            figure_precision_recall_curves(pd.read_csv(predictions_path), args.output_dir)
        else:
            logger.warning("Predicoes ausentes, pulando curvas PR.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha ao gerar figuras: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
