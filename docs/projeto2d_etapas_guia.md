# Guia da Etapa 2: Conteúdo Esperado em Cada Tópico

Este guia resume o que cada etapa do arquivo `docs/Projeto 2/projeto2d.pdf` deve conter no notebook e no artigo final. O objetivo é transformar o enunciado em uma sequência reproduzível de análise de ECG usando a base MIT-BIH.

## 1. Introdução

Deve apresentar o ECG como sinal biomédico unidimensional e explicar por que ele é adequado para Processamento Digital de Sinais. A introdução deve conectar o problema clínico com as técnicas do projeto: filtragem FIR, convolução no tempo, convolução rápida por FFT, filtros de Gabor 1D, análise tempo-frequência e classificação.

## 2. Base de Dados

Deve descrever a MIT-BIH Arrhythmia Database, sua origem no PhysioNet, a frequência de amostragem, os canais disponíveis e as anotações de batimentos. Também deve justificar quais registros serão usados e qual será a unidade de análise: registro completo, janela temporal ou batimento segmentado.

## 3.1 Inspeção Inicial do ECG e Caracterização do Problema

Deve conter a visualização do ECG bruto, a identificação visual das ondas P, complexo QRS e onda T, a frequência de amostragem e as fontes prováveis de ruído. Também deve justificar a janela de análise usada no notebook. Nenhum parâmetro deve ser escolhido sem justificativa fisiológica ou espectral.

## 3.2 Pré-processamento e Filtragem FIR

Deve aplicar o pré-processamento necessário, como remoção de média, normalização quando apropriada e filtragem FIR. É obrigatório justificar a ordem do filtro, as frequências de corte, a janela ou método de projeto e o impacto esperado sobre a morfologia do QRS. Para ECG diagnóstico, a filtragem deve remover ruídos sem deslocar ou deformar de modo relevante os picos R.

## 3.3 Convolução no Domínio do Tempo

Deve implementar explicitamente a convolução discreta no domínio do tempo, sem reduzir a etapa ao uso direto de uma biblioteca. A saída deve ser comparada visualmente com o sinal original ou pré-processado, destacando a preservação dos picos R e das estruturas do ECG.

## 3.4 Convolução Rápida no Domínio da Frequência

Deve reproduzir a mesma filtragem usando FFT: calcular a FFT do sinal, calcular a FFT do filtro, multiplicar os espectros e retornar ao tempo com IFFT. É essencial discutir o uso de zero-padding, pois sem ele a operação vira convolução circular, não convolução linear. A equivalência deve ser verificada numericamente, por exemplo com MSE.

## 3.5 Banco de Filtros de Gabor 1D

Deve implementar um banco de filtros de Gabor 1D variando frequência central `f0`, largura gaussiana `sigma` e escala. A análise deve explicar por que valores próximos de 10 a 25 Hz são úteis para o complexo QRS e por que `sigma` controla o compromisso entre localização temporal e seletividade espectral. Para detectar R, Q e S, o notebook deve comparar configurações mais largas, que respondem ao QRS inteiro, com configurações mais estreitas, que separam melhor as deflexões Q e S ao redor do pico R.

## 3.6 Análise do Espectro de Potência Tempo-Frequência

Deve apresentar o espectrograma por STFT como uma superfície bidimensional de potência, não apenas como imagem. A análise deve interpretar onde a energia se concentra, como o QRS aparece no plano tempo-frequência e como a filtragem altera o espalhamento espectral. Também deve incluir descritores quantitativos, como energia por banda, centroide espectral e largura de banda efetiva.

## 3.7 Extração de Características

Deve construir vetores de características a partir do ECG filtrado, das respostas de Gabor e do espectrograma. Cada atributo deve ter justificativa técnica. Exemplos úteis são amplitude do R, amplitudes Q e S, energia da janela do batimento, largura aproximada do QRS, energia de Gabor em diferentes escalas, centroide espectral e energia em bandas específicas.

## 3.8 Classificação

Deve formular uma tarefa simples e interpretável, preferencialmente normal versus anômalo ou classificação entre tipos de batimento anotados. A divisão entre treino e teste deve ser explícita. A conclusão não pode se apoiar apenas em inspeção visual ou em desempenho calculado no mesmo conjunto usado para ajuste.

## 4. Avaliação dos Resultados

Deve reunir métricas quantitativas para validar o pipeline. O PDF recomenda MSE entre convolução temporal e convolução por FFT, estimativas de SNR ou atenuação de ruído quando possível, erro percentual da amplitude do pico R, descritores do espectrograma, acurácia, precisão, revocação, F1, matriz de confusão e análise de robustez para diferentes parâmetros.

## 5. Trabalho Final em Formato de Artigo Científico

O artigo final deve conter título, resumo, introdução, materiais e métodos, resultados, discussão, conclusão e referências. A escrita deve ser impessoal, objetiva e tecnicamente fundamentada, com figuras e tabelas reprodutíveis.
