# Runbook - Operacao M2 (Model-Driven)

## Objetivo

Padronizar a operacao atual do Modelo 2.0 em arquitetura model-driven.

## Modo de operacao

1. `backtest`: validacao offline da politica.
2. `shadow`: decisao do modelo sem ordem real.
3. `live`: decisao do modelo com ordem real e safety envelope.

## Checklist pre-live

1. Preflight sem erro bloqueante.
2. `risk_gate` e `circuit_breaker` ativos.
3. Reconciliacao operacional saudavel.
4. Nenhuma posicao sem protecao.
5. Evidencia minima de auditoria disponivel.

Comando de preflight:

```bash
python scripts/model2/go_live_preflight.py --live-symbol BTCUSDT
```

## Fluxo operacional

1. Construir estado de mercado.
2. Inferir acao do modelo.
3. Validar safety envelope.
4. Executar acao permitida.
5. Reconciliar estado com exchange.
6. Persistir decisao, eventos e episodio.

## Operacao de monitoramento

Monitorar continuamente:

1. latencia de inferencia;
2. taxa de bloqueio por risco;
3. divergencia banco x exchange;
4. posicoes sem protecao;
5. falhas de idempotencia.

## Resposta a incidente

Quando detectar risco critico:

1. bloquear novas entradas;
2. preservar evidencias;
3. reconciliar posicoes e ordens;
4. aplicar mitigacao fail-safe;
5. registrar trilha de incidente.

Referencia de playbook:

1. `.github/skills/m2-incident-response/SKILL.md`

## Retreino governado

1. Coletar episodios em producao.
2. Treinar fora do runtime live.
3. Validar candidato com gate GO/NO-GO.
4. Promover somente quando aprovado.
5. Reverter para versao anterior se degradar.

## Criterios de operacao saudavel

1. Sem erro bloqueante no preflight.
2. Sem execucao duplicada para mesma decisao.
3. Sem posicao aberta sem protecao.
4. Reconciliacao atualizada e auditavel.
5. Logs e artefatos JSON parseaveis.
