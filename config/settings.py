"""
General settings and configuration for the crypto futures agent.
All sensitive data should be loaded from environment variables.
"""

import os
from typing import Iterable, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables using common truthy values."""
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_symbol_scope(
    raw_value: str | None,
    *,
    fallback_symbols: Iterable[str],
) -> tuple[str, ...]:
    """Normaliza lista de simbolos e expande placeholders suportados."""
    fallback_list = [
        str(symbol).strip().upper()
        for symbol in fallback_symbols
        if str(symbol).strip()
    ]
    fallback_tuple = tuple(dict.fromkeys(fallback_list))
    if raw_value is None:
        return ()

    placeholder_tokens = {
        "M2_SYMBOLS",
        "M2_SYMBOLS:",
        "M2_LIVE_SYMBOLS",
        "M2_LIVE_SYMBOLS:",
        "ALL_SYMBOLS",
        "ALL_SYMBOLS:",
    }
    normalized: list[str] = []
    for token in str(raw_value).split(","):
        symbol = str(token).strip().upper()
        if not symbol:
            continue
        if symbol in placeholder_tokens:
            normalized.extend(fallback_tuple)
            continue
        normalized.append(symbol)

    return tuple(dict.fromkeys(normalized))

# Binance API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# Key Pair Authentication (Ed25519 - opcional, mais seguro)
BINANCE_PRIVATE_KEY_PATH = os.getenv("BINANCE_PRIVATE_KEY_PATH", "")
BINANCE_PRIVATE_KEY_PASSPHRASE = os.getenv("BINANCE_PRIVATE_KEY_PASSPHRASE", "")

# Binance URLs - Testnet
BINANCE_TESTNET_REST_URL = "https://testnet.binancefuture.com"
BINANCE_TESTNET_WS_URL = "wss://stream.binancefuture.com"

# Production URLs are imported from SDK
# DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL
# DERIVATIVES_TRADING_USDS_FUTURES_WS_API_PROD_URL
# DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_PROD_URL

# Database Configuration
DB_PATH = "db/crypto_agent.db"
MODEL2_DB_PATH = os.getenv("MODEL2_DB_PATH", "db/modelo2.db")
M2_CANARY_DB_PATH = os.getenv("M2_CANARY_DB_PATH", "db/modelo2_canary.db")
M2_EXECUTION_MODE = os.getenv("M2_EXECUTION_MODE", "shadow").strip().lower()
M2_SHORT_ONLY = _env_bool("M2_SHORT_ONLY", True)
M2_INJECTION_ENABLED = _env_bool("M2_INJECTION_ENABLED", True)
M2_CANARY_LEVERAGE = int(os.getenv("M2_CANARY_LEVERAGE", "3"))
M2_FUNDING_RATE_MAX_FOR_SHORT = float(os.getenv("M2_FUNDING_RATE_MAX_FOR_SHORT", "0.0005"))
M2_REQUIRE_MAINNET_CONFIRM = _env_bool("M2_REQUIRE_MAINNET_CONFIRM", True)
M2_MAINNET_CONFIRM_TOKEN = os.getenv("M2_MAINNET_CONFIRM_TOKEN", "").strip()
# Single source of truth for M2 operational symbol scope.
# Priority:
# 1) Explicit .env allow-list (`M2_LIVE_SYMBOLS`)
# 2) Legacy universe fallback from `config.symbols.ALL_SYMBOLS`
try:
    from config.symbols import ALL_SYMBOLS as _ALL_SYMBOLS
except Exception:
    _ALL_SYMBOLS = []
M2_LIVE_SYMBOLS = _normalize_symbol_scope(
    os.getenv("M2_LIVE_SYMBOLS", ""),
    fallback_symbols=_ALL_SYMBOLS,
)
M2_SYMBOLS = M2_LIVE_SYMBOLS if M2_LIVE_SYMBOLS else tuple(_ALL_SYMBOLS)
M2_MAX_DAILY_ENTRIES = int(os.getenv("M2_MAX_DAILY_ENTRIES", "10"))
M2_MAX_MARGIN_PER_POSITION_USD = float(os.getenv("M2_MAX_MARGIN_PER_POSITION_USD", "1.0"))
M2_MAX_SIGNAL_AGE_MINUTES = int(os.getenv("M2_MAX_SIGNAL_AGE_MINUTES", "240"))
M2_SYMBOL_COOLDOWN_MINUTES = int(os.getenv("M2_SYMBOL_COOLDOWN_MINUTES", "240"))

# Trading Mode
TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # "paper" or "live"

# Timeframes
TIMEFRAMES = {
    "D1": "1d",
    "H4": "4h",
    "H1": "1h",
    "M1": "1m"
}

# Historical Data Periods (days)
# Aumentados para suportar min_length=1000 com split 80/20 e indicadores de longo prazo
HISTORICAL_PERIODS = {
    "D1": 730,    # 2 anos (para EMA_610 com margem de segurança)
    "H4": 250,    # ~1500 candles H4 (garante 1000+ candles após split 80/20)
    "H1": 209     # ~5016 candles H1 (remove aviso limítrofe de suficiência)
}

# Layer 4 (H4) execution times in UTC
H4_EXECUTION_HOURS = [0, 4, 8, 12, 16, 20]

# Funding rate times in UTC
FUNDING_RATE_HOURS = [0, 8, 16]

# API Retry Configuration
API_MAX_RETRIES = 3
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAYS = [5, 15, 45]  # seconds
API_RETRY_BACKOFF = [5, 15, 45]  # seconds (backward compat)

# Data Collection Limits
KLINES_LIMIT = 1500  # Max per Binance request
SENTIMENT_LIMIT = 30
FORCE_ORDERS_LIMIT = 100

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/agent.log"        # Default: operação live/paper
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Contexto específico de logging (segregação por propósito)
LOG_FILES = {
    "operation": "logs/agent.log",      # Live/paper trading
    "training": "logs/training.log",    # RL model training
    "backtest": "logs/backtest.log",    # Backtesting
    "collection": "logs/collection.log" # Data collection
}

# Model Configuration
MODEL_SAVE_PATH = "models/crypto_agent_ppo.zip"
MODEL_CHECKPOINT_PATH = "models/checkpoints/"

# Sub-agents (treino por símbolo com sinais reais)
SUB_AGENTS_BASE_DIR = os.getenv("SUB_AGENTS_BASE_DIR", "models/sub_agents")
SIGNAL_MIN_TRADES_FOR_RETRAINING = int(os.getenv("SIGNAL_MIN_TRADES_FOR_RETRAINING", "20"))
SIGNAL_RETRAINING_TIMESTEPS = int(os.getenv("SIGNAL_RETRAINING_TIMESTEPS", "10000"))

# WebSocket Configuration
WS_RECONNECT_BACKOFF = [1, 2, 4, 8, 16, 30]  # seconds
WS_MAX_RECONNECT_DELAY = 30  # seconds

# Flash Crash Detection
FLASH_CRASH_THRESHOLD_PCT = 0.05  # 5% in 5 minutes
FLASH_CRASH_WINDOW_MINUTES = 5

# Liquidation Alert Threshold
LIQUIDATION_ALERT_MULTIPLIER = 2.0  # Alert if > 2x 24h average

# Data Validation
ALLOW_DATA_GAPS = False  # Never interpolate missing data
MAX_ALLOWED_GAP_CANDLES = 1

# Performance Tracking
PERFORMANCE_WINDOW_DAYS = 14  # Check for degradation over 14 days
WEEKLY_REPORT_DAY = 0  # Monday

# Cleanup Configuration
CLEANUP_DAYS_KEEP = 90  # Keep data for 90 days

# Position Monitor - Minimum Candles Configuration
# Número mínimo de candles necessários para cálculo de indicadores
MONITOR_MIN_CANDLES_H4 = 700  # Para cobrir EMA(610) com margem
MONITOR_MIN_CANDLES_H1 = 250  # Para cobrir EMA(144) e SMC com margem
MONITOR_FRESH_CANDLES = 50    # Candles frescos a buscar da API
