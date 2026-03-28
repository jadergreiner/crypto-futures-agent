"""Leitura de mercado com retry controlado e fallback conservador.

Este modulo implementa contrato simples para resiliencia em falhas
transitorias da leitura de mercado (M2-025.7).
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Literal

FailureClass = Literal["transient", "permanent"]


@dataclass(frozen=True)
class RetryPolicy:
    """Politica imutavel de retry para leitura de mercado."""

    max_retries: int
    backoff_base_ms: int
    max_budget_ms: int


def classify_market_read_exception(error: Exception) -> FailureClass:
    """Classifica erro de leitura de mercado em transient/permanent."""
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return "transient"
    return "permanent"


def read_market_with_retry(
    *,
    reader: Callable[[], dict[str, Any]],
    policy: RetryPolicy,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Executa leitura com retry e fallback conservador em budget esgotado.

    Retorno padrao:
    - sucesso: payload original + metadados de sucesso
    - falha: payload conservador com reason_code de exaustao
    """
    started = time.monotonic()
    max_attempts = max(1, int(policy.max_retries))
    backoff_base_ms = max(0, int(policy.backoff_base_ms))
    budget_ms = max(1, int(policy.max_budget_ms))

    for attempt in range(max_attempts):
        try:
            payload = dict(reader() or {})
            payload.setdefault("fallback", False)
            payload.setdefault("conservative", False)
            payload.setdefault("reason_code", "")
            payload.setdefault("attempts", attempt + 1)
            return payload
        except Exception as exc:
            failure_class = classify_market_read_exception(exc)
            if failure_class == "permanent":
                return {
                    "fallback": True,
                    "conservative": True,
                    "reason_code": "MARKET_READ_PERMANENT_FAILURE",
                    "attempts": attempt + 1,
                    "failure_class": failure_class,
                    "error_type": type(exc).__name__,
                }

            elapsed_ms = int((time.monotonic() - started) * 1000)
            if attempt >= max_attempts - 1 or elapsed_ms >= budget_ms:
                return {
                    "fallback": True,
                    "conservative": True,
                    "reason_code": "MARKET_READ_RETRY_EXHAUSTED",
                    "attempts": attempt + 1,
                    "failure_class": failure_class,
                    "error_type": type(exc).__name__,
                }

            delay_seconds = ((2 ** attempt) * backoff_base_ms) / 1000.0
            if delay_seconds > 0:
                sleep_fn(delay_seconds)

    return {
        "fallback": True,
        "conservative": True,
        "reason_code": "MARKET_READ_RETRY_EXHAUSTED",
        "attempts": max_attempts,
        "failure_class": "transient",
        "error_type": "UnknownError",
    }
