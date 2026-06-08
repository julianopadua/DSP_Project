PYTHON ?= .venv/bin/python
MPLCONFIGDIR ?= /private/tmp/dsp_matplotlib
MPLBACKEND ?= Agg
PAPER_DIR := docs/paper/article
SMOKE_DIR := /private/tmp/dsp_paper_smoke

.PHONY: help setup data inventory paper-build paper-run paper-figures paper-pdf paper-all paper-smoke test clean-paper

help:
	@printf '%s\n' \
		'Targets principais' \
		'  make setup          instala dependencias e pacote em modo editavel' \
		'  make data           baixa e extrai a MIT-BIH' \
		'  make inventory      gera inventario dos registros MIT-BIH' \
		'  make paper-build    gera features A0-A3' \
		'  make paper-run      executa ablação one-class' \
		'  make paper-figures  gera figuras do artigo' \
		'  make paper-pdf      compila o manuscrito LaTeX' \
		'  make paper-all      executa build, ablação, figuras e PDF' \
		'  make paper-smoke    roda teste curto com registros 100 e 101' \
		'  make test           compila Python e valida integridade dos CSVs'

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

data:
	$(PYTHON) -m src.data.download_dataset

inventory:
	$(PYTHON) -m src.data.summarize_mitdb_records

paper-build:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.build_dataset

paper-run:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.run_ablation

paper-figures:
	MPLBACKEND=$(MPLBACKEND) MPLCONFIGDIR=$(MPLCONFIGDIR) PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.make_figures

paper-pdf:
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error $(PAPER_DIR)/main.tex

paper-all: paper-build paper-run paper-figures paper-pdf

paper-smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.build_dataset --records 100,101 --max-beats-per-record 80 --output-dir $(SMOKE_DIR)
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.run_ablation --input-dir $(SMOKE_DIR) --output-dir $(SMOKE_DIR) --max-train-normals 50

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m compileall src/paper src/config.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.paper.validate_outputs

clean-paper:
	latexmk -cd -C $(PAPER_DIR)/main.tex
