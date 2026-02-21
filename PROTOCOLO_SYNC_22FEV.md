# 📋 PROTOCOLO [SYNC] — Sincronização Obrigatória de Documentação

**Válido a partir de:** 22 FEV 2026  
**Aprovado por:** Board Meeting (Investidor)  
**Owner:** Git Master / Facilitador  
**Referência:** docs/DECISIONS.md #1

---

## 🎯 OBJETIVO

Garantir que **toda mudança em código ou configuração seja imediatamente sincronizada com documentação**, evitando divergência entre realidade e docs.

**Regra de Ouro:** Se não está documentado, não efeito legal.

---

## 📋 CHECKLIST PRÉ-COMMIT

**Antes de fazer `git commit`, SEMPRE:**

```
□ IDENTIFICAR MUDANÇA
  ├─ Qual arquivo foi alterado? ________________________
  ├─ Tipo: [ ] Feature [ ] Fix [ ] Docs [ ] Test [ ] Config
  └─ Impacto: [ ] API [ ] Risk [ ] Data [ ] Reward

□ MAPEAR DEPENDÊNCIAS (usar Matriz abaixo)
  ├─ Documentos que PODEM ser impactados?
  └─ Quem é owner desses documentos?

□ ATUALIZAR DOCUMENTAÇÃO (se necessário)
  ├─ [ ] Arquivo oficial em /docs/ (ex: FEATURES.md)
  ├─ [ ] docs/STATUS_ATUAL.md (timestamp + referência)
  ├─ [ ] docs/SYNCHRONIZATION.md (audit trail)
  ├─ [ ] CHANGELOG.md (Se mudança pública)
  └─ [ ] README.md NUNCA (só links para /docs/)

□ VALIDAÇÃO FINAL
  ├─ [ ] Nenhuma duplicação de conteúdo
  ├─ [ ] Nenhuma linha > 80 caracteres em .md
  ├─ [ ] UTF-8 correto (sem encoding ruído)
  ├─ [ ] Português consistente
  ├─ [ ] Commit message + [SYNC] tag
  └─ [ ] Nenhum segredo em docs

□ SUBMETER
  └─ git commit -m "[SYNC] Descrição clara da mudança"
```

---

## 🗂️ MATRIZ DE DEPENDÊNCIAS

**Quando você altera:**

### `config/symbols.py`
│ Atualizar:
├─ `docs/FEATURES.md` (lista de pares)
├─ `docs/STATUS_ATUAL.md` (timestamp)
├─ `docs/SYNCHRONIZATION.md` (audit)
├─ `README.md` (se visível externamente)
└─ `playbooks/__init__.py` (imports)

### `agent/reward.py`
│ Atualizar:
├─ `docs/FEATURES.md` (Round X status)
├─ `docs/REWARD_FIXES_*.md` (histórico técnico)
├─ `docs/STATUS_ATUAL.md` (timestamp)
├─ `docs/SYNCHRONIZATION.md` (audit)
├─ `CHANGELOG.md` (mudança pública)
└─ Associado: **test_reward_*.py obrigatório**

### `backtest/`, `agent/environment.py`
│ Atualizar:
├─ `docs/FEATURES.md` (F-12 status)
├─ `docs/ROADMAP.md` (timeline)
├─ `docs/STATUS_ATUAL.md` (blockers)
├─ `docs/SYNCHRONIZATION.md` (técnico)
├─ `CHANGELOG.md` (release notes)
└─ Associado: **testes unitários obrigatório** (F-12e)

### `playbooks/*.py`
│ Atualizar:
├─ `docs/FEATURES.md` (novo playbook?)
├─ `config/symbols.py` (aponta?!)
├─ `playbooks/__init__.py` (registrado?)
├─ `docs/STATUS_ATUAL.md` (timestamp)
├─ `docs/SYNCHRONIZATION.md` (audit)
└─ Associado: **test_*playbook.py obrigatório**

### `execution/*.py`, `config/execution_config.py`
│ Atualizar:
├─ `docs/FEATURES.md` (mudança em sizing?)
├─ `docs/STATUS_ATUAL.md` (risk change)
├─ `docs/SYNCHRONIZATION.md` (audit)
├─ `CHANGELOG.md` (se crítico)
└─ Associado: **risk validation obrigatória**

### `README.md`, `/docs/*.md`
│ Atualizar:
├─ `docs/SYNCHRONIZATION.md` (registrar mudança)
├─ CHANGELOG.md (se versão pública)
└─ Não alterar README.md sem necessidade (preferir /docs/)

---

## ✍️ FORMATO DE COMMIT MESSAGE

**Padrão Obrigatório:**

```
[SYNC] Escopo breve em português

- Mudança linha 1
- Mudança linha 2
- Docs sincronizadas: [lista]

Referência: docs/[arquivo].md
```

### Exemplos CORRETOS

```
[SYNC] Atualizado docs/FEATURES.md — feature X completa

- Adicionado F-15 status ready
- Atualizado README.md links
- Sincronizado SYNCHRONIZATION.md

Referência: docs/FEATURES.md, CHANGELOG.md
Affected: docs/STATUS_ATUAL.md
```

```
[SYNC] Corrigido reward function em agent/reward.py

- Removido bug em r_pnl (linha 45)
- Adicionado teste test_reward_fix.py
- Atualizado docs/REWARD_FIXES_2026-02-22.md
- Incrementado CHANGELOG.md

Referência: agent/reward.py, docs/FEATURES.md Round 5+
Tested: pytest -q tests/test_reward_*.py → 12/12 PASSING
```

### Exemplos ERRADOS ❌

```
❌ "Atualizar docs"  (muito vago)
❌ "Fix" (sem contexto)
❌ "atualizou documentação e código" (sem [SYNC] tag)
❌ "Synced everything" (qual tudo?)
❌ "docs: Sumário de atualiza├º├úo" (encoding corrompido)
```

---

## 🔍 VALIDAÇÃO AUTOMÁTICA

**Antes de fazer commit, rodar:**

```bash
# Validar sintaxe markdown
markdownlint --fix docs/*.md

# Validar sem erros e sem >80 chars
python scripts/validate_sync.py

# Resultado esperado:
# ✅ LINT: OK
# ✅ FEATURES: sincronizado
# ✅ ROADMAP: sincronizado
# ✅ CHANGELOG: atualizado
# ✅ SYNCHRONIZATION: audit OK
# → PRONTO PARA COMMIT
```

---

## ⚡ EXEMPLO: MUDANÇA TÍPICA

### Cenário: "Implementar nova feature F-X"

**PASSO 1: Código**
```python
# agent/feature_x.py
def new_feature():
    """Implementação de feature X."""
    return True

# tests/test_feature_x.py
def test_feature_x():
    assert new_feature() == True  # ✅
```

**PASSO 2: Documentação**

1️⃣ Atualizar `docs/FEATURES.md`:
```markdown
| F-X | Descrição | 🔴 CRÍTICA | ✅ DONE (22/02) |
```

2️⃣ Atualizar `docs/STATUS_ATUAL.md`:
```markdown
**Atualizado:** 22 FEV 2026 15:30  
...
## Features Recentes
- [22/FEV] F-X implementado → docs/FEATURES.md
```

3️⃣ Atualizar `CHANGELOG.md`:
```markdown
## [Unreleased]
- Feature F-X implementada (22/02/2026)
```

4️⃣ Atualizar `docs/SYNCHRONIZATION.md`:
```markdown
### Feature F-X (22 FEV 15:30 UTC)
- Implementado: agent/feature_x.py (50L)
- Testado: test_feature_x.py (12L, 1/1 PASSING)
- Sincronizado: docs/FEATURES.md, STATUS_ATUAL.md, CHANGELOG.md
```

**PASSO 3: Commit**
```bash
git add agent/feature_x.py tests/test_feature_x.py \
        docs/FEATURES.md docs/STATUS_ATUAL.md \
        docs/SYNCHRONIZATION.md CHANGELOG.md

git commit -m "[SYNC] Implementado feature F-X com testes

- agent/feature_x.py (50 linhas, novo)
- tests/test_feature_x.py (12 linhas, novo)
- Teste: 1/1 PASSING ✅

Sincronizado:
- docs/FEATURES.md (linha 42)
- docs/STATUS_ATUAL.md (timestamp 15:30)
- docs/SYNCHRONIZATION.md (audit trail)
- CHANGELOG.md (versão unreleased)

Referência: docs/DECISIONS.md #1 (protocolo [SYNC])"
```

**PASSO 4: Push**
```bash
git push origin main
```

---

## 🚨 REGRAS NÃO-NEGOCIÁVEIS

1. ✅ **Código + Doc sincronizam SEMPRE**
   - Sem exceção
   - Sem "vou documentar depois"
   - Sem código orphan

2. ✅ **[SYNC] tag em TODO commit que altere docs**
   - Parserável para auditar
   - Rastreável em git log

3. ✅ **Markdown lint sempre**
   - Max 80 chars/linha
   - UTF-8 correto
   - Português consistente

4. ✅ **Sem duplicação de conteúdo**
   - Um documento oficial por tópico
   - Links, não cópias
   - README.md aponta para /docs/

5. ✅ **Testes + Docs obrigatórios**
   - Feature → Teste + Doc
   - Fix → Teste + Doc
   - Sem exceção

---

## 📞 DÚVIDAS?

Se não sabe se precisa sincronizar documentação:

**Teste com 3 perguntas:**
1. AlteREI código ou config? → **SIM** = sync docs
2. Pode afetar comportamento do sistema? → **SIM** = sync docs
3. Impacta decisão de Investidor/Risk? → **SIM** = sync docs

Se qualquer resposta for SIM → **SYNC docs obrigatório**

---

**Válido até:** Próxima revisão (23 FEV reunião)  
**Aprovado por:** Board Decision #1  
**Implementado:** 22 FEV 2026  
**Status:** ✅ ATIVO
