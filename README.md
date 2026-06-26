# Projeto 2 - DSP em ECG (base MIT-BIH) - Grupo 6

> Pedro Arthur - RA: 814248
> Juliano Eleno Silva Pádua - RA: 800812
> Matheo - RA: 821293

Esse repositório organiza um projeto acadêmico de **Processamento Digital de
Sinais** aplicado a ECG da MIT-BIH Arrhythmia Database. O trabalho combina
ingestão WFDB, filtragem FIR, convolução temporal e por FFT, análise
tempo-frequência, filtros de Gabor 1D e detectores de anomalia treinados apenas
com batimentos normais.

Há duas entregas principais:

- um notebook didático da disciplina, com inspeção do ECG, filtros, Gabor,
  STFT, features e comparação entre SVM supervisionada e One-Class SVM;
- um artigo em LaTeX que compara One-Class SVM, Isolation Forest e LOF em uma
  ablação A0-A3 com split inter-paciente.

## Sumário

1. [Fonte de dados](#fonte-de-dados)
2. [Pipeline do artigo](#pipeline-do-artigo)
3. [Estrutura do repositório](#estrutura-do-repositório)
4. [Configuração do ambiente](#configuração-do-ambiente)
5. [Atalhos com Makefile](#atalhos-com-makefile)
6. [Política de Git](#política-de-git)
7. [Download da base MIT-BIH](#download-da-base-mit-bih)
8. [Execução do notebook da Etapa 01](#execução-do-notebook-da-etapa-01)
9. [Referências](#referências)

## Fonte de dados

- **Base:** [MIT-BIH Arrhythmia Database 1.0.0](https://physionet.org/content/mitdb/1.0.0/)
- **ZIP:** [get-zip 1.0.0](https://physionet.org/content/mitdb/get-zip/1.0.0/) (cerca de 73,5 MB comprimidos; cerca de 104,3 MB descomprimidos, segundo a PhysioNet)
- **Sinais:** 48 trechos de meia hora de ECG ambulatorial em dois canais; amostragem **360 Hz** por canal; resolução de 11 bits em faixa de **10 mV** (descrição PhysioNet)

Os caminhos para dados brutos e processados estão definidos em [`src/config.py`](src/config.py) (`PROJECT_ROOT`, `RAW_DATA_DIR`, `PROCESSED_DATA_DIR`).

## Pipeline do artigo

O pipeline experimental do artigo vive em [`src/paper/`](src/paper/). Ele
constrói uma linha por batimento segmentado em torno da anotação MIT-BIH, usa
`N` como classe normal e trata os demais símbolos válidos não-paced como
anomalia apenas na avaliação. Os registros paced-heavy `102`, `104`, `107` e
`217` ficam fora do protocolo v1.

A ablação mantém a mesma população de batimentos em todos os estágios:

| Estágio | Entrada | Features |
|---------|---------|----------|
| `A0 raw` | ECG bruto | morfologia e intervalos RR |
| `A1 filtered` | ECG filtrado | mesmas features de A0 |
| `A2 spectral` | ECG filtrado | A1 + energia por bandas, entropia, centroide e STFT |
| `A3 gabor` | ECG filtrado | A2 + respostas Gabor em janelas P/QRS/T |

Os detectores comparados são One-Class SVM, Isolation Forest e Local Outlier
Factor com `novelty=True`, todos ajustados apenas com batimentos normais do
conjunto de treino. A métrica principal do artigo é PR-AUC, acompanhada de
ROC-AUC, precision, recall, F1 e matriz de confusão.

## Estrutura do repositório

| Caminho | Função |
|---------|--------|
| `data/raw/` | arquivos WFDB extraídos (ignorados pelo Git por omissão) |
| `data/processed/` | features, métricas e artefatos derivados, ignorados pelo Git |
| `docs/` | documentação, enunciado e manuscrito LaTeX do artigo |
| `docs/paper/article/` | fontes versionados do artigo e figuras finais |
| `llm-wiki/` | base local de estudo e dossiês, mantida fora do Git |
| `notebooks/` | Experimentos em Jupyter |
| `src/` | pacote Python do projeto |
| `src/paper/` | construção de dataset, ablação, figuras e auditoria do artigo |
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

## Atalhos com Makefile

Depois de criar a `.venv`, os comandos recorrentes do projeto podem ser
executados por `make` a partir da raiz do repositório:

```bash
make setup
make data
make inventory
make paper-build
make paper-run
make paper-figures
make paper-pdf
make paper-audit
make test
```

Para uma execução curta de sanidade do pipeline do artigo:

```bash
make paper-smoke
```

O fluxo completo do artigo é:

```bash
make paper-build
make paper-run
make paper-figures
make paper-pdf
make paper-audit
```

`make test` compila os módulos Python do artigo e valida os CSVs gerados em
`data/processed/paper/`.

## Política de Git

Entram no Git:

- códigos em `src/`, incluindo `src/paper/`;
- notebooks versionados sem saídas;
- fontes do artigo em `docs/paper/article/`, incluindo `.tex`, `ref.bib`,
  `arxiv.sty` e PDFs finais de figuras.

Ficam fora do Git:

- `llm-wiki/`, por ser memória local de estudo e trabalho dos agentes;
- `data/raw/` e `data/processed/`, exceto `.gitkeep`;
- `docs/paper/article/main.pdf` e auxiliares de compilação LaTeX;
- `docs/paper/template_raw/` e `docs/paper/ax.tar`;
- caches, ambientes virtuais e artefatos de build.

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

## Execução do notebook da Etapa 01

O notebook da Etapa 01 está em [`notebooks/01_Etapa.ipynb`](notebooks/01_Etapa.ipynb). Abra o arquivo e execute as células sequencialmente. Confirme que o passo de download foi concluído para que existam arquivos WFDB sob `data/raw/`.

Alternativa por terminal (abre o servidor clássico do Jupyter no browser):

```bash
jupyter notebook notebooks/01_Etapa.ipynb
```

O notebook importa `src.config` (incluindo `mitdb_record_dir`) e utiliza `wfdb` para carregar registos da base MIT-BIH e suas anotações `atr`.

A implementação dos códigos utilizados na Etapa 01 está no folder [`src/preprocessing/`](src/preprocessing/). O notebook funciona como camada de apresentação e análise, importando as funções desse pacote. Os módulos disponíveis são:

| Módulo | Função |
|--------|--------|
| [`src/preprocessing/fir_filters.py`](src/preprocessing/fir_filters.py) | Filtros FIR aplicados ao ECG |
| [`src/preprocessing/iir_filters.py`](src/preprocessing/iir_filters.py) | Filtros IIR aplicados ao ECG |
| [`src/preprocessing/gabor_filters.py`](src/preprocessing/gabor_filters.py) | Filtros de Gabor unidimensionais |
| [`src/preprocessing/simple_filters.py`](src/preprocessing/simple_filters.py) | Filtros simples de referência |
| [`src/preprocessing/segments.py`](src/preprocessing/segments.py) | Segmentação dos sinais |
| [`src/preprocessing/metrics.py`](src/preprocessing/metrics.py) | Métricas de avaliação |

## Referências

1. Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng Med Biol (May-June 2001).

2. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000.
