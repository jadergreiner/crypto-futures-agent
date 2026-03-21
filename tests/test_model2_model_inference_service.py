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
