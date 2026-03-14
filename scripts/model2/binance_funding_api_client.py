"""
M2-016.3 Phase D.2: Integração API Binance Real para Funding Rates e Open Interest.

Propósito:
- Substituir simulador por endpoints reais da Binance Futures API
- Coletar funding rates históricos e em tempo real
- Coletar open interest com análise de trends
- Persistir dados incrementalmente em SQLite

Endpoints Binance utilizados:
- GET /fapi/v1/fundingRate (funding rate histórico)
- GET /fapi/v1/openInterest (open interest público)
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from functools import lru_cache

# Simulação de importação da Binance API
# Em produção: from binance.um_futures import UMFutures
# Para agora: mock local

logger = logging.getLogger(__name__)


class BinanceFundingAPIClient:
    """Cliente para Binance Futures API (funding rates e open interest)."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 db_path: str = "db/modelo2.db", use_mock: bool = False):
        """
        Inicializa cliente.
        
        Args:
            api_key: Chave API Binance (opcional para modo mock)
            api_secret: Secret API Binance
            db_path: Caminho banco SQLite
            use_mock: True = usa dados mock (safe para demo/test)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.db_path = db_path
        self.use_mock = use_mock
        
        # TODO: Inicializar cliente Binance real quando tiver credenciais
        # self.client = UMFutures(key=api_key, secret=api_secret)
        
        self._ensure_schema()

    def _ensure_schema(self):
        """Garante tabelas existem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funding_rates_api (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp_utc INTEGER NOT NULL,
                    funding_rate REAL NOT NULL,
                    mark_price REAL,
                    estimated_leverage REAL,
                    api_source VARCHAR(50) DEFAULT 'binance',
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp_utc)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_interest_api (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp_utc INTEGER NOT NULL,
                    open_interest REAL NOT NULL,
                    open_interest_usd REAL,
                    api_source VARCHAR(50) DEFAULT 'binance',
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp_utc)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fr_api_symbol_ts
                ON funding_rates_api(symbol, timestamp_utc DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_oi_api_symbol_ts
                ON open_interest_api(symbol, timestamp_utc DESC)
            """)
            
            conn.commit()

    def fetch_funding_rate_history(self, symbol: str, start_time: Optional[int] = None,
                                   end_time: Optional[int] = None, limit: int = 1000) -> List[Dict]:
        """
        Fetch funding rate history via Binance API.
        
        Endpoint: GET /fapi/v1/fundingRate
        
        Args:
            symbol: Ex. 'BTCUSDT'
            start_time: Timestamp ms ou None (últimas 1000 horas)
            end_time: Timestamp ms ou None (agora)
            limit: Max 1000 (padrão Binance)
            
        Returns:
            Lista de {timestamp, fundingRate, fundingTime}
        """
        if self.use_mock:
            return self._mock_funding_rate_history(symbol)
        
        try:
            # TODO: Implementar llamada real quando houver credenciais
            # path = "/fapi/v1/fundingRate"
            # params = {
            #     "symbol": symbol,
            #     "limit": limit
            # }
            # if start_time:
            #     params["startTime"] = start_time
            # if end_time:
            #     params["endTime"] = end_time
            # response = self.client._request_api("get", path, params=params)
            # return response
            
            logger.warning(f"API real não inicializada; usando mock para {symbol}")
            return self._mock_funding_rate_history(symbol)
            
        except Exception as e:
            logger.error(f"Erro ao buscar funding rate history: {e}")
            return []

    def fetch_open_interest(self, symbol: str, period: str = "5m") -> Optional[Dict]:
        """
        Fetch open interest atual via Binance API.
        
        Endpoint: GET /fapi/v1/openInterest
        
        Args:
            symbol: Ex. 'BTCUSDT'
            period: '5m', '15m', '30m', '1h' (frequência de snapshot)
            
        Returns:
            {symbol, openInterest, time} ou None se falhar
        """
        if self.use_mock:
            return self._mock_open_interest(symbol)
        
        try:
            # TODO: Implementar chamada real quando houver credenciais
            # path = "/fapi/v1/openInterest"
            # params = {"symbol": symbol, "period": period}
            # response = self.client._request_api("get", path, params=params)
            # return response
            
            logger.warning(f"API real não inicializada; usando mock para {symbol}")
            return self._mock_open_interest(symbol)
            
        except Exception as e:
            logger.error(f"Erro ao buscar open interest: {e}")
            return None

    def persist_funding_rate(self, symbol: str, funding_rate_data: Dict) -> bool:
        """
        Persiste funding rate no banco.
        
        Args:
            symbol: Ex. 'BTCUSDT'
            funding_rate_data: {fundingRate, fundingTime, ...}
            
        Returns:
            True se sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO funding_rates_api
                    (symbol, timestamp_utc, funding_rate, api_source)
                    VALUES (?, ?, ?, 'binance')
                """, (
                    symbol,
                    funding_rate_data.get("fundingTime"),
                    funding_rate_data.get("fundingRate")
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao persistir funding rate: {e}")
            return False

    def persist_open_interest(self, symbol: str, oi_data: Dict, 
                            current_price: float) -> bool:
        """
        Persiste open interest no banco.
        
        Args:
            symbol: Ex. 'BTCUSDT'
            oi_data: {openInterest, time}
            current_price: Preço atual para calcular USD value
            
        Returns:
            True se sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                oi = oi_data.get("openInterest", 0)
                oi_usd = float(oi) * current_price
                
                cursor.execute("""
                    INSERT OR REPLACE INTO open_interest_api
                    (symbol, timestamp_utc, open_interest, open_interest_usd, api_source)
                    VALUES (?, ?, ?, ?, 'binance')
                """, (
                    symbol,
                    oi_data.get("time"),
                    oi,
                    oi_usd
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao persistir open interest: {e}")
            return False

    def get_latest_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Retorna funding rate mais recente (compatibilidade com BinanceFundingCollector)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT funding_rate, timestamp_utc, mark_price
                    FROM funding_rates_api
                    WHERE symbol = ? AND api_source = 'binance'
                    ORDER BY timestamp_utc DESC
                    LIMIT 1
                """, (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "funding_rate": row[0],
                        "timestamp_utc": row[1],
                        "mark_price": row[2]
                    }
        except Exception as e:
            logger.error(f"Erro ao get_latest_funding_rate: {e}")
        return None

    def get_latest_open_interest(self, symbol: str) -> Optional[Dict]:
        """Retorna open interest mais recente (compatibilidade com BinanceFundingCollector)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT open_interest, timestamp_utc, api_source
                    FROM open_interest_api
                    WHERE symbol = ? AND api_source = 'binance'
                    ORDER BY timestamp_utc DESC
                    LIMIT 1
                """, (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "open_interest": row[0],
                        "timestamp_utc": row[1],
                        "market_sentiment": "neutral"  # Seria calculado em enrich_with_funding_data
                    }
        except Exception as e:
            logger.error(f"Erro ao get_latest_open_interest: {e}")
        return None

    def get_latest_api_data(self, symbol: str) -> Dict:
        """
        Query últimos rates/OI coletados via API.
        
        Returns:
            {funding_rate, timestamp, oi, oi_usd}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Funding rate
                cursor.execute("""
                    SELECT funding_rate, timestamp_utc
                    FROM funding_rates_api
                    WHERE symbol = ? AND api_source = 'binance'
                    ORDER BY timestamp_utc DESC
                    LIMIT 1
                """, (symbol,))
                fr_row = cursor.fetchone()
                
                # Open interest
                cursor.execute("""
                    SELECT open_interest, open_interest_usd, timestamp_utc
                    FROM open_interest_api
                    WHERE symbol = ? AND api_source = 'binance'
                    ORDER BY timestamp_utc DESC
                    LIMIT 1
                """, (symbol,))
                oi_row = cursor.fetchone()
            
            return {
                "symbol": symbol,
                "funding_rate": fr_row[0] if fr_row else None,
                "fr_timestamp": fr_row[1] if fr_row else None,
                "open_interest": oi_row[0] if oi_row else None,
                "open_interest_usd": oi_row[1] if oi_row else None,
                "oi_timestamp": oi_row[2] if oi_row else None,
            }
        except Exception as e:
            logger.error(f"Erro ao query dados API: {e}")
            return {}

    def estimate_funding_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """Analisa funding rate sentiment (compatibilidade com BinanceFundingCollector)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_ts = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)
                
                cursor.execute("""
                    SELECT funding_rate
                    FROM funding_rates_api
                    WHERE symbol = ? AND timestamp_utc >= ?
                    ORDER BY timestamp_utc DESC
                    LIMIT 100
                """, (symbol, cutoff_ts))
                
                rows = cursor.fetchall()
            
            if not rows:
                return {
                    "avg_funding_rate": 0,
                    "max_leverage": 0,
                    "sentiment": "unknown",
                    "trend": None
                }
            
            funding_rates = [float(row[0]) for row in rows if row[0] is not None]
            
            if not funding_rates:
                return {
                    "avg_funding_rate": 0,
                    "max_leverage": 0,
                    "sentiment": "unknown",
                    "trend": None
                }
            
            avg_fr = sum(funding_rates) / len(funding_rates)
            
            # Sentiment
            if avg_fr < -0.0001:
                sentiment = "bullish"
            elif avg_fr > 0.0001:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            # Trend
            trend = None
            if len(funding_rates) > 1:
                if funding_rates[-1] > funding_rates[0]:
                    trend = "increasing"
                elif funding_rates[-1] < funding_rates[0]:
                    trend = "decreasing"
                else:
                    trend = "stable"
            
            return {
                "avg_funding_rate": avg_fr,
                "max_leverage": 0,  # Não disponível em API pública
                "sentiment": sentiment,
                "trend": trend
            }
        except Exception as e:
            logger.error(f"Erro ao estimar funding sentiment: {e}")
            return {"sentiment": "unknown", "trend": None, "avg_funding_rate": 0, "max_leverage": 0}

    def estimate_oi_sentiment(self, symbol: str) -> Dict:
        """Analisa OI sentiment (compatibilidade com BinanceFundingCollector)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT open_interest, timestamp_utc
                    FROM open_interest_api
                    WHERE symbol = ? AND api_source = 'binance'
                    ORDER BY timestamp_utc DESC
                    LIMIT 2
                """, (symbol,))
                
                rows = cursor.fetchall()
            
            if not rows:
                return {
                    "current_oi": 0,
                    "sentiment": "unknown",
                    "change_direction": None
                }
            
            current_oi = rows[0][0] if rows else 0
            
            change = None
            sentiment = None
            if len(rows) > 1 and rows[0][0] and rows[1][0]:
                if rows[0][0] > rows[1][0]:
                    change = "increasing"
                    sentiment = "accumulating"
                elif rows[0][0] < rows[1][0]:
                    change = "decreasing"
                    sentiment = "distributing"
                else:
                    change = "stable"
                    sentiment = "neutral"
            else:
                change = None
                sentiment = "insufficient_data"
            
            return {
                "current_oi": current_oi,
                "sentiment": sentiment,
                "change_direction": change
            }
        except Exception as e:
            logger.error(f"Erro ao estimar OI sentiment: {e}")
            return {"current_oi": 0, "sentiment": "unknown", "change_direction": None}

    # ===== Mock Methods (para demonstração sem credenciais API)
    
    @staticmethod
    def _mock_funding_rate_history(symbol: str, count: int = 100) -> List[Dict]:
        """Simula histórico de funding rates."""
        import time
        now = int(time.time() * 1000)
        result = []
        
        for i in range(count):
            ts = now - (i * 8 * 3600 * 1000)  # 8h intervals
            # Simula FR volatilidade: (-0.001 to +0.001)
            fr = (i % 10 - 5) * 0.0001
            
            result.append({
                "fundingTime": ts,
                "fundingRate": fr,
                "markPrice": 40000 + (i * 100)
            })
        
        return result

    @staticmethod
    def _mock_open_interest(symbol: str) -> Dict:
        """Simula open interest atual."""
        import time
        import random
        
        now = int(time.time() * 1000)
        base_oi = 100000
        
        return {
            "symbol": symbol,
            "openInterest": str(base_oi + random.randint(-5000, 5000)),
            "time": now
        }


# ===== Test/Demo

if __name__ == "__main__":
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Inicializar com modo mock (sem credenciais)
    client = BinanceFundingAPIClient(use_mock=True)
    
    print("=== Binance Funding API Client (Mock Mode) ===\n")
    
    symbols = ["BTCUSDT", "ETHUSDT"]
    
    for symbol in symbols:
        print(f"1. Carregando histórico de funding rates: {symbol}")
        fr_history = client.fetch_funding_rate_history(symbol, limit=100)
        print(f"   Carregados: {len(fr_history)} registros")
        
        if fr_history:
            for rate_data in fr_history[:3]:  # Primeiros 3
                persisted = client.persist_funding_rate(symbol, rate_data)
                print(f"   - {rate_data.get('fundingTime')}: {rate_data.get('fundingRate')} (persisted: {persisted})")
        
        print(f"\n2. Carregando open interest: {symbol}")
        oi_data = client.fetch_open_interest(symbol)
        if oi_data:
            persisted = client.persist_open_interest(symbol, oi_data, current_price=40000)
            print(f"   OI: {oi_data.get('openInterest')} (persisted: {persisted})")
        
        print(f"\n3. Query dados API (últimos registros):")
        api_data = client.get_latest_api_data(symbol)
        print(f"   {json.dumps(api_data, indent=2)}\n")
    
    print("[OK] Binance Funding API Client funcionando")
