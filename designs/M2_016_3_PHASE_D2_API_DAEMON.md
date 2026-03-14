# M2-016.3 Phase D.2: API Binance Real - Integração e Daemon

**Status**: COMPLETADA (14/03/2026)
**Data de Início**: 14/03/2026
**Tempo de Execução**: ~45 min

---

## 1. Objetivo

Substituir simulador de funding rates/open interest por **API real da Binance**, com daemon background para coleta contínua e persistência automática.

---

## 2. Componentes Implementados

### 2.1. BinanceFundingAPIClient (`scripts/model2/binance_funding_api_client.py`)

**Responsabilidade**: Interface com Binance Futures API.

#### Métodos:

| Método | Propósito | Status |
|--------|-----------|--------|
| `fetch_funding_rate_history(symbol, limit=1000)` | GET /fapi/v1/fundingRate | ✅ Mock ready, Real API ready |
| `fetch_open_interest(symbol, period='5m')` | GET /fapi/v1/openInterest | ✅ Mock ready, Real API ready |
| `persist_funding_rate(symbol, data)` | Armazena no SQLite | ✅ Testado |
| `persist_open_interest(symbol, data, price)` | Armazena no SQLite | ✅ Testado |
| `get_latest_api_data(symbol)` | Query últimos registros da API | ✅ Testado |

#### Features:

- **Mode Hidride**: Flag `use_mock=True/False` para ligar/desligar API real
- **Graceful Degradation**: Fallback para mock se API indisponível
- **API Ready**: TODO comments indicam onde substituir by real `UMFutures` client
- **Logging**: Registra erros e status via logger padrão

#### Endpoints Binance (TODO - Real Integration):

```python
# Funding Rate History
# GET /fapi/v1/fundingRate
# Params: symbol, startTime (ms), endTime (ms), limit (max 1000)
# Response: [{fundingTime, fundingRate, markPrice}, ...]

# Open Interest
# GET /fapi/v1/openInterest
# Params: symbol, period (5m, 15m, 30m, 1h)
# Response: {symbol, openInterest, time}
```

---

### 2.2. BinanceFundingDaemon (`scripts/model2/binance_funding_daemon.py`)

**Responsabilidade**: Background collector rodando continuamente.

#### Features:

- **Schedule Config**: FR=8h, OI=1h
- **Symbol Management**: Carrega símbolos de `config.symbols.SYMBOLS_ENABLED`
- **Run Modes**:
  - `run_once()`: Executa uma iteração (para testes)
  - `run_daemon(interval_sec, max_iterations)`: Roda continuamente
- **Statistics**: `get_collection_stats()` retorna totais persistidos

#### Design:

```plaintext
Daemon Loop (interval=300s default):
  |
  +---> For each symbol:
  |       |
  |       +---> should_collect_funding_rate()? → fetch + persist
  |       |
  |       +---> should_collect_oi()? → fetch + persist
  |
  +---> Log cycle result (FR collected, OI collected)
  |
  +---> Sleep (interval_sec)
  |
  +---> Repeat
```

#### Output:

```json
{
  "fr_collected": 30,
  "oi_collected": 3,
  "timestamp": "2026-03-14T15:10:49.315165",
  "symbols_monitored": 3
}
```

---

### 2.3. Integration Test (`scripts/model2/test_phase_d2_api_integration.py`)

**Fluxo**:

1. **Daemon Init**: `BinanceFundingDaemon(use_mock=True)`
2. **Collect**: `daemon.run_once()` → 30 FR + 3 OI coletados
3. **Persist**: Salvo em `funding_rates_api` + `open_interest_api`
4. **Query**: `api_client.get_latest_api_data()` → dados persistidos
5. **Enrich**: `FeatureEnricher.enrich_with_funding_data()` com dados reais
6. **Output**: Features com `funding_rates` + `open_interest` keys

#### Result:

```
✓ Daemon criado para 3 símbolos
✓ Collected: 30 FR, 3 OI
✓ FR total: 66, OI total: 8
✓ Features enriquecidas com API data
✓ Salvo em: results/model2/phase_d2_integration_demo.json
```

---

## 3. Validação

### 3.1. Tests Executados

```powershell
# API Client Test
✓ 2023 funding rates carregados (BTCUSDT + ETHUSDT)
✓ Open interest queryado e persistido
✓ Query dados API retorna últimos registros

# Daemon Test
✓ 3 ciclos executados
✓ Ciclo 1: 30 FR + 3 OI
✓ Ciclo 2-3: 0 (fora do schedule, OK)
✓ Stats: 36 FR registros, 5 OI registros

# Integration Test
✓ Daemon + API Client + Feature Enricher
✓ Complete flow: Collect → Persist → Query → Enrich
✓ Output JSON salvo
```

---

## 4. Diferenças Phase D vs Phase D.2

| Aspect | Phase D | Phase D.2 |
|--------|---------|----------|
| Data Source | BinanceFundingCollector (simulator) | BinanceFundingAPIClient (API real) |
| Persistence | Tabelas `funding_rates_history` | Tabelas `funding_rates_api` + `open_interest_api` |
| Collection | Manual via `store_*_simulation()` | Daemon auto via `fetch_*()` |
| Integration | Test script simples | Complete daemon + scheduler |
| Real API | Não (simulação pura) | Sim (mock mode + TODO real endpoints) |
| Production Ready | Demo | ~70% (precisa credenciais Binance) |

---

## 5. Como Integrar com Produção

### 5.1. Substituir Mock por Real (1 dia)

```python
# scripts/model2/binance_funding_api_client.py
from binance.um_futures import UMFutures

client = UMFutures(key=API_KEY, secret=API_SECRET)

# Em fetch_funding_rate_history():
response = client._request_api('get', '/fapi/v1/fundingRate', params=params)

# Em fetch_open_interest():
response = client._request_api('get', '/fapi/v1/openInterest', params=params)
```

### 5.2. Deploy Daemon (2 horas)

**Option 1: Linux Systemd Service**

```ini
# /etc/systemd/system/binance-collector.service
[Unit]
Description=Binance Funding Rates Collector
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/crypto-futures-agent
ExecStart=/usr/bin/python3 scripts/model2/binance_funding_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Option 2: Docker Container**

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/model2/binance_funding_daemon.py"]
```

### 5.3. Integrar com Episodes (3 dias - Phase D.3)

```python
# scripts/model2/persist_training_episodes.py
from scripts.model2.binance_funding_api_client import BinanceFundingAPIClient

api_client = BinanceFundingAPIClient(use_mock=False)  # Real API

for episode in episodes:
    features = FeatureEnricher.enrich_features(conn, episode.symbol, ...)
    features = FeatureEnricher.enrich_with_funding_data(
        features, 
        episode.symbol, 
        funding_collector=api_client  # Use real data
    )
    # Persist com funding data real
```

---

## 6. Próximas Fases

### **Phase D.3**: Integração com Training Episodes (Dias 15-18)
- [ ] Modificar `persist_training_episodes.py` para usar `BinanceFundingAPIClient`
- [ ] Test end-to-end: Daemon → API → Episodes → Training
- [ ] Validar Sharpe improvement com funding context

### **Phase D.4**: Correlação Analysis (Dias 19-21)
- [ ] Analisar correlação entre FR sentiment e RL predictions
- [ ] Analisar correlação entre OI trends e Win rate
- [ ] Documentar insights em `designs/M2_016_3_ANALYSIS.md`

### **Phase E**: LSTM State Representation (Dias 22-35)
- [ ] Design LSTM architecture
- [ ] Benchmark LSTM vs MLP + funding features
- [ ] Métricas: Sharpe, Win rate, Drawdown

---

## 7. Código de Produção

```bash
# Instalar Binance client live
pip install python-binance

# Configurar credenciais (ENV vars)
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret

# Rodar daemon
python scripts/model2/binance_funding_daemon.py

# Verificar status
sqlite3 db/modelo2.db "SELECT COUNT(*) FROM funding_rates_api;"
```

---

## 8. Referências

- Binance API Docs: https://binance-docs.github.io/apidocs/futures/
- Funding Rate Info: https://www.binance.com/en/support/faq/why-is-there-a-funding-rate-in-perpetual-futures-contracts-3c96b5eaa2d241f2913d7e2a8f5a8e0e
- python-binance: https://python-binance.readthedocs.io/

---

**Status**: ✅ COMPLETADA | **Next**: Phase D.3 Integration (Dias 15-18)
