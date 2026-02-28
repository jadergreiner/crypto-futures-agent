# 🏗️ Arquitetura — Crypto Futures Agent

**Versão:** 0.3.0 (Issue #67 Data Strategy LIVE)
**Atualizado:** 28 FEV 2026
**Responsável:** Arquiteto (#6)

---

## 📐 Visão Geral

O Crypto Futures Agent é um **sistema modular e seguro** que
combina análise de preços SMC com aprendizado de máquina (PPO).
A arquitetura prioriza **segurança operacional**, **integridade
de dados** e **backtesting determinístico**.

### Camadas Principais

```text
┌──────────────────────────────────────────────┐
│          Interface do Usuário                │
│   (menu.py, iniciar.bat, dashboard)          │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│  Execução e Gerenciamento de Risco           │
│  (OrderExecutor, PositionManager, RiskGates) │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│  Motor de Estratégia (SMC + ML Inference)    │
│  (SMCAnalyzer, PPOInference, Heuristics)     │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│  Camada de Dados e Cache (Issue #67)         │
│  (KlinesOrchestrator, SQLite, Parquet, API)  │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────┴─────────────────────────────┐
│     Infraestrutura e Monitoramento            │
│  (Logs, DB, Rate Limiting, Métricas)         │
└──────────────────────────────────────────────┘
```

---

## 📦 Módulos Principais

### 1. Camada de Dados (`data/`)

**Propósito:** Ingestão, cache e validação de dados históricos.

| Módulo | Propósito | Status |
|--------|-----------|--------|
| klines_cache_manager.py | Busca 1Y × 60 símbolos | ✅ Live |
| binance_client.py | Wrapper API Binance | ✅ Validado |
| sync_daily.py | Sincronização incremental | 🟡 Planejado |

**Características principais:**

- ✅ Conformidade com rate limit (1200 req/min)
- ✅ Backoff exponencial para erros 429
- ✅ Detecção de duplicatas
- ✅ SQLite + Parquet dual cache
- ✅ Latência <100ms no cache

**Data Flow:**
```
Binance API ─(REST, 4h)─> RateLimitManager
                           ├─→ KlinesFetcher
                           ├─→ KlineValidator
                           └─→ KlinesOrchestrator
                                  │
                         ┌────────┴────────┐
                    SQLite (650 KB)    Parquet (580 KB)
```

---

### 2. Strategy Layer (`agent/`, `data/strategies/`)

**Purpose:** Price analysis, signal generation, ML inference.

| Module | Purpose | Status |
|--------|---------|--------|
| `smc_analyzer.py` | Order Blocks + Break of Structure | ✅ Live |
| `heuristics.py` | Multi-timeframe validation (D1→H1) | ✅ Live |
| `rl_agent.py` | PPO model training + inference | 🔄 Training (TASK-005) |
| `feature_engineering.py` | RSI, ADX, EMA, volume features | ✅ Live |

**Entry Rules (Current Heuristics):**
1. SMC Order Block detected on H4
2. EMA 21 > EMA 50 (uptrend)
3. RSI > 40 (not overbought)
4. ADX > 20 (directional strength)
5. Multi-timeframe validation (D1 context)

**Exit Rules:**
- Static SL: 2% below entry
- Static TP: 3× risk (6% above entry)
- Trailing SL: 1.5% TrailingStopManager
- Time-based: 48h max duration

---

### 3. Execution Layer (`execution/`)

**Purpose:** Order placement, position management, risk enforcement.

| Module | Purpose | Status |
|--------|---------|--------|
| `order_executor.py` | Place / cancel / fill tracking | ✅ Live (100% vol) |
| `position_manager.py` | LIFO + closing orchestration | ✅ Live |
| `trailing_stop_manager.py` | Dynamic stop loss adjustment | ✅ Live (S2-4) |

**Risk Controls (Inviolable):**
- Position sizing: $500 max per symbol
- Leverage cap: 3× (60% margin usage)
- Portfolio drawdown: -5% circuit breaker
- Single symbol drawdown: -3% emergency stop
- Max positions: 5 concurrent
- Liquidation prevention: 200% margin buffer

---

### 4. Risk & Treasury (`risk/`, `execution/treasury.py`)

**Purpose:** Capital allocation, risk metrics, compliance gates.

| Component | Purpose | Status |
|-----------|---------|--------|
| `RiskGates` | Validate position sizing + leverage | ✅ Live |
| `TreasuryManager` | Track margin + balance + P&L | ✅ Live |
| `CircuitBreaker` | Emergency stop mechanisms | ✅ Live |

**Key Metrics:**
- Initial capital: $10,000 (configurable)
- Current balance tracking (real-time)
- Margin ratio: Must stay $\geq$ 300% (2× leverage)
- Max leverage: 3× (margin ratio $\geq$ 200%)
- Drawdown tolerance: -5% (stops all trading)

---

### 5. Backtesting Engine (`backtest/`)

**Purpose:** Historical simulation, performance validation.

| Module | Purpose | Status |
|--------|---------|--------|
| `backtester.py` | Deterministic OHLC replay | 🟡 Ready (Issue #67) |
| `metrics.py` | Sharpe, MaxDD, Calmar, Win Rate, PF, CL | 🟡 Ready |
| `reports.py` | Equity curve, drawdown, trade log | 🟡 Ready |

**Metrics Calculated:**
- **Sharpe Ratio**: Risk-adjusted return (target ≥ 1.0)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: % profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Calmar Ratio**: Return / Max Drawdown
- **Consecutive Losses**: Streak analysis

---

### 6. Configuration (`config/`)

**Purpose:** Symbol list, parameters, settings.

| File | Purpose |
|------|---------|
| `symbols.json` | 60 core trading pairs (Binance Futures) |
| `symbols_extended.json` | 200 expanded pairs (Future) |
| `params.yaml` | Strategy parameters, risk limits |

---

## 🔄 Data Flow Diagram

### Live Trading Flow

```
Event: Market opens (02:00 UTC)
     │
     ├─→ [1] Fetch latest 4h candles (Binance API)
     │        └─→ RateLimitManager respects <1200/min
     │        └─→ Sync to SQLite cache
     │
     ├─→ [2] SMC Analysis on all 60 symbols
     │        ├─→ Order Block detection
     │        ├─→ Break of Structure?
     │        └─→ Multi-timeframe validation
     │
     ├─→ [3] Feature Engineering
     │        ├─→ RSI, ADX, EMA calculation
     │        ├─→ Volume + volatility metrics
     │        └─→ Normalize for PPO input
     │
     ├─→ [4] PPO Inference (each signal candidate)
     │        └─→ Confidence score 0.0–1.0
     │
     ├─→ [5] Risk Gate Validation
     │        ├─→ Position size OK?
     │        ├─→ Leverage OK?
     │        ├─→ Portfolio drawdown OK?
     │        └─→ → GO / NO-GO
     │
     ├─→ [6] Order Execution (if GO)
     │        ├─→ Place LIMIT order (Binance API)
     │        ├─→ Track fill status
     │        ├─→ Update PositionManager
     │        └─→ Log trade
     │
     └─→ [7] Monitoring (every 1h)
              ├─→ P&L tracking
              ├─→ Trailing SL adjustment
              ├─→ Exit signal detection
              └─→ Position closing orchestration
```

### Backtesting Flow

```
Input: 1Y historical data (131.400 candles, 60 symbols)
     │
     ├─→ [1] Load from SQLite/Parquet cache
     │        └─→ <100ms per symbol
     │
     ├─→ [2] Replay OHLC bars chronologically
     │        └─→ Deterministic order
     │
     ├─→ [3] For each bar: Run strategy (SMC + PPO)
     │        ├─→ Generate signals
     │        ├─→ Apply risk gates
     │        └─→ Simulate fills (open → close price)
     │
     ├─→ [4] Track equity, P&L, margin
     │        └─→ Detect circuit breaks
     │
     └─→ [5] Generate metrics report
              ├─→ Sharpe, MaxDD, Win Rate, etc.
              ├─→ Equity curve chart
              └─→ Trade log CSV
```

---

## 🔌 API Integrations

### Binance Futures API

**Endpoints Used:**
- `GET /fapi/v1/klines` — Historical candlesticks (1500 candles max)
- `POST /fapi/v1/order` — Place LIMIT orders
- `GET /fapi/v1/openOrders` — Fetch active orders
- `DELETE /fapi/v1/order` — Cancel order
- `GET /fapi/v1/account` — Margin ratio + balance

**Rate Limits:**
- 1200 weight / minute (global)
- 88 requests for 1Y × 60 symbols = 7% capacity
- Exponential backoff on 429 (Rate Limited)

---

## 🗂️ Database Schema

### SQLite: `klines` Table

```sql
CREATE TABLE klines (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,
  open_time INTEGER NOT NULL,         -- Unix ms
  open REAL, high REAL, low REAL, close REAL,
  volume REAL, quote_volume REAL,
  trades INTEGER,
  taker_buy_volume REAL,
  taker_buy_quote_volume REAL,
  is_validated BOOLEAN DEFAULT 0,
  sync_timestamp DATETIME,
  UNIQUE(symbol, open_time)
);
CREATE INDEX idx_symbol_time ON klines(symbol, open_time);
```

### SQLite: `sync_log` Table

```sql
CREATE TABLE sync_log (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,
  sync_type TEXT,                     -- "fetch_full", "sync_daily"
  rows_inserted INTEGER,
  rows_updated INTEGER,
  duration_seconds REAL,
  status TEXT,                        -- "success", "error"
  error_message TEXT,
  sync_timestamp DATETIME
);
```

---

## 🚀 Deployment Modes

### Paper Mode
- Simulated trading (no live orders)
- Complete data pipeline (real cache)
- Risk gates enforced (practice discipline)
- Usage: Development + validation

### Live Mode
- Real Binance Futures account
- $10,000 initial capital (configurable)
- All risk gates active (inviolable)
- Circuit breakers + emergency stops
- Usage: Production trading

---

## 📋 Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 15 FEV | SMC heuristics + order execution MVP |
| 0.2.0 | 22 FEV | TASK-011 200 symbols + Parquet optimization |
| 0.3.0 | 28 FEV | Issue #67 Data Strategy LIVE (1Y × 60 symbols) |

---

## 🔍 Key Design Decisions

1. **SQLite + Parquet Dual Cache**
   - SQLite: Structured queries, hot data, incremental updates
   - Parquet: Columnar compression, snapshots, long-term storage

2. **4h Candlesticks (Issue #67)**
   - Reason: Balance between granularity + historical depth (1Y fits <650 KB)
   - Trade-off: Lower frequency than intraday but sufficient for daily rebalancing

3. **Deterministic Backtesting**
   - Bar-by-bar replay (OHLC order: open → high/low → close)
   - No lookahead bias
   - Market hours only (excludes gaps)

4. **Risk-First Execution**
   - Gates validate **before** ordering (never bypass)
   - Circuit breakers trigger on portfolio drawdown
   - Margin buffer: 200% minimum (allows only 3× leverage)

---

## 🔗 Related Documents

- [data_models.md](data_models.md) — Data structures + ORM schema
- [ISSUE_67_DATA_STRATEGY_SPEC.md](ISSUE_67_DATA_STRATEGY_SPEC.md) — Data pipeline spec
- [DECISIONS.md](DECISIONS.md) — Architecture decision history
- [FEATURES.md](FEATURES.md) — Feature roadmap (F-H1 → F-ML3)

