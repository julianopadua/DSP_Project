# Visão Geral do Projeto — Estado Atual

**Projeto 2: Redução de Ruído em Sinais de ECG**
Disciplina de Processamento de Sinais Digitais — Grupo 6
Pedro Arthur · Juliano Eleno Silva Pádua (RA: 800812) · Matheo

---

## 1. Objetivo Geral do Projeto

Aplicar técnicas de processamento digital de sinais sobre ECGs da base MIT-BIH Arrhythmia Database, cobrindo quatro etapas sequenciais:

| Etapa | Tema | Status |
|-------|------|--------|
| 1 | Pré-processamento / denoising (FIR + alternativas) | **Concluída** |
| 2 | Filtragem FIR — análise aprofundada e convolução rápida (FFT) | Não iniciada |
| 3 | Filtros de Gabor 1D | Não iniciada |
| 4 | Espectro de potência tempo-frequência | Não iniciada |

---

## 2. Base de Dados

- **MIT-BIH Arrhythmia Database 1.0.0** (PhysioNet)
- 48 registros de ECG ambulatorial com dois canais, ~30 min cada
- Taxa de amostragem: **360 Hz** por canal; resolução 11 bits / 10 mV
- Formato: **WFDB** (`.hea`, `.dat`, `.atr`)
- Dados brutos em: `data/raw/mit-bih-arrhythmia-database-1.0.0/` (**já baixados**)
- Inventário tabular gerado em: `data/processed/mitdb_record_inventory.csv`

---

## 3. Estrutura do Repositório

```
DSP_Project/
├── data/
│   ├── raw/mit-bih-arrhythmia-database-1.0.0/      # 48 registros WFDB (ignorado pelo Git)
│   └── processed/
│       ├── mitdb_record_inventory.csv               # inventário gerado
│       └── etapa01_denoising_metrics.csv            # tabela consolidada da Etapa 01
├── docs/
│   ├── visao_geral.md                              # este arquivo
│   ├── agents.md                                   # guia para agentes Claude
│   ├── etapa_01_denoising.md                       # guia didático da Etapa 01
│   ├── data_dictionary.md                          # tipos WFDB
│   ├── mitdb_record_inventory_dictionary.md        # colunas do CSV
│   └── src/                                        # docs por módulo
├── notebooks/
│   ├── 01_EDA_Initial_Inspection.ipynb             # EDA inicial
│   └── 02_Denoising_FIR.ipynb                      # FIR + alternativas (Etapa 01)
├── src/
│   ├── config.py                                   # caminhos centralizados
│   ├── data/
│   │   ├── download_dataset.py                     # download MIT-BIH
│   │   └── summarize_mitdb_records.py              # inventário tabular
│   ├── preprocessing/                              # Etapa 01
│   │   ├── fir_filters.py                          # FIR fase linear (janela)
│   │   ├── iir_filters.py                          # Butterworth alternativo
│   │   ├── simple_filters.py                       # MA + filtragem espectral
│   │   ├── segments.py                             # seleção de janelas com símbolo + ruído
│   │   └── metrics.py                              # métricas padronizadas
│   └── visualization/
│       └── ecg_plots.py                            # overlays, PSD, resposta de filtro
├── pyproject.toml
└── requirements.txt
```

---

## 4. O Que Já Está Implementado

### 4.1 Infraestrutura

- Ambiente Python com `.venv`, `requirements.txt` e instalação editável via `pyproject.toml`
- `nbstripout` configurado para higiene de notebooks no Git
- Caminhos centralizados em `src/config.py` (`PROJECT_ROOT`, `RAW_DATA_DIR`, `PROCESSED_DATA_DIR`, `mitdb_record_dir()`)

### 4.2 Ingestão de Dados

- `src/data/download_dataset.py`: baixa e extrai o ZIP da PhysioNet automaticamente
- Dados já presentes em `data/raw/`

### 4.3 Inventário e Análise Exploratória de Ruído

- `src/data/summarize_mitdb_records.py`: percorre todos os 48 registros e gera CSV com:
  - Metadados do cabeçalho WFDB (fs, n_sig, duração, ganho ADC, etc.)
  - Contagem de anotações por símbolo (N, V, A, F, etc.) e por ritmo (AFIB, VT, etc.)
  - **Métricas de ruído preliminares** calculadas por janelas via Welch:
    - `noise_score_bw`: deriva de linha de base (< 0.8 Hz vs. 5–40 Hz)
    - `noise_score_pli`: interferência da rede elétrica (~60 Hz)
    - `noise_score_emg`: ruído muscular (> 40 Hz)
    - `noise_score_motion`: artefatos de movimento (spike ratio + outlier fraction)
  - Flags booleanas e rótulo primário de ruído por registro

### 4.4 EDA Inicial

- `notebooks/01_EDA_Initial_Inspection.ipynb`: carrega registro 100, lê anotações `.atr`, inspeciona formas de onda

### 4.5 Denoising — Etapa 01 (concluída)

Implementação modular em `src/preprocessing/`:

- `fir_filters.py`: projeto FIR pelo método da janela (Hamming) — passa-alta para BW, rejeita-faixa para PLI, passa-baixa para EMG. Aplicação via `filtfilt` (fase zero), `lfilter` com compensação de atraso e `fftconvolve` (convolução rápida).
- `iir_filters.py`: alternativa Butterworth de ordem baixa via `sosfiltfilt`.
- `simple_filters.py`: média móvel (incl. notch exato em 60 Hz com N=6 em fs=360 Hz) e filtragem direta no domínio da frequência.
- `segments.py`: seleção de janelas reais que contêm um símbolo-alvo de anotação WFDB e maximizam um indicador heurístico de ruído.
- `metrics.py`: métricas espectrais aplicáveis a sinal real (sem ground truth) — redução em banda alvo (dB), preservação de banda passante (dB), deslocamento RMS de picos R em ms.

Trabalhamos exclusivamente com **sinais reais** — três registos (100 Normal, 109 LBBB, 118 RBBB), com janela de duração configurável (`SAMPLE_DURATION_SEC` no notebook). Demonstração e comparação no notebook `notebooks/02_Denoising_FIR.ipynb`. Tabela consolidada exportada em `data/processed/etapa01_denoising_metrics.csv`. Justificativa didática completa em [`docs/etapa_01_denoising.md`](etapa_01_denoising.md).

---

## 5. Etapa 01 — Status dos Requisitos (PDF)

### 5.1 Pipeline de Denoising

| Requisito | Status | Onde |
|-----------|--------|------|
| Filtro FIR com fase linear (técnica principal) | **Concluído** | `src/preprocessing/fir_filters.py` |
| Remoção de baseline wander (HP 0,5 Hz) | **Concluído** | notebook §4 |
| Rejeição de PLI 60 Hz (BS 59–61 Hz) | **Concluído** | notebook §5 |
| Limitação de banda superior (LP 40 Hz) | **Concluído** | notebook §6 |
| Cadeia FIR completa (HP → BS → LP) | **Concluído** | notebook §7 |
| FIR via FFT (convolução rápida) | **Concluído** | notebook §8 |
| Técnica alternativa — IIR Butterworth | **Concluído** | notebook §9 |
| Técnica alternativa — Média móvel | **Concluído** | notebook §10 |
| Técnica alternativa — Filtragem espectral direta | **Concluído** | notebook §11 |
| Filtragem em fase zero (`filtfilt`/`sosfiltfilt`) | **Concluído** | aplicada em todas as cadeias |

### 5.2 Justificativa e Avaliação

| Requisito | Status | Onde |
|-----------|--------|------|
| Justificativa técnica das frequências de corte e ordem do filtro | **Concluído** | [`etapa_01_denoising.md`](etapa_01_denoising.md) §3 |
| Visualização comparativa cru × filtrado (overlay) | **Concluído** | notebook (todas as seções) |
| Análise espectral (Welch) antes e depois | **Concluído** | notebook (todas as seções) |
| Preservação morfológica e correlação com sinal limpo | **Concluído** | métrica `correlação_clean` |
| Estabilidade temporal dos eventos cardíacos pós-filtro | **Concluído** | métrica `picos_R_RMS_ms` |
| Tabela final de comparação entre métodos | **Concluído** | notebook §12 + CSV exportado |

---

## 6. Dependências Atuais

| Biblioteca | Versão mínima | Uso |
|-----------|--------------|-----|
| `numpy` | 1.24 | arrays, álgebra |
| `pandas` | 2.0 | inventário CSV |
| `matplotlib` | 3.7 | visualização |
| `scipy` | 1.11 | Welch, projeto de filtros FIR/IIR |
| `wfdb` | 4.1 | leitura WFDB |
| `requests` | 2.31 | download |
| `jupyter` | 1.0 | notebooks |
| `nbstripout` | 0.6 | higiene Git |

`scipy.signal` já disponível: suporta `firwin`, `firwin2`, `remez` (Parks-McClellan), `butter`, `sosfiltfilt`, `welch` — sem dependências adicionais para a Etapa 01.

---

## 7. Critérios de Avaliação da Etapa 01 (extraídos do PDF)

1. Redução efetiva de: baseline wander, interferência PLI e ruído de alta frequência (EMG)
2. Preservação morfológica das ondas P, QRS e T
3. Estabilidade temporal da posição dos eventos cardíacos
4. Coerência entre a resposta do filtro projetado e o espectro observado
5. Clareza da justificativa técnica para os parâmetros escolhidos

---

## 8. Como Atualizar Este Arquivo

Este documento deve ser atualizado a cada etapa concluída. Para cada item da seção 5, mova o status de **Faltando** para **Concluído** e adicione uma referência ao notebook ou módulo correspondente. Ao iniciar uma nova etapa (Etapa 02 e seguintes), adicione uma nova seção ao estilo da seção 5 com os requisitos extraídos do PDF correspondente, e replique o padrão de estrutura modular adotado em `src/preprocessing/` para a Etapa 01.
