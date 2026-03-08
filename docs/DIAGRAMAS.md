# 📐 Diagramas — Arquitetura do Sistema

**Versão:** 0.2.1
**Data:** 07 MAR 2026
**Responsável:** Arquiteto (#6), Data (#11)

---

## 🎯 Propósito

Fornecer representações visuais (ASCII + UML) da arquitetura de **classes** e **dados** do projeto para facilitar compreensão e onboarding.

---

## 📊 PARTE 1: DIAGRAMA DE CLASSES

### Nível 1: Visão Geral (Agregados Raízes)

```
┌────────────────────────────────────────────────────────────────┐
│                    CRYPTO FUTURES AGENT                        │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    AGREGADOS RAÍZES                             │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │  Account        │  — Estado financeiro
    │  (Agregado)     │    [account_id PK]
    │                 │
    │ Properties:     │
    │  • balance_usd  │
    │  • equity_usd   │
    │  • margin_ratio │
    │  • is_active    │
    └────────┬────────┘
             │ 1
             │ aggregates
             │ many
             ↓
    ┌─────────────────────┐
    │  Position           │  — Posição aberta
    │  (Entity)           │    [position_id FK account]
    │                     │
    │ Properties:         │
    │  • symbol           │
    │  • entry_price      │
    │  • side (L/S)       │
    │  • stop_loss_price  │
    │  • take_profit_*    │
    │  • unrealized_pnl   │
    │  • is_closed        │
    └──────────┬──────────┘
               │ 1
               │ contains
               │ many
               ↓
    ┌──────────────────────┐
    │  Order               │  — Execução
    │  (Entity)            │    [order_id, binance_order_id]
    │                      │
    │ Properties:          │
    │  • symbol            │
    │  • side (BUY/SELL)   │
    │  • quantity          │
    │  • status (PENDING..)│
    │  • filled_qty        │
    │  • filled_price_avg  │
    └──────────┬───────────┘
               │ N
               │ creates
               │ 1
               ↓
    ┌──────────────────────┐
    │  Trade               │  — Operação fechada
    │  (Entity)            │    [trade_id, position_id]
    │                      │
    │ Properties:          │
    │  • entry_price       │
    │  • exit_price        │
    │  • profit_loss_usd   │
    │  • r_multiple        │
    │  • close_reason      │
    │  • win (boolean)     │
    └────────────────────┘
```

**Referência Técnica:** [C4_MODEL.md nível 3 — Components](C4_MODEL.md)

---

### Nível 2: Módulos Estratégicos (Classes Principais)

```
┌──────────────────────────────────────────────────────────────┐
│                   agent/ — Inteligência                      │
└──────────────────────────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  CryptoAgent            │  (Classe Principal)
    ├─────────────────────────┤
    │ Methods:                │
    │ + reset()               │  → Inicia episódio
    │ + step(action)          │  → Executa ação (0-3)
    │ + close_position()      │  → Fecha posição
    │ + get_state()           │  → Retorna observation (104 features)
    │                         │
    │ Attributes:             │
    │ - env: TradingEnv       │
    │ - risk_manager: RM      │
    │ - heuristics: HFilter   │
    │ - reward_calc: RC       │
    └────────┬────────────────┘
             │
             ├─owns─→ ┌──────────────────────┐
             │        │  SMCAnalyzer         │
             │        ├──────────────────────┤
             │        │ - detect_ob()        │  Order Blocks
             │        │ - detect_bos()       │  Break of Structure
             │        │ - detect_fvg()       │  Fair Value Gap
             │        │ + analyze_multi_tf() │
             │        └──────────────────────┘
             │
             ├─owns─→ ┌──────────────────────┐
             │        │  RLAgent (PPO)       │
             │        ├──────────────────────┤
             │        │ + predict(obs)       │  → action, confidence
             │        │ - model (SB3)        │  Stable-Baselines3
             │        │ - confidence score   │
             │        └──────────────────────┘
             │
             ├─owns─→ ┌──────────────────────┐
             │        │  MetricsUtils        │
             │        ├──────────────────────┤
             │        │ + compute_performance│  PnL/equity metrics
             │        │ + sanity checks      │  Sharpe/PF bounds
             │        │ + vol floor policy   │
             │        └──────────────────────┘
             │
             └─owns─→ ┌──────────────────────┐
                      │  TradingEnv          │
                      ├──────────────────────┤
                      │ - observation space  │  104 features
                      │ - action space       │  4 actions
                      │ + step(action)       │
                      │ + reset()            │
                      │ + render()           │
                      │ + raw_pnl output     │  financial metric
                      │ + shaped_reward      │  RL learning signal
                      │ - market_data        │
                      │ - positions          │
                      │ - account            │
                      └──────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│               execution/ — Execução de Ordens                 │
└──────────────────────────────────────────────────────────────┘

    ┌──────────────────────────┐
    │  OrderExecutor           │  (Classe Principal)
    ├──────────────────────────┤
    │ Methods:                 │
    │ + place_order(spec)      │  → Valida + envia Binance
    │ + cancel_order(id)       │  → Cancela ordem
    │ + close_position(pos)    │  → Fecha posição
    │ - validate_risk()        │  → Checa limites (R1-R7)
    │                          │
    │ Attributes:              │
    │ - binance_client         │  REST API
    │ - db_manager: DBM        │  SQLite persistence
    │ - risk_mgr: RM           │  Risk validation
    └────────┬─────────────────┘
             │
             ├─uses─→ ┌──────────────────────┐
             │        │  BinanceClient       │
             │        ├──────────────────────┤
             │        │ + place_order()      │
             │        │ + get_position()     │
             │        │ + get_open_orders()  │
             │        │ - session            │  REST
             │        └──────────────────────┘
             │
             └─uses─→ ┌──────────────────────┐
                      │  RiskManager         │
                      ├──────────────────────┤
                      │ + validate_order()   │  R1-R7
                      │ + check_leverage()   │
                      │ + check_capital()    │
                      │ + check_positions()  │
                      │ - rules_db           │  Reg. de Negócio
                      └──────────────────────┘


┌──────────────────────────────────────────────────────────────┐
│              risk/ — Gestão de Risco                          │
└──────────────────────────────────────────────────────────────┘

    ┌────────────────────────┐
    │  RiskManager           │
    ├────────────────────────┤
    │ Methods:               │
    │ + validate_order()     │  → Bloqueia ou aprova
    │ + get_margin_used()    │
    │ + get_leverage()       │
    │ + check_capital()      │  → R2: > 50%
    │ + check_equity()       │  → Rebalance automático
    │                        │
    │ Attributes:            │
    │ - config: RiskConfig   │
    │ - rules: List[Rule]    │  R1-R15
    │ - account: Account DF  │
    └────────┬───────────────┘
             │
             └─manages─→ ┌──────────────────────┐
                         │  DrawdownMonitor     │
                         ├──────────────────────┤
                         │ + calc_drawdown()    │
                         │ + check_limits()     │  R5
                         │ + notify_alerts()    │  > -5%, -8%, -15%
                         │ - alert_level        │
                         └──────────────────────┘
```

---

### Nível 3: Fluxo de Dados (Class Interactions)

```
OPERAÇÃO COMPLETA (1 episódio)

1. LOOP PRINCIPAL (agent/__init__.py)
   ┌──────────────────────┐
   │ CryptoAgent.step()   │
   └─────────┬────────────┘
             │
             ├─call──→ TradingEnv.get_observation()
             │         ├─fetch─→ BinanceClient.get_candles()
             │         ├─fetch─→ BinanceClient.get_positions()
             │         └─return─→ observation (104-D array)
             │
             ├─call──→ SMCAnalyzer.analyze_multi_tf()
             │         ├─detect─→ order_blocks
             │         ├─detect─→ break_of_structure
             │         └─return─→ smc_signal
             │
             ├─call──→ RLAgent.predict(observation)
             │         └─return─→ action (0-3), confidence (0-1.0)
             │
             ├─IF confidence ≥ 0.65:
             │    ├─call──→ HeuristicFilter.apply()
             │    │          (validates: consensus, loss_streak, etc)
             │    │
             │    └─IF pass:
             │         ├─call──→ RiskManager.validate_order()
             │         │          (checks R1-R7)
             │         │
             │         └─IF valid:
             │              ├─call──→ OrderExecutor.place_order()
             │              │          ├─send──→ Binance API
             │              │          ├─store──→ order (SQLite)
             │              │          └─return─→ order
             │              │
             │              ├─create─→ Position entity
             │              ├─create─→ Signal record
             │              │
             │              └─SET UP MONITOR:
             │                 └─watch─→ position for SL/TP hit
             │
             └─ELSE: log rejection reason


2. MONITOR CONTÍNUO (monitoring/)
   ┌──────────────────────┐
   │ PerformanceMonitor   │  (rodando paralelo)
   └─────────┬────────────┘
             │
             ├─TICK (cada candle 4h):
             │  ├─fetch─→ position.current_price
             │  ├─calc──→ unrealized_pnl
             │  ├─monitor─→ drawdown
             │  │
             │  ├─IF SL HIT:
             │  │  ├─call──→ OrderExecutor.close_position("SL")
             │  │  ├─create─→ Trade record (win=FALSE)
             │  │  ├─notify─→ telegram alert
             │  │  └─update─→ performance metrics
             │  │
             │  └─IF TP HIT:
             │     ├─call──→ OrderExecutor.close_position("TP")
             │     ├─create─→ Trade record (win=TRUE)
             │     ├─calc──→ r_multiple
             │     ├─notify─→ telegram alert
             │     └─update─→ performance metrics
             │
             └─DAILY check:
                ├─IF drawdown ≤ -15%:
                │  └─CIRCUIT BREAKER: parar novos trades (R5)
                │
                ├─IF 2+ dias consecutivos com loss:
                │  └─PAUSE: 1 dia sem trades (R13)
                │
                └─IF Sharpe < 0.5 por 2 semanas:
                   └─ALERT: retreinamento necessário (R15)
```

---

## 📊 PARTE 2: DIAGRAMA DE DADOS (ER Model)

### Entity Relationship Diagram (Normalizado)

```
┌────────────────────────────────────────────────────────────────┐
│                    CRYPTO FUTURES AGENT DB                     │
│                        SQLite 3.x                              │
└────────────────────────────────────────────────────────────────┘


        ┌──────────────────┐
        │     ACCOUNT      │  (Agregado Raiz)
        ├──────────────────┤
    PK  │ account_id UUID  │
        │ exchange VARCHAR │
        │ balance_usd DEC  │
        │ equity_usd DEC   │
        │ margin_ratio DEC │
        │ is_active BOOL   │
        └────────┬─────────┘
                 │ 1:N
                 └─aggregates─→
                               │
            ┌──────────────────┴──────────┐
            │                             │
    ┌───────▼─────────┐      ┌──────────▼────────┐
    │   POSITION      │      │     ORDER         │
    ├─────────────────┤      ├───────────────────┤
PK  │ position_id UUID│  PK  │ order_id UUID     │
FK  │ account_id UUID │  FK  │ account_id UUID   │
    │ symbol VARCHAR  │  FK  │ position_id UUID? │
    │ entry_price DEC │      │ symbol VARCHAR    │
    │ side ENUM       │      │ side ENUM         │
    │ stop_loss DEC   │      │ status ENUM       │
    │ take_profit DEC │      │ quantity DEC      │
    │ unrealized_pnl  │      │ filled_qty DEC    │
    │ is_closed BOOL  │      │ filled_price_avg  │
    └───────┬─────────┘      └───────┬──────────┘
            │ 1:1 closes with        │
            │                        │ N:1 fills
            │                        │
            └────────────┬───────────┘
                         │
         ┌───────────────┴─────────────┐
         │                             │
    ┌────▼──────────────┐    ┌────────▼────────┐
    │      TRADE        │    │     SIGNAL      │
    ├───────────────────┤    ├─────────────────┤
PK  │ trade_id UUID     │PK  │ signal_id UUID  │
FK  │ account_id UUID   │    │ symbol VARCHAR  │
FK  │ position_id UUID  │    │ timestamp TS    │
FK  │ entry_order_id    │    │ signal_type     │
FK  │ exit_order_id     │    │ smc_bias ENUM   │
    │ entry_price DEC   │    │ ml_confidence   │
    │ exit_price DEC    │    │ price_at_signal │
    │ quantity DEC      │FK? │ trade_id UUID   │
    │ profit_loss_usd   │    │ ignored_reason  │
    │ r_multiple DEC    │    └─────────────────┘
    │ close_reason      │
    │ entry_time TS     │
    │ exit_time TS      │
    └───────────────────┘


┌───────────────────┐  ┌──────────────────┐
│     CANDLE        │  │  PERFORMANCE     │
├───────────────────┤  ├──────────────────┤
│ symbol VARCHAR    │  │ perf_id UUID     │
│ timeframe VARCHAR │  │ account_id UUID  │
│ timestamp TS      │  │ period VARCHAR   │
│ open DEC          │  │ date_start DATE  │
│ high DEC          │  │ date_end DATE    │
│ low DEC           │  │ total_trades INT │
│ close DEC         │  │ win_rate DEC     │
│ volume DEC        │  │ profit_loss_usd  │
│ is_closed BOOL    │  │ sharpe_ratio DEC │
└───────────────────┘  │ drawdown_max DEC │
   (Indexed)           │ createD_at TS    │
                       └──────────────────┘
                           (Indexed)
```

---

### Índices de Desempenho (Query Optimization)

```
┌─────────────────────────────────────────────────────┐
│            ÍNDICES CRÍTICOS                         │
└─────────────────────────────────────────────────────┘

account:
  ├─ PK: account_id
  └─ Índices: is_active

position:
  ├─ PK: position_id
  ├─ FK: account_id
  ├─ Índices:
  │  ├─ (account_id, is_closed)  [Query: posições abertas]
  │  ├─ symbol
  │  └─ (entry_time DESC)        [Query: histórico recente]

order:
  ├─ PK: order_id
  ├─ Índices:
  │  ├─ account_id, status
  │  ├─ binance_order_id (UNIQUE)
  │  └─ (created_at DESC)

trade:
  ├─ PK: trade_id
  ├─ Índices:
  │  ├─ account_id, closed_at (DESC)
  │  ├─ symbol
  │  ├─ win
  │  └─ (r_multiple DESC)   [Query: melhor R]

signal:
  ├─ PK: signal_id
  ├─ Índices:
  │  ├─ symbol, timestamp
  │  └─ signal_type

candle:
  ├─ Particionamento: por timeframe (3 tabelas)
  ├─ PK: (symbol, timeframe, timestamp)
  ├─ Índices:
  │  ├─ (symbol, timeframe, timestamp DESC)
  │  └─ symbol

performance:
  ├─ PK: perf_id
  └─ Índices: (account_id, period, date_start DESC)
```

---

### Fluxo de Persistência

```
CICLO DE DADOS (Write Path)

Memory (Trading Env)
    ↓
    ├─NEW POSITION
    │  └─→ SQLite: INSERT position
    │      └─→ SQLite: INSERT signal
    │          └─→ SQLite: INSERT order
    │              └─→ JSON: notifications/
    │
    ├─POSITION UPDATE (unrealized PnL)
    │  └─→ SQLite: UPDATE position (current_price, pnl)
    │
    └─POSITION CLOSE
       └─→ SQLite: UPDATE position (is_closed=TRUE, closed_at)
           └─→ SQLite: INSERT trade (results)
               └─→ SQLite: UPDATE account (balance_usd, equity_usd)
                   └─→ SQLite: INSERT performance (daily aggregates)
                       └─→ JSON: performance report


READ PATH (Query)

Dashboard / Backtester
    ↓
    ├─Get candles → SQLite (últimas 500) ou Parquet (1Y)
    ├─Get positions → SQLite (index: account_id, is_closed)
    ├─Get trades → SQLite (ordered by closed_at DESC)
    ├─Get performance → SQLite (period = 'daily' or 'weekly')
    └─Get signals → SQLite (últimas N)
```

---

## 🔄 Mapeamento: Classes → Entidades

| Classe | Tabela Principal | Fluxo |
|--------|------------------|-------|
| CryptoAgent | — (orquestrador) | Coordena steps |
| SMCAnalyzer | signal | Gera signal |
| RLAgent | signal | Enriquece confidence |
| OrderExecutor | order, position | Cria order → position |
| RiskManager | — (validador) | Bloqueia order |
| PerformanceMonitor | performance, trade | Calcula métricas |
| TradingEnv | position, account | Fornece observação |

---

## 📍 Integridade Referencial (Cascatas)

```
Operação: Deletar Account
  ├─RESTRICT feedback (não deletar se houver dependentes)
  ├─Positions cascade → close all
  ├─Orders cascade → cancel pending
  ├─Trades cascade → mark deleted
  └─Signals cascade → mark orphaned

Operação: Deletar Position
  ├─Cascade → Signals (signal.trade_id = NULL)
  └─SET NULL → Orders (order.position_id)

Operação: Deletar Order
  └─RESTRICT (Trade referencia order)
```

---

## 🚀 Histórico de Evolução

| Sprint | Mudança | Status |
|--------|---------|--------|
| S1 | Estrutura base (Account, Position, Order) | ✅ |
| S2 | Adicionar Trade, Signal | ✅ |
| S2 | Adicionar Candle (Parquet) | ✅ |
| S2 | Adicionar Performance (rolling metrics) | ✅ |
| S3 | Adicionar notification logs | ✅ |
| S3 | TASK-005 v2: Unified RL metrics utility | ✅ |

---

## 📚 Referências Cruzadas

- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) — Descrição detalhada das entidades
- [C4_MODEL.md nível 2](C4_MODEL.md) — Containers de dados (SQLite, Parquet)
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) — Mapeamento R1-R15 → Classes
- [BACKLOG.md](BACKLOG.md) — Tasks que criaram/modificaram schemas
