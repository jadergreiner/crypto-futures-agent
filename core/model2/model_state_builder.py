"""Consolidador de estado de inferencia para o Modelo 2.0 (M2-020.3)."""

from __future__ import annotations

import json
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


def _safe_json_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _lookup_nested(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _normalize_serializable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_serializable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_serializable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def build_model_decision_input(
    *,
    candidate: Mapping[str, Any],
    decision_timestamp: int,
    model_version: str,
    execution_mode: str,
    max_margin_per_position_usd: float,
    market_context: Mapping[str, Any] | None = None,
    position_state: Mapping[str, Any] | None = None,
    risk_context: Mapping[str, Any] | None = None,
) -> StateBuilderResult:
    """Monta estado único de inferência com validações críticas.

    Em caso de inconsistência crítica, retorna resultado com `success=False`
    para bloquear o fluxo de forma auditável (fail-safe).
    """

    now_ms = int(time.time() * 1000)

    try:
        decision_timestamp_normalized = int(decision_timestamp)
        if decision_timestamp_normalized <= 0:
            raise ValueError("decision_timestamp invalido")

        model_version_normalized = str(model_version).strip()
        if not model_version_normalized:
            raise ValueError("model_version ausente")

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

        payload = _safe_json_dict(candidate.get("payload_json"))
        payload_market_context = _normalize_serializable(
            _lookup_nested(payload, "market_context")
            if isinstance(_lookup_nested(payload, "market_context"), Mapping)
            else {}
        )
        merged_market_context = {
            **dict(payload_market_context),
            **dict(_normalize_serializable(market_context or {})),
        }
        funding_rate = payload.get("funding_rate")
        if funding_rate is None:
            funding_rate = _lookup_nested(payload, "market_context", "funding_rate")
        basis_value = payload.get("basis")
        if basis_value is None:
            basis_value = _lookup_nested(payload, "market_context", "basis")
        market_regime = payload.get("market_regime")
        if market_regime is None:
            market_regime = _lookup_nested(payload, "market_context", "market_regime")
        if funding_rate is not None and "funding_rate" not in merged_market_context:
            merged_market_context["funding_rate"] = funding_rate
        if basis_value is not None and "basis" not in merged_market_context:
            merged_market_context["basis"] = basis_value
        if market_regime is not None and "market_regime" not in merged_market_context:
            merged_market_context["market_regime"] = market_regime

        normalized_position_state = {
            "has_open_position": bool((position_state or {}).get("has_open_position", False)),
            **dict(_normalize_serializable(position_state or {})),
        }

        risk_state = {
            "execution_mode": execution_mode_normalized,
            "max_margin_per_position_usd": margin_limit,
            **dict(_normalize_serializable(risk_context or {})),
        }

        model_input = ModelDecisionInput(
            symbol=symbol,
            timeframe=timeframe,
            decision_timestamp=decision_timestamp_normalized,
            model_version=model_version_normalized,
            market_state={
                "signal_side": signal_side,
                "entry_type": str(candidate.get("entry_type") or "").strip().upper(),
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "signal_timestamp": signal_timestamp,
                "opportunity_id": int(candidate.get("opportunity_id") or 0),
                "source_rule_id": str(candidate.get("rule_id") or ""),
                "market_context": merged_market_context,
                "source_payload": _normalize_serializable(payload),
            },
            position_state=normalized_position_state,
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
                    "decision_timestamp",
                    "model_version",
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
                "has_payload_json": bool(payload),
                "market_context_keys": sorted(str(key) for key in merged_market_context.keys()),
                "position_state_keys": sorted(
                    str(key) for key in normalized_position_state.keys()
                ),
                "risk_state_keys": sorted(str(key) for key in risk_state.keys()),
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
