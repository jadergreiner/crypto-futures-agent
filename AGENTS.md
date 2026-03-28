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
`PO:` com frase obrigatoria de sucesso e foco em valor real capturado via
operacao do `iniciar.bat`.

**Entrada**
- Lista de issues/backlog
- Critérios de priorização (impacto, risco, dependências)
- Contexto operacional/evidencias de execucao do `iniciar.bat`

**Saída**
- Atualizacao de `docs/BACKLOG.md` no item priorizado (`Em analise` + `PO:`)
- Bloco explicito: "Qual o valor real capturado pela operacao em iniciar.bat?"
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
- APROVADO: atualiza backlog para `REVISADO_APROVADO` + `TL:`
     e gera prompt para Doc Advocate
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
6. Em caso APROVADO, emitir prompt executável para `7.doc-advocate`

**Guardrails**
- Decisão binária: APROVADO ou DEVOLVIDO (sem aprovação parcial)
- Guardrail ausente → DEVOLVIDO automático
- Nunca aprovar sem reprodução local dos testes
- Fail-safe: em dúvida sobre risco → DEVOLVIDO

---

### 7. Agent: Doc Advocate (`.github/agents/7.doc-advocate.agent.md` + `.github/skills/7.doc-advocate/SKILL.md`)

**Descrição**
Guardião da governança de documentação em `docs/` na etapa final.
É acionado somente após aprovação do Tech Lead para revisar e atualizar
docs existentes sem criar documentação nova.

**Entrada**
- Prompt estruturado do Tech Lead com decisão `APROVADO`
- Lista de impactos documentais da task
- Evidências mínimas da implementação aprovada

**Saída**
- Revisão/atualização de docs existentes em `docs/`
- Registro `[SYNC]` em `docs/SYNCHRONIZATION.md`
- Relatório executivo acionável para o agente `8.project-manager`

**Acionamento**
- Invocado automaticamente pelo Tech Lead quando APROVADO
- Via slash command `/doc-advocate` ou invocação direta
- User-invocable: ✅ Sim

**Guardrails**
- Não criar novos arquivos em `docs/`
- Não executar etapa final de docs sem aprovação do Tech Lead
- Em ambiguidade documental, ser conservador e registrar pendência

---

### 8. Agent: Project Manager (`.github/agents/8.project-manager.agent.md` + `.github/skills/8.project-manager/SKILL.md`)

**Descrição**
Valida a atividade ponta-a-ponta e decide o `ACEITE` final para fechamento.
Executa ajustes finais quando necessário, atualiza backlog para `CONCLUIDO`,
realiza commit/push para `main` e garante árvore local limpa.

**Entrada**
- Relatório executivo do Doc Advocate
- Evidências de documentação sincronizada
- Status atual da atividade no backlog

**Saída**
- Decisão final: `ACEITE` ou `DEVOLVER_PARA_AJUSTE`
- Backlog atualizado para `CONCLUIDO` (quando ACEITE)
- Commit e push para `main`
- Confirmação de árvore local limpa

**Acionamento**
- Invocado automaticamente pelo Doc Advocate
- Via slash command `/project-manager` ou invocação direta
- User-invocable: ✅ Sim

**Guardrails**
- Não emitir ACEITE sem validar trilha completa da demanda
- Não fechar atividade sem atualizar backlog para `CONCLUIDO`
- Não encerrar com árvore local suja
- Em dúvida de conformidade: DEVOLVER para ajuste

---

### 9. Agent: QA-Live (Futura — Stage 9)

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
                             │              ├─→ Emite prompt para Doc Advocate
                             │              │
                             │              └─→ DEVOLVIDO → Prompt para Software Engineer
                             │                   │
                             │                   └─→ (loop de revisão)
                             │
                             └─→ Doc Advocate
                                  │
                                  ├─→ [/doc-advocate] Governança final de docs
                                  ├─→ Atualiza docs existentes + [SYNC]
                                  └─→ Emite relatório executivo para Project Manager
                             │
                             └─→ Project Manager
                                  │
                                  ├─→ [/project-manager] Decisão final de ACEITE
                                  ├─→ Atualiza docs/BACKLOG.md para CONCLUIDO
                                  ├─→ Commit + push para main
                                  └─→ Garante árvore local limpa
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
/doc-advocate <paste do APROVADO do Tech Lead>
/project-manager <paste do relatorio executivo do Doc Advocate>
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

resultado = runSubagent(
     agentName="7.doc-advocate",
     prompt="Aqui vai o APROVADO do Tech Lead com impactos de docs...",
     description="Governanca final de docs da feature X"
)

resultado = runSubagent(
     agentName="8.project-manager",
     prompt="Aqui vai o relatorio executivo do Doc Advocate...",
     description="Aceite final e fechamento da feature X"
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
**Alterações mais recentes**: Doc Advocate passou a emitir relatório executivo
para novo agente Project Manager (stage 8), responsável por aceite final,
fechamento no backlog e publicação em main com árvore limpa.
