# 🚀 Quick Reference — Operações 24/7 (S2-1)

**Role:** The Blueprint (#7) — Infrastructure Lead  
**Status:** ✅ DESIGN COMPLETE (Planning phase for Sprint 2)  
**Docs:** `docs/OPERATIONS_24_7_INFRASTRUCTURE.md`  

---

## 📋 Deliverables Checklist

| # | Deliverable | File | Status | Notes |
|---|---|---|---|---|
| **1** | Cron Job Specification | `/opt/jobs/daily_sync.sh` | ✅ Created | 30-min timeout, daily 01:00 UTC |
| **2** | Daily Sync Engine | `scripts/daily_candle_sync.py` | ✅ Created | Python script, retry logic built-in |
| **3** | Health Check | `scripts/health_check.py` | ✅ Created | 6-point metric check, ready manual/cron |
| **4** | DB Recovery | `scripts/db_recovery.py` | ✅ Created | Corrupted DB → Restore from backup |
| **5** | Alerting Rules | `conf/alerting_rules.yml` | ✅ Created | 10 alerts (Prometheus-ready) |
| **6** | Master Doc | `docs/OPERATIONS_24_7_INFRASTRUCTURE.md` | ✅ Created | 7 sections, implementation guide |

---

## 🎯 Quick Deploy (Step-by-Step)

### Phase 1: Setup (30 minutes)

```bash
# 1. Create necessary directories
mkdir -p /opt/jobs
mkdir -p /var/log/crypto-futures-agent
mkdir -p backups/{hot,warm}

# 2. Copy bash wrapper to cron location
cp scripts/../opt/jobs/daily_sync.sh /opt/jobs/daily_sync.sh
chmod +x /opt/jobs/daily_sync.sh

# 3. Create cron job entry
# Edit: crontab -e
# Add this line:
0 1 * * * /opt/jobs/daily_sync.sh >> /var/log/crypto-futures-agent/cron.log 2>&1
# (Runs daily at 01:00 UTC)

# 4. Verify cron is running
crontab -l | grep daily_sync
```

### Phase 2: Validation (15 minutes)

```bash
# 1. Test health check
python3 scripts/health_check.py
# Expected output: ✅ ALL CHECKS PASSED (or lists issues)

# 2. Test daily sync manually
python3 -m scripts.daily_candle_sync --workspace . --symbols all --lookback 4
# Expected: ✅ SYNC COMPLETE, all 60 symbols ✅

# 3. Test recovery (on corrupted test DB, not production!)
python3 scripts/db_recovery.py --workspace . --backup-dir backups
# Expected: ✅ DATABASE RECOVERY COMPLETE
```

### Phase 3: Monitoring Setup (30 minutes)

**Option A: Simple Email Alerts**
```bash
# Bash already sends email on cron failure (if sendmail configured)
# Test: echo "test" | mail -s "Test Alert" ops@company.com
```

**Option B: Slack Integration (Recommended)**
```bash
# Set environment variable
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Then in alert code (already in db_recovery.py):
import requests
requests.post(os.getenv("SLACK_WEBHOOK_URL"), json=payload)
```

**Option C: Prometheus + Grafana Dashboard**
```bash
# 1. Export metrics from scripts
# (Not yet implemented, add later if needed)

# 2. Scrape metrics endpoint in Prometheus
# prometheus.yml:
# - job_name: 'crypto-futures-agent'
#   static_configs:
#     - targets: ['localhost:8080']
```

---

## 📊 Core Metrics (6 Targets)

Monitor these **every 5-30 minutes**:

```
1. last_sync_timestamp        → Should be <26h old
2. daily_sync_duration        → Should be <30min (p99)
3. sync_symbols_success_count → Should be 60/60 ✅
4. db_record_count_ohlcv_h4   → Should be 60×4+ (240+)
5. rate_limit_hits_total      → Should be <1/hour
6. backup_size_bytes          → Should be stable (not shrinking)
```

**Manual check (anytime):**
```bash
python3 scripts/health_check.py
```

---

## 🔴 Critical Alerts (3 Severity Levels)

| Alert | Trigger | Action | SLA |
|---|---|---|---|
| **CRITICAL** 🔴 | Data >26h old (RPO breach) | Immediate manual sync | <1h response |
| **CRITICAL** 🔴 | DB corruption detected | Run db_recovery.py | <30min RTO |
| **WARNING** ⚠️  | Sync timeout (>30min) | Check server perf | <2h investigate |
| **WARNING** ⚠️  | Backup >26h old | Trigger backup manually | <4h fix |

**Alert destinations:**
- Slack: `#alerts` channel
- Email: ops@company.com
- PagerDuty: On-call engineer (for 🔴 CRITICAL only)

---

## 🔄 Daily Operations Runbook

### ✅ Morning Standup (08:00 UTC = 05:00 AM BR)

```bash
# 1. Check if daily sync ran
ls -lrt /var/log/crypto-futures-agent/daily_sync_*.log | tail -1
# Should show entry from last 24 hours

# 2. Run health check
python3 scripts/health_check.py
# Expected: ✅ ALL CHECKS PASSED

# 3. Quick DB sanity check
sqlite3 data/agent.db "SELECT MAX(timestamp), COUNT(*) FROM ohlcv_h4;" 
# Expected: Recent timestamp (< 26h ago), ~240+ records
```

### 🔧 If Sync Failed

```bash
# 1. Check logs
tail -50 /var/log/crypto-futures-agent/daily_sync_*.log

# 2. Manual retry
/opt/jobs/daily_sync.sh

# 3. If still failing, check common issues:
#    a) Binance API down? → Wait 30min, retry
#    b) DB locked? → Kill old process, retry
#    c) Network issue? → Check connectivity, retry
#    d) Disk full? → df -h, cleanup

# 4. Last resort: Recover from backup
python3 scripts/db_recovery.py --workspace . --backup-dir backups
```

---

## 📈 SLA Targets

| Metric | Target | Measurement |
|---|---|---|
| **Availability** | 99.5% | Sync succeeds 29/30 days |
| **RPO** (Recovery Point Objective) | 2 hours | Backup every 2h max |
| **RTO** (Recovery Time Objective) | 30 minutes | Restore from backup in 30min |
| **Data Freshness** | <26 hours | Last candle <26h old |
| **Sync Duration** | <30 min | Hard timeout |

---

## 🛡️ 3-2-1 Backup Strategy

**Backup locations:**
- **Copy 1 (Hot):** Local NVMe (`backups/hot/`) — 14-day retention
- **Copy 2 (Warm):** Local HDD (`/mnt/slow_hdd/backups/warm/`) — 30-day retention
- **Copy 3 (Cold):** AWS S3 Glacier (`s3://bucket/backups/`) — 90-day retention

**Backup trigger:** Daily @ 02:00 UTC (automatic, after sync @ 01:00 UTC)

**Recovery procedure:**
```bash
# Automatic (if DB corrupted):
python3 scripts/db_recovery.py

# Or manual (if needed):
cp backups/hot/agent_backup_LATEST.db data/agent.db
python3 -m scripts.daily_candle_sync --lookback 10
```

---

## 🧪 Testing Checklist

Before going live, validate:

- [ ] Cron job runs daily @ 01:00 UTC (check `/var/log/cron`)
- [ ] Daily sync completes in <5 min typically (<30 min SLA)
- [ ] All 60 symbols synced successfully (0 failures or <1)
- [ ] Database integrity check passes (`PRAGMA integrity_check`)
- [ ] Health check reports ✅ (run `python3 scripts/health_check.py`)
- [ ] Backup created daily @ 02:00 UTC (check `backups/hot/`)
- [ ] Manual sync works (`/opt/jobs/daily_sync.sh`)
- [ ] DB recovery tested on test DB (not production!)
- [ ] Alerts fire correctly (Slack/Email test)
- [ ] Monitored for 7 days (watch for anomalies)

---

## 📚 File Index

**Main Documentation:**
- [`docs/OPERATIONS_24_7_INFRASTRUCTURE.md`](../docs/OPERATIONS_24_7_INFRASTRUCTURE.md) — Complete reference (7 sections)

**Scripts (Ready to Use):**
- [`scripts/daily_candle_sync.py`](../scripts/daily_candle_sync.py) — Daily sync engine (retry logic)
- [`scripts/health_check.py`](../scripts/health_check.py) — Health check (6 metrics)
- [`scripts/db_recovery.py`](../scripts/db_recovery.py) — DB recovery (from corruption)

**Automation:**
- [`/opt/jobs/daily_sync.sh`](../opt/jobs/daily_sync.sh) — Cron wrapper (timeout, logging)

**Configuration:**
- [`conf/alerting_rules.yml`](../conf/alerting_rules.yml) — 10 alert rules (Prometheus-ready)

---

## 🎓 Key Design Decisions

| Decision | Rationale | Alternative |
|---|---|---|
| **Daily @ 01:00 UTC** | 5h after market close (consolidation) | Could be 23:00 UTC (earlier) |
| **Last 4 candles** | Incremental, avoids re-fetching history | Could be 10 candles (safety margin) |
| **30-min timeout** | Binance fetch for 60 symbols takes ~2-5min | Could be 60min (generous) |
| **3-2-1 backup** | Balance safety + cost | Could be 2-copy (cheaper) |
| **SQLite** | Lightweight, no server needed | Could use PostgreSQL (more robust) |
| **Cron (not Kubernetes)** | Simple, predictable | Could use K8s CronJob |

---

## 🚨 Known Limitations & Future Work

| Limitation | Impact | Solution (Future) |
|---|---|---|
| No distributed sync | Cron runs on 1 server only | Add multi-node sync + consensus |
| Sync not idempotent | If run twice, duplicates candles | Add deduplication logic |
| Recovery manual | Requires human intervention | Implement auto-recovery on corruption |
| No horizontal scaling | 60 symbols = ~2-5 min (serial) | Parallelize fetch (thread pool) |
| SQLite write lock | Blocking reads during sync | Migrate to PostgreSQL |

---

## 💡 Tips & Tricks

### Useful Commands

```bash
# View last sync status
tail -20 /var/log/crypto-futures-agent/daily_sync_*.log

# Force immediate sync (don't wait for cron)
/opt/jobs/daily_sync.sh

# Check if sync is running
ps aux | grep daily_candle_sync

# Kill stuck sync (if running >30 min)
pkill -f daily_candle_sync

# View cron schedule
crontab -l

# Check cron execution logs
grep daily_sync /var/log/cron | tail -10

# List all backups
ls -lrt backups/hot/*.db

# Restore from specific backup
cp backups/hot/agent_backup_2026-02-22_02-00-00.db data/agent.db
```

### Monitoring Dashboard (Grafana)

Example dashboard panels:

```
┌────────────────────┬────────────────────┐
│ Data Freshness     │ Sync Success Rate  │
│ (hours old)        │ (%)                │
└────────────────────┴────────────────────┘
┌────────────────────┬────────────────────┐
│ Sync Duration      │ Symbol Coverage    │
│ (minutes, p99)     │ (60 symbols)       │
└────────────────────┴────────────────────┘
┌────────────────────┬────────────────────┐
│ Backup Age         │ DB Size            │
│ (hours)            │ (MB)               │
└────────────────────┴────────────────────┘
```

---

## 📞 Support Escalation

| Issue | Level 1 (Self) | Level 2 (Team) | Level 3 (On-call) |
|---|---|---|---|
| Sync failed 1x | Run health_check.py, retry | Check Slack #alerts | - |
| Sync timeout (>30min) | Check server perf (top, du) | Review logs + DB performance | Escalate if persistent |
| DB corruption | Run db_recovery.py | Verify recovery success | PagerDuty alert |
| Disk full | Cleanup logs/backups | Investigate growth | Resize disk |
| Rate limit abuse | Wait 60s + retry | Check concurrent requests | Scale infrastructure |

---

**Document Version:** 1.0 (Quick Reference)  
**Last Updated:** 2026-02-22 (Issue #59, S2-1)  
**Maintainer:** The Blueprint (#7) — Infrastructure Lead 🔵
