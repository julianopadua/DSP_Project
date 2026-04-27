# Projeto 2 - DSP em ECG (base MIT-BIH) - Grupo 6

> Pedro Arthur - RA: 814248
> Juliano Eleno Silva Pádua - RA: 800812
> Matheo - RA: 821293

Esse projeto baixa a base acadêmica do MIT-BIH para **processamento digital de sinais** aplicado ao ECG: etapas futuras incluirão filtragem FIR, convolução, filtros de Gabor unidimensionais e análise tempo-frequência. Aqui, realiza-se **ingestão de dados**, **caminhos centralizados**, **documentação** e um **notebook inicial de EDA** para a base MIT-BIH Arrhythmia em formato WFDB.

## Sumário

1. [Fonte de dados](#fonte-de-dados)
2. [Estrutura do repositório](#estrutura-do-repositório)
3. [Configuração do ambiente](#configuração-do-ambiente)
4. [Instalação editável do pacote](#instalação-editável-do-pacote)
5. [Higiene de notebooks no Git (nbstripout)](#higiene-de-notebooks-no-git-nbstripout)
6. [Download da base MIT-BIH](#download-da-base-mit-bih)
7. [Sumarização dos registos MIT-BIH](#sumarização-dos-registos-mit-bih)
8. [Execução do notebook de EDA](#execução-do-notebook-de-eda)
9. [Mapa da documentação (módulos)](#mapa-da-documentação-módulos)
10. [Referências](#referências)

## Fonte de dados

- **Base:** [MIT-BIH Arrhythmia Database 1.0.0](https://physionet.org/content/mitdb/1.0.0/)
- **ZIP:** [get-zip 1.0.0](https://physionet.org/content/mitdb/get-zip/1.0.0/) (cerca de 73,5 MB comprimidos; cerca de 104,3 MB descomprimidos, segundo a PhysioNet)
- **Sinais:** 48 trechos de meia hora de ECG ambulatorial em dois canais; amostragem **360 Hz** por canal; resolução de 11 bits em faixa de **10 mV** (descrição PhysioNet)

Os caminhos para dados brutos e processados estão definidos em [`src/config.py`](src/config.py) (`PROJECT_ROOT`, `RAW_DATA_DIR`, `PROCESSED_DATA_DIR`).

## Estrutura do repositório

| Caminho | Função |
|---------|--------|
| `data/raw/` | arquivos WFDB extraídos (ignorados pelo Git por omissão) |
| `data/processed/` | Reservado a sinais filtrados ou derivados |
| `docs/` | Dicionário de dados e documentação Markdown por módulo |
| `notebooks/` | Experimentos em Jupyter |
| `src/` | Pacote Python (`config`, `data`, `visualization`) |
| `requirements.txt` | Dependências Python (fonte única) |
| `pyproject.toml` | Instalação editável; dependências não duplicadas aqui |

## Configuração do ambiente

1. **Crie e ative um ambiente virtual** (a partir da raiz do repositório):

   ```bash
   python -m venv .venv
   ```

   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - Linux ou macOS: `source .venv/bin/activate`

2. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

## Instalação editável do pacote

Instale o projeto para que `import src` funcione a partir de qualquer diretório de trabalho (incluindo Jupyter) sem alterar `PYTHONPATH`:

```bash
pip install -e .
```

Utiliza [`pyproject.toml`](pyproject.toml) com Setuptools. Os pacotes de execução permanecem apenas em `requirements.txt`.

## Higiene de notebooks no Git (nbstripout)

Após instalar dependências, **registe o filtro de limpeza de notebooks** neste repositório Git:

```bash
nbstripout --install
```

Essa etapa configura um clean filter para que os `.ipynb` versionados omitam saídas das células e dados binários grandes embutidos. Isto mantém diffs legíveis, evita histórico inchado com gráficos regenerados e reduz conflitos ruidosos. É especialmente relevante com edição colaborativa de notebooks. **Reinstale o filtro** se clonar o repositório noutra máquina.

## Download da base MIT-BIH

Com o ambiente virtual ativo e o pacote instalado em modo editável:

```bash
python -m src.data.download_dataset
```

Faz o download do ZIP da PhysioNet para `data/raw/`, extrai o conteúdo e remove o ZIP. Opções de linha de comandos em [`docs/src/data/download_dataset.md`](docs/src/data/download_dataset.md).

## Sumarização dos registos MIT-BIH

Depois do download da base, gere o inventário tabular dos registos:

```bash
python -m src.data.summarize_mitdb_records
```

Se o seu sistema não tiver o alias `python`, use:

```bash
python3 -m src.data.summarize_mitdb_records
```

O comando percorre os registos WFDB encontrados em `data/raw/mit-bih-arrhythmia-database-1.0.0` e escreve, por omissão, o folder:

`data/processed/mitdb_record_inventory.csv`

Para acelerar uma execução inicial (sem cálculo de ruído), pode usar:

```bash
python -m src.data.summarize_mitdb_records --skip-noise
```

## Execução do notebook de EDA

Pode abrir e executar o notebook diretamente: abra `notebooks/01_EDA_Initial_Inspection.ipynb` e execute as células sequencialmente. Confirme que o passo de download foi concluído para que existam ficheiros WFDB sob `data/raw/`.

Alternativa por terminal (abre o servidor clássico do Jupyter no browser):

```bash
jupyter notebook notebooks/01_EDA_Initial_Inspection.ipynb
```

O notebook importa `src.config` (incluindo `mitdb_record_dir`) e utiliza `wfdb` para carregar o registo **100** e as anotações `atr`.

## Mapa da documentação (módulos)

| Código | Documentação |
|--------|----------------|
| [`src/config.py`](src/config.py) | [`docs/src/config.md`](docs/src/config.md) |
| [`src/__init__.py`](src/__init__.py) | [`docs/src/__init__.md`](docs/src/__init__.md) |
| [`src/data/__init__.py`](src/data/__init__.py) | [`docs/src/data/__init__.md`](docs/src/data/__init__.md) |
| [`src/data/download_dataset.py`](src/data/download_dataset.py) | [`docs/src/data/download_dataset.md`](docs/src/data/download_dataset.md) |
| [`src/visualization/__init__.py`](src/visualization/__init__.py) | [`docs/src/visualization/__init__.md`](docs/src/visualization/__init__.md) |
| Tipos de ficheiro WFDB (`.hea`, `.dat`, `.atr`) | [`docs/data_dictionary.md`](docs/data_dictionary.md) |

## Referências

1. Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng Med Biol (May-June 2001).

2. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000.
