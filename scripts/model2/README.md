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
