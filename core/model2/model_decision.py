"""Contrato unico de decisao do modelo para o Modelo 2.0 (M2-020.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

M2_020_1_RULE_ID = "M2-020.1-RULE-MODEL-DECISION-CONTRACT"

ACTION_OPEN_LONG = "OPEN_LONG"
ACTION_OPEN_SHORT = "OPEN_SHORT"
ACTION_HOLD = "HOLD"
ACTION_REDUCE = "REDUCE"
ACTION_CLOSE = "CLOSE"

OFFICIAL_MODEL_ACTIONS = (
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    ACTION_HOLD,
    ACTION_REDUCE,
    ACTION_CLOSE,
)


class ModelDecisionValidationError(ValueError):
    """Erro de validacao do payload de decisao do modelo."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class ModelDecisionInput:
    """Entrada canonica para inferencia da decisao model-driven."""

    symbol: str
    timeframe: str
    decision_timestamp: int
    model_version: str
    market_state: Mapping[str, Any]
    position_state: Mapping[str, Any]
    risk_state: Mapping[str, Any]


@dataclass(frozen=True)
class ModelDecision:
    """Saida canonica de decisao do modelo com campos obrigatorios."""

    action: str
    confidence: float
    size_fraction: float
    sl_target: float | None
    tp_target: float | None
    reason_code: str
    decision_timestamp: int
    symbol: str
    model_version: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class ModelDecisionOutcome:
    """Resultado de validacao com bloqueio seguro para payload invalido."""

    allow_execution: bool
    decision: ModelDecision | None
    reason: str
    rule_id: str
    details: Mapping[str, Any]


def _to_float(value: Any, *, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ModelDecisionValidationError(
            "invalid_numeric_field",
            f"campo numerico invalido: {field_name}",
        ) from exc


def _validate_required_fields(payload: Mapping[str, Any]) -> None:
    required_fields = ("action", "confidence", "size_fraction", "sl", "tp", "reason")
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ModelDecisionValidationError(
            "missing_required_fields",
            f"campos obrigatorios ausentes: {', '.join(missing)}",
        )


def parse_model_decision_payload(
    model_input: ModelDecisionInput,
    payload: Mapping[str, Any],
) -> ModelDecision:
    """Valida e converte payload bruto para o contrato canonico de decisao."""

    _validate_required_fields(payload)

    action = str(payload["action"]).strip().upper()
    if action not in OFFICIAL_MODEL_ACTIONS:
        raise ModelDecisionValidationError(
            "unsupported_action",
            f"acao de decisao nao suportada: {action}",
        )

    confidence = _to_float(payload["confidence"], field_name="confidence")
    if confidence < 0.0 or confidence > 1.0:
        raise ModelDecisionValidationError(
            "confidence_out_of_range",
            "confidence deve estar entre 0.0 e 1.0",
        )

    size_fraction = _to_float(payload["size_fraction"], field_name="size_fraction")
    if size_fraction < 0.0 or size_fraction > 1.0:
        raise ModelDecisionValidationError(
            "size_fraction_out_of_range",
            "size_fraction deve estar entre 0.0 e 1.0",
        )

    sl_raw = payload.get("sl")
    tp_raw = payload.get("tp")
    sl_target = None if sl_raw is None else _to_float(sl_raw, field_name="sl")
    tp_target = None if tp_raw is None else _to_float(tp_raw, field_name="tp")

    reason_code = str(payload["reason"]).strip()
    if not reason_code:
        raise ModelDecisionValidationError(
            "empty_reason_code",
            "reason deve ser nao vazio",
        )

    if action == ACTION_HOLD and size_fraction != 0.0:
        raise ModelDecisionValidationError(
            "hold_requires_zero_size",
            "acao HOLD exige size_fraction igual a 0.0",
        )

    if action in {ACTION_OPEN_LONG, ACTION_OPEN_SHORT}:
        if sl_target is None or tp_target is None:
            raise ModelDecisionValidationError(
                "missing_protection_targets",
                "acoes de abertura exigem sl e tp definidos",
            )
        if size_fraction <= 0.0:
            raise ModelDecisionValidationError(
                "non_positive_size_fraction",
                "acoes de abertura exigem size_fraction > 0",
            )
        if action == ACTION_OPEN_LONG and sl_target >= tp_target:
            raise ModelDecisionValidationError(
                "invalid_long_protection_geometry",
                "OPEN_LONG exige sl < tp",
            )
        if action == ACTION_OPEN_SHORT and tp_target >= sl_target:
            raise ModelDecisionValidationError(
                "invalid_short_protection_geometry",
                "OPEN_SHORT exige tp < sl",
            )

    return ModelDecision(
        action=action,
        confidence=confidence,
        size_fraction=size_fraction,
        sl_target=sl_target,
        tp_target=tp_target,
        reason_code=reason_code,
        decision_timestamp=model_input.decision_timestamp,
        symbol=model_input.symbol,
        model_version=model_input.model_version,
        metadata=dict(payload.get("metadata", {})),
    )


def evaluate_model_decision_payload(
    model_input: ModelDecisionInput,
    payload: Mapping[str, Any],
) -> ModelDecisionOutcome:
    """Valida payload de decisao com fail-safe para bloqueio operacional."""

    try:
        decision = parse_model_decision_payload(model_input, payload)
    except ModelDecisionValidationError as exc:
        return ModelDecisionOutcome(
            allow_execution=False,
            decision=None,
            reason="invalid_model_decision_payload",
            rule_id=M2_020_1_RULE_ID,
            details={
                "error_code": exc.error_code,
                "error_message": str(exc),
                "symbol": model_input.symbol,
                "model_version": model_input.model_version,
            },
        )

    return ModelDecisionOutcome(
        allow_execution=True,
        decision=decision,
        reason="decision_payload_valid",
        rule_id=M2_020_1_RULE_ID,
        details={
            "action": decision.action,
            "symbol": decision.symbol,
            "model_version": decision.model_version,
        },
    )
