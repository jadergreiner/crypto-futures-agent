from core.model2.order_layer import OrderLayerInput, evaluate_signal_for_order_layer


def _input(signal_side: str) -> OrderLayerInput:
    return OrderLayerInput(
        signal_id=1,
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side=signal_side,
        entry_type="MARKET",
        entry_price=100.0,
        stop_loss=110.0 if signal_side == "SHORT" else 90.0,
        take_profit=90.0 if signal_side == "SHORT" else 110.0,
        status="CREATED",
        signal_timestamp=1_700_000_000_000,
        payload={},
        decision_timestamp=1_700_000_000_500,
    )


def test_order_layer_cancels_long_when_short_only_enabled() -> None:
    decision = evaluate_signal_for_order_layer(_input("LONG"), short_only=True)
    assert decision.target_status == "CANCELLED"
    assert decision.reason == "short_only_enforced"


def test_order_layer_consumes_short_when_short_only_enabled() -> None:
    decision = evaluate_signal_for_order_layer(_input("SHORT"), short_only=True)
    assert decision.target_status == "CONSUMED"
