# 🏗️ ARQUITETURA DO AGENTE AUTÔNOMO

**Versão**: 1.0
**Data**: 2026-02-20
**Status**: ✅ DOCUMENTADO
**Responsável**: Product Owner + CTO

---

## 📊 Visão Estratégica

```text
AGENTE AUTÔNOMO DE RL (Reinforcement Learning)
│
├─ Objetivo: Operar futuros de criptomoedas com gestão de risco inviolável
├─ Plataforma: Binance Futures (USDⓈ-M)
├─ Modelo: PPO (Proximal Policy Optimization)
├─ Pares: 16 USDT (BTC, ETH, SOL, +13 outros)
├─ Timeframes: D1, H4, H1 (multi-timeframe)
└─ Features: 104 indicadores + SMC + sentimento + macro
```text

## 🏛️ Estrutura em Camadas

```text
┌─────────────────────────────────────────────────────┐
│              EXECUÇÃO OPERACIONAL                    │
│  (Live Trading + Paralela C + Monitoring)           │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼────────┐ ┌─▼──────────┐
│   Agente RL   │ │ Backtest  │ │ Monitoring  │
│   (Core)      │ │ Engine    │ │ & Risk      │
└───────┬──────┘ └──┬────────┘ └─┬──────────┘
        │           │            │
        └───────────┼────────────┘
                    │
        ┌───────────▼───────────┐
        │  Executor + API       │
        │  (Binance + DB)       │
        └───────────┬───────────┘
                    │
        ┌───────────▼───────────┐
        │  Data Collector       │
        │  (OHLCV + Macro)      │
        └───────────────────────┘
```text

## 🎯 Componentes Críticos

### 1. Agente RL (Core)

| Módulo | Função | Status |
|--------|--------|--------|
| `agent/environment.py` | Gym environment | ✅ v0.3 |
| `agent/reward.py` | Reward shaping | ✅ v0.3 |
| `agent/trainer.py` | PPO training loop | ✅ v0.3 |
| `agent/risk_manager.py` | Risk constraints | ✅ v0.3 |
| `agent/signal_environment.py` | Signal generation | ✅ v0.3 |

### 2. Backtest Engine

| Módulo | Função | Status |
|--------|--------|--------|
| `backtest/backtest_environment.py` | Deterministic env | ✅ v0.4 |
| `backtest/backtest_metrics.py` | Metrics + GO/NO-GO | ✅ v0.4 |
| `backtest/backtester.py` | Single-asset backtest | ⏳ v0.4 |
| `backtest/walk_forward.py` | Walk-forward analysis | ⏳ v0.4 |

### 3. Data Pipeline

| Módulo | Função | Status |
|--------|--------|--------|
| `data/binance_client.py` | Binance API wrapper | ✅ v0.3 |
| `data/data_loader.py` | Multi-layer data | ✅ v0.3 |
| `data/collector.py` | Histórico collection | ✅ v0.3 |
| `data/macro_collector.py` | Macro indicators | ⏳ v0.3 |
| `data/sentiment_collector.py` | Sentiment data | ⏳ v0.3 |

### 4. Execution Layer

| Módulo | Função | Status |
|--------|--------|--------|
| `execution/order_executor.py` | Order management | ✅ v0.3 |
| `execution/position_manager.py` | Position tracking | ✅ v0.3 |
| `execution/risk_controls.py` | Stop/limit enforcement | ✅ v0.3 |
| `scripts/execute_1dollar_trade.py` | MARKET + SL + TP real (Binance) | ✅ v0.3.1 |
| `scripts/manage_positions.py` | Parciais, breakeven, close | ✅ v0.3.1 |
| `scripts/monitor_and_manage_positions.py` | Monitoramento 24/7 | ✅ v0.3.1 |

### 5. Monitoring & Governance

| Módulo | Função | Status |
|--------|--------|--------|
| `monitoring/logger.py` | Structured logging | ✅ v0.3 |
| `monitoring/alerter.py` | Alert system | ⏳ v0.3 |
| `monitoring/dashboard.py` | Real-time dashboard | ⏳ v0.4 |
| `core/orchestrator.py` | Mode orchestration | ✅ v0.3 |

## 6. Sistema de Gestão de Posições (Novo — v0.3.1)

### 🆕 Arquitetura 3-Fases com Ordens Reais Binance

**Problema Resolvido**: SL/TP simulados localmente → Ordens REAIS apregoadas Binance

| Fase | Script | Função | Status |
|------|--------|--------|--------|
| 1: Abertura | `execute_1dollar_trade.py` | MARKET + SL + TP real (new_algo_order) | ✅ v0.3.1 |
| 2: Gestão | `manage_positions.py` | Parciais 50%, breakeven, fechamento | ✅ v0.3.1 |
| 3: Monitor | `monitor_and_manage_positions.py` | Health check, PnL, timeout detection | ✅ v0.3.1 |

**APIs Binance Descobertas**:
- `new_algo_order()` ← Cria ordens condicionais REAIS
- `trigger_price` ← Ponto de disparo (não `stopPrice`)
- `algo_id` ← Identificador retornado pela API

**Prova Funcional**: Trade ID 7
```text
ANKRUSDT LONG (2,174 @ $0.00459815)
├─ MARKET Order: 5412778331 ✅
├─ SL Algo: 3000000742992546 ✅ (trigger @ -5%)
└─ TP Algo: 3000000742992581 ✅ (trigger @ +10%)
```

**Database Schema** (novo em v0.3.1):
```sql
trade_partial_exits (11 colunas)
├─ partial_id (PK)
├─ trade_id (FK → trade_log)
├─ partial_number, quantity_closed, quantity_remaining
├─ exit_price, exit_time
├─ binance_sl_order_id_new, binance_tp_order_id_new
└─ reason (MANUAL, TP_TRIGGER, SL_TRIGGER, etc)
```

---

### 5. Monitoring & Governance

| Módulo | Função | Status |
|--------|--------|--------|
| `monitoring/logger.py` | Structured logging | ✅ v0.3 |
| `monitoring/alerter.py` | Alert system | ⏳ v0.3 |
| `monitoring/dashboard.py` | Real-time dashboard | ⏳ v0.4 |
| `core/orchestrator.py` | Mode orchestration | ✅ v0.3 |

## 7. Sistema de Learning Contextual (Novo — v0.3.2)

### 🆕 Round 5 & Round 5+ Meta-Learning Architecture

**Problema Resolvido**: Agente não diferenciava contexto de decisões (prudência vs oportunismo)

#### Round 5 — Stay-Out Learning

| Componente | Função | Status |
|-----------|--------|--------|
| `agent/reward.py` (modificado) | r_out_of_market component | ✅ v0.3.2 |
| `agent/environment.py` (modificado) | Pass flat_steps parameter | ✅ v0.3.2 |
| `test_stay_out_of_market.py` (novo) | 5/5 testes validação | ✅ v0.3.2 |

**Mecanismo**:
```text
Contexto: Drawdown ≥ 2%
  └─ Ação: Agente fica fora
     └─ Reward: +0.15 (prudência)

Contexto: 3+ trades em 24h (cansaço)
  └─ Ação: Agente fica fora
     └─ Reward: +0.10 (descanso saudável)

Contexto: > 16 dias sem posição
  └─ Ação: Continua fora
     └─ Reward: -0.03 (inatividade excessiva)
```

#### Round 5+ — Opportunity Learning (Meta-Learning)

| Componente | Função | Status |
|-----------|--------|--------|
| `agent/opportunity_learning.py` (novo) | OpportunityLearner meta-learning engine | ✅ v0.3.2 |
| `test_opportunity_learning.py` (novo) | 6/6 testes validação | ✅ v0.3.2 |
| `docs/LEARNING_CONTEXTUAL_DECISIONS.md` | Documentação técnica completa | ✅ v0.3.2 |

**Dataclass & Logic**:
```text
MissedOpportunity
├─ symbol, direction, entry_price, confluence
├─ drawdown_pct, recent_trades_24h
├─ hypothetical_tp, hypothetical_sl
├─ would_have_been_winning
├─ profit_pct_if_entered
├─ opportunity_quality
├─ contextual_reward
└─ reasoning (texto)

OpportunityLearner.evaluate_opportunity()
├─ Input: MissedOpportunity + result_after_20_candles
├─ Contexto detectado: 4 cenários
├─ Computa reward contextual (-0.20 a +0.30)
└─ Armazena para episódio summary
```

**Contextos & Rewards**:
```
Cenário 1: Opp EXCELENTE + Drawdown ALTO
  └─ Reward: -0.15 (deveria ter entrado com size menor)

Cenário 2: Opp BOA + MÚLTIPLOS TRADES últimas 24h
  └─ Reward: -0.10 (descanso foi longo)

Cenário 3: Opp BOA + Contexto NORMAL
  └─ Reward: -0.20 (nenhuma desculpa, puro desperdício)

Cenário 4: Opp RUIM + Qualquer contexto
  └─ Reward: +0.30 (excelente evasão de perda)
```

**Evolução de Componentes de Reward**:

| Versão | r_pnl | r_hold | r_invalid | r_out_of_market | r_contextual | Total |
|--------|-------|--------|-----------|----------|--------------|-------|
| Round 4 | ✅ | ✅ | ✅ | ❌ | ❌ | 3 |
| Round 5 | ✅ | ✅ | ✅ | ✅ | ❌ | 4 |
| Round 5+ | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |

**Validação**:
- Round 5: 5/5 testes passando
- Round 5+: 6/6 testes passando
- Total: 11/11 testes ✅
- Sintaxe: python -m py_compile ✅
- Backward compatibility: ✅ Non-breaking

---

## 🔐 Modos Operacionais

### Mode 1: Automático Live
```text
Agente RL → Sinais → Executor → Binance Live
└─ Sem intervenção manual
   Riscos: Capital real em jogo
   SLA: 99.9% uptime
```text

### Mode 2: Backtest
```text
PPO Model → Backtest Env → Métricas → Report
└─ Validação histórica
   Riscos: Overfitting
   Timeline: 1-2 horas por teste
```text

### Mode 3: Paper Trading
```text
Agente RL → Simulador → Report
└─ Sem marcar posições reais
   Riscos: Nenhum (fictício)
   Uso: QA, testing
```text

### Mode 4: Profit Guardian (Defensiva)
```text
Posições existentes → Apenas CLOSE/REDUCE
├─ Sinais bloqueados (no "OPEN")
├─ Objetivo: Proteção capital
└─ Status: 🔴 ATIVO (20/02, bloqueador ACAO-001)
```json

## 📐 Fluxo de Dados

```text
COLETA CONTÍNUA (Horária)
├─ OHLCV H1: Binance API
├─ OHLCV H4: Agregado de H1
├─ OHLCV D1: Agregado de H4
├─ Indicadores: RSI, MACD, BB, SMC
├─ Sentimento: News API
└─ Macro: Economic calendar

   ↓↓↓

STORAGE (SQLite)
├─ 89k+ candles H1 (3-4 meses)
├─ 78k+ candles H4
├─ 7.5k+ candles D1
└─ 30k+ indicador records

   ↓↓↓

RL TRAINING (Episódio = 100 steps)
├─ Input: Observation (104 features)
├─ PPO Process: π(a|s) → action → reward
├─ Output: Policy weights (modelo treinado)
└─ Timeline: 10+ horas (100 episódios)

   ↓↓↓

DEPLOYMENT (Live ou Backtest)
├─ Load trained model
├─ Initialize env + tracker
├─ Step/episode loop
├─ Action execution
└─ Real-time reporting
```text

## 🎛️ Governança de Decisões

```text
CFO (Finanças)
├─ Aprova: ACAO-001 (posição closes)
├─ Oversee: Budget, risk limits
└─ SLA: 1 hora (crítico)

CTO (Técnico)
├─ Aprova: v0.3 release, deployment
├─ Oversee: Architecture, stability
└─ SLA: 4 horas (alto)

PO (Produto)
├─ Aprova: Backlog, roadmap, features
├─ Oversee: Delivery, documentation
└─ SLA: 24 horas (médio)
```text

## 🔄 Ciclo de Desenvolvimento

```text
PLANEJAMENTO (Roadmap 12 meses)
    ↓
IMPLEMENTAÇÃO (Sprint 1-4 semanas)
    ├─ v0.3: Validação RL
    ├─ v0.4: Backtest engine
    ├─ v0.5: Scaling + risk
    └─ v1.0: Production-ready
    ↓
VALIDAÇÃO (QA + Testing)
    ├─ Unit tests (85%+ coverage)
    ├─ Integration tests
    ├─ Backtest validation
    └─ Go/No-Go gate
    ↓
DEPLOYMENT (Live)
    ├─ Staging validation
    ├─ Monitoring setup
    ├─ Operator training
    └─ Launch
    ↓
MONITORING (24/7)
    ├─ Real-time dashboards
    ├─ Alert rules
    ├─ Incident response
    └─ Continuous optimization
```text

## 📋 Matriz de Sincronização

```text
Código (agente/*.py)
    ↓↔↓
Documentos (AGENTE_AUTONOMO_*.md)
    ├─ ARQUITETURA (este)
    ├─ ROADMAP (timeline)
    ├─ TRACKER (status)
    ├─ BACKLOG (what's next)
    ├─ FEATURES (lista)
    ├─ RELEASE (versioning)
    └─ CHANGELOG (history)
    ↓↔↓
Configuração (config/*)
    ├─ symbols.py (16 pares)
    ├─ execution_config.py (bloqueante?)
    └─ risk_params.py (limites)
```python

## ✅ Validação de Integridade

Antes de cada commit, validar:

```bash
[ ] Código executa sem erro
[ ] Testes passam (pytest -q)
[ ] Documentação sincronizada
[ ] AGENTE_AUTONOMO_*.md atualizados
[ ] Nenhuma breaking change
[ ] Risk constraints respeitadas
```

## 🔄 Mecanismo de Sincronização Obrigatória (v0.3.1+)

**Regra**: Toda alteração em qualquer dos documentos abaixo DEVE sincronizar os demais:

| Documento | Mantém | Impacta |
|-----------|--------|---------|
| ARQUITETURA (este) | Componentes, APIs, features | ROADMAP, FEATURES, TRACKER |
| ROADMAP | Timeline, milestones | TRACKER, FEATURES, CHANGELOG |
| FEATURES | Feature matrix | ROADMAP, CHANGELOG, TRACKER |
| TRACKER | Status v0.3 → v2.0 | ROADMAP, CHANGELOG |
| CHANGELOG | Histórico de mudanças | README.md, RELEASE |

**Checklist de Sincronização** (executar após mudança):

```bash
# Ao alterar documentação:
□ ARQUITETURA.md → revisar ROADMAP.md (timelines ainda válidas?)
□ ROADMAP.md → revisar FEATURES.md (features alinhadas?)
□ FEATURES.md → revisar TRACKER.md (status atual OK?)
□ TRACKER.md → revisar CHANGELOG.md (entradas registradas?)
□ CHANGELOG.md → revisar README.md (seção status atualizada?)
□ Todos acima → revisar BACKLOG.md (prioridades ainda OK?)

# Validação final:
[ ] git log --oneline -1 (mensagem contém [SYNC]?)
[ ] Nenhuma referência quebrada (ex: v0.X.X != versão)
[ ] Linhas < 80 caracteres marcdownlint ✅
```

---

**Mantido por**: CTO + Product Owner
**Próxima revisão**: Quando mudança arquitetura ou v0.3.1 deployment
**Last Updated**: 2026-02-21 00:52 UTC
**Sincronização**: [SYNC] v0.3.1 — Sistema de Gestão com Ordens Reais Binance


```

---

**Mantido por**: CTO + Product Owner
**Próxima revisão**: Quando mudança arquitetura
**Last Updated**: 2026-02-20 22:05 UTC

