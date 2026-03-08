# ✅ Protocol de Avaliação de Tasks — Integridade Estrutural

**Versão:** 0.1.0
**Data:** 07 MAR 2026
**Responsável:** Doc Advocate, Arquiteto, Planner
**Aplicabilidade:** Todas as tasks, issues, PRs (desde Sprint 3 em diante)

---

## 🎯 Objetivo

Garantir que **cada task entregue/avaliada** observe a estrutura mínima de documentação e mapear **integridade referencial** entre:
- Código implementado
- Arquitetura (C4_MODEL)
- Decisões (ADR_INDEX)
- Regras de negócio (REGRAS_DE_NEGOCIO)
- Modelo de dados (MODELAGEM_DE_DADOS)
- Diagramas (DIAGRAMAS)

---

## 📋 CHECKLIST DE AVALIAÇÃO (Must-Have)

Toda **task/issue/PR** deve passar por este checklist antes de marcar como ✅ **COMPLETA**:

### 1️⃣ **Impacto na Arquitetura**

- [ ] **Novo módulo criado?**
  - ✅ SIM → Adicionar em [C4_MODEL.md](C4_MODEL.md) nível 3 (Components)
  - ✅ SIM → Adicionar em [DIAGRAMAS.md](DIAGRAMAS.md) seção "Diagrama de Classes"
  - ❌ NÃO → Saltar

- [ ] **Novo container de dados criado?**
  - ✅ SIM → Adicionar em [C4_MODEL.md](C4_MODEL.md) nível 2 (Containers)
  - ❌ NÃO → Saltar

- [ ] **Mudança em fluxo existente?**
  - ✅ SIM → Atualizar diagrama de interação em [DIAGRAMAS.md](DIAGRAMAS.md)
  - ❌ NÃO → Saltar

**Exemplo:** TASK-011 (F-12b Symbols)
- ✅ Adicionou módulo `data/parquet_manager.py` → C4_MODEL nivel 3
- ✅ Adicionou "Parquet Storage" container → C4_MODEL nivel 2
- ✅ Atualizou fluxo Read Path → DIAGRAMAS.md

---

### 2️⃣ **Decisão Técnica**

- [ ] **Decisão de design novo criado?**
  - ✅ SIM → Criar novo ADR em [ADR_INDEX.md](ADR_INDEX.md)
  - ✅ Seguir formato: Status | Champion | Contexto | Decisão | Consequências | Alternativas
  - ❌ NÃO (mudança trivial/configuração) → Saltar

- [ ] **ADR impacta decisões futuras?**
  - ✅ SIM → Documentar "Referências" ao fim do ADR
  - ❌ NÃO → Apenas auto-contido

**Exemplo:** TASK-001 (Consolidação Documentária)
- ✅ Criou ADR-008: "Decision Log Consolidation"
- ✅ Status: APPROVED | Date: 22 FEV 2026
- ✅ Champion: Doc Advocate
- ✅ Impacta: DECISIONS.md (policy de commit [SYNC])

---

### 3️⃣ **Regras de Negócio**

- [ ] **Lógica de trading/risk alterada?**
  - ✅ SIM → Mapear a [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md)
  - ✅ Se nova regra → Adicionar R16, R17, etc com formato Rnn
  - ✅ Se alteração de regra existente → Atualizar versão + data + mudanças
  - ✅ Se implementação da regra → Referenciar Rnn na seção "Mapeamento: Regras → Código"
  - ❌ NÃO (mudança puramente técnica) → Saltar

- [ ] **Capital, posições, drawdown, leverage afetados?**
  - ✅ SIM → Validar contra R1-R7 (regras invioláveis)
  - ✅ Se mudança de limite → CEO approval (DECISIONS.md)
  - ✅ Se bypasss de regra → BLOQUEADO (não permitido)

**Exemplo:** Issue #64 (Telegram Alerts)
- ✅ Implementou notificação para R5 (drawdown limits)
- ✅ Adicionou alerta em -5%, -8%, -12%, -15%
- ✅ Referenciado em REGRAS_DE_NEGOCIO.md R5 → "Aplicação: Monitoramento em tempo real"

---

### 4️⃣ **Modelagem de Dados**

- [ ] **Nova entidade criada ou alterada?**
  - ✅ SIM → Atualizar [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md)
  - ✅ Adicionar bloco da entidade com estrutura completa
  - ✅ Atualizar seção "Integridade Referencial" (FKs, deletes, updates)
  - ✅ Atualizar histórico "Histórico de Mudanças"
  - ❌ NÃO → Saltar

- [ ] **Novo schema/tabela adicionado?**
  - ✅ SIM → Atualizar [DIAGRAMAS.md](DIAGRAMAS.md) seção "Diagrama de Dados (ER Model)"
  - ✅ Atualizar índices recomendados (seção "Índices Críticos")
  - ✅ Mapear na seção "Fluxo de Dados Críticos"

- [ ] **Fluxo de dados alterado?**
  - ✅ SIM → Atualizar [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) → "Fluxos de Dados Críticos"
  - ✅ ASCII diagram atualizado ou novo

**Exemplo:** TASK-011 (Parquet Snapshots)
- ✅ Adicionou entidade `parquet_snapshot` em MODELAGEM_DE_DADOS
- ✅ Adicionou "Persistência: Parquet Storage" container
- ✅ Atualizou fluxo "Backup de Candles 1Y" em MODELAGEM_DE_DADOS

---

### 5️⃣ **Diagramas Atualizados**

- [ ] **Classes/Componentes impactados?**
  - ✅ SIM → Atualizar [DIAGRAMAS.md](DIAGRAMAS.md) seção "Diagrama de Classes"
  - ✅ Se novo agregado → Adicionar bloco completo com métodos + atributos
  - ✅ Se novo relacionamento → Atualizar setas de agregação/ownership/use

- [ ] **ER Model afetado?**
  - ✅ SIM → Atualizar [DIAGRAMAS.md](DIAGRAMAS.md) seção "Diagrama de Dados"
  - ✅ Atualizar relações 1:1, 1:N, FKs
  - ✅ Adicionar em "Fluxo de Persistência" se novo

---

### 6️⃣ **Commit com Tag [SYNC]**

- [ ] **Todas mudanças de docs com tag [SYNC]?**
  - ✅ SIM → Commit message segue padrão: `[SYNC] Descrição breve (max 72 chars)`
  - ✅ Múltiplos docs afetados → Exemplo: `[SYNC] C4_MODEL + REGRAS_DE_NEGOCIO: Task-011 Parquet`
  - ✅ Registrar em [SYNCHRONIZATION.md](SYNCHRONIZATION.md) com:
    - Task ID
    - Documentos alterados
    - Timestamp
    - Mudanças resumidas
  - ❌ NÃO → Task não pode ser marcada como COMPLETA

---

## 🎓 EXEMPLOS DE APLICAÇÃO

### Exemplo 1: TASK-011 (F-12b Symbols + Parquet) ✅ CORRETO

**Checklist Resultado:**

1. ✅ **Impacto Arquitetura**
   - [ C4_MODEL.md ](C4_MODEL.md) — Adicionado container "Parquet Snapshots" nível 2
   - [ C4_MODEL.md ](C4_MODEL.md) — Adicionado componente "ParquetManager" nível 3
   - [ DIAGRAMAS.md ](DIAGRAMAS.md) — Atualizado fluxo de Read Path

2. ✅ **Decisão Técnica**
   - [ ADR_INDEX.md ](ADR_INDEX.md) — ADR-002 já existia (Dual Cache Strategy)
   - Task-011 = implementação do ADR-002, não nova decisão

3. ✅ **Regras de Negócio**
   - [ REGRAS_DE_NEGOCIO.md ](REGRAS_DE_NEGOCIO.md) — R1, R6, R7 validadas em 200 símbolos
   - Nenhuma regra nova introduzida

4. ✅ **Modelagem de Dados**
   - [ MODELAGEM_DE_DADOS.md ](MODELAGEM_DE_DADOS.md) — Entidade "Candle" atualizada
   - Tabela `candle_parquet` adicionada com schema completo
   - Índices recomendados (symbol, timeframe)

5. ✅ **Diagramas**
   - [ DIAGRAMAS.md ](DIAGRAMAS.md) — ER Model: adicionado `candle` ligado a `signal`
   - [ DIAGRAMAS.md ](DIAGRAMAS.md) — Fluxo Read Path: Parquet adicionado como fallback

6. ✅ **Commit [SYNC]**
   - `[SYNC] C4_MODEL + MODELAGEM_DE_DADOS + DIAGRAMAS: Task-011 Parquet integration`
   - Registrado em SYNCHRONIZATION.md

**Status:** ✅ **COMPLETA** — todas as seções de documentação atualizadas

---

### Exemplo 2: Mudança Trivial (Bug Fix) ❌ NÃO REQUER SYNC

**Task:** "Fix cálculo de reward na linha 456 de reward_calculator.py"

**Checklist Resultado:**

1. ❌ **Impacto Arquitetura** — Simples mudança lógica, sem novo módulo
2. ❌ **Decisão Técnica** — Bug fix, não decisão de design
3. ❌ **Regras de Negócio** — Lógica de reward = implementação, não mudança de regra
4. ❌ **Modelagem de Dados** — Nenhum schema adiciona
5. ❌ **Diagramas** — Sem mudança visual
6. ✅ **Commit** — Padrão normal (sem [SYNC]): `[FIX] Corrigir cálculo reward`

**Status:** ✅ **COMPLETA** — sem exigência [SYNC]

---

### Exemplo 3: Nova Regra de Trading ✅ REQUER TODAS SEÇÕES

**Task:** "Adicionar corte de risco de -20% diário (nova regra)"

**Checklist Resultado:**

1. ✅ **Impacto Arquitetura**
   - Se novo módulo `risk/daily_circuit_breaker.py` → C4_MODEL + DIAGRAMAS

2. ✅ **Decisão Técnica**
   - Criar ADR-009: "Daily Loss Limit Circuit Breaker"

3. ✅ **Regras de Negócio** 🔴 **CRÍTICO**
   - Adicionar: `R16: Limite de Perda Diária -20%`
   - Classificar: Regra inviolável (sim/não)?
   - Mapeamento: que classe implementa?

4. ✅ **Modelagem de Dados**
   - Se novo campo `daily_loss_usd` na `performance` table

5. ✅ **Diagramas**
   - Se novo `DailyLossMonitor` → Diagrama de Classes
   - Se novo campo em `performance` → ER Model

6. ✅ **Commit [SYNC]**
   - `[SYNC] ADR + REGRAS_DE_NEGOCIO + C4_MODEL + DIAGRAMAS: Task-New Daily Circuit Breaker (R16)`

**Status:** ✅ **COMPLETA** ou 🟡 **BLOQUEADO** se CEO não aprova em DECISIONS.md

---

## 🔍 VERIFICAÇÃO (Antes de merge)

### Checklist do PR Reviewer

```markdown
## Documentação - Integridade Estrutural

- [ ] Checklist de Avaliação preenchido (5/6 seções aplicáveis)
- [ ] Se Arquitetura impactada → C4_MODEL.md atualizado
- [ ] Se Decisão nova → ADR_INDEX.md com novo ADR
- [ ] Se Regra alterada → REGRAS_DE_NEGOCIO.md sincronizado
- [ ] Se Schema mudou → MODELAGEM_DE_DADOS.md + DIAGRAMAS.md
- [ ] Se Classes afetadas → DIAGRAMAS.md Classe atualizado
- [ ] Commit com tag [SYNC] se docs alteradas
- [ ] SYNCHRONIZATION.md atualizado (task ID + docs + timestamp)
- [ ] TODO: Nível correto (P0=must, P1=should, P2=nice-to-have)
```

---

## 🚀 Integração com Workflow

### Onde aparecer este checklist?

1. **GitHub PR Template** — Campo obrigatório na descrição do PR
2. **GitHub Issue Template** — Campo "Documentação" em tarefas
3. **BACKLOG.md** — Validação como "Entrada em AC (Acceptance Criteria)"
4. **Board** — Status "Documentation ✅" antes de "Done"

### Quem valida?

| Papel | Responsabilidade |
|-------|-----------------|
| **Executor (Dev)** | Prenchimento do checklist ao submeter PR |
| **Code Reviewer** | Validação técnica integridade code |
| **Doc Advocate** | Validação integridade documentação (checklist) |
| **Arquiteto** | Validação impacto C4_MODEL + ADR |
| **Planner** | Validação contra REGRAS_DE_NEGOCIO |
| **Merge Master** | Checklist 100% ✅ antes de merge |

---

## 📊 Matriz de Verificação Rápida

Imprima e use:

```
TASK ID: ____________________
TÍTULO: ____________________

┌─────────────────────────────────────────┐
│ 1. ARQUITETURA     ☐ N/A  ☐ ✅  ☐ ❌   │
│ 2. DECISÃO         ☐ N/A  ☐ ✅  ☐ ❌   │
│ 3. REGRAS NEG.     ☐ N/A  ☐ ✅  ☐ ❌   │
│ 4. MODELAGEM       ☐ N/A  ☐ ✅  ☐ ❌   │
│ 5. DIAGRAMAS       ☐ N/A  ☐ ✅  ☐ ❌   │
│ 6. SYNC COMMIT     ☐ N/A  ☐ ✅  ☐ ❌   │
│                                         │
│ STATUS: ☐ INCOMPLETO  ☐ COMPLETO      │
└─────────────────────────────────────────┘

DOCS ALTERADOS:
  □ C4_MODEL.md
  □ ADR_INDEX.md
  □ REGRAS_DE_NEGOCIO.md
  □ MODELAGEM_DE_DADOS.md
  □ DIAGRAMAS.md
  □ SYNCHRONIZATION.md

DATA: __________  REVISOR: ________________
```

---

## 🎓 Treinamento Recomendado (1h)

**Conteúdo:**
1. Visão geral da estrutura mínima (10 min)
2. Percurso passo-a-passo do checklist (20 min)
3. Exemplos práticos (Task-011, Issue-64) (20 min)
4. Dúvidas + Q&A (10 min)

**Para:** Todos os developers, squad leads, arquiteto

**Frequência:** Kickoff de Sprint ou quando novo membro

---

## 📚 Referências

- [DOCS_INDEX.md](DOCS_INDEX.md) — Guia da estrutura mínima
- [C4_MODEL.md](C4_MODEL.md) — Arquitetura (4 níveis)
- [ADR_INDEX.md](ADR_INDEX.md) — Decisões técnicas
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) — Regras operacionais
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) — Esquemas
- [DIAGRAMAS.md](DIAGRAMAS.md) — Classes + ER Model
- [SYNCHRONIZATION.md](SYNCHRONIZATION.md) — Audit trail [SYNC]
