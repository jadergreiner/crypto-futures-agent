"""Deterministic signal bridge for Model 2.0 validated theses (M2-006.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

M2_006_1_RULE_ID = "M2-006.1-RULE-STANDARD-SIGNAL"
DEFAULT_ENTRY_TYPE = "MARKET"
DEFAULT_SIGNAL_STATUS = "CREATED"


@dataclass(frozen=True)
class SignalBridgeInput:
    """Input payload to convert a validated opportunity into a standard signal."""

    opportunity_id: int
    symbol: str
    timeframe: str
    side: str
    status: str
    zone_low: float
    zone_high: float
    trigger_price: float
    invalidation_price: float
    metadata: Mapping[str, Any]
    signal_timestamp: int


@dataclass(frozen=True)
class SignalBridgeResult:
    """Signal bridge decision output."""

    eligible: bool
    reason: str
    signal_side: str | None
    entry_type: str | None
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    status: str | None
    rule_id: str
    payload: Mapping[str, Any]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_standard_signal(signal_input: SignalBridgeInput) -> SignalBridgeResult:
    """Build standard signal fields for a VALIDADA thesis."""

    if signal_input.status != "VALIDADA":
        return SignalBridgeResult(
            eligible=False,
            reason="status_not_validada",
            signal_side=None,
            entry_type=None,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            status=None,
            rule_id=M2_006_1_RULE_ID,
            payload={"current_status": signal_input.status},
        )

    side = signal_input.side
    if side not in {"LONG", "SHORT"}:
        return SignalBridgeResult(
            eligible=False,
            reason="unsupported_side",
            signal_side=None,
            entry_type=None,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            status=None,
            rule_id=M2_006_1_RULE_ID,
            payload={"side": side},
        )

    entry_price = _safe_float(signal_input.trigger_price)
    stop_loss = _safe_float(signal_input.invalidation_price)
    if entry_price is None or stop_loss is None:
        return SignalBridgeResult(
            eligible=False,
            reason="invalid_price_fields",
            signal_side=None,
            entry_type=None,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            status=None,
            rule_id=M2_006_1_RULE_ID,
            payload={},
        )

    risk_distance = abs(stop_loss - entry_price)
    if risk_distance <= 0:
        return SignalBridgeResult(
            eligible=False,
            reason="non_positive_risk_distance",
            signal_side=None,
            entry_type=None,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            status=None,
            rule_id=M2_006_1_RULE_ID,
            payload={"entry_price": entry_price, "stop_loss": stop_loss},
        )

    take_profit = entry_price + risk_distance if side == "LONG" else entry_price - risk_distance
    payload = {
        "opportunity_id": signal_input.opportunity_id,
        "symbol": signal_input.symbol,
        "timeframe": signal_input.timeframe,
        "bridge_timestamp": signal_input.signal_timestamp,
        "source_status": signal_input.status,
        "zone_low": signal_input.zone_low,
        "zone_high": signal_input.zone_high,
    }
    return SignalBridgeResult(
        eligible=True,
        reason="ok",
        signal_side=side,
        entry_type=DEFAULT_ENTRY_TYPE,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        status=DEFAULT_SIGNAL_STATUS,
        rule_id=M2_006_1_RULE_ID,
        payload=payload,
    )
