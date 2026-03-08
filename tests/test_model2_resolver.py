from core.model2.resolver import (
    RESOLUTION_ACTION_EXPIRED,
    RESOLUTION_ACTION_INVALIDATED,
    RESOLUTION_ACTION_NONE,
    ResolutionInput,
    evaluate_monitoring_resolution,
)


def _base_input(
    candles: list[dict],
    *,
    expires_at: int | None = 200,
    resolution_timestamp: int = 150,
) -> ResolutionInput:
    return ResolutionInput(
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        side="SHORT",
        invalidation_price=110.0,
        expires_at=expires_at,
        monitoring_started_at=100,
        candles=candles,
        resolution_timestamp=resolution_timestamp,
    )


def test_resolver_invalidates_when_premise_breaks_before_expiration() -> None:
    decision = evaluate_monitoring_resolution(
        _base_input(
            candles=[
                {"timestamp": 101, "close": 109.0},
                {"timestamp": 120, "close": 111.0},
            ],
            expires_at=200,
            resolution_timestamp=150,
        )
    )
    assert decision.action == RESOLUTION_ACTION_INVALIDATED
    assert decision.reason == "premise_broken"
    assert decision.details["invalidation_candle"]["timestamp"] == 120


def test_resolver_expires_when_time_limit_reached_without_invalidation() -> None:
    decision = evaluate_monitoring_resolution(
        _base_input(
            candles=[
                {"timestamp": 120, "close": 109.0},
                {"timestamp": 140, "close": 108.0},
            ],
            expires_at=145,
            resolution_timestamp=200,
        )
    )
    assert decision.action == RESOLUTION_ACTION_EXPIRED
    assert decision.reason == "time_limit_reached"


def test_resolver_prioritizes_expiration_when_break_occurs_after_expiry() -> None:
    decision = evaluate_monitoring_resolution(
        _base_input(
            candles=[
                {"timestamp": 160, "close": 109.0},
                {"timestamp": 250, "close": 111.0},
            ],
            expires_at=200,
            resolution_timestamp=260,
        )
    )
    assert decision.action == RESOLUTION_ACTION_EXPIRED
    assert decision.reason == "time_limit_reached"


def test_resolver_keeps_monitoring_when_no_conditions_met() -> None:
    decision = evaluate_monitoring_resolution(
        _base_input(
            candles=[
                {"timestamp": 120, "close": 109.0},
            ],
            expires_at=300,
            resolution_timestamp=200,
        )
    )
    assert decision.action == RESOLUTION_ACTION_NONE
    assert decision.reason == "no_resolution"


def test_resolver_rejects_unsupported_side() -> None:
    base = _base_input([{"timestamp": 120, "close": 120.0}])
    decision = evaluate_monitoring_resolution(
        ResolutionInput(
            opportunity_id=base.opportunity_id,
            symbol=base.symbol,
            timeframe=base.timeframe,
            side="LONG",
            invalidation_price=base.invalidation_price,
            expires_at=base.expires_at,
            monitoring_started_at=base.monitoring_started_at,
            candles=base.candles,
            resolution_timestamp=base.resolution_timestamp,
        )
    )
    assert decision.action == RESOLUTION_ACTION_NONE
    assert decision.reason == "unsupported_side"
