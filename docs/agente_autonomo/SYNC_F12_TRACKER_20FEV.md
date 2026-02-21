# 📋 SYNCHRONIZATION TRACKER — F-12 Sprint Preparation

**Data**: 20/02/2026 23:45 UTC
**Status**: INICIANDO SINCRONIZAÇÃO
**Tipo**: Post-Sprint F-12 Preparation Documentation Sync

---

## 🔄 MATRIZ DE SINCRONIZAÇÃO OBRIGATÓRIA

Toda mudança em um documento DEVE propagar para todos os documentos correlatos:

```text
DOCUMENTOS IMPACTADOS
═════════════════════════════════════════════════════════════

1. README.md
   ├─ ⚠️ PRECISA UPDATE: Status operacional (v0.3 → v0.4 início)
   ├─ ⚠️ PRECISA UPDATE: Timeline (23 FEV v0.3 → 21-24 FEV v0.4 sprint)
   ├─ ⚠️ PRECISA UPDATE: Seção de governança (novos documentos F-12)
   └─ Correlatos: ROADMAP.md, RELEASE.md, BACKLOG

2. docs/agente_autonomo/AGENTE_AUTONOMO_ROADMAP.md
   ├─ ⚠️ PRECISA UPDATE: Timeline v0.4 (24-28 FEV → 21-24 FEV)
   ├─ ⚠️ PRECISA UPDATE: Milestones F-12a-f (datas e status)
   ├─ ⚠️ PRECISA UPDATE: Features (BacktestEnvironment completo)
   └─ Correlatos: RELEASE.md

3. docs/agente_autonomo/AGENTE_AUTONOMO_RELEASE.md
   ├─ ⚠️ PRECISA UPDATE: v0.4 release date (28 FEV → 23-24 FEV)
   ├─ ⚠️ PRECISA UPDATE: Critérios de aprovação (Sharpe thresholds)
   ├─ ⚠️ PRECISA UPDATE: Checklist v0.4 features (F-12a-f)
   └─ Correlatos: ROADMAP.md

4. docs/agente_autonomo/AGENTE_AUTONOMO_CHANGELOG.md
   ├─ ⚠️ PRECISA ADD: Entry v0.4 (F-12 Backtest Engine)
   ├─ ⚠️ PRECISA ADD: Validações críticas (Reward + Database)
   └─ Correlatos: Todos

5. docs/agente_autonomo/AGENTE_AUTONOMO_FEATURES.md
   ├─ ⚠️ PRECISA UPDATE: F-12 status (⏳ TODO → ⏳ IN PROGRESS)
   ├─ ⚠️ PRECISA UPDATE: Subtasks F-12a-f status
   └─ Correlatos: BACKLOG, ROADMAP

6. docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md
   ├─ ⚠️ PRECISA UPDATE: F-12 backlog items prioridade
   └─ Correlatos: FEATURES, ROADMAP

7. docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER.md
   ├─ ⚠️ PRECISA UPDATE: Progress F-12 (Validações ✅ PASS)
   ├─ ✅ ADICIONAR: Novos documentos F12 (F12_KICKOFF_SUMMARY.md)
   ├─ ✅ ADICIONAR: Sprint tracker entries
   └─ Correlatos: Todos

8. .github/copilot-instructions.md
   ├─ ⚠️ PRECISA UPDATE: Status de referência para v0.4
   └─ Correlatos: README.md

9. CHANGELOG.md (root)
   ├─ ⚠️ PRECISA UPDATE: Entry F-12 start
   └─ Correlatos: README.md
```text

---

## ✅ CHECKLIST DE SINCRONIZAÇÃO

### **Fase 1: README.md + ROADMAP.md + RELEASE.md (CRITICAL PATH)**

- [ ] **README.md** — Seção "Status Operacional Atual"
  - [ ] Alterar heading de "⚠️ CRÍTICO" para "🟠 v0.3 VALIDAÇÃO + v0.4 SPRINT"
  - [ ] Atualizar texto: "Aguardando aprovação HEAD para ACAO-001" → "Sprint
  F-12 prep complete, começando 21/02"
  - [ ] Adicionar: "v0.4 (21-24 FEV): Backtester Engine"
  - [ ] Adicionar link novo documento: `F12_KICKOFF_SUMMARY.md`

- [ ] **ROADMAP.md** — Seção "v0.4 — BACKTEST ENGINE"
  - [ ] Alterar datas: 24-28 FEV → 21-24 FEV
  - [ ] F-12a status: ✅ 20 FEV → DONE
  - [ ] F-12b-f: ⏳ 25-27 FEV → TERÇA 21-QUINTA 23/02
  - [ ] Milestone "v0.4 release": 28 FEV → 23 FEV (ideal) / 24 FEV (worst case)

- [ ] **RELEASE.md** — Pre-release Checklist v0.4
  - [ ] Adicionar lines: "Sharpe ≥ 0.80 (target 1.20)" + "Max DD ≤ 12%"
  - [ ] Completar checklist v0.4 (atualmente TBD)

### **Fase 2: CHANGELOG + FEATURES + BACKLOG (SUPPORTIVO)**

- [ ] **CHANGELOG.md** (root)
  - [ ] Adicionar entry v0.4: "F-12 Backtest Engine sprint iniciado 21/02"
  - [ ] Registrar validações (Reward OK, Database validated)

- [ ] **AGENTE_AUTONOMO_CHANGELOG.md**
  - [ ] Adicionar: "v0.4 Development Started (2026-02-20)"
  - [ ] Detalhar: Validações críticas completadas

- [ ] **AGENTE_AUTONOMO_FEATURES.md**
  - [ ] F-12: ⏳ TODO → ⏳ IN PROGRESS (21/02 start)
  - [ ] F-12a: ⏳ TODO → ✅ DONE
  - [ ] F-12b-f: ⏳ TODO → ⏳ IN PROGRESS

- [ ] **AGENTE_AUTONOMO_BACKLOG.md**
  - [ ] Mover F-12 de "Planejado" para "Em Andamento"
  - [ ] Atualizar prioridade (CRÍTICA)

### **Fase 3: TRACKER + INSTRUÇÕES (OBSERVABILIDADE)**

- [ ] **AGENTE_AUTONOMO_TRACKER.md**
  - [ ] Adicionar entry: "F-12 Validation Passed (2026-02-20 23:00)"
  - [ ] Listar documentos atualizados
  - [ ] Status sync version: 1.1

- [ ] **.github/copilot-instructions.md**
  - [ ] Adicionar seção: "v0.4 F-12 Sprint (21-24 FEV)"
  - [ ] Instruções específicas para ESP-ENG + ESP-ML

---

## 🔗 DEPENDÊNCIAS DE SINCRONIZAÇÃO

```text
README.md (MAIN)
  ├─→ ROADMAP.md (timeline)
  ├─→ RELEASE.md (critérios)
  ├─→ CHANGELOG.md (versions)
  └─→ .github/copilot-instructions.md

ROADMAP.md
  ├─→ RELEASE.md (milestones)
  ├─→ FEATURES.md (feature status)
  └─→ TRACKER.md (progress)

FEATURES.md
  ├─→ BACKLOG.md (prioridade)
  └─→ CHANGELOG.md (history)

TRACKER.md (CONSOLIDAÇÃO)
  ├─→ ROADMAP.md
  ├─→ FEATURES.md
  ├─→ CHANGELOG.md
  └─→ TODAS
```text

---

## 📊 STATUS SYNC

| Documento | Situação | Prioridade | Ação |
|-----------|----------|------------|------|
| README.md | ⚠️ Desatualizado | 🔴 CRÍTICA | Atualizar hoje |
| ROADMAP.md | ⚠️ Datas erradas | 🔴 CRÍTICA | Corrigir datas F-12 |
| RELEASE.md | ⚠️ Incompleto | 🔴 CRÍTICA | Adicionar v0.4 critérios |
| CHANGELOG.md (root) | ✅ Ok | 🟡 ALTA | Adicionar F-12 entry |
| FEATURES.md | ⚠️ Desatualizado | 🟡 ALTA | Atualizar F-12 status |
| BACKLOG.md | ⚠️ Desatualizado | 🟡 ALTA | Mover F-12 para "Em Andamento" |
| TRACKER.md | ⚠️ Desatualizado | 🟡 ALTA | Adicionar entries recentes |
| copilot-instructions.md | ✅ Ok | 🟢 MÉDIA | Adicionar v0.4 seção |

---

## 🚀 PLANO DE EXECUÇÃO (HOJE — 23:45 UTC)

```text
FASE 1 — CRITICAL PATH (30 min):
├─ README.md atualizar status + roadmap
├─ ROADMAP.md corrigir datas v0.4
└─ RELEASE.md completar critérios v0.4

FASE 2 — SUPPORTIVO (20 min):
├─ CHANGELOG.md adicionar entry
├─ FEATURES.md atualizar F-12
└─ BACKLOG.md moverF-12

FASE 3 — OBSERVABILIDADE (10 min):
├─ TRACKER.md consolidar status
└─ copilot-instructions.md v0.4 seção

TOTAL: ~60 min.
```text

---

## 📝 VALIDAÇÃO PÓS-SYNC

**Checklist Final** (antes de commit):

- [ ] 100% documentos impactados foram revisados
- [ ] Datas consistentes (21-24 FEV v0.4 em TODOS)
- [ ] Status de features sincronizados
- [ ] Nenhuma seção conflitante
- [ ] Links funcionam (README → ROADMAP, etc)
- [ ] Português correto (sem typos, encoding UTF-8)
- [ ] Markdown lint OK (80 chars max)
- [ ] SYNCHRONIZATION.md atualizado com versão 1.1

**Commit Message**:
```text
[SYNC] Atualizar docs para F-12 Sprint (v0.4)

- README.md: Status operacional + novo roadmap
- ROADMAP.md: Datas F-12 (21-24 FEV)
- RELEASE.md: Critérios aprovação v0.4
- FEATURES.md: F-12 in-progress
- CHANGELOG.md: v0.4 entry
- TRACKER.md: Sprint F-12 consolidated

Referências:
- F12_KICKOFF_SUMMARY.md
- reward_validation_20feb.txt

Sync version: 1.1
```text

---

## 🎯 PRÓXIMO PASSO

**Executar**: Sincronização em 3 fases conforme plano acima
**Responsável**: Agente Autônomo (hoje 23:45-00:45 UTC)
**Validação**: Antes de commit final

---

**Status Inicial**: ✅ TRACKER CRIADO
**Status Ação**: ⏳ AGUARDANDO EXECUÇÃO

Execute as fases acima para manter documentação sincronizada!
