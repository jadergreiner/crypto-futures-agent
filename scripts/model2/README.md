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
