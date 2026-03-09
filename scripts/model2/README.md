# Scripts do Modelo 2.0

Este diretório contém apenas scripts operacionais do Modelo 2.0.

## Comando de migração

```bash
python scripts/model2/migrate.py up
```

Parâmetros opcionais:

```bash
python scripts/model2/migrate.py up --db-path db/modelo2.db --output-dir results/model2/runtime
```

## Comando de scanner (M2-002)

Execucao completa (le OHLCV/indicadores do banco legado e persiste tese inicial no M2):

```bash
python scripts/model2/scan.py --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/scan.py --timeframe H4 --symbol BTCUSDT --dry-run
```

## Comando de rastreador (M2-003.1)

Transicao de oportunidades `IDENTIFICADA` para `MONITORANDO`:

```bash
python scripts/model2/track.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/track.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de validador (M2-003.2)

Aplicar regras de validacao em oportunidades `MONITORANDO`:

```bash
python scripts/model2/validate.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/validate.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de resolvedor (M2-003.3)

Aplicar regras de invalidacao/expiracao em oportunidades `MONITORANDO`:

```bash
python scripts/model2/resolve.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/resolve.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de painel (M2-004.1)

Materializa snapshot de contagem por estado e tempo medio de resolucao:

```bash
python scripts/model2/dashboard.py
```

Com retencao customizada:

```bash
python scripts/model2/dashboard.py --retention-days 30
```

## Comando de auditoria (M2-004.2)

Materializa snapshot de transicoes com filtros:

```bash
python scripts/model2/audit.py --symbol BTCUSDT --timeframe H4 --limit 200
```

Filtro por `opportunity_id`:

```bash
python scripts/model2/audit.py --opportunity-id 123
```

## Comando de reprocessamento historico (M2-005.2)

Replay deterministico em banco isolado (`db/modelo2_replay.db`):

```bash
python scripts/model2/reprocess.py --timeframe H4 --symbol BTCUSDT --start-ts 1700000000000 --end-ts 1701000000000
```

Por padrao o comando bloqueia replay no banco operacional (`db/modelo2.db`).
Para sobrescrever explicitamente:

```bash
python scripts/model2/reprocess.py --replay-db-path db/modelo2.db --allow-operational-db
```

## Comando de ponte de sinal (M2-006.1)

Gerar sinal padrao para oportunidades `VALIDADA`:

```bash
python scripts/model2/bridge.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/bridge.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de camada de ordem (M2-007.1)

Consumir sinais `technical_signals` em status `CREATED` para decisao de ordem
sem envio real na Fase 1:

```bash
python scripts/model2/order_layer.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/order_layer.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de adaptador para legado (M2-007.2)

Exportar sinais `technical_signals` consumidos para `trade_signals` em dual-write
controlado (sem envio de ordem real):

```bash
python scripts/model2/export_signals.py --symbol BTCUSDT --timeframe H4
```

Execucao em modo dry-run:

```bash
python scripts/model2/export_signals.py --symbol BTCUSDT --timeframe H4 --dry-run
```

## Comando de observabilidade do fluxo de sinais (M2-007.3)

Materializa snapshot de contagens, taxa de exportacao, erros e latencias do fluxo:
`CREATED -> CONSUMED -> exported_to_trade_signals`.

```bash
python scripts/model2/export_dashboard.py
```

Com retencao customizada:

```bash
python scripts/model2/export_dashboard.py --retention-days 30
```

## Comando de pipeline diario ponta a ponta (M2-008.1)

Orquestra as etapas operacionais M2 em sequencia:
`migrate -> scan -> track -> validate -> resolve -> bridge -> order_layer -> export_signals -> export_dashboard`.

Execucao padrao:

```bash
python scripts/model2/daily_pipeline.py --timeframe H4 --symbol BTCUSDT
```

Execucao em modo dry-run (sem export_dashboard):

```bash
python scripts/model2/daily_pipeline.py --timeframe H4 --symbol BTCUSDT --dry-run
```

Continuar execucao mesmo em erro de etapa:

```bash
python scripts/model2/daily_pipeline.py --timeframe H4 --symbol BTCUSDT --continue-on-error
```

## Comando de agendamento do pipeline diario (M2-008.2)

Executa o pipeline M2 em horario fixo diario com lock de concorrencia
e politica de retry para falhas transientes.

Execucao imediata unica (modo operacional):

```bash
python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4 --symbol BTCUSDT
```

Agendamento diario (loop local) as 00:05 UTC:

```bash
python scripts/model2/schedule_daily_pipeline.py --run-at 00:05 --timezone UTC --timeframe H4
```

Com retry customizado e lock stale:

```bash
python scripts/model2/schedule_daily_pipeline.py --once --max-retries 3 --retry-delay-seconds 120 --lock-stale-seconds 21600
```

## Comando de healthcheck do agendamento diario (M2-008.3)

Valida recencia e status do ultimo `model2_daily_schedule_*.json`.
Dispara alerta operacional via exit code (`0=ok`, `1=alert`).

Execucao padrao:

```bash
python scripts/model2/healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok
```

Com comando de alerta customizado em falha:

```bash
python scripts/model2/healthcheck_daily_schedule.py --alert-command "echo [ALERT] model2 schedule healthcheck failed"
```

## Comando de execucao real/shadow (M2-009/M2-011.1)

Cria candidatos em `signal_executions` a partir de `technical_signals` ja
consumidos e, quando `--execution-mode live`, envia entrada `MARKET`.

Execucao em `shadow`:

```bash
python scripts/model2/live_execute.py --timeframe H4 --symbol BTCUSDT --execution-mode shadow
```

Execucao em `live` com whitelist restrita:

```bash
python scripts/model2/live_execute.py --timeframe H4 --symbol BTCUSDT --execution-mode live --live-symbol BTCUSDT
```

## Comando de reconciliacao live (M2-010.1/M2-011.2)

Reconcilia execucoes em `READY|ENTRY_SENT|ENTRY_FILLED|PROTECTED`,
reconstrui protecao ausente e detecta saida manual/externa.

```bash
python scripts/model2/live_reconcile.py --timeframe H4 --symbol BTCUSDT --execution-mode live --live-symbol BTCUSDT
```

## Comando de dashboard live (M2-010.2)

Materializa snapshot de backlog, falhas, latencias e posicoes sem protecao:

```bash
python scripts/model2/live_dashboard.py --retention-days 30
```

## Comando de healthcheck live (M2-010.3)

Valida recencia do ultimo dashboard live e thresholds de risco.
Dispara alerta via exit code (`0=ok`, `1=alert`).

```bash
python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0
```

Com comando de alerta customizado:

```bash
python scripts/model2/healthcheck_live_execution.py --alert-command "echo [ALERT] model2 live healthcheck failed"
```

## Comando de ciclo live (M2-011.3)

Encadeia `live_execute -> live_reconcile -> live_dashboard` no caminho critico
do live, sem depender de `export_signals -> trade_signals`.

```bash
python scripts/model2/live_cycle.py --timeframe H4 --symbol BTCUSDT --execution-mode shadow
```

## Configuracoes de ativacao da Fase 2 (M2-012)

Variaveis de ambiente principais:

1. `M2_EXECUTION_MODE=shadow|live`
2. `M2_LIVE_SYMBOLS=BTCUSDT,ETHUSDT`
3. `M2_MAX_DAILY_ENTRIES=3`
4. `M2_MAX_MARGIN_PER_POSITION_USD=25`
5. `M2_MAX_SIGNAL_AGE_MINUTES=240`
6. `M2_SYMBOL_COOLDOWN_MINUTES=240`
