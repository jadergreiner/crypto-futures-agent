# Runbook - Operacao M2 (Daily Pipeline e Live)

## Objetivo

Padronizar a operacao do Modelo 2.0 em dois trilhos:

1. Pipeline diario de tese/sinal.
2. Execucao real nativa live/shadow.

## Escopo

Cobertura deste runbook:

1. M2-008.1, M2-008.2 e M2-008.3.
2. M2-009, M2-010, M2-011 e M2-012.

Componentes do pipeline diario:

1. `scripts/model2/daily_pipeline.py`
2. `scripts/model2/schedule_daily_pipeline.py`
3. `scripts/model2/healthcheck_daily_schedule.py`

Componentes do live:

1. `scripts/model2/live_execute.py`
2. `scripts/model2/live_reconcile.py`
3. `scripts/model2/live_dashboard.py`
4. `scripts/model2/healthcheck_live_execution.py`
5. `scripts/model2/live_cycle.py`

Artefatos esperados em `results/model2/runtime/`:

1. `model2_daily_pipeline_*.json`
2. `model2_daily_schedule_*.json`
3. `model2_daily_healthcheck_*.json`
4. `model2_live_execute_*.json`
5. `model2_live_reconcile_*.json`
6. `model2_live_dashboard_*.json`
7. `model2_live_healthcheck_*.json`

## Pre-flight do live

Verificar antes do go-live:

1. Confirmar o banco operacional efetivo:
   `python -c "from config.settings import MODEL2_DB_PATH; print(MODEL2_DB_PATH)"`
2. Validar escrita no path resolvido de `MODEL2_DB_PATH` (necessario para snapshots e reconciliacao):
   `python -c "import sqlite3; from config.settings import MODEL2_DB_PATH as p; c=sqlite3.connect(p); c.execute('BEGIN IMMEDIATE'); c.execute('CREATE TABLE IF NOT EXISTS __perm_test(id INTEGER)'); c.execute('DROP TABLE __perm_test'); c.execute('COMMIT'); c.close(); print('ok', p)"`
3. Se houver erro de permissao no Windows, corrigir ACL da pasta `db/`:
   `cmd /c "icacls db /grant %USERNAME%:(OI)(CI)M /T"`
4. `python scripts/model2/migrate.py up`
5. `M2_EXECUTION_MODE=shadow`
6. `M2_LIVE_SYMBOLS` com subset explicito
7. `M2_MAX_DAILY_ENTRIES` revisado
8. `M2_MAX_MARGIN_PER_POSITION_USD` revisado
9. `M2_MAX_SIGNAL_AGE_MINUTES` revisado
10. `M2_SYMBOL_COOLDOWN_MINUTES` revisado

## Operacao diaria do pipeline

### 1) Execucao do scheduler (once)

Comando recomendado para infraestrutura:

```bash
python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4
```

### 2) Healthcheck pos-execucao

```bash
python scripts/model2/healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok
```

Interpretacao:

1. Exit `0`: operacao saudavel.
2. Exit `1`: alerta operacional.

## Operacao do live

### 1) Ciclo manual recomendado

Staging e entrada:

```bash
python scripts/model2/live_execute.py --timeframe H4 --execution-mode shadow
```

Reconciliacao:

```bash
python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live
```

Dashboard:

```bash
python scripts/model2/live_dashboard.py --retention-days 30
```

Healthcheck:

```bash
python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0
```

### 2) Ciclo combinado

```bash
python scripts/model2/live_cycle.py --timeframe H4 --execution-mode shadow
```

### 3) Sequencia de rollout

1. Rodar em `shadow`.
2. Validar `model2_live_dashboard_*.json` e `model2_live_healthcheck_*.json`.
3. Ativar `M2_EXECUTION_MODE=live` com whitelist restrita.
4. Ampliar `M2_LIVE_SYMBOLS` progressivamente.

## Agendamento recomendado

### Linux (cron)

Exemplo diario em UTC:

```bash
5 0 * * * cd /path/repo && python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4 >> logs/model2_schedule.log 2>&1
10 0 * * * cd /path/repo && python scripts/model2/healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok >> logs/model2_healthcheck.log 2>&1
```

Exemplo de loop live curto:

```bash
*/5 * * * * cd /path/repo && python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live >> logs/model2_live_reconcile.log 2>&1
*/10 * * * * cd /path/repo && python scripts/model2/live_dashboard.py >> logs/model2_live_dashboard.log 2>&1
*/10 * * * * cd /path/repo && python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime >> logs/model2_live_healthcheck.log 2>&1
```

### Windows (Task Scheduler)

Criar tarefas separadas:

1. `schedule_daily_pipeline.py --once --timeframe H4`
2. `healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok`
3. `live_reconcile.py --timeframe H4 --execution-mode live`
4. `live_dashboard.py`
5. `healthcheck_live_execution.py --runtime-dir results/model2/runtime`

## Sinais de incidente

Alertar quando qualquer condicao ocorrer:

1. Nao existe `model2_daily_schedule_*.json` do dia.
2. `status` do ultimo schedule diferente de `ok`.
3. Ultimo dashboard live acima do limite de recencia.
4. `unprotected_filled_count > 0`.
5. `stale_entry_sent_count > 0`.
6. `open_position_mismatches_count > 0`.

## Resposta a incidentes

### Incidente A: sem execucao no dia

1. Verificar logs do host (cron/Task Scheduler).
2. Executar manualmente:

```bash
python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4
```

3. Reexecutar o healthcheck diario.

### Incidente B: entrada enviada e fill nao reconciliado

1. Abrir o ultimo `model2_live_reconcile_*.json`.
2. Confirmar se a execucao esta em `ENTRY_SENT`.
3. Validar ordem/posicao na exchange.
4. Reexecutar:

```bash
python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live
```

### Incidente C: posicao sem protecao

1. Abrir o ultimo `model2_live_dashboard_*.json`.
2. Confirmar `unprotected_filled_count`.
3. Executar reconciliacao imediatamente.
4. Se a protecao nao puder ser recriada, encerrar a posicao manualmente e abrir incidente.

### Incidente D: divergencia Binance x banco

1. Revisar `model2_live_dashboard_*.json` e `model2_live_healthcheck_*.json`.
2. Conferir `signal_executions` e `signal_execution_events` no banco.
3. Conferir ordens abertas, protecoes e posicoes na exchange.
4. Reexecutar `live_reconcile.py`.
5. Se persistir, congelar o rollout (`M2_EXECUTION_MODE=shadow`) ate correção.

## Evidencias minimas por dia

1. `model2_daily_schedule_*.json` com `status=ok`.
2. `model2_daily_healthcheck_*.json` com `status=ok`.
3. `model2_live_dashboard_*.json` atualizado.
4. `model2_live_healthcheck_*.json` com `status=ok`.
5. Logs do host sem falhas criticas.
