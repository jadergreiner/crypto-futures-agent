# 📚 Índice de Documentação — Estrutura Mínima

**Versão:** 0.1.0
**Data:** 07 MAR 2026
**Responsável:** Doc Advocate, Arquiteto

---

## 🎯 Objetivo

Manter **integridade referencial** da documentação através de uma estrutura mínima consolidada. Cada task entregue/avaliada deve observar esta estrutura e mapear seus impactos.

---

## 📊 ESTRUTURA MÍNIMA OBRIGATÓRIA

Ciclo fechado de documentação técnica e de negócio:

| # | Pilar | Documento | Propósito | Owner |
|---|-------|-----------|----------|-------|
| **1** | **ARQUITETURA** | [C4_MODEL.md](C4_MODEL.md) | Diagrama completo do projeto (4 níveis: Context, Containers, Components, Code) | Arquiteto (#6) |
| **2** | **DECISÕES TÉCNICAS** | [ADR_INDEX.md](ADR_INDEX.md) | Registro de 7+ decisões técnicas críticas com contexto, decisão e consequências | Arquiteto (#6) |
| **3** | **REGRAS DE NEGÓCIO** | [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) | Regras operacionais em linguagem não-técnica (risk, trading, gestão de capital) | Business Analyst |
| **4** | **MODELAGEM DE DADOS** | [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) | Entidades, relacionamentos, fluxos de dados, schemas (SQLite + Parquet) | Arquiteto (#6), Data (#11) |
| **5** | **DIAGRAMA DE CLASSES** | [DIAGRAMAS.md](DIAGRAMAS.md) — Seção 1 | Estrutura OOP dos módulos críticos (Agent, Environment, Executor, Risk Manager) | Arquiteto (#6) |
| **6** | **DIAGRAMA DE DADOS** | [DIAGRAMAS.md](DIAGRAMAS.md) — Seção 2 | ERD (Entity Relationship Diagram) para SQLite + Parquet snapshots | Data (#11) |

---

## 🔄 PROTOCOL DE AVALIAÇÃO

Para garantir **integridade referencial em cada task**, use:

📋 **[PROTOCOL_TASK_EVALUATION.md](PROTOCOL_TASK_EVALUATION.md)**
- Checklist obrigatório para toda entrega
- Exemplos de aplicação (Task-011, Issue-64)
- Integração com GitHub PR + Board
- Matriz de verificação rápida

---

## 🚀 Próximos Passos

- [ ] **Sprint 3+**: Aplicar protocol em todas as tasks
- [ ] **Week 1**: Treinar squad no protocol (1h workshop)
- [ ] **Week 2**: Adicionar checklist em GitHub PR template
- [ ] **Week 3**: Integrar validação em pipeline CI/CD (lint + cross-refs)
- [ ] **Contínuo**: Atualizar SYNCHRONIZATION.md ao cada [SYNC] commit

---

## ✅ PROTOCOL: Avaliação de Tasks

Toda task entregue ou avaliada deve:

1. **[ ] Mapear Impacto na Arquitetura**
   - Novo módulo? → Atualizar C4_MODEL.md nível 3 (Components)
   - Novo container? → Atualizar C4_MODEL.md nível 2

2. **[ ] Registrar Decisão Técnica**
   - Decisão de design novo? → Criar novo ADR em ADR_INDEX.md

3. **[ ] Validar Regras de Negócio**
   - Muda lógica de risk/trading? → Atualizar REGRAS_DE_NEGOCIO.md
   - Impacta capital, posições, drawdown? → Registrar em REGRAS_DE_NEGOCIO.md

4. **[ ] Atualizar Modelagem**
   - Nova entidade/tabela? → Atualizar MODELAGEM_DE_DADOS.md
   - Novo fluxo de dados? → Desenhar diagrama atualizado

5. **[ ] Atualizar Diagramas**
   - Novo serviço/classe? → Atualizar DIAGRAMAS.md seção Classes
   - Novo schema/relacionamento? → Atualizar DIAGRAMAS.md seção Dados

6. **[ ] Commit com Tag [SYNC]**
   - Todas as mudanças docs com `[SYNC] Descrição breve`
   - Registrar em SYNCHRONIZATION.md

---

## 📌 Documentos ADICIONAIS (Estratégicos)

Complementam a estrutura mínima:

| Documento | Propósito |
|-----------|----------|
| [BACKLOG.md](BACKLOG.md) | Source of truth para tasks e sprints |
| [ROADMAP.md](ROADMAP.md) | Timeline Now-Next-Later |
| [FEATURES.md](FEATURES.md) | Feature list completa (F-H1 → F-ML3) |
| [USER_STORIES.md](USER_STORIES.md) | Requisitos funcionais (US-01 → US-08) |
| [DECISIONS.md](DECISIONS.md) | Decisões executivas do board |
| [RELEASES.md](RELEASES.md) | Versionamento e deliverables |
| [USER_MANUAL.md](USER_MANUAL.md) | Setup, operação, deploy |

---

## 🚀 Próximos Passos

- [ ] Task: Validar completude de documentação da Estrutura Mínima
- [ ] Task: Treinar squad em Protocol de Avaliação de Tasks
- [ ] Task: Integrar checklist de Impacto no template de PR
