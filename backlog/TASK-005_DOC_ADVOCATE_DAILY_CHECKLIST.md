# ✅ DOC ADVOCATE TASK-005 SIGN-OFF CHECKLIST

**Owner:** Doc Advocate
**Date Started:** 22 FEV 2026
**Status:** 🟢 READY FOR DAILY USE

---

## 🎯 PURPOSE

Doc Advocate uses this checklist **daily** (08:00 UTC) during TASK-005 to verify:

1. **Code ↔ Docs Synchronization** (README, BEST_PRACTICES sync'd)
2. **Commit Message Compliance** ([SYNC]/[FEAT] tags, ASCII, ≤72 chars)
3. **Markdown Lint** (80 char lines, UTF-8 encoding)
4. **Cross-Reference Validation** (broken links, 100% valid)
5. **Audit Trail** (documentation of all changes logged)

**Check frequency:** Daily @ 08:00 UTC (after standup)
**Time budget:** 30 minutes
**Slack report:** Post summary to #docs-governance

---

## 📋 CHECKLIST TEMPLATE (Copy-Paste Daily)

```markdown
## 📚 Daily DOC SYNC AUDIT — TASK-005 PPO Training

**Date:** [DATE] (e.g., 23 FEV 2026)
**Audit Time:** 08:00-08:30 UTC
**Doc Advocate:** [NAME]
**Status:** ✅ PASS / 🔴 FAIL

---

### 1️⃣  CODE → DOCS SYNCHRONIZATION

#### 1.1 README.md Updates
- [ ] New module `agent/checkpoint_manager.py` mentioned? (with link)
- [ ] New module `agent/convergence_monitor.py` mentioned?
- [ ] New module `agent/rollback_handler.py` mentioned?
- [ ] New script `scripts/ppo_training_orchestrator.py` mentioned?
- [ ] Quick-start example provided for training?
- [ ] All links are valid (not broken)?

**Action if FAIL:** Add missing sections + commit [SYNC]

#### 1.2 BEST_PRACTICES.md Updates
- [ ] Section "### Checkpoint Management" exists?
- [ ] Code example in checkpoint section matches source?
- [ ] Section "### Convergence Monitoring" documented?
- [ ] Section "### Rollback Strategy" documented?
- [ ] All code examples are syntactically valid?
- [ ] References point to correct agent/ files?

**Action if FAIL:** Update missing sections + commit [SYNC]

#### 1.3 Architecture Documentation
- [ ] docs/ folder reflects TASK-005 structure?
- [ ] Data pipeline diagram updated?
- [ ] Integration points documented?

**Action if FAIL:** Create/update relevant docs

---

### 2️⃣  COMMIT MESSAGE VALIDATION

#### 2.1 [SYNC] Tag Compliance
- [ ] All doc-related commits have [SYNC] tag? (git log last 48h)
- [ ] Format: `[SYNC] Brief description — files`?
- [ ] Zero commits without [SYNC] in TASK-005 branch?

**Validation command:**
```bash
git log --oneline origin/main..feature/task-005-ppo-training | grep -v "\[SYNC\]\|\[FEAT\]\|\[FIX\]" | wc -l
# Should output: 0
```

#### 2.2 Message Length & Format
- [ ] All messages ≤ 72 characters?
- [ ] No "Updated docs" or "typo fix" (too vague)?
- [ ] All messages start with [TAG]?

**Sample bad messages (FAIL the audit):**
- ❌ "Updated documentation" (no tag)
- ❌ "[SYNC] This is a very long message that exceeds 72 chars limit and needs refactor" (too long)
- ❌ "Fix typo in README" (missing tag)

#### 2.3 ASCII-Only Validation
- [ ] All commit messages contain ONLY ASCII (0-127)?
- [ ] No Unicode chars (ç, ã, é, ó, etc)?

**Validation command:**
```bash
git log --oneline origin/main..feature/task-005-ppo-training | \
  while read line; do
    if echo "$line" | grep -qP '[^\x00-\x7F]'; then
      echo "NON-ASCII: $line"
    fi
  done
# Should output: (nothing)
```

---

### 3️⃣  MARKDOWN LINT COMPLIANCE

#### 3.1 File Encoding
- [ ] README.md is UTF-8 encoded?
- [ ] BEST_PRACTICES.md is UTF-8?
- [ ] All .md files in docs/ are UTF-8?
- [ ] All .md files in backlog/ are UTF-8?

**Validation command:**
```bash
file -i README.md BEST_PRACTICES.md docs/*.md backlog/*.md | \
  grep -v "UTF-8\|us-ascii"
# Should output: (nothing)
```

#### 3.2 Line Length (Max 80 chars)
- [ ] README.md: 0 lines > 80 chars?
- [ ] BEST_PRACTICES.md: 0 lines > 80 chars?
- [ ] docs/SYNCHRONIZATION.md: 0 lines > 80 chars?
- [ ] backlog/SPRINT_BACKLOG: 0 lines > 80 chars?
- [ ] backlog/TASKS_TRACKER_REALTIME: 0 lines > 80 chars?

**Validation command:**
```bash
for file in README.md BEST_PRACTICES.md docs/SYNCHRONIZATION.md backlog/*.md; do
  LONG=$(awk 'length > 80' "$file" | wc -l)
  [ "$LONG" -gt 0 ] && echo "$file: $LONG lines > 80 chars"
done
# Should output: (nothing)
```

#### 3.3 Trailing Whitespace
- [ ] README.md: no trailing spaces?
- [ ] BEST_PRACTICES.md: no trailing spaces?
- [ ] SYNCHRONIZATION.md: no trailing spaces?

**Validation command:**
```bash
grep ' $' README.md BEST_PRACTICES.md docs/SYNCHRONIZATION.md | wc -l
# Should output: 0
```

#### 3.4 Custom Markdown Rules
- [ ] Headings are properly formatted (# H1, ## H2)?
- [ ] Code blocks have language specified (```python)?
- [ ] Lists are properly indented?
- [ ] Tables are properly formatted (pipes aligned)?

---

### 4️⃣  CROSS-REFERENCE VALIDATION

#### 4.1 Broken Link Check
- [ ] All internal links in README are valid?
- [ ] All file references exist (not deleted)?
- [ ] All line number references are correct?

**Validation command:**
```bash
grep -o "\[.*\]([^)]*\.py)" README.md BEST_PRACTICES.md | \
  while read link; do
    file=$(echo "$link" | sed 's/.*(\([^)]*\)).*/\1/')
    if ! [ -f "$file" ]; then
      echo "BROKEN: $link"
    fi
  done
# Should output: (nothing)
```

#### 4.2 Format Validation
- [ ] Links use correct format: `[text](path.md)` or `[text](path.md#L10)`?
- [ ] Line number format: `#L10` (not `#line10` or `#L10-L15`)?
- [ ] File paths use `/` (not `\`)?

**Valid examples:**
- ✅ `[checkpoint manager](agent/checkpoint_manager.py)`
- ✅ `[See example](BEST_PRACTICES.md#L150)`
- ✅ `[Find link](docs/folder/file.md)`

**Invalid examples:**
- ❌ `[text](C:\repo\file.md)` (Windows pathss)
- ❌ `[text](file.md#150)` (wrong line format)
- ❌ `[text](#L10-L15)` (range, should be separate links)

#### 4.3 Cross-Reference Matrix
- [ ] All code files mentioned in README exist?
- [ ] All TASK-005 modules documented in BEST_PRACTICES?
- [ ] All TASK-005 doc updates logged in SYNCHRONIZATION.md?

---

### 5️⃣  AUDIT TRAIL & LOGGING

#### 5.1 SYNCHRONIZATION.md Entries
- [ ] SYNCHRONIZATION.md updated with TASK-005 progress?
- [ ] Each entry has: DATE | TIME | EVENT | OWNER | STATUS?
- [ ] No older than 2 hours (continuous update during dev)?

**Example entry:**
```
| 23 FEV | 10:00 UTC | agent/checkpoint_manager.py created | SWE Sr | ✅ README updated |
```

#### 5.2 CHANGELOG.md Entry
- [ ] CHANGELOG.md has TASK-005 section?
- [ ] Lists 4 new modules?
- [ ] Includes metrics (Sharpe, training time)?
- [ ] Dated correctly?

#### 5.3 Commit Audit Trail
- [ ] All [SYNC] commits logged in SYNCHRONIZATION.md?
- [ ] Timestamps match git log?
- [ ] Owners documented for each change?

**Validation command:**
```bash
git log origin/main..feature/task-005-ppo-training --oneline | \
  grep "\[SYNC\]" | wc -l
# Cross-check this count with SYNCHRONIZATION.md entries
```

---

### 6️⃣  RISK & BLOCKER CHECK

#### 6.1 Any Issues Found?
- [ ] Encoding errors detected?
- [ ] Broken links in docs?
- [ ] Missing [SYNC] tags?
- [ ] Line length violations?
- [ ] Non-ASCII in commits?

#### 6.2 Blockers for Merge
- [ ] Any [SYNC] tag violations? (FAIL = blocker)
- [ ] Any encoding violations? (FAIL = blocker)
- [ ] Any broken links in README? (FAIL = blocker)
- [ ] Any critical doc missing? (FAIL = blocker)

**If ANY blockers: Set status to 🔴 FAIL and do NOT sign off**

---

## 📊 AUDIT RESULT

### Overall Status

**Date:** [DATE]
**Result:** ✅ PASS / 🔴 FAIL
**Blocker Count:** 0 / _
**Warning Count:** _ / _

### Sign-Off

- [ ] Doc Advocate reviewed all sections above
- [ ] All blockers resolved (if any)
- [ ] Ready for merge? **YES / NO**

**Doc Advocate Name:** ___________________
**Signature/Approval:** ✅ / 🔴
**Time Completed:** _________ UTC

---

## 📝 NOTES & ACTIONS

Actions taken today:
1. [Describe any fixes made]
2. [Any blockers escalated to SWE Sr?]
3. [Next steps for tomorrow?]

---

## 🔗 REFERENCES

- 📋 Sync Plan: [backlog/TASK-005_DOC_SYNCHRONIZATION_PLAN.md](../backlog/TASK-005_DOC_SYNCHRONIZATION_PLAN.md)
- 📊 Sync Matrix: [backlog/TASK-005_SYNC_MATRIX.json](../backlog/TASK-005_SYNC_MATRIX.json)
- 📚 SYNCHRONIZATION: [docs/SYNCHRONIZATION.md](../docs/SYNCHRONIZATION.md)
- 🎯 SPRINT BACKLOG: [backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md](../backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md)
- 🔄 TRACKER: [backlog/TASKS_TRACKER_REALTIME.md](../backlog/TASKS_TRACKER_REALTIME.md)

---

## ✅ AUDIT COMPLETION

After completing audit, **post summary to Slack:**

```
📚 DOC SYNC AUDIT PASS — TASK-005
✅ README sync'd (4 modules listed)
✅ BEST_PRACTICES updated (3 sections)
✅ 100% [SYNC] tag compliance
✅ Markdown lint: 0 errors
✅ Cross-refs: 100% valid
✅ Ready for merge

Next: Training day N, continuing sync monitoring
```

---

**Template Version:** 1.0
**Last Updated:** 22 FEV 2026
**Status:** 🟢 READY FOR DAILY USE
