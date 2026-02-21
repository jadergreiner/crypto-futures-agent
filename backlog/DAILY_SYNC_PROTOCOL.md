# 📋 DAILY SYNC PROTOCOL — PARA PLANNER

**Responsável:** Planner (Gerente Projetos)
**Frequência:** Diáriamente @ 20:00 UTC
**Tempo estimado:** 15 minutos
**Status:** ✅ ATIVO

---

## 🎯 OBJETIVO

Manter backlog atualizado em tempo real para que Copilot sempre retorne status ATUAL quando usuário pedir "backlog" ou "prioridades".

---

## ✅ DAILY CHECKLIST @ 20:00 UTC

**Executar nesta ordem:**

### **1. Coletar Status de Cada Task (5 min)**

Contate owners:

```
👨‍💻 Dev (The Implementer)
   └─ "Status TASK-001?", "TASK-004?", "TASK-007?"

🧪 Audit/QA (QA Manager)
   └─ "Status TASK-002?", "TASK-006?"

📈 Alpha (Senior Trader)
   └─ "Status TASK-003?"

🤖 The Brain (ML Engineer)
   └─ "Status TASK-005? PPO training progress?"

💰 Dr. Risk (Head Risk)
   └─ "Status TASK-009?"

🏗️ Flux (Arquiteto Dados)
   └─ "Status TASK-011?"

👑 Angel (Investor)
   └─ "Status TASK-008?", "TASK-010?"
```

### **2. Atualizar TASKS_TRACKER_REALTIME.md (5 min)**

Edit `backlog/TASKS_TRACKER_REALTIME.md`:

```markdown
# Seção: "🔴 SPRINT 1: MUST ITEMS — STATUS ATUAL"

Atualizar coluna "Status" para cada TASK:
├─ NOT STARTED → Se owner disse "não iniciou ainda"
├─ IN PROGRESS → Se owner disse "estou trabalhando"
├─ COMPLETED → Se owner disse "pronto"
├─ WAITING → Se blockeado (add no field "Blocker")
└─ SCHEDULED → Se agendado mas não começou

Atualizar coluna "% Done":
├─ 0% → NOT STARTED
├─ 1-99% → IN PROGRESS (pergunta % específico)
├─ 100% → COMPLETED

Atualizar coluna "Blocker":
├─ "None" → Se sem bloqueador
├─ "TASK-XXX" → Se dependência não pronta
├─ "[ISSUE]" → Se bug/problema descoberto
└─ "[ETA resolução]" → Se bloqueador, quando esperado fix
```

**Exemplo:**

```markdown
Antes:
| **#1.1** | Heurísticas Dev | Dev | 21 23:00 → 22 06:00 | ⏳ WAITING | 0% | None |

Depois (se Dev reportou 50% done):
| **#1.1** | Heurísticas Dev | Dev | 21 23:00 → 22 06:00 | 🔄 IN PROGRESS | 50% | None |

Depois (se Dev found bug):
| **#1.1** | Heurísticas Dev | Dev | 21 23:00 → 22 06:00 | 🔄 IN PROGRESS | 50% | Bug found, fix ETA 23:30 UTC |
```

### **3. Atualizar CHANGE_LOG.txt (3 min)**

Adicionar entrada:

```
[21 FEV 20:00 UTC]
├─ TASK-001: 0% → 50% (Dev "implementing now")
├─ TASK-005: 0% → 0% waiting go-live approval
└─ No new blockeadores

[22 FEV 08:00 UTC]
├─ TASK-001: 100% COMPLETE (code ready for QA)
├─ TASK-002: 0% → IN PROGRESS (QA testing started)
└─ Gate #1 (QA) scheduled for 08:00 vote
```

### **4. Git Commit (2 min)**

```bash
cd crypto-futures-agent

git add backlog/TASKS_TRACKER_REALTIME.md
git add backlog/CHANGE_LOG.txt

git commit -m "[SYNC] Backlog update — $(date +'%d %b %H:%M') UTC

Tarefas atualizadas:
- TASK-001: X%
- TASK-005: Y%
- ...

Bloqueadores: [n identified]
Status geral: GREEN/YELLOW/RED
"

git push origin main
```

---

## 🚨 SPECIAL EVENTS & ESCALATIONS

### **Quando uma task vai para BLOCKED:**

1. **Copilot identifica:** TASK-X em status "WAITING" com blocker
2. **Planner notificado** (via daily standup)
3. **Escalate:** Se blocker impacta critical path:

```
IMPACTO:
├─ TASK-X bloqueado
├─ Tarefas subsequentes: TASK-Y, TASK-Z atrasam
└─ Timeline impact: X horas atraso

AÇÃO:
├─ Contatar owner da dependency (TASK-prior)
├─ Ask: "Quando você consegue desbloquear?"
└─ Update: Blocker field com ETA resolução
```

### **Quando task está RED (atraso crítico):**

```
CENÁRIO:
TASK-004 (Go-Live) scheduled 22 FEV 14:00
Agora é 22 FEV 12:00 e TASK-003 ainda não passou

AÇÃO IMEDIATA:
1. Contatar Alpha (TASK-003 owner)
2. "Alpha, você consegue validar em 1h?"
3. Se NÃO:
   └─ Escalate para Angel (Investor)
   └─ Angel decide: Delay go-live? Ou proceed anyway?
4. Update TASKS_TRACKER: Status RED + Escalation note
5. Copilot verá RED na próxima query
```

### **Quando gate é falhado:**

```
EXEMPLO: Gate #1 (QA) falhou @ 08:00 UTC

AÇÃO:
1. QA reports: "3 critérios não passaram"
2. Dev precisa fix bugs
3. Planner:
   ├─ Update TASK-001: Status "WAITING" (blocker = QA gates)
   ├─ Update TASK-002: Status "BLOCKED" (dependency = TASK-001)
   ├─ Add CHANGE_LOG entry: "[GATE FAIL] QA gate #1 failed 08:00 UTC, reasons..."
   └─ Notify Angel & Dev: "Gate failed, new ETA?"
4. Git commit: "[SYNC] Gate #1 FAILED — QA blockeadores identified"
5. Copilot verá YELLOW/RED na próxima query
```

---

## 📊 METRICS TO TRACK DAILY

**Adicione esta seção em TASKS_TRACKER (update daily):**

```markdown
## 📈 DAILY METRICS

**Data: 21 FEV 20:00 UTC**

| Métrica | Target | Actual | Status |
|---------|--------|--------|--------|
| % Sprint Completion | - | 0% | 🔴 Just Starting |
| Bloqueadores Open | <2 | 0 | 🟢 |
| Gates Passed | 1+ | 0 | 🔴 Pending #1 |
| Critical Path Health | 100% | 100% | 🟢 On Track |
| Dev velocity | 50 LOC/h | TBD | 📊 Watch |
| QA passage rate | 100% | N/A | 📚 TBD |

**Trend:** [Yesterday vs Today]
├─ Progress: +X% (or status same)
├─ Issues discovered: [n new]
└─ Confidence: HIGH/MEDIUM/LOW
```

---

## 🔍 AUDIT CHECKS (Weekly, Planner)

**Às segundas-feiras @ 09:00 UTC:**

```
1. Verificar git log
   └─ "Houve commit [SYNC] diariamente?" (0 failures OK)

2. Verificar arquivo recency
   └─ "TASKS_TRACKER_REALTIME.md foi atualizado ontem?" (< 24h OK)

3. Verificar consistência
   └─ "Dados em TASKS_TRACKER match com SPRINT_BACKLOG maestro?"

4. Verificar completude
   └─ "Todos 7+4+3 tasks têm status?" (deve estar 100%)
```

If problema encontrado:
```
FIX IMMEDIATELY:
├─ Se arquivo outdated: run sync agora
├─ Se inconsistência: resolve com owners
├─ Se dado faltante: contact owner direct
└─ Git commit: "[SYNC] Weekly audit — XXX corrected"
```

---

## 📞 IF COPILOT ENCOUNTERS OUTDATED DATA

**Copilot notará se TASKS_TRACKER data > 24h:**

```
Copilot sees: "Last updated: 1 day ago"

Copilot responde:
"⚠️ Backlog pode estar desatualizado.
 Última sincronização há 24h+.
 Contactar Planner para refresh? @Planner"
```

**Planner ação:**
```
1. Receive Copilot alert
2. Run full standup immediately
3. Collect all status
4. Update TASKS_TRACKER
5. Git commit: "[SYNC] Emergency update — data was stale"
```

---

## 📅 EXAMPLE: 3-DAY SPRINT TRACKING

### **21 FEV 20:00 UTC (Start)**

```
collectstatus:
├─ All tasks: NOT STARTED
├─ Dev ready: "Iniciando TASK-001 em 3h"
└─ Others: Awaiting decisions

UPDATE:
├─ TASK-001: NOT STARTED (starts 21 23:00)
├─ TASK-002-007: NOT STARTED
└─ TASK-008+: SCHEDULED

GIT: "[SYNC] Sprint 1 kickoff — all items status initialized"
```

### **22 FEV 08:00 UTC (Morning check)**

```
collect_status:
├─ Dev (TASK-001): "100% DONE, code ready for QA"
├─ QA (TASK-002): "Running tests now, result in 2h"
├─ Alpha: "Waiting for QA to pass"
└─ Others: Awaiting gates

UPDATE:
├─ TASK-001: COMPLETED (100%)
├─ TASK-002: IN PROGRESS (50%)
├─ TASK-003: WAITING (blocker=TASK-002)
└─ Add metrics: Dev velocity = 50 LOC/h ✓

GIT: "[SYNC] TASK-001 COMPLETE — QA testing in progress"
```

### **22 FEV 14:00 UTC (Go-Live!)**

```
collect_status:
├─ Dev (TASK-004): "Canary phase 1 live, metrics good"
├─ Guardian (Risk): "Circuit breaker armed, all OK"
├─ Others: "Monitoring"
└─ The Brain: "PPO training started"

UPDATE:
├─ TASK-001-004: COMPLETED ✅
├─ TASK-005: IN PROGRESS (PPO training day 1/4)
├─ Metrics: 🟢 GREEN — critical path on track
└─ Add: "🚀 HEURÍSTICAS LIVE @ 14:00 UTC"

GIT: "[SYNC] CRITICAL — Heurísticas GO-LIVE SUCCESSFUL"
     "Canary metrics GREEN. PPO training started."
```

### **25 FEV 20:00 UTC (PPO Go-Live!)**

```
collect_status:
├─ The Brain: "PPO trained, Sharpe 1.2 ✓"
├─ QA: "Quality gates passed ✓"
├─ Dev: "PPO merge live, canary OK"
└─ Guardian: "Risk limits confirmed"

UPDATE:
├─ TASK-001-007: COMPLETED ✅
├─ Sprint 1: 100% DONE 🎉
├─ Next: TASK-008 (Decision #3) scheduled 26 FEV
└─ Add: "🚀 PPO LIVE @ 20:00 UTC"

GIT: "[SYNC] SPRINT 1 COMPLETE 100%"
     "PPO deployed successfully. Sprint 2 begins 26 FEV."
```

---

## 🎯 END-OF-DAY SYNC CHECKLIST

**Every day @ 20:15 UTC (after updates):**

- [ ] TASKS_TRACKER_REALTIME.md atualizado
- [ ] CHANGE_LOG.txt atualizado
- [ ] Git commit executado & pushed
- [ ] Copilot pode ler arquivo fresco
- [ ] No outstanding blockers sem owner contactado
- [ ] Próximo día's agenda clara (se há gates)

---

## 📞 CONTACT TEMPLATE

**Daily @ 20:00 UTC, envie para cada owner:**

```
Hi [Owner Name],

Daily sync checkpoint @ 20:00 UTC.
Quick status update on [TASK-XXX]:

Current status: [NOT STARTED/IN PROGRESS/COMPLETE]
% Done: [n%]
Blockeadores: [NONE / details]
Any issues: [YES → explain / NO]

ETA for next milestone: [date time]
Anything I can help with: [list]

Please reply by 20:30 UTC.
Thanks! — Planner
```

---

## ✅ VALIDATION: Self-check

**Every morning @ 08:00 UTC:**

```bash
# 1. Yesterday's sync completed?
git log --oneline | head -5 | grep "\[SYNC\]"
# Should show yesterday's sync

# 2. File updated yesterday?
ls -la --time-style=+%Y-%m-%d backlog/TASKS_TRACKER_REALTIME.md
# Should be yesterday's date or today

# 3. Data consistent?
grep "SPRINT_BACKLOG" backlog/TASKS_TRACKER_REALTIME.md
# Should exist and reference correct file
```

If any check fails → Run immediate sync + alert team.

---

**Status:** ✅ PROTOCOL ATIVO
**Versão:** 1.0
**Primeira sync:** 21 FEV 2026 20:00 UTC
**Review:** Daily @ 20:00 UTC
