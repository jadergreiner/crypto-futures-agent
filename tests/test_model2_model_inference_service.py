from typing import Any, Mapping

from core.model2.model_decision import ACTION_OPEN_SHORT, ModelDecisionInput
from core.model2.model_inference_service import ModelInferenceService


class _FakeProvider:
    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        return {
            "action": ACTION_OPEN_SHORT,
            "confidence": 0.81,
            "size_fraction": 0.4,
            "sl": 110.0,
            "tp": 96.0,
            "reason": "provider_fake_ok",
        }


def _base_input() -> ModelDecisionInput:
    return ModelDecisionInput(
        symbol="BTCUSDT",
        timeframe="H4",
        decision_timestamp=1_700_001_000_000,
        model_version="m2-inference-v1",
        market_state={
            "signal_side": "SHORT",
            "entry_price": 100.0,
            "stop_loss": 110.0,
            "take_profit": 96.0,
        },
        position_state={},
        risk_state={},
    )


def test_model_inference_service_returns_validated_decision() -> None:
    service = ModelInferenceService(provider=_FakeProvider(), model_version="m2-vtest")
    result = service.infer(_base_input())

    assert result.accepted is True
    assert result.decision is not None
    assert result.model_version == "m2-vtest"
    assert result.decision.action == ACTION_OPEN_SHORT
    assert result.inference_latency_ms >= 0


def test_model_inference_service_rejects_invalid_provider_payload() -> None:
    class _InvalidProvider:
        def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
            return {
                "action": "UNKNOWN_ACTION",
                "confidence": 0.9,
                "size_fraction": 0.5,
                "sl": 90.0,
                "tp": 120.0,
                "reason": "payload_invalido",
            }

    service = ModelInferenceService(provider=_InvalidProvider(), model_version="m2-vtest")
    result = service.infer(_base_input())

    assert result.accepted is False
    assert result.decision is None
    assert result.reason == "invalid_model_decision_payload"


def test_model_inference_service_blocks_when_competence_checker_rejects() -> None:
    service = ModelInferenceService(
        provider=_FakeProvider(),
        model_version="m2-vtest",
        competence_checker=lambda _version: False,
    )

    result = service.infer(_base_input())

    assert result.accepted is False
    assert result.decision is None
    assert result.reason == "model_incompetent"
    assert result.details.get("competence_reason") == "competence_checker_rejected"


def test_model_inference_service_returns_fail_safe_when_provider_raises() -> None:
    class _ErrorProvider:
        def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
            raise RuntimeError("provider_down")

    service = ModelInferenceService(provider=_ErrorProvider(), model_version="m2-vtest")
    result = service.infer(_base_input())

    assert result.accepted is False
    assert result.decision is None
    assert result.reason == "inference_provider_error"
    assert result.details.get("error") == "provider_down"
