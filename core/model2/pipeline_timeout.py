"""Timeout por etapa critica do pipeline de dados M2 (M2-025.8).

Define contrato imutavel de budget por etapa (coleta, validacao e
consolidacao) e wrappers deterministas para short-circuit com telemetria
auditavel quando houver expiracao.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


_TIMEOUT_COLLECT = "TIMEOUT_COLLECT"
_TIMEOUT_VALIDATE = "TIMEOUT_VALIDATE"
_TIMEOUT_CONSOLIDATE = "TIMEOUT_CONSOLIDATE"


@dataclass(frozen=True)
class TimeoutPolicy:
    """Budget de timeout por etapa critica (ms)."""

    collect_timeout_ms: int
    validate_timeout_ms: int
    consolidate_timeout_ms: int

    def __post_init__(self) -> None:
        for field_name in (
            "collect_timeout_ms",
            "validate_timeout_ms",
            "consolidate_timeout_ms",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"TimeoutPolicy.{field_name} deve ser int > 0, recebeu: {value!r}"
                )


def check_collect_timeout(*, elapsed_ms: int, policy: TimeoutPolicy) -> str | None:
    """Retorna reason_code de timeout da coleta quando budget e excedido."""
    if int(elapsed_ms) <= policy.collect_timeout_ms:
        return None
    return _TIMEOUT_COLLECT


def check_validate_timeout(*, elapsed_ms: int, policy: TimeoutPolicy) -> str | None:
    """Retorna reason_code de timeout da validacao quando budget e excedido."""
    if int(elapsed_ms) <= policy.validate_timeout_ms:
        return None
    return _TIMEOUT_VALIDATE


def check_consolidate_timeout(*, elapsed_ms: int, policy: TimeoutPolicy) -> str | None:
    """Retorna reason_code de timeout da consolidacao quando budget e excedido."""
    if int(elapsed_ms) <= policy.consolidate_timeout_ms:
        return None
    return _TIMEOUT_CONSOLIDATE


def _build_timeout_payload(
    *,
    stage: str,
    elapsed_ms: int,
    budget_ms: int,
    reason_code: str,
    cycle_id: str | None,
    decision_id: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timed_out": True,
        "stage": stage,
        "elapsed_ms": int(elapsed_ms),
        "budget_ms": int(budget_ms),
        "reason_code": reason_code,
    }
    if cycle_id is not None:
        payload["cycle_id"] = cycle_id
    if decision_id is not None:
        payload["decision_id"] = int(decision_id)
    return payload


def _emit_timeout_telemetry(
    *,
    telemetry_fn: Callable[..., Any],
    symbol: str,
    stage: str,
    elapsed_ms: int,
    budget_ms: int,
    cycle_id: str | None,
    reason_code: str,
) -> None:
    telemetry_fn(
        symbol=symbol,
        stage=stage,
        elapsed_ms=int(elapsed_ms),
        budget_ms=int(budget_ms),
        cycle_id=cycle_id,
        reason_code=reason_code,
    )


def wrap_scanner_with_timeout(
    *,
    scanner_fn: Callable[[Mapping[str, Any]], dict[str, Any]],
    scanner_input: Mapping[str, Any],
    policy: TimeoutPolicy,
    started_at_ms: int,
    now_ms: int,
    telemetry_fn: Callable[..., Any],
) -> dict[str, Any]:
    """Aplica timeout na etapa de coleta/scanner com short-circuit seguro."""
    elapsed_ms = int(now_ms) - int(started_at_ms)
    reason_code = check_collect_timeout(elapsed_ms=elapsed_ms, policy=policy)
    symbol = str(scanner_input.get("symbol", ""))
    cycle_id_raw = scanner_input.get("cycle_id")
    cycle_id = str(cycle_id_raw) if cycle_id_raw is not None else None

    if reason_code is not None:
        _emit_timeout_telemetry(
            telemetry_fn=telemetry_fn,
            symbol=symbol,
            stage="collect",
            elapsed_ms=elapsed_ms,
            budget_ms=policy.collect_timeout_ms,
            cycle_id=cycle_id,
            reason_code=reason_code,
        )
        return _build_timeout_payload(
            stage="collect",
            elapsed_ms=elapsed_ms,
            budget_ms=policy.collect_timeout_ms,
            reason_code=reason_code,
            cycle_id=cycle_id,
            decision_id=None,
        )

    result = dict(scanner_fn(scanner_input) or {})
    result.setdefault("timed_out", False)
    return result


def wrap_validator_with_timeout(
    *,
    validator_fn: Callable[[Mapping[str, Any]], dict[str, Any]],
    validation_input: Mapping[str, Any],
    policy: TimeoutPolicy,
    started_at_ms: int,
    now_ms: int,
    telemetry_fn: Callable[..., Any],
) -> dict[str, Any]:
    """Aplica timeout na etapa de validacao com preservacao de decision_id."""
    elapsed_ms = int(now_ms) - int(started_at_ms)
    reason_code = check_validate_timeout(elapsed_ms=elapsed_ms, policy=policy)
    symbol = str(validation_input.get("symbol", ""))
    cycle_id_raw = validation_input.get("cycle_id")
    cycle_id = str(cycle_id_raw) if cycle_id_raw is not None else None
    decision_id_raw = validation_input.get("decision_id")
    decision_id: int | None
    try:
        decision_id = int(decision_id_raw) if decision_id_raw is not None else None
    except (TypeError, ValueError):
        decision_id = None

    if reason_code is not None:
        _emit_timeout_telemetry(
            telemetry_fn=telemetry_fn,
            symbol=symbol,
            stage="validate",
            elapsed_ms=elapsed_ms,
            budget_ms=policy.validate_timeout_ms,
            cycle_id=cycle_id,
            reason_code=reason_code,
        )
        return _build_timeout_payload(
            stage="validate",
            elapsed_ms=elapsed_ms,
            budget_ms=policy.validate_timeout_ms,
            reason_code=reason_code,
            cycle_id=cycle_id,
            decision_id=decision_id,
        )

    result = dict(validator_fn(validation_input) or {})
    result.setdefault("timed_out", False)
    if decision_id is not None:
        result.setdefault("decision_id", decision_id)
    return result

