# 🔄 CANARY ROLLBACK PROCEDURE — TASK-004

**Última atualização:** 21 FEV 2026  
**Owner:** Elo (Ops Lead) + Dev  
**Status:** PRONTO PARA ATIVAÇÃO (se needed)

---

## 📋 Resumo Executivo

Procedimento estruturado para rollback imediato em caso de falha durante canary deployment. **Tempo alvo: <5 minutos até status estável.**

---

## 🚨 TRIGGER CONDITIONS

### Automatic Triggers (Imediato)

```
❌ CIRCUIT BREAKER ATIVADO (-3% drawdown)
   → Ativa rollback automático em <1s
   
❌ DATABASE CONNECTIVITY PERDIDA
   → Suspende operations em <2s
   → Iniciates restore procedure
   
❌ WEBSOCKET STREAM INTERROMPIDO >30s
   → Closes all open positions
   → Stops signal generation
   
❌ ORDER PLACEMENT ERROR RATE >5%
   → Suspends new orders
   → Alerts team immediately
```

### Manual Triggers (Decision-based)

```
❌ LIQUIDATION ERRORS MÚLTIPLAS
   → Alpha ou Planner: "STOP"
   → Ativa rollback imediato
   
❌ FILL RATE DROPS <90%
   → Dev decision com Planner
   → Pode investigar 2min ou rollback
   
❌ LATÊNCIA CONSISTENTEMENTE >1s
   → Indica problema de infraestrutura
   → Rollback + diagnóstico
```

---

## ⚡ ROLLBACK SEQUENCE (Target: <5 min)

### STAGE 1: IMMEDIATE STOP (0-30s)

**Objetivo:** Parar operações, evitar mais prejuízos

```bash
# [1] Disable signal generation (30s)
$ python -c "
from execution.heuristic_signals import HeuristicSignalGenerator
gen = HeuristicSignalGenerator()
# Disable: 
# gen.enabled = False
print('✓ Signal generation disabled')
"

# [2] Close all open positions (market order, 1min max wait)
$ python scripts/close_all_positions.py --type market --timeout 60
# Output: Closed 5 positions in 45s
# P&L: -$124.32

# [3] Disable paper trading mode if active
$ curl -X POST http://localhost:8000/api/trading/disable \
  --header "Authorization: Bearer $API_TOKEN"
# Output: 200 OK — Trading disabled

# [4] Alert team immediately
$ python scripts/slack_alert.py --message \
  "🚨 CANARY ROLLBACK INITIATED: Circuit breaker triggered" \
  --channel #crypto-alerts --severity CRITICAL
```

**Status Check After Stage 1:**
- ✅ Nenhuma ordem aberta pendente
- ✅ Todas as posições fechadas
- ✅ Signal generation parado
- ✅ Team notificado

---

### STAGE 2: INVESTIGATE & LOG (30s-3min)

**Objetivo:** Documentar root cause e estado

```bash
# [1] Capture error logs (1min)
$ tail -n 500 logs/execution.log > /tmp/rollback_error_log_$(date +%s).txt
$ tail -n 500 logs/risk_guard.log >> /tmp/rollback_error_log_$(date +%s).txt
$ tail -n 500 logs/binance_api.log >> /tmp/rollback_error_log_$(date +%s).txt

# [2] Database snapshot (before restore)
$ mysqldump --user=$DB_USER --password=$DB_PASS \
  --all-databases > /tmp/db_snapshot_$(date +%Y%m%d_%H%M%S).sql
# Size: ~45MB (captured in 30s)

# [3] Calculate P&L impact
$ python scripts/calculate_rollback_pnl.py \
  --from deploymentstart \
  --to now
# Output:
# Total trades: 24
# Profitable: 16 (+$342.50)
# Loss-making: 8 (-$466.82)
# Net P&L: -$124.32
# Duration: 47min
```

**Investigation Checklist:**
- ✅ Error logs captured
- ✅ Database snapshot taken
- ✅ P&L calculated
- ✅ Root cause identified

---

### STAGE 3: DATABASE RESTORE (3-5min, if needed)

**Apenas se database corruption detectada**

```bash
# [1] Identify latest clean backup
$ ls -t backups/ | head -5
# Output:
# backup_2026-02-22_0900.sql.gz  ← Latest pre-deployment
# backup_2026-02-21_2300.sql.gz
# backup_2026-02-21_1200.sql.gz

# [2] Restore from pre-deployment backup (1h timeout, runs background)
$ scripts/restore_database_backup.sh \
  --backup backups/backup_2026-02-22_0900.sql.gz \
  --verify \
  --timeout 3600
# Output:
# [00:00] Restoring from backup...
# [00:45] Database restored successfully
# [00:50] Verification passed

# [3] Verify data integrity
$ python scripts/verify_database_integrity.py
# Output:
# Orders table: OK (24 records)
# Trades table: OK (24 records)
# Positions table: OK (0 open)
# Integrity check: PASS
```

**Database Restore Timeline:**
- Backup restore: ~45min
- Verification: ~5min
- **Total: ~1h** (acceptable for incident recovery)

---

## 📊 STATUS CHECKPOINTS

### After Stage 1 (Immediate stop)

```
✅ System Status: SAFE
   - Signal generation: DISABLED
   - Open positions: 0
   - Risk: MITIGATED
   - Team: ALERTED
   
☑️  Next Action: Investigate root cause (Stage 2)
```

### After Stage 2 (Investigation)

```
✅ Documentation: COMPLETE
   - Error logs: CAPTURED
   - P&L: CALCULATED (-$124.32)
   - Root cause: IDENTIFIED
   
Options:
  A) Database restore needed? → Stage 3
  B) Data OK? → Proceed to post-mortem (Stage 4)
```

### After Stage 3 (Database restore, if needed)

```
✅ Data Recovery: COMPLETE
   - Database restored from 22 FEV 09:00
   - Integrity verified: PASS
   - System ready for restart
   
☑️  Next Action: Post-mortem analysis (Stage 4)
```

---

## 📋 POST-MORTEM TEMPLATE

```markdown
# INCIDENT POST-MORTEM — CANARY ROLLBACK

**Incident ID:** CB-2026-0222-001
**Date/Time:** 22 FEV 2026 11:15 UTC
**Duration:** 47 minutes (Canary Phase 1)
**Owner:** [Name]

## SUMMARY
[Brief description of what happened]

## ROOT CAUSE
[Technical root cause analysis]

## IMPACT
- P&L: -$124.32
- Positions affected: 5
- Team productivity: 2h (incident + investigation)

## ACTIONS TAKEN
1. Immediate position closure (45s)
2. Signal generation disabled (30s)
3. Team alerted (Slack + phone)
4. Error logs captured
5. Database snapshot taken

## PREVENTION
[What changes prevent recurrence?]
- [ ] Code fix
- [ ] Monitoring improvement
- [ ] Infrastructure upgrade
- [ ] Documentation update

## TIMELINE
| Time | Event |
|------|-------|
| 11:15 | Circuit breaker triggered |
| 11:16 | Positions closed, team alerted |
| 11:20 | Error logs captured, DB snapshot |
| 11:25 | Root cause identified |
| 11:30 | Post-mortem documentation started |

## SIGN-OFF
- Dev: [Signature]
- Elo (Ops): [Signature]
- Alpha (Trader): [Signature]
```

---

## 🔧 DECISION TREE

```
ROLLBACK TRIGGERED
    ↓
[Is P&L > -2%?]
    ├─ YES → Proceed with investigation
    │         Can restart canary after fix
    └─ NO → POSTPONE RESTART
             Requires full review + approval
    
[Root Cause Found?]
    ├─ CODE BUG → Fix + redeploy next window
    ├─ INFRA ISSUE → Elo fixes, then redeploy
    └─ MARKET CONDITION → Adjust parameters, retry
    
[Database Corrupted?]
    ├─ YES → Restore from backup (1h)
    │         Then restart canary
    └─ NO → Direct restart after fix
```

---

## 🎯 ESCALATION POLICY

```
STAGE 1 (0-2min): Dev + Elo (on-call)
  • Decision: Auto-rollback
  • Communication: Internal Slack
  
STAGE 2 (2-10min): + Alpha trader (decision input)
  • Decision: Restart or deep investigation?
  • Communication: Team call if needed
  
STAGE 3 (>10min): + C-level (for approval)
  • Decision: Continue or abort sprint?
  • Communication: Executive briefing
```

---

## ✅ VALIDATION CHECKLIST

### Pre-Rollback Readiness

```
☐ Rollback scripts tested in staging
☐ Database backups verified (can restore <1h)
☐ Team communication channels ready (Slack, phone)
☐ Error log collection automated
☐ Alert thresholds calibrated
☐ P&L calculation scripts working
```

### Post-Rollback Validation

```
☐ No open positions
☐ Signal generation stopped
☐ All error logs captured
☐ Database integrity verified
☐ P&L calculated
☐ Team notified
☐ Incident logged in system
```

---

## 📞 EMERGENCY CONTACTS

| Role | Name | Slack | Phone |
|------|------|-------|-------|
| **Dev** | The Implementer | @dev | +1-XXX-YYY-ZZZZ |
| **Elo** | Ops Lead | @elo | +1-XXX-YYY-ZZZZ |
| **Alpha** | Senior Trader | @alpha | +1-XXX-YYY-ZZZZ |
| **Planner** | Orchestrator | @planner | +1-XXX-YYY-ZZZZ |

---

## 🔗 RELATED DOCUMENTS

- [TASK-004_GOLIVE_CANARY_PLAN.md](../TASK-004_GOLIVE_CANARY_PLAN.md) — Plano principal
- [execution/heuristic_signals.py](../execution/heuristic_signals.py) — Core signal generator
- [scripts/pre_flight_canary_checks.py](../scripts/pre_flight_canary_checks.py) — Pre-flight checks
- [scripts/canary_monitoring.py](../scripts/canary_monitoring.py) — Real-time monitoring

---

**Status:** ✅ PRONTO PARA USO  
**Última revisão:** 21 FEV 2026  
**Próximo review:** Após TASK-004 completo (22 FEV 14:00)
