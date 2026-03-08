# 🏗️ 24/7 Backtesting Infrastructure — Visual Architecture

## System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    CRYPTO FUTURES AGENT — 24/7 OPERATION                  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                       PROCESS LAYER                                 │ │
│  │                                                                      │ │
│  │  ┌─────────────────────────────┐    ┌──────────────────────────┐  │ │
│  │  │  LIVE TRADING (Main)        │    │ BACKTESTING (Subprocess) │  │ │
│  │  │                             │    │                          │  │ │
│  │  │ • Real Order Execution      │    │ • Historical Simulation  │  │ │
│  │  │ • WebSocket Streaming       │    │ • Strategy Testing       │  │ │
│  │  │ • Risk Gate + Protection    │    │ • Signal Validation      │  │ │
│  │  │ • PID: Main                 │    │ • PID: Child (isolated)  │  │ │
│  │  │ • CPU: 60%                  │    │ • CPU: 30%               │  │ │
│  │  │ • Memory: 260MB             │    │ • Memory: 300MB          │  │ │
│  │  └──────────┬──────────────────┘    └────────────┬─────────────┘  │ │
│  │             │                                    │                 │ │
│  │             └────────────────┬───────────────────┘                 │ │
│  │                              │                                     │ │
│  └──────────────────────────────┼─────────────────────────────────────┘ │
│                                 │                                        │
│                        Shared Read/Write                                 │
│                                 ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    SQLITE DATABASE                                │ │
│  │         db/crypto_agent.db (1.2 GB with backups)                 │ │
│  │                                                                   │ │
│  │  WAL Mode Enabled: Write-Ahead Logging                           │ │
│  │  • Live trading: Write + read ordens                             │ │
│  │  • Backtesting: Read-only historical data                        │ │
│  │  • No locks: Concurrent access safe                             │ │
│  │                                                                   │ │
│  │  Tables:                                                         │ │
│  │  • ohlcv_d1, ohlcv_h4, ohlcv_h1 (historical candles)            │ │
│  │  • indicadores_tecnico (pre-calculated indicators)              │ │
│  │  • sentimento_mercado (sentiment data)                          │ │
│  │  • macro_data (macro indicators from FRED)                      │ │
│  │  • trades (execution log from live trading)                     │ │
│  │                                                                   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

         ▲                                                    ▼

┌────────┴────────────────────────────────────────────────┬──────────┐
│                   JOB SCHEDULER                         │ MONITORING
│                  (APScheduler)                          │
│                                                         │
│  ┌─────────────────────────────────────────────┐       │  • Staleness
│  │  CRON JOBS (UTC Timezone)                   │       │    Detector
│  │                                             │       │
│  │  00:30 — DATA UPDATE                        │       │  • Health
│  │          Fetch +4 candles per symbol        │       │    Probe
│  │          Rate limit: 240 req/day✅           │       │
│  │                                             │       │  • Log
│  │  01:00 — DATA VALIDATION                    │       │    Monitor
│  │          Staleness check (D1/H4/H1)         │       │
│  │          Symbol coverage (>95%)             │       │  • Recovery
│  │          Continuity (no gaps)               │       │    Automation
│  │                                             │       │
│  │  02:00 — SENTIMENT/MACRO UPDATE             │       │
│  │          Market sentiment from Binance      │       │
│  │          Macro indicators from FRED API     │       │
│  │                                             │       │
│  │  03:00 — BACKUP & COMPACT (Sunday)          │       │
│  │          3×Local + 1×Offsite (3-3-1 policy)│       │
│  │          VACUUM to compact DB               │       │
│  │                                             │       │
│  │  04:00 — ALERT DIGEST                       │       │
│  │          Send Telegram summary              │       │
│  │                                             │       │
│  │  23:30 — DAILY BACKTEST                     │       │
│  │          Run full strategy backtest         │       │
│  │          Duration: ~2 hours                 │       │
│  │          Save results → backtest/results/   │       │
│  │                                             │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘


```

---

## Resource Allocation

### Memory (1.0-1.5 GB Total)

```
┌─────────────────────────────────────────────┐
│          MEMORY BREAKDOWN                   │
├─────────────────────────────────────────────┤
│                                             │
│  Live Trading Process:        260 MB        │
│  ├─ PPO Model loaded:         150 MB        │
│  ├─ DataFrames cache (250 H4): 80 MB       │
│  ├─ WebSocket buffers:         20 MB        │
│  └─ Order queue + metadata:    10 MB        │
│                                             │
│  Backtesting Process:         300 MB        │
│  ├─ PPO Model (own copy):     150 MB        │
│  ├─ Backtest env + trades:    100 MB        │
│  └─ Results buffers:           50 MB        │
│                                             │
│  OS + Framework:              400+ MB       │
│  ├─ Python interpreter:       250 MB        │
│  ├─ numpy/pandas/torch:       150 MB        │
│  └─ Buffer growth headroom:   100 MB        │
│                                             │
│  TOTAL (Safe):              1.0-1.5 GB ✅  │
│                                             │
└─────────────────────────────────────────────┘
```

### CPU Allocation

```
NORMAL OPERATION (Outside backtest window 23:30-01:30)
┌──────────────────────────────────────────────────────┐
│  Live Trading:         60-70%  (1.5-2 cores)         │
│  Backtesting:           0%     (sleeping)             │
│  System:               20-30%                         │
├──────────────────────────────────────────────────────┤
│  TOTAL:                ~80% (Safe)  ✅               │
└──────────────────────────────────────────────────────┘

PEAK OPERATION (Backtest running 23:30-01:30 UTC)
┌──────────────────────────────────────────────────────┐
│  Live Trading:         60-70%  (1.5 cores)           │
│  Backtesting:          25-30%  (1 core)              │
│  System:               5-10%                         │
├──────────────────────────────────────────────────────┤
│  TOTAL:                ~90% (Safe max)  ✅           │
└──────────────────────────────────────────────────────┘

RECOMMENDATION: 4-8 cores (4 min, 8 recommended)
```

### Storage Usage

```
┌─────────────────────────────────────────────┐
│        DATABASE STORAGE BREAKDOWN           │
├─────────────────────────────────────────────┤
│                                             │
│  OHLCV Data:                                │
│  ├─ D1 (1 year × 60 symbols):    2.6 MB   │
│  ├─ H4 (250 days × 60 symbols): 15.8 MB   │
│  ├─ H1 (209 days × 60 symbols): 63.0 MB   │
│                                             │
│  Indicators:                                │
│  ├─ D1/H4/H1 Technical Vars:   186.0 MB   │
│                                             │
│  Additional Tables:                         │
│  ├─ Market Sentiment (daily):    4.4 MB   │
│  ├─ Macro Data:                  0.1 MB   │
│  ├─ Trades (execution):          7.5 MB   │
│  ├─ Indices + Overhead:         15.0 MB   │
│                                             │
│  DATABASE SUBTOTAL:              294 MB    │
│                                             │
│  Backups (3-3-1 Policy):        882 MB    │
│  ├─ Local 3×:                  882 MB    │
│  ├─ Offsite 1× (separate):       294 MB   │
│                                             │
│  TOTAL WITH BACKUPS:           1.2 GB ✅  │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Data Flow During Backtest

```
                    DAILY BACKTEST FLOW (23:30 UTC)
                              │
                    ┌─────────▼─────────┐
                    │  Daemon Wakeup    │
                    │  (subprocesso)    │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Load Historical  │
                    │  Data (H4 250d)   │
                    │  × 60 symbols     │
                    │  Unfiltered: OK✅ │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Strategy Engine   │
                    │  • SMC signals     │
                    │  • Entry rules     │
                    │  • Risk checks     │
                    │  ~100-150 candles  │
                    │  of stepping       │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Performance Calc  │
                    │  • Win rate        │
                    │  • Profit factor   │
                    │  • Sharpe ratio    │
                    │  • DD analysis     │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Save Results      │
                    │  backtest/results/ │
                    │  JSON format       │
                    │  + Timestamp log   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Sleep until       │
                    │  next schedule     │
                    │  (24h later)       │
                    └────────────────────┘

TIME: ~2 hours max | CPU: 30% | Memory: 300MB
DATABASE: Read-only for OHLCV | Write-only for results
```

---

## Failure Scenarios & Response

```
┌────────────────────────────────────────────────────────────────┐
│                    INCIDENT DETECTION                         │
└────────────────────────────────────────────────────────────────┘

SCENARIO 1: Process Died
────────────────────────
  Detector: health_probe.py checks PID file
  Trigger: PID file empty or process not running
  Action: Attempt graceful restart (3× backoff)
  Time: 5 minutes to restart
  Status: Auto-recovery ✅

SCENARIO 2: Heartbeat Stale
────────────────────────────
  Detector: heartbeat file age > 2 minutes
  Indicator: Process hung (likely infinite loop)
  Action: Force kill + restart
  Time: 5 minutes to recover
  Status: Auto-recovery ✅

SCENARIO 3: Data Stale
───────────────────────
  Detector: staleness_detector.py checks timestamp
  Trigger: H4 > 24h old, H1 > 6h old
  Action: Retry data collection with exponential backoff
  Time: 15 minutes for recovery
  Status: Auto-recovery ✅

SCENARIO 4: Database Corrupted
────────────────────────────
  Detector: PRAGMA integrity_check fails
  Trigger: Bitflip or crash during write
  Action: Restore from backup (yesterday)
  Time: 30 minutes (restore + reindex)
  Status: Auto-recovery ✅

SCENARIO 5: Persistent Failure
───────────────────────────────
  Detector: 3+ crashes in 24 hours
  Trigger: Repeated restart failures
  Action: Manual rollback (48h ago)
  Time: 60 minutes (investigate + restore)
  Escalation: DRI investigates root cause
  Status: Manual recovery (last resort) 🟡

```

---

## Monitoring Dashboard (Sample Output)

```
┌─────────────────────────────────────────────────────────────────┐
│  BACKTEST MONITORING — Real-Time Status                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Process Health:                                                │
│    Status: ✅ HEALTHY                                           │
│    PID: 12847 | Uptime: 168h 23m | CPU: 28% | Memory: 312MB   │
│    Heartbeat Age: 8s (fresh) | Last Check: 2026-02-22 23:58   │
│                                                                 │
│  Data Freshness:                                                │
│    D1 Age: 2h 15m (OK ✅)     | Coverage: 60/60 ✅             │
│    H4 Age: 1h 05m (OK ✅)     | Coverage: 60/60 ✅             │
│    H1 Age: 35m    (OK ✅)     | Coverage: 60/60 ✅             │
│    Continuity: No gaps ✅                                       │
│                                                                 │
│  Last Backtest:                                                 │
│    Execution: 2026-02-22 23:30 — 01:45 UTC (135 min)          │
│    Symbols: 60 | Candles: ~15K                                 │
│    Win Rate: 58% | Sharpe: 1.8 | DD: -8.3%                    │
│    Status: ✅ PASSED (ready for live validation)               │
│                                                                 │
│  Recent Alerts:                                                 │
│    None 🎉 (clean 24h)                                         │
│                                                                 │
│  Resource Usage:                                                │
│    Memory: 312 MB / 1500 MB (21%)                              │
│    CPU: 28% (1 core allocated)                                 │
│    Disk: 1.2 GB / 20 GB (6%)                                   │
│                                                                 │
│  Estimation (Next 48h):                                         │
│    Backtest runs: 2 (daily 23:30)                              │
│    Data updates: 96 (~4 req/h)                                 │
│    Backups: 0 (next Sunday)                                    │
│    No issues detected ✅                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Before Go-Live

```
Setup & Configuration
☐ Enable WAL mode in database.py
☐ Configure APScheduler with UTC timezone
☐ Deploy backtest_config.py to config/
☐ Create backtest/results/ directory
☐ Create run/ directory for PID files
☐ Create logs/ directory for backtest logs

Code Deployment
☐ deploy backtest/daemon_24h7.py
☐ Deploy monitoring/staleness_detector.py
☐ Deploy monitoring/health_probe.py
☐ Integrate health probe into main.py monitoring thread
☐ Add subprocess launcher in main.py

Testing
☐ Unit tests: 80% coverage min
☐ Integration test: Full 24h dry run
☐ Failure simulation: Crash, hang, stale data
☐ Recovery test: Restore from backup

Monitoring Setup
☐ Configure Telegram alerts (@backtest_alerts_critical, etc)
☐ Setup on-call escalation path
☐ Document runbook for team
☐ Configure PagerDuty/Slack integration (if applicable)

Go-Live Approval
☐ DRI sign-off (The Blueprint #7)
☐ DevOps lead sign-off
☐ On-call engineer sign-off
☐ Board infrastructure review
```

---

## Success Criteria

After 7 days of 24/7 operation:

✅ **Uptime:** 99.5% (max 7.3 min downtime)  
✅ **Data Freshness:** 100% H4 candles updated daily  
✅ **Isolation:** Live trading unaffected by backtest CPU/memory  
✅ **Recovery:** All auto-recovery scenarios < 5 min  
✅ **Alerts:** < 1 false positive per day  
✅ **Backup:** 3+ daily restore tests pass  

---

**Created by:** The Blueprint (#7)  
**Status:** ✅ Ready for Implementation  
**Next:** Code Review → Staging E2E → Production Canary
