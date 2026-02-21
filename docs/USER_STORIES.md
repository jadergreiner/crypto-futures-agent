# 📖 User Stories — Crypto Futures Agent

## v0.2 — Pipeline Fix

### US-01: Integrar Multi-Timeframe no Observation Vector ✅ DONE

**Como** desenvolvedor, **quero** que o `build_observation` consuma o
`multi_tf_result` **para que** os Blocos 7 (Correlação BTC) e 8 (D1 Bias/Regime)
tenham valores reais em vez de placeholders.

**Critérios de aceite:**

- `build_observation` aceita parâmetro `multi_tf_result` ✅
- Bloco 7: `btc_return`, `correlation_btc`, `beta_btc` preenchidos ✅
- Bloco 8: `d1_bias` mapeado para -1/0/1, `market_regime` mapeado para -1/0/1 ✅
- Dry-run mostra valores não-zero nos blocos 7 e 8 ✅

### US-02: Fix Bug R-Multiple no Reward Calculator ✅ DONE

**Como** desenvolvedor, **quero** corrigir o bug da lógica de R-multiple no
`RewardCalculator` **para que** bonus de 3R+ funcione corretamente.

**Critérios de aceite:**

- `if r_multiple > 3.0` vem antes de `elif r_multiple > 2.0` ✅
- Teste unitário validando ambos os cenários ✅

### US-03: Sincronizar Feature Names ✅ DONE

**Como** desenvolvedor, **quero** que `get_feature_names()` esteja 100%
sincronizado com `build_observation()` **para** debugging confiável.

## v0.3 — Training Ready

### US-04: Episódio Completo de Treinamento

**Como** agente, **quero** executar um episódio completo de treinamento (reset →
N steps → done) com dados históricos reais **para** aprender padrões de mercado.

**Critérios de aceite:**

- `env.reset()` retorna observation válida de 104 features
- `env.step(action)` retorna (obs, reward, done, truncated, info)
- Episódio termina após `episode_length` steps ou capital < 50% do inicial
- Modelo PPO treina por pelo menos 100k steps sem erro

### US-05: Salvar e Carregar Modelos

**Como** desenvolvedor, **quero** salvar e carregar modelos treinados **para**
iterar sem retreinar do zero.

## v0.4 — Backtest

### US-06: Backtest com Métricas Reais

**Como** trader, **quero** executar um backtest sobre dados históricos reais e
ver métricas de performance **para** validar se o modelo é rentável.

**Critérios de aceite:**

- `python main.py --backtest --start-date 2025-01-01 --end-date 2025-12-31`
- Output: total trades, win rate, Sharpe, max drawdown, profit factor
- Gráfico de equity curve salvo como PNG

## v0.5 — Paper Trading

### US-07: Operação Autônoma em Paper Mode

**Como** trader, **quero** rodar o agente em modo paper 24/7, observando
decisões e PnL simulado, **para** validar antes de arriscar capital real.

## v1.0 — Live

### US-08: Execução Real com Proteções

**Como** trader, **quero** que o agente execute ordens reais na Binance Futures
com proteções (max drawdown, max posições, circuit breaker) **para** operar de
forma segura.
