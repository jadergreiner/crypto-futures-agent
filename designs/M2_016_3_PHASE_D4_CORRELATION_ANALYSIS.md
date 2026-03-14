# M2-016.3 Phase D.4 - Analise de Correlacao FR/OI vs Performance RL

**Status**: CONCLUIDA (2026-03-14)
**Commit**: TBD
**Evidencias**: `results/model2/analysis/phase_d4_correlation_*.json`

## Objetivo

Analisar correlacoes entre dados de funding rates (FR) e open interest (OI) 
coletados na Phase D.3 com a performance do modelo RL (labels e rewards).

Objetivo secundario: Identificar leverage points para tuning de reward function.

## Metodologia

### 1. Carregamento de Episodes
- Fonte: `training_episodes` table (Phase D.3, com features enriched)
- Total: 100 episodes sinteticos com correlacoes realistas
- Estructura: `{label, reward_proxy, features:{funding_rates, open_interest}}`

### 2. Analises Realizadas

#### A. FR SENTIMENT vs LABEL (WIN/LOSS)

Pergunta: "Sinais com FR bullish tem maior taxa de win?"

Metodo:
- Mapear sentimento FR (bullish=+1, neutral=0, bearish=-1)
- Mapear label (win=+1, loss=-1, breakeven=0)
- Correlacao de Pearson (r) + p-value
- Analise por sentimento: % wins, n_episodes, avg_reward

**Resultados**:
- Pearson r: 0.2738 (fraca positiva, p=0.0058 significante)
- Win rates:
  - bullish: 25.81% (n=31)
  - neutral: 37.14% (n=35)
  - bearish: 0.00% (n=34)
- Insight: FR bearish muito preditivo para LOSS (0% win rate)
  FR bullish NAO aumenta win rate (contra intuicao)

#### B. FR TREND vs REWARD (PROXY)

Pergunta: "FR crescente (increasing trend) correlaciona com maior reward?"

Metodo:
- Mapear trend (increasing=+1, stable=0, decreasing=-1)
- Correlacao com numeriko reward_proxy
- Analise por trend: avg_reward, std, min/max

**Resultados**:
- Pearson r: 0.0880 (muito fraca, p=0.3842 NAO significante)
- Avg rewards:
  - increasing: -0.1568 (n=34)
  - stable: -0.1972 (n=43)
  - decreasing: -0.2891 (n=23)
- Insight: FR trend NAO prediz reward (sinal ruido?)
  Rewards sao consistentemente negativos (problema na reward fn ou dados?)

#### C. OI SENTIMENT vs LABEL

Pergunta: "OI accumulating correlaciona com wins?"

Metodo:
- Mapear sentimento OI (accumulating=+1, neutral=0, distributing=-1)
- Correlacao com label
- Analise por sentimento: % wins

**Resultados**:
- Problema: Todas as 100 amostras sao OI neutral
- Pearson r: nan (cannot compute, constant input)
- Insight: Dados sinteticos nao tem variacao OI suficiente

## Recomendacoes Geradas

1. **[WARNING] Win rate baixo (<40%)**
   - Acao: Aumentar reward para winners, investigar FR bullish/OI acc, revisar SL/TP

2. **[INFO] Reward media negativa**
   - Acao: Aumentar reward para winners ou reduzir penalidade para losers

3. **[DATA] Apenas 100 episodes**
   - Acao: Coletar 100+ episodes para significancia estatistica

## Limitacoes

1. **Dados Sinteticos**: Correlacoes forcadas, nao refletem realidade
2. **OI Sentiment**: Nao varia (sempre neutral nos dados simulados)
3. **Sample Size**: 100 < 300 ideal para Pearson com p < 0.01
4. **Lookback Period**: FR trend calculado com historico curto (pode nao capturar ciclos)

## Proximas Etapas (Phase D.5 ou E)

1. Coletar 500+ episodes reais de trade (do M2-016.2 em background)
2. Recalcular correlacoes com dados reais (nao sinteticos)
3. Se correlacoes >0.5 (moderadas), fazer A/B test:
   - Model A: Weights atuais
   - Model B: Weights ajustados baseado em correlacoes
   - Compare Sharpe ratio, Win rate, Max drawdown
4. Se A/B favoravel, fazer rollout gradual

## Deliverables

- `scripts/model2/phase_d4_correlation_analysis.py`: Script analise
- `scripts/model2/test_phase_d4_synthetic_data.py`: Gerador dados teste
- `results/model2/analysis/phase_d4_correlation_*.json`: Relatorio JSON
- Este documento: Spec + insights

## Conclusao

Phase D.4 validou a pipeline de analise de correlacoes mas com dados sinteticos.
Proximalidades proximas sao: (1) coletar dados reais, (2) validar correlacoes,
(3) tunar reward function baseado em insights.

Sistema pronto para Phase E (LSTM) ou D.5 (Real data correlation).
