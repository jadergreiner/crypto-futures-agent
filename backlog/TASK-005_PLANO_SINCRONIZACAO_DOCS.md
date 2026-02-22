# 📚 Plano Mestre Sincronização Documentação — TASK-005

**Responsável:** Doc Advocate
**Data:** 22 FEV 2026
**Status:** 🟢 PRONTO PARA IMPLEMENTAÇÃO
**Prazo:** 25 FEV 20:00 UTC

---

## 🎯 Objetivo

Manter documentação projeto sincronizada com mudanças TASK-005
em tempo real, garantindo:

✅ Audit trail completo de mudanças
✅ Rastreabilidade código ↔ docs
✅ Conformidade markdown lint (80 chars, UTF-8)
✅ Política commit (ASCII, 72 chars, tags [SYNC])
✅ Zero duplicação/inconsistência

---

## 📋 Matriz Dependências Documentação

| Documento | Responsável | Prioridade | Frequência |
|-----------|-------------|-----------|-----------|
| README.md | Doc Advocate | 🔴 CRÍTICA | Diária |
| BEST_PRACTICES.md | SWE Sr + Doc | 🔴 CRÍTICA | Diária |
| SYNCHRONIZATION.md | Doc Advocate | 🔴 CRÍTICA | A cada 2h |
| CHANGELOG.md | Doc Advocate | 🟠 ALTA | Milestones |
| SPRINT_BACKLOG | Planner | 🟠 ALTA | Diária |

---

## 🔄 Fluxo Sincronização

### Fase 0: Pré-Implementação (22 FEV 15:00-22:00)

**Responsável:** Doc Advocate
**Duração:** 7 horas

```
15:00-15:30  Criar plano sincronização
             BRANCH: feature/task-005-ppo-training

15:30-16:00  Configurar .githooks/
             - pre-commit: validador markdown
             - pre-commit: validador tag [SYNC]
             - pre-push: validador UTF-8
             COMMIT: [SYNC] Setup hooks enforcing

16:00-16:30  Criar POLITICA_GOVERNANCA_PHASE4.md
             - Regras enforcement TASK-005
             - Tag [SYNC] obrigatória
             - Formato commit (ASCII, 72 chars)
             COMMIT: [SYNC] Add policy governança

16:30-17:00  Criar matriz sincronização
             - Mapa arquivo código → docs
             - Mapa requisito PR → checklist doc
             COMMIT: [SYNC] Matriz sincronização

17:00-22:00  Integração CI/CD + local hooks
             - Setup markdownlint GitHub Actions
             - Setup docstring checker Python
             COMMIT: [SYNC] Enforce doc sync CI/CD
```

### Fase 1: Implementação (23 FEV 00:00-18:00)

**Responsável:** Doc Advocate + SWE Sr + ML Specialist
**Duração:** 18 horas

**Evento:** SWE Sr cria agent/checkpoint_manager.py

**Ações Doc Advocate:**

1. Atualizar README.md
   └─ Link código + descrição
   └─ COMMIT: [SYNC] Update README checkpoint

2. Atualizar BEST_PRACTICES.md
   └─ Padrões serialização
   └─ Exemplos uso
   └─ COMMIT: [SYNC] Add checkpoint patterns

3. Registrar em SYNCHRONIZATION.md
   └─ Timestamp + owner + status
   └─ COMMIT: [SYNC] Log TASK-005 progress

**Repetir para cada módulo:**
- agent/convergence_monitor.py
- agent/rollback_handler.py
- scripts/ppo_training_orchestrator.py
- tests/*.py (fixtures)

**Monitoramento contínuo (a cada 2h):**
- Atualizar TASKS_TRACKER_REALTIME.md
- Atualizar SYNCHRONIZATION.md
- Validar tags [SYNC] em commits

### Fase 2: Treinamento (23 FEV 14:00 - 25 FEV 10:00)

**Responsável:** Doc Advocate (monitoramento passivo)
**Duração:** 72 horas

**A cada 12h:**
- Atualizar status em TASKS_TRACKER_REALTIME.md
- Passos treinamento
- Estimativa Sharpe ratio
- Drawdown máximo
- COMMIT: [SYNC] Training checkpoint

**Diariamente (08:00 UTC):**
- Relatório standup
- % conclusão vs deadline
- Blockers/rollbacks?
- Novas docs necessárias?

**Checklist diário:**
- [ ] Docs TASK-005 sincronizadas?
- [ ] Commits com tags [SYNC]?
- [ ] Lint markdown passou?
- [ ] Links válidos?

### Fase 3: Finalização (25 FEV 10:00-20:00)

**Responsável:** Doc Advocate + SWE Sr
**Duração:** 10 horas

**10:00-12:00: Code Review**
- Código TASK-005 revisado ✅
- Tags [SYNC] validadas ✅
- Lint markdown passing ✅
- Cross-references verificadas ✅

**12:00-14:00: Audit Completude**

README.md:
- [ ] Lista 4 módulos novos
- [ ] Descrição breve cada um
- [ ] Links para código

BEST_PRACTICES.md:
- [ ] Padrões PPO documentados
- [ ] Exemplos checkpoint
- [ ] Tratamento edge case

CHANGELOG.md:
- [ ] Entrada TASK-005 adicionada
- [ ] Métricas finais incluídas

SYNCHRONIZATION.md:
- [ ] Todos arquivos TASK-005 logados
- [ ] Timestamps auditoria
- [ ] Sign-offs owners completos

**14:00-16:00: Validação Cross-References**
- grep "TASK-005" em docs/
- Verificar links internos
- Nenhuma ref desatualizada
- URLs corretas

**16:00-20:00: Checklist Merge**
- COMMIT: [SYNC] Audit final documentação
- Verificações bloqueadores
- Pronto para merge

---

## 📝 Política Mensagem Commit

### Formato

```
[TAG] Título breve português — arquivos

Exemplos VÁLIDOS:
[SYNC] Update README checkpoint — README.md
[FEAT] Implement monitoring — 3 files

Exemplos INVÁLIDOS:
❌ Updated documentation
❌ [SYNC] Very long message that exceeds 72 characters limit
❌ Fix typo README
```

### Tags Obrigatórias

- [SYNC] = Sincronização docs
- [FEAT] = Feature nova
- [FIX]  = Bug fix
- [TEST] = Testes
- [DOCS] = Apenas docs

### Regras Validação (Git Hooks)

```bash
Validar em pre-commit:
  - Mensagem contém [SYNC]/[FEAT]/[FIX]?
  - Comprimento ≤ 72 chars?
  - ASCII-only (sem ç, ã, é, ó)?

Validar em pre-push:
  - Arquivos .md passam lint?
  - Encoding UTF-8?
  - Sem trailing spaces?
```

---

## ✅ Checklist Diário Doc Advocate

**Tempo:** 08:00 UTC (após standup)
**Duração:** 30 minutos
**Relatório:** Canal #docs-governance

### Auditar

```markdown
## Audit Sincronização Doc — TASK-005

**Data:** [DATA] 2026
**Status:** ✅ PASS / 🔴 FAIL

### 1. Sincronização Código ↔ Docs

- [ ] README.md lista checkpoint_manager?
- [ ] README.md lista convergence_monitor?
- [ ] README.md lista rollback_handler?
- [ ] README.md lista ppo_orchestrator?
- [ ] Todos links válidos?

- [ ] BEST_PRACTICES.md: section checkpoint?
- [ ] BEST_PRACTICES.md: examples sincronizados?
- [ ] BEST_PRACTICES.md: section monitor?
- [ ] BEST_PRACTICES.md: section rollback?

### 2. Validação Mensagem Commit

- [ ] Todos commits TASK-005 têm [SYNC]?
- [ ] Formato [TAG] Desc — arquivos?
- [ ] Zero commits sem [SYNC] em 48h?

Validação comando:
```bash
git log --oneline last48h | \
  grep -v "[SYNC]|[FEAT]|[FIX]" | \
  wc -l
# Deve output: 0
```

### 3. Markdown Lint

- [ ] README.md: 0 lines > 80 chars?
- [ ] BEST_PRACTICES.md: 0 lines > 80?
- [ ] SYNCHRONIZATION.md: 0 lines > 80?
- [ ] Nenhum trailing whitespace?
- [ ] UTF-8 válido todos?

### 4. Cross-References

- [ ] Todos links internos válidos?
- [ ] Nenhum link quebrado?
- [ ] Formato correto [file.md](file.md)?

### 5. Audit Trail

- [ ] SYNCHRONIZATION.md atualizado?
- [ ] CHANGELOG.md reflete TASK-005?
- [ ] TASKS_TRACKER atual (< 2h)?
- [ ] Todos entries têm owner?
- [ ] Timestamps logados?

### 6. Blockers

- [ ] Erros encoding detectados?
- [ ] Links quebrados?
- [ ] Tags [SYNC] faltando?
- [ ] Violações line length?

Status Final: ✅ PASS / 🔴 FAIL

Doc Advocate: _________________
Horário: _________ UTC
```

---

## 🔗 Validação Cross-References

### Comandos Validação

```bash
# Verificar refs TASK-005 válidas
grep -rn "TASK-005" docs/ README.md backlog/ \
  | grep -v ".git"

# Encontrar links quebrados
grep -o "\[.*\](.*\.py)" docs/*.md | \
  while read link; do
    file=$(echo "$link" | grep -o "[^/]*\.py")
    if ! find agent/ -name "$file"; then
      echo "QUEBRADO: $link"
    fi
  done

# Validar markdown lint
markdownlint --config .markdownlint.json \
  README.md docs/ backlog/*.md

# Verificar UTF-8
file -i README.md BEST_PRACTICES.md \
  | grep -v "UTF-8|us-ascii"

# Audit tags [SYNC]
git log --oneline --since="22 FEV" \
  feature/task-005-ppo-training \
  | grep -v "\[SYNC\]" | wc -l
# Deve retornar 0
```

---

## ✅ Critérios Aceição

### Pré-Implementação (22 FEV 22:00)

- ✅ Plano sincronização criado
- ✅ Git hooks instalados + CI/CD
- ✅ Validação commit funcionando
- ✅ Config markdown lint finalizada

### Durante Implementação (23-25 FEV)

- ✅ Audit diário 08:00 UTC completo
- ✅ Zero violações [SYNC] (100%)
- ✅ Lint: 0 errors em TASK-005 docs
- ✅ UTF-8: Válido em todos
- ✅ Cross-refs: 100% válidas

### Pós-Implementação (25 FEV 20:00)

- ✅ SYNCHRONIZATION.md completo logado
- ✅ CHANGELOG.md entry criada
- ✅ README reflete conclusão
- ✅ BEST_PRACTICES atualizado
- ✅ Review aprovado + sign-off
- ✅ Merge ready (todos itens ✅)

---

## 📊 Dashboard Monitoramento

**Arquivo:** `reports/TASK-005_DOC_SYNC_DASHBOARD.csv`

```
Data,Hora,Evento,Responsável,Status,Notas
22FEV,15:00,Branch criado,SWE Sr,DONE,task-005
22FEV,15:30,Hooks setup,Doc,DONE,instalado
22FEV,16:30,Git workflow,Doc,DONE,markdownlint
23FEV,08:00,Audit #1,Doc,✅,todos pass
23FEV,10:00,checkpoint.py,SWE Sr,DONE,README [SYNC]
```

---

## 🔴 Escalação

**Falhas menores** (lint, encoding) → Auto-fix + retest

**Falhas médias** (tag [SYNC]) → Bloquear commit

**Falhas críticas** (cross-refs) → Bloquear PR

**Escalação Angel (se):**
- Matriz impossível em timeline
- Git hooks causa blockers prod
- > 3 inconsistências doc

---

**VERSÃO:** 1.0
**STATUS:** ✅ Pronto implementação
**PRÓXIMO:** Doc Advocate executa FASE 0 (15:00 hoje)
