---
name: backlog-examples
description: |
  Exemplos curtos de uso do skill backlog-development.
user-invocable: false
---

# Exemplos

## Criar task a partir de evidencia RL

Prompt:

```text
/backlog-development Criar task para investigar queda de Sharpe de 2.1 para
1.4 nas ultimas 500 epocas
```

Comportamento esperado:

- ler docs/BACKLOG.md
- criar novo BLID sequencial
- sincronizar docs/SYNCHRONIZATION.md se houve escrita oficial

## Atualizar status

Prompt:

```text
/backlog-development Mover BLID-072 para Done e registrar sync
```

Comportamento esperado:

- atualizar apenas o bloco da BLID-072
- nao abrir tabela longa
- registrar sync de forma objetiva

## Consultar sprint

Prompt:

```text
/backlog-development Qual o status atual da sprint S-2?
```

Comportamento esperado:

- responder com resumo curto
- listar no maximo 3 bloqueadores relevantes

## Repriorizar com PRD

Prompt:

```text
/backlog-development Revalidar prioridade da BLID-073 com base no PRD atual
```

Comportamento esperado:

- ler docs/BACKLOG.md e docs/PRD.md
- manter a resposta curta
- sincronizar so se houver mudanca real
