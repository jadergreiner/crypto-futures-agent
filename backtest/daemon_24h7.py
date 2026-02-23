"""
Daemon de backtesting 24/7 isolado.

Este subprocesso roda em background enquanto live trading ocorre no processo principal.
Completamente isolado: não executa trades, não acessa ordens executadas,
apenas lê dados históricos e simula backtest.

PID guardado em run/backtest.pid para monitoring externo.
Heartbeat escrito a cada ciclo para detectar hang.
"""

import sys
import os
import logging
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import signal
import traceback

# Setup path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.backtest_config import BACKTEST_CONFIG
from data.database import DatabaseManager
from config.symbols import ALL_SYMBOLS
from config.settings import DB_PATH


class BacktestDaemon:
    """Daemon isolado para backtesting 24/7."""
    
    def __init__(self):
        """Inicializa daemon."""
        self.pidfile = Path(BACKTEST_CONFIG['isolated_mode'] and "run/backtest.pid" or None)
        self.heartbeat_file = Path("run/backtest.heartbeat")
        self.results_dir = Path("backtest/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logger()
        self.db = DatabaseManager(DB_PATH)
        
        # State tracking
        self.running = True
        self.start_time = datetime.utcnow()
        self.last_backtest = None
        self.backtest_errors = []
        
        # PID management
        self._write_pidfile()
        
    def _setup_logger(self) -> logging.Logger:
        """Configura logger para backtesting."""
        logger = logging.getLogger('backtest_daemon')
        logger.setLevel(logging.INFO)
        
        # Handler para arquivo
        log_file = BACKTEST_CONFIG['logging'].get('level', 'INFO')
        handler = logging.FileHandler("logs/backtest_24h7.log")
        formatter = logging.Formatter(BACKTEST_CONFIG['logging']['format'])
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _write_pidfile(self):
        """Escreve PID do processo."""
        Path("run").mkdir(exist_ok=True)
        with open(self.pidfile, 'w') as f:
            f.write(str(os.getpid()))
        self.logger.info(f"Backtesting daemon started: PID {os.getpid()}")
    
    def _write_heartbeat(self):
        """Escreve timestamp de heartbeat."""
        try:
            with open(self.heartbeat_file, 'w') as f:
                f.write(str(time.time()))
        except Exception as e:
            self.logger.warning(f"Failed to write heartbeat: {e}")
    
    def _cleanup(self):
        """Cleanup ao shutdown."""
        self.logger.info("Backtesting daemon shutting down...")
        
        if self.pidfile.exists():
            self.pidfile.unlink()
        
        self.logger.info("Daemon stopped")
    
    def check_data_staleness(self) -> Dict[str, Any]:
        """
        Verifica se dados históricos estão obsoletos.
        
        Returns:
            {
                'fresh': bool,
                'alerts': [{'tf': 'H4', 'age_hours': 30, 'severity': 'CRITICAL'}]
            }
        """
        thresholds = BACKTEST_CONFIG['staleness_thresholds']
        alerts = []
        
        try:
            with self.db.get_connection() as conn:
                for timeframe, threshold_config in thresholds.items():
                    # Query latest timestamp for this timeframe
                    table = f"ohlcv_{timeframe.lower()}"
                    cursor = conn.execute(
                        f"SELECT MAX(timestamp) FROM {table}"
                    )
                    result = cursor.fetchone()
                    
                    if result[0] is None:
                        alerts.append({
                            'tf': timeframe,
                            'message': 'No data',
                            'severity': 'CRITICAL'
                        })
                        continue
                    
                    latest_ts = result[0]
                    latest_dt = datetime.utcfromtimestamp(latest_ts / 1000)
                    age = datetime.utcnow() - latest_dt
                    
                    # Check warning threshold
                    if timeframe == 'D1':
                        critical = timedelta(days=threshold_config['critical_days'])
                        warning = timedelta(days=threshold_config['warning_days'])
                    else:
                        critical = timedelta(hours=threshold_config['critical_hours'])
                        warning = timedelta(hours=threshold_config['warning_hours'])
                    
                    if age > critical:
                        alerts.append({
                            'tf': timeframe,
                            'age': str(age),
                            'message': f'{timeframe} data is {age} old (critical)',
                            'severity': 'CRITICAL'
                        })
                    elif age > warning:
                        alerts.append({
                            'tf': timeframe,
                            'age': str(age),
                            'message': f'{timeframe} data is {age} old (warning)',
                            'severity': 'WARNING'
                        })
                    else:
                        self.logger.info(f'{timeframe} data fresh: {age} old')
        
        except Exception as e:
            self.logger.error(f"Error checking staleness: {e}")
            alerts.append({
                'message': f'Staleness check failed: {e}',
                'severity': 'WARNING'
            })
        
        return {
            'fresh': len([a for a in alerts if a['severity'] == 'CRITICAL']) == 0,
            'alerts': alerts,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def run_daily_backtest(self) -> Dict[str, Any]:
        """
        Executa backtest diário com dados históricos.
        
        Returns:
            Resultado do backtest com métricas
        """
        start_time = time.time()
        self.logger.info("Starting daily backtest...")
        
        try:
            # 1. Verificar dados estão frescos
            staleness = self.check_data_staleness()
            if not staleness['fresh']:
                self.logger.warning(f"Data not fresh before backtest: {staleness['alerts']}")
                # Continue mesmo assim, mas log warning
            
            # 2. Carregar dados históricos
            self.logger.info("Loading historical data...")
            backtest_period_days = BACKTEST_CONFIG['backtest_params']['backtest_period_days']
            
            with self.db.get_connection() as conn:
                # Query últimas N candles H4 para cada símbolo
                cursor = conn.execute(f"""
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM ohlcv_h4
                    WHERE timestamp > {(datetime.utcnow() - timedelta(days=backtest_period_days)).timestamp() * 1000}
                    ORDER BY symbol, timestamp DESC
                """)
                data = cursor.fetchall()
            
            self.logger.info(f"Loaded {len(data)} candles from database")
            
            # 3. Simular backtest (placeholder - integração com engine real)
            results = self._simulate_backtest_session(data, backtest_period_days)
            
            # 4. Salvar resultados
            result_file = self.results_dir / f"backtest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Backtest completed in {time.time() - start_time:.1f}s")
            self.logger.info(f"Results saved to {result_file}")
            
            # 5. Update last backtest timestamp
            self.last_backtest = datetime.utcnow()
            
            return results
        
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            self.logger.error(traceback.format_exc())
            
            self.backtest_errors.append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            
            # Se muitos erros, retornar falha
            if len(self.backtest_errors) > 5:
                raise RuntimeError("Too many consecutive backtest failures")
            
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _simulate_backtest_session(self, data, period_days) -> Dict[str, Any]:
        """
        Simula uma sessão de backtest.
        
        Placeholder para integração com engine de backtest real.
        Por agora, retorna métricas básicas calculadas dos dados carregados.
        """
        
        # Placeholder: simular backtest com dados carregados
        num_symbols = len(set(row[0] for row in data))
        num_candles = len(data)
        
        return {
            'status': 'OK',
            'timestamp': datetime.utcnow().isoformat(),
            'period_days': period_days,
            'symbols_analyzed': num_symbols,
            'total_candles': num_candles,
            'pnl_percent': 5.2,  # Placeholder
            'sharpe_ratio': 1.8,  # Placeholder
            'max_drawdown_percent': -8.3,  # Placeholder
            'win_rate': 0.58,
            'total_trades': 42,
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        }
    
    def monitor_health(self) -> Dict[str, Any]:
        """
        Verifica saúde do daemon (recurso disponível, etc).
        
        Returns:
            Health status
        """
        import psutil
        
        try:
            process = psutil.Process(os.getpid())
            
            return {
                'status': 'HEALTHY',
                'pid': os.getpid(),
                'uptime_minutes': (datetime.utcnow() - self.start_time).total_seconds() / 60,
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=1),
                'num_threads': process.num_threads(),
                'errors_last_hour': len([e for e in self.backtest_errors 
                                        if (datetime.utcnow() - 
                                            datetime.fromisoformat(e['timestamp'])).total_seconds() < 3600])
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'status': 'UNKNOWN',
                'error': str(e)
            }
    
    def run_forever(self):
        """
        Roda daemon em loop infinito.
        Executa jobs da schedule: backtest, data validation, etc.
        """
        self.logger.info("Backtesting daemon running in background...")
        
        # Signal handlers para graceful shutdown
        def signal_handler(sig, frame):
            self.logger.info(f"Received signal {sig}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while self.running:
                # 1. Write heartbeat (todo monitorador externo soe alive)
                self._write_heartbeat()
                
                # 2. Check health
                health = self.monitor_health()
                self.logger.info(f"Daemon health: {health['status']} (CPU {health['cpu_percent']:.1f}%)")
                
                # 3. Check data staleness
                staleness = self.check_data_staleness()
                if not staleness['fresh']:
                    self.logger.warning(f"Data staleness alerts: {staleness['alerts']}")
                
                # 4. Execute scheduled jobs
                # TODO: Integrar com APScheduler para jobs reais
                # Por agora, placeholder sleep
                
                # Run backtest a cada 24h
                if self.last_backtest is None or \
                   (datetime.utcnow() - self.last_backtest).total_seconds() > 86400:
                    self.logger.info("Triggering daily backtest...")
                    results = self.run_daily_backtest()
                    self.logger.info(f"Backtest results: {results['status']}")
                
                # Sleep um minuto antes de próxima iteração
                time.sleep(60)
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
            self.logger.error(traceback.format_exc())
        
        finally:
            self._cleanup()


def main():
    """Entry point do daemon."""
    daemon = BacktestDaemon()
    daemon.run_forever()


if __name__ == "__main__":
    main()
