# Visão Geral do Projeto — Estado Atual

**Projeto 2: Redução de Ruído em Sinais de ECG**
Disciplina de Processamento de Sinais Digitais — Grupo 6
Pedro Arthur · Juliano Eleno Silva Pádua (RA: 800812) · Matheo

---

## 1. Objetivo Geral do Projeto

Aplicar técnicas de processamento digital de sinais sobre ECGs da base MIT-BIH Arrhythmia Database, cobrindo quatro etapas sequenciais:

| Etapa | Tema | Status |
|-------|------|--------|
| 1 | Pré-processamento / denoising (FIR + alternativa) | **Em andamento** |
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
│   ├── raw/mit-bih-arrhythmia-database-1.0.0/   # 48 registros WFDB (ignorado pelo Git)
│   └── processed/mitdb_record_inventory.csv       # inventário gerado
├── docs/
│   ├── visao_geral.md                             # este arquivo
│   ├── agents.md                                  # guia para agentes Claude
│   ├── data_dictionary.md                         # tipos WFDB
│   ├── mitdb_record_inventory_dictionary.md       # colunas do CSV
│   └── src/                                       # docs por módulo
├── notebooks/
│   └── 01_EDA_Initial_Inspection.ipynb            # EDA inicial
├── src/
│   ├── config.py                                  # caminhos centralizados
│   ├── data/
│   │   ├── download_dataset.py                    # download MIT-BIH
│   │   └── summarize_mitdb_records.py             # inventário tabular
│   └── visualization/                             # placeholder
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

---

## 5. O Que Falta para a Etapa 01

O PDF `Projeto_02_Etapa_01.pdf` define os requisitos. Abaixo o mapeamento do que ainda precisa ser feito:

### 5.1 Pipeline de Denoising (obrigatório)

| Requisito | Status | Observação |
|-----------|--------|------------|
| Filtro FIR com fase linear (técnica principal) | **Faltando** | Nenhum código de filtragem existe ainda |
| Remoção de baseline wander (passa-alta ~0.5 Hz) | **Faltando** | — |
| Rejeição de PLI 60 Hz (rejeita-faixa estreito) | **Faltando** | — |
| Limitação de banda superior (~35–40 Hz, passa-baixa) | **Faltando** | — |
| Ao menos uma técnica alternativa (IIR, média móvel ou domínio da freq.) | **Faltando** | — |
| Filtragem em fase zero (`sosfiltfilt`) para processamento offline | **Faltando** | — |

### 5.2 Justificativa e Avaliação (obrigatório)

| Requisito | Status |
|-----------|--------|
| Justificativa técnica das frequências de corte e ordem do filtro | **Faltando** |
| Visualização comparativa antes/depois da filtragem | **Faltando** |
| Análise espectral (Welch/FFT) antes e depois | **Faltando** |
| Preservação morfológica: ondas P, QRS, T | **Faltando** |
| Estabilidade temporal dos eventos cardíacos pós-filtro | **Faltando** |

### 5.3 Estrutura de Código Sugerida (ainda não existe)

```
src/
├── preprocessing/          # a criar
│   ├── __init__.py
│   ├── fir_filters.py      # projeto FIR (janela e Parks-McClellan)
│   ├── iir_filters.py      # alternativa IIR (Butterworth)
│   └── pipeline.py         # cadeia completa de denoising
notebooks/
├── 02_Denoising_FIR.ipynb  # a criar — análise e comparação de filtros
```

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

Este documento deve ser atualizado a cada etapa concluída. Para cada item da seção 5, mova o status de **Faltando** para **Concluído** e adicione uma referência ao notebook ou módulo correspondente. Ao iniciar uma nova etapa, adicione uma nova seção ao estilo da seção 5 com os requisitos extraídos do PDF da etapa.
