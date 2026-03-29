---
name: 14.production-value-review
description: |
  Avalia se um item do backlog, requisito ou handoff gera valor real,
  perceptivel e auditavel em producao ao executar `iniciar.bat`.
  Use quando Codex precisar validar valor de negocio ou operacional antes de
  priorizar, aprovar, aceitar ou fechar uma task; questiona beneficios
  indiretos, abre discussao quando a evidencia for fraca e escala ao usuario
  humano quando o repositorio nao permitir concluir o valor real.
metadata:
  workflow-track: apoio
  workflow-order: 4
  workflow-stage: 14
  focus:
    - valor-real
    - backlog
    - iniciar-bat
    - producao
    - escalonamento
user-invocable: true
---

# Skill: production-value-review

## Objetivo

Validar se a mudanca proposta altera de forma util e perceptivel o
comportamento do sistema em producao, tomando `iniciar.bat` como entrada
canonica do operador.

Pergunta obrigatoria:

```text
Se este item ficar pronto, o que muda de forma visivel, mensuravel ou
bloqueante quando o operador roda iniciar.bat?
```

Se a resposta nao for objetiva, tratar o valor como nao comprovado ate surgir
evidencia.

## O que conta como valor real

Aceitar valor real somente quando pelo menos um efeito abaixo estiver claro no
caminho `iniciar.bat` -> `daily_pipeline` -> `live_cycle` ->
`persist_training_episodes` -> `healthcheck` -> `operator_cycle_status`:

- o operador enxerga nova informacao acionavel no terminal, log ou artefato;
- uma falha relevante deixa de ocorrer ou passa a ser bloqueada em fail-safe;
- uma degradacao silenciosa vira alerta auditavel;
- uma acao de risco passa a ser impedida antes de causar dano;
- uma etapa manual vira automatizada com ganho perceptivel de tempo ou
  seguranca;
- um simbolo, modo ou trilha antes instavel passa a operar com evidencia
  objetiva.

## O que nao conta sozinho

- refactor sem efeito observavel no runtime;
- teste verde sem impacto no caminho de producao;
- limpeza de codigo sem reduzir risco, erro ou tempo operacional;
- "preparar para o futuro" sem criterio de promocao ou item dependente
  explicito;
- melhoria que existe apenas em dev ou CI e nao muda `iniciar.bat`, logs,
  runtime ou decisao operacional.

## Leitura minima

Ler apenas o necessario para provar ou derrubar a tese de valor:

1. Ler o item do backlog ou handoff.
2. Ler `iniciar.bat`.
3. Ler a evidencia operacional mais direta citada:
   `logs/startup_log.txt`, `logs/m2_cycle.log`,
   `results/model2/runtime/*`, linhas `[M2][SYM]`, preflight ou historico do
   backlog.
4. Ler codigo apenas no trecho que liga a mudanca ao comportamento observado.
5. Ler `docs/RUNBOOK_M2_OPERACAO.md` ou `docs/REGRAS_DE_NEGOCIO.md` somente se
   a interpretacao de regra ou risco ficar ambigua.

## Fluxo

1. Mapear qual etapa do loop `iniciar.bat` o item toca.
2. Descrever o problema atual em linguagem operacional concreta.
3. Explicar qual mudanca visivel o operador deve perceber.
4. Exigir evidencia direta ou cadeia causal curta entre requisito, codigo,
   runtime e percepcao.
5. Classificar o valor:
   - `CONFIRMADO`
   - `PROVAVEL_MAS_NAO_COMPROVADO`
   - `NAO_ENCONTRADO`
   - `SEM_VALOR_PERCEPTIVEL`
6. Se a classificacao nao for `CONFIRMADO`, abrir contestacao antes de aceitar
   o item como bem definido.

## Contestacao obrigatoria

Quando o valor nao estiver claro, questionar o agente virtual com perguntas
diretas. Preferir formulacoes como:

- `Onde exatamente isso aparece para o operador no fluxo do iniciar.bat?`
- `Qual linha de log, status, artefato ou bloqueio muda depois da entrega?`
- `Que falha real deixa de acontecer em producao?`
- `Se a suite ficar verde e nada mudar no terminal, log ou runtime, por que este item continua valioso agora?`
- `O ganho e imediato ou apenas preparatorio? Se for preparatorio, qual item dependente captura o valor final?`

Nao suavizar a lacuna. Declarar explicitamente quando o backlog estiver
vendendo implementacao como se fosse valor.

## Escalonamento

Abrir discussao com o agente virtual quando:

- o item prometer `robustez`, `governanca` ou `qualidade` sem efeito
  observavel;
- o valor depender de suposicoes nao ligadas ao `iniciar.bat`;
- a evidencia apresentada for apenas teste, diff ou `mypy`;
- o item parecer tecnico demais para justificar prioridade de produto sozinho.

Envolver o usuario humano quando:

- houver duas leituras legitimas de valor e a escolha for de negocio, nao
  tecnica;
- a mudanca for preparatoria e so o humano puder dizer se vale entrar agora;
- faltar evidencia de producao e nao houver forma segura de reproduzir;
- a decisao puder esconder custo de oportunidade relevante.

Ao envolver o humano, fazer uma pergunta por vez. Se precisar, usar no maximo
3 perguntas curtas:

1. `Qual comportamento concreto em iniciar.bat precisa melhorar para este item ser considerado valioso?`
2. `Se nada mudar no terminal, log ou status, este item ainda deve seguir agora?`
3. `Este item captura valor final ou apenas prepara outro item? Qual?`

## Saida

Responder em bloco curto e critico:

```text
VALOR_EM_PRODUCAO: <CONFIRMADO | PROVAVEL_MAS_NAO_COMPROVADO | NAO_ENCONTRADO | SEM_VALOR_PERCEPTIVEL>

MUDANCA_PERCEPTIVEL_EM_INICIAR_BAT:
- <o que muda para o operador>

EVIDENCIAS:
- <logs, status, artefatos, regras ou codigo>

LACUNAS_OU_CONTESTACOES:
- <perguntas ou inconsistencias>

DECISAO_RECOMENDADA:
- <prosseguir | redefinir backlog | dividir item preparatorio | escalar ao humano>
```

Se escalar ao humano, adicionar:

```text
DECISAO_PENDENTE_DO_USUARIO:
- <pergunta unica ou ate 3 perguntas curtas>
```

## Guardrails

- Nunca chamar valor de `real` sem efeito observavel, risco reduzido ou
  bloqueio fail-safe no caminho operacional.
- Nunca confundir `teste passou` com `valor comprovado`.
- Nunca aprovar narrativa vaga de backlog sem contestar.
- Em ambiguidade sobre producao, agir de forma conservadora: valor nao
  comprovado.
- Se o item for apenas habilitador, nomear explicitamente o item que captura o
  valor final.
