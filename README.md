# DSP ECG project (MIT-BIH foundation) - Group 6
> Pedro Arthur - RA: 
> Juliano Eleno Silva Pádua - RA: 800812
> Matheo - RA: 

Academic project foundation for **digital signal processing** on ECG: future stages will cover FIR filtering, convolution, 1D Gabor filters, and time-frequency analysis. This repository sets up **data ingestion**, **centralized paths**, **documentation**, and an **initial EDA notebook** for the MIT-BIH Arrhythmia Database in WFDB format.

## Table of contents

1. [Data source](#data-source)
2. [Repository layout](#repository-layout)
3. [Environment setup](#environment-setup)
4. [Install the package in editable mode](#install-the-package-in-editable-mode)
5. [Notebook Git hygiene (nbstripout)](#notebook-git-hygiene-nbstripout)
6. [Download the MIT-BIH dataset](#download-the-mit-bih-dataset)
7. [Run the EDA notebook](#run-the-eda-notebook)
8. [Documentation map (code modules)](#documentation-map-code-modules)
9. [References](#references)

## Data source

- **Database:** [MIT-BIH Arrhythmia Database 1.0.0](https://physionet.org/content/mitdb/1.0.0/)
- **ZIP:** [get-zip 1.0.0](https://physionet.org/content/mitdb/get-zip/1.0.0/) (about 73.5 MB compressed; about 104.3 MB uncompressed per PhysioNet)
- **Signals:** 48 half-hour two-channel ambulatory ECG excerpts; **360 Hz** sampling per channel; 11-bit resolution over a **10 mV** span (PhysioNet description)

Paths for raw and processed data are defined in [`src/config.py`](src/config.py) (`PROJECT_ROOT`, `RAW_DATA_DIR`, `PROCESSED_DATA_DIR`).

## Repository layout

| Path | Role |
|------|------|
| `data/raw/` | Extracted WFDB files (ignored by Git by default) |
| `data/processed/` | Reserved for filtered or derived signals |
| `docs/` | Data dictionary and per-module Markdown docs |
| `notebooks/` | Jupyter experiments |
| `src/` | Python package (`config`, `data`, `visualization`) |
| `requirements.txt` | Python dependencies (single source of truth) |
| `pyproject.toml` | Editable install only; dependencies are not duplicated here |

## Environment setup

1. **Create and activate a virtual environment** (from the repository root):

   ```bash
   python -m venv .venv
   ```

   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - Linux or macOS: `source .venv/bin/activate`

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Install the package in editable mode

Install the project so `import src` works from any working directory (including Jupyter) without changing `PYTHONPATH`:

```bash
pip install -e .
```

This uses [`pyproject.toml`](pyproject.toml) with Setuptools. Runtime packages remain listed only in `requirements.txt`.

## Notebook Git hygiene (nbstripout)

After dependencies are installed, **register the notebook stripout filter** in this Git repository:

```bash
nbstripout --install
```

This configures a clean filter so committed `.ipynb` files omit cell outputs and large embedded binary image data. That keeps diffs readable, avoids bloating history with regenerated plots, and reduces noisy merges. It is especially important if multiple people edit notebooks. Reinstall the filter if you clone the repo on a new machine.

## Download the MIT-BIH dataset

With the virtual environment active and the package installed in editable mode:

```bash
python -m src.data.download_dataset
```

This downloads the PhysioNet ZIP into `data/raw/`, extracts it, and removes the ZIP. See [`docs/src/data/download_dataset.md`](docs/src/data/download_dataset.md) for CLI options.

## Run the EDA notebook

```bash
jupyter notebook notebooks/01_EDA_Initial_Inspection.ipynb
```

The notebook imports `src.config` (including `mitdb_record_dir`) and uses `wfdb` to load record **100** and its `atr` annotations. Run the download step first so WFDB files exist under `data/raw/`.

## Documentation map (code modules)

| Code | Documentation |
|------|----------------|
| [`src/config.py`](src/config.py) | [`docs/src/config.md`](docs/src/config.md) |
| [`src/__init__.py`](src/__init__.py) | [`docs/src/__init__.md`](docs/src/__init__.md) |
| [`src/data/__init__.py`](src/data/__init__.py) | [`docs/src/data/__init__.md`](docs/src/data/__init__.md) |
| [`src/data/download_dataset.py`](src/data/download_dataset.py) | [`docs/src/data/download_dataset.md`](docs/src/data/download_dataset.md) |
| [`src/visualization/__init__.py`](src/visualization/__init__.py) | [`docs/src/visualization/__init__.md`](docs/src/visualization/__init__.md) |
| WFDB file types (`.hea`, `.dat`, `.atr`) | [`docs/data_dictionary.md`](docs/data_dictionary.md) |

## References

1. Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng Med Biol (May-June 2001).

2. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000;
