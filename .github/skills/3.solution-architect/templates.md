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

Usar exatamente este bloco no chat apos a analise tecnica:

```text
Voce e o agente QA-TDD desta task.

Contexto da demanda:
- ID/Referencia: <BLID ou referencia>
- Objetivo de negocio: <objetivo>
- Escopo fechado: <o que entra>
- Fora de escopo: <o que nao entra>

Requisitos refinados:
1. <requisito funcional verificavel>
2. <requisito funcional verificavel>
3. <requisito nao funcional verificavel>

Arquitetura e integracao:
- Componentes afetados: <arquivos/modulos>
- Pontos de extensao: <funcoes/classes/interfaces>
- Invariantes obrigatorios: <risk_gate, circuit_breaker, decision_id>

Modelagem de dados:
- Entidades/tabelas afetadas: <lista>
- Alteracoes de schema/contrato: <se houver>
- Compatibilidade retroativa: <sim/nao + condicao>

Plano de implementacao orientado a testes:
1. Escreva primeiro os testes que falham para <comportamento A>.
2. Implemente o minimo para passar os testes de <comportamento A>.
3. Repita ciclo TDD para <comportamento B>.
4. Refatore mantendo todos os testes verdes.

Suite de testes minima obrigatoria:
- Unitarios: <casos>
- Integracao: <casos>
- Regressao/risk: <casos>

Criterios de aceite objetivos:
- [ ] <criterio mensuravel 1>
- [ ] <criterio mensuravel 2>
- [ ] Nenhuma quebra de guardrails de risco.

Comandos de validacao:
- `pytest -q tests/`
- `mypy --strict <modulos alterados>`

Entregaveis esperados:
- Lista de arquivos alterados
- Resumo de risco de regressao
- Evidencia de testes executados e resultado
```

## 3) Regra de Consistencia de Status

Para itens analisados pelo SA, usar somente:

```text
Em analise
```

Nao usar variantes, por exemplo:
- Em análise
- Em Analise
- EmAnalise
