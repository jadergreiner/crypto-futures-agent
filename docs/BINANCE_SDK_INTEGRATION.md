# Integração com SDK Oficial Binance USDS-M Futures

## Resumo das Mudanças

Esta integração substitui as chamadas diretas via `requests` pelo SDK oficial da Binance para USDS-M Futures, trazendo benefícios como:

- ✅ **Tipagem completa** com modelos Pydantic
- ✅ **Suporte nativo** a REST API + WebSocket API + WebSocket Streams
- ✅ **Autenticação integrada** (HMAC + Ed25519)
- ✅ **Rate limits** retornados em cada response
- ✅ **Auto-reconnect** para WebSocket

## Arquivos Modificados

### 1. `requirements.txt`
- Adicionado `binance-sdk-derivatives-trading-usds-futures>=1.0.0`
- Mantido `requests` para coleta de dados macro (auxiliar)

### 2. `config/settings.py`
- Adicionadas configurações para URLs de testnet/produção
- Suporte a autenticação Ed25519 via `BINANCE_PRIVATE_KEY_PATH`
- Configurações de retry: `API_MAX_RETRIES` e `API_RETRY_DELAYS`

### 3. `data/binance_client.py` (NOVO)
- Factory para criação de clientes configurados
- Suporta modos "paper" (testnet) e "live" (produção)
- Detecta automaticamente autenticação HMAC ou Ed25519
- Função helper: `create_binance_client(mode)`

### 4. `data/collector.py`
- Reescrito para usar `DerivativesTradingUsdsFutures.rest_api`
- Mapeamento de intervalos para enums do SDK
- Parsing de respostas Pydantic ou arrays raw
- Validação de dados sem interpolação

### 5. `data/sentiment_collector.py`
- Reescrito para usar endpoints do SDK
- Métodos para: long/short ratio, open interest, funding rate, taker volume
- Tratamento individual de erros em `fetch_all_sentiment()`

### 6. `data/websocket_manager.py`
- Reescrito para usar `DerivativesTradingUsdsFutures.websocket_streams`
- Sistema de callbacks para preços, flash events e liquidações
- Buffer de klines 1m para detecção de flash crash/pump
- Buffer de liquidações 24h para detecção de cascatas

### 7. `.env.example`
- Adicionadas variáveis para autenticação Ed25519
- Documentação de configurações disponíveis

### 8. `data/__init__.py`
- Exporta `BinanceClientFactory` e `create_binance_client`

### 9. `tests/test_binance_sdk_integration.py` (NOVO)
- 19 testes unitários cobrindo:
  - Factory de clientes
  - Collector de OHLCV
  - Collector de sentimento
  - Validação de dados

## Como Usar

### Exemplo Básico

```python
from data.binance_client import create_binance_client
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector

# Criar cliente (paper mode por padrão)
client = create_binance_client(mode="paper")

# Inicializar collectors
collector = BinanceCollector(client)
sentiment_collector = SentimentCollector(client)

# Buscar klines
df = collector.fetch_klines("BTCUSDT", "1h", limit=100)

# Buscar dados de sentimento
sentiment = sentiment_collector.fetch_all_sentiment("BTCUSDT")
```

### Script de Exemplo

Execute o script de exemplo para validar a integração:

```bash
python examples/binance_sdk_usage_example.py
```

## Configuração de Ambiente

### Autenticação HMAC (padrão)

```env
BINANCE_API_KEY=sua_chave_api
BINANCE_API_SECRET=seu_secret
TRADING_MODE=paper  # ou "live"
```

### Autenticação Ed25519 (mais seguro)

```env
BINANCE_API_KEY=sua_chave_api
BINANCE_PRIVATE_KEY_PATH=/caminho/para/private_key.pem
BINANCE_PRIVATE_KEY_PASSPHRASE=sua_senha_opcional
TRADING_MODE=paper  # ou "live"
```

## Intervalos Suportados

- **Klines**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
- **Sentimento**: 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d

## Testes

Execute os testes de integração:

```bash
# Apenas testes da integração SDK
pytest tests/test_binance_sdk_integration.py -v

# Todos os testes
pytest tests/ -v
```

## Validação de Dados

O `BinanceCollector.validate_data()` verifica:
- ✅ Valores nulos
- ✅ Valores negativos em preços/volumes
- ✅ Gaps em timestamps (tolerância de 50%)
- ⚠️ **NUNCA interpola dados** - apenas reporta problemas

## Rate Limits

O SDK retorna informações de rate limit em cada response. O código implementa:
- Retry com backoff exponencial (5s, 15s, 45s)
- Sleep entre requests paginados (0.2s)
- Sleep entre símbolos diferentes (0.1s)

## WebSocket Features

### Mark Price Updates
- Frequência: 1s
- Callback: `register_price_callback(callback)`

### Flash Crash Detection
- Janela: 5 minutos (M1)
- Threshold: 5% de variação
- Callback: `register_flash_event_callback(callback)`

### Liquidation Cascade Detection
- Buffer: 24 horas
- Threshold: volume recente > 2x média
- Callback: `register_liquidation_callback(callback)`

## Migração do Código Existente

Para migrar código existente:

1. Substituir instanciação direta de `BinanceCollector`:
   ```python
   # Antes
   collector = BinanceCollector(api_key, api_secret)
   
   # Depois
   client = create_binance_client()
   collector = BinanceCollector(client)
   ```

2. Retornos agora são DataFrames ao invés de listas:
   ```python
   # Antes: List[Dict]
   data = collector.fetch_klines("BTCUSDT", "1h")
   
   # Depois: pd.DataFrame
   df = collector.fetch_klines("BTCUSDT", "1h")
   ```

3. WebSocketManager agora requer client no __init__:
   ```python
   # Antes
   ws_manager = WebSocketManager()
   
   # Depois
   client = create_binance_client()
   ws_manager = WebSocketManager(client)
   ```

## Referências

- SDK Python oficial: https://github.com/binance/binance-connector-python/tree/master/clients/derivatives_trading_usds_futures
- Documentação API: https://www.binance.com/en/binance-api
- Docs USDS-M Futures: https://developers.binance.com/docs/derivatives/usds-margined-futures

## Notas de Segurança

- ⚠️ **Nunca commite** arquivos `.env` com credenciais reais
- ✅ Use autenticação Ed25519 quando possível (mais seguro)
- ✅ Teste sempre em paper trading (testnet) antes de usar em produção
- ✅ Monitore rate limits para evitar banimentos
