"""
Execution configuration — Profit Guardian mode.
Controls which symbols can be auto-managed and execution safety parameters.
"""

from typing import Dict, Any, Set
from config.symbols import ALL_SYMBOLS

# ============================================================================
# AUTHORIZED SYMBOLS — Only these symbols can have orders executed automatically
# Mantido automaticamente a partir de config.symbols.ALL_SYMBOLS.
# Para incluir novos símbolos na whitelist, basta adicioná-los em config/symbols.py.
# ============================================================================
AUTHORIZED_SYMBOLS: Set[str] = set(ALL_SYMBOLS)

# ============================================================================
# EXECUTION PARAMETERS
# ============================================================================
EXECUTION_CONFIG: Dict[str, Any] = {
    # Minimum confidence to execute an order (0.0 to 1.0)
    # Agent must be at least 70% confident to trigger execution
    "min_confidence_to_execute": 0.70,

    # Maximum number of executions per day (resets at 00:00 UTC)
    # With up to 13 symbols, this allows headroom for multiple positions
    "max_daily_executions": 10,

    # Cooldown in seconds between executions on the SAME symbol
    # 900s = 15 minutes = 3 monitor cycles at 5min interval
    "cooldown_per_symbol_seconds": 900,

    # Allowed actions — Allow OPEN, CLOSE, and REDUCE_50
    # Phase 1: Testing with 10x leverage, $1 margin per position
    "allowed_actions": ["OPEN", "CLOSE", "REDUCE_50"],

    # Reduce percentage for REDUCE_50 action
    "reduce_50_pct": 0.50,

    # ========================================================================
    # POSITION SIZING — $1 margin per position, 10x leverage
    # ========================================================================
    # Margem máxima por posição em USD (Binance USDS-M Futures)
    "max_margin_per_position_usd": 1.0,

    # Alavancagem fixa para todas posições
    "leverage": 10,

    # Exposição máxima por posição (margem × leverage)
    "max_exposure_per_position_usd": 10.0,  # $1 × 10 = $10

    # Máximo de posições simultâneas (com $420 margem, pode ter ~40)
    "max_concurrent_positions": 30,

    # Margem total máxima alocada (buffer de $4 para volatilidade)
    "max_total_margin_usd": 40.0,

    # Stop loss automático em % (10% = liquidação com 10x)
    "auto_stop_loss_pct": 10.0,

    # Margin type (CROSS para compartilhar margem entre posições)
    "margin_type": "CROSS",

    # ========================================================================
    # ORDER TYPE & EXECUTION
    # ========================================================================
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
