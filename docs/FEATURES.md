# 🧩 Features — Crypto Futures Agent

## v0.2 — Pipeline Fix

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-01 | Integrar `multi_tf_result` no `build_observation` (Blocos 7 e 8) | 🔴 CRÍTICA |
| F-02 | Adicionar FVG distance features (indices 13-14 do SMC estão mapeados para sweeps, não FVGs) | 🟡 ALTA |
| F-03 | Fix bug no `RewardCalculator` — lógica `r_multiple > 3.0` nunca é atingida (elif após if > 2.0) | 🟡 ALTA |
| F-04 | Validar `get_feature_names()` vs `build_observation()` — contagem dos nomes não bate 100% | 🟡 ALTA |
| F-05 | Testes unitários para cada bloco de features | 🟢 MÉDIA |

## v0.3 — Training Ready

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-06 | Implementar `step()` completo no `CryptoFuturesEnv` | 🔴 CRÍTICA |
| F-07 | Implementar `_get_observation()` usando `FeatureEngineer` | 🔴 CRÍTICA |
| F-08 | Pipeline de dados para treinamento (carregar do DB → DataFrames) | 🔴 CRÍTICA |
| F-09 | Script de treinamento funcional (`python main.py --train`) | 🔴 CRÍTICA |
| F-10 | Reward shaping refinado com curriculum learning | 🟡 ALTA |
| F-11 | Salvar/carregar modelo treinado | 🟢 MÉDIA |

## v0.4 — Backtest Engine

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-12 | Backtester real iterando sobre dados históricos | 🔴 CRÍTICA |
| F-13 | Métricas: Sharpe, Sortino, MaxDD, Win Rate, Profit Factor | 🔴 CRÍTICA |
| F-14 | Equity curve plot com matplotlib | 🟡 ALTA |
| F-15 | Walk-forward com janelas de train/test | 🟡 ALTA |
| F-16 | Relatório de backtest em texto/HTML | 🟢 MÉDIA |

## v0.5 — Paper Trading

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-17 | Scheduler operacional com ciclos H4 | 🔴 CRÍTICA |
| F-18 | Execução simulada (paper) com tracking de PnL | 🔴 CRÍTICA |
| F-19 | Logs estruturados de cada decisão | 🟡 ALTA |
| F-20 | Dashboard simples em terminal (posições, PnL, sinais) | 🟢 MÉDIA |

## v1.0 — Live MVP

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-21 | Execução real de ordens via Binance SDK | 🔴 CRÍTICA |
| F-22 | Circuit breaker (pause se drawdown > 10%) | 🔴 CRÍTICA |
| F-23 | Validação dupla antes de cada ordem | 🔴 CRÍTICA |
| F-24 | Alertas (arquivo de log ou webhook simples) | 🟡 ALTA |
| F-25 | Capital inicial limitado (micro-posições) | 🟡 ALTA |
