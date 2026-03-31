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
    "max_margin_per_position_usd": 15.0,

    # Volatility Sizing (M2-028.3)
    "volatility_sizing_defaults": {
        "min_multiplier": 0.35,
        "max_multiplier": 0.55,
        "low_vol_threshold_pct": 2.0,
        "high_vol_threshold_pct": 6.0,
        "min_size_fraction": 0.01,
        "max_size_fraction": 1.0,
    },
    "volatility_sizing_by_symbol": {
        "BTCUSDT": {
            "min_multiplier": 0.33,
            "max_multiplier": 0.52,
            "low_vol_threshold_pct": 1.8,
            "high_vol_threshold_pct": 5.8,
            "min_size_fraction": 0.01,
            "max_size_fraction": 0.95,
        },
        "ETHUSDT": {
            "min_multiplier": 0.34,
            "max_multiplier": 0.54,
            "low_vol_threshold_pct": 2.0,
            "high_vol_threshold_pct": 6.2,
            "min_size_fraction": 0.01,
            "max_size_fraction": 0.90,
        },
    },

    # Stop Loss & Take Profit
    "stop_loss_atr_multiplier": 1.5,
    "take_profit_atr_multiplier": 3.0,
    "max_stop_distance_pct": 0.03,  # 3% maximum stop distance from entry

    # Trailing Stop
    "trailing_stop_activation_r": 1.5,  # Activate after 1.5x risk achieved
    "trailing_stop_atr_multiplier": 1.0,

    # Correlation & Diversification
    "max_correlation_overlap": 0.8,           # Don't open correlated positions
    "max_positions_per_corr_group": 2,        # max posicoes abertas por grupo correlacionado
    "btc_correlation_high_threshold": 0.75,   # limiar para correlacao BTC ser considerada alta

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

    # Learning-Adaptive Controls (24h)
    "learning_profile_lookback_hours": 24,
    "learning_profile_cache_ttl_seconds": 300,
    "learning_profile_min_samples": 5,
    "learning_profile_adverse_loss_rate": 0.60,
    "learning_profile_adverse_avg_reward_threshold": -1.0,
    "learning_profile_dominant_share_threshold": 0.70,
    "learning_profile_dominant_min_samples": 20,

    # RL Model Degradation
    "degradation_threshold_win_rate": 0.40,  # Below 40% win rate triggers degradation
    "degradation_min_samples": 3,
    "degradation_eval_window": 10,  # Evaluate last 10 episodes
    "model_degradation_defaults": {
        "min_avg_confidence": 0.55,
        "min_hit_rate": 0.40,
        "min_hit_rate_delta": -0.20,
        "evaluation_window": 10,
        "min_samples": 3,
    },
    "model_degradation_thresholds_by_symbol": {
        "BTCUSDT": {
            "min_avg_confidence": 0.58,
            "min_hit_rate": 0.42,
            "min_hit_rate_delta": -0.18,
            "evaluation_window": 12,
            "min_samples": 4,
        },
        "ETHUSDT": {
            "min_avg_confidence": 0.56,
            "min_hit_rate": 0.40,
            "min_hit_rate_delta": -0.20,
            "evaluation_window": 10,
            "min_samples": 3,
        },
    },
}
