---
name: "Project Agents Registry"
description: "Registro centralizado de agentes customizados disponíveis no projeto"
---

# Agentes Customizados — Registro do Projeto

Este arquivo documenta todos os agentes customizados disponíveis no projeto crypto-futures-agent.

## Agentes Disponíveis

### 1. Agent: Product Owner (`.github/skills/2.product-owner/SKILL.md`)

**Descrição**
Prioriza itens do backlog com score simples. Transforma demanda bruta em
handoff estruturado para o Solution Architect.

**Entrada**
- Lista de issues/backlog
- Critérios de priorização (impacto, risco, dependências)

**Saída**
- Prompt executável para Solution Architect

**Acionamento**
- Via slash command `/product-owner` ou invocação direta
- User-invocable: ✅ Sim

---

### 2. Agent: Solution Architect (`.github/skills/3.solution-architect/SKILL.md`)

**Descrição**
Refina demanda do PO em requisitos técnicos, arquitetura, modelagem de dados
e plano de entrega. Emite handoff estruturado para QA-TDD.

**Entrada**
- Handoff do Product Owner com objetivo, escopo, restrições
- Referência de backlog (opcional)

**Saída**
- Prompt executável para QA-TDD

**Acionamento**
- Invocado automaticamente pelo Product Owner
- Via slash command `/solution-architect` ou invocação direta
- User-invocable: ✅ Sim

**Guardrails**
- Nunca propor bypass de `risk_gate` ou `circuit_breaker`
- Manter idempotência por `decision_id`
- Modo conservador em ambiguidade operacional

---

### 3. Agent: QA - TDD (`.github/agents/4.qa-tdd.agent.md` + `.github/skills/4.qa-tdd/SKILL.md`)

**Descrição**
Escreve testes unitários orientados a requisitos (Red Phase), atualiza backlog
e gera prompt executável para Software Engineer implementar com TDD.

**Entrada**
- Prompt estruturado do Solution Architect
- Requisitos funcionais/não-funcionais verificáveis
- Componentes/módulos afetados
- Invariantes obrigatórios (risk_gate, circuit_breaker, decision_id)

**Saída**
- Suite completa de testes (RED phase — testes que falham)
- Atualização de `docs/BACKLOG.md`
- Prompt executável para Software Engineer

**Acionamento**
- Invocado automaticamente pelo Solution Architect
- Via slash command `/qa-tdd` ou invocação direta
- User-invocable: ✅ Sim

**Responsabilidades**
1. Escrever testes unitários que falham inicialmente
2. Validar cobertura 100% de requisitos
3. Atualizar backlog com status `TESTES_PRONTOS`
4. Gerar prompt para Software Engineer contendo:
   - Suite completa de testes
   - Contexto de requisitos
   - Guardrails de risco
   - Plano Green-Refactor

**Guardrails**
- Nunca mockear `risk_gate` ou `circuit_breaker`
- Preservar `decision_id` idempotência
- Cada teste = um requisito
- Nomenclatura: `test_<funcionalidade>_<condicao>_<resultado>`

---

### 4. Agent: Software Engineer (Futura — Stage 5)

**Status**: Planejado
**Descrição**: Implementará código conforme TDD (Red → Green → Refactor)
**Entrada**: Prompt do QA-TDD
**Saída**: Código implementado + evidência de testes verdes

---

### 5. Agent: QA-Live (Futura — Stage 8)

**Status**: Planejado
**Descrição**: Validará qualidade, risco e decidirá GO/NO-GO para live
**Entrada**: Relatório do engenheiro de software
**Saída**: Decisão GO | GO_COM_RESTRICOES | NO_GO

---

## Workflow Integrado

```
Product Owner
    │
    ├─→ [/product-owner] Prioriza backlog
    │
    └─→ Emite handoff
         │
         ├─→ Solution Architect
              │
              ├─→ [/solution-architect] Refina requisitos
              │
              └─→ Emite prompt para QA-TDD
                   │
                   ├─→ QA - TDD
                        │
                        ├─→ [/qa-tdd] Escreve testes (RED phase)
                        ├─→ Atualiza docs/BACKLOG.md
                        │
                        └─→ Emite prompt para Software Engineer
                             │
                             ├─→ Software Engineer (FUTURO)
                                  │
                                  ├─→ Implementa (GREEN → REFACTOR)
                                  └─→ Evidência de testes verdes
                                       │
                                       └─→ QA-Live (FUTURO)
                                            │
                                            └─→ Decisão GO/NO-GO
```

## Como Invocar um Agente

### Via Slash Command

```text
/product-owner <contexto ou paste de issue>
/solution-architect <paste do handoff do PO>
/qa-tdd <paste do handoff do SA>
```

### Via Subagent (Programaticamente)

```python
# Dentro de um skill ou agent
from tools import runSubagent

resultado = runSubagent(
    agentName="qa-tdd",
    prompt="Aqui vai o prompt do Solution Architect...",
    description="Escrever testes para feature X"
)
```

## Convenções de Arquivo

| Tipo | Localização | Convenção |
|------|---|---|
| Agent Definition | `.github/agents/<num>.<name>.agent.md` | YAML frontmatter + markdown |
| Skill | `.github/skills/<num>.<name>/SKILL.md` | YAML frontmatter + markdown |
| Integration Instructions | `.github/instructions/<name>.instructions.md` | YAML frontmatter + markdown |
| Prompt | `.github/prompts/<name>.prompt.md` | YAML frontmatter + markdown |

## Manutenção

### Quando Adicionar um Novo Agente

1. Crie arquivo em `.github/agents/<num>.<name>.agent.md`
2. Defina frontmatter YAML com `name`, `description`, `user-invocable`
3. Documente responsabilidades, entrada, saída e guardrails
4. Registre em `AGENTS.md` (este arquivo)
5. Atualize `docs/SYNCHRONIZATION.md` com tag `[SYNC]`

### Quando Atualizar um Agente

1. Modifique arquivo `.agent.md` ou `SKILL.md` correspondente
2. Se mudou responsabilidades/fluxo, atualize `AGENTS.md`
3. Atualize `docs/SYNCHRONIZATION.md` com tag `[SYNC]`

## Referência Rápida

- **Frontmatter YAML**: Veja qualquer arquivo em `.github/agents/` ou `.github/skills/`
- **Padrão handoff entre agentes**: `.github/instructions/qa-tdd-integration.instructions.md`
- **Exemplo completo**: Leia `.github/skills/4.qa-tdd/SKILL.md`

---

**Última atualização**: 2026-03-22
**Alterações mais recentes**: Criação de agente QA-TDD (stage 4) com integrações.
