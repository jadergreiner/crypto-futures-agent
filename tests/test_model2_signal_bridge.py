from core.model2.signal_bridge import (
    M2_006_1_RULE_ID,
    SignalBridgeInput,
    build_standard_signal,
)


def _base_input() -> SignalBridgeInput:
    return SignalBridgeInput(
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        side="SHORT",
        status="VALIDADA",
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata={},
        signal_timestamp=1_700_000_100_000,
    )


def test_build_standard_signal_from_validated_short() -> None:
    result = build_standard_signal(_base_input())
    assert result.eligible is True
    assert result.reason == "ok"
    assert result.signal_side == "SHORT"
    assert result.entry_type == "MARKET"
    assert result.entry_price == 97.0
    assert result.stop_loss == 110.0
    assert result.take_profit == 84.0
    assert result.status == "CREATED"
    assert result.rule_id == M2_006_1_RULE_ID


def test_build_standard_signal_rejects_non_validated_status() -> None:
    data = _base_input()
    rejected = build_standard_signal(
        SignalBridgeInput(
            **{**data.__dict__, "status": "MONITORANDO"},
        )
    )
    assert rejected.eligible is False
    assert rejected.reason == "status_not_validada"


def test_build_standard_signal_rejects_invalid_side() -> None:
    data = _base_input()
    rejected = build_standard_signal(
        SignalBridgeInput(
            **{**data.__dict__, "side": "BUY"},
        )
    )
    assert rejected.eligible is False
    assert rejected.reason == "unsupported_side"
