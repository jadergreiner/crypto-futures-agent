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

---

## F-ML1: PPO Training Pipeline — Teoria & Implementação (Consolidado Fase 2A)

**Status:** 🟢 SPECIFICATION COMPLETE (22 FEV)
**Responsável:** The Brain (ML Specialist)
**Implementação:** TASK-005 (22-25 FEV)

### Reward Function — Matemática Completa

O agente tenta maximizar a recompensa descontada cumulativa:

$$G_t = \sum_{k=0}^{\infty} \gamma^k r_{t+k}$$

Onde: $\gamma = 0.99$ (discount factor), $r_t$ = reward instant no step $t$

#### Componente 1: Realized PnL Reward

**Trigger:** Trade fecha (SL, TP, close manual)

$$r_{pnl} = \frac{\text{pnl\_realized}}{capital_t} \times 10.0 + \text{r\_bonus}$$

$$\text{r\_bonus} = \begin{cases}
+1.0 & \text{if } R_{multiple} > 3.0 \\
+0.5 & \text{if } 2.0 < R_{multiple} \leq 3.0 \\
0.0 & \text{else}
\end{cases}$$

**Exemplo:** Trade entrada $40k, SL $39k, TP $43k → R-multiple=3 → r_pnl = +1.3

#### Componente 2: Hold Bonus (Assimétrico)

**Trigger:** Cada step enquanto posição aberta

$$r_{hold} = \begin{cases}
+0.05 + \text{pnl\_pct} \times 0.1 + 0.05 \times \text{momentum} & \text{se } \text{pnl\_pct} > 0 \\
-0.02 & \text{se } \text{pnl\_pct} \leq 0
\end{cases}$$

**Rationale:** Winners recebem momentum bonus; losers recebem patience bonus (permitir recuperação).

#### Componente 3: Drawdown Penalty

**Trigger:** Cada step, agregado todas posições abertas

$$r_{dd} = \max\left(-1.0, -0.2 \times \frac{\text{current\_dd}}{0.05}\right)$$

**Penalidade:**
- DD 0% a -1%: penalty 0 (normal)
- DD -1% a -5%: escalação linear (-0.04 a -0.20)
- DD < -5%: episode termina (-1.0 hard stop)

#### Componente 4: Win Rate Bonus

**Trigger:** A cada 50 steps (rolling window)

$$r_{wr} = \begin{cases}
+0.3 & \text{if } \text{WR}_{50} > 52\% \\
-0.1 & \text{if } \text{WR}_{50} < 45\% \\
0.0 & \text{else}
\end{cases}$$

**Rationale:** WR >52% implica sustentabilidade (Profit Factor > 1.5 com sizing correto)

#### Componente 5: Inactivity Penalty

**Trigger:** Cada step enquanto flat (sem posição)

$$r_{inact} = -0.01 \times \frac{\min(\text{flat\_steps}, 50)}{50}$$

**Effect:** Penalidade decai após 50 steps de inatividade

---

### Convergência Esperada

| Fase | Wall-Clock | Steps | Sharpe Esperado | Status |
|---|---|---|---|---|
| **Fase 0** | 0-6h | 0k | 0.0 (baseline) | Exploração aleatória |
| **Fase 1** | 6-24h | 50k-150k | 0.2-0.4 | Learning inicial |
| **Fase 2** | 24-72h | 150k-450k | 0.6-0.9 | Convergência |
| **Fase 3** | 72-96h | 450k-500k | **≥1.0** 🎯 | Sucesso |

---

### Success Metrics (Gate #4)

| Métrica | Threshold | Razão |
|---|---|---|
| **Sharpe Ratio** | ≥1.0 | Risk-adjusted return (risqueza quantificada) |
| **Max Drawdown** | <5% | Proteção capital  |
| **Win Rate** | ≥52% | Viabilidade estatística |
| **Inference Latency** | <100ms | Execution timing |
| **Profit Factor** | ≥1.5 | (Wins total) / (Losses total) |


