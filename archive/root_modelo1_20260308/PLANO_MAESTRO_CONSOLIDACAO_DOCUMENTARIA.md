# 🎯 PLANO MAESTRO — Consolidação Documentária (Decision #3)

**Projeto:** crypto-futures-agent  
**Objetivo:** Implementar fonte da verdade com 10 core docs  
**Status:** ✅ ANÁLISES COMPLETAS — ⏳ PRONTO PARA EXECUÇÃO  
**Data Criação:** 22 FEV 2026  
**Deadline Final:** 25 FEV 2026 (antes de TASK-005 QA)

---

## 📊 STATUS POR FASE

### **FASE 1: Análise & Classificação** ✅ COMPLETA

| Localização | Arquivos | Análise | Status |
|---|---|---|---|
| **docs/** | 58 | [docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md](docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md) | ✅ COMPLETA |
| **backlog/** | 15 | [backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md](backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md) | ✅ COMPLETA |
| **checkpoints/ppo_training/** | 1 | [checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md](checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md) | ✅ COMPLETA |
| **prompts/** | 19 | [prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md](prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md) | ✅ COMPLETA |
| **reports/** | 15 | [reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md](reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md) | ✅ COMPLETA |
| **scripts/** | 1 | [scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md](scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md) | ✅ COMPLETA |
| **raiz/** | 60+ | [DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md](DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md) | ✅ PEND. HUMAN REVIEW |
| **TOTAL** | **169** | — | — |

---

## 🎯 ESTRUTURA DOS 10 CORE DOCS

**Fonte da Verdade Únicos Autorizados:**

| # | Core Doc | Propósito | Maintenance Owner |
|---|---|---|---|
| 1 | `RELEASES.md` | Versões, deliverables, histórico | Product |
| 2 | `ROADMAP.md` | Timeline, planejamento futuro | Elo (Strategic) |
| 3 | `FEATURES.md` | Funcionalidades sistema, spec técnica | The Brain |
| 4 | `TRACKER.md` | Sprints, backlog, tasks, kanban | Planner |
| 5 | `USER_STORIES.md` | Requisitos de usuário (US-01 a US-05) | Product |
| 6 | `LESSONS_LEARNED.md` | Insights, lições, best practices | Executor |
| 7 | `STATUS_ATUAL.md` | Dashboard go-live, status real-time | Status Owner |
| 8 | `DECISIONS.md` | Histórico decisões, approvals, governance | Elo (Decisão) |
| 9 | `USER_MANUAL.md` | Onboarding, operação, procedimentos | Product + Executor |
| 10 | `SYNCHRONIZATION.md` | Audit trail, metadados, histórico mudanças | Doc Advocate |

---

## 📋 PLANO DE EXECUÇÃO SEQUENCIAL

### **Fase 2A: Consolidação `prompts/` (MENOR → MAIOR)**

**Arquivos:** 19 total | **Para unificar:** 7 | **Para deletar:** 10 | **Para mover:** 2

**Destinos:**
- BEST_PRACTICES.md: `prompt_master.md`
- USER_MANUAL.md: `relatorio_executivo.md`
- TRACKER.md: `TASK-005_EXECUTIVE_SUMMARY.md`, `TASK-005_SWE_COORDINATION_PLAN.md`
- FEATURES.md: `TASK-005_ML_THEORY_GUIDE.md`
- SYNCHRONIZATION.md: `TASK-005_SPECIFICATION_PACKAGE_README.md`

**Deletar:**
- `atualiza_docs.md`, `DISPARADOR_REUNIAO.md`, `meeting_kickoff_prompt.md`
- `observacao_simbolo.md`, `reuniao_ciclo_opinoes_ativada.md`, `REUNIAO_HEAD_OPERADOR.md`
- `reuniao_setup.md`, `reuniao.md`, `TASK-005_DAILY_EXECUTION_CHECKLIST.md`
- `TASK-005_DELIVERY_SUMMARY.txt`

**Mover:**
- `TASK-005_ML_SPECIFICATION_PLAN.json` → `backlog/archive/`
- `TASK-005_STATUS_MANIFEST.json` → `backlog/`

**Timeline:** 24h (Fase 1.1-1.4: consolidar, mover, deletar, validar)

**Reference:** [prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md](prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md)

---

### **Fase 2B: Consolidação `scripts/` (1 arquivo)**

**Arquivos:** 40 total | **Para unificar:** 1 MD | **Remover:** __pycache__/

**Destinos:**
- BEST_PRACTICES.md: Seção "Board Meeting Scripts"
- USER_MANUAL.md: Seção "9. Board Meeting Automation"

**Deletar:**
- `scripts/README_BOARD_MEETINGS.md`

**Timeline:** 8h

**Reference:** [scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md](scripts/DOC_ADVOCATE_CONSOLIDACAO_SCRIPTS.md)

---

### **Fase 2C: Consolidação `reports/` (12 arquivos)**

**Arquivos:** 15 total | **Para unificar:** 3 | **Para deletar:** 12

**Destinos:**
- DECISIONS.md: `board_governance_docs_21fev.json`
- STATUS_ATUAL.md: `phase4_readiness_validation.json`, `relatorio_executivo_2026-02-17.md`
- TRACKER.md: Board meetings reference

**Deletar:**
- `board_encerramento_21fev.json`, board meetings (3), `.html` reports
- `REUNIAO_BOARD_ENCERRADA_21FEV2026.md`, data CSVs, revalidation JSONs

**Timeline:** 12h

**Reference:** [reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md](reports/DOC_ADVOCATE_CONSOLIDACAO_REPORTS.md)

---

### **Fase 2D: Consolidação `backlog/` (6 arquivos)**

**Arquivos:** 15 total | **Para unificar:** 6 | **Para deletar:** 6 | **Para manter:** 3

**Destinos:**
- TRACKER.md: Sprint backlogs, realtime tasks
- SYNCHRONIZATION.md: Matriz dependências, task-005 plans
- STATUS_ATUAL.md: Docs updated summary

**Timeline:** 16h

**Reference:** [backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md](backlog/DOC_ADVOCATE_CONSOLIDACAO_BACKLOG.md)

---

### **Fase 2E: Consolidação `checkpoints/ppo_training/` (1 arquivo)**

**Arquivos:** 1 total | **Para unificar:** 1

**Destinos:**
- USER_MANUAL.md: PPO training procedures
- STATUS_ATUAL.md: Phase 4 monitoring

**Timeline:** 8h

**Reference:** [checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md](checkpoints/ppo_training/DOC_ADVOCATE_CONSOLIDACAO_PPO_TRAINING.md)

---

### **Fase 2F: Consolidação `docs/` (24 arquivos — ÚLTIMA)**

**Arquivos:** 58 total | **Para consolidar:** 24 | **Para deletar:** 17 | **Para manter:** 10

**Destinos:**
- Mesclagem em 10 core docs
- Deletar 17 duplicados
- Manter 10 atuais como fonte-da-verdade

**Timeline:** 48h

**Reference:** [docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md](docs/DOC_ADVOCATE_CLASSIFICATION_ANALYSIS.md)

---

### **Fase 3: Validação Global (16h)**

1. ✅ Markdown lint em TODOS 10 core docs (max 80 chars, UTF-8)
2. ✅ Validar referências cruzadas (links entre docs)
3. ✅ Verificar que board_16_members_data.json funciona
4. ✅ Update copilot-instructions.md (remover refs a satellite files)
5. ✅ Update STATUS_ATUAL.md (consolidação completa)
6. ✅ Update SYNCHRONIZATION.md (audit trail completo)

---

### **Fase 4: Consolidação RAIZ (Post-validação)**

**⚠️ REQUER HUMAN REVIEW ANTES DE EXECUÇÃO**

Após fases 2A-2F 100% completas:

1. **Analysis:** Triagem manual de 60+ arquivos markdown raiz
2. **Classification:** [A], [C], [B] por arquivo
3. **Execution:** Consolidação em waves (5 arquivos por wave)
4. **Timeline:** 90-180h (parallelizar por especialidade)

**Reference:** [DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md](DOC_ADVOCATE_CONSOLIDACAO_RAIZ.md)

---

## 🎯 TIMELINE CONSOLIDADO

| Fase | Localização | Duração | Data Est. | Status |
|---|---|---|---|---|
| **2A** | prompts/ | 24h | 22-23 FEV | ⏳ PRONTO |
| **2B** | scripts/ | 8h | 23 FEV | ⏳ PRONTO |
| **2C** | reports/ | 12h | 23 FEV | ⏳ PRONTO |
| **2D** | backlog/ | 16h | 23-24 FEV | ⏳ PRONTO |
| **2E** | checkpoints/ | 8h | 24 FEV | ⏳ PRONTO |
| **2F** | docs/ | 48h | 24-25 FEV | ⏳ PRONTO |
| **3** | Validação Global | 16h | 25 FEV | ⏳ PRONTO |
| **4** | Raiz (Human Review) | 90-180h | 25+ FEV | ⏳ PEND. APROVAÇÃO |
| **TOTAL** | — | **232h + human review** | — | — |

---

## 🔄 [SYNC] PROTOCOL — OBRIGATÓRIO EM TODOS OS COMMITS

**Padrão de commit para cada consolidação:**

```
[SYNC] Consolidação [LOCALIZAÇÃO] nos 10 core docs (Fase 2X)

- Unificar: [N] arquivos em [CORE_DOCS]
- Deletar: [N] arquivos obsoletos
- Mover: [N] arquivos para histórico
- Markdown lint: ✅ Validado
- Links cruzados: ✅ Validado
- Reference: [LOCALIZAÇÃO]/DOC_ADVOCATE_CONSOLIDACAO_*.md

Author: Doc Advocate
Approver: [Responsável da Fase]
```

**Exemplo:**

```
[SYNC] Consolidação prompts/ nos 10 core docs (Fase 2A)

- Unificar: 7 arquivos em BEST_PRACTICES, USER_MANUAL, TRACKER, FEATURES, SYNCHRONIZATION
- Deletar: 10 prompts obsoletos
- Mover: 2 JSON → backlog/archive e backlog/
- Markdown lint: ✅ Validado (max 80 chars, UTF-8)
- Links cruzados: ✅ Validado (prompt_master → BEST_PRACTICES, etc)
- Reference: prompts/DOC_ADVOCATE_CONSOLIDACAO_PROMPTS.md

Author: Doc Advocate
```

---

## ✅ PRÉ-REQUISITOS ANTES DE INICIAR EXECUÇÃO

- [ ] **1. Análises 100% completas em 6 pastas** ✅ (FEITO)
- [ ] **2. [SYNC] protocol documentado** → Ver copilot-instructions.md
- [ ] **3. 10 core docs estáveis** → Validar que existem em docs/
- [ ] **4. board_16_members_data.json atualizado** → Com doc_guidelines para 4 roles
- [ ] **5. README.md referencia 10 core docs** → Validar fonte-da-verdade sección
- [ ] **6. Markdown linter disponível** → `markdownlint *.md docs/*`
- [ ] **7. Git hooks preparado (opcional)** → Pre-commit hook para [SYNC] tags
- [ ] **8. Aprovação de Elo** → Gestor aprova timeline execution

---

## 📞 OWNERS & RESPONSABILIDADES

| Fase | Owner Principal | Validador | Timeline |
|---|---|---|---|
| **2A (prompts/)** | Doc Advocate + Dev | Executor | 22-23 FEV |
| **2B (scripts/)** | Doc Advocate + Dev | Executor | 23 FEV |
| **2C (reports/)** | Doc Advocate + Product | Planner | 23 FEV |
| **2D (backlog/)** | Doc Advocate + Planner | Dev | 23-24 FEV |
| **2E (checkpoints/)** | Doc Advocate + The Brain | Executor | 24 FEV |
| **2F (docs/)** | Doc Advocate | The Brain + Product | 24-25 FEV |
| **3 (Validation)** | Doc Advocate | Audit | 25 FEV |
| **4 (Raiz)** | Doc Advocate (coordenação) | Elo + especialistas | 25+ FEV |

---

## 🚨 CRITÉRIO DE SUCESSO

Consolidação é bem-sucedida quando:

1. ✅ **Deletados:** 51 arquivos satellite (sem perder conteúdo)
2. ✅ **Consolidados:** 118 arquivos em 10 core docs
3. ✅ **Referências:** 100% dos links cruzados validados
4. ✅ **Markdown:** Max 80 chars/linha, UTF-8 válido, português
5. ✅ **[SYNC] tags:** Todos commits com protocolo observado
6. ✅ **Atualizado:** copilot-instructions.md, README.md, STATUS_ATUAL.md, SYNCHRONIZATION.md
7. ✅ **Board:** 16 membros têm doc_guidelines com referências corretas
8. ✅ **Audit Trail:** SYNCHRONIZATION.md com histórico completo consolidação

---

## 📋 CHECKLIST — KICKOFF EXECUÇÃO

**Antes de começar Fase 2A:**

- [ ] **Doc Advocate:** Validar análises 1-6 OK
- [ ] **Executor:** Confirmar disponibilidade timeline (232h sprint)
- [ ] **Elo:** Aprovar Decision #3 + [SYNC] protocol
- [ ] **Product:** Validar conteúdo operacional consolidações
- [ ] **The Brain:** Validar conteúdo técnico consolidações
- [ ] **Audit:** Preparar validation checklist
- [ ] **Dev:** Preparar deploy/merge plan para [SYNC] commits

---

**Prepared by:** Doc Advocate  
**Approved by:** [Elo — Gestor]  
**Reference:** 
- README.md (Fonte da Verdade seção)
- .github/copilot-instructions.md (Documento oficial)
- prompts/board_16_members_data.json (Governance)

**Status:** ⏳ **AGUARDANDO APROVAÇÃO ELO PARA KICKOFF EXECUÇÃO**

