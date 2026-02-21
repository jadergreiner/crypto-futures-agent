# 🏗️ ARQUITETURA DO AGENTE AUTÔNOMO

**Versão**: 1.0  
**Data**: 2026-02-20  
**Status**: ✅ DOCUMENTADO  
**Responsável**: Product Owner + CTO

---

## 📊 Visão Estratégica

```
AGENTE AUTÔNOMO DE RL (Reinforcement Learning)
│
├─ Objetivo: Operar futuros de criptomoedas com gestão de risco inviolável
├─ Plataforma: Binance Futures (USDⓈ-M)
├─ Modelo: PPO (Proximal Policy Optimization)
├─ Pares: 16 USDT (BTC, ETH, SOL, +13 outros)
├─ Timeframes: D1, H4, H1 (multi-timeframe)
└─ Features: 104 indicadores + SMC + sentimento + macro
```

## 🏛️ Estrutura em Camadas

```
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
```

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

### 5. Monitoring & Governance

| Módulo | Função | Status |
|--------|--------|--------|
| `monitoring/logger.py` | Structured logging | ✅ v0.3 |
| `monitoring/alerter.py` | Alert system | ⏳ v0.3 |
| `monitoring/dashboard.py` | Real-time dashboard | ⏳ v0.4 |
| `core/orchestrator.py` | Mode orchestration | ✅ v0.3 |

## 🔐 Modos Operacionais

### Mode 1: Automático Live
```
Agente RL → Sinais → Executor → Binance Live
└─ Sem intervenção manual
   Riscos: Capital real em jogo
   SLA: 99.9% uptime
```

### Mode 2: Backtest
```
PPO Model → Backtest Env → Métricas → Report
└─ Validação histórica
   Riscos: Overfitting
   Timeline: 1-2 horas por teste
```

### Mode 3: Paper Trading
```
Agente RL → Simulador → Report
└─ Sem marcar posições reais
   Riscos: Nenhum (fictício)
   Uso: QA, testing
```

### Mode 4: Profit Guardian (Defensiva)
```
Posições existentes → Apenas CLOSE/REDUCE
├─ Sinais bloqueados (no "OPEN")
├─ Objetivo: Proteção capital
└─ Status: 🔴 ATIVO (20/02, bloqueador ACAO-001)
```

## 📐 Fluxo de Dados

```
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
```

## 🎛️ Governança de Decisões

```
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
```

## 🔄 Ciclo de Desenvolvimento

```
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
```

## 📋 Matriz de Sincronização

```
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
```

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

---

**Mantido por**: CTO + Product Owner  
**Próxima revisão**: Quando mudança arquitetura  
**Last Updated**: 2026-02-20 22:05 UTC

