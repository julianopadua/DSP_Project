# `src/config.py`

## Finalidade

Centralizar caminhos no sistema de ficheiros para que scripts e notebooks partilhem uma única definição da localização dos dados brutos e processados. Os caminhos são construídos com `pathlib` e resolvidos relativamente a este ficheiro: a raiz do projeto é o diretório pai do pacote `src`.

## Exportações

| Nome | Significado |
|------|-------------|
| `PROJECT_ROOT` | Caminho absoluto para a raiz do repositório. |
| `RAW_DATA_DIR` | `PROJECT_ROOT / "data" / "raw"` (extratos PhysioNet, ficheiros WFDB). |
| `PROCESSED_DATA_DIR` | `PROJECT_ROOT / "data" / "processed"` (sinais filtrados futuros). |

## Funções

- **`ensure_data_dirs()`**  
  Cria `RAW_DATA_DIR` e `PROCESSED_DATA_DIR` se não existirem. Utilizada pelo fluxo de descarregamento antes de escrever ficheiros.

- **`mitdb_record_dir()`**  
  Devolve o diretório que contém os ficheiros WFDB do registo (por exemplo `100.hea`). Após extrair o ZIP MIT-BIH, os registos podem estar diretamente em `RAW_DATA_DIR` ou numa subpasta imediata. A função verifica `100.hea` no nível superior e depois subpastas. Gera `FileNotFoundError` se a base estiver em falta.

## Interações

- **`src.data.download_dataset`** importa `RAW_DATA_DIR` e chama `ensure_data_dirs()` antes do descarregamento e da extração.
- **Notebooks** importam `mitdb_record_dir()` (e opcionalmente `RAW_DATA_DIR`) para construir o caminho completo do registo passado a `wfdb.rdrecord` e `wfdb.rdann` (por exemplo `(mitdb_record_dir() / "100").as_posix()`).

## Documentação relacionada

- [Dicionário de dados (ficheiros WFDB)](../data_dictionary.md)
- [`download_dataset.md`](data/download_dataset.md)
