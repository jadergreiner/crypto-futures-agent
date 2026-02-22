# 🎯 DOC ADVOCATE IMPLEMENTATION GUIDE — TASK-005

**To:** Doc Advocate (Synchronization Manager | Documentation Keeper)
**From:** PO + SWE Sr + ML Specialist (in pair)
**Date:** 22 FEV 2026
**Status:** ✅ READY FOR EXECUTION

---

## 🚀 YOUR MISSION (22 FEV - 25 FEV)

Keep **ALL documentation in sync** with TASK-005 PPO Training implementation.
You are the **last approval** before any PR merge. Code doesn't ship without your sign-off.

---

## 📋 WHAT WAS DELIVERED TO YOU (4 Artifacts)

You now have:

1. **📚 TASK-005_DOC_SYNCHRONIZATION_PLAN.md**
   ├─ Master plan: 3 phases (pre-implementation, implementation, training, finalization)
   ├─ Commit schedule for each day (22-25 FEV)
   ├─ Detailed checklist for each phase
   └─ Cross-reference validation procedures

2. **📊 TASK-005_SYNC_MATRIX.json**
   ├─ Code file → Docs dependencies (JSON structured)
   ├─ Which docs update when each module created
   ├─ Commit message templates for each file
   ├─ Acceptance criteria for final merge
   └─ Daily audit template (fill-in format)

3. **🛡️  Git Hooks & Automation** (in .githooks/)
   ├─ pre-push-sync — validates [SYNC] tags + ASCII + line length
   ├─ Markdownlint integration
   ├─ UTF-8 encoding checks
   └─ Cross-reference validation

4. **✅ TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md**
   ├─ Daily @ 08:00 UTC checklist (copy-paste format)
   ├─ 6 audit sections (code sync, commits, markdown, links, audit trail, blockers)
   ├─ Validation commands (bash one-liners)
   ├─ Sign-off template
   └─ Slack report format

---

## 🎯 YOUR DELIVERABLES (DAILY)

### **Day 1 — 22 FEV (TODAY) — SETUP & ENFORCEMENT**

**Time:** 15:00-22:00 UTC (7h)
**Entry:** Docs/sync setup phase

```plaintext
15:00  ✅ Read: TASK-005_DOC_SYNCHRONIZATION_PLAN.md (20 min)
       └─ Understand 3 phases + timeline

15:20  ✅ Read: TASK-005_SYNC_MATRIX.json (20 min)
       └─ Map out code → docs dependencies

15:40  ✅ Setup: Install git hooks + CI/CD (2h)
       └─ git config core.hooksPath .githooks
       └─ chmod +x .githooks/pre-push-sync
       └─ Test locally with fake commit
       └─ COMMIT: [SYNC] Setup git hooks for TASK-005

18:00  ✅ Sync TASK-005_DOC_SYNCHRONIZATION_PLAN.md into docs/
       └─ COMMIT: [SYNC] Add TASK-005 doc sync master plan

18:30  ✅ Create docs/POLICY_DOC_GOVERNANCE_PHASE4.md
       └─ Formalize enforcement rules for this sprint
       └─ COMMIT: [SYNC] Add PHASE4 doc governance policy

19:00  ✅ Verify backup: TASK-005_SYNC_MATRIX.json is safely stored
       └─ Location: backlog/TASK-005_SYNC_MATRIX.json

19:30  ✅ Prepare for Day 2
       └─ Review TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md
       └─ Schedule daily 08:00 UTC audit time (calendar)

20:00  ✅ Slack update to #docs-governance
       └─ "Setup complete. Ready for implementation monitoring."
```

**Sign-off Criteria for Day 1:**
- [ ] Git hooks installed + tested
- [ ] 3 setup commits completed with [SYNC] tags
- [ ] TASK-005_SYNC_MATRIX.json in backlog/
- [ ] Daily checklist template printed/bookmarked
- [ ] Calendar reminder set (08:00 UTC)

---

### **Days 2-5 — 23-25 FEV (IMPLEMENTATION & TRAINING)**

**Time:** Daily 08:00-08:30 UTC (30 min audit) + continuous monitoring
**Entry:** Daily audit + continuous sync

```plaintext
DAILY SCHEDULE (repeat 23, 24, 25 FEV):

08:00  📋 RUN DAILY AUDIT CHECKLIST
       └─ Use: backlog/TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md (copy-paste)
       └─ Check all 6 sections (code sync, commits, lint, links, trail, blockers)
       └─ Duration: 30 min
       └─ Output: Filled checklist + status (PASS/FAIL)

08:30  💬 POST SLACK REPORT to #docs-governance
       └─ Format:
            📚 DOC SYNC AUDIT — [DATE]
            ✅ Code ↔ Docs: [OK/ISSUES]
            ✅ [SYNC] Tags: [NUMBER] (target: 100%)
            ✅ Markdown Lint: [0 errors / ERRORS]
            ✅ Cross-refs: [valid / BROKEN]
            ✅ SYNCHRONIZATION.md: [updated / needs update]
       └─ Add single sentence on blockers (if any)

CONTINUOUS (throughout day):
  - Monitor git commits → ensure [SYNC] tags present
  - If doc added but no [SYNC] tag → DM SWE Sr to fix
  - If broken link found → add to blockers list
  - If markdown lint fails → note in next audit

23-FEV SPECIFIC:
  - SWE Sr implements 4 modules (checkpoint, monitor, rollback, orchestrator)
  - As each module added → update README.md + BEST_PRACTICES.md same day
  - COMMIT: [SYNC] Update README for [module_name]
  - COMMIT: [SYNC] Add [module_name] patterns to BEST_PRACTICES

24-FEV SPECIFIC:
  - Training starts (72h parallel)
  - Update TASKS_TRACKER_REALTIME.md with progress (every 2h)
  - COMMIT [SYNC] Training day 1 checkpoint

25-FEV SPECIFIC (FINAL):
  - Training completes
  - Run final audit (10:00 UTC)
  - Update CHANGELOG.md with TASK-005 entry
  - COMMIT: [SYNC] TASK-005 completion — final metrics
  - Sign-off ready? → YES/NO
```

**Daily Sign-Off Criteria:**
- [ ] Audit completed (checklist 100% filled)
- [ ] Slack report posted
- [ ] All blockers <2h old (escalated if critical)
- [ ] Zero violations of [SYNC] tag policy
- [ ] Markdown lint: 0 errors

---

## 🔴 CRITICAL RULES (Non-negotiable)

### Rule 1: [SYNC] Tag is MANDATORY

**EVERY commit that touches README, BEST_PRACTICES, SYNCHRONIZATION, CHANGELOG, etc MUST have [SYNC] tag.**

```
✅ GOOD:   [SYNC] Update README for checkpoint_manager.py
✅ GOOD:   [FEAT] Implement training orchestrator (includes docs sync commit)
❌ BAD:    Updated docs
❌ BAD:    Fix typo in README
❌ BAD:    Doc update
```

**Enforcement:** Git hooks will WARN at commit time. You MUST escalate to SWE Sr if ignored.

---

### Rule 2: Markdown Lint (80 char lines, UTF-8, no trailing spaces)

**EVERY .md file must pass markdown lint.**

```bash
# Test locally:
markdownlint README.md BEST_PRACTICES.md docs/*.md

# Should output: 0 errors
```

**If FAIL:** GitHub Actions will block merge. You must notify SWE Sr to fix.

---

### Rule 3: Cross-References Must Be 100% Valid

**Every link in README + BEST_PRACTICES + docs must point to existing files.**

```
✅ [agent/checkpoint_manager.py](agent/checkpoint_manager.py)  ← file exists
✅ [L150](BEST_PRACTICES.md#L150)  ← specific line exists
❌ [agent/missing_file.py](agent/missing_file.py)  ← file doesn't exist
```

**Validation:** You run daily:
```bash
grep -o "\[.*\]([^)]*\.py)" README.md | while read link; do
  file=$(echo "$link" | sed 's/.*(\([^)]*\)).*/\1/')
  [ ! -f "$file" ] && echo "BROKEN: $link"
done
```

---

### Rule 4: SYNCHRONIZATION.md is Your Audit Trail

**Whenever you update README/BEST_PRACTICES/CHANGELOG, you MUST log it in SYNCHRONIZATION.md.**

```
Format:
| 23 FEV | 10:00 UTC | README updated for checkpoint_manager | Doc Advocate | ✅ |
```

This is your proof of work + compliance auditing.

---

## 🛠️ TOOLS YOU HAVE

### Git Hooks (Automatic Validation)

**Pre-push validation:**
```bash
git push  # Git hooks will run automatically
          # If [SYNC] tag missing or line too long → ERROR, push blocked
```

### Bash Validation Commands (Run Manually)

```bash
# Check [SYNC] tags (should be 0 violations)
git log origin/main..HEAD --oneline | grep -v "\[SYNC\]\|\[FEAT\]\|\[FIX\]" | wc -l

# Check markdown lint (should be 0 lines > 80 chars)
awk 'length > 80' README.md BEST_PRACTICES.md

# Check UTF-8 encoding (should have no output)
file -i *.md docs/*.md | grep -v "UTF-8\|us-ascii"

# Check cross-ref validity (should have no output)
grep -o "\[.*\](.*\.md)" README.md | while read link; do
  file=$(echo "$link" | sed 's/.*(\([^)]*\)).*/\1/')
  [ ! -f "$file" ] && echo "BROKEN: $link"
done
```

### Templates (Copy-Paste Ready)

- **Daily Checklist:** backlog/TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md
- **Slack Report:** Included in checklist (use template)
- **Commit Messages:** TASK-005_SYNC_MATRIX.json (pre-formatted)

---

## 📞 ESCALATION PROCEDURE

### Minor Issues (Can Auto-Fix)
- [ ] Markdown lint: Fix locally + re-commit
- [ ] Trailing whitespace: Remove locally + re-commit
- [ ] Line too long: Break into 2 lines + re-commit

**Action:** "SWE Sr, found lint issue in README. Fixing now..."

### Medium Issues (Require Code Owner)
- [ ] Broken link: File doesn't exist yet
- [ ] Missing [SYNC] tag: Commit already pushed
- [ ] Wrong encoding: Non-UTF8 file detected

**Action:** "@SWE Sr, link to agent/convergence_monitor.py broken (file not created yet). Adding TODO, will fix when module done."

### Critical Issues (Block Merge)
- [ ] Multiple [SYNC] violations (> 3 commits)
- [ ] Encoding corruption in core files (README, BEST_PRACTICES)
- [ ] Dead links in critical paths

**Action:** "🔴 BLOCKER: Critical encoding issue found. Cannot sign-off merge until fixed. Needs immediate SWE + Arch review."

**Escalate to:** Angel (if > 2h unresolved)

---

## 🎓 REFERENCE CARDS

### Commit Message Format (Copy)

```
[TAG] Breve descrição — arquivos

Valid TAGs: [SYNC] [FEAT] [FIX] [TEST] [DOCS]

Examples:
✅ [SYNC] Update README for checkpoint_manager — README.md
✅ [SYNC] Add convergence patterns to BEST_PRACTICES — BEST_PRACTICES.md
✅ [SYNC] Log TASK-005 progress — docs/SYNCHRONIZATION.md

Rules:
  - Max 72 characters TOTAL
  - ASCII-only (no ç, ã, é, ó, etc)
  - Start with [TAG]
  - End with " — files affected" (optional but recommended)
```

### Markdown Lint Rules (Reference)

```
Max line length:      80 characters
Encoding:             UTF-8 ONLY
Trailing spaces:      NONE ALLOWED
Hard tabs:            Use 2 spaces instead
Code blocks:          Specify language (```python)
Headings:             # H1, ## H2, ### H3
Lists:                Proper indentation (2 spaces)
```

### Daily Checklist (Quick)

```
Every 08:00 UTC:
  [ ] Grep README for TASK-005 mentions — still current?
  [ ] Check git log for [SYNC] violations — any found?
  [ ] Run markdown lint — any errors?
  [ ] Check links in README — all valid?
  [ ] Check SYNCHRONIZATION.md — updated today?
  [ ] Post Slack report
  [ ] Sign-off on checklist
```

---

## 🏆 SUCCESS CRITERIA (Your Win)

**By 25 FEV 20:00 UTC, you will have:**

✅ Zero violations of [SYNC] tag policy (100% compliance)
✅ Markdown lint: 0 errors in all TASK-005 docs
✅ Cross-references: 100% valid (no broken links)
✅ UTF-8 encoding: Valid in 100% of files
✅ SYNCHRONIZATION.md: Complete audit trail logged
✅ CHANGELOG.md: TASK-005 entry created + verified
✅ Daily audits: 4/4 completed (23-25 FEV)
✅ Final sign-off: Approved for merge

**Bonus:**
⭐ Zero escalations to Angel (you handled everything)
⭐ All blockers resolved within 2 hours
⭐ Team trusts your docs quality 100%

---

## 🚀 NEXT STEPS (IMMEDIATE)

**TODAY (22 FEV) 15:00:**

1. ✅ Read: TASK-005_DOC_SYNCHRONIZATION_PLAN.md (20 min)
2. ✅ Read: TASK-005_SYNC_MATRIX.json (20 min)
3. ✅ Setup: Git hooks + CI/CD (2h)
4. ✅ Create: 3 commits with [SYNC] tags
5. ✅ Test: Local git push with fake commit (verify hooks work)
6. ✅ Slack: "Ready for implementation Monday"

**TOMORROW (23 FEV) 08:00:**

1. ✅ Run TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md
2. ✅ Post Slack report to #docs-governance
3. ✅ Monitor: SWE Sr implementation (4 modules)
4. ✅ As modules created: Update README + BEST_PRACTICES same day
5. ✅ Sign-off: Checklist PASS/FAIL

---

## 📚 YOUR DOCUMENTATION

You now own these files:

```
backlog/
├─ TASK-005_DOC_SYNCHRONIZATION_PLAN.md       ← Master plan
├─ TASK-005_SYNC_MATRIX.json                  ← Dependencies map
├─ TASK-005_DOC_ADVOCATE_DAILY_CHECKLIST.md   ← Daily audit
└─ TASK-005_DOC_ADVOCATE_IMPLEMENTATION_GUIDE.md ← This file

.githooks/
├─ pre-push-sync                  ← Validation script
└─ (pre-commit already exists)

docs/
├─ SYNCHRONIZATION.md             ← Your audit trail (update daily)
└─ POLICY_DOC_GOVERNANCE_PHASE4.md ← Enforcement rules (create today)
```

---

## ❓ FAQ

**Q: What if SWE Sr forgets [SYNC] tag?**
A: Git hooks will warn at push time. If they ignore it, block them in code review. Escalate if > 2 violations.

**Q: Can I auto-fix markdown lint?**
A: Yes! If simple (remove trailing spaces, shorten lines), fix it. Complex issues → ask SWE Sr.

**Q: What if line is > 80 chars and I can't break it?**
A: Timestamps, links, code examples are exempt. Use your judgment. Document exception in SYNCHRONIZATION.md.

**Q: How do I know if a link is valid?**
A: Run: `[ -f "path/file.md" ] && echo "valid" || echo "broken"`

**Q: What if SYNCHRONIZATION.md gets too long?**
A: Archive old entries (> 1 month) to: `docs/SYNCHRONIZATION_ARCHIVE_[MONTH].md`

**Q: Can I commit documentation without [SYNC]?**
A: NO. All doc commits require [SYNC] tag. This is enforced in 2024.

---

## 📞 CONTACT

**Your pair:** SWE Senior + ML Specialist
**Your backup:** Audit (QA Manager)
**Your escalation path:** Angel (final authority)

**Slack channel:** #docs-governance
**Daily standup:** 08:00 UTC (you report audit results)

---

## ✅ SIGN HERE

By reading this, you acknowledge:

**I, [NAME], accept the Doc Advocate role for TASK-005.**

I will:
- ✅ Run daily audits @ 08:00 UTC
- ✅ Enforce [SYNC] tag policy (100% compliance)
- ✅ Validate markdown lint + cross-refs
- ✅ Log audit trail in SYNCHRONIZATION.md
- ✅ Post daily Slack reports
- ✅ Escalate blockers within 2h
- ✅ Sign-off PRs only when ALL criteria met

**Signature:** _________________
**Date:** 22 FEV 2026
**Time:** _____:_____ UTC

---

**VERSION:** 1.0 FINAL
**STATUS:** ✅ Ready for implementation
**NEXT CHECKPOINT:** 23 FEV 08:00 UTC (First daily audit)

🚀 You got this!
