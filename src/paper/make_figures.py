"""Gera figuras padronizadas para o manuscrito do paper."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, Rectangle
from sklearn.metrics import average_precision_score, precision_recall_curve

from src.config import PAPER_FIGURES_DIR, PAPER_PROCESSED_DIR, ensure_paper_dirs
from src.paper.constants import DETECTOR_NAMES
from src.paper.dataset import (
    full_beat_bounds,
    is_valid_beat_symbol,
    load_record_annotations,
    load_record_signal,
    selected_records,
    symbol_to_binary_label,
)
from src.paper.features import GABOR_BANK, PHYSIO_WINDOWS_S, gabor_component_response, gabor_kernel_sigma
from src.paper.preprocessing import denoise_fir_chain

logger = logging.getLogger(__name__)

COLORS = {
    "raw": "#7f7f7f",
    "filtered": "#1f77b4",
    "svm_supervised": "#0f4c81",
    "one_class_svm": "#c03d3d",
    "A1": "#1f77b4",
    "A2": "#2ca02c",
    "A3": "#d62728",
}

MODEL_LABELS = {
    "svm_supervised": "SVM supervisionada",
    "one_class_svm": "One-Class SVM",
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


def find_example_beat(label_binary: int = 0) -> tuple[str, int, str, np.ndarray, np.ndarray, float, int]:
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
            r_index = int(sample) - int(start)
            return record_id, int(sample), str(symbol), raw[start:end], filtered[start:end], fs, r_index
    raise RuntimeError(f"Nenhum batimento com label {label_binary} encontrado.")


def figure_raw_vs_filtered(output_dir: Path) -> Path:
    record_id, sample, symbol, raw, filtered, fs, r_index = find_example_beat(label_binary=0)
    t = (np.arange(len(raw)) - r_index) / fs
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    ax.plot(t, raw, color=COLORS["raw"], lw=0.9, alpha=0.8, label="bruto")
    ax.plot(t, filtered, color=COLORS["filtered"], lw=1.0, label="filtrado")
    ax.axvline(0, color="#d62728", lw=0.8, ls="--")
    ax.set_xlabel("Tempo relativo ao R-peak (s)")
    ax.set_ylabel("Amplitude (mV)")
    ax.set_title(
        f"Registro {record_id}, amostra {sample}, símbolo {symbol}",
        fontsize=8,
        loc="left",
    )
    ax.legend(frameon=False)
    ax.grid(alpha=0.22)
    return save_figure(fig, output_dir, "fig_raw_vs_filtered_beat.pdf")


def figure_gabor_filter_bank(output_dir: Path, fs: float = 360.0) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    offset = 0.0
    label_positions = {
        "t": (0.04, 0.80),
        "qrs": (0.18, 0.53),
        "p": (0.04, 0.24),
    }
    for wave_name, cfg in GABOR_BANK.items():
        t, kernel = gabor_kernel_sigma(fs, float(cfg["f0_hz"]), float(cfg["sigma_s"]))
        normalized = kernel / max(np.max(np.abs(kernel)), 1e-12)
        ax.plot(t * 1000.0, normalized + offset, lw=1.0, color=str(cfg["color"]))
        x_text, y_text = label_positions[wave_name]
        ax.text(
            x_text,
            y_text,
            str(cfg["label"]),
            color=str(cfg["color"]),
            ha="left",
            va="center",
            fontsize=8,
            transform=ax.transAxes,
        )
        offset += 1.4
    ax.set_xlabel("Tempo (ms)")
    ax.set_ylabel("Kernel normalizado")
    ax.set_yticks([])
    ax.grid(axis="x", alpha=0.2)
    ax.set_xlim(-210, 210)
    return save_figure(fig, output_dir, "fig_gabor_filter_bank.pdf")


def figure_gabor_response_examples(output_dir: Path) -> Path:
    normal = find_example_beat(label_binary=0)
    anomaly = find_example_beat(label_binary=1)
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True)
    for ax, (record_id, sample, symbol, _, filtered, fs, r_index), label in (
        (axes[0], normal, "normal"),
        (axes[1], anomaly, "anomalo"),
    ):
        t = (np.arange(len(filtered)) - r_index) / fs
        ax.plot(t, filtered, color="#202020", lw=0.9, label="ECG filtrado")
        for wave_name, cfg in GABOR_BANK.items():
            response = gabor_component_response(
                filtered,
                fs,
                float(cfg["f0_hz"]),
                float(cfg["sigma_s"]),
                str(cfg["component"]),
            )
            response = np.abs(response)
            response = response / max(np.max(response), 1e-12)
            response = response * 0.35 + np.min(filtered)
            ax.plot(
                t,
                response,
                lw=0.85,
                color=str(cfg["color"]),
                label=f"Gabor {cfg['label']}",
            )
        for start, end in PHYSIO_WINDOWS_S.values():
            ax.axvspan(start, end, color="#efefef", alpha=0.55)
        ax.axvline(0, color="#d62728", lw=0.8, ls="--")
        ax.set_ylabel("Amplitude")
        ax.set_title(
            f"Batimento {label} - registro {record_id}, amostra {sample}, símbolo {symbol}",
            fontsize=8,
            loc="left",
        )
        ax.grid(alpha=0.2)
    axes[1].set_xlabel("Tempo relativo ao R-peak (s)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.0))
    fig.subplots_adjust(top=0.84, hspace=0.32)
    return save_figure(fig, output_dir, "fig_gabor_response_examples.pdf")


def figure_pipeline(output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 1.55))
    ax.axis("off")
    boxes = [
        ("MIT-BIH\nMLII", 0.01),
        ("Filtro FIR\n0,5-40 Hz", 0.154),
        ("Segmentos\npor R-peak", 0.298),
        ("Split\nDS1/DS2", 0.442),
        ("18 features\nfiltradas", 0.586),
        ("SVM sup.\nOC-SVM", 0.730),
        ("PR-AUC\nF1/MC", 0.874),
    ]
    box_w = 0.108
    box_h = 0.52
    y = 0.28
    for text, x in boxes:
        rect = Rectangle((x, y), box_w, box_h, linewidth=0.9, edgecolor="#303030", facecolor="#f7f7f7")
        ax.add_patch(rect)
        ax.text(x + box_w / 2, y + box_h / 2, text, ha="center", va="center", fontsize=7.4)
    for (_, x0), (_, x1) in zip(boxes[:-1], boxes[1:], strict=False):
        start = (x0 + box_w + 0.006, y + box_h / 2)
        end = (x1 - 0.006, y + box_h / 2)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=10, lw=0.9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return save_figure(fig, output_dir, "fig_pipeline_ablation.pdf")


def figure_model_precision_recall(predictions: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    subset = predictions[predictions["stage"] == "A3"].copy()
    for detector in DETECTOR_NAMES:
        detector_rows = subset[subset["detector"] == detector]
        if detector_rows.empty:
            continue
        y_true = detector_rows["y_true"].astype(int).to_numpy()
        scores = detector_rows["score_anomaly"].to_numpy()
        precision, recall, _ = precision_recall_curve(y_true, scores)
        ap = average_precision_score(y_true, scores)
        ax.plot(
            recall,
            precision,
            lw=1.6,
            color=COLORS.get(detector),
            label=f"{MODEL_LABELS.get(detector, detector)} ({ap:.3f})",
        )
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, loc="upper right")
    return save_figure(fig, output_dir, "fig_model_precision_recall.pdf")


def figure_confusion_matrices(confusion: pd.DataFrame, output_dir: Path) -> Path:
    final_rows = confusion[confusion["stage"] == "A3"].copy()
    fig, axes = plt.subplots(1, len(DETECTOR_NAMES), figsize=(6.4, 2.45), sharey=True)
    axes = np.atleast_1d(axes)
    cmap = LinearSegmentedColormap.from_list("confusion_blue", ["#f6fbff", "#c7ddf0", "#0f4c81"])
    cell_labels = np.array([["TN", "FP"], ["FN", "TP"]])
    for ax, detector in zip(axes, DETECTOR_NAMES, strict=False):
        row = final_rows[final_rows["detector"] == detector]
        if row.empty:
            ax.axis("off")
            continue
        row = row.iloc[0]
        matrix = np.array([[int(row["tn"]), int(row["fp"])], [int(row["fn"]), int(row["tp"])]], dtype=int)
        row_totals = matrix.sum(axis=1, keepdims=True)
        normalized = np.divide(matrix, row_totals, out=np.zeros_like(matrix, dtype=float), where=row_totals != 0)
        ax.imshow(normalized, cmap=cmap, vmin=0.0, vmax=1.0)
        for (i, j), value in np.ndenumerate(matrix):
            pct = normalized[i, j] * 100.0
            color = "white" if normalized[i, j] >= 0.58 else "#1d2733"
            ax.text(
                j,
                i,
                f"{cell_labels[i, j]}\n{value:,}".replace(",", ".") + f"\n{pct:.1f}%".replace(".", ","),
                ha="center",
                va="center",
                color=color,
                fontsize=8.4,
                linespacing=1.25,
                fontweight="semibold",
            )
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["normal", "anômalo"], fontsize=8)
        ax.set_yticklabels(["normal", "anômalo"], fontsize=8)
        ax.set_xlabel("Predito", labelpad=5)
        ax.set_title(MODEL_LABELS.get(detector, detector), fontsize=9, pad=8)
        if ax is axes[0]:
            ax.set_ylabel("Real", labelpad=6)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks(np.arange(-0.5, 2, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 2, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.6)
        ax.tick_params(which="minor", bottom=False, left=False)
    fig.subplots_adjust(wspace=0.34, left=0.08, right=0.98, bottom=0.20, top=0.84)
    return save_figure(fig, output_dir, "fig_confusion_matrices.pdf")


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
        predictions_path = args.processed_dir / "predictions_ablation.csv"
        confusion_path = args.processed_dir / "confusion_matrices.csv"
        if predictions_path.is_file():
            figure_model_precision_recall(pd.read_csv(predictions_path), args.output_dir)
        else:
            logger.warning("Predicoes ausentes, pulando curva PR final.")
        if confusion_path.is_file():
            figure_confusion_matrices(pd.read_csv(confusion_path), args.output_dir)
        else:
            logger.warning("Matrizes de confusao ausentes, pulando heatmaps.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha ao gerar figuras: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
