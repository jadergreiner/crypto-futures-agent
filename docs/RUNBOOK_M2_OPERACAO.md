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

1. `.github/skills/6.m2-incident-response/SKILL.md`

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

## Procedimento de promocao GO/NO-GO (M2-028)

### Pre-condicoes obrigatorias

1. `risk_gate=ATIVO` e `circuit_breaker=ATIVO` no ambiente alvo.
2. Idempotencia por `decision_id` validada no ciclo atual.
3. Sem incidente critico aberto em reconciliacao.
4. Evidencia minima disponivel para shadow->paper e paper->live.

### Comandos de validacao

```bash
python scripts/model2/go_live_preflight.py --live-symbol BTCUSDT
python scripts/model2/healthcheck_live_execution.py
python scripts/model2/daily_pipeline.py --timeframe M5 --symbol BTCUSDT
python scripts/model2/check_critical_module_coverage.py
pytest -q tests/test_docs_model2_sync.py
```

### Criterios de bloqueio (NO_GO)

1. Preflight com erro bloqueante.
2. Evidencia minima incompleta no gate de promocao.
3. Falha de reconciliacao critica ou protecao ausente.
4. Regressao de benchmark com p95 > 2x baseline por etapa critica.
5. Cobertura critica abaixo de 80% linha ou 70% branch.
6. Ausencia de aprovacao manual para paper->live.

### Acao de rollback e degradacao segura

1. Em NO_GO paper->live: manter operacao em `paper`.
2. Em degradacao de latencia: entrar em modo `degraded`.
3. Em drift/risco nao classificado: bloquear novas entradas.
4. Preservar trilha auditavel com reason_code e timestamp.

### Checklist de evidencia minima para decisao

1. GO/NO-GO shadow->paper com criterios de win_rate, episodios e
   drawdown registrados.
2. GO/NO-GO paper->live com aprovacao manual e reconciliacao validada.
3. Risco dinamico ativo:
   sizing por volatilidade + bloqueio por correlacao.
4. Qualidade ativa:
   benchmark por etapa + gate de cobertura critica por modulo.
5. Evidencia de validacao anexada no backlog e em SYNCHRONIZATION.

## Thresholds de Escalonamento Progressivo (M2-018.3)

Fase 1 — Estreia Conservadora (Ciclos 1-5):

- **M2_EXECUTION_MODE**: live
- **M2_LIVE_SYMBOLS**: BTCUSDT, ETHUSDT, SOLUSDT (3 pares)
- **M2_MAX_MARGIN_PER_POSITION_USD**: 1.0 (risk floor)
- **M2_MAX_DAILY_ENTRIES**: 3 (protetor de overtrading)
- **TRADING_MODE**: live (com orders reais)
- Checklist: preflight OK, healthcheck sem erro, sem posicoes
  abertas sem stop

Fase 2 — Ramp-Up Gradual (Ciclos 6-20):

- Expandir para 5 simbolos (adicionar BNBUSDT, XRPUSDT)
- M2_MAX_MARGIN_PER_POSITION_USD: 5.0 (2% do capital tipo)
- M2_MAX_DAILY_ENTRIES: 5
- Criterio de aprovacao: Sharpe >= 1.5, drawdown < 10%

Fase 3 — Producao Plena (Ciclos 21+):

- Habilitar modo ensemble (modelo RL por simbolo)
- M2_MAX_MARGIN_PER_POSITION_USD: 10.0 (4% do capital)
- M2_MAX_DAILY_ENTRIES: 10 (dinamico por volatilidade)
- Gate de promocao: lucro consecutivo, reconciliacao perfeita

**Reversao de Fase**: Se qualquer criterio violar, retornar para
Fase 1 imediatamente com playbook de incidente

## M2-025.15 - Checklist de troubleshooting documental

Objetivo: conectar sinais operacionais de `iniciar.bat` com a trilha de
governanca documental do pacote M2-025.

Checklist:

1. Confirmar startup recente no `iniciar.bat` via `logs/startup_log.txt`
   contendo modo e simbolos ativos.
2. Confirmar atividade do ciclo em `logs/m2_cycle.log` com timestamp BRT e
   status operacional.
3. Mapear leitura operacional em `docs/ARQUITETURA_ALVO.md` e
   `docs/DIAGRAMAS.md` sem contradicao.
4. Confirmar regras vigentes em `docs/REGRAS_DE_NEGOCIO.md` (incluindo
   guardrails `risk_gate`, `circuit_breaker`, `decision_id`).
5. Confirmar trilha `[SYNC]` em `docs/SYNCHRONIZATION.md` para a M2-025.15.
6. Em ambiguidade documental, aplicar fail-safe: nao promover fechamento sem
   alinhamento entre docs.
