# 📊 Sprint Tracker — Crypto Futures Agent

## 🎯 Sprint 1: MUST Items (21-25 FEV 2026) — OPERACIONALIZAÇÃO (Fase 2D Consolidação)

**Duração:** 5 dias (21-25 FEV 2026)
**Priorização:** MoSCoW + Cost of Delay + Risk Impact
**Referência:** Consolidado de `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

| ID | Task | Owner | Status | Entrega | Prioridade |
|----|------|-------|--------|---------|----------|
| **1.1** | Implementar Heurísticas Conservadoras | Dev | ✅ DONE (22 FEV 06:00) | execution/heuristic_signals.py | 🔴 CRÍTICA |
| **1.2** | QA Validação Completa (Heurísticas) | Audit | ✅ DONE (22 FEV 08:00) | 9/9 tests, edge cases | 🔴 CRÍTICA |
| **1.3** | Go-Live Phase 1 (10% volume) | Executor | ✅ DONE (22 FEV 10:00) | Live operação iniciada | 🔴 CRÍTICA |
| **1.4** | Go-Live Phase 2 (50% volume) | Executor | ✅ DONE (22 FEV 11:00) | Escalação sucesso | 🔴 CRÍTICA |
| **1.5** | Go-Live Phase 3 (100% volume) | Executor | ✅ DONE (22 FEV 12:00) | Full deployment | 🔴 CRÍTICA |
| **1.6** | TASK-005 PPO Training (96h) | The Brain | 🔄 IN PROGRESS (22-25 FEV) | Model convergência | 🔴 CRÍTICA |
| **1.7** | TASK-006 PPO QA Validation | Audit | ⏳ PENDING (25 FEV 10:00) | OOT backtest validation | 🔴 CRÍTICA |
| **1.8** | TASK-007 PPO Merge Live | Dev | ⏳ PENDING (25 FEV 14:00) | v0.5 alpha deployment | 🔴 CRÍTICA |

**Documentação Referência:**
- Detalhes completos: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`
- Status real-time: `backlog/TASKS_TRACKER_REALTIME.md`
- Quick start: `backlog/BACKLOG_QUICK_START.md`

---

## Sprint Concluído: v0.2 — Pipeline Fix ✅

**Duração:** 2 semanas
**Esforço total estimado:** ~10h

| Task | Story | Status | Esforço |
|------|-------|--------|---------|
| Atualizar `build_observation` para receber `multi_tf_result` | US-01 | ✅ DONE
| 2h |
| Preencher Bloco 7 com `correlation_btc`, `beta_btc` | US-01 | ✅ DONE | 1h |
| Preencher Bloco 8 com `d1_bias` e `market_regime` scores | US-01 | ✅ DONE | 1h
|
| Fix R-multiple ordering no `RewardCalculator` | US-02 | ✅ DONE | 30min |
| Sincronizar `get_feature_names()` | US-03 | ✅ DONE | 1h |
| Teste unitário `FeatureEngineer.build_observation` | US-01 | ✅ DONE | 2h |
| Teste unitário `MultiTimeframeAnalysis.aggregate` | US-01 | ✅ DONE | 1h |
| Teste unitário `RewardCalculator.calculate` | US-02 | ✅ DONE | 1h |
| Validar dry-run com valores reais nos blocos 7/8 | US-01 | ✅ DONE | 30min |

## Sprint Atual: v0.3 — Training Ready � OPERAÇÃO PARALELA C (20/02/2026)

**Duração:** 20/02 (1 dia - Sprint expedito)
**Esforço total estimado:** ~8h
**Status:** ✅ AUTORIZADO — Operação Paralela C (LIVE + v0.3) desde 20:30 BRT

| Task | Story | Status | Esforço | Prioridade |
|------|-------|--------|---------|----------|
| ✅ Implementar `step()` completo no `CryptoFuturesEnv` | US-04 | ✅ DONE | - | |
| ✅ Implementar `_get_observation()` usando `FeatureEngineer` | US-04 | ✅ DONE |
- | |
| ✅ Pipeline de dados para treinamento | US-04 | ✅ DONE | - | |
| ✅ Script de treinamento funcional (`python main.py --train`) | US-04 | ✅ DONE
| - | |
| ✅ Criar orchestrator paralelo (LIVE + v0.3) | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| ✅ Criar monitor crítico com safeagues | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| ✅ Obter autorização formal (Operação C) | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| 🔄 Criar teste E2E completo (3 símbolos, 10k steps) | US-04 | 🔄 IN PROGRESS |
2h | 🔴 CRÍTICA |
| 🔄 Validar treinamento (CV < 1.5 + WinRate > 45%) | US-04 | 🔄 IN PROGRESS |
1.5h | 🔴 CRÍTICA |
| 🔄 Debug signal generation (0 sinais) | US-04 | 🔄 IN PROGRESS | 1h | 🔴 CRÍTICA
|
| 🔄 Sincronização de documentação | US-04 | 🔄 IN PROGRESS | 1h | 🔴 CRÍTICA |
| ⏳ Salvar/carregar modelo treinado (nice-to-have) | US-05 | ⏳ DEFER v0.4 | - |
🟢 MÉDIA |

## Sprint Planejado: v0.4 — Backtest Engine (21-23/02/2026)

**Duração:** 3 dias (21, 22, 23 fev)
**Esforço total estimado:** ~4.5h (core F-12) + ~2h (documentação + testes)
**Status:** ⏳ PLANEJADO — Aguarda validação v0.3 (até 23:59 BRT hoje)

| Task | Feature | Status | Esforço | Prioridade |
|------|---------|--------|---------|----------|
| Refinar história F-12 com 3 personas (PO + Finance + Tech) | F-12 | ✅ DONE |
0h | 🔴 CRÍTICA |
| Implementar BacktestEnvironment (subclasse CryptoFuturesEnv) | F-12a | ⏳ TODO (Issue #59)
| 1h | 🔴 CRÍTICA |
| Implementar BacktestDataLoader (3-camadas Parquet) | F-12b | ⏳ TODO (Issue #59) | 1.5h | 🔴
CRÍTICA |
| Implementar TradeStateMachine (IDLE/LONG/SHORT) | F-12c | ⏳ TODO (Issue #59) | 1.5h | 🔴
CRÍTICA |
| Implementar BacktestReporter (Text + JSON) | F-12d | ⏳ TODO (Issue #59) | 0.5h | 🟡 ALTA |
| Escrever 8 unit tests (determinismo, SM, métricas) | F-12e | ⏳ TODO (Issue #59) | 1h | 🔴
CRÍTICA |
| Integração `--train-and-backtest` em main.py | F-12f | ⏳ TODO (Issue #59) | 0.5h | 🟡 ALTA |
| Sincronizar documentação (FEATURES, ROADMAP, SYNC) | F-12h | ⏳ TODO (Issue #59) | 0.5h | 🔴
CRÍTICA |
| Teste manual end-to-end (BTCUSDT, 90 dias) | F-12g | ⏳ TODO (Issue #59) | 0.5h | 🟡 ALTA |

**Risk Clearance Checklist** (antes expansão v0.5):

- [ ] Sharpe ≥ 1.0
- [ ] MaxDD ≤ 15%
- [ ] Win Rate ≥ 45%
- [ ] Profit Factor ≥ 1.5
- [ ] Recovery Factor ≥ 2.0
- [ ] Consecutive Losses ≤ 5

## Backlog Priorizado

| Sprint | Release | Foco | Esforço Est. |
|--------|---------|------|-------------|
| Sprint 3 | v0.4 | Backtester real com métricas | ~15h |
| Sprint 4 | v0.4 | Walk-forward + relatório | ~10h |
| Sprint 5 | v0.5 | Paper trading E2E | ~15h |
| Sprint 6 | v1.0 | Execução real + circuit breakers | ~20h |

---

## TASK-005: PPO Training — Phase 4 Operacionalização (Consolidado Fase 2A)

**Responsável:** The Brain (ML Specialist) + Dev (SWE Senior)
**Timeline:** 22 FEV 14:00 UTC → 25 FEV 10:00 UTC (96h wall-clock)
**Status:** 🟢 **SPECIFICATION COMPLETE** — Ready SWE implementation

---

### Resumo Executivo

| Aspecto | Valor |
|---|---|
| **O QUÊ** | Treinar agente PPO para 60 pares simultâneos |
| **POR QUÊ** | Substituir heurísticas estáticas com política adaptativa (Sharpe >1.0) |
| **COMO** | 500k environment steps, 4 parallel episodes, checkpoint every 50k |
| **QUANTO TEMPO** | ≤96 horas de wall-clock (deadline 25 FEV 10:00 UTC) |
| **SUCESSO** | Sharpe ≥1.0, DD <5%, WR ≥52%, latência <100ms |

---

### Arquitetura Overview

```
┌─────────────────────────────────────────────────┐
│  PPO Policy Network (Shared across 60 pairs)    │
│  Input:  State (1320,) = 60 × 22 normalized    │
│  Hidden: [256, 256] ReLU                        │
│  Output: Action logits (180,) = 60 × 3 actions │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│  Multi-Pair Gym Environment (DummyVecEnv×4)    │
│  4 parallel episodes, 60 pairs per episode      │
│  Runs 500k total steps over ≤96 hours          │
│  Checkpoints every 50k steps (best 3 kept)    │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│  Backtest Validation (OOT on last 20% data)    │
│  Verify Sharpe ≥0.9, DD <5.5%, no look-ahead  │
└─────────────────────────────────────────────────┘
```

---

### Plano SWE Coordenação (6 Fases)

**Fase 0: Infraestrutura (90min)**
- GPU server: 4-core CPU, 16GB RAM, 100GB disk
- Install: stable-baselines3, torch, tensorboard

**Fase 1: Environment & Reward (150min)**
- Feature selection: 104 → 22 features via PCA
- Multi-pair environment: obs (1320,), action MultiDiscrete([3×60])
- Data pipeline: 80/20 walk-forward split (NO look-ahead)

**Fase 2: Reward Function (90min)**
- Implement 6 components: PnL, Hold, Drawdown, WinRate, Inactivity, Sharpe
- Range validation: [-1.0, +10.0]

**Fase 3: PPO Training Setup (180min)**
- stable-baselines3 PPO: batch_size=64, learning_rate=3e-4→1e-5 decay
- 500k steps target, converge Sharpe ≥1.0

**Fase 4: Convergence Monitoring (28h)**
- Realtime dashboard: Sharpe, WR, DD vs thresholds
- Early stopping if Sharpe hits 1.0 (save checkpoint)

**Fase 5: OOT Validation (20h)**
- Backtest on validation set (last 20%)
- Verify no look-ahead, metrics realistic

---

### Gates Diários (#0 → #4)

| Gate | Data | Criério Sucesso | Owner |
|---|---|---|---|
| #0 | 22 FEV 16:00 | Infra ready, deps OK | Dev |
| #1 QA | 22 FEV 08:00 | Gate #1 validation checkpoint | Audit |
| #2 | 23 FEV 08:00 | Fase 1-2 complete, reward tested | The Brain |
| #3 | 24 FEV 08:00 | Treinamento in progress, Sharpe trending up | Dev |
| #4 (Final) | 25 FEV 10:00 | Sharpe ≥1.0, OOT validated, ready merge | Executor |

---

### Success Criteria (Gate #4 Final)

- ✅ Sharpe Ratio ≥1.0
- ✅ Max Drawdown <5%
- ✅ Win Rate ≥52%
- ✅ Inference latency <100ms
- ✅ No look-ahead bias (OOT validation)
- ✅ Best 3 checkpoints saved

---

### Referências Técnicas Completas

- **Architecture:** [docs/FEATURES.md](FEATURES.md#f-ml1-ppo-training-pipeline)
- **Reward Math:** [docs/FEATURES.md](FEATURES.md#teoria-ppo--aprendizagem-contextual)
- **Especificação Completa:** [docs/SYNCHRONIZATION.md](SYNCHRONIZATION.md#task-005-especificação--sincronização)
- **JSON Spec:** `prompts/TASK-005_ML_SPECIFICATION_PLAN.json`

---

**Última atualização:** 22 FEV 2026 17:40 UTC (TASK-005 consolidado Fase 2A)
