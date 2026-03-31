from typing import Any, Mapping

from core.model2.model_decision import ACTION_OPEN_SHORT, ModelDecisionInput
from core.model2.model_inference_service import (
    ModelInferenceService,
    TechnicalSignalInferenceProvider,
)
from core.model2.protection_head import ProtectionMultipliers


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


class _FakeLoader:
    def __init__(self, *, confidence: float, action: str) -> None:
        self._confidence = float(confidence)
        self._action = str(action)
        self.is_fallback = False
        self.fallback_reason = ""

    def predict_confidence(self, *, features: Any, signal_side: str) -> tuple[float, str]:
        _ = features
        _ = signal_side
        return self._confidence, self._action


def test_provider_dimensiona_alvos_quando_rl_alinhado() -> None:
    provider = TechnicalSignalInferenceProvider()
    provider._resolve_loader_for_symbol = lambda _symbol: _FakeLoader(confidence=0.9, action="SHORT")

    output = provider.infer(_base_input())

    assert output["action"] == "OPEN_SHORT"
    assert output["sl"] is not None
    assert output["tp"] is not None
    # Alinhado e confiante: altera alvos base (110/96) para dimensionamento dinâmico.
    assert float(output["sl"]) != 110.0
    assert float(output["tp"]) != 96.0
    assert output["metadata"]["protection_sizing_source"] == "rl_dynamic_aligned"


def test_provider_preserva_alvos_base_quando_risco_invalido() -> None:
    provider = TechnicalSignalInferenceProvider()
    provider._resolve_loader_for_symbol = lambda _symbol: _FakeLoader(confidence=0.8, action="SHORT")

    model_input = ModelDecisionInput(
        symbol="BTCUSDT",
        timeframe="H4",
        decision_timestamp=1_700_001_000_000,
        model_version="m2-inference-v1",
        market_state={
            "signal_side": "SHORT",
            "entry_price": 100.0,
            "stop_loss": 100.0,
            "take_profit": 96.0,
        },
        position_state={},
        risk_state={},
    )

    output = provider.infer(model_input)

    assert float(output["sl"]) == 100.0
    assert float(output["tp"]) == 96.0
    assert output["metadata"]["protection_sizing_source"] == "non_positive_risk_distance"


def test_provider_usa_output_explicito_do_protection_head() -> None:
    provider = TechnicalSignalInferenceProvider()
    provider._resolve_loader_for_symbol = lambda _symbol: _FakeLoader(confidence=0.7, action="SHORT")

    class _FakeHeadRegistry:
        def predict(self, *, symbol: str, features: Any) -> ProtectionMultipliers | None:
            _ = symbol
            _ = features
            return ProtectionMultipliers(
                sl_multiplier=0.90,
                tp_multiplier=1.40,
                source="trained_protection_head",
            )

    provider._protection_heads = _FakeHeadRegistry()  # type: ignore[assignment]

    output = provider.infer(_base_input())

    assert output["action"] == "OPEN_SHORT"
    assert output["metadata"]["protection_sizing_source"].startswith("rl_head_")
    assert "trained_protection_head" in output["metadata"]["protection_sizing_source"]


def test_provider_model_first_prioriza_acao_rl_sobre_lado_tecnico() -> None:
    provider = TechnicalSignalInferenceProvider(model_first=True)
    provider._resolve_loader_for_symbol = lambda _symbol: _FakeLoader(confidence=0.83, action="LONG")

    model_input = ModelDecisionInput(
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

    output = provider.infer(model_input)

    assert output["action"] == "OPEN_LONG"
    assert output["metadata"]["action_source"] == "rl_action"
    assert bool(output["metadata"]["model_first"]) is True
