# HANDOFF DO PRODUCT OWNER — M2-ALGO.2

**Para:** 3.solution-architect
**Data:** 2026-04-01
**BLID:** M2-ALGO.2 — Persistir episodios para retreino incremental de ALGOUSDT
**Status backlog:** Em analise

---

## Objetivo de negocio

Garantir que o ciclo shadow de ALGOUSDT gere episodios de treino elegiveis
a cada iteracao, permitindo retreino incremental autonomo sem intervencao
manual. Hoje o contador `pendentes` zera apos cada treino e nunca acumula
os 100 episodios necessarios para o proximo ciclo.

## Evidencia operacional (2026-04-01)

```
Treino: ultimo: 2026-04-01 13:19:35 | pendentes: 0/100 (faltam 100)
eligibility_rule=reward_proxy!=NULL,status_eligivel,label!=context,
created_at>cutoff | cutoff_ms=1775060375951 | timeframe=M5
aud24h: started=3 | running_block=15 | conclusivo=sim
```

## Contexto tecnico

- **Infraestrutura disponivel**: `persist_training_episodes.py` ja possui
  logica de reward counterfactual (BLID-099 CONCLUIDO) e `flush_deferred_rewards`.
- **OHLCV populado**: `ohlcv_m5` para ALGOUSDT carregado via M2-ALGO.1 (CONCLUIDO).
- **Retreino automatico**: BLID-094 CONCLUIDO — maquinaria ativa, mas sem
  episodios elegiveis para alimentar.
- **Eligibility rule**: `reward_proxy!=NULL`, `status != context`,
  `status IN elegivel`, `created_at > cutoff_ms`,
  `symbol='ALGOUSDT'`, `timeframe='M5'`.

## Hipoteses de causa raiz (investigar)

1. `persist_training_episodes.py` nao esta gerando episodios HOLD/counterfactual
   para ALGOUSDT — pode depender de `signal_executions` que ALGOUSDT em shadow
   nunca popula, enquanto os candles M5 estao disponíveis mas o script nao os
   usa para gerar episodios.
2. `flush_deferred_rewards` computa reward mas os episodios ficam com
   `label='context'` (excluidos pela eligibility rule).
3. O `cutoff_ms` avanca a cada treino, invalidando episodios recem-criados
   antes de acumular 100.
4. `rl_training_log_by_symbol` registra ALGOUSDT mas episodios nao trazem
   `symbol='ALGOUSDT'` (fallback para simbolo global).

## Escopo

1. Diagnosticar o fluxo completo: decisao shadow ALGOUSDT →
   `training_episodes` → `flush_deferred_rewards` →
   `collect_training_info_for_symbol`
2. Garantir que cada ciclo shadow ALGOUSDT M5 persiste episodio com
   `reward_proxy != NULL`, `status` elegivel e `label != 'context'`
3. Validar que `flush_deferred_rewards` usa candles de `ohlcv_m5` para
   ALGOUSDT e preenche `reward_proxy` no prazo esperado (T+1 candle M5)
4. Confirmar que `symbol='ALGOUSDT'` e propagado corretamente em
   `persist_training_episodes.py` e no log de treino por simbolo
5. Verificar se `running_block=15` bloqueia acumulo de novos episodios

## Fora do escopo

- Alteracoes em `risk_gate` ou `circuit_breaker`
- Mudancas na arquitetura de retreino (BLID-094 ja entregue)
- Novos timeframes alem de M5 para ALGOUSDT

## Guardrails de risco

- `risk_gate.py` e `circuit_breaker.py` devem permanecer intocados
- Idempotencia por `decision_id` preservada
- Sem regressao em episodios de BTCUSDT e outros simbolos
- `mypy --strict` sem erros nos modulos alterados
- Modo fail-safe: em duvida sobre elegibilidade, registrar como `pending`
  em vez de `context`

## Valor real capturado em iniciar.bat

`pendentes` para ALGOUSDT passa de 0/100 para acumular autonomamente a cada
ciclo shadow, atingindo 100 e disparando retreino confirmado por
`aud24h.conclusivo=sim` e `started` incrementando sem intervencao manual.

---

**PO:** Garantir persistencia de episodios M5 elegiveis para ALGOUSDT no
ciclo shadow, desbloqueando retreino incremental autonomo. Ao fim deste
desenvolvimento estarei feliz se `pendentes` acumular autonomamente ate 100
e o retreino disparar sem intervencao manual para ALGOUSDT.
