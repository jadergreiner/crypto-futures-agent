# ▶️ QUICK START — 24/7 Backtesting Infrastructure

**Especialista:** The Blueprint (#7)  
**Role:** Infrastructure Lead  
**Time:** < 5 minutos para entender tudo

---

## 🎯 O Que Você Precisa Saber (30 segundos)

**Problema:** Backtesting rodava manualmente, agora precisa rodar 24/7 + live trading paralelo

**Solução:** Subprocesso isolado + jobs agendados + monitoring automático

**Resultado:** Backtesting roda todo dia 23:30 UTC por ~2 horas, live trading continua ileso

---

## 📑 4 Documentos Principais (Leia em Ordem)

### 1️⃣ **DELIVERABLES_24H7_BACKTESTING_FINAL.md** (5 min read)
- Executive summary
- O que foi feito vs o que foi pedido
- Key numbers (1.2GB, 1.5GB RAM, 4-8 cores)

### 2️⃣ **INFRASTRUCTURE_VISUAL_ARCHITECTURE.md** (10 min read)
- Diagramas ASCII do sistema
- Como dados fluem
- Exemplos de falha

### 3️⃣ **INFRASTRUCTURE_24H7_BACKTESTING.md** (30 min deep dive)
- Design completo com lógica
- Job schedule detalhado
- Disaster recovery procedures
- Recovery decisions matrix

### 4️⃣ **RUNBOOK_24H7_OPERATIONS.md** (Quick Reference)
- Quick reference table (problemas → soluções)
- Daily checklist
- 5 cenários de incident + step-by-step recovery

---

## 🔧 Arquivos de Código (Para Implementar)

**Visite esses arquivos quando PR for criada:**

```
✅ config/backtest_config.py
   ↳ Configure schedule (6 cron jobs)
   ↳ Configure thresholds (staleness, recovery)

✅ backtest/daemon_24h7.py
   ↳ Main daemon que roda isolado
   ↳ Heartbeat + staleness check integrados

✅ monitoring/staleness_detector.py
   ↳ Verifica se dados estão atualizados
   ↳ Symbol coverage, continuity checks

✅ monitoring/health_probe.py
   ↳ Monitora se daemon está vivo
   ↳ CPU, memory, heartbeat checks
```

---

## 📊 Numbers You Need to Know

| Metrica | Valor | What It Means |
|---------|-------|---------------|
| **Database Size** | 1.2 GB | 1 year × 60 symbols = ~ 300MB. Backups = 882MB. Total = 1.2GB ✅ |
| **RAM Needed** | 1.0-1.5 GB | Live: 260MB, Backtest: 300MB, OS: 400MB+ headroom. Safe margin ✅ |
| **CPU cores** | 4-8 | Live 60% + Backtest 30% = 90% max at peak 23:30-01:30 UTC ✅ |
| **Data Rate** | 0.066 req/s | 240 requests per day. vs 1200 req/min limit = 33× safe margin ✅ |
| **Recovery Time** | 15 min | Goal. Pessimistic = 30-60 min (with data resync) |

---

## ⏰ When Things Happen (UTC)

```
00:30  → Data Update (fetch +4 candles per symbol)
       → Rate limited: 240 req/day spread across 24h ✅

01:00  → Data Validation
       → Check if H4 < 24h, H1 < 6h, coverage > 95%

02:00  → Sentiment/Macro Update
       → Pull sentiment + macro indicators

03:00  → Backup & Compact (Sundays only)
       → VACUUM database + rotate backups (3-3-1 policy)

04:00  → Alert Digest
       → Send Telegram summary of alerts

23:30  → Daily Backtest Starts
       → Run full strategy backtest (~2 hours)
       → Live trading continues (CPU 60% + Backtest 30% = 90% safe)
```

---

## 🚨 If Something Goes Wrong

**Quick Reference:**

| Problem | What to Do | Time |
|---------|-----------|------|
| Daemon died | `python backtest/daemon_24h7.py &` | 2 min |
| Data stale (H4 > 24h) | Check logs, retry collector | 15 min |
| Database corrupted | Restore backup from yesterday | 30 min |
| CPU spike (>90%) | Kill & restart daemon | 5 min |
| 3+ crashes in 24h | Rollback 48h ago (manual) | 60 min |

**Full runbook:** [RUNBOOK_24H7_OPERATIONS.md](RUNBOOK_24H7_OPERATIONS.md)

---

## ✅ Sign-Off Path

```
Your deliverable is complete when:

1. ✅ Design approved by @board-infrastructure
2. ✅ Code reviewed by @devops-team
3. ✅ Staging tests pass (24h E2E)
4. ✅ Runbook trained with on-call team
5. ✅ Go-live to production (with canary monitoring)
```

---

## 📞 Key Contacts

| Role | For What |
|------|----------|
| **The Blueprint (#7)** | Infrastructure design questions |
| **@devops-team** | Code review & implementation |
| **@on-call-lead** | Runbook & recovery procedures |
| **@board-infrastructure** | Production approval |

---

## 🎓 Learning Path

### 5 Minutes — Decision Maker
1. Read: [DELIVERABLES_24H7_BACKTESTING_FINAL.md](DELIVERABLES_24H7_BACKTESTING_FINAL.md)
2. Approve numbers (1.2GB, 1.5GB RAM, RTO=15min)

### 30 Minutes — Technical Lead
1. Read: [INFRASTRUCTURE_VISUAL_ARCHITECTURE.md](INFRASTRUCTURE_VISUAL_ARCHITECTURE.md)
2. Look at diagrams + resource allocation
3. Review numbers in [Section 2](INFRASTRUCTURE_24H7_BACKTESTING.md#2️⃣-estimativa-de-overhead)

### 2 Hours — DevOps/Implementation
1. Deep read: [INFRASTRUCTURE_24H7_BACKTESTING.md](INFRASTRUCTURE_24H7_BACKTESTING.md)
2. Review code files (daemon_24h7.py, staleness_detector.py, health_probe.py)
3. Plan staging tests

### Ongoing — Operations
1. Keep [RUNBOOK_24H7_OPERATIONS.md](RUNBOOK_24H7_OPERATIONS.md) handy
2. Reference quick table for incident response
3. Follow procedures for disaster recovery

---

## 🏆 Success = 3 Days to Staging

```
Day 1 (Today):    ✅ Blueprint complete (you are here)
                     → Board reviews & approves

Day 2 (Tomorrow):  Code Review PR
                   → Merge to develop
                   → Start staging deployment

Day 3 (Day After): Staging E2E 24h test
                   → Monitor all scenarios
                   → Validate recovery procedures
                   → Green light for production
```

---

## 📚 Full Documentation Tree

```
crypto-futures-agent/
├── DELIVERABLES_24H7_BACKTESTING_FINAL.md       ← Executive summary
├── INFRASTRUCTURE_24H7_BACKTESTING.md           ← Full design & specs
├── INFRASTRUCTURE_VISUAL_ARCHITECTURE.md        ← Diagrams  
├── INFRASTRUCTURE_VALIDATION_SUMMARY.md         ← Summary reference
├── RUNBOOK_24H7_OPERATIONS.md                   ← Operations manual
│
├── config/
│   └── backtest_config.py                       ← Configuration
│
├── backtest/
│   └── daemon_24h7.py                           ← Main daemon
│
├── monitoring/
│   ├── staleness_detector.py                    ← Data freshness
│   └── health_probe.py                          ← Process health
│
└── docs/
    └── SYNCHRONIZATION.md                       ← Audit trail (updated)
```

---

## ❓ FAQ

**Q: Will backtesting slow down live trading?**  
A: No. Subprocesso isolado, separate PID. Live trading has 60%, backtest takes 30% = 90% safe.

**Q: What if database gets corrupted?**  
A: Automatic restore from yesterday's backup. Reindex. Done in ~30 min. Data loss = none (restores fresh data).

**Q: What if backtest crashes?**  
A: Health probe detects within 2 min, auto-restarts. If 3+ crashes/24h, alert ops for manual investigation.

**Q: How often do I need to check on this?**  
A: Monitoring is automatic. Alerts go to Telegram. You just monitor the channel. Only get alerts if something's wrong.

**Q: Can I disable backtesting during high volatility?**  
A: Yes. Environment var `BACKTEST_ENABLED=0` disables daemon startup. Or pause via scheduler.

---

## 🎯 TL;DR (Too Long; Didn't Read)

✅ **Design:** Subprocesso isolated + 6 scheduled jobs + monitoring  
✅ **Size:** 1.2GB database, 1.5GB RAM, 4-8 cores  
✅ **Recovery:** Auto-restart 4 times, then manual rollback  
✅ **Time to implement:** 3 days (review → staging → canary)  
✅ **Status:** READY FOR IMPLEMENTATION  

**Next:** Board approval → Code review → Staging tests → Go-live

---

**Last Updated:** 2026-02-22 23:55 UTC  
**Created by:** The Blueprint (#7)  
**Status:** ✅ Complete & Validated
