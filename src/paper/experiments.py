"""Rotinas de avaliacao para as ablacões do paper."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.paper.constants import DETECTOR_NAMES
from src.paper.models import anomaly_scores, binary_predictions, build_detector


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Seleciona colunas numericas de features, excluindo metadados comuns."""
    excluded = {
        "beat_id",
        "record",
        "split",
        "sample",
        "time_s",
        "ann_symbol",
        "label_binary",
        "stage",
        "stage_label",
        "channel",
        "fs_hz",
        "start_sample",
        "end_sample",
        "r_index",
    }
    return [
        col
        for col in frame.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(frame[col])
    ]


def prepare_feature_matrix(
    frame: pd.DataFrame,
    cols: list[str],
    fill_values: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Seleciona, limpa infinitos e imputa NaN por mediana do treino."""
    x = frame[cols].replace([np.inf, -np.inf], np.nan)
    if fill_values is None:
        fill_values = x.median(numeric_only=True).fillna(0.0)
    return x.fillna(fill_values), fill_values


def fit_detector(
    train: pd.DataFrame,
    detector_name: str,
    *,
    label_col: str = "label_binary",
):
    """Ajusta modelo supervisionado ou one-class conforme o protocolo."""
    cols = feature_columns(train)
    x_train, fill_values = prepare_feature_matrix(train, cols)
    detector = build_detector(detector_name)
    if detector_name == "one_class_svm":
        detector.fit(x_train.loc[train[label_col] == 0])
    else:
        y_train = train[label_col].astype(int).to_numpy()
        detector.fit(x_train, y_train)
    return detector, cols, fill_values


def score_detector(
    detector,
    detector_name: str,
    frame: pd.DataFrame,
    cols: list[str],
    fill_values: pd.Series,
    *,
    label_col: str = "label_binary",
) -> pd.DataFrame:
    """Retorna scores e predicoes alinhados ao dataframe de entrada."""
    x_eval, _ = prepare_feature_matrix(frame, cols, fill_values)
    scores = anomaly_scores(detector, x_eval, detector_name)
    y_pred = binary_predictions(detector, x_eval, detector_name)
    out = frame[
        ["beat_id", "record", "split", "sample", "time_s", "ann_symbol", label_col]
    ].copy()
    out = out.rename(columns={label_col: "y_true"})
    out["score_anomaly"] = scores
    out["y_pred"] = y_pred
    return out


def summarize_scored_predictions(scored: pd.DataFrame) -> dict[str, object]:
    """Calcula metricas a partir de scores ja computados."""
    y_true = scored["y_true"].astype(int).to_numpy()
    scores = scored["score_anomaly"].to_numpy()
    y_pred = scored["y_pred"].astype(int).to_numpy()
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "pr_auc": float(average_precision_score(y_true, scores)),
        "roc_auc": float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else np.nan,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }


def evaluate_detector(
    detector,
    detector_name: str,
    test: pd.DataFrame,
    cols: list[str],
    fill_values: pd.Series,
    *,
    label_col: str = "label_binary",
) -> dict[str, object]:
    """Calcula metricas para um detector ja ajustado."""
    scored = score_detector(
        detector,
        detector_name,
        test,
        cols,
        fill_values,
        label_col=label_col,
    )
    return summarize_scored_predictions(scored)


def run_detector_benchmark(
    train: pd.DataFrame,
    test: pd.DataFrame,
    detector_names: tuple[str, ...] = DETECTOR_NAMES,
) -> pd.DataFrame:
    """Executa benchmark simples para uma tabela de uma ablação."""
    rows = []
    for name in detector_names:
        detector, cols, fill_values = fit_detector(train, name)
        metrics = evaluate_detector(detector, name, test, cols, fill_values)
        metrics.pop("confusion_matrix")
        rows.append({"detector": name, "n_features": len(cols), **metrics})
    return pd.DataFrame(rows)
