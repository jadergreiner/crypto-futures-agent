from core.model2.live_execution import LiveExecutionGateInput, evaluate_live_execution_gate


def _base_gate_input() -> LiveExecutionGateInput:
    return LiveExecutionGateInput(
        technical_signal_id=1,
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        technical_signal_status="CONSUMED",
        signal_timestamp=1_700_000_000_000,
        short_only=True,
        funding_rate=-0.0001,
        basis_value=0.001,
        funding_rate_max_for_short=0.0005,
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        available_balance_usd=100.0,
        max_margin_per_position_usd=1.0,
        recent_entries_today=0,
        max_daily_entries=3,
        symbol_active_execution_count=0,
        open_position_qty=0.0,
        cooldown_active=False,
        signal_age_ms=1_000,
        max_signal_age_ms=240_000,
    )


def test_short_only_blocks_long_signal() -> None:
    gate_input = _base_gate_input()
    gate_input = LiveExecutionGateInput(**{**gate_input.__dict__, "signal_side": "LONG"})
    decision = evaluate_live_execution_gate(gate_input)
    assert decision.allow_execution is False
    assert decision.reason == "short_only_enforced"


def test_funding_gate_blocks_unfavorable_short() -> None:
    gate_input = _base_gate_input()
    gate_input = LiveExecutionGateInput(**{**gate_input.__dict__, "funding_rate": 0.0008})
    decision = evaluate_live_execution_gate(gate_input)
    assert decision.allow_execution is False
    assert decision.reason == "funding_unfavorable"


def test_basis_gate_blocks_negative_basis() -> None:
    gate_input = _base_gate_input()
    gate_input = LiveExecutionGateInput(**{**gate_input.__dict__, "basis_value": -0.0001})
    decision = evaluate_live_execution_gate(gate_input)
    assert decision.allow_execution is False
    assert decision.reason == "negative_basis"


def test_short_signal_with_valid_context_is_ready() -> None:
    decision = evaluate_live_execution_gate(_base_gate_input())
    assert decision.allow_execution is True
    assert decision.reason == "ready_for_live_execution"
