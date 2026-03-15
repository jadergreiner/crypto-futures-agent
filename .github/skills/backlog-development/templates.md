---
name: backlog-templates
description: |
  Templates prontos para uso no skill backlog-development.
  Copie para BACKLOG.md e customize.
  Mensagens: sempre ASCII puro (sem acentos, emojis ou chars corrompidos).
---

# Templates: Agente Backlog Development

## Template 1 — Task Completa (Copy/Paste)

Copie e customize com seus dados:

```markdown
### BLID-XXX: [Título Descritivo, bem específico]

**Sprint:** S-N
**Prioridade:** Alta | Média | Baixa
**Status:** Backlog | Planned | In Progress | Done | WontDo
**Assignee:** [nome] ou [indefinido]
**Created:** DD-MMM-YYYY
**Completed:** [vazio até Done] DD-MMM-YYYY

**Descrição (português, 2-3 linhas):**
Resumir o problema/oportunidade que justifica a task.
Por que isso importa para o projeto?
Qual é o contexto técnico?

**Tipo:** Feature | Fix | Docs | Refactor | Investigation | Infrastructure

**Impacto Arquitetural (REVISAR ANTES DE IMPLEMENTAR):**
- [ ] Segue ARQUITETURA_ALVO.md? [SIM/NÃO]
- [ ] Impacta ADRS existentes? [SIM/NÃO, listar ADR-XXX]
- [ ] Impacta DIAGRAMAS.md? [SIM/NÃO]
- [ ] Mudança em schema (MODELAGEM_DE_DADOS.md)? [SIM/NÃO]
- [ ] Nova regra de negócio (REGRAS_DE_NEGOCIO.md)? [SIM/NÃO]

**Critérios de Aceite (DoD):**
- [ ] Implementação funcional + testes pytest >= 95%
- [ ] Docs/comentários atualizadas (docstrings + inline)
- [ ] Commit com tag [FEAT]/[FIX]/[DOCS]
- [ ] Registrado em docs/SYNCHRONIZATION.md
- [ ] Docs Arquiteturais Sincronizados:
  - [ ] ARQUITETURA_ALVO.md atualizado (se evoluiu)
  - [ ] ADRS.md atualizado (novo ou existente?)
  - [ ] DIAGRAMAS.md 100% atualizado (se impactado)
  - [ ] MODELAGEM_DE_DADOS.md 100% atualizado (se impactado)
  - [ ] REGRAS_DE_NEGOCIO.md 100% atualizado (se impactado)
- [ ] [Específico da task] ...

**Dependências:**
- BLID-XXX (descrição breve)
- BLID-YYY (descrição breve)
ou: Nenhuma

**Bloqueadores (se houver):**
- [ ] Aguardando decisão arquitetural (qual ADR?)
- [ ] Aguardando decisão de design
- [ ] Infra (ex: Binance Testnet access)
- [ ] Outro: [descrição]

**Notas Adicionais:**
- Arquivo principal: `agent/xyz.py`
- Impacto: signal_reward.py, risk_manager.py
- Complexidade: M (1-2 dias) | Alta (3-5 dias)
- Risks: [se houver]
```

---

## Template 2 — Mensagem de Commit (Exemplo ASCII Puro)

**IMPORTANTE:** Mensagens DEVEM ser 100% ASCII (sem acentos, emojis, hifens).

**Exemplo RUIM (❌ nao usar):**
```
[FEAT] Implementar EMA dinâmico — melhoria ML2 (ótima performance!)

- Acentos (ã, é, ú)
- Emojis (🚀, ✓)
- Hifens em-dash (—) corrompem em alguns sistemas
```

**Exemplo BOM (✓ usar):**
```
[FEAT] Implementar EMA dinamico - melhoria ML2

Resultado RL: Sharpe aumentou de 1.9 para 2.3.
Task proposta com base em convergencia do agente.

Detalhes:
- Algoritmo ajuste periodo no agent/signal_reward.py
- Backtest 28FEV-14MAR valida melhoria
- Zero risco compliance violations

Relacionado a: BLID-063
```

**Regras:**
- [ ] 72 chars ASCII maximo (1a linha)
- [ ] Sem acentos (acao, decisao, nenhum)
- [ ] Sem emojis (nada de 🚀 ✓ 🎯)
- [ ] Sem hifens em-dash (— vira OeSÇ): use "-" simples
- [ ] Portugues sempre

---

## Template 3 — Relatorio de Progresso (Para SYNC)

```markdown
## [SYNC] DD-MMM-YYYY HH:MM - Milestone Backlog

**Acao Tomada:** [criar | atualizar | mover | sync]
**Tarefas Afetadas:** BLID-XXX, BLID-YYY, ...

**Antes (estado anterior):**
| Task | Status | Sprint | Prx |
|------|--------|--------|-----|
| BLID-X | Planned | S-2 | — |

**Depois (estado novo):**
| Task | Status | Sprint | Prx |
|------|--------|--------|-----|
| BLID-X | In Progress | S-2 | BLID-Y |

**Impacto:**
- [ ] Dependencias desbloqueadas: BLID-A, BLID-B
- [ ] Novas dependencias criadas: nenhuma
- [ ] Docs sincronizadas:
  - docs/TRACKER.md (contadores)
  - docs/ROADMAP.md (progresso)

**Validacao:**
- \u2713 Estrutura: OK
- \u2713 Regras de negocio: OK
- \u2713 Sem ciclos: OK

**Commit Message (ASCII puro):**
```
[TAG] Descricao breve em una-line, max 72 chars ASCII

Sprint: S-N
Tarefas: BLID-XXX, BLID-YYY
Impacto: [breve]
Docs: SYNCHRONIZATION.md registrado
```

---

## Template 4 — Feature Breakdown (Epics)

Use para features grandes que precisam split em sub-tasks:

```markdown
## BLID-XXX: [Feature Grande]

**Sprint:** S-N
**Prioridade:** Alta
**Status:** Planned | In Progress
**Epic:** ML3 / Infrastructure / v0.3

**Descrição:**
Feature grande que será quebrada em 4-5 sub-tasks.
Context + justificativa.

**Subtasks (não usar BLID para sub, usar nomenclatura simples):**

### [1] Setup Infra Base
- [ ] Criar modulo `agent/xyz_base.py`
- [ ] Placeholder classes + docstrings
- **Depe**: Nenhuma
- **Blocker**: Nenhum
- **ETA**: 1 dia

### [2] Core Logic
- [ ] Implementar `agent/xyz_base.py` função principal
- [ ] 95% test coverage
- **Depe**: [1]
- **Blocker**: Decisão de design (ETA: 16-MAR)
- **ETA**: 2 dias

### [3] Risk Validation
- [ ] Checar BLID-047 requisitos
- [ ] Adicionar validações em `risk_manager.py`
- **Depe**: [1], [2]
- **Blocker**: Nenhum
- **ETA**: 1 dia

### [4] Integration Tests
- [ ] E2E test em `backtest/test_xyz_e2e.py`
- [ ] 90% signal improvement vs baseline (se applicável)
- **Depe**: [3]
- **Blocker**: Dados históricos (disponível)
- **ETA**: 2 dias

### [5] Docs + Sign-off
- [ ] Docs em docs/SYNCHRONIZATION.md
- [ ] Update README.md se necessário
- [ ] Code review + merge
- **Depe**: [4]
- **Blocker**: Code review availability
- **ETA**: 1 dia

**Total Estimate:** ~7 dias (com parallelization possível em [2], [3])

**Critical Path:** [1] → [2] → [3] → [4] → [5]

**Risks:**
- Design decision delay em [2]
- Test flakiness em [4]
```

---

## Template 4 — GitHub Issue Sync (Se Usar Issues)

Quando BLID corresponder a GitHub Issue:

```markdown
## BLID-XXX: [Título sync com GitHub Issue #123]

**Sprint:** S-N
**GitHub Issue:** #123
**URL:** https://github.com/jadergreiner/crypto-futures-agent/issues/123

**Descrição:**
[Copiar do GitHub Issue para BACKLOG.md para histórico]

**Critérios de Aceite:**
- [ ] Resolve issue #123 (link automático ao mergear)
- [ ] Teste coverage >= 95%
- [ ] Commit message: "Resolve #123" ou "Fix #123"

**Dependências:**
[listar BLIDs relacionadas]
```

---

## Template 5 — Decisão de Design (Para Design Decisions)

Quando uma task envolve decisão importante:

```markdown
## BLID-XXX: Design Decision — [Título]

**Sprint:** S-N
**ADR:** ADR-00X (se houver)
**Status:** Pending | Approved | Rejected | Superseded

**Contexto:**
Qual é o problema que exige uma decisão?

**Opções Consideradas:**
1. **Opção A** — Pro: X | Con: Y
2. **Opção B** — Pro: X | Con: Y
3. **Opção C** — Pro: X | Con: Y

**Decisão:**
Opção X foi escolhida porque: [justificativa técnica]

**Consequências:**
- Positiva: [A, B]
- Negativa: [C, D]
- Risco: [E]

**Owner:** [nome]
**Approved By:** [nome, data]

**Implementação:**
- BLID-XXX (subtask 1)
- BLID-YYY (subtask 2)

**Revisão Agendada:** DD-MMM-YYYY
```

---

## Template 6 — Investigation Task (Research/Spike)

Para spikes ou investigações que não geram código direto:

```markdown
## BLID-XXX: [Investigation] Avaliar X para Y

**Sprint:** S-N
**Type:** Investigation | Spike
**Status:** Backlog | In Progress | Done
**Owner:** [nome]

**Objetivo:**
Descobrir se X é viável para Y. Resultado esperado: recomendação.

**Perguntas Chave:**
1. É tecnicamente possível?
2. Qual é o esforço estimado?
3. Quais são os trade-offs (performance, complexity, etc)?
4. Há alternativas melhores?

**Critérios de Aceite:**
- [ ] Documento de findings criado em `docs/investigation_[XX].md`
- [ ] Recomendação clara (sim/não/talvez)
- [ ] Evidence (benchmarks, proofs-of-concept)
- [ ] Decision criada em BLID-ZZZ (follow-up)

**Timeline:** ~3-5 dias
**Output:** Documento + recomendação (não código)
```

---

## Template 7 — Blocke

r Resolution

Quando uma task está bloqueada e precisa de ação:

```markdown
### BLID-XXX: [Título task original]

**Status:** Blocked
**Blocked Since:** DD-MMM-YYYY (N days)
**Blocker:** [Descrição clara]

**Owner of Blocker:** [nome/equipe]
**ETA to Unblock:** DD-MMM-YYYY (estimado)

**Workaround Available:** Sim / Não
**Workaround:** [se houver]

**Escalation:**
- [ ] Criada urgência em Slack? (sim/não, data)
- [ ] Reunião de design agendada? (sim/não, data)
- [ ] Fallback plan exists? (sim/não)

**Dependencies (quem aguarda):**
- BLID-AAA
- BLID-BBB

**Next Action:**
[O que fazer para desbloquear?]
Proprietário: [nome]
Deadline: DD-MMM-YYYY
```

---

## Checklist Rápida de Criação

Sempre que criar uma nova task, checklist isto:

```
□ Tem ID (BLID-XXX)?
□ Tem título descritivo (não vago)?
□ Tem Sprint (S-N)?
□ Tem Prioridade (Alta/Média/Baixa)?
□ Tem Status inicial (Backlog)?
□ Tem Descrição (pelo menos 1-2 linhas)?
□ Tem Critérios de Aceite (DoD)?
□ Dependências estão todas em BACKLOG.md?
□ Sem ciclos circulares?
□ Português correto?

═══════════════════════════════════════════════════════════

ANTES DE COMEÇAR A IMPLEMENTAR:

□ Revisei ARQUITETURA_ALVO.md? (Segue?)
□ Revisei ADRS.md? (Conflita com decisão ativa?)
□ Vai impactar DIAGRAMAS.md? (C4, fluxos, SLA?)
□ Vai impactar MODELAGEM_DE_DADOS.md? (Novo schema?)
□ Vai impactar REGRAS_DE_NEGOCIO.md? (Nova regra?)

═══════════════════════════════════════════════════════════

APÓS IMPLEMENTAR:

□ Código funcional + testes pytest >= 95%?
□ Documentação/docstrings atualizadas?
□ ARQUITETURA_ALVO.md atualizado (se evoluiu)?
□ ADRS.md atualizado (novo ADR criado ou existente?)?
□ DIAGRAMAS.md 100% atualizado (se impactado)?
□ MODELAGEM_DE_DADOS.md 100% atualizado (se impactado)?
□ REGRAS_DE_NEGOCIO.md 100% atualizado, linguagem acessível?
□ Commit message com tag [FEAT]/[SYNC]/[DOCS]?
□ Documentação criada/atualizada NASCE COM LINT OK? ✓
   - Rodar: markdownlint *.md docs/*.md
   - Sem erros? Pronto para commit!
□ Registrado em docs/SYNCHRONIZATION.md?
□ Quando concluir: status Done + Completed date?
```

---

## Copy-Paste a Partir Daqui

### Template Mínimo

```markdown
### BLID-: []

**Sprint:** S-
**Prioridade:**
**Status:** Backlog
**Assignee:** [indefinido]

**Descrição:**
[...]

**Critérios de Aceite:**
- [ ] Implementação + testes
- [ ] Docs + commit

**Dependências:** Nenhuma

**Notas:**
[...]
```

### Template Médio (Recomendado)

```markdown
### BLID-: []

**Sprint:** S-
**Prioridade:** Alta | Média | Baixa
**Status:** Backlog
**Assignee:** [nome]

**Descrição:**
Problema/oportunidade breve.
Impacto técnico.

**Critérios de Aceite:**
- [ ] Implementação funcional
- [ ] Testes pytest >= 95%
- [ ] Docs/docstrings atualizadas
- [ ] Commit [TAG]
- [ ] Registrado em docs/SYNCHRONIZATION.md

**Dependências:**
- BLID-X (motivo)
- BLID-Y (motivo)

**Notas:**
- Arquivo main: `agent/xyz.py`
- Complexidade: M (2 dias)
```

Ver também: [SKILL.md](./SKILL.md), [examples.md](./examples.md)
