# 📊 Data Strategy: Backtesting 1 Year | Binance Futures

**Role:** Data Engineer (#11) | Binance API Expert | Integration Lead  
**Data:** 22 de fevereiro de 2026  
**Status:** ✅ Proposta Técnica Completa  
**Dependência:** Sprint 1 - Conectividade Validada (#55)

---

## 1️⃣ Fonte de Dados: Binance Klines Endpoint

### 1.1 Endpoint Selecionado

```
GET /fapi/v1/klines
```

**Rationale:**
- ✅ Suporta limites até 1500 candles por requisição
- ✅ Cobertura completa de dados históricos (desde inception)
- ✅ Período configurável (4h = 4 horas)
- ✅ Rate limit transparente: 1200 req/min (≈20 req/sec)
- ✅ Incluí OHLCV + outros campos validados

### 1.2 Parâmetros da Requisição

```
symbol:         BTCUSDT (exemplo)
interval:       4h (4 horas)
startTime:      Unix timestamp - 1 ano atrás
endTime:        Unix timestamp - hoje
limit:          1500 (máximo permitido)
```

**Response Structure:**
```json
[
  [
    1645017600000,      // Open time (ms)
    "43500.00",         // Open price
    "44000.00",         // High
    "43200.00",         // Low
    "43800.00",         // Close
    "1234.56",          // Volume (USDT)
    1645104000000,      // Close time
    "0.028",            // Quote asset volume
    42,                 // Trades count
    "625.20",           // Taker buy volume
    "0.014"             // Taker buy quote volume
  ]
]
```

---

## 2️⃣ Cálculo de Volume

### 2.1 Estimativa de Registros

| Métrica | Cálculo | Resultado |
|---------|---------|-----------|
| **Período** | 365 dias | 1 ano |
| **Candles/dia (4h)** | 24h ÷ 4h | 6 candles/dia |
| **Candles/ano** | 6 × 365 | **2.190 candles** |
| **Símbolos** | Subset configurável | **60 símbolos** |
| **Total registros** | 2.190 × 60 | **131.400 candles** |
| **Bytes/registro** | ~500 bytes JSON (bruto) | ~2.3 MB bruto |
| **Compressão** | SQLite/Parquet ~40% | ~930 KB compactado |

### 2.2 Distribuição de Armazenamento

```
Total bruto:        2.3 MB (se raw JSON)
SQLite otimizado:   ~650 KB
Parquet otimizado:  ~580 KB
CSV simples:        ~850 KB

Recomendação: SQLite (balanço query speed + compactação)
```

---

## 3️⃣ Estratégia de Cache Local

### 3.1 Comparação de Opções

| Critério | SQLite | Parquet | CSV | Redis |
|----------|--------|---------|-----|-------|
| **Storage** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ (volatile) |
| **Query Speed** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| **Compactação** | 80% | 75% | - | 30% |
| **Incremental Update** | ⭐⭐⭐⭐ | ⭐ (rebuild) | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Segurança** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Complexidade** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

### 3.2 Decisão: SQLite Primário + Parquet Backup

**Rationale:**
1. **SQLite (produção):** Schema estruturado, updates incrementais, crash-safe
2. **Parquet (backup):** Snapshots diários para analytics/failover
3. Ambos compactados + versionado em Git

**Schema SQLite:**

```sql
CREATE TABLE klines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  open_time INTEGER NOT NULL UNIQUE,           -- Unix ms
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL NOT NULL,                        -- Quote asset volume (USDT)
  close_time INTEGER NOT NULL,
  quote_volume REAL NOT NULL,
  trades INTEGER,
  taker_buy_volume REAL,
  taker_buy_quote_volume REAL,
  is_validated BOOLEAN DEFAULT 0,
  sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uc_symbol_time UNIQUE(symbol, open_time),
  CONSTRAINT chk_price_logic CHECK (low <= open AND low <= close AND high >= open AND high >= close)
);

CREATE INDEX idx_symbol_time ON klines(symbol, open_time);
CREATE INDEX idx_open_time ON klines(open_time);
```

**Diretório de armazenamento:**

```
data/
├── klines_cache.db               (SQLite principal, 650 KB)
├── klines_cache_20260222.parquet (Snapshot diário)
├── sync_log.json                 (Rastreamento de atualizações)
└── integrity_checksums.json      (CRC32 por símbolo/data)
```

---

## 4️⃣ Rate Limit Compliance

### 4.1 Limites da Binance Futures API

```
Peso padrão: 1 request = 1 peso
Limite global: 1200 pesos/minuto
Limite por IP: 5000 requisições/ 5 minutos

Para 60 símbolos × 2190 candles ÷ 1500 candles/req:
  Requisições necessárias = 60 × (2190 ÷ 1500) = 60 × 1.46 = ~88 requisições
```

### 4.2 Algoritmo de Download com Backoff Exponencial

```
Estratégia: Download sequencial com delays adaptativos
Batch size: 10 símbolos por minuto (600 pesos/min)
Backoff: Exponencial se 429 (Retry-After header)
```

**Pseudo-código implementação:**

```python
# File: data/binance_klines_fetcher.py
import time
from typing import List, Dict
from datetime import datetime, timedelta

class KlinesFetcher:
    def __init__(self, rate_limit_per_min=1200):
        self.rate_limit = rate_limit_per_min
        self.requests_this_minute = 0
        self.minute_start = time.time()
        
    def respect_rate_limit(self, weights=1):
        """Garante conformidade com rate limits Binance."""
        now = time.time()
        elapsed = now - self.minute_start
        
        # Reset a cada minuto
        if elapsed >= 60:
            self.requests_this_minute = 0
            self.minute_start = now
        
        # Estimar peso da próxima requisição
        remaining_capacity = self.rate_limit - self.requests_this_minute
        
        if weights > remaining_capacity:
            sleep_time = 60 - elapsed + 0.1
            print(f"[Rate Limit] Aguardando {sleep_time:.1f}s até próximo minuto...")
            time.sleep(max(0, sleep_time))
            self.requests_this_minute = 0
            self.minute_start = time.time()
        
        self.requests_this_minute += weights
    
    def fetch_klines_batch(
        self, 
        symbols: List[str], 
        interval: str = "4h",
        from_date: datetime = None,
        to_date: datetime = None,
        db_conn = None
    ) -> Dict[str, int]:
        """
        Faz download de klines para múltiplos símbolos respeitando rate limits.
        
        Returns:
            Dict com estatísticas: {"BTCUSDT": 2190, ...}
        """
        if from_date is None:
            from_date = datetime.utcnow() - timedelta(days=365)
        if to_date is None:
            to_date = datetime.utcnow()
        
        stats = {}
        start_ms = int(from_date.timestamp() * 1000)
        end_ms = int(to_date.timestamp() * 1000)
        
        for symbol in symbols:
            print(f"\n[{symbol}] Iniciando download...")
            
            candles_count = 0
            current_time = start_ms
            
            while current_time < end_ms:
                # Respeita rate limits ANTES de fazer request
                self.respect_rate_limit(weights=1)
                
                try:
                    # Request Klines
                    response = self._binance_klines_request(
                        symbol=symbol,
                        interval=interval,
                        startTime=current_time,
                        limit=1500
                    )
                    
                    if not response:
                        print(f"[{symbol}] Nenhum dado retornado, finalizando")
                        break
                    
                    # Persist em SQLite
                    self._persist_klines(db_conn, symbol, response)
                    candles_count += len(response)
                    
                    # Move window
                    last_time = response[-1][0]  # close_time
                    current_time = last_time + 1  # +1ms para evitar overlap
                    
                    print(f"[{symbol}] {candles_count} candles armazenados...")
                    
                except Exception as e:
                    if "429" in str(e):
                        # Rate limited - backoff exponencial
                        backoff = 2 ** min(5, self.backoff_count)
                        print(f"[{symbol}] Rate limited! Aguardando {backoff}s...")
                        time.sleep(backoff)
                        self.backoff_count += 1
                    else:
                        raise
            
            stats[symbol] = candles_count
        
        return stats
```

### 4.3 Estimativa de Tempo Total

```
Cenário: 60 símbolos, 1 ano, 4h candles

Cálculo:
- 60 símbolos × 1.46 batches (1500 candles/batch) = 88 requisições
- 88 requisições ÷ 10 símbolos/minuto = ~9 minutos mínimos
- + margins de segurança (backoff, variação) = 15-20 minutos

⏱️ TEMPO TOTAL ESTIMADO: **15-20 minutos** para primeira carga

Sincronização diária:
- 60 símbolos × 1 novo candle/dia = 60 requisições/dia
- ÷ 1200 capacidade/min → negligenciável (~3 segundos)
```

---

## 5️⃣ Validação de Integridade de Dados

### 5.1 Checklist de Validação

```python
class DataIntegrityValidator:
    """Garante qualidade dos dados históricos."""
    
    def validate_kline(self, kline: dict) -> tuple[bool, list]:
        """Retorna (é_válido, [erros])."""
        errors = []
        
        # 1. Lógica de preços (Low ≤ Open, Close ≤ High)
        if kline['low'] > kline['open'] or kline['low'] > kline['close']:
            errors.append("LOW price > OPEN or CLOSE (preços inconsistentes)")
        
        if kline['high'] < kline['open'] or kline['high'] < kline['close']:
            errors.append("HIGH price < OPEN or CLOSE")
        
        # 2. Volume não-negativo
        if kline['volume'] < 0 or kline['quote_volume'] < 0:
            errors.append("Volume negativo detectado")
        
        # 3. Timestamp monotônico
        if kline['open_time'] >= kline['close_time']:
            errors.append("open_time >= close_time")
        
        # 4. Duração esperada (4h = 14400000 ms)
        expected_duration_ms = 4 * 60 * 60 * 1000
        actual_duration = kline['close_time'] - kline['open_time']
        if actual_duration != expected_duration_ms:
            errors.append(f"Duração {actual_duration}ms != 14400000ms")
        
        # 5. Trades count razoável (>0 para 4h candle)
        if kline['trades'] <= 0:
            errors.append("Trades count = 0 (candle vazio/suspeito)")
        
        return len(errors) == 0, errors
    
    def validate_series(self, klines: List[dict], symbol: str) -> dict:
        """Valida série completa de 1 ano."""
        results = {
            "symbol": symbol,
            "total_candles": len(klines),
            "valid_candles": 0,
            "invalid_candles": 0,
            "errors": [],
            "gaps_detected": [],
            "checksum": None
        }
        
        prev_close_time = None
        checksum = 0
        
        for i, kline in enumerate(klines):
            is_valid, errors = self.validate_kline(kline)
            
            if is_valid:
                results["valid_candles"] += 1
            else:
                results["invalid_candles"] += 1
                results["errors"].append(f"Candle #{i}: {errors}")
            
            # Verificar gaps (deve haver exatamente 1 candle a cada 4h)
            if prev_close_time is not None:
                expected_next_open = prev_close_time + 1
                if kline['open_time'] != expected_next_open:
                    results["gaps_detected"].append({
                        "between_candles": [i-1, i],
                        "gap_ms": kline['open_time'] - prev_close_time
                    })
            
            # CRC32 de preço de fechamento (detecção de corrupção)
            checksum ^= hash(kline['close']) & 0xFFFFFFFF
            prev_close_time = kline['close_time']
        
        results["checksum"] = checksum
        results["validation_status"] = (
            "PASS" if results["invalid_candles"] == 0 and len(results["gaps_detected"]) == 0
            else "WARN" if results["invalid_candles"] < 5
            else "FAIL"
        )
        
        return results
```

### 5.2 Relatório de Validação Esperado

```
INTEGRIDADE REPORT: Backtesting Data 1 Year
=============================================

Data: 2026-02-22 10:30 UTC
Período: 2025-02-22 até 2026-02-22
Intervalo: 4h candles

Resumo por Símbolo:
┌─────────┬──────────┬─────────┬───────────┬──────────┐
│ Symbol  │ Candles  │ Valid   │ Invalid   │ Status   │
├─────────┼──────────┼─────────┼───────────┼──────────┤
│ BTCUSDT │ 2190     │ 2190    │ 0         │ ✅ PASS  │
│ ETHUSDT │ 2190     │ 2190    │ 0         │ ✅ PASS  │
│ ...     │ ...      │ ...     │ ...       │ ...      │
├─────────┼──────────┼─────────┼───────────┼──────────┤
│ TOTAL   │ 131400   │ 131380  │ 20        │ ✅ 99.9% │
└─────────┴──────────┴─────────┴───────────┴──────────┘

Problemas Detectados (20):
- LTCUSDT: 1 gap de 8h em 2025-06-15
- XRPUSDT: 5 candles com 0 trades (volume suspeitoso)
- ...

Recomendação: ✅ SEGURO PARA BACKTESTING (99.9% integridade)
```

---

## 6️⃣ Estratégia de Atualização Incremental

### 6.1 Tipos de Sincronização

| Tipo | Frequência | Scope | Uso |
|------|-----------|-------|-----|
| **Full** | 1× ao setup | Todos 60 símbolos, 1 ano | Inicial |
| **Daily Sync** | 1× por dia | Símbolo × últimos 7 dias | Manutenção contínua |
| **Incremental** | A cada 4h | Último candle aberto/fechado | Preparação para SMC |
| **Repair** | Sob demanda | Range específico | Recuperação de gaps |

### 6.2 Lógica de Sincronização Inteligente

```python
class KlinesSyncManager:
    """Gerencia updates inteligentes sem re-download desnecessário."""
    
    def determine_sync_scope(self, symbol: str, db_conn) -> dict:
        """
        Determina qual range precisa ser sincronizado.
        Evita re-download de dados já armazenados.
        """
        # Obter último timestamp armazenado
        last_stored = self._query_latest_timestamp(db_conn, symbol)
        
        if last_stored is None:
            # Primeira carga: 1 ano atrás até agora
            start_time = datetime.utcnow() - timedelta(days=365)
            end_time = datetime.utcnow()
            scope = "FULL_1YEAR"
        else:
            # Apenas candles após último registro
            last_stored_dt = datetime.fromtimestamp(last_stored / 1000)
            time_since_last = datetime.utcnow() - last_stored_dt
            
            if time_since_last.days >= 7:
                # Mais de 7 dias: resync últimas 7 dias (tolerance check)
                start_time = last_stored_dt - timedelta(days=7)
                scope = "DAILY_7DAYS"
            else:
                # Menos de 7 dias: apenas novos candles
                start_time = last_stored_dt + timedelta(hours=4)
                scope = "INCREMENTAL"
            
            end_time = datetime.utcnow()
        
        return {
            "symbol": symbol,
            "scope": scope,
            "start_time": start_time,
            "end_time": end_time,
            "estimated_requests": self._estimate_requests(start_time, end_time)
        }
    
    def sync_all_symbols(self, db_conn, symbols: List[str]):
        """Sincroniza todos os símbolos inteligentemente."""
        for symbol in symbols:
            sync_scope = self.determine_sync_scope(symbol, db_conn)
            
            print(f"[{symbol}] Sync scope: {sync_scope['scope']}")
            print(f"           Range: {sync_scope['start_time']} to {sync_scope['end_time']}")
            print(f"           Est. Requests: {sync_scope['estimated_requests']}")
            
            # Fetch apenas o necessário
            self.fetch_klines_batch(
                symbols=[symbol],
                from_date=sync_scope['start_time'],
                to_date=sync_scope['end_time'],
                db_conn=db_conn
            )
            
            # Validar integridade após insert
            self._validate_and_mark_valid(db_conn, symbol)
```

### 6.3 Cronograma de Sincronização

```
Schedule proposto:

[15:30 UTC] Full Sync (primeira vez)
  └─ Duração: 15-20 minutos
  └─ Resultado: 131.400 candles prontos

[Diariamente às 04:00 UTC] Daily Sync
  └─ Período: último 7 dias de cada símbolo
  └─ Duração: < 5 minutos
  └─ Objetivo: Catch gaps/corrupções em tempo real

[A cada 4 horas] Incremental Sync (antes de SMC)
  └─ Período: últimas 12 horas
  └─ Duração: < 30 segundos
  └─ Objetivo: Últimos dados para backtesting
```

---

## 7️⃣ Entregáveis Técnicos

### 7.1 Estrutura de Arquivos

```
data/
├── klines_cache.db                 # SQLite principal
├── klines_meta.json                # Metadados (last_sync, symbol_count)
├── integrity_report_20260222.json  # Resultado de validação
└── scripts/
    ├── fetch_klines.py             # Script standalone de download
    ├── sync_manager.py             # Gerenciador de syncs
    ├── validator.py                # Validador de integridade
    └── db_schema.sql               # Schema SQLite

backtest/
├── data_loader.py                  # Carrega dados para backtesting
└── tests/
    └── test_data_integrity.py      # Testes de qualidade
```

### 7.2 Interface para SMC (Backtest)

```python
# File: backtest/data_loader.py

class BacktestDataLoader:
    """Fornece dados de backtesting de forma otimizada."""
    
    def __init__(self, db_path: str = "data/klines_cache.db"):
        self.db = sqlite3.connect(db_path)
    
    def load_symbol_range(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Carrega dados de backtesting para um símbolo e período.
        Retorna DataFrame otimizado para numpy operations.
        """
        query = """
            SELECT 
                open_time as timestamp,
                open, high, low, close,
                volume
            FROM klines
            WHERE symbol = ? 
              AND open_time >= ? 
              AND open_time <= ?
              AND is_validated = 1
            ORDER BY open_time ASC
        """
        
        df = pd.read_sql(
            query,
            self.db,
            params=(
                symbol, 
                int(start_date.timestamp() * 1000),
                int(end_date.timestamp() * 1000)
            )
        )
        
        # Converter para numpy arrays para velocidade
        return df.astype({
            'timestamp': 'int64',
            'open': 'float32',
            'high': 'float32',
            'low': 'float32',
            'close': 'float32',
            'volume': 'float32'
        })
    
    def load_portfolio_range(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Carrega múltiplos símbolos em paralelo."""
        results = {}
        for symbol in symbols:
            results[symbol] = self.load_symbol_range(symbol, start_date, end_date)
        return results
```

### 7.3 Checklist de Inicialização

```
[📋] Data Pipeline Setup — Checklist

Fase 1: Configuração (5 minutos)
  [ ] Clone `data/` directory structure
  [ ] Criar arquivo `data/klines_cache.db` (vazio)
  [ ] Validar schema SQLite
  [ ] Definir lista de 60 símbolos em `symbols.json`

Fase 2: Download Inicial (15-20 minutos)
  [ ] Executar `python data/scripts/fetch_klines.py --full`
  [ ] Monitorar rate limits (deve manter <1200 req/min)
  [ ] Não interromper (se houver erro: retornar e resumir)

Fase 3: Validação (5 minutos)
  [ ] Executar `python data/scripts/validator.py`
  [ ] Gerar relatório `integrity_report_*.json`
  [ ] Validar que ≥99% candles passam em check
  [ ] Se <99%: investigar gaps/corrupções

Fase 4: Integração (2 minutos)
  [ ] Testar `BacktestDataLoader.load_symbol_range("BTCUSDT", ...)`
  [ ] Verificar que dados retornam com dtypes corretos
  [ ] Deploy scripts para produção

Fase 5: Cronograma (Contínuo)
  [ ] Agendar daily sync (`cron 04:00`)
  [ ] Agendar incremental sync (6h antes de SMC)
  [ ] Monitorar `klines_meta.json` para anomalias
```

---

## 📐 Resumo Executivo

| Aspecto | Decisão |
|---------|---------|
| **Fonte** | Binance Futures API - `/fapi/v1/klines` |
| **Volume** | 131.400 candles (60 símbolos × 1 ano × 6 candles/dia) |
| **Armazenamento** | SQLite primário (~650 KB) + Parquet backup |
| **Taxa de requisições** | 88 reqs total, respeitando <1200 reqs/min |
| **Tempo 1ª carga** | 15-20 minutos |
| **Validação** | ≥99% integridade, com gap detection |
| **Atualização** | Daily (5 min) + Incremental (< 30s) |
| **Pronto para SMC** | ✅ 24h antes de backtesting |

---

## 🔗 Próximas Dependências

- **Sprint 2:** Integração com `backtest/` module
- **Sprint 3:** ML preprocessing dos dados (normalization, feature engineering)
- **Go-live:** Validação de dados em-produção via API real

**Proprietário:** Data Engineer (#11) | **Status:** ✅ Ready for Implementation
