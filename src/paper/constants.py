"""Constantes do protocolo experimental do paper."""

from __future__ import annotations

from dataclasses import dataclass

NORMAL_SYMBOL = "N"

# Simbolos de batimento do padrao WFDB/MIT-BIH usados como exemplos avaliaveis.
# No protocolo v1, batimentos paced "/" e fusoes paced "f" ficam fora da
# avaliacao para evitar que o problema vire deteccao de marcapasso.
VALID_BEAT_SYMBOLS = frozenset(
    {"N", "L", "R", "B", "A", "a", "J", "S", "V", "r", "F", "e", "j", "n", "E", "Q"}
)

PACED_HEAVY_RECORDS = frozenset({"102", "104", "107", "217"})

# Split inter-paciente popular em trabalhos derivados de de Chazal/AAMI.
DS1_RECORDS = (
    "101", "106", "108", "109", "112", "114", "115", "116", "118", "119", "122",
    "124", "201", "203", "205", "207", "208", "209", "215", "220", "223", "230",
)

DS2_RECORDS = (
    "100", "103", "105", "111", "113", "117", "121", "123", "200", "202", "210",
    "212", "213", "214", "219", "221", "222", "228", "231", "232", "233", "234",
)


@dataclass(frozen=True)
class AblationStage:
    """Definicao compacta de um estagio cumulativo de features."""

    key: str
    label: str
    signal_variant: str
    feature_groups: tuple[str, ...]


ABLATION_STAGES = (
    AblationStage("A0", "raw", "raw", ("morphology", "rr")),
    AblationStage("A1", "filtered", "filtered", ("morphology", "rr")),
    AblationStage("A2", "spectral", "filtered", ("morphology", "rr", "spectral")),
    AblationStage("A3", "gabor", "filtered", ("morphology", "rr", "spectral", "gabor")),
)

DETECTOR_CONFIGS = {
    "one_class_svm": {"nu": 0.05, "kernel": "rbf", "gamma": "scale"},
    "isolation_forest": {
        "n_estimators": 300,
        "contamination": 0.05,
        "random_state": 42,
        "n_jobs": -1,
    },
    "lof": {"novelty": True, "n_neighbors": 35, "contamination": 0.05, "n_jobs": -1},
}

STAGE_KEYS = tuple(stage.key for stage in ABLATION_STAGES)
DETECTOR_NAMES = tuple(DETECTOR_CONFIGS)
