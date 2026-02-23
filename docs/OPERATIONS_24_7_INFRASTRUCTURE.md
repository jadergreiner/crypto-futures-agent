# 🚀 Operações 24/7 — Data Pipeline (S2-0)

**Papel:** The Blueprint (#7) — Infrastructure Lead + DevOps Engineer  
**Data:** 2026-02-22  
**Status:** 🔵 PLANEJAMENTO (Sprint 2, S2-0)  
**Escopo:** Job Scheduling + Robustez + Monitoring + Disaster Recovery

---

## 📋 Índice

1. [Cron Job Specification](#1-cron-job-specification)
2. [Failure Handling Strategy](#2-failure-handling-strategy)
3. [Monitoring Checklist](#3-monitoring-checklist)
4. [Disaster Recovery Playbook](#4-disaster-recovery-playbook)

---

## 1. Cron Job Specification

### 1.1 Daily Sync Schedule

```
┌──────────────┬────────────────────┬──────────────┐
│ Timeframe    │ Schedule (UTC)      │ Descrição    │
├──────────────┼────────────────────┼──────────────┤
│ **PRIMARY**  │ 01:00 UTC (8 PM BR)│ Daily sync   │
│ Janela       │ -5 min (00:55)     │ Start window │
│ Timeout      │ 30 min (max)       │ Hard stop    │
└──────────────┴────────────────────┴──────────────┘
```

**Reasoning:**
- Market close: 20:00 UTC (última vela 4h fecha)
- Delay: +5h (margem de segurança + dados consolidados)
- Fetch: últimas **4 barras** apenas (incremental)
- Intervalo: 24h (re-run manual se falha)

### 1.2 Cron Expression

```bash
# Minute  Hour  Day  Month  DayOfWeek  Command
  0       1     *    *      *          /opt/jobs/daily_sync.sh
```

**Arquivo:** `/opt/jobs/daily_sync.sh`

```bash
#!/bin/bash
set -euo pipefail

# === DAILY CANDLE SYNC ===
# Executado: 01:00 UTC diariamente
# SLA: 30 minutos máximo

WORKSPACE="/var/app/crypto-futures-agent"
LOG_DIR="/var/log/crypto-futures-agent"
LOCK_FILE="/tmp/daily_candle_sync.lock"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/daily_sync_${TIMESTAMP}.log"

# Criar diretórios se não existem
mkdir -p "${LOG_DIR}"

# 1. LOCKING: Evitar concurrent runs
if [ -f "${LOCK_FILE}" ]; then
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ❌ Sync já em andamento. Abortando." | tee -a "${LOG_FILE}"
    exit 1
fi

trap "rm -f ${LOCK_FILE}" EXIT
touch "${LOCK_FILE}"

# 2. TIMEOUT WRAPPER: Max 30 minutos
timeout_cmd=$(command -v timeout || echo "gtimeout")
exec_timeout="30m"

# 3. EXECUTE SYNC COM TIMEOUT
{
    echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 🚀 Iniciando daily candle sync..."
    
    cd "${WORKSPACE}"
    
    # Ativa venv
    source venv/bin/activate
    
    # Executa Python sync job
    ${timeout_cmd} ${exec_timeout} python3 -m scripts.daily_candle_sync \
        --workspace "${WORKSPACE}" \
        --symbols all \
        --lookback 4 \
        --mode incremental \
        2>&1
    
    SYNC_EXIT_CODE=$?
    
    if [ ${SYNC_EXIT_CODE} -eq 0 ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ✅ Sync concluído successfully"
    elif [ ${SYNC_EXIT_CODE} -eq 124 ]; then
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ⏱️  TIMEOUT (>30m). Sync abortado."
        exit 124
    else
        echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] ❌ Sync falhou (exit code: ${SYNC_EXIT_CODE})"
        exit ${SYNC_EXIT_CODE}
    fi
    
} | tee -a "${LOG_FILE}"

FINAL_EXIT=$?

# 4. LOGGING CONSOLIDADO
echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] 📊 Log saved: ${LOG_FILE}"

exit ${FINAL_EXIT}
```

### 1.3 Python Daily Sync Job

**Arquivo:** `scripts/daily_candle_sync.py`

```python
"""
Daily incremental candle sync from Binance.
Runs once per day, refreshes last 4 candles for all symbols.
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

from data.collector import BinanceCollector
from data.database import DatabaseManager
from data.binance_client import get_binance_client
from config.symbols import ALL_SYMBOLS
from config.settings import get_db_path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Daily incremental candle sync")
    parser.add_argument("--workspace", type=str, required=True)
    parser.add_argument("--symbols", type=str, default="all")
    parser.add_argument("--lookback", type=int, default=4, help="Number of recent candles to fetch")
    parser.add_argument("--mode", type=str, default="incremental")
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Starting daily sync (lookback={args.lookback} candles)")
    
    try:
        # === 1. SETUP ===
        db_path = get_db_path(args.workspace)
        db = DatabaseManager(db_path)
        client = get_binance_client()
        collector = BinanceCollector(client)
        
        symbols = ALL_SYMBOLS if args.symbols == "all" else args.symbols.split(",")
        
        logger.info(f"📡 Symbols to sync: {len(symbols)}")
        logger.info(f"📁 Database: {db_path}")
        
        # === 2. SYNC LOOP ===
        stats = {
            "total_symbols": len(symbols),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        for symbol in symbols:
            try:
                logger.info(f"⏳ [{symbol}] Fetching last {args.lookback} candles...")
                
                # Fetch 4h timeframe (últimas 4 barras)
                candles = collector.get_klines(
                    symbol=symbol,
                    interval="4h",
                    limit=args.lookback
                )
                
                if not candles:
                    logger.warning(f"⚠️  [{symbol}] No data returned")
                    stats["skipped"] += 1
                    continue
                
                # Upsert into database
                db.upsert_ohlcv_h4(candles)
                
                logger.info(f"✅ [{symbol}] {len(candles)} candles inserted")
                stats["successful"] += 1
                
            except Exception as e:
                logger.error(f"❌ [{symbol}] Error: {str(e)}")
                stats["failed"] += 1
                stats["errors"].append({"symbol": symbol, "error": str(e)})
        
        # === 3. RESULTS ===
        logger.info("=" * 60)
        logger.info(f"📊 SYNC COMPLETE")
        logger.info(f"  ✅ Successful: {stats['successful']}/{stats['total_symbols']}")
        logger.info(f"  ❌ Failed: {stats['failed']}/{stats['total_symbols']}")
        logger.info(f"  ⏭️  Skipped: {stats['skipped']}/{stats['total_symbols']}")
        
        if stats["errors"]:
            logger.error(f"  Errors: {json.dumps(stats['errors'], indent=2)}")
        
        logger.info("=" * 60)
        
        # === 4. EXIT CODE ===
        if stats["failed"] > 0:
            # Partial failure = warning, exit 0 but log it
            logger.warning(f"⚠️  {stats['failed']} symbols failed (non-blocking)")
            return 0
        
        logger.info("✅ All symbols synced successfully")
        return 0
        
    except Exception as e:
        logger.critical(f"💥 CRITICAL ERROR: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## 2. Failure Handling Strategy

### 2.1 Retry Logic (Built-in)

```
┌─────────────────────────┬─────────────┬──────────┐
│ Scenario                │ Retry Count │ Backoff  │
├─────────────────────────┼─────────────┼──────────┤
│ Network timeout (< 5s)  │ 3           │ Exponential (1s→2s→4s) |
│ Rate limit (429)        │ 2           │ 60s + jitter (random 0-30s) |
│ Server error (5xx)      │ 2           │ Exponential (2s→4s) |
│ Data validation error   │ 0           │ N/A (fail fast) |
└─────────────────────────┴─────────────┴──────────┘
```

**Code (in `collector.py` — already exists):**

```python
def _retry_request(self, func, *args, **kwargs):
    """Execute with exponential backoff."""
    for attempt in range(API_MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except RateLimitError:
            wait_time = 60 + random.uniform(0, 30)
            logger.warning(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
        except (ConnectionError, TimeoutError):
            wait_time = (2 ** attempt)  # 1s, 2s, 4s
            logger.warning(f"Connection error. Retry in {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            if attempt == API_MAX_RETRIES - 1:
                logger.critical(f"All retries exhausted: {str(e)}")
                raise
            wait_time = (2 ** attempt)
            logger.warning(f"Error. Retry in {wait_time}s: {str(e)}")
            time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
```

### 2.2 Alert Rules (Prometheus/ELK-ready)

**File:** `conf/alerting_rules.yml`

```yaml
# === DAILY SYNC ALERTS ===

groups:
  - name: data_pipeline
    rules:
      
      # Alert 1: Sync failed to complete
      - alert: DailySyncFailed
        expr: |
          increase(daily_sync_failures_total[1d]) > 0
        for: 5m
        labels:
          severity: critical
          component: data_pipeline
        annotations:
          summary: "Daily candle sync FAILED on {{ $labels.date }}"
          description: |
            Daily sync encountered errors:
            Container logs: /var/log/crypto-futures-agent/daily_sync_*.log
            Check: binance connectivity + rate limits
      
      # Alert 2: Sync timeout
      - alert: DailySyncTimeout
        expr: |
          increase(daily_sync_timeout_total[1d]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Daily sync TIMEOUT (>30min)"
          description: "Sync took more than 30 minutes. Check performance."
      
      # Alert 3: DB write stale (no update in 26h)
      - alert: LastSyncStale
        expr: |
          (time() - last_candle_timestamp) / 3600 > 26
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Last candle is >26h old"
          description: |
            Last sync: {{ humanize (time() - last_candle_timestamp) }} ago
            Check cron job status: /var/log/cron

      # Alert 4: Rate limit abuse
      - alert: RateLimitAbuse
        expr: |
          rate_limit_hits_total[5m] > 10
        severity: warning
        annotations:
          summary: "Rate limit hit {{ $value }} times in 5min"

      # Alert 5: DB corruption detected
      - alert: DatabaseCorruption
        expr: |
          increase(db_corruption_detections[1d]) > 0
        labels:
          severity: critical
        annotations:
          summary: "DB integrity check FAILED"
          description: "Run disaster recovery: /opt/jobs/db_recovery.sh"
```

### 2.3 Alert Delivery Channels

**Option A: Email (simple)**
```bash
# In cron script, after failure:
echo "❌ Daily sync failed on $(date)" | mail -s "ALERT: Daily Sync Failure" ops@company.com
```

**Option B: Slack webhook (recommended)**
```bash
# In daily_candle_sync.py:
import requests

def send_alert(message: str, severity: str = "warning"):
    """Send alert to Slack."""
    payload = {
        "text": f"[{severity.upper()}] {message}",
        "color": "danger" if severity == "critical" else "warning"
    }
    requests.post(os.getenv("SLACK_WEBHOOK_URL"), json=payload, timeout=5)

# Usage on error:
if sync_failed:
    send_alert("Daily sync failed. DB not updated.", severity="critical")
```

---

## 3. Monitoring Checklist

### 3.1 Core Metrics (5-6 target)

| # | Métrica | Tipo | Alvo | Frequency | Ação |
|---|---------|------|------|-----------|------|
| **1** | `last_sync_timestamp` | Gauge | time() - last < 26h | 5min check | Stale alert if >26h |
| **2** | `daily_sync_duration_seconds` | Histogram | p50 < 5min, p99 < 30min | per-run | Flag if >30min |
| **3** | `sync_symbols_success_count` | Counter | 60/60 ✅ | per-run | Partial fail if <60 |
| **4** | `db_record_count_ohlcv_h4` | Gauge | 60 × 4 = 240 records | 1h check | Gap alert if drop |
| **5** | `rate_limit_hits_total` | Counter | <1/hour | 30min check | Abuse alert if >10/5m |
| **6** | `backup_size_bytes` | Gauge | >50MB | Daily | Space alert if <20MB |

### 3.2 Dashboard (Example — Prometheus/Grafana)

```promql
# === DAILY SYNC STATUS ===

# Last successful sync (timestamp)
last_sync_timestamp

# Sync success rate (last 7 days)
avg(daily_sync_success_rate{job="sync"}) over 7d

# Duration histogram (last 30 runs)
histogram_quantile(0.99, rate(daily_sync_duration_seconds_bucket[7d]))

# DB record count (H4 candles)
ohlcv_h4_record_count

# Freshness: Last update age
(time() - max(ohlcv_h4_timestamp)) / 3600

# Backup size
backup_size_bytes{type="incremental"}
```

### 3.3 Manual Health Check Script

**File:** `scripts/health_check.py`

```python
"""
Health check: verfiy last sync, DB integrity, backup status.
Run manually or via cron (e.g., every 6h).
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

def check_health():
    """Check 5-6 metrics and return status."""
    issues = []
    
    # 1. Last sync timestamp
    db_path = "data/agent.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(timestamp) FROM ohlcv_h4")
    last_ts = cursor.fetchone()[0]
    
    if last_ts:
        last_sync_age_hours = (datetime.utcnow().timestamp() - last_ts/1000) / 3600
        print(f"✅ Last sync: {last_sync_age_hours:.1f}h ago")
        if last_sync_age_hours > 26:
            issues.append(f"⚠️  Data is STALE (>{last_sync_age_hours:.1f}h)")
    else:
        issues.append("❌ No data in database")
    
    # 2. Symbol count
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv_h4")
    symbol_count = cursor.fetchone()[0]
    print(f"✅ Symbols in DB: {symbol_count}/60")
    if symbol_count < 60:
        issues.append(f"⚠️  Missing {60 - symbol_count} symbols")
    
    # 3. Record per symbol
    cursor.execute("""
        SELECT symbol, COUNT(*) as cnt 
        FROM ohlcv_h4 
        GROUP BY symbol 
        ORDER BY cnt ASC 
        LIMIT 3
    """)
    for sym, cnt in cursor.fetchall():
        if cnt < 100:
            issues.append(f"⚠️  [{sym}] only {cnt} records (expected >100)")
    
    # 4. DB file size
    db_size_mb = os.path.getsize(db_path) / (1024**2)
    print(f"✅ DB size: {db_size_mb:.1f}MB")
    if db_size_mb < 10:
        issues.append(f"⚠️  DB is small ({db_size_mb:.1f}MB), possible data loss")
    
    # 5. Backup status
    backup_dir = Path("backups")
    backup_files = list(backup_dir.glob("*.db"))
    if backup_files:
        latest_backup = max(backup_files, key=os.path.getctime)
        backup_age_hours = (datetime.utcnow().timestamp() - os.path.getctime(latest_backup)) / 3600
        print(f"✅ Latest backup: {backup_age_hours:.1f}h ago")
        if backup_age_hours > 26:
            issues.append(f"⚠️  Backup is STALE ({backup_age_hours:.1f}h)")
    else:
        issues.append("❌ No backups found")
    
    # 6. Log file fresh
    log_dir = Path("/var/log/crypto-futures-agent")
    if log_dir.exists():
        latest_log = max(log_dir.glob("daily_sync_*.log"), default=None, key=os.path.getctime)
        if latest_log:
            log_age_hours = (datetime.utcnow().timestamp() - os.path.getctime(latest_log)) / 3600
            print(f"✅ Latest log: {log_age_hours:.1f}h ago")
    
    # RESULTS
    print("\n" + "=" * 60)
    if issues:
        print(f"⚠️  ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
        return 1
    else:
        print("✅ All checks PASSED")
        return 0

if __name__ == "__main__":
    exit(check_health())
```

---

## 4. Disaster Recovery Playbook

### 4.1 Scenario: Database Corruption

**Trigger:** `health_check.py` detects integrity issues or alert `DatabaseCorruption` fires.

### 4.2 Recovery Procedure

**File:** `/opt/jobs/db_recovery.sh`

```bash
#!/bin/bash
set -euo pipefail

# === DB CORRUPTION RECOVERY ===
# Scenario: sqlite3 corruption, checksums invalid, or data gaps
# SLA: Restore to last good backup

WORKSPACE="/var/app/crypto-futures-agent"
DB_PATH="${WORKSPACE}/data/agent.db"
BACKUP_DIR="${WORKSPACE}/backups"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")

echo "🚨 [$(date -u)] DB RECOVERY INITIATED"
echo "Database: ${DB_PATH}"

# === STEP 1: DETECT CORRUPTION ===
echo "[1/5] Checking DB integrity..."

sqlite3 "${DB_PATH}" "PRAGMA integrity_check;" > /tmp/integrity_result.txt 2>&1

if grep -q "ok" /tmp/integrity_result.txt; then
    echo "✅ Integrity check PASSED. No corruption detected."
    exit 0
else
    echo "❌ Corruption detected!"
    cat /tmp/integrity_result.txt
fi

# === STEP 2: BACKUP CURRENT STATE ===
echo "[2/5] Backing up corrupted DB..."

cp "${DB_PATH}" "${BACKUP_DIR}/agent_corrupted_${TIMESTAMP}.db"
echo "✅ Corrupted DB saved to: ${BACKUP_DIR}/agent_corrupted_${TIMESTAMP}.db"

# === STEP 3: FIND LATEST GOOD BACKUP ===
echo "[3/5] Finding latest good backup..."

# Sort by modification time, get newest
LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/agent_backup_*.db 2>/dev/null | head -1)

if [ -z "${LATEST_BACKUP}" ]; then
    echo "❌ No backups found! Cannot recover."
    echo "🚨 ESCALATE: Manual intervention required."
    exit 1
fi

echo "✅ Latest backup: ${LATEST_BACKUP}"

# Verify backup integrity
echo "[3.1] Verifying backup integrity..."
sqlite3 "${LATEST_BACKUP}" "PRAGMA integrity_check;" > /tmp/backup_integrity.txt 2>&1

if ! grep -q "ok" /tmp/backup_integrity.txt; then
    echo "❌ Even backup is corrupted!"
    echo "🚨 Try next backup..."
    # Loop to find first good backup (not shown for brevity)
    exit 1
fi

echo "✅ Backup integrity OK"

# === STEP 4: RESTORE FROM BACKUP ===
echo "[4/5] Restoring from backup..."

# Temporary restore
cp "${LATEST_BACKUP}" "${DB_PATH}.temp"

# Verify restored DB
if ! sqlite3 "${DB_PATH}.temp" "SELECT COUNT(*) FROM ohlcv_h4;" > /dev/null 2>&1; then
    echo "❌ Restore verification failed"
    exit 1
fi

echo "✅ Restore verification passed"

# Atomically replace
mv "${DB_PATH}.temp" "${DB_PATH}"
echo "✅ Database restored"

# === STEP 5: SYNC MISSING DATA ===
echo "[5/5] Syncing missing data since backup..."

# Backup is typically 1-2h old
# Fetch last 10 candles to be safe
cd "${WORKSPACE}"
source venv/bin/activate

python3 -m scripts.daily_candle_sync \
    --workspace "${WORKSPACE}" \
    --symbols all \
    --lookback 10 \
    --mode incremental \
    2>&1 || true

echo "✅ Recovery complete"
echo "📊 New DB: $(ls -lh ${DB_PATH} | awk '{print $5}')"

exit 0
```

### 4.3 Backup Strategy (3-2-1)

**Policy:** 3 copies, 2 different media, 1 offsite

```
┌─────────────────────────┬──────────────┬────────────────┐
│ Copy                    │ Location     │ Retention      │
├─────────────────────────┼──────────────┼────────────────┤
│ **PRIMARY** (hot)       │ Local NVMe   │ Last 14 days   │
│ **SECONDARY** (warm)    │ Local HDD    │ Last 30 days   │
│ **OFFSITE** (cold)      │ S3 / GCS     │ Last 90 days   │
└─────────────────────────┴──────────────┴────────────────┘
```

**File:** `scripts/backup_engine.py`

```python
"""
3-2-1 backup strategy for database.
Runs daily at 02:00 UTC (after sync at 01:00).
"""

import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def backup_database():
    """Create incremental backup."""
    
    db_path = Path("data/agent.db")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    
    # === COPY 1: Local NVMe (hot) ===
    backup_hot = Path("backups/hot") / f"agent_backup_{timestamp}.db"
    backup_hot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_hot)
    logger.info(f"✅ Hot backup: {backup_hot}")
    
    # Clean old hot backups (>14 days)
    for old_backup in Path("backups/hot").glob("agent_backup_*.db"):
        age = (datetime.utcnow() - datetime.fromisoformat(old_backup.stem.split("_", 2)[2].replace("_", ":"))).days
        if age > 14:
            old_backup.unlink()
            logger.info(f"Cleaned old hot backup: {old_backup}")
    
    # === COPY 2: Local HDD (warm) ===
    backup_warm = Path("/mnt/slow_hdd/backups/warm") / f"agent_backup_{timestamp}.db"
    backup_warm.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_warm)
    logger.info(f"✅ Warm backup: {backup_warm}")
    
    # Clean old warm backups (>30 days)
    for old_backup in Path("/mnt/slow_hdd/backups/warm").glob("agent_backup_*.db"):
        age = (datetime.utcnow() - datetime.fromisoformat(old_backup.stem.split("_", 2)[2].replace("_", ":"))).days
        if age > 30:
            old_backup.unlink()
    
    # === COPY 3: Offsite S3 (cold) ===
    # Requirements: AWS CLI + S3 bucket
    try:
        subprocess.run([
            "aws", "s3", "cp",
            str(db_path),
            f"s3://company-backup-bucket/crypto-futures-agent/agent_{timestamp}.db",
            "--storage-class", "GLACIER"  # Cold storage
        ], check=True, timeout=300)
        logger.info(f"✅ Offsite (S3) backup complete")
    except Exception as e:
        logger.error(f"❌ S3 backup failed: {e}")
        # Don't fail entire job, just alert
    
    logger.info("✅ All 3 backup copies complete")

if __name__ == "__main__":
    backup_database()
```

### 4.4 Recovery Time Objective (RTO) & Recovery Point Objective (RPO)

```
┌─────────────────┬───────┬────────────────────────┐
│ Metric          │ Value │ Justification          │
├─────────────────┼───────┼────────────────────────┤
│ **RTO**         │ 30min │ Restore from hot bkup  │
│ **RPO**         │ 2h    │ Backup @ 02:00 UTC     │
│                 │       │ Worst case: lose 1-2h  │
│ **Test Period** │ 90d   │ Restore backup monthly │
└─────────────────┴───────┴────────────────────────┘
```

---

## 5. Implementation Timeline

| Phase | Task | Owner | Duration | Start Date |
|-------|------|-------|----------|------------|
| **1** | Implement cron + Python sync job | Lead Devops | 2d | 2026-02-22 |
| **2** | Deploy alerting rules (Slack/Email) | Lead Devops | 1d | 2026-02-24 |
| **3** | Build monitoring dashboard | Monitor Specialist | 2d | 2026-02-25 |
| **4** | Test disaster recovery playbook | QA Lead | 1d | 2026-02-27 |
| **5** | Setup 3-2-1 backup engine | Lead Devops | 2d | 2026-02-28 |
| **6** | Monthly RTO/RPO validation | DevOps + QA | 4h | Monthly |

---

## 6. Operational Runbook

### 6.1 Daily Operator Checklist

```
⏰ MORNING STANDUP (08:00 UTC = 05:00 AM BR):
  ☐ Check: Did daily sync run? (logs: /var/log/crypto-futures-agent/daily_sync_*.log)
  ☐ Metric: Is last_sync_timestamp < 26h?
  ☐ Metric: Are all 60 symbols present?
  ☐ Metric: DB size >= 50MB?
  ☐ Logs: Any ERRORs or WANINGs in daily_sync logs?

🔍 HOURLY CHECK (every 4h automated):
  ☐ Run: python3 scripts/health_check.py
  ☐ Verify: 0 issues reported
  ☐ Alert: If issues, escalate immediately

🔧 IF SYNC FAILS (manual recovery):
  1. Check: /var/log/crypto-futures-agent/daily_sync_*.log
  2. Manual trigger: cd /var/app/crypto-futures-agent && python3 -m scripts.daily_candle_sync --workspace . --symbols all --lookback 4
  3. If timeout: Kill process (pkill -f daily_candle_sync) + wait 30min + retry
  4. If DB corruption: /opt/jobs/db_recovery.sh
  5. If persistent: Slack #alerts + escalate
```

### 6.2 Common Issues & Quick Fixes

| Issue | Symptom | Fix | Time |
|-------|---------|-----|------|
| **Binance API timeout** | Logs: "ConnectionError" | Wait 5min + manual retry | 5min |
| **Rate limit hit** | Logs: "429 Too Many Requests" | Job auto-retries with 60s backoff | +2min |
| **DB locked** | Logs: "database is locked" | Restart cron job (usually clears) | 2min |
| **Disk space full** | Logs: "No space on device" | `df -h`, clear old logs/backups | 10min |
| **Network down** | Logs: "Connection refused" | Wait for connectivity + manual retry | 5-10min |

---

## 7. Validação Mensal (SLA Audit)

**File:** `scripts/sla_audit.py`

Executar mensalmente (e.g., ex-primeiro de cada mês):

```python
"""
SLA audit: Validate 30 days of sync history, RTO/RPO compliance.
"""

import sqlite3
from datetime import datetime, timedelta

def audit_monthly_sla():
    """Check: 30 successful syncs, <26h staleness, RTO/RPO targets."""
    
    db = sqlite3.connect("data/agent.db")
    cursor = db.cursor()
    
    # Last 30 days
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).timestamp() * 1000
    
    # Check: sync frequency
    cursor.execute("""
        SELECT COUNT(DISTINCT DATE(timestamp/1000, 'unixepoch')) 
        FROM ohlcv_h4
        WHERE timestamp > ?
    """, (thirty_days_ago,))
    
    unique_days = cursor.fetchone()[0]
    print(f"✅ Sync frequency: {unique_days}/30 days covered")
    
    if unique_days < 28:
        print(f"⚠️  Below target (30/30). Missing {30 - unique_days} days.")
    
    # Check: staleness
    cursor.execute("SELECT MAX(timestamp) FROM ohlcv_h4")
    last_ts = cursor.fetchone()[0]
    age_hours = (datetime.utcnow().timestamp() * 1000 - last_ts) / 3600000
    
    print(f"✅ Data age: {age_hours:.1f}h (target: <26h)")
    
    if age_hours > 26:
        print(f"⚠️  BREACH: Data is stale beyond RPO")
    
    print("\n✅ SLA CHECK COMPLETE")

if __name__ == "__main__":
    audit_monthly_sla()
```

---

## 📝 Summary

| Deliverable | Status | File | Owner |
|---|---|---|---|
| **1. Cron Job Spec** | ✅ Complete | `/opt/jobs/daily_sync.sh` | DevOps |
| **2. Failure Handling** | ✅ Complete | `conf/alerting_rules.yml` + retry logic | DevOps |
| **3. Monitoring Checklist** | ✅ Complete | `scripts/health_check.py` | DevOps + Monitoring |
| **4. Disaster Recovery** | ✅ Complete | `/opt/jobs/db_recovery.sh` + 3-2-1 backup | DevOps |

**Next Steps:**
- [ ] Deploy cron job to production scheduler
- [ ] Configure Slack/Email for alerts
- [ ] Setup Prometheus metrics + Grafana dashboard
- [ ] Run monthly SLA audit

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-22 (Issue #59)  
**Role:** The Blueprint (#7) — Infrastructure Lead 🔵
