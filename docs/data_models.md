# 📊 Data Models — Crypto Futures Agent

**Version:** 0.3.0 (Issue #67 Data Strategy LIVE)
**Last Updated:** 28 FEV 2026
**Owner:** Data Engineer (#11), Architect (#6)

---

## 📋 Overview

This document defines all data structures, ORM schemas, and exchange models used in the
Crypto Futures Agent. Data flows through **4 layers**: Raw API → Database → Cache →
Application.

---

## 1️⃣ Exchange Data Models

### Binance Kline (OHLCV Candlestick)

**Source:** `/fapi/v1/klines` endpoint
**Interval:** 4h (selected per Issue #67)
**Data Points per Symbol per Year:** 2,190 candles (365 days × 6 candles/day)

#### Raw API Response

```json
{
  "symbol": "BTCUSDT",
  "interval": "4h",
  "klines": [
    [
      1761052800000,     // [0] open_time (Unix ms)
      "67432.10",        // [1] open
      "69105.50",        // [2] high
      "67200.00",        // [3] low
      "68901.23",        // [4] close
      "12345.67",        // [5] volume (base asset)
      1761066000000,     // [6] close_time
      "850123456.78",    // [7] quote_volume (USDT)
      543,               // [8] trades
      "6789.12",         // [9] taker_buy_base_volume
      "456789123.45",    // [10] taker_buy_quote_volume
      "0"                // [11] ignore
    ],
    ...
  ]
}
```

#### Python DataClass Model

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Kline:
    """OHLCV candlestick from Binance Futures 4h interval."""

    # Identification
    symbol: str                    # e.g., "BTCUSDT"
    interval: str = "4h"          # Fixed at 4h (Issue #67)

    # Timestamps (Unix milliseconds)
    open_time: int                # Bar open
    close_time: int               # Bar close

    # OHLC Prices
    open: float                   # Opening price
    high: float                   # Highest price in bar
    low: float                    # Lowest price in bar
    close: float                  # Closing price

    # Volumes
    volume: float                 # Base asset volume (BTC for BTCUSDT)
    quote_volume: float           # Quote asset volume (USDT)

    # Trading Activity
    trades: int                   # Number of trades in bar
    taker_buy_volume: float       # Aggressive buyer volume
    taker_buy_quote_volume: float # Aggressive buyer quote volume

    # Metadata
    is_validated: bool = False    # Passed integrity checks
    sync_timestamp: Optional[datetime] = None  # When cached

    @property
    def datetime(self) -> datetime:
        """Convert Unix ms to datetime (UTC)."""
        return datetime.utcfromtimestamp(self.open_time / 1000)

    @property
    def mid_price(self) -> float:
        """Average of high + low."""
        return (self.high + self.low) / 2

    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors = []

        # Price order
        if not (self.low <= self.open <= self.high):
            errors.append(f"Preço aberto ({self.open}) fora [low, high]")
        if not (self.low <= self.close <= self.high):
            errors.append(f"Pre\u00e7o fechado ({self.close}) fora [low, high]")

        # Volume
        if self.volume < 0:
            errors.append(f"Volume negativo ({self.volume})")
        if self.trades <= 0:
            errors.append(f"Trades <= 0 (candle suspeito)")

        # Quote volume consistency
        if self.quote_volume < 0:
            errors.append(f"Quote volume negativo")

        return errors
```

---

## 2️⃣ Database Models (SQLite)

### Table: `klines`

Stores all historical candlesticks (1Y × 60 symbols = 131,400+ records).

```sql
CREATE TABLE klines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                  -- "BTCUSDT"
    open_time INTEGER NOT NULL,            -- Unix ms (partition key)
    open REAL NOT NULL,                    -- Price
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,                  -- Base volume
    close_time INTEGER NOT NULL,
    quote_volume REAL NOT NULL,            -- USDT volume
    trades INTEGER,
    taker_buy_volume REAL,
    taker_buy_quote_volume REAL,
    is_validated BOOLEAN DEFAULT 0,        -- QA flag
    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(symbol, open_time),             -- Prevent duplicates
    CHECK (low <= open AND low <= close AND high >= open AND high >= close)
);

CREATE INDEX idx_symbol_time ON klines(symbol, open_time);  -- Query klines by symbol + time
CREATE INDEX idx_validated ON klines(is_validated);          -- Find non-validated records
```

### Table: `sync_log`

Audit trail for data synchronization operations.

```sql
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,                  -- Which symbol
    sync_type TEXT NOT NULL,               -- "fetch_full" or "sync_daily"
    rows_inserted INTEGER,                 -- How many new rows
    rows_updated INTEGER,                  -- How many updated
    start_time INTEGER,                    -- Unix seconds
    end_time INTEGER,
    duration_seconds REAL,                 -- Elapsed time
    status TEXT,                           -- "success" or "error"
    error_message TEXT,                    -- If error
    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Index
    FOREIGN KEY (symbol) REFERENCES klines(symbol)
);

CREATE INDEX idx_sync_symbol ON sync_log(symbol);
```

---

## 3️⃣ Application Models (Python ORM)

### Position Model

Represents an open or closed trade position.

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime

class PositionStatus(Enum):
    OPENING = "opening"       # Order placed, awaiting fill
    OPEN = "open"            # Entry filled
    CLOSING = "closing"      # Exit order placed
    CLOSED = "closed"        # Exit filled + P&L calculated

class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"

@dataclass
class Position:
    """Represents single trade position."""

    # Identification
    position_id: str                       # Unique ID (UUID)
    symbol: str                           # "BTCUSDT"
    side: PositionSide                    # LONG or SHORT
    status: PositionStatus = PositionStatus.OPENING

    # Timing
    entry_time: datetime = field(default_factory=datetime.utcnow)
    exit_time: Optional[datetime] = None

    # Sizing
    quantity: float                       # BTC (base asset qty)
    entry_price: float                   # Entry fill price
    exit_price: Optional[float] = None    # Exit fill price (None if open)

    # Orders
    entry_order_id: Optional[str] = None
    exit_order_id: Optional[str] = None

    # Risk Management
    stop_loss_price: float                # Static SL (2% below entry)
    take_profit_price: float              # Static TP (6% above entry)
    trailing_stop_pct: float = 0.015      # 1.5% trailing stop

    # P&L Tracking
    entry_margin: float = 0.0             # USDT margin used
    current_markup: Optional[float] = None  # Current P&L %
    realized_pnl: Optional[float] = None  # Final P&L (USDT)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_open(self) -> bool:
        return self.status in [PositionStatus.OPENING, PositionStatus.OPEN]

    @property
    def pnl_pct(self) -> Optional[float]:
        """Current P&L as percentage of entry price."""
        if not self.exit_price or self.is_open:
            return None
        if self.side == PositionSide.LONG:
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        else:  # SHORT
            return (self.entry_price - self.exit_price) / self.entry_price * 100

    def calculate_stop_loss_prices(self):
        """Set SL/TP based on entry price + 2%/6% rules."""
        if self.side == PositionSide.LONG:
            self.stop_loss_price = self.entry_price * 0.98      # -2%
            self.take_profit_price = self.entry_price * 1.06    # +6%
        else:  # SHORT
            self.stop_loss_price = self.entry_price * 1.02      # +2%
            self.take_profit_price = self.entry_price * 0.94    # -6%
```

### Signal Model

Price action signal detected by SMC strategy.

```python
from dataclasses import dataclass
from typing import Optional

class SignalType(Enum):
    BUY = "buy"           # Order block completion
    SELL = "sell"         # Break of structure
    NEUTRAL = "neutral"   # No signal

@dataclass
class Signal:
    """SMC signal candidate for entry."""

    # Identification
    symbol: str
    signal_type: SignalType
    timeframe: str              # "D1", "H4", "H1"

    # Detection Details
    detected_time: datetime     # When detected
    order_block_low: float      # OB lower bound
    order_block_high: float     # OB upper bound
    break_price: float          # BoS trigger price

    # Confidence
    volume_confirmed: bool      # Volume >= threshold?
    multi_tf_valid: bool        # H4 + H1 aligned?
    ppo_confidence: float       # 0.0-1.0 from model

    # Recommendations
    suggested_entry: float      # Recommended entry price
    suggested_sl: float         # Calculated SL
    suggested_tp: float         # Calculated TP (3× risk)

    # Status
    traded: bool = False        # Position opened?
    position_id: Optional[str] = None
```

### Trade Report Model

Historical trade record for backtesting + analysis.

```python
@dataclass
class TradeReport:
    """Completed trade with all metrics."""

    # Identity
    trade_id: str
    symbol: str
    date: datetime

    # Execution
    entry_price: float
    exit_price: float
    quantity: float

    # P&L
    gross_pnl: float           # Entry to exit profit/loss
    net_pnl: float             # Gross - fees (TODO: fee calc)
    pnl_pct: float             # % return

    # Duration
    entry_time: datetime
    exit_time: datetime
    duration_hours: float

    # Metadata
    reason_entry: str          # "SMC Order Block"
    reason_exit: str           # "TP", "SL", "Time", etc.
    max_profit: float          # Peak profit during hold
    max_loss: float            # Largest drawdown during hold

    def is_win(self) -> bool:
        return self.net_pnl > 0
```

---

## 4️⃣ Configuration Models

### Symbol Configuration

```python
@dataclass
class SymbolConfig:
    """Per-symbol trading parameters."""

    symbol: str                    # "BTCUSDT"

    # Position Sizing
    position_size_usd: float = 500.0  # Max margin per position
    max_leverage: float = 3.0         # Max 3× (Issue #67 rule)

    # Risk Management
    stop_loss_pct: float = 0.02       # 2% static SL
    take_profit_pct: float = 0.06     # 6% static TP
    trailing_stop_pct: float = 0.015  # 1.5% trailing

    # Strategy Parameters
    rsi_oversold: float = 40.0        # RSI threshold
    adx_min: float = 20.0             # ADX strength

    # Exchange
    binance_symbol: str = "BTCUSDT"   # Binance pair
    active: bool = True               # Include in trading
```

### Portfolio State

```python
@dataclass
class PortfolioState:
    """Real-time portfolio snapshot."""

    # Capital
    initial_capital: float           # Starting balance ($10,000)
    current_balance: float           # Available
    equity: float                    # Balance + unrealized P&L

    # Positions
    open_positions: list[Position]   # Currently held
    num_open: int                    # Count
    max_positions: int = 5           # Limit

    # P&L
    realized_pnl: float             # Closed trades total
    unrealized_pnl: float           # Open trades total
    total_pnl: float                # realized + unrealized
    pnl_pct: float                  # Total % return

    # Risk Metrics
    margin_used: float              # USDT in use
    margin_ratio: float             # equity / margin_used
    max_drawdown: float             # Peak-to-trough decline

    # Gates
    circuit_breaker_triggered: bool = False
    portfolio_safe: bool = True     # margin_ratio >= 300%?

    def is_portfolio_safe(self) -> bool:
        """Check if margin ratio >= 300% (2× leverage limit)."""
        return self.margin_ratio >= 3.0

    def calculate_max_position_size(self) -> float:
        """Max USD for next position given current margin."""
        # Max leverage = 3×, so max margin = equity × 3
        return self.equity * 3 - self.margin_used
```

---

## 5️⃣ JSON Configuration Files

### symbols.json (Issue #67)

```json
{
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "active": true,
      "position_size_usd": 500,
      "max_leverage": 3.0
    },
    {
      "symbol": "ETHUSDT",
      "active": true,
      "position_size_usd": 500,
      "max_leverage": 3.0
    },
    ...
  ],
  "total_symbols": 60,
  "updated": "2026-02-28T18:30:00Z"
}
```

### klines_meta.json (Cache Metadata)

```json
{
  "version": "1.0",
  "generated_at": "2026-02-28T00:57:12Z",
  "symbols_complete": 51,
  "symbols_partial": 4,
  "symbols_error": 5,
  "total_candles": 131400,
  "timeframe": "4h",
  "year_span": "1",
  "database": {
    "path": "data/klines_cache.db",
    "size_bytes": 650000,
    "tables": ["klines", "sync_log"]
  },
  "parquet_backup": {
    "path": "data/klines_cache.parquet",
    "size_bytes": 580000
  }
}
```

---

## 6️⃣ API Request/Response Models

### FetchKlinesRequest

```python
@dataclass
class FetchKlinesRequest:
    symbol: str                    # "BTCUSDT"
    interval: str = "4h"
    start_time: Optional[int] = None    # Unix ms
    end_time: Optional[int] = None
    limit: int = 1500             # Binance max per request
```

### FetchKlinesResponse

```python
@dataclass
class FetchKlinesResponse:
    success: bool
    symbol: str
    klines: list[Kline]
    count: int                    # Actual returned
    duration_ms: float            # API latency
    error: Optional[str] = None
```

---

## 🗂️ Data Dictionary

| Field | Type | Unit | Valid Range | Notes |
|-------|------|------|-------------|-------|
| open_time | int | Unix ms | 1704067200000–∞ | 1 JAN 2024 onwards |
| price | float | USDT | > 0 | High/Low/Open/Close |
| volume | float | BTC (etc.) | ≥ 0 | Base asset quantity |
| quote_volume | float | USDT | ≥ 0 | USDT value |
| trades | int | count | > 0 | Reject if ≤ 0 |
| position_size | float | USDT | 0–500 | Per symbol limit |
| leverage | float | ratio | 1–3 | Max 3× (margin ≥ 300%) |
| margin_ratio | float | ratio | ≥ 2.0 | Liquidation threshold |

---

## 🔗 Related Documents

- [architecture.md](architecture.md) — System design + layers
- [ISSUE_67_DATA_STRATEGY_SPEC.md](ISSUE_67_DATA_STRATEGY_SPEC.md) — Cache implementation
- [FEATURES.md](FEATURES.md) — Feature roadmap
- [config/symbols.json](../config/symbols.json) — Live symbol config

