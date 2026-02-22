# 📋 POLICY DE GOVERNANÇA DE DOCUMENTAÇÃO — PHASE 4

**Versão:** 1.0
**Data Efetiva:** 21 FEV 2026, 22:40 UTC
**Aprovado por:** Angel (Investidor), Board (12/16 unanimidade)
**Owner:** DOC Advocate (delegado Audit)
**Status:** ✅ ATIVO — Operacionalização PHASE 4

---

## 🎯 PRINCÍPIOS FUNDAMENTAIS

### 1. **Responsabilidade Durante (não post-merge)**

- ✅ Dev é responsável por documentação **qua during coding**
- ✅ Commit não deve sair do dev laptop sem docs sincronizada
- ❌ Não é aceitável "vou documentar amanhã"

### 2. **Enforcement Automático (git hooks + CI/CD)**

- ✅ Git hooks bloqueiam commit se markdownlint ou docstring falhar
- ✅ GitHub Actions bloqueiam merge se validação não passar
- ✅ Pre-push verifica [SYNC] tag obrigatória

### 3. **Nível Padrão (not minimal, not maximum)**

- ✅ **Code** — Docstrings em português (agent/, execution/, risk/, backtest/)
- ✅ **Arquitetura** — Diagramas + explanação técnica em docs/
- ✅ **Decisões Executivas** — Rastreabilidade em SYNCHRONIZATION.md
- ❌ **Research papers / Learnings** — Não requerido (futuro nice-to-have)

### 4. **Audit Trail Completo (rastreabilidade)**

- ✅ Cada mudança crítica documentada em `docs/SYNCHRONIZATION.md`
- ✅ Timestamp + Owner + Files alterados + Validation
- ✅ Permite auditoria externa: "O que mudou? Quem aprovou? Quando?"

---

## 📂 ARQUIVOS CRÍTICOS (Requerem [SYNC])

| Arquivo | Trigger | Owner Sync | Frequency | SLA |
|---------|---------|---------|-----------|-----|
| **README.md** | Version muda, install steps mudam, setup altera | Elo + DOC Advocate | On change | 4h |
| **docs/ARCHITECTURE.md** | Arquitetura de software/RL muda, diagramas atualizam | Arch + DOC Advocate | Per sprint | 4h |
| **docs/EQUIPE_FIXA.md** | Time muda, especialidades mudam, roles evoluem | Elo + DOC Advocate | On hire/role change | 4h |
| **BEST_PRACTICES.md** | Padrões dev evoluem, patterns consolidam, regras mudam | Arch + DOC Advocate | Quarterly / on decision | 4h |
| **docs/SYNCHRONIZATION.md** | QUALQUER mudança crítica (isso) | DOC Advocate | Per commit critical | Immediate |
| **docs/POLICY_DOC_GOVERNANCE.md** | Policy própria evolui, SLAs mudam | Elo + DOC Advocate | Per decision | 4h |
| **docs/STATUS_ATUAL.md** | Status real-time do projeto muda, milestones atingem | Planner + Audit | Weekly | Daily |

---

## 🏷️ TAG [SYNC] — OBRIGATÓRIA

Commits que alteram docs críticos **DEVEM** ter tag `[SYNC]` na mensagem.

### ✅ Formato Obrigatório

```
[SYNC] Descrição breve em português — mudanças de docs

Exemplos válidos:
  [SYNC] F-11 Reward Shaping v2 — docs/BEST_PRACTICES.md + agent/ docstrings atualizado
  [SYNC] Novo membro Arch (RL specialist) — docs/EQUIPE_FIXA.md línea 24 atualizado
  [SYNC] Circuit breaker -3% ativado — docs/ARCHITECTURE.md risk layer + runbook criado
  [SYNC] Go-live canary phase 1 — README.md deployment section + SYNCHRONIZATION entry
```

### ❌ Exemplos NÃO Aceitos

```
WRONG:
  "Docs update" ← Muito vago, não descreve o quê
  "Fix typo" ← Se é APENAS typo, pode ser sem [SYNC] (exceção)
  "Updated architecture" ← Sem [SYNC] tag, será rejeitado
  "[FIX] Algo" ← Tag incorreta, deve ser [SYNC]
```

### 🛑 Bloqueio Pré-Push

Git hook (pre-push) valida automaticamente:

```bash
$ git push
  🔍 PRE-PUSH: Verificando conformidade [SYNC] tag...

  ❌ AVISO: Mudanças em arquivos críticos detectadas:
     Arquivos: docs/ARCHITECTURE.md
     Commit: abc1234

  ❌ Sua mensagem de commit NÃO contém [SYNC] tag.
  [TAG OBRIGATÓRIA PARA MUDANÇAS EM DOCS CRÍTICAS]

  CORRIGIR:
  $ git commit --amend -m "[SYNC] Descrição — docs atualizado"
  $ git push
```

---

## 🔧 ENFORCEMENT DURANTE DESENVOLVIMENTO

### ✅ Step 1: Dev trabalha no código

```bash
# Dev altera agent/reward_func.py
$ vi agent/reward_func.py
$ vi docs/BEST_PRACTICES.md  (documentação ao mesmo tempo!)
```

### ✅ Step 2: Pre-commit Hook (local validation)

```bash
$ git add .
$ git commit -m "[SYNC] F-11 Reward Shaping — docs atualizado"

  🔍 PRE-COMMIT: Validando documentação...
    ├─ Executando markdownlint... ✅
    ├─ Executando docstring checker... ✅
    ├─ Verificando encoding UTF-8... ✅
    └─ Verificando [SYNC] tag para mudanças críticas...
       ⚠️ Detectado mudança em docs críticas.
       Certifique-se de usar [SYNC] tag. ✅ (você usou!)

  ✅ PRE-COMMIT VALIDAÇÃO COMPLETA
```

### ✅ Step 3: Pre-push Hook (remote validation)

```bash
$ git push

  🔍 PRE-PUSH: Verificando conformidade [SYNC] tag...
    Commits com docs críticas: 1
    [SYNC] tags: 1 ✅

  ✅ PRE-PUSH VALIDAÇÃO COMPLETA
```

### ✅ Step 4: GitHub Actions (CI/CD)

```
PR abre automaticamente dispara:
  ✓ Markdownlint (80 char, UTF-8, code blocks)
  ✓ Python Docstring Coverage (agent/, execution/, risk/, backtest/)
  ✓ [SYNC] Tag Requirement
  ✓ SYNCHRONIZATION.md Entry validation
  ✓ UTF-8 Encoding check

Se falhar qualquer coisa → Build vermelho, merge bloqueado
```

### ✅ Step 5: DOC Advocate Approve (last person)

```
DOC Advocate checklist ANTES de approve:
  ✅ Markdownlint passed? (CI/CD tá verde)
  ✅ Docstrings completos? (review manual se edge case)
  ✅ [SYNC] tag válida?
  ✅ SYNCHRONIZATION.md entry criada? (ou será criar)
  ✅ Arquivo não tem encoding corrompido?

Se tudo OK → Approve + sign-off
Se falhar → Request changes + motivo específico
```

---

## 📊 COMPLIANCE MATRIX

| Phase | Item | Owner | Tool | Blocker? | SLA |
|-------|------|-------|------|----------|-----|
| **Local** | Markdownlint | Dev | Git Hook | ❌ YES | Real-time |
| **Local** | Docstring Check | Dev | Git Hook | ❌ YES | Real-time |
| **Local** | UTF-8 Encoding | Dev | Git Hook | ❌ YES | Real-time |
| **Local** | [SYNC] Tag | Dev | Git Hook (warn) | ⚠️ WARN | Pre-commit |
| **Remote** | [SYNC] Tag Requirement | Git | Pre-push hook | ❌ YES | Pre-push |
| **CI/CD** | Markdownlint Full | CI | GitHub Actions | ❌ YES | Pre-merge |
| **CI/CD** | Docstring Coverage | CI | GitHub Actions | ❌ YES | Pre-merge |
| **CI/CD** | [SYNC] Tag Validation | CI | GitHub Actions | ❌ YES | Pre-merge |
| **CI/CD** | SYNCHRONIZATION Entry | CI | GitHub Actions | ⚠️ WARN | Pre-merge |
| **Review** | DOC Advocate Approval | Human | Manual | ❌ YES | Pre-merge |

---

## 📋 ACCEPTANCE CRITERIA (Merge Permission)

Uma PR **PODE mergear** SOMENTE SE **ALL** dos seguintes:

```
🟢 Code Review: Aprovado (lógica correta)
🟢 QA Testing: Aprovado (testes passam)
🟢 Markdownlint CI: ✅ PASSED
🟢 Docstring Check CI: ✅ PASSED
🟢 UTF-8 Encoding CI: ✅ PASSED
🟢 [SYNC] Tag Validation CI: ✅ PASSED ou N/A (if no docs changes)
🟢 DOC Advocate: ✅ APROVADO (last sign-off)
🟢 Branch Protection: ✅ SATISFIED (all checks green)
```

Se **ANY** estiver vermelho → **MERGE BLOQUEADO** até correção.

---

## 📊 MÉTRICAS & SLAs

### Responsabilidade Time (Durante Dev)

| Métrica | Target | SLA | Owner |
|---------|--------|-----|-------|
| **Markdownlint Pass Rate** | 100% | Per commit | Dev |
| **Docstring Coverage** | 100% (critical paths) | Per commit | Dev |
| **UTF-8 Validity** | 100% | Per commit | Dev |
| **[SYNC] Tag If Needed** | 100% (critical changes) | Per commit | Dev |

### Responsabilidade DOC Advocate (Review)

| Métrica | Target | SLA | Owner |
|---------|--------|-----|-------|
| **PR Review Time** | <2h during work hours | Per PR | DOC Advocate |
| **Daily Audit Completion** | 08:00-09:00 UTC | Daily | DOC Advocate |
| **Docs Gap Resolution** | <4h from discovery | Per incident | DOC Advocate |
| **SYNCHRONIZATION.md Entries** | 100% critical changes | On commit | DOC Advocate |

### Indicadores de Saúde (Board)

| Métrica | Target | Frequency | Owner |
|---------|--------|-----------|-------|
| **Compliance %** | ≥95% | Weekly | Audit |
| **Critical Gaps** | 0 | Daily | DOC Advocate |
| **CI/CD Pass Rate** | 100% | Per PR | GitHub Actions |

---

## ⚠️ EXCEÇÕES (SEM [SYNC] TAG)

### Permitido SEM [SYNC] tag:

```
✅ Typo fixes em .md files (grammar, spelling)
   Example: "Fix typo in README → 'confgiuation' → 'configuration'"

✅ Comentário em código Python (não muda interface)
   Example: "Add clarification comment in agent/decision.py"

✅ Reformatação de código (sem mudança lógica/interface)
   Example: "[FIX] Black formatting in execution/manager.py"
```

### Requer [SYNC] tag:

```
❌ Docstring novo/alterado (interface/behavior doc)
❌ README.md alterado
❌ docs/ arquivo qualquer
❌ BEST_PRACTICES.md
❌ Qualquer mudança de API/interface pública
```

**Rule of thumb:** "Se próximo operator/trader precisa saber sobre isso, é [SYNC]"

---

## 🚨 VIOLATIONS & ESCALAÇÃO

### Cenário 1: Dev faz commit SEM [SYNC] mas docs foi alterado

```
Detecção:
  - Pre-push hook tenta bloquear (mas dev força --no-verify)
  - CI/CD detecta violação

Ação imediata:
  1. GitHub Actions falha com mensagem clara
  2. PR fica em MERGE BLOCKED state
  3. DOC Advocate notificado
  4. Dev recebe notification e corrige:
     $ git commit --amend -m "[SYNC] Descrição — docs atualizado"
     $ git push --force-with-lease
```

### Cenário 2: Markdownlint falha (80 char, UTF-8)

```
Detecção:
  - Pre-commit hook para
  - Dev vê erro específico

Ação imediata:
  1. Dev corrige arquivo .md
  2. Re-runs markdownlint: markdownlint docs/**/*.md
  3. Se tá OK, tenta commit de novo
  4. Se não consegue, DOC Advocate ajuda (advisory)
```

### Cenário 3: Encoding corrompido (caracteres UTF-8 invalid)

```
Detecção:
  - Encoding check hook detecta
  - CI/CD confirma

Ação imediata:
  1. Dev reescreve arquivo com iconv:
     iconv -f ISO-8859-1 -t UTF-8 arquivo.md > arquivo-fixed.md
     mv arquivo-fixed.md arquivo.md
  2. Commit de novo
  3. Se persistir → Elo (Governance) envolve para ajuda
```

### Escalação Crítica (Risk/Compliance docs desatualizado)

```
Se detectado:
  - Mudança de risco NÃO DOCUMENTADA
  - Compliance procedure alterada sem docs
  - Liquidation safety não update em README

Trigger imediato:
  → Escalação para Elo (Governance) + Dr. Risk + Compliance
  → MERGE BLOQUEADO até sincronização
  → Possível rollback de commit anterior
```

---

## 📅 IMPLEMENTAÇÃO & TIMELINE

### ✅ **Phase 4 Kickoff (21 FEV 22:40 UTC)**

- [ ] Git hooks criados e testados (`.githooks/pre-commit`, `.pre-push`)
- [ ] CI/CD workflow ativo (`.github/workflows/docs-validate.yml`)
- [ ] Policy formalizada (este arquivo)
- [ ] DOC Advocate nomeado (Audit delegation)

### ✅ **Pre-Go-Live (22 FEV 08:00 UTC)**

- [ ] Git hooks configurado em todos os devs (`git config core.hooksPath .githooks`)
- [ ] First daily audit executado
- [ ] Team briefing: "Docs policy ativa agora"

### ✅ **Go-Live Canary (22 FEV 10:00 UTC)**

- [ ] TASK-004 PR tem [SYNC] tag + approval
- [ ] Runbooks documentados
- [ ] Operador pode ler README e entender deploy

### 📈 **Sprint 1 (21-25 FEV)**

- [x] TASK-001 até TASK-007 com [SYNC] + docs
- [x] 100% compliance esperado
- [x] Weekly report consolidado

---

## 📞 GOVERNANCE CONTACTS

| Role | Name | Slack | Report |
|------|------|-------|--------|
| **DOC Advocate** | Audit Team | #docs-governance | Daily 08:00 UTC |
| **Supervisor** | Elo (Governance) | @elo | Weekly Friday |
| **Escalation** | Angel (Investidor) | @angel.investor | Per incident |

---

## ✅ APROVAÇÃO & SIGN-OFF

```
DECISÃO #3 — POLICY DE DOCUMENTAÇÃO APROVADA

Aprovado por:     Angel (Investidor Principal)
Board Quórum:     12/16 — UNANIMIDADE
Timestamp:        21 FEV 2026, 22:40 UTC
Efetivo em:       IMEDIATO (next commit com docs)

Dissidências:     NENHUMA
Condicionantes:   NENHUMA
Próxima Revisão:  PHASE 5 (post-live 72h)
```

---

**Status:** ✅ OPERACIONAL — Phase 4 "Governança de DOCs"
**Última Atualização:** 21 FEV 2026, 22:40 UTC
**Próximo Update:** 22 FEV 2026, 08:00 UTC (daily audit report)
