from core.model2.validator import (
    ValidationInput,
    evaluate_monitoring_validation,
)


def _base_input(candles: list[dict], metadata: dict | None = None) -> ValidationInput:
    return ValidationInput(
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        side="SHORT",
        trigger_price=97.0,
        zone_low=100.0,
        monitoring_started_at=50,
        metadata=metadata
        if metadata is not None
        else {
            "rejection_candle": {
                "timestamp": 40,
                "open": 100.0,
                "high": 111.0,
                "low": 97.0,
                "close": 98.0,
            }
        },
        candles=candles,
        validation_timestamp=1000,
    )


def test_validate_monitoring_short_success() -> None:
    candles = [
        {"timestamp": 49, "low": 98.0},
        {"timestamp": 51, "low": 96.5},
    ]
    decision = evaluate_monitoring_validation(_base_input(candles))

    assert decision.is_validated is True
    assert decision.reason == "ok"
    assert decision.details["confirmation_candle"]["timestamp"] == 51


def test_validate_monitoring_fails_without_rejection_payload() -> None:
    candles = [
        {"timestamp": 51, "low": 96.5},
    ]
    decision = evaluate_monitoring_validation(
        _base_input(candles, metadata={"context": {"market_structure": "range"}})
    )

    assert decision.is_validated is False
    assert decision.reason == "missing_rejection_candle"


def test_validate_monitoring_fails_when_trigger_not_broken_after_monitoring() -> None:
    candles = [
        {"timestamp": 51, "low": 97.0},
        {"timestamp": 55, "low": 97.1},
    ]
    decision = evaluate_monitoring_validation(_base_input(candles))

    assert decision.is_validated is False
    assert decision.reason == "trigger_not_broken_after_monitoring"


def test_validate_monitoring_long_accepted() -> None:
    """Test that LONG side is now accepted in monitoring validation."""
    # For LONG: trigger_price is the resistance level, we look for HIGH > trigger_price
    candles = [
        {"timestamp": 49, "high": 96.0},
        {"timestamp": 51, "high": 97.5},  # HIGH breaks above trigger_price (97.0)
    ]
    # For LONG, rejection_candle should be above zone_low with visible lower wicks
    # (pattern of being rejected from lower prices)
    long_metadata = {
        "rejection_candle": {
            "timestamp": 40,
            "open": 110.0,
            "high": 115.0,  # High wick
            "low": 100.0,   # Very strong lower wick (rejected from below)
            "close": 112.0,  # Closed near the top, above zone
        }
    }
    long_input = ValidationInput(
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        side="LONG",
        trigger_price=97.0,  # For LONG, this is the breakout level
        zone_low=105.0,  # For LONG, rejection must be ABOVE this (close > zone_low)
        monitoring_started_at=50,
        metadata=long_metadata,
        candles=candles,
        validation_timestamp=1000,
    )
    decision = evaluate_monitoring_validation(long_input)

    # LONG should now be accepted (same logic as SHORT, but with HIGH instead of LOW)
    assert decision.is_validated is True
    assert decision.reason == "ok"


def test_validate_monitoring_fails_with_invalid_side() -> None:
    """Test that truly invalid sides are still rejected."""
    candles = [{"timestamp": 51, "low": 96.0}]
    base = _base_input(candles)
    invalid_side = ValidationInput(
        opportunity_id=base.opportunity_id,
        symbol=base.symbol,
        timeframe=base.timeframe,
        side="NEUTRAL",  # Invalid side
        trigger_price=base.trigger_price,
        zone_low=base.zone_low,
        monitoring_started_at=base.monitoring_started_at,
        metadata=base.metadata,
        candles=base.candles,
        validation_timestamp=base.validation_timestamp,
    )
    decision = evaluate_monitoring_validation(invalid_side)

    assert decision.is_validated is False
    assert decision.reason == "unsupported_side"
