"""Deterministic validator for Model 2.0 monitoring stage (M2-003.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ValidationInput:
    """Input payload for monitoring-stage validation."""

    opportunity_id: int
    symbol: str
    timeframe: str
    side: str
    trigger_price: float
    zone_low: float
    monitoring_started_at: int | None
    metadata: Mapping[str, Any]
    candles: Sequence[Mapping[str, Any]]
    validation_timestamp: int


@dataclass(frozen=True)
class ValidationDecision:
    """Validation outcome for a monitored thesis."""

    is_validated: bool
    reason: str
    details: Mapping[str, Any]


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _visible_rejection(rejection: Mapping[str, Any], zone_low: float) -> bool:
    open_price = _to_float(rejection.get("open"))
    close_price = _to_float(rejection.get("close"))
    high_price = _to_float(rejection.get("high"))
    low_price = _to_float(rejection.get("low"))
    if None in (open_price, close_price, high_price, low_price):
        return False

    if close_price >= zone_low:
        return False

    body = abs(close_price - open_price)
    upper_wick = high_price - max(open_price, close_price)
    lower_wick = min(open_price, close_price) - low_price
    return upper_wick > body and upper_wick > lower_wick and upper_wick > 0


def _find_trigger_break_after_monitoring(
    candles: Sequence[Mapping[str, Any]],
    *,
    trigger_price: float,
    monitoring_started_at: int,
) -> dict[str, Any] | None:
    for candle in candles:
        ts = _to_int(candle.get("timestamp"))
        low_price = _to_float(candle.get("low"))
        if ts is None or low_price is None:
            continue
        if ts <= monitoring_started_at:
            continue
        if low_price < trigger_price:
            return {
                "timestamp": ts,
                "low": low_price,
            }
    return None


def evaluate_monitoring_validation(validation_input: ValidationInput) -> ValidationDecision:
    """Evaluate if a MONITORANDO thesis can transition to VALIDADA."""

    if validation_input.side != "SHORT":
        return ValidationDecision(
            is_validated=False,
            reason="unsupported_side",
            details={"side": validation_input.side},
        )

    monitoring_started_at = validation_input.monitoring_started_at
    if monitoring_started_at is None:
        return ValidationDecision(
            is_validated=False,
            reason="missing_monitoring_start",
            details={},
        )

    rejection = validation_input.metadata.get("rejection_candle")
    if not isinstance(rejection, Mapping):
        return ValidationDecision(
            is_validated=False,
            reason="missing_rejection_candle",
            details={},
        )

    if not _visible_rejection(rejection, zone_low=validation_input.zone_low):
        return ValidationDecision(
            is_validated=False,
            reason="invalid_rejection_candle",
            details={},
        )

    trigger_break = _find_trigger_break_after_monitoring(
        validation_input.candles,
        trigger_price=validation_input.trigger_price,
        monitoring_started_at=monitoring_started_at,
    )
    if trigger_break is None:
        return ValidationDecision(
            is_validated=False,
            reason="trigger_not_broken_after_monitoring",
            details={
                "monitoring_started_at": monitoring_started_at,
                "trigger_price": validation_input.trigger_price,
            },
        )

    details = {
        "monitoring_started_at": monitoring_started_at,
        "trigger_price": validation_input.trigger_price,
        "confirmation_candle": trigger_break,
        "rule_checks": {
            "rejection_confirmed": True,
            "trigger_break_after_monitoring": True,
        },
        "validation_timestamp": validation_input.validation_timestamp,
    }
    return ValidationDecision(
        is_validated=True,
        reason="ok",
        details=details,
    )
