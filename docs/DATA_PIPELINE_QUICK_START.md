# ⚡ Data Pipeline — Quick Start

**Role:** Data Engineer (#11) | Status: ✅ Ready for Implementation  
**Last Updated:** 22-FEV-2026 | **Target:** Sprint 2 Backend Integration

---

## 🎯 Objetivo Rápido

Preparar dados históricos de **1 ano × 60 símbolos × 4h candles** (131.400 registros) em cache SQLite local **ANTES** que o módulo SMC (Backtesting) execute.

---

## 📋 Checklist de Setup (30 minutos)

### Passo 1: Diretórios e Schema (5 min)

```bash
# Criar estrutura
mkdir -p data/scripts
mkdir -p config
mkdir -p logs

# Inicializar DB (vazio)
python data/scripts/klines_cache_manager.py --action init --db data/klines_cache.db
```

**Resultado esperado:** `data/klines_cache.db` criado com schema SQLite

### Passo 2: Download de 1 Ano (15-20 min)

```bash
# Full fetch: todas 60 moedas, 365 dias atrás
python data/scripts/klines_cache_manager.py \
  --action fetch_full \
  --db data/klines_cache.db \
  --symbols config/symbols.json

# Monitorar console para rate limits
# Esperar mensagem: "✅ CONCLUSÃO: 60 símbolos em XX.X minutos"
```

**Estimativa:** 88 requisições totais @ <1200 req/min = **15-20 minutos**

**Output:** `data/klines_cache.db` (~650 KB)

### Passo 3: Validação de Integridade (5 min)

```bash
python data/scripts/klines_cache_manager.py \
  --action validate \
  --db data/klines_cache.db

# Verificar relatório
cat data/integrity_report_*.json
```

**Critério de sucesso:** ≥99% candles com `status: PASS`

### Passo 4: Integração com Backtest (2 min)

```python
# File: backtest/test_data_loader.py
from data.scripts.klines_cache_manager import BacktestDataLoader
import pandas as pd

loader = BacktestDataLoader("data/klines_cache.db")
btc_data = loader.load_symbol_range(
    "BTCUSDT",
    start_date=datetime(2025, 2, 22),
    end_date=datetime(2026, 2, 22)
)

assert len(btc_data) > 2000  # Mínimo ~2190 esperado
assert btc_data.dtypes['close'] == 'float32'
print(f"✅ Dados prontos para backtesting: {len(btc_data)} candles")
```

**Se passar:** Pipeline pronto para SMC!

---

## 🔄 Sincronizações Automáticas (Após Setup)

### Daily Sync (todos os dias @ 04:00 UTC)

```bash
# Cron job (recomendado)
0 4 * * * python data/scripts/klines_cache_manager.py --action sync_daily
```

**O que faz:** Verifica último candle armazenado, baixa últimos 7 dias (timeout check)  
**Duração:** < 5 minutos  
**Rate limit impact:** Negligenciável

### Pre-Backtest Sync (4h antes de SMC rodar)

```bash
# Manual antes de executar backtests
python data/scripts/klines_cache_manager.py --action sync_incremental
```

**O que faz:** Atualiza apenas últimos candles abertos  
**Duração:** < 30 segundos  
**Rate limit impact:** Nenhuma

---

## 📊 Monitoramento

### Verificar Status

```bash
# Query rápida do SQLite
sqlite3 data/klines_cache.db \
  "SELECT symbol, COUNT(*) as candles FROM klines GROUP BY symbol;"

# Resultado esperado:
# BTCUSDT|2190
# ETHUSDT|2190
# ...
# Total: 131400 candles
```

### Verificar Últimos Syncs

```bash
sqlite3 data/klines_cache.db \
  "SELECT symbol, sync_type, rows_inserted, status, datetime(sync_timestamp) \
   FROM sync_log \
   ORDER BY sync_timestamp DESC \
   LIMIT 10;"
```

### Relatório Visual

```bash
cat data/klines_meta.json
# Output:
# {
#   "last_full_sync": "2026-02-22T10:45:30Z",
#   "symbols_count": 60,
#   "last_update": "2026-02-22T10:45:30Z"
# }
```

---

## ⚠️ Troubleshooting

### Problema: Requisição toma 429 (Rate Limited)

**Solução:** Script implementa backoff exponencial automático. Não faça ctrl+C!

```
Esperado:
❌ 429 Rate Limited! Backoff 2s (attempt 1)
❌ 429 Rate Limited! Backoff 4s (attempt 2)
✅ Recuperado, continuando...
```

### Problema: Dados faltam ou incompletos

**Solução:** Rodar validação e repair:

```bash
# 1. Identificar símbolo problemático
python data/scripts/klines_cache_manager.py --action validate

# 2. Re-fetch símbolo específico
python data/scripts/klines_cache_manager.py \
  --action fetch_full \
  --symbols config/symbols_single.json  # apenas BTCUSDT
```

### Problema: DB corrompido

**Solução:** Reconstruir do zero

```bash
rm data/klines_cache.db
python data/scripts/klines_cache_manager.py --action init
# Voltar ao Passo 2
```

---

## 📦 Outputs Esperados

Após conclusão:

```
data/
├── klines_cache.db                    ✅ ~650 KB
├── klines_cache_*.parquet             ✅ Backup
├── klines_meta.json                   ✅ {"last_full_sync": "..."}
├── integrity_report_20260222_104530.json  ✅ {
│                                              "BTCUSDT": {
│                                                "status": "PASS",
│                                                "valid": 2190,
│                                                "gaps": []
│                                              }
│                                            }
└── scripts/
    ├── klines_cache_manager.py        ✅ Main orchestrator
    ├── test_data_loader.py            ⏳ Teste de integração
    └── [...outros scripts]
```

---

## 🔗 Próximos Passos

1. **Sprint 2:** Integração com `backtest/data_loader.py`
2. **Sprint 3:** ML preprocessing (normalization, feature engineering)
3. **Go-live:** Validação com dados reais de produção

---

## 👤 Responsabilidade

- **Data Engineer (#11):** Implementação + manutenção
- **SMC Lead:** Consumir via `BacktestDataLoader`
- **DevOps:** Agendar cron jobs para daily/incremental syncs

**Status:** ✅ Pronto para implementação. Aguardando autorização para deploy Sprint 2.
