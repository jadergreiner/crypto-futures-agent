"""
SQLite database manager for the crypto futures agent.
Manages all data persistence including OHLCV, indicators, sentiment, macro data, SMC structures, and trades.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database operations for the crypto futures agent.
    All tables use composite primary keys on [timestamp, symbol] where applicable.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self) -> None:
        """Create all database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table 1: OHLCV D1
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_d1 (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    quote_volume REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    PRIMARY KEY (timestamp, symbol)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_d1_symbol ON ohlcv_d1(symbol)")
            
            # Table 2: OHLCV H4
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_h4 (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    quote_volume REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    PRIMARY KEY (timestamp, symbol)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_h4_symbol ON ohlcv_h4(symbol)")
            
            # Table 3: OHLCV H1
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_h1 (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    quote_volume REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    PRIMARY KEY (timestamp, symbol)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_h1_symbol ON ohlcv_h1(symbol)")
            
            # Table 4: Technical Indicators
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicadores_tecnico (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    ema_17 REAL,
                    ema_34 REAL,
                    ema_72 REAL,
                    ema_144 REAL,
                    ema_305 REAL,
                    ema_610 REAL,
                    rsi_14 REAL,
                    macd_line REAL,
                    macd_signal REAL,
                    macd_histogram REAL,
                    bb_upper REAL,
                    bb_middle REAL,
                    bb_lower REAL,
                    bb_bandwidth REAL,
                    bb_percent_b REAL,
                    vp_poc REAL,
                    vp_vah REAL,
                    vp_val REAL,
                    obv REAL,
                    atr_14 REAL,
                    adx_14 REAL,
                    di_plus REAL,
                    di_minus REAL,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicadores_symbol_tf ON indicadores_tecnico(symbol, timeframe)")
            
            # Table 5: Market Sentiment
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentimento_mercado (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    long_short_ratio REAL,
                    open_interest REAL,
                    open_interest_change_pct REAL,
                    funding_rate REAL,
                    liquidations_long_vol REAL,
                    liquidations_short_vol REAL,
                    liquidations_total_vol REAL,
                    PRIMARY KEY (timestamp, symbol)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentimento_symbol ON sentimento_mercado(symbol)")
            
            # Table 6: Macro Data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dados_macro (
                    timestamp INTEGER NOT NULL PRIMARY KEY,
                    dxy REAL,
                    dxy_change_pct REAL,
                    fed_rate REAL,
                    cpi_actual REAL,
                    cpi_expected REAL,
                    cpi_surprise REAL,
                    fear_greed_value INTEGER,
                    fear_greed_classification TEXT,
                    btc_dominance REAL,
                    btc_dominance_change_pct REAL,
                    stablecoin_exchange_flow_net REAL
                )
            """)
            
            # Table 7: SMC Market Structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smc_market_structure (
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    swing_type TEXT,
                    swing_price REAL,
                    swing_timestamp INTEGER,
                    structure_type TEXT,
                    bos_detected INTEGER DEFAULT 0,
                    bos_price REAL,
                    bos_timestamp INTEGER,
                    choch_detected INTEGER DEFAULT 0,
                    choch_price REAL,
                    choch_timestamp INTEGER,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_structure ON smc_market_structure(symbol, timeframe)")
            
            # Table 8: SMC Zones (Order Blocks, FVGs, Breakers)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smc_zones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_criacao INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    zone_type TEXT NOT NULL,
                    zone_high REAL NOT NULL,
                    zone_low REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'FRESH',
                    strength_score REAL DEFAULT 0,
                    last_tested_timestamp INTEGER,
                    invalidated_timestamp INTEGER
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_zones_symbol ON smc_zones(symbol, timeframe, status)")
            
            # Table 9: SMC Liquidity
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smc_liquidity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_criacao INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    liquidity_type TEXT NOT NULL,
                    price_level REAL NOT NULL,
                    touch_count INTEGER DEFAULT 0,
                    swept INTEGER DEFAULT 0,
                    swept_timestamp INTEGER,
                    strength_score REAL DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_liquidity ON smc_liquidity(symbol, swept)")
            
            # Table 10: Trade Log
            # NOTA: Novos campos adicionados (leverage, margin_type, liquidation_price, 
            # position_size_usdt, unrealized_pnl_at_snapshot). Se a tabela já existe,
            # os campos serão NULL para registros antigos. Em produção, considerar
            # usar ALTER TABLE para adicionar as colunas de forma incremental.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_log (
                    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_entrada INTEGER NOT NULL,
                    timestamp_saida INTEGER,
                    symbol TEXT NOT NULL,
                    direcao TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    pnl_usdt REAL,
                    pnl_pct REAL,
                    r_multiple REAL,
                    score_confluencia INTEGER,
                    reward_total REAL,
                    motivo_saida TEXT,
                    leverage INTEGER,
                    margin_type TEXT,
                    liquidation_price REAL,
                    position_size_usdt REAL,
                    unrealized_pnl_at_snapshot REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_log_symbol ON trade_log(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_log_timestamp ON trade_log(timestamp_entrada)")
            
            # Table 11: Position Snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    
                    -- Position data (from Binance)
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    mark_price REAL NOT NULL,
                    liquidation_price REAL,
                    position_size_qty REAL NOT NULL,
                    position_size_usdt REAL NOT NULL,
                    leverage INTEGER NOT NULL,
                    margin_type TEXT NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    unrealized_pnl_pct REAL NOT NULL,
                    margin_balance REAL,
                    
                    -- Technical indicators snapshot
                    rsi_14 REAL,
                    ema_17 REAL,
                    ema_34 REAL,
                    ema_72 REAL,
                    ema_144 REAL,
                    macd_line REAL,
                    macd_signal REAL,
                    macd_histogram REAL,
                    bb_upper REAL,
                    bb_lower REAL,
                    bb_percent_b REAL,
                    atr_14 REAL,
                    adx_14 REAL,
                    di_plus REAL,
                    di_minus REAL,
                    
                    -- SMC snapshot
                    market_structure TEXT,
                    bos_recent INTEGER DEFAULT 0,
                    choch_recent INTEGER DEFAULT 0,
                    nearest_ob_distance_pct REAL,
                    nearest_fvg_distance_pct REAL,
                    premium_discount_zone TEXT,
                    liquidity_above_pct REAL,
                    liquidity_below_pct REAL,
                    
                    -- Sentiment snapshot
                    funding_rate REAL,
                    long_short_ratio REAL,
                    open_interest_change_pct REAL,
                    
                    -- Decision output
                    agent_action TEXT NOT NULL,
                    decision_confidence REAL,
                    decision_reasoning TEXT,
                    
                    -- Risk assessment
                    risk_score REAL,
                    stop_loss_suggested REAL,
                    take_profit_suggested REAL,
                    trailing_stop_price REAL,
                    
                    -- For RL training
                    reward_calculated REAL,
                    outcome_label TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON position_snapshots(symbol, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_action ON position_snapshots(agent_action)")
            
            # Table 12: WebSocket Events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eventos_websocket (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    acao_tomada TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eventos_timestamp ON eventos_websocket(timestamp)")
            
            # Table 13: Reports
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relatorios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    dados_json TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_relatorios_tipo ON relatorios(tipo, timestamp)")
            
            logger.info("Database initialized successfully")
    
    def insert_ohlcv(self, timeframe: str, data: List[Dict[str, Any]]) -> None:
        """
        Insert OHLCV data into the appropriate table.
        
        Args:
            timeframe: "D1", "H4", or "H1"
            data: List of OHLCV dictionaries
        """
        table_name = f"ohlcv_{timeframe.lower()}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(f"""
                INSERT OR REPLACE INTO {table_name} 
                (timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count)
                VALUES (:timestamp, :symbol, :open, :high, :low, :close, :volume, :quote_volume, :trades_count)
            """, data)
        
        logger.debug(f"Inserted {len(data)} {timeframe} candles")
    
    def get_ohlcv(self, timeframe: str, symbol: str, start_time: Optional[int] = None, 
                   end_time: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve OHLCV data from the database.
        
        Args:
            timeframe: "D1", "H4", or "H1"
            symbol: Trading pair symbol
            start_time: Optional start timestamp
            end_time: Optional end timestamp
            limit: Optional limit on number of records
            
        Returns:
            List of OHLCV dictionaries
        """
        table_name = f"ohlcv_{timeframe.lower()}"
        query = f"SELECT * FROM {table_name} WHERE symbol = ?"
        params = [symbol]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_indicators(self, data: List[Dict[str, Any]]) -> None:
        """Insert technical indicators into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO indicadores_tecnico
                (timestamp, symbol, timeframe, ema_17, ema_34, ema_72, ema_144, ema_305, ema_610,
                 rsi_14, macd_line, macd_signal, macd_histogram,
                 bb_upper, bb_middle, bb_lower, bb_bandwidth, bb_percent_b,
                 vp_poc, vp_vah, vp_val, obv, atr_14, adx_14, di_plus, di_minus)
                VALUES (:timestamp, :symbol, :timeframe, :ema_17, :ema_34, :ema_72, :ema_144, :ema_305, :ema_610,
                        :rsi_14, :macd_line, :macd_signal, :macd_histogram,
                        :bb_upper, :bb_middle, :bb_lower, :bb_bandwidth, :bb_percent_b,
                        :vp_poc, :vp_vah, :vp_val, :obv, :atr_14, :adx_14, :di_plus, :di_minus)
            """, data)
        
        logger.debug(f"Inserted {len(data)} indicator records")
    
    def get_indicators(self, symbol: str, timeframe: str, start_time: Optional[int] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve technical indicators from the database."""
        query = "SELECT * FROM indicadores_tecnico WHERE symbol = ? AND timeframe = ?"
        params = [symbol, timeframe]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_sentiment(self, data: List[Dict[str, Any]]) -> None:
        """Insert market sentiment data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO sentimento_mercado
                (timestamp, symbol, long_short_ratio, open_interest, open_interest_change_pct,
                 funding_rate, liquidations_long_vol, liquidations_short_vol, liquidations_total_vol)
                VALUES (:timestamp, :symbol, :long_short_ratio, :open_interest, :open_interest_change_pct,
                        :funding_rate, :liquidations_long_vol, :liquidations_short_vol, :liquidations_total_vol)
            """, data)
        
        logger.debug(f"Inserted {len(data)} sentiment records")
    
    def get_sentiment(self, symbol: str, start_time: Optional[int] = None, 
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve sentiment data."""
        query = "SELECT * FROM sentimento_mercado WHERE symbol = ?"
        params = [symbol]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_macro(self, data: Dict[str, Any]) -> None:
        """Insert macro data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO dados_macro
                (timestamp, dxy, dxy_change_pct, fed_rate, cpi_actual, cpi_expected, cpi_surprise,
                 fear_greed_value, fear_greed_classification, btc_dominance, btc_dominance_change_pct,
                 stablecoin_exchange_flow_net)
                VALUES (:timestamp, :dxy, :dxy_change_pct, :fed_rate, :cpi_actual, :cpi_expected, :cpi_surprise,
                        :fear_greed_value, :fear_greed_classification, :btc_dominance, :btc_dominance_change_pct,
                        :stablecoin_exchange_flow_net)
            """, data)
        
        logger.debug("Inserted macro data")
    
    def get_macro(self, start_time: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve macro data."""
        query = "SELECT * FROM dados_macro"
        params = []
        
        if start_time:
            query += " WHERE timestamp >= ?"
            params.append(start_time)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_smc_structure(self, data: Dict[str, Any]) -> None:
        """Insert SMC market structure data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO smc_market_structure
                (timestamp, symbol, timeframe, swing_type, swing_price, swing_timestamp,
                 structure_type, bos_detected, bos_price, bos_timestamp,
                 choch_detected, choch_price, choch_timestamp)
                VALUES (:timestamp, :symbol, :timeframe, :swing_type, :swing_price, :swing_timestamp,
                        :structure_type, :bos_detected, :bos_price, :bos_timestamp,
                        :choch_detected, :choch_price, :choch_timestamp)
            """, data)
        
        logger.debug("Inserted SMC structure data")
    
    def insert_smc_zone(self, data: Dict[str, Any]) -> int:
        """Insert SMC zone and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO smc_zones
                (timestamp_criacao, symbol, timeframe, zone_type, zone_high, zone_low,
                 status, strength_score)
                VALUES (:timestamp_criacao, :symbol, :timeframe, :zone_type, :zone_high, :zone_low,
                        :status, :strength_score)
            """, data)
            zone_id = cursor.lastrowid
            logger.debug(f"Inserted SMC zone {zone_id}")
            return zone_id
    
    def update_smc_zone_status(self, zone_id: int, status: str, last_tested_timestamp: Optional[int] = None,
                                invalidated_timestamp: Optional[int] = None) -> None:
        """Update SMC zone status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smc_zones
                SET status = ?, last_tested_timestamp = ?, invalidated_timestamp = ?
                WHERE id = ?
            """, (status, last_tested_timestamp, invalidated_timestamp, zone_id))
        
        logger.debug(f"Updated SMC zone {zone_id} status to {status}")
    
    def get_active_smc_zones(self, symbol: str, timeframe: str, zone_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve active SMC zones."""
        query = "SELECT * FROM smc_zones WHERE symbol = ? AND timeframe = ? AND status != 'MITIGATED'"
        params = [symbol, timeframe]
        
        if zone_type:
            query += " AND zone_type = ?"
            params.append(zone_type)
        
        query += " ORDER BY timestamp_criacao DESC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_smc_liquidity(self, data: Dict[str, Any]) -> int:
        """Insert SMC liquidity level and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO smc_liquidity
                (timestamp_criacao, symbol, timeframe, liquidity_type, price_level,
                 touch_count, strength_score)
                VALUES (:timestamp_criacao, :symbol, :timeframe, :liquidity_type, :price_level,
                        :touch_count, :strength_score)
            """, data)
            liq_id = cursor.lastrowid
            logger.debug(f"Inserted liquidity level {liq_id}")
            return liq_id
    
    def update_liquidity_sweep(self, liq_id: int, swept_timestamp: int) -> None:
        """Mark liquidity level as swept."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smc_liquidity
                SET swept = 1, swept_timestamp = ?
                WHERE id = ?
            """, (swept_timestamp, liq_id))
        
        logger.debug(f"Marked liquidity {liq_id} as swept")
    
    def insert_trade(self, data: Dict[str, Any]) -> int:
        """Insert trade and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trade_log
                (timestamp_entrada, timestamp_saida, symbol, direcao, entry_price, exit_price,
                 stop_loss, take_profit, pnl_usdt, pnl_pct, r_multiple, score_confluencia,
                 reward_total, motivo_saida)
                VALUES (:timestamp_entrada, :timestamp_saida, :symbol, :direcao, :entry_price, :exit_price,
                        :stop_loss, :take_profit, :pnl_usdt, :pnl_pct, :r_multiple, :score_confluencia,
                        :reward_total, :motivo_saida)
            """, data)
            trade_id = cursor.lastrowid
            logger.info(f"Inserted trade {trade_id} for {data['symbol']}")
            return trade_id
    
    def update_trade_exit(self, trade_id: int, exit_data: Dict[str, Any]) -> None:
        """Update trade exit information."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trade_log
                SET timestamp_saida = ?, exit_price = ?, pnl_usdt = ?, pnl_pct = ?,
                    r_multiple = ?, motivo_saida = ?
                WHERE trade_id = ?
            """, (exit_data['timestamp_saida'], exit_data['exit_price'], exit_data['pnl_usdt'],
                  exit_data['pnl_pct'], exit_data['r_multiple'], exit_data['motivo_saida'], trade_id))
        
        logger.info(f"Updated trade {trade_id} exit")
    
    def get_trades(self, symbol: Optional[str] = None, start_time: Optional[int] = None,
                   end_time: Optional[int] = None, open_only: bool = False) -> List[Dict[str, Any]]:
        """Retrieve trades."""
        query = "SELECT * FROM trade_log WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if start_time:
            query += " AND timestamp_entrada >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp_entrada <= ?"
            params.append(end_time)
        if open_only:
            query += " AND timestamp_saida IS NULL"
        
        query += " ORDER BY timestamp_entrada DESC"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def insert_event(self, data: Dict[str, Any]) -> None:
        """Insert WebSocket event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eventos_websocket
                (timestamp, symbol, event_type, details, acao_tomada)
                VALUES (:timestamp, :symbol, :event_type, :details, :acao_tomada)
            """, data)
        
        logger.debug(f"Inserted event {data['event_type']} for {data['symbol']}")
    
    def insert_report(self, tipo: str, dados: Dict[str, Any]) -> None:
        """Insert report."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO relatorios
                (timestamp, tipo, dados_json)
                VALUES (?, ?, ?)
            """, (int(datetime.now().timestamp() * 1000), tipo, json.dumps(dados)))
        
        logger.info(f"Inserted report: {tipo}")
    
    def insert_position_snapshot(self, data: Dict[str, Any]) -> int:
        """
        Insert position snapshot and return its ID.
        
        Args:
            data: Position snapshot dictionary with all fields
            
        Returns:
            ID of inserted snapshot
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO position_snapshots
                (timestamp, symbol, direction, entry_price, mark_price, liquidation_price,
                 position_size_qty, position_size_usdt, leverage, margin_type,
                 unrealized_pnl, unrealized_pnl_pct, margin_balance,
                 rsi_14, ema_17, ema_34, ema_72, ema_144,
                 macd_line, macd_signal, macd_histogram,
                 bb_upper, bb_lower, bb_percent_b,
                 atr_14, adx_14, di_plus, di_minus,
                 market_structure, bos_recent, choch_recent,
                 nearest_ob_distance_pct, nearest_fvg_distance_pct,
                 premium_discount_zone, liquidity_above_pct, liquidity_below_pct,
                 funding_rate, long_short_ratio, open_interest_change_pct,
                 agent_action, decision_confidence, decision_reasoning,
                 risk_score, stop_loss_suggested, take_profit_suggested, trailing_stop_price,
                 reward_calculated, outcome_label)
                VALUES (:timestamp, :symbol, :direction, :entry_price, :mark_price, :liquidation_price,
                        :position_size_qty, :position_size_usdt, :leverage, :margin_type,
                        :unrealized_pnl, :unrealized_pnl_pct, :margin_balance,
                        :rsi_14, :ema_17, :ema_34, :ema_72, :ema_144,
                        :macd_line, :macd_signal, :macd_histogram,
                        :bb_upper, :bb_lower, :bb_percent_b,
                        :atr_14, :adx_14, :di_plus, :di_minus,
                        :market_structure, :bos_recent, :choch_recent,
                        :nearest_ob_distance_pct, :nearest_fvg_distance_pct,
                        :premium_discount_zone, :liquidity_above_pct, :liquidity_below_pct,
                        :funding_rate, :long_short_ratio, :open_interest_change_pct,
                        :agent_action, :decision_confidence, :decision_reasoning,
                        :risk_score, :stop_loss_suggested, :take_profit_suggested, :trailing_stop_price,
                        :reward_calculated, :outcome_label)
            """, data)
            snapshot_id = cursor.lastrowid
            logger.debug(f"Inserted position snapshot {snapshot_id} for {data['symbol']}")
            return snapshot_id
    
    def get_position_snapshots(self, symbol: str, start_time: Optional[int] = None, 
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve position snapshots.
        
        Args:
            symbol: Trading pair symbol
            start_time: Optional start timestamp
            limit: Optional limit on number of records
            
        Returns:
            List of snapshot dictionaries
        """
        query = "SELECT * FROM position_snapshots WHERE symbol = ?"
        params = [symbol]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_snapshot_outcome(self, snapshot_id: int, reward: float, outcome_label: str) -> None:
        """
        Update snapshot with outcome data retroactively.
        
        Args:
            snapshot_id: ID of the snapshot
            reward: Calculated reward value
            outcome_label: Outcome label (win/loss/hold)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE position_snapshots
                SET reward_calculated = ?, outcome_label = ?
                WHERE id = ?
            """, (reward, outcome_label, snapshot_id))
        
        logger.debug(f"Updated snapshot {snapshot_id} outcome: {outcome_label}, reward: {reward}")
    
    def get_snapshots_for_training(self, symbol: Optional[str] = None, 
                                   limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get snapshots with outcome filled for RL training.
        
        Args:
            symbol: Optional symbol filter
            limit: Maximum number of records to return
            
        Returns:
            List of snapshots with outcome_label not NULL
        """
        query = "SELECT * FROM position_snapshots WHERE outcome_label IS NOT NULL"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> None:
        """
        Clean up old data from the database.
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        cutoff_timestamp = int((datetime.now() - timedelta(days=days_to_keep)).timestamp() * 1000)
        
        tables_to_clean = [
            'ohlcv_d1', 'ohlcv_h4', 'ohlcv_h1', 'indicadores_tecnico',
            'sentimento_mercado', 'smc_market_structure', 'eventos_websocket'
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables_to_clean:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_timestamp,))
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Cleaned {deleted} old records from {table}")
        
        logger.info(f"Database cleanup completed (keeping {days_to_keep} days)")
