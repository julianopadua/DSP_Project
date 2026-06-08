"""Detectores de anomalia usados no benchmark do paper."""

from __future__ import annotations

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from src.paper.constants import DETECTOR_CONFIGS


def build_detector(name: str) -> Pipeline:
    """Cria detector pelo nome canonico do protocolo."""
    if name == "one_class_svm":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", OneClassSVM(**DETECTOR_CONFIGS[name])),
            ]
        )
    if name == "isolation_forest":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", IsolationForest(**DETECTOR_CONFIGS[name])),
            ]
        )
    if name == "lof":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LocalOutlierFactor(**DETECTOR_CONFIGS[name])),
            ]
        )
    raise ValueError(f"Detector desconhecido: {name!r}")


def anomaly_scores(detector, x):
    """Retorna escores orientados: maior valor = mais anomalo."""
    if not hasattr(detector, "decision_function"):
        raise TypeError("Detector precisa expor decision_function para pontuar novidades.")
    return -detector.decision_function(x)
