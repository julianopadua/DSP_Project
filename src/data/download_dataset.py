# src/data/download_dataset.py
"""Descarrega e extrai o arquivo ZIP da base MIT-BIH Arrhythmia (PhysioNet)."""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path
from typing import Final

import requests

from src.config import RAW_DATA_DIR, ensure_data_dirs

DEFAULT_DOWNLOAD_URL: Final[str] = (
    "https://physionet.org/content/mitdb/get-zip/1.0.0/"
)
DEFAULT_ZIP_NAME: Final[str] = "mitdb-1.0.0.zip"


def configure_logging(level: int = logging.INFO) -> None:
    """Configura o logging de raiz para execução em linha de comandos."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def download_zip(url: str, dest_path: Path, chunk_size: int = 1 << 20) -> Path:
    """Descarrega um ZIP remoto para ``dest_path`` (cria diretórios ascendentes).

    Parâmetros
    ----------
    url
        URL HTTP(S) do ficheiro ZIP.
    dest_path
        Caminho completo onde o ZIP será escrito.
    chunk_size
        Tamanho do bloco em fluxo contínuo, em bytes.

    Retorno
    -------
    pathlib.Path
        ``dest_path`` após descarregamento bem-sucedido.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.info("A descarregar %s", url)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total = response.headers.get("Content-Length")
        total_bytes = int(total) if total and total.isdigit() else None
        written = 0
        with dest_path.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                file_handle.write(chunk)
                written += len(chunk)
                if total_bytes and written % (10 * chunk_size) < chunk_size:
                    logger.info(
                        "Descarregados %s / %s bytes",
                        written,
                        total_bytes,
                    )
    logger.info("Descarregamento concluído: %s bytes -> %s", written, dest_path)
    return dest_path


def extract_zip(zip_path: Path, extract_to: Path) -> None:
    """Extrai todos os membros de ``zip_path`` para ``extract_to``."""
    logger = logging.getLogger(__name__)
    logger.info("A extrair %s -> %s", zip_path, extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.namelist()
        logger.info("O arquivo contém %s entradas", len(members))
        archive.extractall(extract_to)
    logger.info("Extração concluída")


def cleanup_zip(zip_path: Path) -> None:
    """Remove o ficheiro ZIP em ``zip_path``, se existir."""
    logger = logging.getLogger(__name__)
    if zip_path.is_file():
        zip_path.unlink()
        logger.info("ZIP removido: %s", zip_path)
    else:
        logger.warning("ZIP não encontrado para remoção: %s", zip_path)


def run_download_pipeline(
    url: str = DEFAULT_DOWNLOAD_URL,
    raw_dir: Path | None = None,
    zip_name: str = DEFAULT_ZIP_NAME,
) -> Path:
    """Descarrega o ZIP MIT-BIH, extrai para a pasta de dados brutos e apaga o ZIP.

    Parâmetros
    ----------
    url
        URL de descarregamento (por omissão: get-zip PhysioNet da versão 1.0.0).
    raw_dir
        Diretório para o conteúdo extraído. Por omissão: ``RAW_DATA_DIR`` em
        ``src.config``.
    zip_name
        Nome do ficheiro ZIP temporário dentro de ``raw_dir``.

    Retorno
    -------
    pathlib.Path
        ``raw_dir`` após extração (absoluto).
    """
    ensure_data_dirs()
    target_raw = (raw_dir or RAW_DATA_DIR).resolve()
    target_raw.mkdir(parents=True, exist_ok=True)
    zip_path = target_raw / zip_name

    download_zip(url, zip_path)
    extract_zip(zip_path, target_raw)
    cleanup_zip(zip_path)
    return target_raw


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Interpreta argumentos da linha de comandos."""
    parser = argparse.ArgumentParser(
        description="Descarrega e extrai a base MIT-BIH Arrhythmia (WFDB).",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_DOWNLOAD_URL,
        help="URL do ZIP (por omissão: get-zip PhysioNet mitdb 1.0.0).",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Substitui o diretório de dados brutos (por omissão: src.config.RAW_DATA_DIR).",
    )
    parser.add_argument(
        "--zip-name",
        default=DEFAULT_ZIP_NAME,
        help="Nome do ZIP temporário dentro do diretório de dados brutos.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Apenas avisos no registo (menos verboso).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada para execução como script."""
    args = parse_args(argv)
    configure_logging(logging.WARNING if args.quiet else logging.INFO)
    try:
        run_download_pipeline(
            url=args.url,
            raw_dir=args.raw_dir,
            zip_name=args.zip_name,
        )
    except requests.RequestException as exc:
        logging.getLogger(__name__).error("Falha no descarregamento: %s", exc)
        return 1
    except (OSError, zipfile.BadZipFile) as exc:
        logging.getLogger(__name__).error("Erro no arquivo: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
