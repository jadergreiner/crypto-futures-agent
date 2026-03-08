"""Deterministic resolver for Model 2.0 invalidation/expiration stage (M2-003.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


RESOLUTION_ACTION_NONE = "NONE"
RESOLUTION_ACTION_INVALIDATED = "INVALIDATED"
RESOLUTION_ACTION_EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ResolutionInput:
    """Input payload for monitoring-stage invalidation/expiration rules."""

    opportunity_id: int
    symbol: str
    timeframe: str
    side: str
    invalidation_price: float
    expires_at: int | None
    monitoring_started_at: int | None
    candles: Sequence[Mapping[str, Any]]
    resolution_timestamp: int


@dataclass(frozen=True)
class ResolutionDecision:
    """Resolution outcome for a monitored thesis."""

    action: str
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


def _find_invalidation_after_monitoring(
    candles: Sequence[Mapping[str, Any]],
    *,
    invalidation_price: float,
    monitoring_started_at: int,
) -> dict[str, Any] | None:
    for candle in candles:
        ts = _to_int(candle.get("timestamp"))
        close_price = _to_float(candle.get("close"))
        if ts is None or close_price is None:
            continue
        if ts <= monitoring_started_at:
            continue
        if close_price > invalidation_price:
            return {
                "timestamp": ts,
                "close": close_price,
            }
    return None


def evaluate_monitoring_resolution(resolution_input: ResolutionInput) -> ResolutionDecision:
    """Evaluate if a MONITORANDO thesis must be INVALIDADA or EXPIRADA."""

    if resolution_input.side != "SHORT":
        return ResolutionDecision(
            action=RESOLUTION_ACTION_NONE,
            reason="unsupported_side",
            details={"side": resolution_input.side},
        )

    monitoring_started_at = resolution_input.monitoring_started_at
    if monitoring_started_at is None:
        return ResolutionDecision(
            action=RESOLUTION_ACTION_NONE,
            reason="missing_monitoring_start",
            details={},
        )

    invalidation_candle = _find_invalidation_after_monitoring(
        resolution_input.candles,
        invalidation_price=resolution_input.invalidation_price,
        monitoring_started_at=monitoring_started_at,
    )

    expires_at = resolution_input.expires_at
    if invalidation_candle is not None and (
        expires_at is None or int(invalidation_candle["timestamp"]) <= int(expires_at)
    ):
        return ResolutionDecision(
            action=RESOLUTION_ACTION_INVALIDATED,
            reason="premise_broken",
            details={
                "monitoring_started_at": monitoring_started_at,
                "invalidation_price": resolution_input.invalidation_price,
                "invalidation_candle": invalidation_candle,
                "resolution_timestamp": resolution_input.resolution_timestamp,
            },
        )

    if expires_at is not None and resolution_input.resolution_timestamp > int(expires_at):
        return ResolutionDecision(
            action=RESOLUTION_ACTION_EXPIRED,
            reason="time_limit_reached",
            details={
                "monitoring_started_at": monitoring_started_at,
                "expires_at": int(expires_at),
                "resolution_timestamp": resolution_input.resolution_timestamp,
            },
        )

    return ResolutionDecision(
        action=RESOLUTION_ACTION_NONE,
        reason="no_resolution",
        details={
            "monitoring_started_at": monitoring_started_at,
            "invalidation_price": resolution_input.invalidation_price,
            "expires_at": expires_at,
            "resolution_timestamp": resolution_input.resolution_timestamp,
        },
    )
