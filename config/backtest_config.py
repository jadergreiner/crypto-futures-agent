"""
Configuração dedicada para backtesting 24/7 isolado.

Esta configuração é separada intencionalmente da live trading (config/settings.py)
para garantir que nenhuma modificação em uma afeta a outra.
"""

from typing import Dict, Any
from pathlib import Path

# ============================================================================
# BACKTESTING ISOLATION SETTINGS
# ============================================================================

# Modo isolado: desabilita trade execution, usa apenas dados históricos
BACKTEST_ISOLATED_MODE = True

# PID do processo live trading (para verificar se está vivo antes de executar)
LIVE_TRADING_PIDFILE = Path("run/main.pid")

# PID deste subprocesso
BACKTEST_PIDFILE = Path("run/backtest.pid")

# Arquivo de heartbeat (timestamp da última execução)
BACKTEST_HEARTBEAT_FILE = Path("run/backtest.heartbeat")

# Log file único para backtesting (separado do agent.log)
BACKTEST_LOG_FILE = "logs/backtest_24h7.log"

# Diretório de resultados (JSON com histórico de backtests)
BACKTEST_RESULTS_DIR = Path("backtest/results")

# ============================================================================
# SCHEDULE SETTINGS
# ============================================================================

BACKTEST_SCHEDULE = {
    # Daily backtest rodando no final do dia (com resultado pronto antes do mercado)
    "daily_backtest": {
        "hour": 23,
        "minute": 30,
        "timezone": "UTC",
        "timeout_minutes": 120,  # Max 2 horas para completar
        "misfire_grace_time": 600,  # Se atrasado > 10 min, skip
    },
    
    # Data update: Fetch últimas 4 candles de cada símbolo
    "data_update": {
        "hour": 0,
        "minute": 30,
        "timezone": "UTC",
        "timeout_minutes": 15,
        "misfire_grace_time": 300,
    },
    
    # Validação de dados: Checar staleness
    "data_validation": {
        "hour": 1,
        "minute": 0,
        "timezone": "UTC",
        "timeout_minutes": 5,
        "misfire_grace_time": 60,
    },
    
    # Sentiment + Macro: Atualizar dados de sentimento/macro
    "sentiment_macro_update": {
        "hour": 2,
        "minute": 0,
        "timezone": "UTC",
        "timeout_minutes": 10,
        "misfire_grace_time": 300,
    },
    
    # Backup & Compactação
    "backup_and_compact": {
        "day_of_week": "sunday",  # Domingo
        "hour": 3,
        "minute": 0,
        "timezone": "UTC",
        "timeout_minutes": 20,
        "misfire_grace_time": 600,
    },
    
    # Alert Digest
    "alert_digest": {
        "hour": 4,
        "minute": 0,
        "timezone": "UTC",
        "timeout_minutes": 5,
        "misfire_grace_time": 120,
    },
}

# ============================================================================
# DATA FRESHNESS THRESHOLDS
# ============================================================================

DATA_STALENESS_THRESHOLDS = {
    # Se D1 > 7 dias sem update, alert CRITICAL
    "D1": {
        "warning_days": 3,
        "critical_days": 7,
    },
    # Se H4 > 24 horas sem update, alert CRITICAL
    "H4": {
        "warning_hours": 12,
        "critical_hours": 24,
    },
    # Se H1 > 6 horas sem update, alert CRITICAL
    "H1": {
        "warning_hours": 3,
        "critical_hours": 6,
    },
}

# ============================================================================
# MONITORING & HEALTH CHECKS
# ============================================================================

HEALTH_CHECK_SETTINGS = {
    # Intervalo entre checks (em segundos)
    "probe_interval": 60,
    
    # Timeout do heartbeat (se não updated por X segundos, considera morto)
    "heartbeat_timeout": 120,
    
    # Max CPU usage antes de alertar (%)
    "max_cpu_percent": 90,
    
    # Time window para calcular CPU (min)
    "cpu_window_minutes": 10,
    
    # Max erros por hora antes de alertar
    "max_errors_per_hour": 5,
    
    # Tempo máximo para backtest completar
    "backtest_max_duration_minutes": 150,
}

# ============================================================================
# RECOVERY SETTINGS
# ============================================================================

RECOVERY_SETTINGS = {
    # Max tentativas de restart antes de rollback
    "max_restart_attempts": 3,
    
    # Janela de tempo para contar restarts (horas)
    "restart_count_window_hours": 24,
    
    # Se falhar N vezes em X horas, trigger rollback
    "rollback_threshold": {
        "attempts": 3,
        "hours": 24,
    },
    
    # Quantos dias de backups manter
    "backup_retention_days": 30,
    
    # Validar restore toda X horas (0 = disable, apenas backup)
    "restore_validation_hours": 168,  # Weekly
}

# ============================================================================
# DATABASE ISOLATION SETTINGS
# ============================================================================

DATABASE_SETTINGS = {
    # Usar WAL mode (vital para concorrência)
    "wal_mode": True,
    
    # WAL autocheckpoint (numero de páginas changed)
    "wal_autocheckpoint": 1000,
    
    # Synchronous mode: 0=ASYNC (fast, risky), 1=NORMAL (ok), 2=FULL (safe, slow)
    "synchronous": 1,  # NORMAL: ok para backtest
    
    # Cache size em MB
    "cache_size_mb": 10,
    
    # Number of connections allowed
    "max_connections": 5,
    
    # Connection timeout em segundos
    "timeout": 30,
}

# ============================================================================
# RATE LIMITING (Binance API)
# ============================================================================

RATE_LIMITING = {
    # Binance limit: 1200 requests/min
    "max_requests_per_minute": 1200,
    
    # Our throttle: never exceed 20% of limit
    "throttle_percentage": 0.2,  # = 240 req/min = 4 req/s
    
    # Backoff sequence (segundos) para retries
    "backoff_sequence": [5, 15, 45],
    
    # Max retries por requisição
    "max_retries": 5,
    
    # Jitter factor (random delay 0-X%)
    "jitter_percent": 0.1,
}

# ============================================================================
# BACKTESTING PARAMETERS
# ============================================================================

BACKTEST_PARAMS = {
    # Timeframe principal para backtest
    "primary_timeframe": "4h",
    
    # Lookback (quantas candles no passado para context)
    "lookback_candles": 250,
    
    # Período de backtest (dias para trás)
    "backtest_period_days": 90,
    
    # Initial capital
    "initial_capital": 10000,
    
    # Rebalance a cada X candles (0 = no rebalance)
    "rebalance_interval": 24,
}

# ============================================================================
# ALERTING SETTINGS
# ============================================================================

ALERTING = {
    # Telegram
    "telegram_enabled": True,
    "telegram_channel_critical": "@backtest_alerts_critical",
    "telegram_channel_warning": "@backtest_alerts_warning",
    "telegram_channel_info": "@backtest_alerts_info",
    
    # Rate limiting de alertas (não spam)
    "alert_rate_limit": {
        "CRITICAL": 60,  # Max 1 critical alert per minute
        "WARNING": 300,  # Max 1 warning alert per 5 minutes
        "INFO": 3600,    # Max 1 info alert per hour
    },
    
    # Batching: agrupar múltiplos alertas antes de enviar
    "batch_alerts": True,
    "batch_window_seconds": 60,
    
    # Max alertas por batch
    "alerts_per_batch": 10,
}

# ============================================================================
# LOGGING
# ============================================================================

LOGGING = {
    # Log level para backtesting
    "level": "INFO",
    
    # File size antes de rotacionar (50 MB)
    "file_max_bytes": 50 * 1024 * 1024,
    
    # Número de backups a manter
    "file_backup_count": 10,
    
    # Formato de log
    "format": "[%(asctime)s] %(levelname)-8s %(name)s - %(message)s",
}

# ============================================================================
# EXPORT Para uso em código
# ============================================================================

BACKTEST_CONFIG: Dict[str, Any] = {
    "isolated_mode": BACKTEST_ISOLATED_MODE,
    "schedule": BACKTEST_SCHEDULE,
    "staleness_thresholds": DATA_STALENESS_THRESHOLDS,
    "health_check": HEALTH_CHECK_SETTINGS,
    "recovery": RECOVERY_SETTINGS,
    "database": DATABASE_SETTINGS,
    "rate_limiting": RATE_LIMITING,
    "backtest_params": BACKTEST_PARAMS,
    "alerting": ALERTING,
    "logging": LOGGING,
}
