# 📦 BACKLOG SYSTEM — README

**Status:** ✅ OPERACIONAL
**Data:** 21 FEV 2026
**Responsável:** Planner (Gerente Projetos)

---

## 🎯 O QUE É ESTE DIRETÓRIO

Centralização de **backlog priorizado, rastreamento de tasks, e cronograma executivo** para o projeto crypto-futures-agent.

Qualquer person que entre via chat e pedir "backlog" ou "prioridades", o Copilot automaticamente:
1. Lê os arquivos deste diretório
2. Retorna status ATUAL
3. Oferece ajuda específica

---

## 📁 ARQUIVOS E PROPÓSITO

| Arquivo | Propósito | Para quem | Atualizado |
|---------|----------|----------|-----------|
| **SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md** | Maestro completo: todos tasks, detalhes, timelines | Tech leads, owners | 21 FEV |
| **TASKS_TRACKER_REALTIME.md** | Status em tempo real: tabelas, standup templates | Planner, QA, team | Daily 20:00 UTC |
| **BACKLOG_QUICK_START.md** | Referência visual rápida para roles específicos | Dev, product, stakeholders | 21 FEV |
| **CHANGE_LOG.txt** | Histórico de mudanças no backlog | Audit, compliance | Daily |

---

## 🚀 QUICK START: 3 FORMAS DE USAR

### **1️⃣ Chat Copilot (Mais comum)**

```
você: "quero ver o backlog"

copilot: [Lê TASKS_TRACKER_REALTIME.md]
         [Lê SPRINT_BACKLOG_21FEV...]
         [Responde com formato padrão]
```

**Como funciona:** Copilot tem instrução embutida (`.github/copilot-backlog-instructions.md`) que diz:
- Quando usuário menciona "backlog/prioridades/sprint"
- Leia arquivo MAESTRO desta pasta
- Responda com template padrão
- Ofereça detalhes de task específica

### **2️⃣ Acesso direto (Dev implementando)**

```
você: "preciso de ajuda em TASK-001"

copilot: [Lê backlog/SPRINT_BACKLOG_21FEV.md seção #1.1)
         [Retorna: Escopo, Criteria, Timeline, Blocker)
         [Oferece: Code template, teste guide, git format)
```

### **3️⃣ Daily Standup (Planner coordenando)**

```
planner: "status de todas as tasks"

copilot: [Lê TASKS_TRACKER_REALTIME.md]
         [Mostra tabela com % done, blocker, próximas ações]
         [Alerta se algo está RED]
```

---

## 🔄 SINCRONIZAÇÃO: Como funciona diariamente

**@ 20:00 UTC cada dia:**

1. **Planner atualiza:** `TASKS_TRACKER_REALTIME.md`
   - Coleta status de cada owner
   - Atualiza % done
   - Registra novos bloqueadores
   - Marca gates passados

2. **Adiciona:** `CHANGE_LOG.txt`
   ```
   21 FEV 22:30 - SPRINT_BACKLOG created, 7 MUST + 4 SHOULD items
   21 FEV 22:45 - TASKS_TRACKER initialized, status NOT_STARTED
   22 FEV 08:00 - TASK-001 advanced to 100%, TASK-002 started
   ...
   ```

3. **Git commit:**
   ```bash
   git commit -am "[SYNC] Backlog status update — tasks X% as of 20:00 UTC"
   ```

4. **Copilot encontra:**
   - Next chat que usuário pedir "backlog"
   - Copilot lê arquivo FRESCO
   - Retorna status ATUAL (não cached)

---

## 🎯 INTEGRAÇÃO COM COPILOT: 4 Arquivos Espelhados

Quando você cria/atualiza algo em `backlog/`, o Copilot o encontra via:

**`.github/copilot-instructions.md`**
- Instrução principal (atualizada 21 FEV)
- Referencia: "Se usuário pedir backlog → leia copilot-backlog-instructions.md"

**`.github/copilot-backlog-instructions.md`** ← NOVO
- Protocolo específico de backlog
- Quando copilot recebe query tipo "backlog/prioridades"
- Como montar resposta
- Qual arquivo é o maestro
- Quando sincronizar

**`.github/PRIORITY_INDEX.md`** ← NOVO
- Índice rápido de arquivos
- "Se usuario pedir XXX, vá para arquivo YYZ"
- Mapping de trigger keywords

**`.github/BACKLOG_RESPONSE_TEMPLATE.md`** ← NOVO
- Template que Copilot preenche dinamicamente
- Formato padrão de resposta
- Instruções de preenchimento (quais campos ler de onde)

---

## 🔴 ESTRUTURA: 7+4+3 Tasks

### **🔴 SPRINT 1 (7 MUST): 21-25 FEV**

Bloqueadores críticos para operacionalizar sistema:

1. **TASK-001** — Heurísticas Dev (Dev, 6h)
2. **TASK-002** — QA Testing (QA, 2h) [Gate #1]
3. **TASK-003** — Alpha Validation (Alpha, 2h) [Gate #2]
4. **TASK-004** — Go-Live Canary (Dev, 4h) [Gate #3 / GO-LIVE]
5. **TASK-005** — PPO Training (Brain, 96h PARALLEL)
6. **TASK-006** — PPO Quality Gate (QA, 4h) [Gate #5]
7. **TASK-007** — PPO Merge Live (Dev, 6h) [Gate #6 / GO-LIVE PPO]

**Critical Path:** 14h + 96h parallel → Fim 25 FEV 20:00 UTC

### **🟠 SPRINT 2 (4 SHOULD): 26-27 FEV**

Importantes, não-bloqueadores:

8. **TASK-008** — Decision #3 Vote (Angel, 2h)
9. **TASK-009** — Decision #3 Implementation (Risk, 7h)
10. **TASK-010** — Decision #4 Vote (Angel, 2h)
11. **TASK-011** — F-12b Expansion (Flux, 9h)

**Depende de:** SPRINT 1 completo

### **🟡 SPRINT 3+ (3 COULD): Week 2+**

Backlog futuro:

12. **TASK-012** — A2C/A3C Research (Brain)
13. **TASK-013** — Advanced Hedging (Risk)
14. **TASK-014** — Dashboard Advanced (Vision)

**Status:** Não iniciado, priorizado quando Sprint 1-2 OK

---

## 📊 EXEMPLOS DE QUERY & RESPOSTA

### **Query 1: "Backlog"**

```
usuário: "Qual é o backlog atual?"

copilot lê TASKS_TRACKER_REALTIME.md
copilot retorna:

🎯 BACKLOG PRIORIZADO ATUAL
Última atualização: 21 FEV 22:45 UTC
Status geral: 🟢 GREEN (on track)

🔴 MUST ITEMS (Sprint 1: 21-25 FEV)
| # | Task | Owner | Timeline | Status | % |
|---|------|-------|----------|--------|---|
|1.1|Heurísticas|Dev |21 23:00→22 06:00|🔴 STARTED|0%|
|1.2|QA Testing |QA |22 06:00→08:00  |⏳ WAITING|0%|
...

📊 MÉTRICAS
Progress: 0% of 7 MUST items
...

❓ COMO POSSO AJUDAR?
- "Detalhes de TASK-001"
- "Próximo item?"
- etc.
```

### **Query 2: "Detalhes de TASK-001"**

```
usuário: "Quero detalhes da TASK-001"

copilot lê SPRINT_BACKLOG_21FEV... seção #1.1
copilot retorna:

**TASK-001: Implementar Heurísticas Conservadoras**

Owner: Dev (The Implementer)
Timeline: 21 FEV 23:00 → 22 FEV 06:00 (6h)
Estimativa: 6 horas

Entregáveis:
├─ execution/heuristic_signals.py (250 LOC)
├─ SMC validation logic
├─ Risk gates (max DD 5%, circuit -3%)
├─ Logging & audit trail
└─ 100% test coverage

Acceptance Criteria:
├─ 9/9 unit tests passing
├─ Code review approved
├─ Edge cases tested (5 scenarios)
└─ Audit trail configured

Bloqueador: Nenhum
Risco: Threshold agressivo → false positives
Mitigação: Alpha valida simulação 1h

❓ COMO POSSO AJUDAR?
- "Preciso implementar isto, me ajuda com code"
- "Qual é o edge cases?"
- "Git format para commit?"
- "Tempo remainning/ETA?"
```

### **Query 3: "Vou fazer TASK-001, me ajuda"**

```
usuário: "Vou fazer TASK-001, me ajuda"

copilot oferece:
├─ Code template (heurísticas scaffold)
├─ Unit test template
├─ SMC reference documentation
├─ Git workflow:
│  ├─ Branch: feature/TASK-001-heuristics
│  ├─ Commit: "[TASK-001] Add SMC order block detection"
│  └─ PR: Link to sprint backlog TASK-001
├─ Timeline reminder
├─ Link ao gate #1 (QA testing requirements)
└─ Link ao próximo TASK (TASK-002 - expects input)
```

---

## ✅ VALIDAÇÃO & HEALTH CHECKS

**Como confirmar que sistema está funcionando:**

```bash
# 1. Confirmar arquivos existem
ls -la backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
ls -la backlog/TASKS_TRACKER_REALTIME.md
ls -la .github/copilot-backlog-instructions.md

# 2. Testar Copilot
# (no chat)
"backlog"
# → Copilot responde com taexbl status + link a arquivo

# 3. Verificar sincronização
git log --oneline | grep "\[SYNC\]"
# → Deve ter commits [SYNC] diários
```

---

## 📞 TROUBLESHOOTING

| Problema | Solução |
|----------|---------|
| Copilot não encontra backlog | Confirme `.github/copilot-backlog-instructions.md` existe |
| Status outdated | Planner deve executar sync @ 20:00 UTC |
| Git log "message not found" | Use: `git log --all --grep="SYNC"` |
| Arquivo "not in workspace" | Confirme path em `.github/PRIORITY_INDEX.md` |

---

## 🎯 PRÓXIMAS AÇÕES

1. ✅ **Backlog criado** (3 arquivos maestros)
2. ✅ **Copilot instruções criadas** (4 arquivos `.github/`)
3. ✅ **Sync protocol ativo** (daily @ 20:00 UTC)
4. 🔄 **Dev inicia TASK-001** (21 FEV 23:00 UTC — AGORA)
5. 📅 **Daily standup** (22 FEV 08:00 UTC onwards)

---

## 📖 REFERÊNCIAS RÁPIDAS

- **Sprint backlog maestro:** [SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md](./SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md)
- **Tracker real-time:** [TASKS_TRACKER_REALTIME.md](./TASKS_TRACKER_REALTIME.md)
- **Quick start:** [BACKLOG_QUICK_START.md](./BACKLOG_QUICK_START.md)
- **Copilot instructions:** [../../.github/copilot-backlog-instructions.md](../.github/copilot-backlog-instructions.md)
- **Priority index:** [../../.github/PRIORITY_INDEX.md](../.github/PRIORITY_INDEX.md)
- **Response template:** [../../.github/BACKLOG_RESPONSE_TEMPLATE.md](../.github/BACKLOG_RESPONSE_TEMPLATE.md)

---

**Status:** ✅ SISTEMA OPERACIONAL
**Última atualização:** 21 FEV 2026 22:50 UTC
**Próxima sincronização:** 21 FEV 23:00 UTC (quando Dev inicia TASK-001)
