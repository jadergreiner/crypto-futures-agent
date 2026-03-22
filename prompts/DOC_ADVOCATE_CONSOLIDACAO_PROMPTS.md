# 📋 ANÁLISE DE CONSOLIDAÇÃO — Pasta `/prompts`

**Data:** 22 FEV 2026 16:00 UTC
**Responsável:** Doc Advocate
**Objetivo:** Unificar 19 arquivos de prompts nos 10 core docs (Decision #3)
**Status:** ✅ ANÁLISE COMPLETA

---

## 📊 RESUMO EXECUTIVO

| Classificação | Quantidade | Ação |
|---|---|---|
| **[A] DELETAR** | 10 | Prompts duplicados/auxiliares |
| **[C] UNIFICAR** | 7 | Consolidar em core docs |
| **[B] REPURPOSEAR** | 2 | Mover para local operacional |
| **[KEEP]** | 1 | board_16_members_data.json (config JSON) |
| **[INFO] JSON** | 2 | Status e manifests (deprecar) |
| **TOTAL** | **19** | |

---

## 📑 TABELA COMPLETA DE CLASSIFICAÇÃO

### 🗑️ [A] DELETAR — Prompts Obsoletos/Duplicados (10 arquivos)

| Arquivo | Classificação | Motivo Curto |
|:---|:---:|:---|
| `atualiza_docs.md` | [A] | Prompt para agente; sincronização já em SYNCHRONIZATION.md |
| `DISPARADOR_REUNIAO.md` | [A] | Trigger de reunião dated; protocolo em DECISIONS.md |
| `meeting_kickoff_prompt.md` | [A] | Prompt de kickoff; template consolidado em BEST_PRACTICES.md |
| `observacao_simbolo.md` | [A] | Prompt de análise de símbolo; conteúdo técnico, não necessário |
| `reuniao_ciclo_opinoes_ativada.md` | [A] | Ata de reunião específica; consolidar em DECISIONS.md |
| `REUNIAO_HEAD_OPERADOR.md` | [A] | Ata de reunião operador; consolidar em DECISIONS.md |
| `reuniao_setup.md` | [A] | Setup de reunião (template); em BEST_PRACTICES.md |
| `reuniao.md` | [A] | Template reunião genérico; em BEST_PRACTICES.md |
| `TASK-005_DELIVERY_SUMMARY.txt` | [A] | Arquivo TXT dated; conteudo em BACKLOG.md |
| `TASK-005_DAILY_EXECUTION_CHECKLIST.md` | [A] | Checklist diário; conteúdo em SYNCHRONIZATION.md |

---

### 🔄 [C] UNIFICAR — Consolidar em Core Docs (7 arquivos)

| Arquivo | Destino | Consolidação | Motivo |
|:---|:---|:---|:---|
| `prompt_master.md` | [BEST_PRACTICES.md](../docs/BEST_PRACTICES.md) | Seção "Protocolo de Board Interativo" | Template para reuniões board |
| `relatorio_executivo.md` | [USER_MANUAL.md](../docs/USER_MANUAL.md) | Seção "9. Operações: Relatórios Executivos" | Guia geração de relatórios diários |
| `TASK-005_EXECUTIVE_SUMMARY.md` | [BACKLOG.md](../docs/BACKLOG.md) | Seção "TASK-005: Resumo Executivo" | Especificacao PPO training |
| `TASK-005_ML_THEORY_GUIDE.md` | [FEATURES.md](../docs/FEATURES.md) | Seção "F-ML1: Teoria PPO Training" | Referência técnica ML |
| `TASK-005_SWE_COORDINATION_PLAN.md` | [BACKLOG.md](../docs/BACKLOG.md) | Seção "TASK-005: Plano SWE" | Timeline e milestones implementacao |
| `TASK-005_SPECIFICATION_PACKAGE_README.md` | [SYNCHRONIZATION.md](../docs/SYNCHRONIZATION.md) | Seção "TASK-005: Especificação" | Pacote entregável PPO |

---

### 🔄 [B] REPURPOSEAR — Mover para Local Operacional (2 arquivos)

| Arquivo | Ação | Novo Local | Motivo |
|:---|:---|:---|:---|
| `TASK-005_ML_SPECIFICATION_PLAN.json` | **ARQUIVAR** | `backlog/archive/TASK-005_ML_SPEC_20FEV.json` | Especificação concluída; guardar histórico |
| `TASK-005_STATUS_MANIFEST.json` | **MOVER** | `backlog/TASK-005_STATUS_MANIFEST.json` | Status atual de backlog |

---

### ✅ [KEEP] Manter como Referência

| Arquivo | Propósito | Localização |
|:---|:---|:---|
| `board_16_members_data.json` | Configuração de board (16 membros) | ✅ MANTER em `prompts/` (não é doc, é config) |

---

## 🎯 PLANO DE EXECUÇÃO DETALHADO

### **Fase 1: Consolidação em Core Docs (24h)**

#### 1.1 → `docs/BEST_PRACTICES.md`

**Adicionar seção:**

```markdown
## 🎭 Protocolo de Board Interativo (16 Membros)

### [Fluxo da Sessão]
[Migrar conteúdo de prompt_master.md seção "FLUXO DA SESSÃO"]

### [Dinâmica de Facilitação]
[Migrar conteúdo de prompt_master.md seção "DINÂMICA DA REUNIÃO ABERTA"]

### [Mapa de Consultoria por Especialidade]
[Migrar tabela de prompt_master.md]
```

**Ação:** Doc Advocate adapta para Markdown e valida integridade.

#### 1.2 → `docs/USER_MANUAL.md`

**Adicionar seção:**

```markdown
## 9. Operações: Relatórios Executivos

### [Objetivo e Trigger]
[Migrar conteúdo de relatorio_executivo.md seção "OBJECTIVE"]

### [Dados Requeridos]
[Migrar conteúdo de relatorio_executivo.md seção "INPUT DATA REQUIRED"]

### [Estrutura do Relatório]
[Migrar conteúdo de relatorio_executivo.md seção "OUTPUT"]
```

**Ação:** Doc Advocate consolida e adiciona exemplos reais.

#### 1.3 -> `docs/BACKLOG.md`

**Adicionar seção:**

```markdown
## TASK-005: PPO Training Phase 4

### [Resumo Executivo]
[Migrar conteúdo de TASK-005_EXECUTIVE_SUMMARY.md seção "The Ask"]

### [Arquitetura Overview]
[Migrar conteúdo de TASK-005_EXECUTIVE_SUMMARY.md seção "Architecture Overview"]

### [Plano SWE Coordenação]
[Migrar conteúdo de TASK-005_SWE_COORDINATION_PLAN.md]

### [Key Design Choices]
[Migrar tabela de TASK-005_EXECUTIVE_SUMMARY.md]
```

**Ação:** Dev + Doc Advocate mesclam conteúdo técnico.

#### 1.4 → `docs/FEATURES.md`

**Adicionar seção:**

```markdown
## F-ML1: PPO Training Pipeline

### [Teoria PPO & Aprendizagem Contextual]
[Migrar conteúdo de TASK-005_ML_THEORY_GUIDE.md]

### [Convergência & Métricas]
[Adicionar: Sharpe ≥1.0, DD <5%, WR ≥52%]
```

**Ação:** The Brain valida conteúdo técnico ML.

#### 1.5 → `docs/SYNCHRONIZATION.md`

**Adicionar seção:**

```markdown
## TASK-005: Especificação & Sincronização

### [Pacote Entregável]
[Migrar conteúdo de TASK-005_SPECIFICATION_PACKAGE_README.md]

### [Matriz de Dependências TASK-005]
[Converter TASK-005_ML_SPECIFICATION_PLAN.json para Markdown table]
```

**Ação:** Doc Advocate converte JSON em Markdown.

---

### **Fase 2: Repurposear Arquivos JSON (8h)**

#### 2.1 Arquivar Status Manifest

```bash
# Mover para histórico
mv prompts/TASK-005_STATUS_MANIFEST.json backlog/TASK-005_STATUS_MANIFEST.json
# Arquivar especificação concluída
mkdir -p backlog/archive
mv prompts/TASK-005_ML_SPECIFICATION_PLAN.json backlog/archive/TASK-005_ML_SPEC_20FEV.json
```

#### 2.2 Validar board_16_members_data.json

```bash
# Verificar que está sendo usado
grep -r "board_16_members_data.json" .github/ backlog/ docs/ 2>/dev/null
# Manter em prompts/ (é config JSON, não doc)
```

---

### **Fase 3: Deletar Prompts Obsoletos (4h)**

**Remove:**

```bash
rm prompts/atualiza_docs.md
rm prompts/DISPARADOR_REUNIAO.md
rm prompts/meeting_kickoff_prompt.md
rm prompts/observacao_simbolo.md
rm prompts/reuniao_ciclo_opinoes_ativada.md
rm prompts/REUNIAO_HEAD_OPERADOR.md
rm prompts/reuniao_setup.md
rm prompts/reuniao.md
rm prompts/TASK-005_DELIVERY_SUMMARY.txt
rm prompts/TASK-005_DAILY_EXECUTION_CHECKLIST.md
```

---

### **Fase 4: Validação & Commit (8h)**

1. ✅ Markdown lint em docs atualizados (max 80 chars, UTF-8)
2. ✅ Validar links cruzados (BACKLOG -> FEATURES -> BEST_PRACTICES)
3. ✅ Verificar que board_16_members_data.json funciona após consolidação
4. ✅ Atualizar STATUS_ATUAL.md com nova estrutura
5. ✅ Atualizar SYNCHRONIZATION.md com histórico mudanças
6. ✅ Commit: `[SYNC] Consolidação prompts/ nos 10 core docs`

---

## 📊 IMPACTO ESPERADO

### **Antes:**
- 19 arquivos em `prompts/` (prompts + docs + configs misturados)
- Duplicação: protocolo de board em 3 arquivos diferentes
- Risco: prompts desatualizados quando docs mudam

### **Depois:**
- 1 arquivo em `prompts/` (somente `board_16_members_data.json` — config)
- 7 consolidados em 10 core docs
- 10 deletados (obsoletos)
- 2 movidos para `backlog/` (histórico)
- ✅ Fonte da verdade centralizada

---

## 🔄 ARQUIVOS QUE PERMANECEM EM `prompts/`

**Única permanência:**

| Arquivo | Propósito | Por quê |
|:---|:---|:---|
| `board_16_members_data.json` | Config estrutura board 16 membros | Config JSON, não documentação |

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [ ] **Fase 1:** Consolidar em BEST_PRACTICES.md, USER_MANUAL.md, BACKLOG.md, FEATURES.md, SYNCHRONIZATION.md
- [ ] **Fase 2:** Arquivar TASK-005_ML_SPECIFICATION_PLAN.json; mover TASK-005_STATUS_MANIFEST.json
- [ ] **Fase 3:** Deletar 10 prompts obsoletos
- [ ] **Fase 4:** Validação markdown lint + links
- [ ] **Fase 5:** Verificar board_16_members_data.json ainda funciona
- [ ] **Fase 6:** Commit [SYNC] + merge
- [ ] **Fase 7:** Atualizar referência em `.github/copilot-instructions.md`

---

## 📞 PRÓXIMAS AÇÕES

**Imediato (hoje/amanhã):**
1. Copiar conteúdo de prompts em 5 core docs
2. Validar markdown lint
3. Deletar 10 prompts obsoletos
4. Arquivar JSON histórico

**Follow-up (antes de TASK-005 QA):**
- Testar board_16_members_data.json após consolidação
- Atualizar copilot-instructions.md (remover referência a prompts/)

---

**Prepared by:** Doc Advocate
**For:** Elo (Facilitador), Product, Dev Team
**Deadline:** 23 FEV 2026 (antes de TASK-005 QA)

