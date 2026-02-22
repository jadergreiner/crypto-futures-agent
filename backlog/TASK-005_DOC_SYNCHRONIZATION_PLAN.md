# 📚 DOC SYNCHRONIZATION MASTER PLAN — TASK-005 PPO Training

**Owner:** Doc Advocate (Synchronization Manager)
**Co-owner:** SWE Senior + ML Specialist
**Date:** 22 FEV 2026
**Status:** 🟢 READY FOR IMPLEMENTATION
**Deadline:** 25 FEV 20:00 UTC (parallel with training phases)

---

## 🎯 OBJETIVO

Manter **TODAS as documentações do projeto sincronizadas com mudanças
TASK-005** (PPO Training implementation) em tempo real, garantindo:

✅ Audit trail completo de cada mudança
✅ Rastreabilidade código ↔ docs (cross-references)
✅ Markdown lint compliance (max 80 chars, UTF-8)
✅ Commit message policy (ASCII, max 72 chars, [SYNC] tags)
✅ Zero duplicação/inconsistência de informações

---

## 📋 MATRIZ DE DEPENDÊNCIAS — DOCS QUE MUDAM

| Doc | Owner | Priority | Timeline | Sync Frequency | Audit |
|-----|-------|----------|----------|----------------|-------|
| **README.md** | Doc Advocate | 🔴 CRÍTICA | 23 FEV | E2E daily | ✅ |
| **BEST_PRACTICES.md** | SWE Sr + Doc Adv | 🔴 CRÍTICA | 23 FEV | Daily | ✅ |
| **docs/SYNCHRONIZATION.md** | Doc Advocate | 🔴 CRÍTICA | Continuous | Every 2h | ✅ |
| **CHANGELOG.md** | Doc Advocate | 🟠 ALTA | 25 FEV | Post-milestone | ✅ |
| **backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md** | Planner | 🟠 ALTA | Daily | Daily standup | ✅ |
| **backlog/TASKS_TRACKER_REALTIME.md** | Planner + Doc Adv | 🟠 ALTA | Continuous | Every 2h | ✅ |
| **.github/copilot-instructions.md** | SWE Sr | 🟡 MÉDIA | Post-implementation | 1x | ✅ |
| **docs/BEST_PRACTICES.md** | Doc Advocate | 🟡 MÉDIA | 25 FEV final | Post-testing | ✅ |
| **prompts/TASK-005_* files** | ML Specialist | 🟡 MÉDIA | 23 FEV deliverables | During implementation | ✅ |

---

## 🔄 FLUXO DE SINCRONIZAÇÃO (3 Fases)

### **FASE 0: PRÉ-IMPLEMENTATION (22 FEV 15:00-22:00)**

**Responsável:** Doc Advocate
**Duração:** 7h
**Objetivo:** Preparar matriz de sincronização + git hooks

```plaintext
15:00-15:30  Create TASK-005_DOC_SYNCHRONIZATION_PLAN.md (this file)
             ✅ BRANCH: feature/task-005-ppo-training

15:30-16:00  Setup .githooks/ directory
             - pre-commit: markdownlint checker
             - pre-commit: [SYNC] tag validator
             - pre-push: UTF-8 encoding checker
             ✅ COMMIT: [SYNC] Setup git hooks for doc enforcement

16:00-16:30  Create docs/POLICY_DOC_GOVERNANCE_PHASE4.md
             - Enforcement rules para TASK-005 (strict)
             - [SYNC] tag obrigatória em commits
             - Commit message format (ASCII, 72 char max)
             - Markdown lint rules (80 char word wrap)
             ✅ COMMIT: [SYNC] Add PHASE4 doc governance policy

16:30-17:00  Create SYNCHRONIZATION_MATRIX.json
             - Map: code file → affected docs
             - Map: PR requirement → doc update checklist
             - Map: test → documentation validation
             ✅ COMMIT: [SYNC] Add sync matrix for TASK-005

17:00-22:00  Git hooks installation + CI/CD integration
             - Setup markdownlint in GHA workflow
             - Setup Python docstring checker
             - Test locally: make hooks-setup
             ✅ COMMIT: [SYNC] Enforce doc sync via CI/CD (72h window)

ERROR IF: Hook setup fails → rollback to manual enforcement Day 3
```

### **FASE 1: IMPLEMENTATION (23 FEV 00:00-18:00)**

**Responsável:** Doc Advocate (monitoring) + SWE Sr + ML Specialist
**Duração:** 18h
**Objective:** Keep docs in sync AS code is written

```plaintext
TRIGGER: SWE Senior creates agent/checkpoint_manager.py
    ↓
Event: New module added to agent/ package
    ↓
DOC ADVOCATE ACTION:
    1. Update README.md: add "### New Modules in TASK-005" section
       └─ Link to code file + brief description
       └─ [SYNC] tag in commit (ASCII, max 72 chars)
       └─ COMMIT: [SYNC] Update README for checkpoint_manager

    2. Update BEST_PRACTICES.md: add code pattern section
       └─ Example: "Checkpoint serialization best practices"
       └─ Reference: agent/checkpoint_manager.py (with link)
       └─ Markdown lint: max 80 char lines
       └─ COMMIT: [SYNC] Add checkpoint patterns to BEST_PRACTICES

    3. Update docs/SYNCHRONIZATION.md: log the change
       └─ Entry: "DATE TIME | agent/checkpoint_manager.py | Created"
       └─ Owner: SWE Sr | Doc Advocate sign-off
       └─ COMMIT: [SYNC] Log TASK-005 progress in SYNCHRONIZATION

    4. Daily 08:00 UTC Audit Checklist:
       [ ] All new PRs have [SYNC] tag?
       [ ] Markdown lint passing?
       [ ] SYNCHRONIZATION.md updated?
       [ ] Cross-references valid?
       [ ] No duplicates (search README + BEST_PRACTICES)?

REPEAT for each new file:
    - agent/convergence_monitor.py
    - agent/rollback_handler.py
    - scripts/ppo_training_orchestrator.py
    - tests/*.py (test fixtures)

CONTINUOUS MONITORING (every 2h):
    - TASKS_TRACKER_REALTIME.md status ← ML + SWE report progress
    - docs/SYNCHRONIZATION.md update ← DOC Advocate timestamps
    - Commit log review ← Validate [SYNC] tags
```

### **FASE 2: TRAINING RUN (23 FEV 14:00 - 25 FEV 10:00)**

**Responsible:** Doc Advocate (passive monitoring)
**Duration:** 72h (parallel with training)
**Objective:** Log training milestones, no code changes

```plaintext
CONTINUOUS (every 12h):
    Update TASKS_TRACKER_REALTIME.md with:
    - Training step count (from convergence_monitor.py logs)
    - Sharpe ratio estimate (daily backtest)
    - Max drawdown current value
    - Checkpoint saves (count + quality)

    COMMIT: [SYNC] Training progress update — 72h checkpoint

DAILY (08:00 UTC):
    Daily Standup Report:
    - % completion vs deadline
    - Any blockers/rollbacks triggered?
    - New docs needed? (e.g., troubleshooting guide)

    AUDIT CHECKLIST:
    [ ] TASK-005 docs in sync with code?
    [ ] Git log shows [SYNC] tags regularly?
    [ ] No encoding errors in logs?
    [ ] Markdown lint passing in all new files?

TRAINING END (25 FEV 10:00):
    Update SYNCHRONIZATION.md with final training metrics
    └─ COMMIT: [SYNC] TASK-005 training completion — metrics logged
```

### **FASE 3: FINALIZATION (25 FEV 10:00-20:00)**

**Responsible:** Doc Advocate + SWE Sr (code review)
**Duration:** 10h
**Objective:** Final sync check before merge

```plaintext
10:00-12:00  Code Review Checkpoint
             - All TASK-005 code files reviewed ✅
             - All [SYNC] tags validated ✅
             - Markdown lint passing on all docs ✅
             - Cross-references verified ✅

12:00-14:00  Documentation Completeness Audit
             README.md:
                 ✅ Lists all 4 new modules
                 ✅ Brief description for each
                 ✅ Links to code + API docs

             BEST_PRACTICES.md:
                 ✅ PPO training patterns documented
                 ✅ Examples for checkpoint_manager
                 ✅ Edge case handling documented

             CHANGELOG.md:
                 ✅ TASK-005 entry added
                 ✅ PR description condensed
                 ✅ Metrics included (Sharpe, win rate)

             docs/SYNCHRONIZATION.md:
                 ✅ All TASK-005 files logged
                 ✅ Timestamps for auditing
                 ✅ Owner sign-offs complete

14:00-16:00  Final Cross-Reference Check
             - Run: grep -r "TASK-005" docs/ backlog/
             - Verify: All references point to correct files
             - Check: No outdated TASK-004 references
             - Validate: URLs internal (correct line numbers)

16:00-20:00  Prepare Merge Checklist
             [SYNC] Final documentation audit pass — TASK-005

             Merge Blocker Checklist:
             ✅ Code review approved (SWE)
             ✅ Tests passing (Audit)
             ✅ Docs synchronized (Doc Advocate)
             ✅ [SYNC] tags all valid
             ✅ Markdown lint 100% passing
             ✅ No encoding errors in any file
             ✅ Audit trail complete
             └─ PROCEED TO MERGE
```

---

## 📝 COMMIT MESSAGE POLICY (ENFORCED)

### Format (ASCII only, max 72 chars)

```
[TAG] Titulo breve em Portugues — docs afetadas

Exemplo VALIDO:
[SYNC] Update README for TASK-005 modules — README.md

Exemplo INVALIDO:
[SYNC] Updated docs/SYNCHRONIZATION.md with new PPO training info about convergence monitoring and alert thresholds for ML specialist oversight
└─ TOO LONG (exceeds 72 chars)
└─ Should be: [SYNC] Add PPO monitoring docs to SYNCHRONIZATION

Tags Obrigatorias:
[SYNC] = Synchronization de docs (sempre que update docs)
[FEAT] = Feature implementation (código novo, com docs)
[FIX]  = Bug fix (com teste + doc update)
[TEST] = Test addition (sem doc update, exceto BEST_PRACTICES)
[DOCS] = Documentation only (nunca sem análise Doc Advocate)
```

### Validation Rules (Git Hooks)

```bash
# Pre-commit: Validate commit message in progress (before push)
if message NOT contains "[SYNC]" or "[FEAT]" or "[FIX]":
    WARN: "Docs may not be synchronized"

if message length > 72 chars:
    ERROR: "Commit message exceeds 72 chars (max)"

if message contains non-ASCII char (ç, ã, ó, etc):
    ERROR: "Commit message must be ASCII only"
    └─ Use: ç → c, ã → a, ó → o

# Pre-push: Check files for violations
for each file in push:
    if file is .md:
        run: markdownlint --config .markdownlint.json
        if fails: ERROR "Markdown lint failed"

    if file is .py:
        check: docstrings present for public functions
        if fails: WARN "Missing docstrings"

    if file is SYNCHRONIZATION.md:
        check: UTF-8 encoding valid
        if fails: ERROR "UTF-8 encoding violation"
```

### Example Commits (Valid)

```
✅ [SYNC] Add checkpoint_manager.py to README — README.md, BEST_PRACTICES.md

✅ [FEAT] Implement convergence monitoring decorator — 3 files sync'd

✅ [SYNC] Update TASK-005 progress in tracker — backlog/TASKS_TRACKER_REALTIME.md

✅ [TEST] Add mock fixtures for training loop — tests/conftest.py docstrings

✅ [SYNC] Final audit pass — SYNCHRONIZATION.md, CHANGELOG.md
```

---

## ✅ DOC ADVOCATE DAILY AUDIT CHECKLIST

**Time:** 08:00 UTC (after standup)
**Owner:** Doc Advocate
**Duration:** 30 min
**Slack Report:** #docs-governance

### Checklist (Copy-Paste)

```markdown
## 📚 Daily Doc Sync Audit — TASK-005 (22-25 FEV)

**Date:** 22 FEV 2026
**Status:** ✅ PASS / 🔴 FAIL

### Code ↔ Docs Synchronization

- [ ] All new modules listed in README.md?
- [ ] agent/checkpoint_manager.py mentioned? (with link)
- [ ] agent/convergence_monitor.py mentioned?
- [ ] agent/rollback_handler.py mentioned?
- [ ] scripts/ppo_training_orchestrator.py mentioned?

### Commit Message Audit

- [ ] All TASK-005 commits have [SYNC]/[FEAT] tag?
- [ ] Commit messages < 72 chars (check git log)?
- [ ] No non-ASCII chars in messages? (git log --format=%B)
- [ ] TODO references tracked in SYNCHRONIZATION.md?

### Markdown Lint

- [ ] README.md passing markdownlint? (80 char rule)
- [ ] BEST_PRACTICES.md passing? (UTF-8 valid)
- [ ] SYNCHRONIZATION.md passing? (line length)
- [ ] New files in prompts/ or backlog/ passing?

### Documentation Version Control

- [ ] SYNCHRONIZATION.md updated with latest entries?
- [ ] CHANGELOG.md reflects TASK-005 progress?
- [ ] TASKS_TRACKER_REALTIME.md current (< 2h old)?
- [ ] Cross-references in README → BEST_PRACTICES valid?
- [ ] No broken internal links? (grep #L[0-9])

### Audit Trail

- [ ] Owner sign-offs complete on critical docs?
- [ ] Timestamps logged for each update?
- [ ] Any rollbacks/conflicts documented?

### Action Items

- [ ] Doc Advocate sign-off ready? (thumbs up emoji here)
- [ ] Any blockers for approval? (list below)
- [ ] Next checkpoint scheduled?

**Blockers (if any):**
- None

**Next Audit:** 23 FEV 08:00 UTC

---
EOC
```

---

## 🔗 CROSS-REFERENCE VALIDATION

### Matrix: Code → Docs

```json
{
  "dependencies": {
    "agent/checkpoint_manager.py": {
      "docs": [
        "README.md (installation + usage)",
        "BEST_PRACTICES.md (patterns)",
        "SYNCHRONIZATION.md (audit trail)"
      ],
      "link": "[checkpoint_manager.py](agent/checkpoint_manager.py)",
      "validation": "Grep README for link. Check 1x daily."
    },
    "agent/convergence_monitor.py": {
      "docs": [
        "README.md (real-time monitoring)",
        "BEST_PRACTICES.md (monitoring patterns)"
      ],
      "validation": "Same as checkpoint_manager"
    },
    "tests/conftest.py": {
      "docs": [
        "BEST_PRACTICES.md (testing fixtures)",
        "README.md (dev setup)"
      ],
      "validation": "Docstring examples match BEST_PRACTICES"
    },
    "scripts/ppo_training_orchestrator.py": {
      "docs": [
        "README.md (training runbook)",
        "backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md"
      ],
      "validation": "Timeline in SPRINT_BACKLOG matches README"
    }
  },
  "bidirectional_check": {
    "rule_1": "If doc mentions 'TASK-005', code must exist",
    "rule_2": "If code file created, README must reference",
    "rule_3": "If README updated, SYNCHRONIZATION.md logged",
    "rule_4": "If SYNCHRONIZATION.md updated, audit slack posted"
  }
}
```

### Validation Commands (Doc Advocate runs daily)

```bash
# 1. Check all TASK-005 references valid
grep -rn "TASK-005\|checkpoint_manager\|convergence_monitor" \
    docs/ README.md backlog/ \
    | grep -v ".git" \
    | sort

# 2. Find broken links (files that don't exist)
grep -o "\[.*\]([^)]*\.py)" docs/*.md | \
    while read link; do
        file=$(echo "$link" | grep -o "[^/]*\.py")
        if ! find agent/ scripts/ tests/ -name "$file" -quit; then
            echo "BROKEN: $link"
        fi
    done

# 3. Check markdown lint
markdownlint --config .markdownlint.json \
    README.md docs/ backlog/*.md prompts/*.md

# 4. Check UTF-8 encoding
file -i README.md BEST_PRACTICES.md docs/SYNCHRONIZATION.md \
    | grep -v "UTF-8\|us-ascii"

# 5. Audit commits [SYNC] tags
git log --oneline --since="22 FEV" \
    feature/task-005-ppo-training \
    | grep -v "\[SYNC\]\|\[FEAT\]\|\[TEST\]" \
    | wc -l  # Should be 0
```

---

## 🎯 ACCEPTANCE CRITERIA (Doc Advocate Sign-Off)

### Pre-Implementation (22 FEV 22:00)

- ✅ TASK-005_DOC_SYNCHRONIZATION_PLAN.md created (this file)
- ✅ Git hooks installed locally + CI/CD integrated
- ✅ Commit message validation working
- ✅ Markdown lint configuration finalized

### During Implementation (23-25 FEV)

- ✅ Daily audit checklist completed each 08:00 UTC
- ✅ Zero [SYNC] tag violations (100% compliance)
- ✅ Markdown lint: 0 errors in all TASK-005 docs
- ✅ UTF-8 encoding: Valid in ALL updated files
- ✅ Cross-references: 100% valid (no broken links)

### Post-Implementation (25 FEV 20:00)

- ✅ SYNCHRONIZATION.md fully logged (all changes documented)
- ✅ CHANGELOG.md entry created + verified
- ✅ README.md reflects TASK-005 completion
- ✅ BEST_PRACTICES.md updated with new patterns
- ✅ Code review approved + Doc Advocate sign-off
- ✅ Merge ready (all checklist items ✅)

---

## 📊 MONITORING DASHBOARD (Doc Advocate)

**Create:** `reports/TASK-005_DOC_SYNC_DASHBOARD.csv`

```csv
Date,Time,Event,Owner,Status,Notes
"22 FEV","15:00","Branch created",SWE Sr,DONE,feature/task-005-ppo-training
"22 FEV","15:30","Hooks setup",Doc Advocate,DONE,git pre-commit installed
"22 FEV","16:30","Git workflow",Doc Advocate,DONE,markdownlint integrated
"23 FEV","08:00","Daily Audit #1",Doc Advocate,✅,All pass
"23 FEV","10:00","checkpoint_manager.py","SWE Sr",DONE,README updated [SYNC]
... (repeat for each phase)
"25 FEV","20:00","Merge ready",Doc Advocate,✅,All audit items PASS
```

Update every time Doc Advocate completes audit.

---

## 🔴 ESCALATION PROCEDURE

**If Doc Advisory fails:**

1. **Minor (Markdown lint, encoding)** → Auto-fix + retest
2. **Medium ([SYNC] tag missing)** → Block commit, require re-do
3. **Critical (Broken cross-refs)** → Block PR merge, notify SWE Sr

**Escalation to Angel (if):**
- Sync matrix unachievable in timeline
- Git hooks cause prod blockers
- > 3 doc inconsistencies discovered

---

**VERSION:** 1.0
**STATUS:** ✅ Ready for implementation
**NEXT STEP:** Doc Advocate executes PHASE 0 (15:00 today)
