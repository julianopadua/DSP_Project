# Dicionário de dados: MIT-BIH e arquivos WFDB

Este projeto utiliza a **MIT-BIH Arrhythmia Database** da PhysioNet. Os registos seguem o formato **WFDB** (Waveform Database), comum na PhysioNet.

## Origem da base

- **Página:** [MIT-BIH Arrhythmia Database 1.0.0](https://physionet.org/content/mitdb/1.0.0/)
- **Descarregamento ZIP:** [get-zip 1.0.0](https://physionet.org/content/mitdb/get-zip/1.0.0/)
- **Tamanho descomprimido:** cerca de 104,3 MB (segundo a PhysioNet).
- **Tamanho do ZIP:** cerca de 73,5 MB.
- **Conteúdo:** 48 trechos de meia hora de ECG ambulatorial em dois canais de 47 sujeitos; frequência de amostragem **360 Hz** por canal; resolução de 11 bits num intervalo de **10 mV** (conforme a PhysioNet).

A ingestão está implementada em `src.data.download_dataset` e os caminhos em `src.config`.

## Tipos de arquivos WFDB

### Arquivo de cabeçalho (`.hea`)

Texto simples. Descreve a gravação: número de sinais, frequência de amostragem, calibração, ganho, formato de cada canal, nomes dos arquivos binários de sinal e outros metadados. Pode ser lido em editor; bibliotecas como `wfdb` utilizam-no para descodificar o `.dat` correspondente.

### Arquivo de sinal (`.dat`)

Arquivo binário com amostras da forma de onda. **Não** é texto simples. Utilize a biblioteca compatível com WFDB (no caso, `wfdb`).

### Arquivo de anotação (`.atr`)

Arquivo binário de anotações. Etiquetas produzidas por clínico ou algoritmo, alinhadas a amostras (por exemplo tipos de batimento, alterações de ritmo). Na MIT-BIH, as anotações de referência de batimento carregam-se frequentemente com extensão `atr` via `wfdb.rdann`. Utilize `wfdb` para descodificar; não trate como texto.

- Após o download, os arquvivos WFDB ficam armazenados em `data/raw/mit-bih-arrhythmia-database-1.0.0`.

## Referências 

1. Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. IEEE Eng Med Biol 20(3):45-50 (May-June 2001).

2. Goldberger AL, Amaral LAN, Glass L, et al. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. Circulation. 2000;101(23):e215-e220.
