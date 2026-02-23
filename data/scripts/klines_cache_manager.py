#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Binance Klines Fetcher + Cache Manager
Responsável por: download, validação, cache e sincronização de dados históricos 1 ano

Role: Data Engineer (#11)
Status: Implementation Ready
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. Database Schema & Initialization
# ============================================================================

DB_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS klines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    open_time INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    close_time INTEGER NOT NULL,
    quote_volume REAL NOT NULL,
    trades INTEGER,
    taker_buy_volume REAL,
    taker_buy_quote_volume REAL,
    is_validated BOOLEAN DEFAULT 0,
    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, open_time),
    CHECK (low <= open AND low <= close AND high >= open AND high >= close)
);

CREATE INDEX IF NOT EXISTS idx_symbol_time ON klines(symbol, open_time);
CREATE INDEX IF NOT EXISTS idx_validated ON klines(is_validated);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    sync_type TEXT NOT NULL,
    rows_inserted INTEGER,
    rows_updated INTEGER,
    start_time INTEGER,
    end_time INTEGER,
    duration_seconds REAL,
    status TEXT,
    error_message TEXT,
    sync_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sync_symbol ON sync_log(symbol);
"""


def init_database(db_path: str) -> sqlite3.Connection:
    """Inicializa schema SQLite."""
    conn = sqlite3.connect(db_path)
    conn.executescript(DB_SCHEMA_SQL)
    conn.commit()
    logger.info(f"✅ Database initialized: {db_path}")
    return conn


# ============================================================================
# 2. Rate Limit Manager (Binance Compliance)
# ============================================================================

@dataclass
class RateLimitState:
    """Estado de rate limiting."""
    weights_used: int = 0
    minute_start: float = None
    max_weights_per_minute: int = 1200
    backoff_count: int = 0
    
    def __post_init__(self):
        if self.minute_start is None:
            self.minute_start = time.time()


class RateLimitManager:
    """Garante conformidade com rate limits da Binance (<1200 req/min)."""
    
    def __init__(self, max_weights_per_min: int = 1200):
        self.state = RateLimitState(max_weights_per_minute=max_weights_per_min)
    
    def respect_limit(self, weights: int = 1) -> float:
        """
        Aguarda se necessário para respeitar rate limit.
        
        Returns:
            float: segundos aguardados
        """
        now = time.time()
        elapsed = now - self.state.minute_start
        
        # Reset a cada minuto
        if elapsed >= 60:
            self.state.weights_used = 0
            self.state.minute_start = now
            self.state.backoff_count = 0
            elapsed = 0
        
        # Verificar capacidade
        remaining = self.state.max_weights_per_minute - self.state.weights_used
        
        if weights > remaining:
            sleep_time = max(0.1, 60 - elapsed)
            logger.warning(
                f"⏱️ Rate limit atingido! Aguardando {sleep_time:.1f}s "
                f"(usado {self.state.weights_used}/{self.state.max_weights_per_minute})"
            )
            time.sleep(sleep_time)
            self.state.weights_used = 0
            self.state.minute_start = time.time()
        
        self.state.weights_used += weights
        return elapsed
    
    def handle_429_backoff(self, retry_after_seconds: Optional[int] = None):
        """Backoff exponencial para 429 (Rate Limited)."""
        backoff = retry_after_seconds or (2 ** min(5, self.state.backoff_count))
        self.state.backoff_count += 1
        logger.error(f"❌ 429 Rate Limited! Backoff {backoff}s (attempt {self.state.backoff_count})")
        time.sleep(backoff)


# ============================================================================
# 3. Data Fetcher (Binance Client Wrapper)
# ============================================================================

class BinanceKlinesFetcher:
    """Faz fetch de klines da API Binance Futures."""
    
    def __init__(self, rate_limiter: RateLimitManager = None):
        self.rate_limiter = rate_limiter or RateLimitManager()
        self.base_url = "https://fapi.binance.com/fapi/v1"
        self.session = requests.Session()
        self.session.timeout = 30
    
    def fetch_klines(
        self,
        symbol: str,
        interval: str = "4h",
        start_time_ms: int = None,
        end_time_ms: int = None,
        limit: int = 1500
    ) -> List[List]:
        """
        Fetch klines do Binance.
        
        Args:
            symbol: e.g., "BTCUSDT"
            interval: e.g., "4h"
            start_time_ms: Unix ms
            end_time_ms: Unix ms
            limit: Max 1500
        
        Returns:
            Lista de candles: [[open_time, open, high, low, close, ...], ...]
        """
        # Respeita rate limit ANTES do request
        self.rate_limiter.respect_limit(weights=1)
        
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1500)
        }
        
        if start_time_ms:
            params["startTime"] = start_time_ms
        if end_time_ms:
            params["endTime"] = end_time_ms
        
        try:
            logger.info(f"📥 Fetching {symbol} {interval} ({limit} candles)")
            response = self.session.get(f"{self.base_url}/klines", params=params, timeout=30)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "60"))
                logger.warning(f"⚠️  Rate limited (429). Retry-After: {retry_after}s")
                self.rate_limiter.handle_429_backoff(retry_after)
                return []
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                logger.warning(f"⚠️  Empty response for {symbol} {interval}")
                return []
            
            logger.debug(f"✅ Fetched {len(data)} candles")
            return data
        
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout fetching {symbol}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error fetching {symbol}: {e}")
            raise


# ============================================================================
# 4. Data Validator (Integridade)
# ============================================================================

class KlineValidator:
    """Valida integridade individual de candles."""
    
    @staticmethod
    def validate_single(kline: dict) -> Tuple[bool, List[str]]:
        """
        Valida um candle individual.
        
        Returns:
            (é_válido, [lista de erros])
        """
        errors = []
        
        # Lógica de preços
        if kline['low'] > kline['open'] or kline['low'] > kline['close']:
            errors.append("LOW > OPEN ou CLOSE (inválido)")
        
        if kline['high'] < kline['open'] or kline['high'] < kline['close']:
            errors.append("HIGH < OPEN ou CLOSE (inválido)")
        
        # Volume não-negativo
        if kline['volume'] < 0 or kline['quote_volume'] < 0:
            errors.append("Volume negativo")
        
        # Timestamps
        if kline['open_time'] >= kline['close_time']:
            errors.append("open_time >= close_time")
        
        # Duração esperada (4h = 14400000 ms)
        expected_duration = 4 * 60 * 60 * 1000
        actual_duration = kline['close_time'] - kline['open_time']
        tolerance_ms = 100  # Tolerância de 100ms para sincronização de servidor
        if abs(actual_duration - expected_duration) > tolerance_ms:
            errors.append(f"Duração {actual_duration}ms fora do intervalo permitido (∆≤{tolerance_ms}ms)")
        
        # Trades count > 0
        if kline.get('trades', 1) <= 0:
            errors.append("Trades <= 0 (candle suspeito)")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_series(
        klines: List[dict],
        symbol: str
    ) -> Dict:
        """
        Valida série completa de 1 ano.
        """
        results = {
            "symbol": symbol,
            "total": len(klines),
            "valid": 0,
            "invalid": 0,
            "gaps": [],
            "status": "UNKNOWN"
        }
        
        prev_close_time = None
        
        for i, kline in enumerate(klines):
            is_valid, errors = KlineValidator.validate_single(kline)
            
            if is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            
            # Detectar gaps (deve haver exatamente 1 candle a cada 4h)
            if prev_close_time is not None:
                expected_next_open = prev_close_time + 1
                if kline['open_time'] != expected_next_open:
                    results["gaps"].append({
                        "candles": [i-1, i],
                        "gap_ms": kline['open_time'] - prev_close_time
                    })
            
            prev_close_time = kline['close_time']
        
        # Determinar status
        pass_rate = results["valid"] / max(1, results["total"])
        results["status"] = (
            "PASS" if results["invalid"] == 0 and len(results["gaps"]) == 0
            else "WARN" if pass_rate >= 0.99
            else "FAIL"
        )
        
        return results


# ============================================================================
# 5. Cache Manager (Persist + Sync)
# ============================================================================

class KlinesCacheManager:
    """Gerencia armazenamento e sincronização de dados em SQLite."""
    
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self.conn.row_factory = sqlite3.Row
    
    def insert_klines_batch(
        self,
        symbol: str,
        klines: List[List],
        validate: bool = True
    ) -> Dict:
        """
        Insere lote de klines em SQLite.
        
        Args:
            symbol: e.g., "BTCUSDT"
            klines: Lista de arrays Binance
            validate: Se True, valida antes de inserir
        
        Returns:
            {"inserted": int, "updated": int, "errors": int}
        """
        stats = {"inserted": 0, "updated": 0, "errors": 0}
        
        cursor = self.conn.cursor()
        
        for kline in klines:
            try:
                # Parse Binance response
                open_time = int(kline[0])
                open_price = float(kline[1])
                high = float(kline[2])
                low = float(kline[3])
                close = float(kline[4])
                volume = float(kline[5])
                close_time = int(kline[6])
                quote_volume = float(kline[7])
                trades = int(kline[8])
                taker_buy_vol = float(kline[9])
                taker_buy_quote_vol = float(kline[10])
                
                # Validar se solicitado
                kline_dict = {
                    "open_time": open_time,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "close_time": close_time,
                    "quote_volume": quote_volume,
                    "trades": trades
                }
                
                if validate:
                    is_valid, errors = KlineValidator.validate_single(kline_dict)
                    if not is_valid:
                        logger.warning(f"⚠️  Invalid kline {symbol} {open_time}: {errors}")
                        stats["errors"] += 1
                        continue
                
                # INSERT OR REPLACE
                cursor.execute("""
                    INSERT OR REPLACE INTO klines (
                        symbol, open_time, open, high, low, close,
                        volume, close_time, quote_volume, trades,
                        taker_buy_volume, taker_buy_quote_volume, is_validated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, open_time, open_price, high, low, close,
                    volume, close_time, quote_volume, trades,
                    taker_buy_vol, taker_buy_quote_vol, 1
                ))
                
                stats["inserted"] += 1
            
            except Exception as e:
                logger.error(f"❌ Error inserting kline {symbol}: {e}")
                stats["errors"] += 1
        
        self.conn.commit()
        logger.info(f"✅ {symbol}: {stats['inserted']} inserted, {stats['errors']} errors")
        
        return stats
    
    def get_latest_timestamp(self, symbol: str) -> Optional[int]:
        """Obtém último open_time armazenado para um símbolo."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT MAX(open_time) FROM klines WHERE symbol = ? AND is_validated = 1
        """, (symbol,))
        
        result = cursor.fetchone()[0]
        return result
    
    def count_candles(self, symbol: str) -> int:
        """Conta total de candles para um símbolo."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM klines WHERE symbol = ?", (symbol,))
        return cursor.fetchone()[0]
    
    def log_sync(
        self,
        symbol: str,
        sync_type: str,
        inserted: int,
        updated: int,
        start_time_ms: int,
        end_time_ms: int,
        duration_sec: float,
        status: str,
        error_msg: str = None
    ):
        """Registra evento de sincronização."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log (
                symbol, sync_type, rows_inserted, rows_updated,
                start_time, end_time, duration_seconds, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, sync_type, inserted, updated,
            start_time_ms, end_time_ms, duration_sec, status, error_msg
        ))
        self.conn.commit()


# ============================================================================
# 6. Orchestrator (Fluxo Principal)
# ============================================================================

class KlinesOrchestrator:
    """Orquestra fluxo completo: fetch -> validate -> cache -> log."""
    
    def __init__(
        self,
        db_path: str = "data/klines_cache.db",
        symbols_file: str = "config/symbols.json"
    ):
        self.db_conn = init_database(db_path)
        self.cache_mgr = KlinesCacheManager(self.db_conn)
        self.fetcher = BinanceKlinesFetcher()
        self.symbols = self._load_symbols(symbols_file)
        self.metadata = {
            "last_full_sync": None,
            "symbols_count": len(self.symbols),
            "last_update": None
        }
    
    @staticmethod
    def _load_symbols(symbols_file: str) -> List[str]:
        """Carrega lista de símbolos de arquivo JSON."""
        try:
            with open(symbols_file, 'r') as f:
                data = json.load(f)
                return data.get("symbols", [])
        except FileNotFoundError:
            logger.warning(f"⚠️  {symbols_file} não encontrado, usando default")
            return ["BTCUSDT", "ETHUSDT"]  # Default fallback
    
    def fetch_full_year(
        self,
        symbols: List[str] = None,
        interval: str = "4h",
        from_days_ago: int = 365
    ) -> Dict:
        """
        Faz download de 1 ano completo para múltiplos símbolos.
        
        Estimativa: 15-20 minutos para 60 símbolos
        """
        if symbols is None:
            symbols = self.symbols
        
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=from_days_ago)
        
        start_ms = int(from_date.timestamp() * 1000)
        end_ms = int(to_date.timestamp() * 1000)
        
        logger.info(f"🚀 Iniciando fetch de 1 ano para {len(symbols)} símbolos")
        logger.info(f"   Período: {from_date} até {to_date}")
        
        full_stats = {}
        start_time = time.time()
        
        for symbol in symbols:
            logger.info(f"\n📊 [{symbol}] Iniciando downlo (1 year, {interval})...")
            
            current_time = start_ms
            candles_count = 0
            sync_start_ms = start_ms
            
            try:
                while current_time < end_ms:
                    # Fetch batch
                    klines = self.fetcher.fetch_klines(
                        symbol=symbol,
                        interval=interval,
                        start_time_ms=current_time,
                        limit=1500
                    )
                    
                    if not klines:
                        logger.info(f"[{symbol}] Nenhum dado retornado (fim?)")
                        break
                    
                    # Insert em cache
                    stats = self.cache_mgr.insert_klines_batch(
                        symbol,
                        klines,
                        validate=True
                    )
                    candles_count += stats["inserted"]
                    
                    # Move window forward
                    last_time = int(klines[-1][0])
                    current_time = last_time + (4 * 60 * 60 * 1000)  # +4h
                    
                    logger.info(f"[{symbol}] {candles_count} candles sofar...")
                
                # Log sync event
                duration = time.time() - start_time
                self.cache_mgr.log_sync(
                    symbol=symbol,
                    sync_type="FULL",
                    inserted=candles_count,
                    updated=0,
                    start_time_ms=sync_start_ms,
                    end_time_ms=end_ms,
                    duration_sec=duration,
                    status="SUCCESS"
                )
                
                full_stats[symbol] = candles_count
                logger.info(f"✅ [{symbol}] Concluído: {candles_count} candles")
            
            except Exception as e:
                logger.error(f"❌ [{symbol}] Erro: {e}")
                full_stats[symbol] = f"ERROR: {str(e)}"
        
        self.metadata["last_full_sync"] = datetime.utcnow().isoformat()
        self._save_metadata()
        
        total_duration = time.time() - start_time
        logger.info(f"\n✅ CONCLUSÃO: {len(symbols)} símbolos em {total_duration/60:.1f} minutos")
        
        return full_stats
    
    def _save_metadata(self):
        """Salva metadados em JSON."""
        meta_file = Path("data/klines_meta.json")
        with open(meta_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"💾 Metadados salvos: {meta_file}")
    
    def validate_all(self) -> Dict:
        """Valida integridade de todos os symbols."""
        logger.info(f"🔍 Validando integridade de {len(self.symbols)} símbolos...")
        
        results = {}
        for symbol in self.symbols:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT 
                    open_time, open, high, low, close,
                    volume, close_time, quote_volume, trades
                FROM klines
                WHERE symbol = ?
                ORDER BY open_time ASC
            """, (symbol,))
            
            klines = [dict(row) for row in cursor.fetchall()]
            
            if not klines:
                logger.warning(f"⚠️  {symbol}: Nenhum candle")
                continue
            
            validate_result = KlineValidator.validate_series(klines, symbol)
            results[symbol] = validate_result
            
            logger.info(f"✅ {symbol}: {validate_result['valid']}/{validate_result['total']} "
                       f"válidos ({validate_result['status']})")
        
        # Save report
        report_file = Path(f"data/integrity_report_{datetime.utcnow():%Y%m%d_%H%M%S}.json")
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"📊 Relatório salvo: {report_file}")
        
        return results


# ============================================================================
# 7. CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Binance Klines Fetcher & Cache Manager")
    parser.add_argument(
        "--action",
        choices=["fetch_full", "validate", "sync_daily"],
        default="fetch_full",
        help="Ação a executar"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        help="Arquivo JSON com lista de símbolos (default: config/symbols.json)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/klines_cache.db",
        help="Caminho do banco de dados SQLite"
    )
    
    args = parser.parse_args()
    
    # Inicializa orchestrator
    orch = KlinesOrchestrator(db_path=args.db)
    
    # Executa ação
    if args.action == "fetch_full":
        logger.info("🚀 Iniciando FULL FETCH de 1 ano...")
        stats = orch.fetch_full_year()
        logger.info(f"Resultado: {json.dumps(stats, indent=2)}")
    
    elif args.action == "validate":
        logger.info("🔍 Executando VALIDAÇÃO de integridade...")
        results = orch.validate_all()
    
    elif args.action == "sync_daily":
        logger.info("📅 Executando SYNC diário...")
        # TODO: Implementar lógica de sync incremental
        logger.info("(Em desenvolvimento)")
