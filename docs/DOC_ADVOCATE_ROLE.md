# 📚 DOC ADVOCATE — Guardiá de Documentação

**Papel Crítico Aprovado:** DECISION #3 — Governança de Documentação (21 FEV 2026)
**Status:** ✅ ATIVO — Operacionalização PHASE 4
**Owner Delegado:** Audit Team (QA Lead)

---

## 📋 Definição do Papel

**DOC Advocate** é a persona responsável por garantir que toda documentação do projeto (`docs/`, `README.md`, `BEST_PRACTICES.md`, etc) esteja **sempre sincronizada com o código**, com padrões elevados de qualidade (80 char max, UTF-8 válido, docstrings completas).

### 🎯 Propósito

- ✅ Evitar "código pronto, docs desatualizado"
- ✅ Enforçar responsabilidade **durante desenvolvimento**, não post-merge
- ✅ Manter auditoria trail limpo (rastreabilidade de decisões)
- ✅ Facilitar operações live (operadores entendem o sistema)

---

## 👤 Responsabilidades Principais

### 1. **Enforcement de Padrões Markdown**

```
Diárias: Validar que novos/alterados .md files obedecem:
  ✓ Max 80 chars por linha
  ✓ UTF-8 válido (sem caracteres corrompidos ou encoded)
  ✓ Code blocks com language declaration (```python, ```bash)
  ✓ Títulos descritivos (não vazios)
  ✓ Listas formatadas corretamente
```

**Tool:** `markdownlint` com config `.markdownlintrc.json`

### 2. **Validação de Docstrings Python**

```
Módulos críticos (agent/, execution/, risk/, backtest/):
  ✓ Cada arquivo >20 linhas deve ter docstring inicial
  ✓ Funções/classes devem ter docstrings descritivas
  ✓ @param, @return, @raises documentados em português
```

**Tool:** Python AST parser + manual code review

### 3. **Approval de PR — Última Pessoa**

```
Fluxo de PR:
  1. Dev abre PR com [SYNC] tag
  2. Code reviewer aprova lógica
  3. Tester aprova funcionalidade
  4. DOC Advocate APROVA ÚLTIMO
     └─ Sign-off final: docs sincronizadas + padrões OK
```

### 4. **Sign-off em `docs/SYNCHRONIZATION.md`**

```
Toda mudança CRÍTICA requer entry:

## 🔄 MUDANÇA: [Data HH:MM UTC] — [Descrição]
- Owner: [Nome]
- Files alterados: [lista]
- Sincronização: ✅ COMPLETA
- Validação: DOC Advocate ✅ [Nome]
- Timestamp: 2026-02-21T22:40:00Z
```

### 5. **Daily Audit @ 08:00 UTC**

```
Checklist:
  ✓ PRs merged ontem têm docs updates?
  ✓ Gaps de documentação detectados?
  ✓ Markdownlint passou 100%?
  ✓ Python docstrings completas?
  ✓ SYNCHRONIZATION.md atualizado?

Report: Slack channel #docs-governance
  Format: "✅ N docs synced, Y gaps fixed, Z blockers"
```

### 6. **Escalação Imediata de Gaps Críticos**

```
Se detectar:
  🔴 Mudança de risco NÃO DOCUMENTADA → escalação imediata
  🔴 API/interface pública alterada → update docs obrigatório
  🔴 Encoding corrompido → commit deve ser refeito

Owner: Elo (Governança) + Audit (QA Lead)
```

---

## 🔐 Autoridade & Poder de Veto

### ✅ Poder de APROVAÇÃO

- ✓ PR só pode mergear após DOC Advocate sign-off
- ✓ Tag `[SYNC]` validação — rejeita commits sem ela
- ✓ Designar member novo para documentação específica

### 🚫 Poder de BLOQUEIO

- 🔴 Bloquear merge se docstring faltando em agent/, execution/, risk/
- 🔴 Bloquear merge se markdownlint falhar
- 🔴 Bloquear merge se SYNCHRONIZATION.md não atualizado (mudanças críticas)
- 🔴 Bloquear push se encoding UTF-8 inválido

### ⚠️ Poder ADVISORY

- 💡 Aconselhar Dev sobre estrutura melhor de docs
- 💡 Propor templates para novos arquivos
- 💡 Sugerir reorganização de docs para clarity

---

## 📊 KPIs & Métricas de Sucesso

| Métrica | Target | SLA | Owner |
|---------|--------|-----|-------|
| **Markdownlint Pass Rate** | 100% | Real-time | DOC Advocate |
| **Docstring Coverage (critical paths)** | 100% | Per PR | DOC Advocate |
| **[SYNC] Tag Compliance** | 100% (critical changes) | Pre-push | DOC Advocate |
| **Daily Audit Completion** | 08:00-09:00 UTC | Daily | DOC Advocate |
| **Time to Fix DOC Gap** | ≤4h | Per incident | DOC Advocate |
| **SYNCHRONIZATION.md Entries** | 100% critical changes | On commit | DOC Advocate |

---

## 🔄 Interfaces & Coordenação

### Trabalha COM:

- **Dev Team** — Implementa docs durante coding
- **Audit/QA** — Supervisor, daily standup, weekly reports
- **Arch** — Valida mudanças de arquitetura
- **Elo** — Governança, escalações críticas
- **Board** — Reporta status semanal

### Board Members Críticos:

| Membro | Interação | Frequência |
|--------|-----------|-----------|
| **Audit** | Supervisor direto | Daily (08:00 UTC) |
| **Elo** | Escalações + governance | Weekly |
| **Arch** | Arquitetura docs alignment | Per sprint |
| **The Brain** | ML/RL docs validation | Per feature |
| **Compliance** | Audit trail validation | Weekly |

---

## 📅 Timeline & Operacionalização

### ⏰ **Phase 4 Kickoff (21 FEV 2026, 22:40 UTC)**

- ✅ Role formalizado
- ✅ Git hooks setup (`.githooks/pre-commit`, `.pre-push`)
- ✅ CI/CD workflow criado (`.github/workflows/docs-validate.yml`)
- ✅ Policy document publicado (`docs/POLICY_DOC_GOVERNANCE.md`)

### 🚀 **Go-Live Preparado (22 FEV 10:00 UTC)**

- ✓ DOC Advocate nomeado
- ✓ Daily audits iniciadas
- ✓ Git hooks ativo em todos repos
- ✓ CI/CD bloqueios de validação ativo

### 📈 **Sprint 1 (21-25 FEV)**

- Todos PRs de TASK-001 até TASK-007 com [SYNC] tag
- 100% de compliance esperado
- Weekly report consolidado

---

## 🛠️ Tools & Setup

### Git Hooks

```bash
# Setup automático
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push

# Run manual (testing)
bash .githooks/pre-commit
bash .githooks/pre-push
```

### CI/CD Pipeline

```yaml
# Automaticamente roda em cada push/PR:
  - Markdownlint: ❌ bloqueia merge se falhar
  - Docstring Check: ❌ bloqueia merge se falhar
  - UTF-8 Validation: ❌ bloqueia merge se falhar
  - [SYNC] Tag Check: ❌ bloqueia merge se falhar
```

### Local Validation

```bash
# Before dev commits
markdownlint docs/**/*.md README.md BEST_PRACTICES.md
python scripts/check_docstrings.py agent/ execution/ risk/ backtest/

# Dev commit (hooks run automatically)
git commit -m "[SYNC] Descrição — docs atualizado"

# Before push (hooks validate)
git push
```

---

## ✍️ Exemplo: O que DOC Advocate Faz

### Cenário: Dev altera F-11 (Reward Shaping)

```
[Dev]
  1. Altera agent/reward_func.py
  2. Atualiza docstring em português
  3. Altera agent/reward_config.yaml
  4. Commit local (hooks executam):
     ✓ Markdownlint: nada (é .py)
     ✓ Docstring: OK
     ✓ Encoding: OK
  5. Commit msg: "[SYNC] F-11 Reward Shaping v2 — docs/BEST_PRACTICES atualizado"
  6. Abre PR

[DOC Advocate]
  1. Recebe PR
  2. Verifica: [SYNC] tag ✅, docs/BEST_PRACTICES.md alterado ✅
  3. Valida: markdownlint, docstring, encoding all ✅
  4. Assina entry em docs/SYNCHRONIZATION.md:
     ```
     ## 🔄 MUDANÇA: 22 FEV 11:30 UTC — F-11 Reward Shaping v2
     - Owner: Dev
     - Files: agent/reward_func.py, agent/reward_config.yaml, docs/BEST_PRACTICES.md
     - Sincronização: ✅ COMPLETA
     - Validação: DOC Advocate ✅ [Audit Team]
     ```
  5. Aprova PR ✅ → Merge liberado

[Result]
  ✅ Code + Docs sincronizados
  ✅ Audit trail limpo (entry em SYNCHRONIZATION.md)
  ✅ Próximo operador entende mudança
```

---

## 📞 Contact & Escalação

**Reporta para:** Audit Team (QA Lead)
**Escalação:** Elo (Governance)
**Decision Authority:** Angel (Investidor)

**Slack:** #docs-governance
**Daily Report:** 08:00 UTC
**Weekly Report:** Friday 21:00 UTC

---

**Status:** ✅ OPERACIONAL — Phase 4 Iniciada
**Última Atualização:** 21 FEV 2026, 22:40 UTC
