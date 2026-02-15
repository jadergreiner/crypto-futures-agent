"""
Risk management parameters - INVIOLABLE rules for position sizing and risk control.
"""

from typing import Dict, Any

RISK_PARAMS: Dict[str, Any] = {
    # Position Sizing
    "max_risk_per_trade_pct": 0.02,  # 2% of capital per trade
    "max_simultaneous_risk_pct": 0.06,  # 6% total risk across all positions
    "max_single_asset_exposure_pct": 0.40,  # 40% of capital in a single asset
    
    # Drawdown Limits
    "max_daily_drawdown_pct": 0.05,  # 5% → close all positions, block for 24h
    "max_total_drawdown_pct": 0.15,  # 15% → PAUSE agent completely
    
    # Position Limits
    "max_simultaneous_positions": 3,
    "max_leverage": 10,  # Isolated margin — atualizado para 10x
    
    # Stop Loss & Take Profit
    "stop_loss_atr_multiplier": 1.5,
    "take_profit_atr_multiplier": 3.0,
    "max_stop_distance_pct": 0.03,  # 3% maximum stop distance from entry
    
    # Trailing Stop
    "trailing_stop_activation_r": 1.5,  # Activate after 1.5x risk achieved
    "trailing_stop_atr_multiplier": 1.0,
    
    # Correlation & Diversification
    "max_correlation_overlap": 0.8,  # Don't open correlated positions
    
    # Overtrading Protection
    "overtrading_max_trades_24h": 3,
    
    # Confluence Requirements
    "confluence_min_score": 8,  # Minimum 8/14 to open position
    "confluence_full_size_score": 11,  # 11/14 for full position size
    
    # Entry Timing
    "entry_timeout_h1_candles": 12,  # Cancel signal after 12 H1 candles (12h)
    
    # R-Multiple Targets
    "target_r_multiple": 2.0,  # Target 2:1 reward:risk minimum
    "excellent_r_multiple": 3.0,  # Excellent trades at 3:1
    
    # Monitoring Thresholds
    "extreme_funding_rate_threshold": 0.05,  # 0.05% funding rate considerado extremo
    "trailing_stop_activation_r_multiple": 1.5,  # Ativar trailing stop após 1.5R
    
    # Cross Margin Risk
    "cross_margin_risk_multiplier": 1.5,  # Multiplicador de risco para posições em cross margin
}
