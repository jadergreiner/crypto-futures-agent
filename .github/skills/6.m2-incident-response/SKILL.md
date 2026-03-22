---
name: m2-incident-response
description: |
  Contem e reconcilia incidentes do Modelo 2.0 em modo fail-safe.
  Prioriza risco atual, evidencias minimas e correcao localizada.
metadata:
  workflow-stage: 6
  focus:
    - fail-safe
    - leitura-minima
    - reconciliacao
user-invocable: true
---

# Skill: m2-incident-response

## Objetivo

Responder incidentes de execucao no Modelo 2.0 com prioridade para
seguranca operacional, preservacao de capital e trilha de auditoria.

Meta de custo: minimizar leitura e resposta sem perder seguranca.

## Quando usar

Use esta skill quando houver sinais como:

- posicao aberta sem protecao;
- divergencia entre banco e exchange;
- ordem duplicada, rejeitada ou com estado inconsistente;
- fill sem atualizacao de `signal_executions`;
- comportamento inesperado em `live_service` ou `live_exchange`.

## Leitura Minima

Regra principal: conter risco primeiro e investigar depois.

Ordem de leitura:

1. Ler a evidencia mais direta do incidente: logs, execution_id,
  order_id, simbolo, erro ou diff citado.
2. Ler banco, exchange e eventos apenas na janela UTC e simbolo afetados.
3. Ler codigo apenas no caminho de execucao do sintoma (`core/model2/**`,
  `scripts/model2/**`, `risk/**`).
4. Ler docs somente se necessario para mudanca de processo ou auditoria.

Evitar varredura ampla, narrativa longa e mudanca arquitetural para defeito
localizado.

## Principios

- Seguranca antes de performance.
- Em duvida, falhar fechado e bloquear continuidade.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Registrar o que foi observado, decidido e executado.

## Fluxo

1. Classificar severidade e escopo minimo: simbolo, execution_id,
  componente e janela UTC.
2. Conter risco imediato antes de aprofundar diagnostico.
3. Coletar evidencias minimas para reconciliar banco, exchange e logs.
4. Manter fluxo bloqueado se houver divergencia critica.
5. Corrigir a causa raiz com mudanca minima e localizada.
6. Validar o fluxo seguro e registrar apenas o que for necessario.

Casos frequentes:

1. Posicao sem protecao: bloquear fluxo e confirmar SL/TP.
2. Divergencia banco vs exchange: reconciliar antes de liberar.
3. Ordem duplicada: travar por idempotencia e auditar `decision_id`.

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

Se os itens acima estiverem completos, nao expandir investigacao sem motivo.

## Guardrails

- Se houver ambiguidade de estado, manter bloqueio ate reconciliacao.
- Nunca liberar fluxo com posicao potencialmente desprotegida.
- Nunca desabilitar validacoes de risco para "destravar" incidente.
- Priorizar retries, idempotencia e conciliacao antes de qualquer bypass.

## Saida

Responder em bloco curto:

- Severidade
- Escopo
- Evidencias
- Mitigacao imediata
- Divergencia reconciliada ou pendente
- Causa raiz provavel
- Correcao aplicada ou proposta
- Validacao
- Follow-up, se existir

Triagem: ate 6 linhas. Fechamento: ate 12 linhas.
