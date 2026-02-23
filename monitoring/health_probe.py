"""
Health Probe para monitorar daemon de backtesting 24/7.

Verifica:
1. Se subprocesso está vivo
2. Se heartbeat está sendo atualizado (não travado)
3. CPU/RAM usage razoável
4. Logs sem muitos erros
5. Última execução de backtest recente

Roda em thread separada no main.py, não interfere com live trading.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import sys

try:
    import psutil
except ImportError:
    psutil = None

from config.backtest_config import BACKTEST_CONFIG


logger = logging.getLogger(__name__)


class BacktestHealthProbe:
    """Probe de saúde para backtesting daemon."""
    
    def __init__(self):
        """Inicializa probe."""
        self.pidfile = Path("run/backtest.pid")
        self.heartbeat_file = Path("run/backtest.heartbeat")
        self.results_dir = Path("backtest/results")
        self.log_file = Path("logs/backtest_24h7.log")
        self.health_check_settings = BACKTEST_CONFIG['health_check']
        
        self.last_probe_result = {}
        self.consecutive_failures = 0
    
    def probe(self) -> Dict[str, Any]:
        """
        Roda health probe completo.
        
        Returns:
            {
                'status': 'HEALTHY' | 'DEGRADED' | 'DEAD',
                'pid': 12345,
                'uptime_minutes': 120.5,
                'memory_mb': 320,
                'cpu_percent': 15.2,
                'heartbeat_age_seconds': 5,
                'last_backtest': '2026-02-22T23:30:00Z',
                'log_errors_1h': 3,
                'issues': ['CPU > threshold', ...]
            }
        """
        
        issues = []
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'HEALTHY',
            'issues': []
        }
        
        # 1. Check if process is running
        pid_result = self._check_process_alive()
        if not pid_result['alive']:
            result['status'] = 'DEAD'
            issues.append(f"Process not running (expected PID {pid_result.get('expected_pid')})")
            result['pid'] = None
        else:
            result['pid'] = pid_result['pid']
            result['uptime_minutes'] = pid_result.get('uptime_minutes')
            
            # 2. Check process resources (only if alive)
            resource_result = self._check_process_resources(pid_result['pid'])
            result.update(resource_result)
            
            if resource_result.get('cpu_percent', 0) > self.health_check_settings['max_cpu_percent']:
                issues.append(f"CPU > {self.health_check_settings['max_cpu_percent']}%")
            
            memory_threshold = 500  # MB
            if resource_result.get('memory_mb', 0) > memory_threshold:
                issues.append(f"Memory > {memory_threshold}MB")
        
        # 3. Check heartbeat
        heartbeat_result = self._check_heartbeat()
        result.update(heartbeat_result)
        
        if not heartbeat_result['alive']:
            if result['status'] != 'DEAD':
                result['status'] = 'DEGRADED'
            issues.append(f"Heartbeat stale ({heartbeat_result['age_seconds']}s old)")
        
        # 4. Check last backtest execution
        backtest_result = self._check_last_backtest()
        result.update(backtest_result)
        
        if backtest_result.get('last_backtest') is None:
            issues.append("No recent backtest results")
        
        # 5. Check log for errors
        log_result = self._check_logs()
        result.update(log_result)
        
        if log_result.get('errors_last_hour', 0) > self.health_check_settings['max_errors_per_hour']:
            issues.append(f"Too many errors in logs ({log_result['errors_last_hour']}/h)")
        
        # Set final status
        if len(issues) > 0:
            if result['status'] == 'HEALTHY':
                result['status'] = 'DEGRADED'
        
        result['issues'] = issues
        
        # Track consecutive failures
        if result['status'] != 'HEALTHY':
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
        
        result['consecutive_failures'] = self.consecutive_failures
        
        self.last_probe_result = result
        return result
    
    def _check_process_alive(self) -> Dict[str, Any]:
        """Verifica se subprocesso está vivo."""
        
        if not self.pidfile.exists():
            return {
                'alive': False,
                'expected_pid': None,
                'error': 'PID file not found'
            }
        
        try:
            with open(self.pidfile, 'r') as f:
                pid_str = f.read().strip()
            
            if not pid_str:
                return {
                    'alive': False,
                    'expected_pid': None,
                    'error': 'PID file empty'
                }
            
            pid = int(pid_str)
            
            # Check if process exists
            if psutil:
                try:
                    proc = psutil.Process(pid)
                    is_alive = proc.is_running()
                except psutil.NoSuchProcess:
                    is_alive = False
            else:
                # Fallback: tentar enviar signal 0 (test se processo existe)
                try:
                    os.kill(pid, 0)
                    is_alive = True
                except ProcessLookupError:
                    is_alive = False
            
            if is_alive:
                start_time = None
                if psutil:
                    try:
                        start_time = psutil.Process(pid).create_time()
                    except:
                        pass
                
                uptime_seconds = (time.time() - start_time) if start_time else 0
                
                return {
                    'alive': True,
                    'pid': pid,
                    'uptime_minutes': uptime_seconds / 60
                }
            else:
                return {
                    'alive': False,
                    'expected_pid': pid,
                    'error': 'Process not found'
                }
        
        except Exception as e:
            logger.error(f"Error checking process: {e}")
            return {
                'alive': False,
                'error': str(e)
            }
    
    def _check_process_resources(self, pid: int) -> Dict[str, Any]:
        """Verifica recursos usados pelo processo."""
        
        if not psutil:
            return {}
        
        try:
            proc = psutil.Process(pid)
            
            return {
                'cpu_percent': proc.cpu_percent(interval=1),
                'memory_mb': proc.memory_info().rss / 1024 / 1024,
                'num_threads': proc.num_threads()
            }
        
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            return {}
    
    def _check_heartbeat(self) -> Dict[str, Any]:
        """Verifica se heartbeat está sendo atualizado."""
        
        if not self.heartbeat_file.exists():
            return {
                'alive': False,
                'age_seconds': None,
                'error': 'Heartbeat file not found'
            }
        
        try:
            with open(self.heartbeat_file, 'r') as f:
                heartbeat_ts = float(f.read().strip())
            
            age_seconds = time.time() - heartbeat_ts
            timeout = self.health_check_settings['heartbeat_timeout']
            
            return {
                'alive': age_seconds < timeout,
                'age_seconds': age_seconds,
                'timeout_seconds': timeout
            }
        
        except Exception as e:
            logger.error(f"Error checking heartbeat: {e}")
            return {
                'alive': False,
                'error': str(e)
            }
    
    def _check_last_backtest(self) -> Dict[str, Any]:
        """Verifica última execução de backtest."""
        
        if not self.results_dir.exists():
            return {
                'last_backtest': None,
                'error': 'Results directory not found'
            }
        
        try:
            # Achar arquivo de resultado mais recente
            result_files = list(self.results_dir.glob('backtest_*.json'))
            
            if not result_files:
                return {
                    'last_backtest': None,
                    'error': 'No backtest results found'
                }
            
            # Get most recent file
            latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
            age_seconds = (datetime.utcnow() - 
                          datetime.fromtimestamp(latest_file.stat().st_mtime)).total_seconds()
            
            max_age = self.health_check_settings['backtest_max_duration_minutes'] * 60 * 2
            
            return {
                'last_backtest': latest_file.name,
                'age_seconds': age_seconds,
                'max_age_seconds': max_age,
                'fresh': age_seconds < max_age
            }
        
        except Exception as e:
            logger.error(f"Error checking backtest: {e}")
            return {
                'last_backtest': None,
                'error': str(e)
            }
    
    def _check_logs(self) -> Dict[str, Any]:
        """Verifica erros nos logs."""
        
        if not self.log_file.exists():
            return {
                'errors_last_hour': 0,
                'warnings_last_hour': 0,
                'error': 'Log file not found'
            }
        
        try:
            errors_1h = 0
            warnings_1h = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    # Parse log line (simplificado)
                    if 'ERROR' in line and cutoff_time.isoformat()[:10] in line:
                        errors_1h += 1
                    elif 'WARNING' in line and cutoff_time.isoformat()[:10] in line:
                        warnings_1h += 1
            
            return {
                'errors_last_hour': errors_1h,
                'warnings_last_hour': warnings_1h
            }
        
        except Exception as e:
            logger.error(f"Error checking logs: {e}")
            return {
                'errors_last_hour': 0
            }
    
    def on_unhealthy(self, result: Dict[str, Any]):
        """Callback quando saúde detecta problema."""
        
        severity = 'WARNING' if result['status'] == 'DEGRADED' else 'CRITICAL'
        
        message = f"Backtesting daemon {result['status'].lower()}: "
        message += ", ".join(result['issues'])
        
        logger.warning(f"[{severity}] {message}")
        
        # Se muitos failures, trigger recovery
        if result['consecutive_failures'] >= 3:
            logger.error("Multiple health check failures, may need recovery")
            # TODO: Integrar com recovery automation
    
    def suggest_action(self, result: Dict[str, Any]) -> Optional[str]:
        """Sugere ação baseada no health check."""
        
        if result['status'] == 'DEAD':
            return 'RESTART_BACKTEST_DAEMON'
        
        elif result['status'] == 'DEGRADED':
            if result['consecutive_failures'] >= 3:
                return 'RESTART_BACKTEST_DAEMON'
            else:
                return 'MONITOR'
        
        return None


def run_health_probe_continuous():
    """Roda probe contínuamente (para integração em thread)."""
    
    probe = BacktestHealthProbe()
    interval = BACKTEST_CONFIG['health_check']['probe_interval']
    
    while True:
        try:
            result = probe.probe()
            
            if result['status'] != 'HEALTHY':
                probe.on_unhealthy(result)
            
            action = probe.suggest_action(result)
            if action:
                logger.info(f"Recommended action: {action}")
        
        except Exception as e:
            logger.error(f"Error in health probe: {e}")
        
        time.sleep(interval)


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    
    probe = BacktestHealthProbe()
    result = probe.probe()
    
    import json
    print(json.dumps(result, indent=2))
