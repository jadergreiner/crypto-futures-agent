from core.model2.order_layer import (
    M2_007_1_RULE_ID,
    OrderLayerInput,
    evaluate_signal_for_order_layer,
)


def _base_input() -> OrderLayerInput:
    return OrderLayerInput(
        signal_id=1,
        opportunity_id=10,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        entry_type="MARKET",
        entry_price=97.0,
        stop_loss=110.0,
        take_profit=84.0,
        status="CREATED",
        signal_timestamp=1_700_000_100_000,
        payload={},
        decision_timestamp=1_700_000_200_000,
    )


def test_order_layer_accepts_valid_created_signal() -> None:
    decision = evaluate_signal_for_order_layer(_base_input(), authorized_symbols={"BTCUSDT"})
    assert decision.should_transition is True
    assert decision.target_status == "CONSUMED"
    assert decision.reason == "decision_recorded_no_real_order"
    assert decision.rule_id == M2_007_1_RULE_ID
    assert decision.details["would_send_real_order"] is False


def test_order_layer_cancels_unauthorized_symbol() -> None:
    decision = evaluate_signal_for_order_layer(_base_input(), authorized_symbols={"ETHUSDT"})
    assert decision.should_transition is True
    assert decision.target_status == "CANCELLED"
    assert decision.reason == "symbol_not_authorized"


def test_order_layer_cancels_invalid_geometry() -> None:
    source = _base_input()
    decision = evaluate_signal_for_order_layer(
        OrderLayerInput(
            **{**source.__dict__, "take_profit": 109.0},
        ),
        authorized_symbols={"BTCUSDT"},
    )
    assert decision.should_transition is True
    assert decision.target_status == "CANCELLED"
    assert decision.reason == "invalid_price_geometry"


def test_order_layer_skips_non_created_signal() -> None:
    source = _base_input()
    decision = evaluate_signal_for_order_layer(
        OrderLayerInput(
            **{**source.__dict__, "status": "CONSUMED"},
        ),
        authorized_symbols={"BTCUSDT"},
    )
    assert decision.should_transition is False
    assert decision.target_status == "CONSUMED"
    assert decision.reason == "status_not_created"
