# 🏛️ C4 Model — Crypto Futures Agent

**Versão:** 0.3.0
**Data:** 28 FEV 2026
**Responsável:** Arkurat (#6)

---

## Nível 1: Contexto (System Context Diagram)

```
┌──────────────────────────────────────────────────────────┐
│                       OPERADOR                           │
│              (Gestor de Trading, Board)                  │
└─────────────────────┬──────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    ┌────────┐  ┌──────────┐  ┌──────────┐
    │ Iniciar│  │  Dashboard│  │  Telegram│
    │.bat    │  │  Web UI   │  │ Alerts   │
    └────────┘  └──────────┘  └──────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
        ┌────────────────────────────────┐
        │  CRYPTO FUTURES AGENT (APP)    │
        │                                │
        │ • SMC Analysis                 │
        │ • PPO Model Inference          │
        │ • Order Execution              │
        │ • Risk Management              │
        └────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Binance  │ │ SQLite   │ │ Parquet  │
    │Futures   │ │ Cache    │ │ Snapshots│
    │API (REST)│ │ (Local)  │ │ (S3)     │
    └──────────┘ └──────────┘ └──────────┘
```

**Descrição:**

- **Operador:** Interage via iniciar.bat, dashboard ou alerts Telegram
- **Sistema Central:** Orquestra análise SMC + ML inference + execução
- **Dados:** Armazena cache local (SQLite) + snapshots (Parquet)
- **Exchange:** Sincroniza com Binance Futures REST API em tempo real

---

## Nível 2: Containers (Technical Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE / INTERFACE                      │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │  iniciar.bat   │  │  menu.py    │  │  dashboard   │     │
│  │  (Batch)       │  │  (CLI)      │  │  (Web)       │     │
│  └────────────────┘  └─────────────┘  └──────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / CLI
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               PYTHON APPLICATION (crypto-futures-agent)     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ STRATEGY LAYER                                       │  │
│  │  • smc_analyzer.py (Order Blocks + BoS)             │  │
│  │  • rl_agent.py (PPO Model Inference)                │  │
│  │  • heuristics.py (Multi-timeframe Validation)       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ EXECUTION LAYER                                      │  │
│  │  • order_executor.py (Place / Cancel)               │  │
│  │  • position_manager.py (LIFO Closing)               │  │
│  │  • trailing_stop_manager.py (Dynamic SL)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ DATA LAYER                                           │  │
│  │  • klines_cache_manager.py (1Y × 60 Symbols)        │  │
│  │  • risk/risk_gates.py (Capital + Leverage Checks)   │  │
│  │  • backtest/backtester.py (Historical Simulation)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ PERSISTENCE LAYER                                    │  │
│  │  • SQLite (Local Cache): 650 KB                      │  │
│  │  • Parquet (Snapshots): 580 KB                       │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────┬───────────────────────┬──────────────────┘
                   │ REST API              │ File I/O
                   ▼                       ▼
        ┌──────────────────┐    ┌─────────────────────┐
        │ BINANCE FUTURES  │    │ LOCAL FILESYSTEM    │
        │                  │    │                     │
        │ /fapi/v1/klines  │    │ ./data/             │
        │ /fapi/v1/order   │    │ ./logs/             │
        │ /fapi/v1/account │    │ ./config/           │
        └──────────────────┘    └─────────────────────┘
```

**Componentes:**

1. **Cliente:** iniciar.bat (batch) → menu.py (CLI) → dashboard (web)
2. **Aplicação Python:** 4 camadas lógicas (Strategy, Execution, Data, Persistence)
3. **Externos:** Binance API + Sistema de Arquivos Local

---

## Nível 3: Componentes (Detailed Components)

```
┌─────────────────────────────────────────────────────────┐
│ STRATEGY LAYER                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SMCAnalyzer ◄──────────────┐                          │
│    │                         │                          │
│    ├─► Order Block Detection │                          │
│    ├─► Break of Structure     │ Feedback Loop          │
│    └─► Volume Validation      │                          │
│                               │                          │
│  HeuristicValidator ◄─────────┤                          │
│    │                           │                          │
│    ├─► Multi-timeframe (D1/H4/H1)                       │
│    ├─► RSI/ADX/EMA Indicators                           │
│    └─► Signal Confidence Scoring                        │
│                               │                          │
│  RLAgent (PPO Model) ◄────────┤                          │
│    │                           │                          │
│    ├─► Inference on Candidates │                          │
│    ├─► Confidence 0.0–1.0 Output                        │
│    └─► Model Version Management │                          │
│                               │                          │
│  MetricsUtils (TASK-005 v2) ◄─┤                          │
│    │                           │                          │
│    ├─► Unified Sharpe/PF/WR/DD calculations              │
│    ├─► Volatility floor + sanity checks                  │
│    └─► Shared by training_loop and final_validation      │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ EXECUTION LAYER                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  RiskGates                                              │
│    ├─► Capital Available Check                          │
│    ├─► Leverage Validation (≤ 3×)                       │
│    ├─► Portfolio Drawdown Check (-5% threshold)         │
│    └─► GO / NO-GO Decision                              │
│          │                                              │
│          ▼                                              │
│  OrderExecutor                                          │
│    ├─► Place LIMIT Order (Binance)                      │
│    ├─► Fill Status Tracking                             │
│    └─► Cancel Logic (if needed)                         │
│          │                                              │
│          ▼                                              │
│  PositionManager                                        │
│    ├─► LIFO Tracking (Last-In-First-Out)               │
│    ├─► P&L Calculation                                 │
│    ├─► SL/TP Management                                │
│    └─► Closing Orchestration                            │
│                                                         │
│  TrailingStopManager                                    │
│    └─► Dynamic SL Adjustment (1.5%)                     │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ DATA LAYER                                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  KlinesOrchestrator                                     │
│    ├─► RateLimitManager (<1200 req/min)                 │
│    ├─► KlinesFetcher (Binance API)                      │
│    ├─► KlineValidator (Integrity Checks)                │
│    └─► KlinesCache (SQLite + Parquet)                   │
│                                                         │
│  TreasuryManager                                        │
│    ├─► Capital Tracking                                │
│    ├─► Margin Calculation                              │
│    └─► Circuit Breaker Logic                            │
│                                                         │
│  Backtester                                             │
│    ├─► OHLC Bar Replay (Deterministic)                  │
│    ├─► Metrics Calculation (Sharpe, MaxDD, Calmar)      │
│    └─► Report Generation (Equity Curve)                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Nível 4: Código (Class Diagrams & Data Flows)

### Position Management Flow

```python
Signal (detected)
  │
  ├─► RiskGates.validate(signal)
  │     ├─► check_capital_available()
  │     ├─► check_leverage_limit(3.0)
  │     ├─► check_portfolio_drawdown(-5%)
  │     └─► return GO / NO-GO
  │
  ├─► [IF GO]
  │     │
  │     ├─► OrderExecutor.place_order(symbol, qty, entry_price)
  │     │     └─► Binance API: POST /fapi/v1/order
  │     │
  │     ├─► PositionManager.new_position(order_id, symbol, qty, entry)
  │     │     ├─► Create Position object
  │     │     ├─► Set SL = entry × 0.98 (2% below)
  │     │     ├─► Set TP = entry × 1.06 (6% above)
  │     │     └─► Store in portfolio
  │     │
  │     └─► [EVERY 1H]
  │           │
  │           ├─► TrailingStopManager.adjust_stop(position)
  │           │     └─► New SL = max(current SL, high × 0.985)
  │           │
  │           ├─► Monitor for exit signals (SL/TP hit)
  │           │
  │           └─► [IF EXIT SIGNAL]
  │                 │
  │                 ├─► OrderExecutor.place_exit_order(position)
  │                 │
  │                 ├─► PositionManager.close_position(position)
  │                 │     ├─► Calculate realized P&L
  │                 │     ├─► Update TreasuryManager
  │                 │     └─► Log trade to history
  │                 │
  │                 └─► Position marked CLOSED
  │
  └─► [IF NO-GO]
        └─► Signal ignored, no order placed
```

### Data Sync Flow (Issue #67)

```
┌──────────────────────┐
│ Binance Futures API  │
│ /fapi/v1/klines     │
└──────┬───────────────┘
       │ (4h candles)
       ▼
┌──────────────────────┐
│ RateLimitManager     │
│ <1200 req/min        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ KlinesFetcher        │
│ Batch: 1500 candles  │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ KlineValidator       │
│ • Price order check  │
│ • Trades > 0         │
│ • No duplicates      │
└──────┬───────────────┘
       │
       ├─────────────────────┐
       ▼                     ▼
┌──────────────────┐  ┌──────────────┐
│ SQLite Cache     │  │ Parquet      │
│ (Hot Data)       │  │ (Snapshots)  │
│ 650 KB           │  │ 580 KB       │
└──────────────────┘  └──────────────┘
       │
       └─► <100ms read latency ✅
```

---

## Decisões de Arquitetura Documentadas

| Decisão | Rationale | Trade-offs |
|---------|-----------|-----------|
| **4h Candlesticks** | Balance: granularidade + profundidade 1Y | ↔ Frequência menor que intraday |
| **SQLite + Parquet** | Hot (SQL) + Cold (columnnar) storage | ↔ Dupla manutenção |
| **LIFO Position Management** | Fair+ determinístico | ↔ Menos controle granular |
| **3× Max Leverage** | Risk tolerance | ↔ Menor upside |
| **Paper + Live Modes** | Praticar antes de produção | ↔ Code duplication |

---

## Referências

- [DECISIONS.md](DECISIONS.md) — ADRs formalizadas
- [ARCHITECTURE.md](ARCHITECTURE.md) — Arquitetura operacional consolidada
- [data_models.md](data_models.md) — ORM + Schemas

