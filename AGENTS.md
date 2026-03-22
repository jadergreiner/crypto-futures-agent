---
name: "Project Agents Registry"
description: "Registro centralizado de agentes customizados disponíveis no projeto"
---

# Agentes Customizados — Registro do Projeto

Este arquivo documenta todos os agentes customizados disponíveis no projeto crypto-futures-agent.

## Agentes Disponíveis

### 1. Agent: Backlog Development (`.github/agents/1.backlog-development.agent.md` + `.github/skills/1.backlog-development/SKILL.md`)

**Descrição**
Abre o workflow de desenvolvimento organizando e saneando o backlog.
Estrutura itens no `docs/BACKLOG.md` para que o Product Owner possa priorizar.
Não gera prompt executável para o próximo agente.
Não emite recomendação de prioridade; apenas organiza o backlog.

**Entrada**
- Demanda bruta, bug, melhoria ou ajuste de prioridade/status
- Referência de BLID, sprint ou iniciativa (quando existir)

**Saída**
- Backlog atualizado e rastreável em `docs/BACKLOG.md`
- Resumo curto com backlog pronto para priorização do PO

**Acionamento**
- Via slash command `/backlog-development` ou invocação direta
- User-invocable: ✅ Sim

---

### 2. Agent: Product Owner (`.github/agents/2.product-owner.agent.md` + `.github/skills/2.product-owner/SKILL.md`)

**Descrição**
Prioriza itens do backlog com score simples. Transforma demanda bruta em
handoff estruturado para o Solution Architect.
Ao finalizar, marca o item em `Em analise` no backlog e registra comentario
`PO:` com resumo de ate 150 caracteres.

**Entrada**
- Lista de issues/backlog
- Critérios de priorização (impacto, risco, dependências)

**Saída**
- Atualizacao de `docs/BACKLOG.md` no item priorizado (`Em analise` + `PO:`)
- Prompt executável para Solution Architect

**Acionamento**
- Via slash command `/product-owner` ou invocação direta
- User-invocable: ✅ Sim

---

### 3. Agent: Solution Architect (`.github/agents/3.solution-architect.agent.md` + `.github/skills/3.solution-architect/SKILL.md`)

**Descrição**
Refina demanda do PO em requisitos técnicos, arquitetura, modelagem de dados
e plano de entrega. Emite handoff estruturado para QA-TDD.
Ao finalizar, mantem o item em `Em analise` no backlog e registra comentario
`SA:` com resumo de ate 150 caracteres.

**Entrada**
- Handoff do Product Owner com objetivo, escopo, restrições
- Referência de backlog (opcional)

**Saída**
- Atualizacao de `docs/BACKLOG.md` no item analisado (`Em analise` + `SA:`)
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

### 4. Agent: QA - TDD (`.github/agents/4.qa-tdd.agent.md` + `.github/skills/4.qa-tdd/SKILL.md`)

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

### 5. Agent: Software Engineer (`.github/agents/5.software-engineer.agent.md` + `.github/skills/5.software-engineer/SKILL.md`)

**Descrição**
Implementa código Python orientado a testes (TDD Green-Refactor), modelagem
de banco de dados (DBA) e calibração de modelos ML. Atualiza backlog para
`EM_DESENVOLVIMENTO` ao iniciar e para `IMPLEMENTADO` ao concluir.

**Entrada**
- Prompt estruturado do QA-TDD com suite de testes em fase RED
- Requisitos mapeados para testes
- Guardrails e invariantes obrigatórios
- Plano Green-Refactor

**Saída**
- Código implementado com todos os testes passando (GREEN)
- Atualização de `docs/BACKLOG.md` (EM_DESENVOLVIMENTO → IMPLEMENTADO)
- Prompt executável para Tech Lead

**Acionamento**
- Invocado automaticamente pelo QA-TDD
- Via slash command `/software-engineer` ou invocação direta
- User-invocable: ✅ Sim

**Perfis de Expertise**
- DBA: migrações de schema, modelagem `modelo2.db`/`crypto_agent.db`
- Engenheiro Python: tipagem estrita, `mypy --strict`, padrões M2
- Engenheiro ML: treino PPO, Optuna, validação Sharpe/win-rate/drawdown

**Guardrails**
- Nunca desabilitar `risk_gate` ou `circuit_breaker`
- Preservar `decision_id` idempotência
- `mypy --strict` zero erros nos módulos alterados
- Sem credenciais ou hardcode de valores fora de `config/`

---

### 6. Agent: Tech Lead (`.github/agents/6.tech-lead.agent.md` + `.github/skills/6.tech-lead/SKILL.md`)

**Descrição**
Realiza code review da entrega do Software Engineer. Verifica cobertura de
testes, qualidade de código, guardrails de risco e conformidade com requisitos.
Emite decisão binária: APROVADO ou DEVOLVIDO_PARA_REVISAO.

**Entrada**
- Prompt estruturado do Software Engineer com evidências de implementação
- Lista de arquivos alterados e mapeamento requisito → código → teste
- Guardrails verificados e pontos de atenção

**Saída**
- APROVADO: atualiza backlog para `REVISADO_APROVADO` + `TL:` + comunicado final
- DEVOLVIDO: registra `TL:` e gera prompt estruturado para Software Engineer
     com itens detalhados

**Acionamento**
- Invocado automaticamente pelo Software Engineer
- Via slash command `/tech-lead` ou invocação direta
- User-invocable: ✅ Sim

**Responsabilidades**
1. Reproduzir testes localmente (não confiar só no relatório)
2. Revisar código: qualidade, segurança, guardrails de risco
3. Revisar testes: cobertura, estrutura AAA, determinismo
4. Verificar conformidade com `docs/REGRAS_DE_NEGOCIO.md`
5. Atualizar `docs/BACKLOG.md` com decisão final

**Guardrails**
- Decisão binária: APROVADO ou DEVOLVIDO (sem aprovação parcial)
- Guardrail ausente → DEVOLVIDO automático
- Nunca aprovar sem reprodução local dos testes
- Fail-safe: em dúvida sobre risco → DEVOLVIDO

---

### 7. Agent: QA-Live (Futura — Stage 8)

**Status**: Planejado
**Descrição**: Validará qualidade, risco e decidirá GO/NO-GO para live
**Entrada**: Relatório aprovado pelo Tech Lead
**Saída**: Decisão GO | GO_COM_RESTRICOES | NO_GO

---

## Workflow Integrado

```
Backlog Development
    │
    ├─→ [/backlog-development] Organiza docs/BACKLOG.md
    │
    └─→ Backlog pronto para priorizacao
         │
         ├─→ Product Owner
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
                             ├─→ Software Engineer
                             │    │
                             │    ├─→ [/software-engineer] Implementa (GREEN → REFACTOR)
                             │    ├─→ Atualiza docs/BACKLOG.md (EM_DESENVOLVIMENTO)
                             │    │
                             │    └─→ Emite prompt para Tech Lead
                             │         │
                             │         ├─→ Tech Lead
                             │              │
                             │              ├─→ [/tech-lead] Code Review
                             │              ├─→ APROVADO → BACKLOG: REVISADO_APROVADO
                             │              │
                             │              └─→ DEVOLVIDO → Prompt para Software Engineer
                             │                   │
                             │                   └─→ (loop de revisão)
                             │
                             └─→ QA-Live (FUTURO)
                                  │
                                  └─→ Decisão GO/NO-GO
```

## Como Invocar um Agente

### Via Slash Command

```text
/backlog-development <demanda bruta, ajuste de BLID, status ou sprint>
/product-owner <contexto ou paste de issue>
/solution-architect <paste do handoff do PO>
/qa-tdd <paste do handoff do SA>
/software-engineer <paste do prompt do QA-TDD>
/tech-lead <paste do prompt do Software Engineer>
```

### Via Subagent (Programaticamente)

```python
# Dentro de um skill ou agent
from tools import runSubagent

resultado = runSubagent(
    agentName="4.qa-tdd",
    prompt="Aqui vai o prompt do Solution Architect...",
    description="Escrever testes para feature X"
)

resultado = runSubagent(
    agentName="5.software-engineer",
    prompt="Aqui vai o prompt do QA-TDD com suite RED...",
    description="Implementar feature X com TDD Green-Refactor"
)

resultado = runSubagent(
    agentName="6.tech-lead",
    prompt="Aqui vai o prompt do Software Engineer com evidencias...",
    description="Code review da implementacao de feature X"
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
**Alterações mais recentes**: Inclusão do agente Backlog Development (stage 1)
como início do workflow, preparando `docs/BACKLOG.md` para priorização do PO.
