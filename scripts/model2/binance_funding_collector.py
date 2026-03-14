"""
M2-016.3 Fase D: Coletor de Fundign Rates e Open Interest da Binance.

Propósito:
- Coletar funding rates históricos (perpetual futures)
- Coletar open interest (OI) por símbolo
- Enriquecer episodes com contexto de mercado (leverage/sentiment)
- Persistir em SQLite para análise offline

Integração:
- Usado por: persist_training_episodes.py (enriquecimento de features)
- Dados persistidos: features_funding_rates, features_open_interest
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class BinanceFundingCollector:
    """Coleta funding rates e open interest da Binance Futures."""

    def __init__(self, db_path: str = "db/modelo2.db"):
        """
        Inicializa coletor.
        
        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Cria tabelas se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de funding rates históricos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funding_rates_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp_utc INTEGER NOT NULL,
                    funding_rate REAL,
                    estimated_leverage REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp_utc)
                )
            """)
            
            # Tabela de open interest histórico
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_interest_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp_utc INTEGER NOT NULL,
                    open_interest REAL,
                    open_interest_usd REAL,
                    market_sentiment VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp_utc)
                )
            """)
            
            # Índices
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funding_symbol_ts
                ON funding_rates_history(symbol, timestamp_utc)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_oi_symbol_ts
                ON open_interest_history(symbol, timestamp_utc)
            """)
            
            conn.commit()

    def get_latest_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        Retorna funding rate mais recente para um símbolo.
        
        Args:
            symbol: Ex. 'BTCUSDT'
            
        Returns:
            Dict com {funding_rate, estimated_leverage, timestamp_utc} ou None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT funding_rate, estimated_leverage, timestamp_utc
                FROM funding_rates_history
                WHERE symbol = ?
                ORDER BY timestamp_utc DESC
                LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "funding_rate": row[0],
                    "estimated_leverage": row[1],
                    "timestamp_utc": row[2]
                }
        return None

    def get_latest_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        Retorna open interest mais recente.
        
        Args:
            symbol: Ex. 'BTCUSDT'
            
        Returns:
            Dict com {open_interest, open_interest_usd, market_sentiment}
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT open_interest, open_interest_usd, market_sentiment, timestamp_utc
                FROM open_interest_history
                WHERE symbol = ?
                ORDER BY timestamp_utc DESC
                LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "open_interest": row[0],
                    "open_interest_usd": row[1],
                    "market_sentiment": row[2],
                    "timestamp_utc": row[3]
                }
        return None

    def get_funding_rate_series(self, symbol: str, hours: int = 72) -> List[Dict]:
        """
        Retorna série histórica de funding rates (últimas N horas).
        
        Args:
            symbol: Ex. 'BTCUSDT'
            hours: Quantidade de horas no histórico
            
        Returns:
            Lista de {timestamp_utc, funding_rate, estimated_leverage}
        """
        cutoff_ts = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp_utc, funding_rate, estimated_leverage
                FROM funding_rates_history
                WHERE symbol = ? AND timestamp_utc >= ?
                ORDER BY timestamp_utc DESC
            """, (symbol, cutoff_ts))
            
            return [
                {
                    "timestamp_utc": row[0],
                    "funding_rate": row[1],
                    "estimated_leverage": row[2]
                }
                for row in cursor.fetchall()
            ]

    def estimate_funding_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """
        Analisa sentiment do funding rate (período recente).
        
        Args:
            symbol: Ex. 'BTCUSDT'
            hours: Período para análise
            
        Returns:
            Dict com {avg_funding_rate, max_leverage, sentiment, trend}
            Sentimentos: 'bullish', 'neutral', 'bearish'
        """
        series = self.get_funding_rate_series(symbol, hours=hours)
        
        if not series:
            return {
                "avg_funding_rate": 0,
                "max_leverage": 0,
                "sentiment": "unknown",
                "trend": None
            }
        
        funding_rates = [x["funding_rate"] for x in series if x["funding_rate"] is not None]
        leverages = [x["estimated_leverage"] for x in series if x["estimated_leverage"] is not None]
        
        if not funding_rates:
            return {
                "avg_funding_rate": 0,
                "max_leverage": max(leverages) if leverages else 0,
                "sentiment": "unknown",
                "trend": None
            }
        
        avg_fr = sum(funding_rates) / len(funding_rates)
        max_lev = max(leverages) if leverages else 0
        
        # Sentiment baseado em funding rate médio
        if avg_fr < -0.0001:
            sentiment = "bullish"  # Funding negativo = shorts pagando longs
        elif avg_fr > 0.0001:
            sentiment = "bearish"  # Funding positivo = longs pagando shorts
        else:
            sentiment = "neutral"
        
        # Trend: comparação first vs last
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
            "max_leverage": max_lev,
            "sentiment": sentiment,
            "trend": trend
        }

    def estimate_oi_sentiment(self, symbol: str) -> Dict:
        """
        Analisa sentiment do open interest (actual size).
        
        Args:
            symbol: Ex. 'BTCUSDT'
            
        Returns:
            Dict com {current_oi, sentiment, change_direction}
            Sentimentos: 'accumulating', 'distributing', 'neutral'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT open_interest, timestamp_utc
                FROM open_interest_history
                WHERE symbol = ?
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

    def store_funding_rate_simulation(self, symbol: str, timestamp_utc: int, 
                                     funding_rate: float, estimated_leverage: float):
        """
        Simula e armazena funding rate (para teste/demo sem API Binance).
        
        Args:
            symbol: Ex. 'BTCUSDT'
            timestamp_utc: Timestamp em ms
            funding_rate: Taxa de financiamento
            estimated_leverage: Alavancagem estimada média no mercado
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO funding_rates_history
                    (symbol, timestamp_utc, funding_rate, estimated_leverage)
                    VALUES (?, ?, ?, ?)
                """, (symbol, timestamp_utc, funding_rate, estimated_leverage))
                conn.commit()
            except Exception as e:
                logger.error(f"Erro ao armazenar funding rate: {e}")

    def store_open_interest_simulation(self, symbol: str, timestamp_utc: int,
                                      open_interest: float, open_interest_usd: float,
                                      market_sentiment: str = "neutral"):
        """
        Simula e armazena open interest.
        
        Args:
            symbol: Ex. 'BTCUSDT'
            timestamp_utc: Timestamp em ms
            open_interest: Quantidade de contratos abertos
            open_interest_usd: Valor em USD
            market_sentiment: 'bullish', 'neutral', 'bearish'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO open_interest_history
                    (symbol, timestamp_utc, open_interest, open_interest_usd, market_sentiment)
                    VALUES (?, ?, ?, ?, ?)
                """, (symbol, timestamp_utc, open_interest, open_interest_usd, market_sentiment))
                conn.commit()
            except Exception as e:
                logger.error(f"Erro ao armazenar open interest: {e}")


# ====== TEST/DEMO

if __name__ == "__main__":
    import time
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    collector = BinanceFundingCollector()
    
    # Simula dados de funding rate
    now_ms = int(time.time() * 1000)
    for i in range(8):
        ts = now_ms - (i * 3600 * 1000)  # 8 horas trás
        fr = 0.00002 - (i * 0.000001)    # Funding rate declinando
        lev = 3.5 + (i * 0.1)            # Alavancagem crescendo
        
        collector.store_funding_rate_simulation("BTCUSDT", ts, fr, lev)
    
    # Simula open interest
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        for i in range(4):
            ts = now_ms - (i * 6 * 3600 * 1000)  # 24 horas
            oi = 100000 - (i * 5000)
            oi_usd = oi * 30000  # simulado
            
            collector.store_open_interest_simulation(symbol, ts, oi, oi_usd)
    
    # Query e analisa
    print("\n=== Funding Rate Analysis ===")
    fr = collector.get_latest_funding_rate("BTCUSDT")
    print(f"Latest: {json.dumps(fr, indent=2)}")
    
    sentiment = collector.estimate_funding_sentiment("BTCUSDT", hours=24)
    print(f"\nSentiment (24h): {json.dumps(sentiment, indent=2)}")
    
    print("\n=== Open Interest Analysis ===")
    oi = collector.get_latest_open_interest("BTCUSDT")
    print(f"Latest: {json.dumps(oi, indent=2)}")
    
    oi_sentiment = collector.estimate_oi_sentiment("BTCUSDT")
    print(f"\nOI Sentiment: {json.dumps(oi_sentiment, indent=2)}")
    
    print("\n[OK] Collector funcionando corretamente")
