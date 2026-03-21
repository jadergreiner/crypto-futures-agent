from core.model2.model_state_builder import (
    M2_020_3_RULE_ID,
    M2_020_3_SCHEMA_VERSION,
    build_model_decision_input,
)


def _candidate_base() -> dict:
    return {
        "symbol": "BTCUSDT",
        "timeframe": "H4",
        "signal_side": "SHORT",
        "entry_price": 100.0,
        "stop_loss": 110.0,
        "take_profit": 96.0,
        "signal_timestamp": 1_700_000_000_000,
        "entry_type": "MARKET",
        "opportunity_id": 42,
        "rule_id": "M2-006.1-RULE-STANDARD-SIGNAL",
        "payload_json": {
            "funding_rate": 0.0004,
            "market_context": {
                "basis": 0.0012,
                "market_regime": "risk_on",
            },
            "zone_low": 100.0,
            "zone_high": 110.0,
        },
    }


def test_build_model_decision_input_success_returns_serializable_state() -> None:
    result = build_model_decision_input(
        candidate=_candidate_base(),
        decision_timestamp=1_700_000_000_100,
        model_version="m2-inference-v1",
        execution_mode="shadow",
        max_margin_per_position_usd=1.0,
        position_state={"has_open_position": False},
        risk_context={"recent_entries_today": 0},
    )

    assert result.success is True
    assert result.model_input is not None
    assert result.error_code is None
    assert result.schema_version == M2_020_3_SCHEMA_VERSION
    assert result.model_input.symbol == "BTCUSDT"
    assert result.model_input.market_state["signal_side"] == "SHORT"
    assert result.model_input.market_state["entry_type"] == "MARKET"
    assert result.model_input.market_state["market_context"]["funding_rate"] == 0.0004
    assert result.model_input.market_state["market_context"]["basis"] == 0.0012
    assert result.model_input.risk_state["execution_mode"] == "shadow"
    assert result.model_input.risk_state["recent_entries_today"] == 0
    assert result.model_input.position_state["has_open_position"] is False


def test_build_model_decision_input_merges_explicit_market_context() -> None:
    result = build_model_decision_input(
        candidate=_candidate_base(),
        decision_timestamp=1_700_000_000_100,
        model_version="m2-inference-v1",
        execution_mode="shadow",
        max_margin_per_position_usd=1.0,
        market_context={"basis": 0.0025, "funding_rate": 0.0008},
        position_state={"has_open_position": True, "position_size_qty": 0.3},
        risk_context={"recent_entries_today": 1, "cooldown_active": True},
    )

    assert result.success is True
    assert result.model_input is not None
    assert result.model_input.market_state["market_context"]["basis"] == 0.0025
    assert result.model_input.market_state["market_context"]["funding_rate"] == 0.0008
    assert result.model_input.position_state["has_open_position"] is True
    assert result.model_input.risk_state["cooldown_active"] is True


def test_build_model_decision_input_fails_closed_when_symbol_missing() -> None:
    candidate = _candidate_base()
    candidate["symbol"] = ""

    result = build_model_decision_input(
        candidate=candidate,
        decision_timestamp=1_700_000_000_100,
        model_version="m2-inference-v1",
        execution_mode="shadow",
        max_margin_per_position_usd=1.0,
    )

    assert result.success is False
    assert result.model_input is None
    assert result.error_code == "invalid_inference_state"
    assert result.error_message is not None
    assert "symbol" in result.error_message
    assert result.diagnostics["builder_rule_id"] == M2_020_3_RULE_ID


def test_build_model_decision_input_fails_closed_when_model_version_missing() -> None:
    result = build_model_decision_input(
        candidate=_candidate_base(),
        decision_timestamp=1_700_000_000_100,
        model_version=" ",
        execution_mode="shadow",
        max_margin_per_position_usd=1.0,
    )

    assert result.success is False
    assert result.model_input is None
    assert result.error_code == "invalid_inference_state"
    assert result.error_message is not None
    assert "model_version" in result.error_message
