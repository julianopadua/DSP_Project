"""Entry point para treinar e avaliar os modelos do paper nas ablacoes filtradas."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from src.config import PAPER_PROCESSED_DIR, ensure_data_dirs
from src.paper.build_dataset import stage_filename
from src.paper.constants import ABLATION_STAGES, DETECTOR_NAMES
from src.paper.experiments import (
    fit_detector,
    score_detector,
    summarize_scored_predictions,
)

logger = logging.getLogger(__name__)


def load_stage_frames(input_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for stage in ABLATION_STAGES:
        path = input_dir / stage_filename(stage.key, stage.label)
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo de features ausente: {path}")
        frames[stage.key] = pd.read_csv(path)
    return frames


def assert_protocol_integrity(stage_frames: dict[str, pd.DataFrame]) -> None:
    train_records = set()
    test_records = set()
    expected_ids: list[str] | None = None
    for stage, frame in stage_frames.items():
        beat_ids = frame["beat_id"].astype(str).tolist()
        if expected_ids is None:
            expected_ids = beat_ids
        elif beat_ids != expected_ids:
            raise AssertionError(f"Batimentos desalinhados no estagio {stage}.")
        stage_train = set(frame.loc[frame["split"] == "train", "record"].astype(str))
        stage_test = set(frame.loc[frame["split"] == "test", "record"].astype(str))
        if stage_train & stage_test:
            raise AssertionError(f"Vazamento treino/teste no estagio {stage}.")
        train_records |= stage_train
        test_records |= stage_test
    if train_records & test_records:
        raise AssertionError("Ha registros compartilhados entre treino e teste.")


def maybe_subsample_train(
    train: pd.DataFrame,
    max_train_normals: int | None,
    random_state: int,
) -> pd.DataFrame:
    if max_train_normals is None:
        return train
    normals = train[train["label_binary"] == 0]
    anomalies = train[train["label_binary"] == 1]
    if len(normals) <= max_train_normals:
        return train
    sampled = normals.sample(n=max_train_normals, random_state=random_state)
    combined = pd.concat([sampled, anomalies], ignore_index=True)
    return combined.sort_values(["record", "sample"]).reset_index(drop=True)


def run_ablation(
    stage_frames: dict[str, pd.DataFrame],
    *,
    detector_names: tuple[str, ...] = DETECTOR_NAMES,
    max_train_normals: int | None = None,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, float | int | str]] = []
    confusion_rows: list[dict[str, float | int | str]] = []
    prediction_frames: list[pd.DataFrame] = []

    for stage in ABLATION_STAGES:
        frame = stage_frames[stage.key]
        train = frame[frame["split"] == "train"].copy()
        test = frame[frame["split"] == "test"].copy()
        n_train_normals_available = int((train["label_binary"] == 0).sum())
        n_test_anomalies = int((test["label_binary"] == 1).sum())
        if n_train_normals_available == 0:
            raise ValueError(f"Sem normais de treino em {stage.key}.")
        if n_test_anomalies == 0:
            raise ValueError(f"Sem anomalias de teste em {stage.key}.")

        train_for_fit = maybe_subsample_train(train, max_train_normals, random_state)
        n_train_normals_used = int((train_for_fit["label_binary"] == 0).sum())
        n_train_anomalies_used = int((train_for_fit["label_binary"] == 1).sum())
        logger.info(
            "%s: treino normal usado %d/%d, anomalias de treino %d, teste %d linhas",
            stage.key,
            n_train_normals_used,
            n_train_normals_available,
            n_train_anomalies_used,
            len(test),
        )

        for detector_name in detector_names:
            logger.info("Treinando %s em %s", detector_name, stage.key)
            fit_start = perf_counter()
            detector, cols, fill_values = fit_detector(train_for_fit, detector_name)
            fit_seconds = perf_counter() - fit_start
            score_start = perf_counter()
            scored = score_detector(detector, detector_name, test, cols, fill_values)
            score_seconds = perf_counter() - score_start
            metrics = summarize_scored_predictions(scored)
            cm = metrics.pop("confusion_matrix")
            metric_rows.append(
                {
                    "stage": stage.key,
                    "stage_label": stage.label,
                    "detector": detector_name,
                    "n_features": len(cols),
                    "n_train_normals_available": n_train_normals_available,
                    "n_train_normals_used": n_train_normals_used,
                    "n_train_anomalies_used": n_train_anomalies_used,
                    "n_test": int(len(test)),
                    "n_test_normals": int((test["label_binary"] == 0).sum()),
                    "n_test_anomalies": n_test_anomalies,
                    "fit_seconds": fit_seconds,
                    "score_seconds": score_seconds,
                    "score_ms_per_beat": 1000.0 * score_seconds / max(len(test), 1),
                    **metrics,
                }
            )
            confusion_rows.append(
                {
                    "stage": stage.key,
                    "stage_label": stage.label,
                    "detector": detector_name,
                    "tn": int(cm[0][0]),
                    "fp": int(cm[0][1]),
                    "fn": int(cm[1][0]),
                    "tp": int(cm[1][1]),
                }
            )
            scored.insert(0, "detector", detector_name)
            scored.insert(0, "stage_label", stage.label)
            scored.insert(0, "stage", stage.key)
            prediction_frames.append(scored)

    return (
        pd.DataFrame(metric_rows),
        pd.DataFrame(confusion_rows),
        pd.concat(prediction_frames, ignore_index=True),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o benchmark SVM supervisionada vs One-Class SVM para A1-A3.",
    )
    parser.add_argument("--input-dir", type=Path, default=PAPER_PROCESSED_DIR)
    parser.add_argument("--output-dir", type=Path, default=PAPER_PROCESSED_DIR)
    parser.add_argument(
        "--detectors",
        default=",".join(DETECTOR_NAMES),
        help="Modelos separados por virgula.",
    )
    parser.add_argument("--max-train-normals", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_data_dirs()
    detector_names = tuple(part.strip() for part in args.detectors.split(",") if part.strip())
    unknown = sorted(set(detector_names) - set(DETECTOR_NAMES))
    if unknown:
        logger.error("Detectores desconhecidos: %s", ", ".join(unknown))
        return 1

    try:
        frames = load_stage_frames(args.input_dir)
        assert_protocol_integrity(frames)
        metrics, confusion, predictions = run_ablation(
            frames,
            detector_names=detector_names,
            max_train_normals=args.max_train_normals,
            random_state=args.random_state,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        metrics.to_csv(args.output_dir / "metrics_ablation.csv", index=False)
        confusion.to_csv(args.output_dir / "confusion_matrices.csv", index=False)
        predictions.to_csv(args.output_dir / "predictions_ablation.csv", index=False)
        run_info = {
            "detectors": list(detector_names),
            "max_train_normals": args.max_train_normals,
            "random_state": args.random_state,
            "metric_rows": int(len(metrics)),
            "prediction_rows": int(len(predictions)),
        }
        (args.output_dir / "ablation_run_info.json").write_text(
            json.dumps(run_info, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha na ablação: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
