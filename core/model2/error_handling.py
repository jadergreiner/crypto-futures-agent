"""Camada padronizada de handling de erros e timeouts para o ciclo M2.

Centraliza o contrato de falhas para API, DB e live sem bypass de
`risk_gate` ou `circuit_breaker`. Em duvida operacional, o retorno e
conservador e auditavel.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Literal, Mapping, TypedDict

from .live_execution import REASON_CODE_ACTION, REASON_CODE_SEVERITY

ErrorSource = Literal["api", "db", "live", "unknown"]
ErrorCategory = Literal[
    "timeout",
    "transient",
    "validation",
    "permanent",
    "unknown",
]

FIVE_ERROR_CATEGORIES: tuple[ErrorCategory, ...] = (
    "timeout",
    "transient",
    "validation",
    "permanent",
    "unknown",
)


class ErrorContextPayload(TypedDict):
    source: str
    operation: str
    category: str
    reason_code: str
    status: str
    severity: str
    recommended_action: str
    should_retry: bool
    timeout_seconds: float
    decision_id: int | None
    execution_id: int | None
    error_type: str
    error_message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class ErrorTimeoutPolicy:
    """Timeouts explicitos por dominio operacional."""

    api_timeout_seconds: float = 5.0
    db_timeout_seconds: float = 5.0
    live_timeout_seconds: float = 10.0
    reconciliation_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        for field_name in (
            "api_timeout_seconds",
            "db_timeout_seconds",
            "live_timeout_seconds",
            "reconciliation_timeout_seconds",
        ):
            value = getattr(self, field_name)
            if float(value) <= 0:
                raise ValueError(f"{field_name} deve ser > 0, recebeu {value!r}")


def normalize_error_source(source: str) -> ErrorSource:
    """Normaliza a origem operacional para o conjunto canonico."""
    normalized = str(source or "").strip().lower()
    if normalized == "api":
        return "api"
    if normalized == "db":
        return "db"
    if normalized == "live":
        return "live"
    return "unknown"


def resolve_timeout_seconds(
    *,
    source: str,
    policy: ErrorTimeoutPolicy | None = None,
    operation: str | None = None,
) -> float:
    """Resolve timeout explicito para API, DB e live/reconciliacao."""
    resolved_policy = policy or ErrorTimeoutPolicy()
    normalized_source = normalize_error_source(source)
    operation_name = str(operation or "").strip().lower()

    if normalized_source == "api":
        return float(resolved_policy.api_timeout_seconds)
    if normalized_source == "db":
        return float(resolved_policy.db_timeout_seconds)
    if normalized_source == "live" and "reconcil" in operation_name:
        return float(resolved_policy.reconciliation_timeout_seconds)
    if normalized_source == "live":
        return float(resolved_policy.live_timeout_seconds)
    return float(resolved_policy.live_timeout_seconds)


def _is_sqlite_timeout(error: Exception) -> bool:
    if not isinstance(error, sqlite3.OperationalError):
        return False
    message = str(error).lower()
    return any(token in message for token in ("locked", "busy", "timeout"))


def _classify_exception(
    error: Exception,
) -> tuple[ErrorCategory, str, bool]:
    """Classifica excecao em uma das 5 categorias canonicas."""
    if isinstance(error, TimeoutError) or _is_sqlite_timeout(error):
        return "timeout", "timeout", True

    if isinstance(error, (ConnectionError, BrokenPipeError, OSError)):
        return "transient", "transient_error", True

    if isinstance(error, (ValueError, TypeError, KeyError, AssertionError)):
        return "validation", "validation_error", False

    if isinstance(error, RuntimeError):
        return "permanent", "permanent_error", False

    return "unknown", "unknown_execution_error", False


def classify_execution_error(
    error: Exception,
    *,
    source: str,
    operation: str,
    decision_id: int | None = None,
    execution_id: int | None = None,
    timeout_policy: ErrorTimeoutPolicy | None = None,
    details: dict[str, Any] | None = None,
) -> ErrorContextPayload:
    """Gera contrato deterministico de erro com correlacao auditavel."""
    normalized_source = normalize_error_source(source)
    category, reason_code, should_retry = _classify_exception(error)
    timeout_seconds = resolve_timeout_seconds(
        source=normalized_source,
        policy=timeout_policy,
        operation=operation,
    )
    payload_details = dict(details or {})
    payload_details.setdefault("source", normalized_source)
    payload_details.setdefault("operation", str(operation))

    severity = REASON_CODE_SEVERITY.get(reason_code, "CRITICAL")
    recommended_action = REASON_CODE_ACTION.get(reason_code, "bloquear_operacao")
    status = "FAILED" if severity in {"HIGH", "CRITICAL"} else "BLOCKED"

    return {
        "source": normalized_source,
        "operation": str(operation),
        "category": category,
        "reason_code": reason_code,
        "status": status,
        "severity": severity,
        "recommended_action": recommended_action,
        "should_retry": should_retry,
        "timeout_seconds": timeout_seconds,
        "decision_id": decision_id,
        "execution_id": execution_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "details": payload_details,
    }


def build_error_event(context: Mapping[str, Any]) -> dict[str, Any]:
    """Converte o contexto padronizado em evento auditavel unico."""
    severity = str(context.get("severity") or "CRITICAL").upper()
    default_status = "FAILED" if severity in {"HIGH", "CRITICAL"} else "BLOCKED"
    status = str(context.get("status") or default_status)
    return {
        "event_type": "execution_error_contract",
        "status": status,
        "reason_code": str(context["reason_code"]),
        "severity": severity,
        "recommended_action": str(context["recommended_action"]),
        "decision_id": context.get("decision_id"),
        "execution_id": context.get("execution_id"),
        "metadata": {
            "source": str(context["source"]),
            "operation": str(context["operation"]),
            "category": str(context["category"]),
            "should_retry": bool(context["should_retry"]),
            "timeout_seconds": float(context["timeout_seconds"]),
            "error_type": str(context["error_type"]),
            "error_message": str(context["error_message"]),
            **dict(context.get("details") or {}),
        },
    }
