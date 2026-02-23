"""
Detector de Staleness de Dados Históricos.

Monitora se dados D1, H4, H1 estão atualizados e alerta
se ficarem obsoletos por mais que o threshold configurado.

Roda como check periódico dentro do daemon de backtesting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from config.backtest_config import BACKTEST_CONFIG
from data.database import DatabaseManager
from config.settings import DB_PATH


logger = logging.getLogger(__name__)


class StalenessDetector:
    """Detecta dados históricos obsoletos."""
    
    def __init__(self, db: DatabaseManager):
        """
        Inicializa detector.
        
        Args:
            db: DatabaseManager conectado ao banco de dados
        """
        self.db = db
        self.thresholds = BACKTEST_CONFIG['staleness_thresholds']
        self.last_alerts = {}  # Rastreamento de último alerta por timeframe
    
    def check_all_timeframes(self) -> Dict[str, Any]:
        """
        Verifica staleness para todos os timeframes configurados.
        
        Returns:
            {
                'status': 'OK' | 'WARNING' | 'CRITICAL',
                'last_update': {
                    'D1': '2026-02-22T15:00:00Z',
                    'H4': '2026-02-22T22:00:00Z',
                    'H1': '2026-02-22T22:30:00Z'
                },
                'staleness': {
                    'D1': {'age': '1 day', 'status': 'OK'},
                    'H4': {'age': '2 hours', 'status': 'OK'},
                    'H1': {'age': '30 minutes', 'status': 'OK'}
                },
                'alerts': [...]
            }
        """
        
        alerts = []
        last_update = {}
        staleness = {}
        max_severity = 'OK'
        
        try:
            with self.db.get_connection() as conn:
                for timeframe in ['D1', 'H4', 'H1']:
                    table = f"ohlcv_{timeframe.lower()}"
                    threshold_config = self.thresholds[timeframe]
                    
                    # Query latest timestamp
                    cursor = conn.execute(f"""
                        SELECT MAX(timestamp) as max_ts, COUNT(*) as row_count
                        FROM {table}
                    """)
                    result = cursor.fetchone()
                    
                    if result['max_ts'] is None or result['row_count'] == 0:
                        # No data!
                        alerts.append({
                            'timeframe': timeframe,
                            'status': 'CRITICAL',
                            'message': f'No {timeframe} data in database',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        staleness[timeframe] = {
                            'status': 'MISSING',
                            'age': 'N/A'
                        }
                        max_severity = 'CRITICAL'
                        continue
                    
                    # Convert timestamp (milliseconds to datetime)
                    latest_ts = result['max_ts']
                    latest_dt = datetime.utcfromtimestamp(latest_ts / 1000)
                    last_update[timeframe] = latest_dt.isoformat() + 'Z'
                    
                    # Calculate age
                    age = datetime.utcnow() - latest_dt
                    age_str = self._format_timedelta(age)
                    
                    # Determine thresholds
                    if timeframe == 'D1':
                        critical_td = timedelta(days=threshold_config['critical_days'])
                        warning_td = timedelta(days=threshold_config['warning_days'])
                    else:
                        critical_td = timedelta(hours=threshold_config['critical_hours'])
                        warning_td = timedelta(hours=threshold_config['warning_hours'])
                    
                    # Check severity
                    if age > critical_td:
                        alerts.append({
                            'timeframe': timeframe,
                            'status': 'CRITICAL',
                            'message': f'{timeframe} data is {age_str} old (> {critical_td})',
                            'age': age_str,
                            'threshold': str(critical_td),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        staleness[timeframe] = {
                            'status': 'CRITICAL',
                            'age': age_str
                        }
                        max_severity = 'CRITICAL'
                    
                    elif age > warning_td:
                        alerts.append({
                            'timeframe': timeframe,
                            'status': 'WARNING',
                            'message': f'{timeframe} data is {age_str} old (> {warning_td})',
                            'age': age_str,
                            'threshold': str(warning_td),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        staleness[timeframe] = {
                            'status': 'WARNING',
                            'age': age_str
                        }
                        if max_severity != 'CRITICAL':
                            max_severity = 'WARNING'
                    
                    else:
                        logger.info(f'{timeframe} data fresh: {age_str} old')
                        staleness[timeframe] = {
                            'status': 'OK',
                            'age': age_str
                        }
        
        except Exception as e:
            logger.error(f"Error in staleness check: {e}")
            alerts.append({
                'status': 'ERROR',
                'message': f'Staleness check failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })
            max_severity = 'ERROR'
        
        return {
            'status': max_severity,
            'last_update': last_update,
            'staleness': staleness,
            'alerts': alerts,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def check_symbol_coverage(self, timeframe: str = 'H4') -> Dict[str, Any]:
        """
        Verifica quantos símbolos têm dados atualizados.
        
        Exemplo: 58/60 símbolos têm H4 data frescos.
        
        Args:
            timeframe: Qual timeframe checar ('D1', 'H4', 'H1')
        
        Returns:
            {
                'covered': 58,
                'total': 60,
                'coverage_percent': 96.7,
                'missing_symbols': ['UNKNOWNUSDT', 'DEEPUSDT']
            }
        """
        
        from config.symbols import ALL_SYMBOLS
        
        table = f"ohlcv_{timeframe.lower()}"
        threshold_config = self.thresholds[timeframe]
        
        # Determine age threshold
        if timeframe == 'D1':
            age_threshold = timedelta(days=threshold_config['critical_days'])
        else:
            age_threshold = timedelta(hours=threshold_config['critical_hours'])
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT symbol FROM {table}
                    WHERE timestamp > {(datetime.utcnow() - age_threshold).timestamp() * 1000}
                    GROUP BY symbol
                """)
                
                covered_symbols = set(row[0] for row in cursor.fetchall())
        
        except Exception as e:
            logger.error(f"Error checking symbol coverage: {e}")
            return {
                'error': str(e),
                'covered': 0,
                'total': len(ALL_SYMBOLS),
                'coverage_percent': 0
            }
        
        missing = [s for s in ALL_SYMBOLS if s not in covered_symbols]
        
        return {
            'covered': len(covered_symbols),
            'total': len(ALL_SYMBOLS),
            'coverage_percent': 100.0 * len(covered_symbols) / len(ALL_SYMBOLS) if ALL_SYMBOLS else 0,
            'missing_symbols': missing
        }
    
    def check_data_continuity(self, timeframe: str = 'H4', 
                              lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Verifica se há gaps (candles faltando) nos dados recentes.
        
        Retorna lista de símbolos com gaps > 1 candle.
        
        Args:
            timeframe: Quale timeframe ('H4', 'H1', 'D1')
            lookback_hours: Quantas horas para trás verificar
        
        Returns:
            {
                'gaps_found': False,
                'symbols_with_gaps': [],
                'details': {
                    'BTCUSDT': {'gap_size_candles': 2, 'time_gap': '8 hours'}
                }
            }
        """
        
        from config.symbols import ALL_SYMBOLS
        
        # Converter timeframe para minutos
        tf_minutes = {
            'D1': 24 * 60,
            'H4': 4 * 60,
            'H1': 60,
            '15m': 15,
            '5m': 5
        }
        
        if timeframe not in tf_minutes:
            return {'error': f'Unknown timeframe {timeframe}'}
        
        candle_minutes = tf_minutes[timeframe]
        table = f"ohlcv_{timeframe.lower()}"
        
        gaps_found = False
        symbols_with_gaps = []
        details = {}
        
        try:
            with self.db.get_connection() as conn:
                lookback_ms = lookback_hours * 60 * 60 * 1000
                cutoff_ts = int((datetime.utcnow() - timedelta(hours=lookback_hours)).timestamp() * 1000)
                
                for symbol in ALL_SYMBOLS:
                    cursor = conn.execute(f"""
                        SELECT timestamp FROM {table}
                        WHERE symbol = ? AND timestamp > ?
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """, (symbol, cutoff_ts))
                    
                    timestamps = [row[0] for row in cursor.fetchall()]
                    
                    if not timestamps:
                        continue
                    
                    # Check for gaps between consecutive candles
                    for i in range(len(timestamps) - 1):
                        current_ts = timestamps[i]
                        next_ts = timestamps[i + 1]
                        
                        expected_gap_ms = candle_minutes * 60 * 1000
                        actual_gap_ms = current_ts - next_ts
                        
                        if actual_gap_ms > expected_gap_ms * 1.5:  # 50% tolerance
                            gap_candles = actual_gap_ms / expected_gap_ms
                            gap_hours = actual_gap_ms / (60 * 60 * 1000)
                            
                            symbols_with_gaps.append(symbol)
                            details[symbol] = {
                                'gap_size_candles': gap_candles,
                                'time_gap_hours': gap_hours
                            }
                            gaps_found = True
                            break  # One gap per symbol é suficiente
        
        except Exception as e:
            logger.error(f"Error checking continuity: {e}")
            return {
                'error': str(e),
                'gaps_found': False
            }
        
        return {
            'gaps_found': gaps_found,
            'symbols_with_gaps': list(set(symbols_with_gaps)),
            'details': details,
            'lookback_hours': lookback_hours
        }
    
    @staticmethod
    def _format_timedelta(td: timedelta) -> str:
        """Formata timedelta de forma legível."""
        total_seconds = int(td.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h"
        else:
            days = total_seconds // 86400
            return f"{days}d"


def run_staleness_check():
    """Entry point para rodar staleness check."""
    
    logger.info("Starting staleness check...")
    
    db = DatabaseManager(DB_PATH)
    detector = StalenessDetector(db)
    
    # Check general staleness
    result = detector.check_all_timeframes()
    logger.info(f"Staleness check: {result['status']}")
    
    for alert in result['alerts']:
        logger.warning(f"  {alert['timeframe']}: {alert['message']}")
    
    # Check symbol coverage
    coverage_h4 = detector.check_symbol_coverage('H4')
    logger.info(f"H4 coverage: {coverage_h4['coverage_percent']:.1f}% "
                f"({coverage_h4['covered']}/{coverage_h4['total']})")
    
    if coverage_h4.get('missing_symbols'):
        logger.warning(f"  Missing: {coverage_h4['missing_symbols']}")
    
    # Check for gaps
    continuity = detector.check_data_continuity('H4', lookback_hours=24)
    if continuity['gaps_found']:
        logger.warning(f"H4 data gaps found in {len(continuity['symbols_with_gaps'])} symbols")
        for symbol, gap_info in continuity['details'].items():
            logger.warning(f"  {symbol}: {gap_info['gap_size_candles']:.1f} candles (~{gap_info['time_gap_hours']:.1f}h)")
    else:
        logger.info("H4 data continuity: OK")
    
    return result


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    run_staleness_check()
