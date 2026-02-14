"""
General settings and configuration for the crypto futures agent.
All sensitive data should be loaded from environment variables.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Binance API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_WS_URL = "wss://fstream.binance.com/ws/"

# Database Configuration
DB_PATH = "db/crypto_agent.db"

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
HISTORICAL_PERIODS = {
    "D1": 365,
    "H4": 180,
    "H1": 90
}

# Layer 4 (H4) execution times in UTC
H4_EXECUTION_HOURS = [0, 4, 8, 12, 16, 20]

# Funding rate times in UTC
FUNDING_RATE_HOURS = [0, 8, 16]

# API Retry Configuration
API_RETRY_ATTEMPTS = 3
API_RETRY_BACKOFF = [5, 15, 45]  # seconds

# Data Collection Limits
KLINES_LIMIT = 1500  # Max per Binance request
SENTIMENT_LIMIT = 30
FORCE_ORDERS_LIMIT = 100

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/agent.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Model Configuration
MODEL_SAVE_PATH = "models/crypto_agent_ppo.zip"
MODEL_CHECKPOINT_PATH = "models/checkpoints/"

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
