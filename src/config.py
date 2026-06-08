# src/config.py
"""Caminhos do projeto e estrutura de diretórios relativamente a este ficheiro."""

from __future__ import annotations

from pathlib import Path

# Raiz do repositório: diretório pai do pacote `src`.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

RAW_DATA_DIR: Path = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR: Path = PROJECT_ROOT / "data" / "processed"
PAPER_PROCESSED_DIR: Path = PROCESSED_DATA_DIR / "paper"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
PAPER_DIR: Path = DOCS_DIR / "paper"
PAPER_ARTICLE_DIR: Path = PAPER_DIR / "article"
PAPER_FIGURES_DIR: Path = PAPER_ARTICLE_DIR / "figures"
LLM_WIKI_DIR: Path = PROJECT_ROOT / "llm-wiki"
LLM_WIKI_RAW_DIR: Path = LLM_WIKI_DIR / "raw"


def ensure_data_dirs() -> None:
    """Cria os diretórios de dados brutos e processados, se ainda não existirem."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def ensure_paper_dirs() -> None:
    """Cria os diretórios de artefatos do paper, se ainda não existirem."""
    PAPER_ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    PAPER_FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def mitdb_record_dir() -> Path:
    """Devolve o diretório que contém os ficheiros WFDB do registo (por exemplo ``100.hea``).

    Após extrair o ZIP da PhysioNet, os ficheiros podem estar diretamente em
    ``RAW_DATA_DIR`` ou dentro de uma subpasta (por exemplo ``mitdb``).
    Esta função devolve o primeiro diretório que contém ``100.hea``, ou gera
    exceção se a base não estiver presente.

    Retorno
    -------
    pathlib.Path
        Caminho absoluto a utilizar como prefixo de caminho para os leitores
        ``wfdb`` (por exemplo ``wfdb.rdrecord((caminho / '100').as_posix())``).

    Exceções
    --------
    FileNotFoundError
        Se não forem encontrados ficheiros da MIT-BIH sob ``RAW_DATA_DIR``.
    """
    marker = RAW_DATA_DIR / "100.hea"
    if marker.is_file():
        return RAW_DATA_DIR
    if not RAW_DATA_DIR.is_dir():
        raise FileNotFoundError(
            f"Diretório de dados brutos inexistente: {RAW_DATA_DIR}. "
            "Execute src.data.download_dataset para obter e extrair a base."
        )
    for child in sorted(RAW_DATA_DIR.iterdir()):
        if child.is_dir() and (child / "100.hea").is_file():
            return child
    raise FileNotFoundError(
        f"Não foi possível localizar registos WFDB (esperado 100.hea) em {RAW_DATA_DIR}. "
        "Descarregue e extraia o ZIP MIT-BIH para a pasta de dados brutos."
    )
