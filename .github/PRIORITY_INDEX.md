# 📍 ÍNDICE DE PRIORIDADES — ACESSO RÁPIDO

**Atualizado:** 21 FEV 2026
**Para:** GitHub Copilot + Team
**Propósito:** Localizar rapidamente documentação de prioridades

---

## 🎯 SE O USUÁRIO PEDIR...

### **"Backlog"**
→ Responda com: `backlog/TASKS_TRACKER_REALTIME.md` (status tabular)
→ Aprofunde com: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

### **"Prioridades"**
→ Responda com: `backlog/BACKLOG_QUICK_START.md` (visual rápido)
→ Details para tarefas específicas em: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md`

### **"Sprint backlog" ou "Detalhes de TASK-XXX"**
→ Direto para: `backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md` (buscar seção)

### **"Qual é o próximo item?"**
→ Consulte: `backlog/TASKS_TRACKER_REALTIME.md` (procure status = "NOT STARTED")
→ Se bloqueado, consulte campo "Blocker"

### **"Status da sprint"**
→ Responda com: `backlog/TASKS_TRACKER_REALTIME.md` (tabela status + métricas)

### **"Cronograma de implementação"**
→ Mostre: `backlog/BACKLOG_QUICK_START.md` (visual Gantt) ou
→ Detalhado: `docs/CHRONOGRAM.md` (timeline executivo)

### **"Roadmap do projeto"**
→ Leia: `docs/ROADMAP.md` (v0.4 → v1.0 features)

### **"Decisões de board"**
→ Consulte: `docs/DECISIONS.md` (decision registry)
→ Contexto: `ATA_REUNIAO_22FEV_2026.md` (última reunião)

---

## 📂 ESTRUTURA DE ARQUIVOS

```
📦 crypto-futures-agent/
│
├─ 📁 backlog/                           ← MASTER DIRECTORY
│  ├─ 📄 SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md  [MAESTRO]
│  ├─ 📄 TASKS_TRACKER_REALTIME.md       [STATUS ATUAL]
│  ├─ 📄 BACKLOG_QUICK_START.md          [QUICK REFERENCE]
│  └─ 📄 CHANGE_LOG.txt                  [HISTORY]
│
├─ 📁 docs/
│  ├─ 📄 CHRONOGRAM.md                   [Timeline]
│  ├─ 📄 ROADMAP.md                      [Features v0.4→v1.0]
│  ├─ 📄 DECISIONS.md                    [Decision registry]
│  └─ 📄 SYNCHRONIZATION.md              [Sync matrix]
│
├─ 📁 .github/
│  ├─ 📄 copilot-instructions.md         [Instruções copilot]
│  ├─ 📄 copilot-backlog-instructions.md [Backlog protocol]
│  └─ 📄 PRIORITY_INDEX.md               [Este arquivo]
│
└─ 📄 ATA_REUNIAO_22FEV_2026.md          [Última reunião board]
```

---

## 🔴 MUST ITEMS (Bloqueadores) — 21-25 FEV

| # | Task | Owner | Timeline | Crítico? |
|---|------|-------|----------|----------|
| 1.1 | Heurísticas Dev | Dev | 21 23:00→22 06:00 | 🔴 CRÍTICO |
| 1.2 | QA Testing | QA | 22 06:00→08:00 | 🔴 CRÍTICO (gate) |
| 1.3 | Alpha Validation | Alpha | 22 08:00→10:00 | 🔴 CRÍTICO (gate) |
| 1.4 | Go-Live Canary | Dev | 22 10:00→14:00 | 🔴 CRÍTICO (ops) |
| 1.5 | PPO Training | Brain | 22 14:00→25 10:00 | 🔴 CRÍTICO (parallel) |
| 1.6 | PPO Quality Gate | QA | 25 10:00→14:00 | 🔴 CRÍTICO (gate) |
| 1.7 | PPO Merge Live | Dev | 25 14:00→20:00 | 🔴 CRÍTICO (ops) |

**Se usuário pergunta "qual é a tarefa mais urgente?"**
→ Responda: TASK-001 (Heurísticas) iniciam **AGORA** (21 FEV 23:00)

---

## 🟠 SHOULD ITEMS (Importantes) — 26-27 FEV

| # | Task | Owner | Timeline | Depende de? |
|---|------|-------|----------|-------------|
| 2.1 | Decision #3 Vote | Angel | 26 09:00→11:00 | TASK-1.7 OK |
| 2.2 | Decision #3 Impl | Risk | 26 11:00→18:00 | TASK-2.1 |
| 2.3 | Decision #4 Vote | Angel | 27 09:00→11:00 | TASK-2.2 OK |
| 2.4 | F-12b Expansion | Flux | 27 11:00→20:00 | TASK-2.3 |

**Se usuário pergunta próximo item após TASK-1.7**
→ Responda: TASK-008 (Decision #3) @ 26 FEV 09:00

---

## 🟡 COULD ITEMS (Backlog) — Semana 2+

| # | Task | Owner | Timeline | Status |
|---|------|-------|----------|--------|
| 3.1 | A2C/A3C Research | Brain | Week 2+ | 📦 Backlog |
| 3.2 | Advanced Hedging | Risk | Week 2+ | 📦 Backlog |
| 3.3 | Dashboard Advanced | Vision | Week 2+ | 📦 Backlog |

---

## ⏰ GATES CRÍTICOS (Go/No-Go)

**Se usuário pergunte "quando é a próxima decisão crítica?"**

| Gate | Data | Hora | Owner | Critério |
|------|------|------|-------|----------|
| #1 QA | 22 FEV | 08:00 | Audit | 9/9 tests |
| #2 Trading | 22 FEV | 10:00 | Alpha | SMC OK |
| #3 Operations | 22 FEV | 14:00 | Planner | Canary health |
| #4 PPO Conv | 25 FEV | 10:00 | Brain | Sharpe >1.0 |
| #5 PPO QA | 25 FEV | 14:00 | QA | OOT valid |
| #6 PPO Ops | 25 FEV | 20:00 | Dev | Merge OK |

---

## 💼 ROLES & RESPONSABILIDADES

**Se usuário pedir "quem faz XXX?"**

| Papel | Tasks | Role | Contact |
|-------|-------|------|---------|
| Dev | 1.1, 1.4, 1.7 | Implementação | core engineer |
| Audit (QA) | 1.2, 1.6 | Validação | QA sign-off |
| Alpha | 1.3 | Validação trade | trader approval |
| The Brain | 1.5, 1.6 | ML training | model owner |
| Guardian | Risk gates | Risk management | risk approval |
| Planner | Exec oversight | Project manager | timeline owner |
| Angel | 2.1, 2.3 | Investment approval | final decision |
| Flux | 2.4 | Data arch | scaling owner |

---

## 📞 QUANDO COPILOT NÃO ENCONTRA RESPOSTA

**Se documentação outdated ou confusa:**

1. Assume: `backlog/TASKS_TRACKER_REALTIME.md` é a VERDADE
2. Avisa usuário: "Baseado na última atualização em [data]"
3. Oferece: "Quer que Planner atualize o status?"
4. Escalona: "@Planner: Documentação desatualizada"

---

## ✅ VALIDAÇÃO: Teste este índice

**Copilot, teste seus próprios links:**

```bash
# Verificar que arquivos existem
ls -la backlog/SPRINT_BACKLOG_21FEV_OPERACIONALIZACAO.md
ls -la backlog/TASKS_TRACKER_REALTIME.md
ls -la backlog/BACKLOG_QUICK_START.md
ls -la docs/CHRONOGRAM.md
ls -la docs/ROADMAP.md
```

---

## 🔄 SINCRONIZAÇÃO

**Diariamente @ 20:00 UTC:**
- Planner atualiza: `backlog/TASKS_TRACKER_REALTIME.md`
- Adiciona: `backlog/CHANGE_LOG.txt`
- Git commit: `[SYNC] Backlog status update`

**Copilot:**
- Lê arquivo FRESCO a cada query
- Nunca caches antigos
- Sempre cita data da última atualização

---

## 🚀 PRÓXIMA AÇÃO

**Copilot agora sabe:**
- Onde encontrar prioridades (backlog/ directory)
- Como responder a usuário (formato standardizado)
- Qual é o arquivo maestro (SPRINT_BACKLOG_21FEV...)
- Quando sincronizar (diariamente @ 20:00 UTC)

**Teste agora:**
```
usuário: "Quais são as prioridades agora?"

copilot: [Lê TASKS_TRACKER_REALTIME.md] → Responde com tabela status
```

---

**Status:** ✅ ÍNDICE ATIVO
**Referência:** `.github/PRIORITY_INDEX.md`
**Manutenido por:** Planner
**Última sincronização:** 21 FEV 2026 22:45 UTC
