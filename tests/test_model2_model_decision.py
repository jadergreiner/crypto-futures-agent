from core.model2.model_decision import (
    ACTION_HOLD,
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    M2_020_1_RULE_ID,
    ModelDecisionInput,
    ModelDecisionValidationError,
    evaluate_model_decision_payload,
    parse_model_decision_payload,
)


def _base_input() -> ModelDecisionInput:
    return ModelDecisionInput(
        symbol="BTCUSDT",
        timeframe="H4",
        decision_timestamp=1_700_000_100_000,
        model_version="ppo-v1",
        market_state={"close": 100.0},
        position_state={"qty": 0.0},
        risk_state={"max_risk": 0.01},
    )


def test_parse_model_decision_accepts_valid_open_long_payload() -> None:
    decision = parse_model_decision_payload(
        _base_input(),
        {
            "action": ACTION_OPEN_LONG,
            "confidence": 0.87,
            "size_fraction": 0.35,
            "sl": 95.0,
            "tp": 110.0,
            "reason": "breakout_confirmado",
        },
    )

    assert decision.action == ACTION_OPEN_LONG
    assert decision.confidence == 0.87
    assert decision.size_fraction == 0.35
    assert decision.sl_target == 95.0
    assert decision.tp_target == 110.0
    assert decision.reason_code == "breakout_confirmado"


def test_parse_model_decision_accepts_valid_hold_payload() -> None:
    decision = parse_model_decision_payload(
        _base_input(),
        {
            "action": ACTION_HOLD,
            "confidence": 0.61,
            "size_fraction": 0.0,
            "sl": None,
            "tp": None,
            "reason": "contexto_inconclusivo",
        },
    )

    assert decision.action == ACTION_HOLD
    assert decision.size_fraction == 0.0
    assert decision.sl_target is None
    assert decision.tp_target is None


def test_parse_model_decision_rejects_missing_required_fields() -> None:
    try:
        parse_model_decision_payload(
            _base_input(),
            {
                "action": ACTION_OPEN_SHORT,
                "confidence": 0.74,
                "size_fraction": 0.30,
                "sl": 105.0,
                "tp": 92.0,
            },
        )
        assert False, "era esperado ModelDecisionValidationError"
    except ModelDecisionValidationError as exc:
        assert exc.error_code == "missing_required_fields"


def test_parse_model_decision_rejects_hold_with_non_zero_size() -> None:
    try:
        parse_model_decision_payload(
            _base_input(),
            {
                "action": ACTION_HOLD,
                "confidence": 0.52,
                "size_fraction": 0.15,
                "sl": None,
                "tp": None,
                "reason": "aguardar",
            },
        )
        assert False, "era esperado ModelDecisionValidationError"
    except ModelDecisionValidationError as exc:
        assert exc.error_code == "hold_requires_zero_size"


def test_evaluate_model_decision_payload_blocks_invalid_payload_fail_safe() -> None:
    outcome = evaluate_model_decision_payload(
        _base_input(),
        {
            "action": "OPEN_UNKNOWN",
            "confidence": 0.90,
            "size_fraction": 0.10,
            "sl": 90.0,
            "tp": 120.0,
            "reason": "invalido",
        },
    )

    assert outcome.allow_execution is False
    assert outcome.decision is None
    assert outcome.reason == "invalid_model_decision_payload"
    assert outcome.rule_id == M2_020_1_RULE_ID
    assert outcome.details["error_code"] == "unsupported_action"


def test_evaluate_model_decision_payload_accepts_valid_payload() -> None:
    outcome = evaluate_model_decision_payload(
        _base_input(),
        {
            "action": ACTION_OPEN_SHORT,
            "confidence": 0.77,
            "size_fraction": 0.25,
            "sl": 110.0,
            "tp": 96.0,
            "reason": "confirmacao_tendencia",
        },
    )

    assert outcome.allow_execution is True
    assert outcome.decision is not None
    assert outcome.reason == "decision_payload_valid"
    assert outcome.decision.action == ACTION_OPEN_SHORT
