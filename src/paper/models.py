"""Modelos usados no benchmark do paper."""

from __future__ import annotations

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM, SVC

from src.paper.constants import DETECTOR_CONFIGS


def build_detector(name: str) -> Pipeline:
    """Cria modelo pelo nome canonico do protocolo."""
    if name == "svm_supervised":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", SVC(**DETECTOR_CONFIGS[name])),
            ]
        )
    if name == "one_class_svm":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", OneClassSVM(**DETECTOR_CONFIGS[name])),
            ]
        )
    raise ValueError(f"Detector desconhecido: {name!r}")


def anomaly_scores(detector, x, name: str):
    """Retorna escores orientados: maior valor = mais anomalo."""
    if name == "svm_supervised":
        if hasattr(detector, "predict_proba"):
            return detector.predict_proba(x)[:, 1]
        if hasattr(detector, "decision_function"):
            return detector.decision_function(x)
        raise TypeError("SVM supervisionada precisa expor predict_proba ou decision_function.")
    if name == "one_class_svm":
        if not hasattr(detector, "decision_function"):
            raise TypeError("One-Class SVM precisa expor decision_function.")
        return -detector.decision_function(x)
    raise ValueError(f"Modelo desconhecido: {name!r}")


def binary_predictions(detector, x, name: str):
    """Retorna predicoes binarias alinhadas ao protocolo 0=normal, 1=anomalo."""
    pred = detector.predict(x)
    if name == "svm_supervised":
        return pred.astype(int)
    if name == "one_class_svm":
        return (pred == -1).astype(int)
    raise ValueError(f"Modelo desconhecido: {name!r}")
