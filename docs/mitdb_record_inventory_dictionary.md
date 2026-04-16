# Dicionário do inventário MIT-BIH (`mitdb_record_inventory.csv`)

Este documento descreve as colunas produzidas por [`src/data/summarize_mitdb_records.py`](../src/data/summarize_mitdb_records.py) ao percorrer todos os ficheiros `*.hea` no diretório devolvido por `mitdb_record_dir()` (ficheiros WFDB da [MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/)).

## Como gerar o CSV

Na raiz do repositório, com o ambiente virtual activo e dependências instaladas (`pip install -r requirements.txt` e `pip install -e .`):

```bash
python -m src.data.summarize_mitdb_records
```

Por omissão o ficheiro é escrito em `data/processed/mitdb_record_inventory.csv` (pasta ignorada pelo Git; criada se necessário). Opções úteis:

| Opção | Efeito |
|--------|--------|
| `--output-csv CAMINHO` | Define o ficheiro de saída. |
| `--skip-noise` | Não carrega `p_signal`; colunas de ruído ficam vazias / `noise_analysis_error=skipped`. |
| `--noise-full-record` | Uma única janela com o registo completo (mais memória e tempo). |
| `--noise-window-sec` | Duração de cada janela em segundos (por omissão: 10). |
| `--noise-max-windows` | Número máximo de janelas uniformemente distribuídas ao longo do registo (por omissão: 12). |
| `--pli-hz` | Frequência da rede para PLI (por omissão: 60; use 50 em dados europeus). |
| `--fail-fast` | Aborta se `build_row` lançar excepção (erros de `wfdb` por registo são capturados sem abortar). |

## Convenções gerais

- **Uma linha por registo** identificado por `record_id` (stem do ficheiro `.hea`, por exemplo `100`).
- Valores em falta aparecem como células vazias no CSV (pandas escreve como campo vazio ou `NaN` conforme o tipo).
- Booleanos aparecem como `True` / `False` no CSV.
- Contagens de anotações são inteiras não negativas.

---

## Tabela de colunas (ordem do CSV)

### Bloco A — Identidade, ficheiros e estado de leitura

| Coluna | Tipo | Origem | Descrição |
|--------|------|--------|-----------|
| `record_id` | string | stem de `*.hea` | Identificador do registo WFDB (sem extensão). |
| `record_prefix_posix` | string | `Path` | Prefixo absoluto POSIX passado a `wfdb.rdheader` / `wfdb.rdann` / `wfdb.rdrecord`. |
| `has_hea` | bool | `Path.is_file()` | Existe `{id}.hea`. |
| `has_dat` | bool | idem | Existe `{id}.dat`. |
| `has_atr` | bool | idem | Existe `{id}.atr`. |
| `triplet_complete` | bool | derivado | `True` apenas se os três ficheiros existirem. |
| `bytes_hea` | float/int | `stat().st_size` | Tamanho em bytes; vazio se o ficheiro não existir. |
| `bytes_dat` | float/int | idem | idem |
| `bytes_atr` | float/int | idem | idem |
| `header_ok` | bool | `wfdb.rdheader` | `True` se o cabeçalho foi lido sem excepção. |
| `ann_ok` | bool | `wfdb.rdann(..., "atr")` | `True` se as anotações `atr` foram lidas sem excepção. |
| `parse_error` | string | excepções | Resumo curto (`rdheader:...`, `rdann:...`, `missing_triplet_file`, ou vazio). |

### Bloco B — Metadados do cabeçalho (`wfdb.rdheader`)

Equivalentes aos campos habituais de [`wfdb.Record`](https://wfdb.readthedocs.io/en/latest/record.html) após leitura só do `.hea` (sem carregar amostras da forma de onda).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `fs_hz` | float | Frequência de amostragem em Hz (MIT-BIH: 360). |
| `n_sig` | int | Número de canais. |
| `sig_len_samples` | int | Número de amostras por canal. |
| `duration_s` | float | `sig_len_samples / fs_hz`. |
| `sig_names` | string | Nomes dos canais separados por `\|`. |
| `base_date` | string | Data de referência WFDB (pode estar vazia). |
| `base_time` | string | Hora de referência WFDB (pode estar vazia). |
| `n_comments` | int | Número de linhas de comentário no cabeçalho. |
| `comments_concat` | string | Comentários concatenados (truncado a 2000 caracteres). |
| `sig_0_*` / `sig_1_*` | vários | Metadados por canal: `file` (nome do ficheiro de amostras), `fmt` (formato WFDB, ex. `212`), `units`, `adc_gain`, `baseline`, `init_val`, `adc_res`, `samps_per_frame`. O canal 1 fica vazio/`NaN` se `n_sig < 2`. |

### Bloco C — Resumo das anotações `atr`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `n_annotations` | int | Número de entradas de anotação (comprimento de `ann.sample`). |
| `ann_first_sample` | int | Primeiro índice de amostra anotado. |
| `ann_last_sample` | int | Último índice de amostra anotado. |
| `ann_sym_*` | int | Contagem por símbolo em `ann.symbol` (ver tabela abaixo). Nomes seguros: `ann_sym_SLASH` para `/`, `ann_sym_PIPE` para `\|`, etc. |
| `ann_sym_other_count` | int | Símbolos observados que **não** pertencem à lista canónica do script. |
| `ann_sym_unlisted` | string | Símbolos não canónicos únicos, separados por `\|`. |

### Bloco D — Ritmos em `aux_note`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `n_aux_note_nonempty` | int | Número de entradas `aux_note` não vazias após normalização (remoção de `\x00` e espaços). |
| `aux_note_unique_truncated` | string | Até 40 strings `aux_note` distintas, separadas por ` \|\| ` (truncado a 4000 caracteres). |
| `aux_rhy_<SLUG>` | int | Contagem de notas de ritmo: para cada `aux_note` normalizado, procuram-se substrings conhecidas (ex. `(AFIB`). Se várias substrings coincidem numa mesma nota, **mantêm-se apenas as maximais** (nenhuma é subcadeia estrita de outra coincidente), para evitar duplo contar `(P` dentro de `(PM` ou `(N` dentro de `(NOD`. |

Colunas `aux_rhy_*` (ordem **exacta** no CSV, alinhada com `RHYTHM_AUX_SUBSTRINGS` no código — substrings mais longas primeiro para evitar ambiguidades):

| Coluna | Substring procurada em `aux_note` |
|--------|-----------------------------------|
| `aux_rhy_AFIB` | `(AFIB` |
| `aux_rhy_ASMI` | `(ASMI` |
| `aux_rhy_BIGU` | `(BIGU` |
| `aux_rhy_HGEA` | `(HGEA` |
| `aux_rhy_PREX` | `(PREX` |
| `aux_rhy_SVTA` | `(SVTA` |
| `aux_rhy_AFL` | `(AFL` |
| `aux_rhy_BII` | `(BII` |
| `aux_rhy_IVR` | `(IVR` |
| `aux_rhy_NOD` | `(NOD` |
| `aux_rhy_SBR` | `(SBR` |
| `aux_rhy_VFL` | `(VFL` |
| `aux_rhy_AB` | `(AB` |
| `aux_rhy_VT` | `(VT` |
| `aux_rhy_PM` | `(PM` |
| `aux_rhy_B` | `(B` |
| `aux_rhy_N` | `(N` |
| `aux_rhy_P` | `(P` |
| `aux_rhy_T` | `(T` |

---

## Códigos `ann.symbol` (WFDB / batidas e marcadores)

Os significados clínicos seguem a convenção WFDB / MIT-BIH; consulte o [WFDB Programmer's Guide — Annotation Codes](https://archive.physionet.org/physiotools/wpg/wpg_36.htm) e o [diretório MIT-BIH](https://www.physionet.org/physiobank/database/html/mitdbdir/).

| Símbolo | Coluna | Significado (resumo) |
|---------|--------|----------------------|
| N | `ann_sym_N` | Batimento normal |
| L | `ann_sym_L` | Bloqueio de ramo esquerdo |
| R | `ann_sym_R` | Bloqueio de ramo direito |
| B | `ann_sym_B` | Bloqueio de ramo indefinido |
| A | `ann_sym_A` | Extrassístole atrial |
| a | `ann_sym_a` | Extrassístole atrial aberrante |
| J | `ann_sym_J` | Extrassístole nodal (nodal prematura) |
| S | `ann_sym_S` | Extrassístole supraventricular |
| V | `ann_sym_V` | Extrassístole ventricular (PVC) |
| r | `ann_sym_r` | PVC tipo R-on-T |
| F | `ann_sym_F` | Fusão de batimento normal e ventricular |
| e | `ann_sym_e` | Escape atrial |
| j | `ann_sym_j` | Escape nodal |
| E | `ann_sym_E` | Escape ventricular |
| / | `ann_sym_SLASH` | Batimento marcado (paced) |
| f | `ann_sym_f` | Fusão de batimento marcado e normal |
| x | `ann_sym_x` | Onda P não conduzida |
| Q | `ann_sym_Q` | Batimento não classificável |
| \| | `ann_sym_PIPE` | Artefacto / onda tipo QRS isolada (não batimento) |
| + | `ann_sym_PLUS` | Ritmo (início de mudança de ritmo; contexto aux) |
| ~ | `ann_sym_TILDE` | Sinal isorrítmico |
| [ | `ann_sym_LBRACKET` | Início de flutter/fibrilação ventricular |
| ] | `ann_sym_RBRACKET` | Fim de flutter/fibrilação ventricular |
| ! | `ann_sym_EXCLAIM` | Onda de flutter ventricular |

**Nota:** `+` e mudanças de ritmo detalhadas aparecem frequentemente em conjunto com texto em `aux_note`; as colunas `aux_rhy_*` tratam sobretudo desse texto.

---

## Ruído e artefactos (Bloco E)

### Tipos considerados

Em ECG real surgem com frequência, entre outros: **baseline wander** (baixa frequência), **interferência de rede (PLI)** em 50 ou 60 Hz, **ruído muscular (EMG)** em altas frequências e **artefactos de movimento de elétrodo** (transientes e saltos). Uma síntese clínica em [Main artifacts in electrocardiography (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6931710/).

### O que o script calcula

São **indicadores heurísticos** no domínio tempo–frequência (Welch via `scipy.signal.welch`), **não** um laudo de qualidade clínica certificada.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `noise_analysis_ok` | bool | `True` se pelo menos uma janela válida foi analisada. |
| `noise_analysis_error` | string | `skipped` com `--skip-noise`; `triplet_incomplete`; `header_missing_or_invalid_fs`; `no_windows`; mensagem curta em caso de excepção ao ler o sinal. |
| `noise_score_bw` | float 0–1 | Baseline / baixa frequência: energia 0,05–0,8 Hz vs banda 5–40 Hz, mapeada com `tanh(log1p(ratio)/3)`. |
| `noise_score_pli` | float 0–1 | Energia estreita em `pli_hz` ± 1 Hz vs bandas de referência adjacentes (`tanh(log1p(ratio)/2.5)`). |
| `noise_score_emg` | float 0–1 | Energia 40 Hz–min(90 Hz, Nyquist−1) vs banda 5–40 Hz (`tanh(log1p(ratio)/3)`). Com `fs=360` Hz o Nyquist é 180 Hz; acima de ~80 Hz a resolução espectral é limitada. |
| `noise_score_motion` | float 0–1 | Combinação de percentil 99 de `\|diff(x)\|` vs mediana e fração de amostras fora de 5×MAD robusto. |
| `noise_flag_bw` | bool | `noise_score_bw > 0.35` |
| `noise_flag_pli` | bool | `noise_score_pli > 0.25` |
| `noise_flag_emg` | bool | `noise_score_emg > 0.22` |
| `noise_flag_motion` | bool | `noise_score_motion > 0.35` |
| `noise_primary_label` | string | `bw`, `pli`, `emg`, `motion`, `none` (se todos os escores < 0,08), ou `mixed` (segundo maior escore ≥ 0,85× o máximo). |
| `noise_windowing_policy` | string | Resumo textual (número de janelas, amostras por janela, `pli_hz`, ou `skip-noise`). |

**Agregação:** por janela e por canal calculam-se escores; o valor do registo é o **máximo** entre todos os canais e janelas (cenário “pior caso” na amostragem).

**Cruzamento com anotações:** `ann_sym_PIPE` conta marcadores WFDB de artefacto; não coincide necessariamente com `noise_score_pli` ou `noise_score_emg`, mas pode correlacionar.

### Limitações

- EMG e movimento partilham bandas e morfologias; os escores são **proxies**.
- Harmónicos do QRS podem elevar falsamente o indicador de PLI.
- Janelas esparsas podem falhar segmentos muito ruidosos ou muito limpos noutras partes do registo.
- Com `--noise-full-record`, o cálculo reflecte o espectro global, mais estável mas mais pesado.

---

## Referências

1. Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng Med Biol 20(3):45-50 (May-June 2001).

2. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000;101(23):e215-e220.

3. MIT-BIH Arrhythmia Database 1.0.0. PhysioNet. https://physionet.org/content/mitdb/1.0.0/

4. WFDB Programmer's Guide — Annotation codes. https://archive.physionet.org/physiotools/wpg/wpg_32.htm#Annotation-Codes

5. Goldberger A, et al. Main artifacts in electrocardiography. Biomed Eng Online (2020). https://pmc.ncbi.nlm.nih.gov/articles/PMC6931710/
