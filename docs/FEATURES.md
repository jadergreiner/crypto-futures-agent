# 🧩 Features — Crypto Futures Agent

**Versão Atual:** v1.0-alpha (PHASE 4 Operacionalização)
**Status:** 🟢 GO-LIVE EM PROGRESSO (22 FEV 2026)
**Última Atualização:** 22 FEV 2026, 00:30 UTC (Decision #3 + TASK-001 iniciada)

---

## v1.0-alpha — PHASE 4 Operacionalização (22 FEV - ATUAL)

| ID | Feature | Prioridade | Status | TASK | Deadline |
|----|---------|-----------|--------|------|----------|
| **F-H1** | Heurísticas Conservadoras (SMC + EMA + RSI) | 🔴 CRÍTICA | 🔄 IN PROGRESS | TASK-001 | 22 FEV 06:00 |
| **F-H2** | Order Block Detection & Validation | 🔴 CRÍTICA | 🔄 IN PROGRESS | TASK-001 | 22 FEV 06:00 |
| **F-H3** | Fair Value Gap (FVG) Mapping | 🔴 CRÍTICA | 🔄 IN PROGRESS | TASK-001 | 22 FEV 06:00 |
| **F-H4** | Multi-Timeframe Alignment (D1→H4→H1) | 🔴 CRÍTICA | 🔄 IN PROGRESS | TASK-001 | 22 FEV 06:00 |
| **F-H5** | Risk Gates (Drawdown -5%, Circuit -3%) | 🔴 CRÍTICA | 🔄 IN PROGRESS | TASK-001 | 22 FEV 06:00 |

### Próximas Features (Paralelo PPO)

| ID | Feature | Prioridade | Status | TASK | Deadl ine |
|----|---------|-----------|--------|------|----------|
| **F-ML1** | PPO Training Pipeline | 🔴 CRÍTICA | ⏳ WAITING | TASK-005 | 25 FEV 10:00 |
| **F-ML2** | Model Convergence Validation | 🔴 CRÍTICA | ⏳ WAITING | TASK-006 | 25 FEV 14:00 |
| **F-ML3** | Live Model Deployment | 🔴 CRÍTICA | ⏳ WAITING | TASK-007 | 25 FEV 20:00 |

---

## v0.3 — Training Ready (CONCLUÍDO)

| ID | Feature | Prioridade | Status |
|----|---------|-----------|--------|
| F-06 | Implementar `step()` completo no `CryptoFuturesEnv` | 🔴 CRÍTICA | ✅ DONE |
| F-07 | Implementar `_get_observation()` usando `FeatureEngineer` | 🔴 CRÍTICA | ✅ DONE |
| F-08 | Pipeline de dados para treinamento | 🔴 CRÍTICA | ✅ DONE |
| F-09 | Script de treinamento funcional | 🔴 CRÍTICA | ✅ DONE |
| F-10 | Teste E2E de pipeline completo | 🔴 CRÍTICA | ✅ DONE |
| F-11 | Reward shaping refinado | 🟡 ALTA | ✅ DONE |
| F-13 | Orchestrator paralelo | 🔴 CRÍTICA | ✅ DONE |
| F-14 | Monitor crítico com health checks | 🔴 CRÍTICA | ✅ DONE |
| F-15 | Autorização formal (AUTHORIZATION_OPÇÃO_C_20FEV.txt) | 🔴 CRÍTICA | ✅
DONE (20/02 20:30) |

## v0.4 — Backtest Engine (21-24/02/2026)

| ID | Feature | Prioridade | Status | Detalhes |
|----|---------|-----------|--------|----------|
| F-12 | Backtester funcional com 6 métricas + Risk Clearance | 🔴 CRÍTICA | 🔄 IN PROGRESS (60%) | Sharpe≥1.0, DD≤15%, WR≥45%, PF≥1.5, Calmar≥2.0, CL≤5 |
| F-12a | BacktestEnvironment (subclasse CryptoFuturesEnv) | 🔴 CRÍTICA | ✅ DONE (21/02) | Determinístico, herança 99%, 168L |
| F-12b | Data pipeline 3-camadas (cache Parquet) | 🔴 CRÍTICA | 🔄 IN PROGRESS (22/02) | 6-10x mais rápido, iniciando amanhã |
| F-12c | TradeStateMachine (IDLE/LONG/SHORT) | 🔴 CRÍTICA | ✅ DONE (21/02) | Estados + PnL/fees exatos, 205L |
| F-12d | BacktestMetrics Reporter (JSON+text) | 🔴 CRÍTICA | ✅ DONE (21/02) | 6 métricas GO/NO-GO, 345L |
| F-12e | 8 unit tests (core coverage) | 🔴 CRÍTICA | 🔄 5/8 PASSING (21/02) | 3 testes bloqueados, resolved 22 FEV |
| F-13 | Walk-forward com janelas train/test | 🟡 ALTA | ⏳ Após F-12 | Valida
retreinamento incremental (v0.4.1) |
| F-14 | Métricas extras (Sortino, Calmar) | 🟡 ALTA | ⏳ Após F-12 | Análise mais
profunda |
| F-15 | Equity curve plot com matplotlib | 🟡 ALTA | ⏳ Após F-12 | Visualização
de performance |

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
