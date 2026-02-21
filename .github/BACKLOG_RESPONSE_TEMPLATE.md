# 🎯 TEMPLATE DE RESPOSTA PADRÃO — BACKLOG QUERIES

**Quando copilot receber:** "backlog", "prioridades", "tarefas", "sprint backlog", etc.

**Copilot responde com este template (atualizar dados dinamicamente):**

---

# 🎯 BACKLOG PRIORIZADO ATUAL

**Última atualização:** [DATA — Ler de TASKS_TRACKER_REALTIME.md]
**Status geral:** [GREEN/YELLOW/RED — Ler de TASKS_TRACKER_REALTIME.md]
**Critical path:** [STATUS do item mais crítico]
**Próximo checkpoint:** [DATA e HORA do gate crítico]

---

## 🔴 SPRINT 1: MUST ITEMS (21-25 FEV) — BLOQUEADORES CRÍTICOS

**7 tasks sequenciais + 1 paralelo = Timeline crítica 14h manual + 96h paralelo**

| # | Task | Owner | Timeline | Status | % Done | Gate |
|---|------|-------|----------|--------|--------|------|
| [Preencher com dados atuais de TASKS_TRACKER_REALTIME.md] |

### Quick Status:
- **TASK-001:** Heurísticas Dev [STATUS] — Owner: Dev
- **TASK-002:** QA Testing [STATUS] — Owner: Audit(QA)
- **TASK-003:** Alpha Validation [STATUS] — Owner: Alpha
- **TASK-004:** Go-Live Canary [STATUS] — Owner: Dev
- **TASK-005:** PPO Training [STATUS] — Owner: The Brain (PARALLEL)
- **TASK-006:** PPO Quality Gate [STATUS] — Owner: Audit(QA)
- **TASK-007:** PPO Merge Live [STATUS] — Owner: Dev

---

## 🟠 SPRINT 2: SHOULD ITEMS (26-27 FEV) — IMPORTANTES

**4 tasks dependentes (Decision #3 & #4)**

| # | Task | Owner | Timeline | Status | Depende de |
|---|------|-------|----------|--------|-----------|
| [Preencher com dados atuais de TASKS_TRACKER_REALTIME.md] |

### Quick Status:
- **TASK-008:** Decision #3 Vote [STATUS] — Owner: Angel | Depende: TASK-1.7
- **TASK-009:** Decision #3 Impl [STATUS] — Owner: Dr.Risk | Depende: TASK-008
- **TASK-010:** Decision #4 Vote [STATUS] — Owner: Angel | Depende: TASK-009
- **TASK-011:** F-12b Expansion [STATUS] — Owner: Flux | Depende: TASK-010

---

## 🟡 SPRINT 3+: COULD ITEMS (Semana 2+) — NICE-TO-HAVE

**3 items backlog futuro (não bloqueador)**

| # | Task | Owner | Timeline | Status |
|---|------|-------|----------|--------|
| [Preencher com dados atuais de TASKS_TRACKER_REALTIME.md] |

---

## 📊 MÉTRICAS SPRINT 1

```
Progress: X% of 7 MUST items completed
├─ Completed: [n tasks]
├─ In Progress: [n tasks]
└─ Not Started: [n tasks]

Bloqueadores: [Y items] (if any)
├─ [Listar bloqueadores identificados]
└─ ETA resolução: [when]

Timeline Status:
├─ On track ✅ / At risk ⚠️ / CRITICAL 🔴
└─ Próximo gate: [Data hora] (TASK #X)

Velocity:
├─ Target: X LOC/h (dev), Y hours (QA)
├─ Actual: [dados atuais]
└─ Health: 📊 [GREEN/YELLOW/RED]
```

---

## 🔗 DOCUMENTAÇÃO REFERENCIADA

**Para detalhes completos:**
- 📄 **Sprint backlog maestro:** `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`
- 📊 **Tracker real-time:** `backlog/TASKS_TRACKER_REALTIME.md`
- 🚀 **Quick reference:** `backlog/BACKLOG_QUICK_START.md`
- 📋 **Índice prioridades:** `.github/PRIORITY_INDEX.md`

**Documentação relacionada:**
- 📅 **Timeline:** `docs/CHRONOGRAM.md`
- 🗺️ **Roadmap:** `docs/ROADMAP.md`
- 🎯 **Decisões:** `docs/DECISIONS.md`

---

## ❓ COMO POSSO AJUDAR?

Escolha uma das opções abaixo ou tipo livremente:

- [ ] **"Detalhes de TASK-XXX"** — Vou retornar info completa
- [ ] **"Quero implementar TASK-XXX, me ajuda"** — Code templates + guide
- [ ] **"Qual é o próximo item?"** — Próxima task não-iniciada
- [ ] **"Estamos blocados em TASK-XXX"** — Análise de impacto + alternativas
- [ ] **"Qual é o status agora?"** — Resumo de progresso + métricas
- [ ] **"Timeline de implementação?"** — Gantt visual + milestone dates
- [ ] **"Qual é o roadmap?"** — v0.4 → v1.0 features
- [ ] **Outro (descreva)** → Ajudarei conforme necessário

---

## 🔄 COMO ESTE TEMPLATE FUNCIONA

1. **Copilot recebe query:** "backlog", "prioridades", "tarefas", etc.
2. **Copilot lê arquivo maestro:** `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`
3. **Copilot consulta tracker:** `backlog/TASKS_TRACKER_REALTIME.md` (status atual)
4. **Copilot preenche template:** Com dados FRESCOS (datatime = now)
5. **Copilot responde:** Com este template (seções acima)
6. **Copilot oferece:** Próxima ação ("Como posso ajudar?")

---

## ✅ INSTRUÇÕES PARA PREENCHIMENTO

**Campos dinâmicos (ler de arquivo):**

```
[DATA] → Ler: backlog/TASKS_TRACKER_REALTIME.md
        Procure: "Last Updated:" ou "Atualizado:"

[STATUS] → Ler: TASKS_TRACKER_REALTIME.md tabela "Status"
          Valores: NOT STARTED / IN PROGRESS / COMPLETED / WAITING / SCHEDULED

[% DONE] → Ler: TASKS_TRACKER_REALTIME.md coluna "% Done"

[STATUS GERAL] → Derivar de: todos status acima
                 GREEN se >75% tarefas no track
                 YELLOW se 50-75% ou alguma em risco
                 RED se <50% ou crítico blockeado

[GATES] → Ler: SPRINT_BACKLOG_21FEV... section "Critical Gates"
         Próximo = primeira data que ainda não passou

[MÉTRICAS] → Ler: TASKS_TRACKER_REALTIME.md seção "Métricas"
            LOC/h, test pass rate, latency, etc.

[BLOQUEADORES] → Ler: coluna "Blocker" da tabela status
                 Se vazio = nenhum bloqueador
                 Se preenchido = listar
```

---

## 🚀 TESTE AGORA

**Para validar que funciona:**

```
Copilot: "backlog priorizado atual"

[Copilot deve responder com template acima, preenchido com dados FRESCOS]
```

---

## 📞 TROUBLESHOOTING

**If Copilot pode't find file:**
```
ERROR: Formato esperado: backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
SOLUÇÃO: Confirmar arquivo existe em workspace root
```

**If dados outdated:**
```
WARNING: Tracker desatualizado (> 24h)
AÇÃO: Contactar Planner para sincronização
```

**If usuário pede TASK non-existent:**
```
RESPOSTA: "TASK-XXX não encontrada. Tarefas válidas: TASK-001 a 011"
LINK: "Veja lista completa em: backlog/SPRINT_BACKLOG_..."
```

---

## 🎯 PRÓXIMA AÇÃO

1. **Copilot memoriza este template**
2. **Usuário digita:** "backlog"
3. **Copilot responde AUTOMÁTICO** com este formato + dados frescos

✅ **Pronto para execução**

---

**Versão:** 1.0
**Status:** ✅ ATIVO
**Última revisão:** 21 FEV 2026
**Manutenido por:** Planner + Audit (Doc Advocate)
