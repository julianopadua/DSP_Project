"""Valida artefatos gerados pelo pipeline do paper."""

from __future__ import annotations

import logging
import sys

import pandas as pd

from src.config import PAPER_PROCESSED_DIR
from src.paper.build_dataset import stage_filename
from src.paper.constants import ABLATION_STAGES, DETECTOR_NAMES

logger = logging.getLogger(__name__)


def validate_stage_alignment() -> None:
    expected_ids: list[str] | None = None
    for stage in ABLATION_STAGES:
        path = PAPER_PROCESSED_DIR / stage_filename(stage.key, stage.label)
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path, usecols=["beat_id", "record", "split", "label_binary"])
        logger.info("%s possui %d linhas", stage.key, len(frame))
        current_ids = frame["beat_id"].astype(str).tolist()
        if expected_ids is None:
            expected_ids = current_ids
        elif current_ids != expected_ids:
            raise AssertionError(f"Batimentos desalinhados em {stage.key}.")


def validate_split_and_results() -> None:
    frame = pd.read_csv(
        PAPER_PROCESSED_DIR / stage_filename("A0", "raw"),
        usecols=["record", "split", "label_binary"],
    )
    train_records = set(frame.loc[frame["split"] == "train", "record"].astype(str))
    test_records = set(frame.loc[frame["split"] == "test", "record"].astype(str))
    overlap = train_records & test_records
    if overlap:
        raise AssertionError(f"Registros aparecem em treino e teste: {sorted(overlap)}")
    if int((frame["label_binary"] == 0).sum()) == 0:
        raise AssertionError("Sem batimentos normais no manifesto.")
    if int((frame["label_binary"] == 1).sum()) == 0:
        raise AssertionError("Sem batimentos anomalos no manifesto.")

    metrics_path = PAPER_PROCESSED_DIR / "metrics_ablation.csv"
    predictions_path = PAPER_PROCESSED_DIR / "predictions_ablation.csv"
    if not metrics_path.is_file():
        raise FileNotFoundError(metrics_path)
    if not predictions_path.is_file():
        raise FileNotFoundError(predictions_path)
    metrics = pd.read_csv(metrics_path)
    expected_rows = len(ABLATION_STAGES) * len(DETECTOR_NAMES)
    if len(metrics) != expected_rows:
        raise AssertionError(f"Esperadas {expected_rows} linhas de metricas, obtidas {len(metrics)}.")
    required = {"stage", "detector", "pr_auc", "roc_auc", "precision", "recall", "f1"}
    missing = required - set(metrics.columns)
    if missing:
        raise AssertionError(f"Metricas sem colunas obrigatorias: {sorted(missing)}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        validate_stage_alignment()
        validate_split_and_results()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Validacao falhou: %s", exc)
        return 1
    logger.info("Artefatos do paper validados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
