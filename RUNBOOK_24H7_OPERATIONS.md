# 🆘 Operação 24/7 — Runbook de Maintenance & Recovery

**Role:** DevOps / Infrastructure Lead  
**Audience:** Operadores, On-Call Engineer, Incident Commander  
**Criticidade:** 🔴 P1 — Infraestrutura de Backtesting

---

## 📋 Quick Reference

| Problema | Sintoma | Fix | ETA |
|----------|---------|-----|-----|
| **Daemon morreu** | Health probe: DEAD | `python backtest/daemon_24h7.py &` | 2 min |
| **Dados obsoletos** | Staleness alert | Check collector status, retry manual | 15 min |
| **DB corrupto** | `PRAGMA integrity_check fail` | Restore backup de ontem | 30 min |
| **CPU spike** | CPU > 90% × 10min | Kill & restart daemon | 5 min |
| **3+ crashes × 24h** | Consecutive failures | Trigger rollback 48h | 60 min |

---

## 🔧 Daily Operation Checklist

### Start of Day (00:00 UTC)

- [ ] **Data Update Job** (scheduled 00:30)
  - Monitor `logs/backtest_24h7.log` for completion
  - Verify: `SELECT MAX(timestamp) FROM ohlcv_h4` shows today's candles
  - Alert if > 5 min late

- [ ] **Data Validation Job** (scheduled 01:00)
  - Check staleness: `H4 < 24h, H1 < 6h` old
  - Coverage: ≥ 95% of 60 symbols
  - Continuity: No gaps > 2 candles

- [ ] **Sentiment/Macro Update** (scheduled 02:00)
  - Verify `sentimento_mercado` table updated
  - Macro data from FRED API loaded

### During Day

- [ ] **Every Hour** (Automated via health probe)
  - Daemon process alive? ✅
  - Heartbeat fresh (< 2 min old)? ✅
  - CPU < 90%? ✅
  - Memory < 500MB? ✅

- [ ] **If Backtest Running** (23:30-01:30)
  - Monitor: CPU (main: 60%, backtest: 30%) = 90% total ✅
  - Monitor: Memory stable < 1.5 GB
  - No log errors > 5/minute

### End of Week (Saturday 23:59 UTC)

- [ ] **Backup & Compact** (Sunday 03:00)
  - DB backup created: `db_backup_YYYYMMDD.db`
  - Storage: < 1.2 GB used
  - Backup tested (dry restore on staging)

- [ ] **Integrity Check**
  ```bash
  sqlite3 db/crypto_agent.db "PRAGMA integrity_check"
  # Output should be: "ok"
  ```

---

## 🚨 Incident Response

### Scenario 1: Daemon Crashed

**Symptom:** 
```
Health probe: status=DEAD
PID file empty or invalid
Backtest results stale > 2h
```

**Recovery (5 min):**

```bash
# 1. Verify crash (don't restart yet if within 5 min)
ps aux | grep daemon_24h7.py  # Should show nothing or [defunct]

# 2. Check logs for root cause
tail -100 logs/backtest_24h7.log | grep -i error

# 3. Quick diagnosis
python -c "
from data.database import DatabaseManager
db = DatabaseManager('db/crypto_agent.db')
result = db.check_integrity()
print('DB OK' if result else 'DB CORRUPTED')
"

# 4. Restart if DB OK
if [ $? -eq 0 ]; then
    python backtest/daemon_24h7.py > /tmp/backtest_daemon.log 2>&1 &
    echo "Daemon restarted"
else
    echo "DB corrupted, escalate to recovery"
fi
```

### Scenario 2: Data Staleness Alert

**Symptom:**
```
H4 data > 24 hours old
H1 data > 6 hours old
Coverage < 95%
```

**Recovery (15-30 min):**

```bash
# 1. Check if Binance API is down
curl -s "https://api.binance.com/api/v3/time" | head -1
# Should return valid timestamp

# 2. Check rate limit status
python -c "
from data.rate_limit_manager import RateLimitManager
rm = RateLimitManager()
print(f'Rate limit requests: {rm._request_count_in_window}')
"

# 3. If API OK, retry data update manually
python data/collector.py --mode=update --symbols=BTCUSDT,ETHUSDT
# Will backfill missing candles

# 4. Monitor completion
sqlite3 db/crypto_agent.db \
    "SELECT symbol, MAX(timestamp) FROM ohlcv_h4 GROUP BY symbol LIMIT 5"
# Should show recent timestamps (within last 4 hours)

# 5. If still failing, escalate to data recovery
```

### Scenario 3: Database Corruption

**Symptom:**
```
PRAGMA integrity_check returns: "row 5 missing from index..."
Query timeouts or returns garbage
```

**Recovery (30-60 min):**

```bash
# 1. STOP all processes immediately
pkill -f main.py
pkill -f daemon_24h7.py
touch db/LOCKED

# 2. Diagnose severity
sqlite3 db/crypto_agent.db "PRAGMA integrity_check" | head -20

# 3. Attempt recovery with REINDEX
sqlite3 db/crypto_agent.db << EOF
PRAGMA integrity_check;
REINDEX;
PRAGMA integrity_check;
EOF

# 4. If still corrupted, restore backup
yesterday=$(date -d "yesterday" +%Y%m%d)
backup_file="db_backup_${yesterday}.db"

if [ -f "$backup_file" ]; then
    cp "$backup_file" db/crypto_agent.db
    echo "Restored from $backup_file"
else
    echo "No backup found, attempting 2-day old backup"
    two_days_ago=$(date -d "2 days ago" +%Y%m%d)
    cp "db_backup_${two_days_ago}.db" db/crypto_agent.db
fi

# 5. Verify restoration
sqlite3 db/crypto_agent.db "PRAGMA integrity_check"

# 6. Resync missing data (check age of latest records)
python data/collector.py --mode=update-all --lookback-hours=72

# 7. Validate coverage
python monitoring/staleness_detector.py

# 8. Resume operations
python main.py &
sleep 120
python backtest/daemon_24h7.py &
```

### Scenario 4: CPU Spike / Process Hang

**Symptom:**
```
Health probe: CPU > 90% for > 10 min
Heartbeat stale > 2 min
No recent backtest results
```

**Recovery (5-10 min):**

```bash
# 1. Capture debug info
pstack $(cat run/backtest.pid) > /tmp/pstack_$(date +%s).txt

# 2. Graceful kill (30s timeout)
kill $(cat run/backtest.pid)
sleep 5

# 3. If still running, force kill
if ps -p $(cat run/backtest.pid) > /dev/null 2>&1; then
    kill -9 $(cat run/backtest.pid)
fi

# 4. Clean up state files
rm -f run/backtest.pid run/backtest.heartbeat

# 5. Wait for cleanup
sleep 5

# 6. Restart
python backtest/daemon_24h7.py > /tmp/backtest.log 2>&1 &
```

### Scenario 5: Persistent Failures (3+ crashes in 24h)

**Symptom:**
```
Health probe: consecutive_failures >= 3
Daemon keeps crashing despite restarts
```

**Recovery (60+ min):** ⚠️ **LAST RESORT**

```bash
# 1. Stop everything
pkill -f main.py
pkill -f daemon_24h7.py
sleep 10

# 2. Rollback to 48h ago
two_days_ago=$(date -d "2 days ago" +%Y%m%d)
if [ -f "db_backup_${two_days_ago}.db" ]; then
    cp "db_backup_${two_days_ago}.db" db/crypto_agent.db
    echo "Rolled back to ${two_days_ago}"
else
    echo "ERROR: No 2-day backup found"
    exit 1
fi

# 3. Full validation
sqlite3 db/crypto_agent.db "PRAGMA integrity_check"
python monitoring/staleness_detector.py

# 4. Resume live trading ONLY (priority)
python main.py &
logger "ROLLBACK COMPLETE: Live trading resumed, backtest PAUSED for investigation"

# 5. Alert operator on-call
# Send Telegram / Slack to incident channel:
# "🚨 BACKTEST ROLLBACK: Persistent issues detected, rolled back 48h. 
#  Investigate /tmp/backtest.log and pstack*.txt"
```

---

## 📊 Monitoring Dashboard (DIY)

Create a simple status check via cron:

```bash
#!/bin/bash
# File: scripts/status_check.sh
# Run: Every 5 minutes via cron

PIDFILE="run/backtest.pid"
HEARTBEAT="run/backtest.heartbeat"

if ! [ -f "$PIDFILE" ]; then
    echo "DEAD: No PID file"
    exit 1
fi

PID=$(cat "$PIDFILE")
if ! ps -p "$PID" > /dev/null; then
    echo "DEAD: Process $PID not running"
    exit 1
fi

if [ -f "$HEARTBEAT" ]; then
    AGE=$(($(date +%s) - $(cat "$HEARTBEAT")))
    if [ "$AGE" -gt 120 ]; then
        echo "DEGRADED: Heartbeat stale ${AGE}s"
        exit 1
    fi
fi

echo "HEALTHY: PID $PID"
```

Add to crontab:
```bash
*/5 * * * * /path/to/scripts/status_check.sh >> /tmp/backtest_status.log 2>&1
```

---

## 🔐 Backup Verification

Test restore monthly:

```bash
#!/bin/bash
# File: scripts/backup_test.sh
# Run: First Sunday of every month

BACKUP_FILE="db_backup_$(date -d "yesterday" +%Y%m%d).db"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup not found: $BACKUP_FILE"
    exit 1
fi

# 1. Copy to test database
cp "$BACKUP_FILE" /tmp/db_test.db

# 2. Run integrity check
INTEGRITY=$(sqlite3 /tmp/db_test.db "PRAGMA integrity_check")

if [ "$INTEGRITY" != "ok" ]; then
    echo "ERROR: Backup corrupted: $INTEGRITY"
    exit 1
fi

# 3. Count records
OHLCV_COUNT=$(sqlite3 /tmp/db_test.db "SELECT COUNT(*) FROM ohlcv_h4")

if [ "$OHLCV_COUNT" -lt 1000 ]; then
    echo "ERROR: Test DB too small: $OHLCV_COUNT rows"
    exit 1
fi

echo "✅ Backup test passed: $BACKUP_FILE (rows=$OHLCV_COUNT)"
```

---

## 📞 Escalation Path

| Issue | L1 (You) | L2 (DevOps) | L3 (Lead) |
|-------|----------|-----------|-----------|
| **Daemon crashed** | Restart | If 3× fails | Investigate root |
| **Data stale** | Retry update | Check Binance API | Contact Binance |
| **DB corrupted** | Restore backup | Manual reindex | Incident review |
| **Persistent fail** | Trigger rollback | Post-incident | Root cause analysis |
| **Live trading affected** | STOP backtest | Page on-call lead | War room |

---

## 📝 Post-Incident Checklist

After any incident, fill out:

```markdown
# Incident Report

**Date:** 2026-02-22  
**Time:** 14:30 UTC  
**Duration:** 45 min  
**Impact:** Backtest paused, live trading OK  

## Root Cause
[ ] Process hang [ ] DB corruption [ ] API throttle [ ] Other: ___

## Detection
Who found? [ ] Automated [ ] Manual notice
Detection delay: ___ min

## Recovery
Action taken: ___
Recovery time: ___ min
Data loss: ___ hours

## Prevention
[ ] Auto-restart added
[ ] Backup validation improved
[ ] Monitoring threshold adjusted
[ ] Other: ___

## Assigned to
Owner: ___ | Due: 2026-02-24
```

---

## 🔗 Related Documentation

- [INFRASTRUCTURE_24H7_BACKTESTING.md](INFRASTRUCTURE_24H7_BACKTESTING.md) — Design doc completo
- [config/backtest_config.py](config/backtest_config.py) — Tunning parameters
- [backtest/daemon_24h7.py](backtest/daemon_24h7.py) — Daemon source
- [monitoring/staleness_detector.py](monitoring/staleness_detector.py) — Data freshness check
- [monitoring/health_probe.py](monitoring/health_probe.py) — Health monitoring

---

## 📞 Support

- **On-Call:** Check Slack #infrastructure-oncall
- **Emergency:** Page @devops-lead
- **Database issues:** Message @the-blueprint
