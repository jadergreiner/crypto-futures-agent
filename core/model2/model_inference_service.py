"""Servico desacoplado de inferencia para decisao model-driven (M2-020.2)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .model_decision import (
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    M2_020_1_RULE_ID,
    ModelDecision,
    ModelDecisionInput,
    evaluate_model_decision_payload,
)

M2_020_2_RULE_ID = "M2-020.2-RULE-DECOUPLED-INFERENCE-SERVICE"
DEFAULT_MODEL_VERSION = "m2-inference-v1"


class InferenceProvider(Protocol):
    """Contrato de provider de inferencia para permitir troca de implementacao."""

    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class InferenceServiceResult:
    """Resultado de inferencia com telemetria operacional."""

    accepted: bool
    decision: ModelDecision | None
    model_version: str
    inference_latency_ms: int
    reason: str
    rule_id: str
    details: Mapping[str, Any]


class TechnicalSignalInferenceProvider:
    """Provider inicial para M2-020.2 com inferencia baseada no candidato atual.

    Mantem o comportamento estavel enquanto desacopla o ponto de decisao.
    """

    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        signal_side = str(model_input.market_state.get("signal_side") or "").upper()
        if signal_side == "LONG":
            action = ACTION_OPEN_LONG
        elif signal_side == "SHORT":
            action = ACTION_OPEN_SHORT
        else:
            action = "HOLD"

        sl_value = model_input.market_state.get("stop_loss")
        tp_value = model_input.market_state.get("take_profit")
        if action == "HOLD":
            size_fraction = 0.0
            sl_value = None
            tp_value = None
            confidence = 0.50
        else:
            size_fraction = 1.0
            confidence = 0.72

        return {
            "action": action,
            "confidence": confidence,
            "size_fraction": size_fraction,
            "sl": sl_value,
            "tp": tp_value,
            "reason": "inference_from_technical_signal_candidate",
            "metadata": {
                "provider": "TechnicalSignalInferenceProvider",
                "source_rule_id": M2_020_1_RULE_ID,
            },
        }


class ModelInferenceService:
    """Executa inferencia de forma desacoplada e retorna decisao validada."""

    def __init__(
        self,
        *,
        provider: InferenceProvider | None = None,
        model_version: str = DEFAULT_MODEL_VERSION,
    ) -> None:
        self._provider = provider or TechnicalSignalInferenceProvider()
        self._model_version = str(model_version)

    @property
    def model_version(self) -> str:
        return self._model_version

    def infer(self, model_input: ModelDecisionInput) -> InferenceServiceResult:
        started = time.perf_counter()
        raw_payload = self._provider.infer(model_input)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        outcome = evaluate_model_decision_payload(model_input, raw_payload)
        return InferenceServiceResult(
            accepted=bool(outcome.allow_execution and outcome.decision is not None),
            decision=outcome.decision,
            model_version=self._model_version,
            inference_latency_ms=max(0, elapsed_ms),
            reason=str(outcome.reason),
            rule_id=M2_020_2_RULE_ID,
            details=dict(outcome.details),
        )
