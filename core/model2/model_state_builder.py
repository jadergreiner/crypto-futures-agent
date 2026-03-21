"""Consolidador de estado de inferencia para o Modelo 2.0 (M2-020.3)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

from .model_decision import ModelDecisionInput

M2_020_3_RULE_ID = "M2-020.3-RULE-CONSOLIDATED-STATE"
M2_020_3_SCHEMA_VERSION = "m2-state-v1"


@dataclass(frozen=True)
class StateBuilderResult:
    """Resultado da montagem do estado com semântica fail-safe."""

    success: bool
    model_input: ModelDecisionInput | None
    error_code: str | None
    error_message: str | None
    diagnostics: Mapping[str, Any]
    generated_at_ms: int
    schema_version: str


def _safe_float(raw: Any, *, field: str) -> float:
    try:
        if raw is None:
            raise ValueError("valor nulo")
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"campo numerico invalido: {field}") from exc


def build_model_decision_input(
    *,
    candidate: Mapping[str, Any],
    decision_timestamp: int,
    model_version: str,
    execution_mode: str,
    max_margin_per_position_usd: float,
    position_state: Mapping[str, Any] | None = None,
    risk_context: Mapping[str, Any] | None = None,
) -> StateBuilderResult:
    """Monta estado único de inferência com validações críticas.

    Em caso de inconsistência crítica, retorna resultado com `success=False`
    para bloquear o fluxo de forma auditável (fail-safe).
    """

    now_ms = int(time.time() * 1000)

    try:
        symbol = str(candidate.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("symbol ausente")

        timeframe = str(candidate.get("timeframe") or "").strip().upper()
        if not timeframe:
            raise ValueError("timeframe ausente")

        signal_side = str(candidate.get("signal_side") or "").strip().upper()
        if signal_side not in {"LONG", "SHORT"}:
            raise ValueError("signal_side invalido")

        signal_timestamp = int(candidate.get("signal_timestamp") or 0)
        if signal_timestamp <= 0:
            raise ValueError("signal_timestamp invalido")

        entry_price = _safe_float(candidate.get("entry_price"), field="entry_price")
        stop_loss = _safe_float(candidate.get("stop_loss"), field="stop_loss")
        take_profit = _safe_float(candidate.get("take_profit"), field="take_profit")

        if signal_side == "LONG" and not (stop_loss < entry_price < take_profit):
            raise ValueError("geometria de preco invalida para LONG")
        if signal_side == "SHORT" and not (take_profit < entry_price < stop_loss):
            raise ValueError("geometria de preco invalida para SHORT")

        execution_mode_normalized = str(execution_mode).strip().lower()
        if execution_mode_normalized not in {"paper", "shadow", "live"}:
            raise ValueError("execution_mode invalido")

        margin_limit = float(max_margin_per_position_usd)
        if margin_limit <= 0:
            raise ValueError("max_margin_per_position_usd deve ser > 0")

        risk_state = {
            "execution_mode": execution_mode_normalized,
            "max_margin_per_position_usd": margin_limit,
            **dict(risk_context or {}),
        }

        model_input = ModelDecisionInput(
            symbol=symbol,
            timeframe=timeframe,
            decision_timestamp=int(decision_timestamp),
            model_version=str(model_version),
            market_state={
                "signal_side": signal_side,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "signal_timestamp": signal_timestamp,
            },
            position_state=dict(position_state or {}),
            risk_state=risk_state,
        )

        return StateBuilderResult(
            success=True,
            model_input=model_input,
            error_code=None,
            error_message=None,
            diagnostics={
                "builder_rule_id": M2_020_3_RULE_ID,
                "validated_fields": [
                    "symbol",
                    "timeframe",
                    "signal_side",
                    "entry_price",
                    "stop_loss",
                    "take_profit",
                    "signal_timestamp",
                    "execution_mode",
                    "max_margin_per_position_usd",
                ],
            },
            generated_at_ms=now_ms,
            schema_version=M2_020_3_SCHEMA_VERSION,
        )
    except Exception as exc:  # noqa: BLE001 - fail-safe explicit
        return StateBuilderResult(
            success=False,
            model_input=None,
            error_code="invalid_inference_state",
            error_message=str(exc),
            diagnostics={
                "builder_rule_id": M2_020_3_RULE_ID,
                "candidate_symbol": str(candidate.get("symbol") or ""),
                "candidate_timeframe": str(candidate.get("timeframe") or ""),
            },
            generated_at_ms=now_ms,
            schema_version=M2_020_3_SCHEMA_VERSION,
        )
