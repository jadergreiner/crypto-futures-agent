"""
Execution configuration — Profit Guardian mode.
Controls which symbols can be auto-managed and execution safety parameters.
"""

from typing import Dict, Any, List, Set

# ============================================================================
# AUTHORIZED SYMBOLS — Only these symbols can have orders executed automatically
# To add a new symbol, add it to this set. To disable, remove it.
# ============================================================================
AUTHORIZED_SYMBOLS: Set[str] = {
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "XRPUSDT",
    "LTCUSDT",
    "C98USDT",
}

# ============================================================================
# EXECUTION PARAMETERS
# ============================================================================
EXECUTION_CONFIG: Dict[str, Any] = {
    # Minimum confidence to execute an order (0.0 to 1.0)
    # Agent must be at least 70% confident to trigger execution
    "min_confidence_to_execute": 0.70,

    # Maximum number of executions per day (resets at 00:00 UTC)
    # With max 3 simultaneous positions, this allows ~2 actions per position per day
    "max_daily_executions": 6,

    # Cooldown in seconds between executions on the SAME symbol
    # 900s = 15 minutes = 3 monitor cycles at 5min interval
    "cooldown_per_symbol_seconds": 900,

    # Allowed actions — ONLY reduce/close, NEVER open
    # This is a hard safety guard: even if code has a bug, only these actions pass
    "allowed_actions": ["CLOSE", "REDUCE_50"],

    # Reduce percentage for REDUCE_50 action
    "reduce_50_pct": 0.50,

    # Order type for execution (MARKET for immediate fills)
    "order_type": "MARKET",

    # recv_window for Binance API calls (milliseconds)
    # Higher value = more tolerance for clock skew
    "recv_window": 10000,

    # Whether to verify position after execution
    "verify_after_execution": True,

    # Retry configuration for order placement
    "max_order_retries": 2,
    "order_retry_delay_seconds": 3,
}
