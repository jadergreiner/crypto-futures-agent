# 📊 Pipeline de Dados — Crypto Futures Agent

**Versão:** 1.0.0
**Última atualização:** 22 de fevereiro de 2026
**Responsável:** Data (#11) | Doc Advocate (#17)

---

## 🎯 Objetivo

Pipeline de coleta, validação e cache de dados históricos Binance para
backtesting e suporte à decisão de trading em tempo real.

**Escopo S2-0:**
- Coleta automática de dados OHLCV 1 ano (60 símbolos)
- Cache multi-nível (L1: memória, L2: SQLite, L3: Parquet)
- Validação: sem gaps, duplicatas, preços inválidos
- Mínimo 250 candles por símbolo (timeframe 4H)
- Rate limits Binance respeitados
- Integração com BacktestOrchestrator

---

## 🗂️ Arquitetura — Componentes

### 1. Coletor Principal (`data/collector.py`)

```python
class BinanceDataCollector:
    """Coleta dados OHLCV da Binance REST API com rate limiting"""

    def __init__(self, api_key, api_secret):
        self.client = binance_client(api_key, api_secret)
        self.rate_limiter = RateLimitManager(1200)  # max req/min

    def fetch_ohlcv(self, symbol, interval="4h", limit=250):
        """Busca OHLCV com retry automático"""
        # Rate-limited
        # Retry em 429 (Too Many Requests)
        # Fallback: cache L2
        pass
```

### 2. Gerenciador de Cache (`data/klines_cache_manager.py`)

**Objetivo:** Reduzir latência e respeitar rate limits Binance

**3 Níveis de Cache:**

| Nível | Tecnologia | Latência | Capacidade | TTL     |
|-------|------------|----------|-----------|---------|
| L1    | LRU Memory | <1ms     | 1GB       | Sessão  |
| L2    | SQLite DB  | 10-50ms  | Ilimitado | 24h     |
| L3    | Parquet    | 100-500ms| Ilimitado | ∞       |

**Uso:**

```python
cache = KlinesCacheManager(db_path="data/cache.db")

# Fetch com cache automático (L1 → L2 → L3 → API)
klines = cache.get_klines(
    symbol="BTCUSDT",
    interval="4h",
    limit=250,
)

# Salvar em Parquet para análise offline
cache.export_to_parquet("data/backtest_cache/BTCUSDT_4h.parquet")
```

### 3. Validador (`data/data_loader.py` — `validate_ohlcv`)

Valida cada candle retornado:

- ✅ Timestamp válido (crescente, sem gaps > intervalo)
- ✅ OHLC lógico (open ≤ high, close ≤ high, etc.)
- ✅ Volume > 0
- ✅ Sem duplicatas (unique timestamp)
- ✅ Preços reais (não NaN, não infinito)

**Relatório de Validação:**

```
BTCUSDT:
  - Candles: 250 (válido ✅)
  - Gaps: 0 (válido ✅)
  - Duplicatas: 0 (válido ✅)
  - Período: 2025-02-22 — 2026-02-22 (válido ✅)
  - Status: READY FOR BACKTEST ✅
```

### 4. Configuração de Símbolos (`config/symbols.json`)

Define qual símbolo, intervalo e lookback usar:

```json
{
  "symbols": [
    {"symbol": "BTCUSDT", "interval": "4h", "lookback_days": 365},
    {"symbol": "ETHUSDT", "interval": "4h", "lookback_days": 365},
    {"symbol": "BNBUSDT", "interval": "4h", "lookback_days": 365}
  ]
}
```

---

## ⚙️ Como Usar

### Setup Inicial (15-20 min)

1. **Instalar dependências:**

   ```bash
   pip install python-binance pandas numpy
   ```

2. **Configurar API Binance (testnet ou live):**

   ```bash
   export BINANCE_API_KEY=your_key
   export BINANCE_API_SECRET=your_secret
   ```

3. **Executar coleta inicial:**

   ```bash
   python data/collector.py --symbols BTCUSDT ETHUSDT --interval 4h
   ```

4. **Aguardar cache ser preenchido (5-10 min para 60 símbolos)**

### Validar Dados

```python
from data.data_loader import load_and_validate

# Valida e retorna dados prontos para backtest
df = load_and_validate(
    symbol="BTCUSDT",
    interval="4h",
    min_candles=250,
)
print(f"Candles válidos: {len(df)}")  # Esperado: >= 250
```

### Exportar para Backtesting

```python
from data.klines_cache_manager import KlinesCacheManager

cache = KlinesCacheManager()
cache.export_to_parquet(
    symbol="BTCUSDT",
    output_dir="backtest/cache/",
)

# Uso em BacktestOrchestrator:
from backtest.core.orchestrator import BacktestOrchestrator

orch = BacktestOrchestrator(
    data_provider=ParquetDataProvider("backtest/cache/"),
)
results = orch.run_backtest(strategy, symbols=["BTCUSDT"])
```

---

## 🧪 Testes

Todos os testes estão em `tests/test_data_pipeline.py`:

```bash
# Executar testes
pytest tests/test_data_pipeline.py -v

# Esperado: ✅ 6/6 PASS (100% coverage)
```

**Testes inclusos:**

| Teste | Objetivo | Automatizado? |
|-------|----------|---------------|
| `test_fetch_ohlcv` | Coleta dados Binance sem erro | ✅ Sim |
| `test_rate_limiting` | Rate limiter respeita <1200 req/min | ✅ Sim |
| `test_cache_l2_performance` | SQLite <50ms latência | ✅ Sim |
| `test_validation_gaps` | Detecta gaps em candles | ✅ Sim |
| `test_validation_duplicates` | Detecta duplicatas | ✅ Sim |
| `test_parquet_export` | Salva em Parquet com sucesso | ✅ Sim |

---

## 📋 Critérios de Aceite (S2-0)

Todos os itens abaixo devem estar **✅ PRONTO** para passar no Gate 1:

| Critério | Como testar | Status |
|----------|-------------|--------|
| 250+ candles/símbolo | `pytest test_data_pipeline.py` | 🟡 |
| 0 gaps | Validador OHLCV | 🟡 |
| 0 duplicatas | Validador OHLCV | 🟡 |
| Cache <50ms | Teste de performance | 🟡 |
| Rate limits OK | Logs collector (5 min) | 🟡 |
| Pronto p/ backtest | Integração with orchestrator | 🟡 |

---

## 🔗 Documentação Relacionada

- [PRD.md](../docs/PRD.md) — contexto geral de produto e prioridades
- [CRITERIOS_DE_ACEITE_MVP.md](../docs/CRITERIOS_DE_ACEITE_MVP.md) — S2-0 Gates
- [STATUS_ENTREGAS.md](../docs/STATUS_ENTREGAS.md) — Sprint 2 status
- [Issue #60](https://github.com/crypto-futures-agent/issues/60) — Detalhes técnicos

---

## 🚨 Troubleshooting

### Erro: "429 Too Many Requests"

**Causa:** Rate limiter configurado errado ou muitas requisições simultâneas

**Solução:**

```python
limiter = RateLimitManager(max_requests=1200, window_minutes=1)
limiter.wait_if_needed()  # Bloqueia se necessário
```

### Erro: "Dados com gaps (faltam candles)"

**Causa:** Intervalo não tem 250 candles no período (ex: novo símbolo)

**Solução:** Usar `lookback_days` maior em `config/symbols.json`

### Cache L2 muito grande (SQLite > 5GB)

**Causa:** Muitos símbolos ou alta frequência de coleta

**Solução:** Rotacionar data (mover candles antigos para Parquet L3)

---

## 📞 Contato / Suporte

- **Responsável técnico:** Data (#11)
- **Sincronização docs:** Doc Advocate (#17)
- **Issues:** GitHub [#60](https://github.com/crypto-futures-agent/issues/60)

---

*Documento sincronizado via `[SYNC]` Copilot. Última atualização:
22/FEV/2026.*
