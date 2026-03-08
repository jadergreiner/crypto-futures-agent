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


def test_validate_monitoring_fails_with_unsupported_side() -> None:
    candles = [{"timestamp": 51, "low": 96.0}]
    base = _base_input(candles)
    invalid_side = ValidationInput(
        opportunity_id=base.opportunity_id,
        symbol=base.symbol,
        timeframe=base.timeframe,
        side="LONG",
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
