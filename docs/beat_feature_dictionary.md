# Dicionário de Features por Batimento

## Visão Geral

Cada linha do arquivo `data/processed/mitdb_beat_features.csv` representa um batimento segmentado da base MIT-BIH Arrhythmia Database. A janela é centrada na anotação do batimento e cobre aproximadamente `0.25 s` antes da anotação e `0.45 s` depois dela. Essa escolha mantém a região do complexo QRS no centro e ainda preserva trechos nos quais ondas P e T podem aparecer.

O objetivo do dataset é diferenciar batimentos normais e anômalos em uma tarefa binária simples. O conjunto de atributos foi mantido pequeno para facilitar a explicação do método na apresentação.

## Rótulo

`ann_symbol` é o símbolo original da anotação MIT-BIH. Neste projeto, apenas símbolos que representam batimentos entram no dataset. Marcadores de ruído, mudança de ritmo ou eventos técnicos são descartados.

`label_binary` é o rótulo binário usado na modelagem. O símbolo `N` recebe rótulo `0`, interpretado como normal. Os demais símbolos válidos de batimento recebem rótulo `1`, interpretado como anômalo. Essa é uma simplificação experimental: o objetivo não é diagnosticar o tipo exato de arritmia, mas separar batimentos normais de batimentos que fogem do padrão normal.

## Features Morfológicas

### r_amp

Amplitude do sinal filtrado exatamente na amostra anotada do batimento. Ela vem da região central do QRS, pois a anotação MIT-BIH normalmente está próxima do pico R. Essa feature mede a intensidade local do batimento. Pode ajudar porque alguns batimentos anômalos possuem amplitude diferente dos batimentos normais. Sua limitação é depender da qualidade da anotação e da escala do canal.

### beat_peak_to_peak

Diferença entre o maior e o menor valor dentro da janela do batimento. Ela usa toda a janela segmentada. Mede a excursão total de amplitude do batimento. Pode ajudar a identificar morfologias com QRS mais largo, mais profundo ou mais alto. A limitação é que ruído residual ou deslocamentos de linha de base podem aumentar esse valor.

### beat_energy

Soma dos quadrados das amostras da janela filtrada. Ela mede a energia total do batimento no domínio do tempo. Batimentos com morfologia mais intensa, larga ou irregular tendem a apresentar energia diferente. A limitação é que a feature não diz em qual parte da janela a energia ocorreu.

### beat_abs_area

Soma dos valores absolutos das amostras da janela. Ela aproxima a área total do batimento sem cancelar partes positivas e negativas. Pode ajudar quando a forma do QRS muda de polaridade ou quando há alterações mais distribuídas no trecho. Sua limitação é ser sensível ao tamanho da janela e à amplitude global do sinal.

### beat_std

Desvio-padrão das amostras da janela. Mede a variabilidade da amplitude dentro do batimento. Batimentos com transições fortes ou morfologia mais irregular podem ter maior desvio-padrão. A limitação é que ela mistura variações fisiológicas e ruído.

### max_slope

Maior valor absoluto da primeira diferença do sinal dentro da janela. Funciona como uma aproximação da rapidez das transições, especialmente no complexo QRS. Pode ajudar porque batimentos anômalos podem ter subidas e descidas diferentes das normais. A limitação é ser sensível a ruído de alta frequência.

## Features Rítmicas

### rr_prev_s

Intervalo, em segundos, entre o batimento atual e o batimento anterior do mesmo registro. Essa feature vem da sequência de anotações. Mede o ritmo local antes do batimento. Pode ajudar porque batimentos ectópicos e padrões irregulares frequentemente alteram o intervalo RR. A limitação é que ela depende do contexto temporal, não apenas da morfologia do batimento.

### rr_next_s

Intervalo, em segundos, entre o próximo batimento e o batimento atual. Mede o ritmo local depois do batimento. Pode ajudar a capturar pausas compensatórias ou irregularidades após batimentos anômalos. A limitação é que o último batimento de uma sequência não pode usar essa feature, então batimentos sem vizinho posterior são descartados.

### rr_ratio

Razão `rr_prev_s / rr_next_s`, com proteção contra divisão por zero. Mede assimetria no ritmo ao redor do batimento. Valores próximos de 1 indicam ritmo local mais regular. Valores distantes de 1 podem sugerir irregularidade. A limitação é que alterações de ritmo normal também podem afetar essa razão.

## Features de Gabor

As features de Gabor usam respostas locais de filtros 1D em regiões fisiológicas aproximadas do batimento. O método realça padrões locais, mas não deve ser interpretado como detecção clínica precisa de ondas P, QRS e T.

### p_gabor_energy

Energia da resposta de Gabor na janela relativa da onda P, entre `-0.22 s` e `-0.08 s` antes da anotação. Mede a presença de estrutura oscilatória suave antes do QRS. Pode ajudar porque alterações de condução e ritmo podem modificar ou dificultar a presença da onda P. A limitação é que a posição real da onda P varia entre batimentos.

### qrs_gabor_energy

Energia da resposta de Gabor na janela do QRS, entre `-0.06 s` e `+0.08 s`. Mede a concentração de energia em uma resposta ajustada para transições rápidas. Pode ajudar porque o QRS é uma das partes mais informativas para distinguir morfologias normais e anômalas. A limitação é que energia alta não identifica sozinha o tipo de alteração.

### t_gabor_energy

Energia da resposta de Gabor na janela aproximada da onda T, entre `+0.12 s` e `+0.36 s`. Mede padrões mais lentos após o QRS. Pode ajudar porque mudanças de repolarização podem alterar a região da onda T. A limitação é que a onda T pode ser pequena, sobreposta a ruído ou deslocada temporalmente.

### qrs_gabor_max

Maior valor da resposta de Gabor dentro da janela QRS. Mede o ponto de maior compatibilidade entre o sinal e o filtro de Gabor ajustado ao QRS. Pode ajudar a comparar a força relativa do complexo QRS entre batimentos. A limitação é que um único máximo pode ser afetado por ruído local.

### qrs_gabor_peak_offset_ms

Distância, em milissegundos, entre a anotação do batimento e o ponto de máximo da resposta de Gabor na janela QRS. Mede se a maior resposta local está alinhada com a anotação. Pode ajudar a identificar morfologias deslocadas ou QRS mais assimétricos. A limitação é que pequenas diferenças podem refletir apenas variação da anotação.

## Features Espectrais

### spectral_centroid_hz

Centroide espectral da janela do batimento, calculado a partir da densidade espectral estimada por Welch. Mede a frequência média ponderada pela potência. Pode ajudar porque batimentos com transições mais rápidas tendem a deslocar energia para frequências mais altas. A limitação é que a janela curta reduz a resolução espectral.

### spectral_bandwidth_hz

Largura de banda efetiva ao redor do centroide espectral. Mede o espalhamento da energia em frequência. Pode ajudar porque batimentos mais abruptos ou ruidosos podem ter espectro mais espalhado. A limitação é que ruído residual também aumenta a largura de banda.

### qrs_band_power_8_20

Potência estimada na banda de `8 Hz` a `20 Hz`. Essa faixa está associada a componentes rápidas do complexo QRS. Pode ajudar a separar batimentos com QRS normal de morfologias mais largas ou alteradas. A limitação é que a faixa é uma aproximação e pode variar entre registros.

### high_band_power_20_40

Potência estimada na banda de `20 Hz` a `40 Hz`. Mede componentes ainda mais rápidas, que podem aparecer em transições abruptas, alterações morfológicas ou ruído muscular. Pode ajudar na separação binária, mas deve ser interpretada com cuidado porque nem toda potência alta nessa banda é fisiológica.

## Modelos Avaliados

### SVM Supervisionada

A SVM supervisionada recebe exemplos normais e anômalos no treinamento e aprende uma fronteira entre as duas classes. O parâmetro `class_weight="balanced"` não balanceia o dataset. Ele apenas aumenta o peso dos erros na classe minoritária, o que ajuda em problemas desbalanceados.

### One-Class SVM

A One-Class SVM é treinada apenas com batimentos normais. Ela aprende uma região de normalidade e marca como anômalos os batimentos que se afastam dessa região. Essa abordagem é útil quando há poucos exemplos anômalos ou quando se deseja modelar o padrão normal.

## Métricas

### accuracy

Proporção total de acertos. Deve ser reportada, mas não deve ser a métrica principal, porque o dataset é desbalanceado e muitos acertos podem vir apenas da classe normal.

### precision

Entre os batimentos previstos como anômalos, mede quantos realmente eram anômalos. É importante quando falsos alarmes precisam ser controlados.

### recall

Entre os batimentos realmente anômalos, mede quantos foram encontrados pelo modelo. É importante quando perder anomalias é um problema.

### f1-score

Média harmônica entre precision e recall. Ajuda a resumir o equilíbrio entre encontrar anomalias e evitar falsos alarmes.

### ROC-AUC

Mede a separação geral entre classes ao variar o limiar de decisão. Pode ser útil, mas deve ser interpretada com cautela em dados desbalanceados.

### PR-AUC

Área sob a curva Precision-Recall. É especialmente relevante neste projeto porque a classe anômala é minoritária. Por isso, PR-AUC, precision, recall e F1 são mais informativas que accuracy isolada.
