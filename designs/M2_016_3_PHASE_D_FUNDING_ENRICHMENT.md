# M2-016.3 Fase D: Enriquecimento de Features - Funding Rates e Open Interest

**Status**: EM_IMPLEMENTAÇÃO
**Data de Início**: 14/03/2026
**Estimativa**: 7-14 dias

---

## 1. Objetivo

Enriquecer episódios de treinamento com dados de **funding rates** e **open interest** da Binance Futures, permitindo que o modelo RL capture dinâmicas de alavancagem e sentimento de mercado.

---

## 2. Componentes Implementados

### 2.1. BinanceFundingCollector (`scripts/model2/binance_funding_collector.py`)

**Responsabilidade**: Coleta, armazenamento e análise de funding rates e open interest.

#### Componentes:
- **`funding_rates_history`**: Tabela SQLite com histórico de funding rates
- **`open_interest_history`**: Tabela SQLite com histórico de OI

#### Métodos Principais:

| Método | Propósito | Output |
|--------|-----------|--------|
| `get_latest_funding_rate(symbol)` | Funding rate mais recente | `{funding_rate, estimated_leverage, timestamp_utc}` |
| `get_latest_open_interest(symbol)` | OI mais recente | `{open_interest, open_interest_usd, market_sentiment}` |
| `estimate_funding_sentiment(symbol, hours)` | Analisa sentiment FR (24h) | `{avg_funding_rate, max_leverage, sentiment, trend}` |
| `estimate_oi_sentiment(symbol)` | Analisa sentiment OI | `{current_oi, sentiment, change_direction}` |
| `get_funding_rate_series(symbol, hours)` | Série histórica FR | Lista `[{timestamp, funding_rate, leverage}, ...]` |

#### Sentimentos:
- **Funding Rate Sentiment**: `'bullish'` (FR < -0.0001) | `'neutral'` (|FR| ≤ 0.0001) | `'bearish'` (FR > 0.0001)
- **OI Sentiment**: `'accumulating'` (OI crescendo) | `'distributing'` (OI diminuindo) | `'neutral'` (OI estável)

#### Simulação:
- `store_funding_rate_simulation()`: Simula dados para teste sem API Binance
- `store_open_interest_simulation()`: Simula datos para teste

---

### 2.2. Integração FeatureEnricher (`scripts/model2/feature_enricher.py`)

**Novo Método**: `enrich_with_funding_data()`

```python
@staticmethod
def enrich_with_funding_data(
    enriched_features: dict,
    symbol: str,
    funding_collector: BinanceFundingCollector = None
) -> dict:
    """Adiciona chaves 'funding_rates' e 'open_interest' ao dict de features."""
```

**Output Esperado**:
```json
{
  "latest_candle": {...},
  "volatility": {...},
  "multi_timeframe_context": {...},
  "funding_rates": {
    "latest_rate": 0.00002,
    "estimated_leverage": 3.5,
    "timestamp_utc": 1773491607204,
    "sentiment_24h": "neutral",
    "avg_rate_24h": 0.0000127,
    "trend": "decreasing"
  },
  "open_interest": {
    "current_oi": 100000.0,
    "oi_usd": 3000000000.0,
    "timestamp_utc": 1773491607204,
    "oi_sentiment": "neutral",
    "oi_change_direction": "stable"
  }
}
```

---

## 3. Fluxo de Integração

```plaintext
Training Episode (banco)
          |
          v
persist_training_episodes.py
          |
          +---> feature_enricher.enrich_features() [Fase A-C]
          |     (ATR, RSI, BB, multi-TF)
          |
          +---> feature_enricher.enrich_with_funding_data() [Fase D]
          |     (Funding rates, OI, sentimentos)
          |
          +---> Salvar features completas em SQLite
          |
          v
Training Dataset (completo)
```

---

## 4. Dados Coletados e Sua Interpretação

### 4.1. Funding Rate (FR)

**O que é**: Taxa de juros paga entre detentores de contratos perpétuos.
- FR positivo = Longs pagam shorts (bullish market)
- FR negativo = Shorts pagam longs (bearish market)

**Uso no RL**:
- Identifica alavancagem-heavy markets (risco elevado)
- Informa sobre liquidação/squeeze risk
- Captura movimento de grandes traders

**Exemplo**:
- BTCUSDT FR = +0.00002 (0.2% dia) → Longs alavancados → Risco de squeeze
- BTCUSDT FR = -0.00001 (shorts dominam) → Ambiente de rally recovery

### 4.2. Open Interest (OI)

**O que é**: Total de contratos abertos (não fechados).

**Uso no RL**:
- OI crescente + preço subindo = Momentum (compradores entrando)
- OI decrescente + preço subindo = Liquidação de shorts (fraco)
- OI extremo = Risco de reversão de volatilidade

**Exemplo**:
- BTCUSDT OI 100K contratos crescendo → Acumulação bullish
- BTCUSDT OI 100K contratos caindo → Distribuição ou squeeze

---

## 5. Validação (Test/Demo)

**Script de Teste**: `scripts/model2/test_phase_d_funding_enrichment.py`

**Resultado**:
```
1. Simulando dados de mercado...
   ✓ 8 funding rates + 4 OI por símbolo armazenados

2. Enriquecendo features com funding data...
   ✓ Features contêm 'funding_rates' e 'open_interest'
   ✓ Sentimentos calculados corretamente

3. Validação:
   ✓ Funding rate atual: 2e-05
   ✓ Sentiment (24h): neutral
   ✓ OI atual: 100000.0
   ✓ OI sentiment: neutral

[OK] Integração Phase D funcionando corretamente
```

---

## 6. Próximos Passos (Fase D.2)

### 6.1. Integrar API Binance Real
```python
# Substituir simulação por API real
from binance.um_futures import UMFutures

client = UMFutures(key=API_KEY, secret=API_SECRET)
funding_rate = client.funding_rate(symbol="BTCUSDT")
open_interest = client.open_interest(symbol="BTCUSDT")
```

### 6.2. Coletor Daemon (Background)
- Coletar funding rates a cada 8h (frequência oficial Binance)
- Coletar OI a cada 1h
- Armazenar em SQLite para análise offline offline

### 6.3. Análise de Correlação
- Correlação entre FR volatilidade e prédições RL
- Correlação entre OI trends e rentabilidade

---

## 7. Contribuição ao Modelo RL

### Antes (Fase A-C):
- Features: OHLCV + ATR + RSI + BB + multi-TF
- **Missing**: Contexto de alavancagem/sentimento

### Depois (Fase D):
- **Adiciona**: Funding rates + OI + sentimentos
- **Impacto esperado**: +5-15% Sharpe ratio (estimado)
- **Uso imediato**: RL pode evitar entry durante high-leverage markets

---

## 8. Roadmap Fase D (Próximos Passos)

| Task | Estimativa | Prioridade |
|------|-----------|-----------|
| Integrar API Binance real `funding_rate()` | 2 dias | ALTA |
| Integrar API Binance real `open_interest()` | 1 dia | ALTA |
| Coletor daemon 8h/1h | 2 dias | MÉDIA |
| Análise correlação FR/OI vs sinais | 3 dias | MÉDIA |
| Tune reward weights (funding impact) | 2 dias | BAIXA |

**Conclusão Fase D**: ~7-10 dias

---

## 9. Referências

- [Binance Funding Rate API](https://binance-docs.github.io/apidocs/futures/en/#funding-rate-history-user_data)
- [Binance Open Interest API](https://binance-docs.github.io/apidocs/futures/en/#open-interest-statistics)
- RL Impact Analysis: `designs/M2_016_3_FEATURE_REWARD_IMPROVEMENTS.md` (Fase D section)
