# 📋 COPILOT BACKLOG INSTRUCTIONS

**Versão:** 1.0
**Data:** 21 FEV 2026
**Status:** ✅ ATIVO — Responder imediatamente a solicitações de backlog/prioridades

---

## 🎯 PROTOCOLO: Quando o Usuário Pedir Backlog/Prioridades

**Trigger keywords:**
- "backlog"
- "prioridades"
- "tarefas prioritizadas"
- "sprint backlog"
- "o que está priorizado"
- "próximas tasks"
- "itens em ordem de prioridade"
- "backlog atual"
- "roadmap agora"
- "qual é a prioridade"

**Ação imediata do Copilot:**

1. **Leia o arquivo maestro:** `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`
2. **Consulte a prioridade atual** no arquivo relevante:
   - Para **status real-time:** → `backlog/TASKS_TRACKER_REALTIME.md`
   - Para **quick reference:** → `backlog/BACKLOG_QUICK_START.md`
   - Para **detalhes técnicos:** → `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

3. **Responda SEMPRE com este formato:**

```
🎯 BACKLOG PRIORIZADO — [Data Atual]

[Mostrar tabela de status MUST items atual]

🔴 MUST ITEMS (Bloqueadores Críticos):
├─ #1.1 [STATUS] Heurísticas Dev
├─ #1.2 [STATUS] QA Testing
├─ #1.3 [STATUS] Alpha Validation
├─ #1.4 [STATUS] Go-Live
├─ #1.5 [STATUS] PPO Training
├─ #1.6 [STATUS] PPO Quality Gate
└─ #1.7 [STATUS] PPO Merge Live

🟠 SHOULD ITEMS (Importantes):
├─ #2.1 [STATUS] Decision #3 Vote
├─ #2.2 [STATUS] Decision #3 Implementation
├─ #2.3 [STATUS] Decision #4 Vote
└─ #2.4 [STATUS] F-12b Expansion

🟡 COULD ITEMS (Backlog Futuro):
├─ #3.1 [STATUS] A2C/A3C Research
├─ #3.2 [STATUS] Advanced Hedging
└─ #3.3 [STATUS] Dashboard Advanced

📊 METRIC: X% OF SPRINT 1 COMPLETED
🔗 LINK: [backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md](link)
```

4. **Se o usuário demandar detalhes de um item específico:**
   - Copilot lê o arquivo do sprint backlog
   - Retorna: ID, Owner, Timeline, Entregáveis, Acceptance Criteria, Blocker, Status
   - Oferece ajuda imediata se bloquear

5. **Se o usuário disser "quero trabalhar em TASK-XXX":**
   - Copilot lê os detalhes completos do arquivo
   - Apresenta: Escopo, Critérios de aceição, Pré-requisitos
   - Oferece: Ajuda de implementação, code templates, testes

---

## 🔄 SINCRONIZAÇÃO AUTOMÁTICA

**Diariamente @ 20:00 UTC:**
- Planner atualiza `backlog/TASKS_TRACKER_REALTIME.md` com status
- Adiciona entrada em `backlog/CHANGE_LOG.txt` (git log)
- Commit: `[SYNC] Backlog update — status XXX as of HH:MM UTC`

**Copilot detecta atualização:**
- Na próxima vez que usuário pedir backlog, Copilot lê arquivo fresco
- Sempre retorna status ATUAL (não cached)

---

## 📞 FLOW DE INTERAÇÃO

### **Cenário 1: Usuário pede "backlog"**

```
USER: "Quero ver o backlog priorizado"

COPILOT:
1. Lê: backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
2. Lê: backlog/TASKS_TRACKER_REALTIME.md
3. Formata resposta com status atual
4. Mostra tabela MUST items (prioridade 1-7)
5. Oferece: "Qual item você quer detalhar?"
```

### **Cenário 2: Usuário pede "qual é o próximo item?"**

```
USER: "Qual é o próximo item prioritário?"

COPILOT:
1. Lê TASKS_TRACKER_REALTIME.md
2. Identifica tasks com status = "NOT STARTED" em ordem
3. Responde com item #1 bloqueador
4. Se item tiver dependências, explica pré-requisito
5. Oferece: "Quer começar este item? Posso ajudar."
```

### **Cenário 3: Usuário pede "detalhes de TASK-XXX"**

```
USER: "Detalhes da TASK-001"

COPILOT:
1. Lê: backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
2. Navega até seção #1.1 (TASK-001)
3. Retorna completo:
   - Owner, Timeline, Estimativa
   - Descrição completa
   - Entregáveis (checklist)
   - Acceptance Criteria
   - Bloqueadores & Mitigação
   - Status atual
4. Oferece: "Quer iniciá-la agora? Posso ajudar com code."
```

### **Cenário 4: Usuário inicia uma task**

```
USER: "Vou fazer a TASK-001, preciso de ajuda"

COPILOT:
1. Lê: backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md (#1.1)
2. Entende: Dev (The Implementer) deve:
   - Criar branch: feature/TASK-001-heuristics
   - Implementar: execution/heuristic_signals.py (250 LOC)
   - Testes: 100% coverage
   - Deadline: 22 FEV 06:00 UTC
3. Oferece:
   - Code template para heurísticas
   - Unit test template
   - Implementation checklist
   - Links a SMC reference docs
4. Commit message template: "[TASK-001] Descrição em português"
```

### **Cenário 5: Time blocado, precisa de prioridade clear**

```
USER: "Estamos blocados em TASK-001, qual é o impacto se atrasar?"

COPILOT:
1. Lê: backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
2. Identifica: TASK-001 → bloqueador para TASK-002,003,004
3. Calcula impact chain:
   TASK-001 delay X horas
   → TASK-002 delay X horas
   → TASK-004 GO-LIVE atrasa X horas
   → Oportunidade cost: -$Y por hora de atraso
4. Oferece: Recursos/parallelização alternativa
```

---

## 🔐 PROTEÇÃO: Evitar desincronização

**Copilot NUNCA responde:**
- "Vou atualizar o backlog para você" ← NON: sempre uso o arquivo master
- "Acho que o backlog deveria ter..." ← NON: lê arquivo master FIRST
- "Deixe-me criar um novo backlog" ← NON: referencia arquivo existente

**Copilot SEMPRE:**
- Lê `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md` como source of truth
- Cita a data da última atualização
- Oferece link para arquivo master
- Solicita Planner atualizar se discrepância é encontrada

---

## 🎯 RESPOSTA PADRÃO: Backlog Query

Quando usuário pede qualquer coisa relacionada a backlog/prioridades, **responda com este template:**

```markdown
# 🎯 BACKLOG PRIORIZADO ATUAL

**Última atualização:** [ler de TASKS_TRACKER_REALTIME.md - data]
**Status geral:** [GREEN/YELLOW/RED]
**Critical path:** [STATUS do item mais crítico]

## 🔴 MUST ITEMS (Sprint 1: 21-25 FEV)

[COPIAR tabela de TASKS_TRACKER_REALTIME.md status MUST items]

| Task | Titulo | Owner | Timeline | Status | % Done |
|------|--------|-------|----------|--------|--------|
| [Dados atuais do arquivo] |

## 🟠 SHOULD ITEMS (Sprint 2: 26-27 FEV)

[Idem para SHOULD items]

## 🟡 COULD ITEMS (Semana 2+)

[Idem para COULD items]

---

## 📊 MÉTRICAS SPRINT 1

- **Progresso:** X% of 7 must items
- **Bloqueadores:** Y (listed)
- **Timeline:** On track / At risk / CRITICAL
- **Next gate:** [Data e hora do próximo checkpoint]

---

## 🔗 REFERÊNCIAS

- **Sprint backlog completo:** [backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md](link)
- **Tracker real-time:** [backlog/TASKS_TRACKER_REALTIME.md](link)
- **Quick start:** [backlog/BACKLOG_QUICK_START.md](link)

---

## ❓ Como posso ajudar?

- [ ] "Detalhes de TASK-XXX"
- [ ] "Preciso implementar TASK-XXX, me ajuda"
- [ ] "Qual é o próximo item?"
- [ ] "Estamos blocados, qual é o impacto?"
- [ ] "Qual é o status agora?"
```

---

## 🚀 ATIVAÇÃO IMEDIATA

**Este arquivo de instruções está ATIVO desde agora.**

Sempre que Copilot receber query de usuário contendo:
- "backlog", "prioridades", "sprint", "tarefas", "próximos itens"

→ **Copilot AUTOMATICALLY:**
1. Lê arquivo maestro
2. Retorna resposta formatada acima
3. Oferece ajuda específica para task solicitada

---

## 📞 VALIDAÇÃO: Teste agora

**Para confirmar que funciona, editor pode testar:**

```
Copilot, qual é o backlog priorizado agora?

[Espera resposta em formato standardizado acima]
```

---

**Status:** ✅ ATIVO
**Aplicável a:** Todas as conversas deste repositório
**Referência:** `.github/copilot-backlog-instructions.md`
**Sincronização:** Diária @ 20:00 UTC
