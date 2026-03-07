# 📚 Plano de Reestruturação de Documentação - Arquitetura de Database

**Data:** 2026-03-07
**Contexto:** Consolidação de dois bancos de dados e reorganização de docs
**Duração Estimada:** 45 minutos

---

## 1️⃣ docs/DATABASE_ARCHITECTURE.md (CRIAR)

**Objetivo:** Descrever schema completo, responsabilidades e fluxos de dados

**Seções Obrigatórias:**

```markdown
# Database Architecture

## Single Source of Truth: crypto_futures.db

### Overview
- **Location:** `db/crypto_futures.db`
- **Type:** SQLite 3
- **Primary Responsibility:** All trading operations, audit trail, agent decision history
- **Replicas/Backups:** (TBD)
- **Deprecated:** crypto_agent.db (consolidated 2026-03-07)

### High-Level Schema

#### 1. Core Trading Tables
| Table | Purpose | PK | FK | Updates |
|-------|---------|-----|-----|---------|
| trade_log | Trade lifecycle (entry→exit) | trade_id | - | position_monitor.py |
| execution_log | Order execution audit | id | - | order_executor.py |
| position_snapshots | Decision history + RL feedback | id | - | position_monitor.py |
| trade_signals | Signal identification | id | - | signal_generator.py |

#### 2. Market Data Tables
| Table | Purpose | Source | TTL |
|-------|---------|--------|-----|
| ohlcv_h1, h4, d1 | Candlestick data | Binance API | Real-time |
| indicadores_tecnico | Technical indicators | position_monitor.py | Per cycle |
| sentimento_mercado | Market sentiment | Binance API | Per cycle |
| smc_* | SMC market structure | position_monitor.py | Per cycle |

#### 3. Support Tables
| Table | Purpose |
|-------|---------|
| eventos_websocket | Real-time market events |
| relatorios | Generated reports |

### Detailed Table Schemas

#### trade_log
```sql
CREATE TABLE trade_log (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_entrada INTEGER NOT NULL,  -- Unix ms UTC
    timestamp_saida INTEGER,              -- NULL if open, Unix ms if closed
    symbol TEXT NOT NULL,                 -- E.g., "OGUSDT"
    direcao TEXT NOT NULL,                -- "LONG" or "SHORT"
    entry_price REAL NOT NULL,
    exit_price REAL,                      -- NULL if open
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    pnl_usdt REAL,                        -- NULL if open
    pnl_pct REAL,                         -- NULL if open
    r_multiple REAL,
    leverage INTEGER,
    margin_type TEXT,
    liquidation_price REAL,
    position_size_usdt REAL,
    motivo_saida TEXT,                    -- "SL_HIT", "TP_HIT", "MANUAL_CLOSE", etc
    unrealized_pnl_at_snapshot REAL,

    -- Binance order IDs (for reconciliation)
    binance_order_id TEXT,
    binance_sl_order_id TEXT,
    binance_tp_order_id TEXT,

    score_confluencia INTEGER,
    reward_total REAL
);
```
**Responsibility:** monitoring/position_monitor.py
**Access Pattern:** INSERT (entry) + UPDATE (exit, PnL)
**Read By:** audit_trail.py, scripts/audit_24h_operations.py, RL training

#### execution_log
```sql
CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,           -- Unix ms UTC
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,              -- "LONG" or "SHORT"
    action TEXT NOT NULL,                 -- "OPEN", "CLOSE", "REDUCE_50", "SET_SL", "SET_TP"
    executed INTEGER NOT NULL,            -- 1 = success, 0 = blocked
    mode TEXT NOT NULL,                   -- "paper" or "live"
    reason TEXT,                          -- Why executed or why blocked
    order_id TEXT,                        -- Binance order ID if executed
    fill_price REAL,
    fill_quantity REAL,
    commission REAL,
    entry_price REAL,
    mark_price REAL,
    unrealized_pnl REAL,
    risk_score REAL,
    decision_confidence REAL
);
```
**Responsibility:** execution/order_executor.py
**Access Pattern:** INSERT after each execution attempt
**Read By:** audit_trail.py, risk_gate.py (daily limit checks), scripts

#### position_snapshots
```sql
CREATE TABLE position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,

    -- Position data
    direction TEXT NOT NULL,
    entry_price REAL,
    mark_price REAL,
    position_size_qty REAL,
    leverage INTEGER,
    unrealized_pnl REAL,

    -- Technical indicators (at time of snapshot)
    rsi_14 REAL,
    ema_17 REAL,
    ema_34 REAL,
    ema_72 REAL,
    ema_144 REAL,
    macd_line REAL,
    macd_signal REAL,

    -- Agent decision
    agent_action TEXT,                    -- "HOLD", "CLOSE", "REDUCE_50"
    decision_confidence REAL,
    decision_reasoning TEXT,

    -- Risk assessment
    risk_score REAL,

    -- RL Training
    reward_calculated REAL,
    outcome_label TEXT
);
```
**Responsibility:** monitoring/position_monitor.py
**Access Pattern:** INSERT at each decision cycle (~1-2 per minute)
**Read By:** RL training, audits, analysis

#### trade_signals
```sql
CREATE TABLE trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,              -- "LONG" or "SHORT"
    entry_price REAL,
    confluence_score REAL,

    -- Technical context
    rsi_14 REAL,
    market_structure TEXT,

    -- Execution tracking
    execution_mode TEXT,                  -- "PENDING", "AUTOTRADE", "MANUAL", "CANCELLED"
    executed_at INTEGER,
    executed_price REAL
);
```
**Responsibility:** signal_generation module
**Access Pattern:** INSERT when signal identified, UPDATE on execution
**Read By:** audits, signal_evolution analysis

### Module → Database Access Matrix

| Module | Banco | Tabela | Tipo | Frequência |
|--------|-------|--------|------|-----------|
| monitoring/position_monitor.py | crypto_futures.db | trade_log, execution_log, position_snapshots | RW | Every cycle (1-2/min) |
| execution/order_executor.py | crypto_futures.db | execution_log | W | Per execution attempt |
| scripts/monitor_positions.py | crypto_futures.db | trade_log | U (UPDATE saida) | Per closure detected |
| risk/risk_gate.py | crypto_futures.db | execution_log | R (COUNT) | Per decision |
| logs/audit_trail.py | crypto_futures.db | trade_log, execution_log | R | On-demand |
| scripts/audit_24h_operations.py | crypto_futures.db | All | R | On-demand |
| RL training | crypto_futures.db | position_snapshots, trade_log | R | Batch/offline |

### Deprecated
- **crypto_agent.db:** ❌ **CONSOLIDATED** into crypto_futures.db (2026-03-07)
  - Former Tables:
    - execution_log (128 records) → MIGRATED
    - trade_signals (11 records) → MIGRATED
    - position_snapshots (13,756 records) → MIGRATED
  - Status: Archive only, do not write

### Constraints & Integrity

#### Foreign Keys (To Implement)
```sql
-- position_snapshots must reference a valid symbol from trade_log
ALTER TABLE position_snapshots
ADD CONSTRAINT fk_snapshots_symbol
CHECK (symbol IN (SELECT DISTINCT symbol FROM trade_log));
```

#### Orphan Detection (Queries)
```sql
-- Executions without corresponding trade
SELECT COUNT(*) as orphaned_execs
FROM execution_log e
WHERE NOT EXISTS (
    SELECT 1 FROM trade_log t WHERE t.symbol = e.symbol
);

-- Unclosed trades older than 30 days
SELECT * FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 - timestamp_entrada) > 2592000000;
```

### Data Retention Policy

| Table | Retention | Archive Strategy |
|-------|-----------|------------------|
| trade_log | Forever (operational history) | Monthly snapshots to Parquet |
| execution_log | 90 days online, 1 year archived | Partition by date |
| position_snapshots | 7 days online | Archive to S3/Parquet weekly |
| trade_signals | 30 days online | Archive by symbol |

### Backup & Recovery

```bash
# Daily backup
sqlite3 db/crypto_futures.db ".backup db/crypto_futures.db.backup_$(date +%Y%m%d)"

# Verify integrity
sqlite3 db/crypto_futures.db "PRAGMA integrity_check;"

# Recovery
cp db/crypto_futures.db.backup_YYYYMMDD db/crypto_futures.db
```

### Monitoring & Alerts

- **Size Check:** `SELECT page_count * page_size / 1024 / 1024 as size_mb FROM pragma_page_count(), pragma_page_size();`
- **Orphans:** Run integrity check daily (see Constraints section)
- **Staleness:** Alert if no trade_log updates in 24h
```

---

## 2️⃣ docs/REFERENTIAL_INTEGRITY.md (CRIAR)

**Objetivo:** Documentar relacionamentos e validações de integridade

```markdown
# Referential Integrity & Data Consistency

## Entity Relationships

### Trade Lifecycle (trade_log)
```
Entry Event:
  timestamp_entrada → agent_action = "OPEN" not recorded here
              ↓
  (position opened in Binance)
              ↓
  Entry timestamp + entry_price stored

Exit Event:
  agent_action = "CLOSE" OR SL/TP triggered
              ↓
  order sent to Binance (execution_log record created)
              ↓
  Order fills (fill_price recorded)
              ↓
  monitor_positions.py detects → UPDATE trade_log.timestamp_saida + pnl_usdt
```

### Execution Tracking (execution_log)
```
Decision → order_executor.execute()
           └─ INSERT execution_log (action, executed, reason)
                    ↓
             On Binance:
             - LIMIT/MARKET order placed
             - Order accepted or rejected
             - If filled: fill_price, fill_quantity recorded
                    ↓
             monitor_positions.py:
             - Detects position change
             - Links to corresponding trade_log
             - Updates trade_log.timestamp_saida
```

## Integrity Rules

### Rule 1: Every CLOSE Execution Must Have Trade
**Constraint:**
```sql
-- CLOSE/REDUCE executions must have corresponding trade
CREATE TRIGGER validate_close_execution
BEFORE INSERT ON execution_log
FOR EACH ROW
WHEN NEW.action IN ('CLOSE', 'REDUCE_50')
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM trade_log WHERE symbol = NEW.symbol
    )
    THEN RAISE(ABORT, 'No trade found for symbol: ' || NEW.symbol)
  END;
END;
```

### Rule 2: No Orphaned Executions
**Orphaned Execution:** execution_log record without any trade_log match
**Detection Query:**
```sql
SELECT * FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
  AND t.timestamp_entrada < e.timestamp
)
ORDER BY e.timestamp DESC;
```
**Action if Found:** Investigate gap, may indicate:
- Trade was liquidated before recorded
- Symbol changed or typo
- Data corruption

### Rule 3: No Stale Open Positions
**Rule:** Positions open > 30 days should be investigated
**Query:**
```sql
SELECT *
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 - timestamp_entrada) > 2592000000
ORDER BY timestamp_entrada ASC;
```
**Action:** Manual review or automatic liquidation

### Rule 4: PnL Calculation Consistency
**Rule:** If timestamp_saida IS NOT NULL, then pnl_usdt must be calculated
**Validation:**
```sql
SELECT COUNT(*) as pnl_missing
FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL);
```
**If > 0:** Data inconsistency, requires audit

### Rule 5: Execution Success vs Trade Closure
**Rule:** If execution.executed=1 AND action='CLOSE', then trade_log.timestamp_saida should be NOT NULL (within 60s)
**Timing:** Allows buffer for monitor_positions.py to process

## Validation Procedures

### Daily Validation Script

```bash
#!/bin/bash
# Daily at 00:00 UTC
sqlite3 db/crypto_futures.db << EOF

-- Report 1: Orphaned Executions
.title "=== ORPHANED EXECUTIONS ==="
SELECT COUNT(*) as count FROM execution_log e
WHERE NOT EXISTS (SELECT 1 FROM trade_log t WHERE t.symbol = e.symbol);

-- Report 2: Stale Open Trades
.title "=== STALE OPEN TRADES (> 30 days) ==="
SELECT symbol, timestamp_entrada, CURRENT_TIMESTAMP - timestamp_entrada as age_ms
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 - timestamp_entrada) > 2592000000;

-- Report 3: Missing PnL
.title "=== CLOSED TRADES WITH MISSING PNL ==="
SELECT COUNT(*) as count
FROM trade_log WHERE timestamp_saida IS NOT NULL AND pnl_usdt IS NULL;

-- Report 4: DB Size & Health
.title "=== DATABASE HEALTH ==="
SELECT 'Database Size (MB)' as metric, (page_count * page_size / 1024 / 1024.0) as value
FROM pragma_page_count(), pragma_page_size();
SELECT 'Record Count' as metric, COUNT(*) as value FROM trade_log;

EOF
```

### Manual Integrity Check Command

```bash
sqlite3 db/crypto_futures.db "PRAGMA integrity_check;"
```

## Audit Trail Requirements

When closing a trade manually or fixing data:
1. Log the change with timestamp
2. Record reason (SL_HIT, TP_HIT, MANUAL_OVERRI DE, etc.)
3. Update trade_log.motivo_saida
4. Create corresponding execution_log record (if missing)
5. Update docs/SYNCHRONIZATION.md with [FIX] tag

---

## 3️⃣ docs/DATA_FLOW_DIAGRAM.md (CRIAR)

**Objetivo:** Visualizar ciclo operacional do agente e fluxo de dados

```markdown
# Data Flow Diagram - Agent Operating Cycle

## Overview

Agent executes continuous cycle monitoring positions and making decisions.
Each cycle writes to multiple tables, building audit trail.

## Cycle Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT DECISION CYCLE                             │
│                    (Runs every 1-2 minutes)                         │
└─────────────────────────────────────────────────────────────────────┘

[1. Fetch Market Data]
        │
        ├─→ Binance API (position_monitor.py)
        │       └─→ Open positions, mark price, indicators
        │
        └─→ INSERT/UPDATE: ohlcv_h1, ohlcv_h4, indicadores_tecnico

[2. Analyze Position]
        │
        ├─→ Read: trade_log (historical trades)
        ├─→ Calculate: RSI, EMA, MACD, SMC, etc.
        │
        └─→ INSERT: smc_market_structure, sentimento_mercado

[3. Insert Snapshot]
        │
        └─→ INSERT position_snapshots
            (All current data + decision context for RL)

[4. Make Decision]
        │
        ├─→ decision_logic.evaluate_position()
        │       └─→ Returns: agent_action ∈ {HOLD, CLOSE, REDUCE_50}
        │
        └─→ UPDATE position_snapshots: agent_action, decision_confidence

[5. Execute Decision]
        │
        ├─→ IF agent_action == HOLD: SKIP execution
        │
        ├─→ ELSE: order_executor.execute()
        │       ├─ Insert execution_log record (before order)
        │       ├─ Send MARKET order to Binance
        │       └─ Update execution_log (fill_price, reason)
        │
        └─→ INSERT execution_log (with executed=1 or 0)

[6. Monitor Closure]
        │
        ├─→ monitor_positions.py (separate, running ~every 10s)
        │       ├─ Detects position changes in Binance
        │       ├─ If timestamp_saida IS NULL and position closed:
        │       │   └─ Calculate PnL: exit_price, pnl_usdt, pnl_pct
        │       │
        │       └─ UPDATE trade_log: timestamp_saida, pnl_usdt, etc.
        │
        └─→ Position now marked as CLOSED

[7. Audit & Reporting]
        │
        └─→ scripts/audit_24h_operations.py (on-demand)
            ├─ READ: trade_log, execution_log
            ├─ AGGREGATE: PnL, win rate, risk metrics
            └─ EXPORT: JSON + CSV for analysis
```

## Data Flow by Table

### trade_log Flow
```
INSERT (entry):
  - timestamp_entrada = NOW
  - entry_price = Binance mark price
  - stop_loss, take_profit = From agent decision
  - symbol, direcao, leverage, margin_type
  ↓
UPDATE (exit):
  - timestamp_saida = When position closed
  - exit_price = Fill price
  - pnl_usdt, pnl_pct = Calculated
  - motivo_saida = "SL_HIT", "TP_HIT", "MANUAL_CLOSE", etc.
  ↓
READ (audit):
  - audit_trail.py: Reconstruct PnL history
  - RL training: Extract reward signal
```

### execution_log Flow
```
INSERT:
  - timestamp = NOW (before order sent)
  - action = "OPEN", "CLOSE", "REDUCE_50", "SET_SL", "SET_TP"
  - executed = 0 initially (assumption: will execute)
  ↓
UPDATE:
  - executed = 1 OR 0 (after Binance response)
  - fill_price = Binance fill_price
  - reason = Why blocked if executed=0
  ↓
READ:
  - risk_gate.py: COUNT(executed=1) WHERE TODAY
  - audit: Analyze execution patterns
  - forensics: Debug why trades didn't close
```

### position_snapshots Flow
```
INSERT:
  - timestamp = NOW
  - All position data (mark_price, etc.)
  - All indicators (RSI, EMA, MACD)
  - agent_action = From decision logic
  - decision_confidence, risk_score
  - reward_calculated = NULL (computed later)
  ↓
UPDATE (optional):
  - reward_calculated = After trade closes (RL training)
  - outcome_label = "WIN", "LOSS", "NEUTRAL"
  ↓
READ:
  - RL training: Extract (state, action, reward) tuples
  - Audit: Analyze decision quality vs outcome
```

## Critical Sync Point: Trade Closure

This is where execution_log and trade_log meet:

```
Order Execution (execution_log):
  CLOSE action, executed=1, fill_price=100.50

     ↓↓↓ [CRITICAL SYNC] ↓↓↓

Position Closure Update (trade_log):
  timestamp_saida = order_timestamp
  exit_price = fill_price from execution
  pnl_usdt = (exit_price - entry_price) * qty * position_size

  ⚠️ If this sync doesn't happen:
     - trade_log.timestamp_saida stays NULL
     - Trade shows as "OPEN" in audits
     - PnL is 0 (missing data)
     - Inconsistency between logs!
```

**Current Responsibility:** `scripts/monitor_positions.py`
**Trigger:** Position no longer in Binance response (WebSocket or REST)
**Verification:** Check if trade_log updated within 60s of execution_log.timestamp

---

## 4️⃣ Atualizar docs/C4_MODEL.md

**Adicionar C4 Level 3 (Component Level) com database layer:**

Insert na seção "**Container Diagram**":

```markdown
### Component Diagram (Level 3)

Shows how Agent Trading System breaks down into components and their interactions with database:

[Agent Decision Logic Component]
    ├─ position_monitor.py (fetches positions, decides = CLOSE/HOLD)
    │   └─ writes to: trade_log, position_snapshots
    │
    └─ [Order Execution Component]
        └─ order_executor.py (sends orders to Binance)
            └─ writes to: execution_log

[Monitoring Component]
    └─ monitor_positions.py (detects closures)
        └─ updates: trade_log.timestamp_saida (critical sync!)

[Audit/RL Component]
    ├─ audit_trail.py (analyzes trades)
    ├─ RL training (uses position_snapshots)
    └─ reads from: trade_log, execution_log, position_snapshots

[Database] — crypto_futures.db (SINGLE SOURCE OF TRUTH)
    ├─ Tables: trade_log, execution_log, position_snapshots, trade_signals, ...
    ├─ Relationships: See docs/REFERENTIAL_INTEGRITY.md
    └─ Policy: Single-write, multi-read (optimized for analysis)
```

---

## 5️⃣ Atualizar docs/SYNCHRONIZATION.md

**Adicionar Seção: Database Synchronization Policy**

```markdown
## Database Consolidation & Single Source of Truth

### Status (2026-03-07)
- ✅ Analysis: Two databases identified (crypto_agent.db vs crypto_futures.db)
- ✅ Consolidation: crypto_futures.db selected as primary
- ⏳ Migration: PENDING (scheduled for Phase 3 of root cause remediation)

### Historical Databases
| Name | Status | Records | Reason |
|------|--------|---------|--------|
| crypto_agent.db | ❌ DEPRECATED | 128 exec, 13.7k snapshots | Logging system (parallel) |
| crypto_futures.db | ✅ PRIMARY | 7 trades, 0 exec | Main trading operations |

### Action Taken
- [SYNC] 2026-03-07: Identified dual-database issue in ROOT_CAUSE_ANALYSIS.md
- [SYNC] 2026-03-07: Created DATABASE_ARCHITECTURE.md as authoritative reference
- [TODO] Phase 3: Consolidate all data into crypto_futures.db
- [TODO] Phase 3: Archive/remove crypto_agent.db

### Write Policy
**ALL NEW WRITES:** crypto_futures.db (crypto_agent.db is read-only/archive)

### Module Mapping
See docs/DATABASE_ARCHITECTURE.md for complete module → database access matrix.
```

---

## 6️⃣ Criar reports/db_integrity_check.sql (CRIAR)

**Objetivo:** Script SQL reutilizável para validaçãoautomática

Colocar em arquivo: `reports/db_integrity_check.sql`

```sql
-- Database Integrity Check Script
-- Run daily or before major operations
-- Usage: sqlite3 db/crypto_futures.db < reports/db_integrity_check.sql

.headers on
.mode column

-- Report 1: Summary
SELECT '==== DATABASE INTEGRITY CHECK ====' as report;
SELECT datetime('now', 'utc') as timestamp;
SELECT '' as blank;

-- Report 2: Table Record Counts
.title "=== RECORD COUNTS ==="
SELECT 'trade_log' as table_name, COUNT(*) as count FROM trade_log
UNION ALL
SELECT 'execution_log', COUNT(*) FROM execution_log
UNION ALL
SELECT 'position_snapshots', COUNT(*) FROM position_snapshots
UNION ALL
SELECT 'trade_signals', COUNT(*) FROM trade_signals;

-- Report 3: Orphaned Executions
.title "=== ⚠️ CRITICAL: ORPHANED EXECUTIONS ==="
SELECT COUNT(*) as orphaned_execs FROM execution_log e
WHERE NOT EXISTS (SELECT 1 FROM trade_log t WHERE t.symbol = e.symbol);

-- Report 4: Stale Open Trades
.title "=== ⚠️ STALE OPEN POSITIONS (> 30 days) ==="
SELECT
    trade_id, symbol,
    datetime(timestamp_entrada/1000, 'unixepoch') as opened_at,
    ROUND((strftime('%s', 'now') * 1000 - timestamp_entrada) / 86400000.0) as days_open
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 - timestamp_entrada) > 2592000000
ORDER BY timestamp_entrada ASC;

-- Report 5: Closed Trades with Missing PnL
.title "=== ⚠️ CLOSED TRADES WITH MISSING PnL ==="
SELECT COUNT(*) as missing_pnl_count
FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL);

-- Report 6: Database Size
.title "=== DATABASE SIZE & HEALTH ==="
SELECT
    'Database Size (MB)' as metric,
    ROUND((SELECT page_count * page_size / 1024.0 / 1024.0 FROM pragma_page_count(), pragma_page_size()), 2) as value
UNION ALL
SELECT 'Last Trade Entry', datetime((SELECT MAX(timestamp_entrada) FROM trade_log)/1000, 'unixepoch');

-- Report 7: Integrity Check
.title "=== INTEGRITY CHECK RESULT ==="
PRAGMA integrity_check;

SELECT '' as blank;
SELECT '==== END OF REPORT ====' as done;
```

---

## Checklist de Criação

- [ ] **DATABASE_ARCHITECTURE.md**
  - [ ] High-level overview
  - [ ] Detailed schema (6 main tables)
  - [ ] Module access matrix
  - [ ] Constraints & referential integrity rules
  - [ ] Backup & recovery procedures

- [ ] **REFERENTIAL_INTEGRITY.md**
  - [ ] Entity relationships diagram
  - [ ] 5 Main integrity rules
  - [ ] Orphan detection queries
  - [ ] Daily validation script template
  - [ ] Manual check commands

- [ ] **DATA_FLOW_DIAGRAM.md**
  - [ ] Cycle diagram (7 steps)
  - [ ] Per-table flow diagrams
  - [ ] Critical sync point documentation
  - [ ] Responsibility mapping

- [ ] **Atualizar C4_MODEL.md**
  - [ ] Adicionar Component Diagram (Level 3)
  - [ ] Mostrar database como container
  - [ ] Relacionamentos claros

- [ ] **Atualizar SYNCHRONIZATION.md**
  - [ ] Database consolidation section
  - [ ] Write policy
  - [ ] Historical status

- [ ] **db_integrity_check.sql**
  - [ ] Copy template file
  - [ ] Test queries
  - [ ] Add to CI/CD (future)

---

## Tempo Estimado por Documento

| Documento | Escrever | Revisar | Total |
|-----------|----------|---------|-------|
| DATABASE_ARCHITECTURE.md | 20 min | 5 min | 25 min |
| REFERENTIAL_INTEGRITY.md | 12 min | 3 min | 15 min |
| DATA_FLOW_DIAGRAM.md | 8 min | 2 min | 10 min |
| Atualizar C4_MODEL.md | 5 min | 2 min | 7 min |
| Atualizar SYNCHRONIZATION.md | 3 min | 1 min | 4 min |
| db_integrity_check.sql | 3 min | 1 min | 4 min |
| **TOTAL** | **51 min** | **14 min** | **45 min** |

---

**Status:** Ready for implementation
**Next Step:** Begin with DATABASE_ARCHITECTURE.md
