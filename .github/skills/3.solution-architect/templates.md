---
name: 3.solution-architect-templates
description: |
  Templates fixos para comentario SA no backlog e handoff SA -> QA-TDD.
user-invocable: false
---

# Templates Solution Architect

## 1) Template Fixo de Comentario SA (Backlog)

Formato obrigatorio no rodape do item analisado:

```text
SA: <resumo_em_ate_150_caracteres>
```

Regras:

- Prefixo literal obrigatorio: `SA:`
- Limite maximo: 150 caracteres no resumo
- Linguagem objetiva, sem multiline
- Nao incluir markdown extra, bullets ou tags

Checklist rapido:

1. O item permanece com status `Em analise`.
2. O comentario comeca com `SA:`.
3. O resumo tem no maximo 150 caracteres.

## 2) Bloco Padrao de Handoff SA -> QA-TDD

Nao duplicar template neste arquivo.
Usar o contrato canônico em:
`.github/instructions/qa-tdd-integration.instructions.md`.

Checklist rapido de conformidade antes do envio:

1. `id`, `objetivo`, `escopo_in` e `escopo_out` preenchidos.
2. Requisitos testaveis (sem linguagem vaga).
3. Guardrails explicitos: risk_gate, circuit_breaker, decision_id.
4. Plano Red/Green/Refactor definido.
5. Criterios de aceite mensuraveis.

Resumo operacional:

- Este arquivo contem apenas apoio rapido.
- O contrato SA -> QA-TDD vive somente no arquivo de instruction.

## 3) Regra de Consistencia de Status

Para itens analisados pelo SA, usar somente:

```text
Em analise
```

Nao usar variantes, por exemplo:

- Em análise
- Em Analise
- EmAnalise
