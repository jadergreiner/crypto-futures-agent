---
name: m2-incident-response
description: |
  Responde incidentes do Modelo 2.0 com mitigacao fail-safe.
  Prioriza evidencia minima e reconciliacao auditavel.
metadata:
  tags:
    - incidente
    - live
    - reconciliacao
  focus:
    - economia-de-tokens
    - fail-safe
    - causa-raiz-minima
---

# Skill: M2 Incident Response

## Objetivo

Responder incidentes de execucao no Modelo 2.0 com prioridade para
seguranca operacional, preservacao de capital e trilha de auditoria.

Meta de custo: minimizar leitura e resposta sem perder seguranca.

## Quando usar

Use este skill quando houver sinais como:

- posicao aberta sem protecao;
- divergencia entre banco e exchange;
- ordem duplicada, rejeitada ou com estado inconsistente;
- fill sem atualizacao de `signal_executions`;
- comportamento inesperado em `live_service` ou `live_exchange`.

## Modo Economico

Regra principal: conter risco primeiro e investigar depois, lendo apenas
o necessario para reconciliar o estado.

Ordem de leitura:

1. Ler a evidencia mais direta do incidente: logs, execution_id,
  order_id, simbolo, erro ou diff citado.
2. Ler banco, exchange e eventos apenas na janela UTC e simbolo afetados.
3. Ler codigo apenas no caminho de execucao do sintoma (`core/model2/**`,
  `scripts/model2/**`, `risk/**`).
4. Ler docs somente se necessario para mudanca de processo ou auditoria.

Politica de leitura por tipo:

- Triagem inicial: 1 evidencia + 1 estado de risco atual.
- Reconciliacao: 1 consulta banco + 1 consulta exchange + 1 trilha de evento.
- Correcao localizada: ler apenas arquivo e bloco afetado.
- Pos-incidente: registrar sync apenas se houve mudanca em docs.

Evitar:

- abrir varredura ampla do sistema antes de conter risco
- reler modulos inteiros sem correlacao com o sintoma
- gerar narrativa longa quando bastam evidencias e decisao
- propor mudanca arquitetural ampla para defeito localizado

Regra de parada:

- Quando severidade, escopo e mitigacao estiverem definidos, parar coleta
  adicional e executar reconciliacao/correcao minima.

## Principios

- Seguranca antes de performance.
- Em duvida, falhar fechado e bloquear continuidade.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Registrar o que foi observado, decidido e executado.

## Fluxo Operacional

1. Classificar severidade e escopo minimo: simbolo, execution_id,
  componente e janela UTC.
2. Conter risco imediato antes de aprofundar diagnostico.
3. Coletar evidencias minimas para reconciliar banco, exchange e logs.
4. Manter fluxo bloqueado se houver divergencia critica.
5. Corrigir a causa raiz com mudanca minima e localizada.
6. Validar o fluxo seguro e registrar apenas o que for necessario.

Atalho para casos frequentes:

1. Posicao sem protecao: bloquear fluxo, reconciliar ordens, confirmar SL/TP.
2. Divergencia banco vs exchange: marcar pendente, reconciliar, so depois liberar.
3. Ordem duplicada: travar por idempotencia, auditar `decision_id`, corrigir origem.

## Severidade

- `SEV-1`: risco imediato de perda relevante ou posicao desprotegida.
- `SEV-2`: risco moderado com impacto operacional parcial.
- `SEV-3`: anomalia sem risco imediato, mas com necessidade de correcao.

## Evidencia Minima

- severidade
- componente afetado
- simbolo e `execution_id`, quando houver
- order_id(s) de entrada e protecao, quando houver
- status de posicao, SL/TP e sequencia de eventos
- janela UTC do incidente

Suficiencia minima:

- Se os itens acima estiverem completos, nao expandir investigacao sem motivo.

## Guardrails

- Se houver ambiguidade de estado, manter bloqueio ate reconciliacao.
- Nunca liberar fluxo com posicao potencialmente desprotegida.
- Nunca desabilitar validacoes de risco para "destravar" incidente.
- Priorizar retries, idempotencia e conciliacao antes de qualquer bypass.

## Formato de Resposta

Para economizar tokens, responder em bloco curto:

- Severidade
- Escopo
- Evidencias
- Mitigacao imediata
- Divergencia reconciliada ou pendente
- Causa raiz provavel
- Correcao aplicada ou proposta
- Validacao
- Follow-up, se existir

Limites de saida:

- Triagem: ate 6 linhas.
- Mitigacao + reconciliacao: ate 10 linhas.
- Fechamento com causa raiz: ate 14 linhas.

Nao gerar relatorio longo se o caso couber nesses limites.

## Template Curto

```markdown
- Severidade: SEV-X
- Componente: core/model2/<arquivo>
- Symbol: <SYMBOL>
- Execution ID: <ID>
- Janela UTC: <inicio> -> <fim>
- Exchange: <ordens/posicao>
- Banco: <execucao/eventos>
- Logs: <arquivos>
- <acao 1>
- <acao 2>
- <descricao objetiva>
- <mudanca minima>
- <teste/check>
- <acao futura>
```

## Prompts de Exemplo

```text
Use o skill m2-incident-response para investigar uma posicao sem SL/TP apos
ENTRY_FILLED e proponha mitigacao fail-safe.
```

```text
Aplique o playbook m2-incident-response para reconciliar divergencia entre
signal_executions e ordens da exchange para execution_id 42.
```

## Resultado Esperado

Uma skill de incidente mais barata e previsivel:

- menos leitura ampla e mais leitura direcionada
- menos narrativa e mais decisao operacional
- resposta curta por fase do incidente
- mitigacao fail-safe preservada em todos os cenarios
