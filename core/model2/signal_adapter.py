"""Adapter from Model2 technical_signals to legacy trade_signals (M2-007.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

M2_007_2_RULE_ID = "M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL"
ADAPTER_EXPORT_KEY = "adapter_export_trade_signals"
ADAPTER_LAST_ERROR_KEY = "last_error"
LEGACY_EXECUTION_MODE = "PENDING"
LEGACY_STATUS = "ACTIVE"


@dataclass(frozen=True)
class SignalAdapterInput:
    """Input payload for conversion from technical_signals to trade_signals."""

    technical_signal_id: int
    opportunity_id: int
    symbol: str
    timeframe: str
    signal_side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str
    signal_timestamp: int
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class SignalAdapterResult:
    """Adapter result for legacy trade_signals dual-write."""

    exportable: bool
    reason: str
    payload: Mapping[str, Any] | None


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def build_legacy_trade_signal_payload(adapter_input: SignalAdapterInput) -> SignalAdapterResult:
    """Build payload compatible with DatabaseManager.insert_trade_signal."""

    if adapter_input.status != "CONSUMED":
        return SignalAdapterResult(exportable=False, reason="status_not_consumed", payload=None)
    if adapter_input.signal_side not in {"LONG", "SHORT"}:
        return SignalAdapterResult(exportable=False, reason="unsupported_signal_side", payload=None)

    risk_distance = abs(float(adapter_input.entry_price) - float(adapter_input.stop_loss))
    if risk_distance <= 0:
        return SignalAdapterResult(exportable=False, reason="non_positive_risk_distance", payload=None)

    if adapter_input.signal_side == "LONG":
        take_profit_1 = float(adapter_input.entry_price) + risk_distance
        take_profit_2 = float(adapter_input.entry_price) + (1.5 * risk_distance)
    else:
        take_profit_1 = float(adapter_input.entry_price) - risk_distance
        take_profit_2 = float(adapter_input.entry_price) - (1.5 * risk_distance)

    rr_ratio = abs(float(adapter_input.take_profit) - float(adapter_input.entry_price)) / risk_distance
    source_payload = _safe_dict(adapter_input.payload)
    confluence_details = {
        "adapter": "m2_007_2",
        "rule_id": M2_007_2_RULE_ID,
        "m2_technical_signal_id": int(adapter_input.technical_signal_id),
        "m2_opportunity_id": int(adapter_input.opportunity_id),
        "m2_timeframe": str(adapter_input.timeframe),
        "m2_source_payload": source_payload,
        "would_send_real_order": False,
    }

    payload = {
        "timestamp": int(adapter_input.signal_timestamp),
        "symbol": str(adapter_input.symbol),
        "direction": str(adapter_input.signal_side),
        "entry_price": float(adapter_input.entry_price),
        "stop_loss": float(adapter_input.stop_loss),
        "take_profit_1": float(take_profit_1),
        "take_profit_2": float(take_profit_2),
        "take_profit_3": float(adapter_input.take_profit),
        "position_size_suggested": None,
        "risk_pct": None,
        "risk_reward_ratio": float(rr_ratio),
        "leverage_suggested": None,
        "confluence_score": 0.0,
        "confluence_details": json.dumps(confluence_details, ensure_ascii=True, sort_keys=True),
        "rsi_14": None,
        "ema_17": None,
        "ema_34": None,
        "ema_72": None,
        "ema_144": None,
        "macd_line": None,
        "macd_signal": None,
        "macd_histogram": None,
        "bb_upper": None,
        "bb_lower": None,
        "bb_percent_b": None,
        "atr_14": None,
        "adx_14": None,
        "di_plus": None,
        "di_minus": None,
        "market_structure": None,
        "bos_recent": 0,
        "choch_recent": 0,
        "nearest_ob_distance_pct": None,
        "nearest_fvg_distance_pct": None,
        "premium_discount_zone": None,
        "liquidity_above_pct": None,
        "liquidity_below_pct": None,
        "funding_rate": None,
        "long_short_ratio": None,
        "open_interest_change_pct": None,
        "fear_greed_value": None,
        "d1_bias": None,
        "h4_trend": None,
        "h1_trend": None,
        "market_regime": None,
        "execution_mode": LEGACY_EXECUTION_MODE,
        "executed_at": None,
        "executed_price": None,
        "execution_slippage_pct": None,
        "status": LEGACY_STATUS,
    }
    return SignalAdapterResult(exportable=True, reason="ok", payload=payload)
