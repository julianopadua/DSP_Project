# `src/data/download_dataset.py`

## Finalidade

Descarrega o arquivo **get-zip** da PhysioNet para a MIT-BIH versão 1.0.0, grava-o temporariamente no diretório de dados brutos, extrai todo o conteúdo para essa mesma pasta e remove o ZIP para poupar espaço em disco. O progresso é registado com o módulo standard `logging`.

## Configuração

- **URL por omissão:** `https://physionet.org/content/mitdb/get-zip/1.0.0/`
- **Diretório bruto por omissão:** `src.config.RAW_DATA_DIR` (salvo `--raw-dir`).
- **Nome do ZIP em disco por omissão:** `mitdb-1.0.0.zip` (removido após extração).

O módulo chama `ensure_data_dirs()` de `src.config` antes do descarregamento.

## Funções principais

| Função | Papel |
|--------|------|
| `configure_logging` | Define logging básico para uso em CLI. |
| `download_zip` | Transmite a resposta HTTP para ficheiro em blocos. |
| `extract_zip` | Descompacta o arquivo com `zipfile` para a pasta de destino. |
| `cleanup_zip` | Elimina o ficheiro ZIP após extração. |
| `run_download_pipeline` | Orquestra descarregamento, extração e limpeza. |
| `main` | Ponto de entrada da CLI (`argparse`). |

## Linha de comandos

Após `pip install -e .`, a partir da raiz do repositório:

```bash
python -m src.data.download_dataset
```

Opções:

- `--url` : URL alternativa do ZIP
- `--raw-dir` : substitui o diretório de dados brutos
- `--zip-name` : nome do ZIP temporário dentro do diretório bruto
- `-q` / `--quiet` : registo menos verboso

## Interações

- **`src.config`:** `RAW_DATA_DIR`, `ensure_data_dirs`.
- **A jusante:** os ficheiros WFDB são lidos por notebooks ou outro código com `wfdb`; consulte `src.config.mitdb_record_dir()` e o [Dicionário de dados](../data_dictionary.md).

## Documentação relacionada

- [`config.md`](../config.md)
