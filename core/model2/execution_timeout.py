"""Politica de timeout por etapa de execucao do ciclo M2 (M2-024.5).

Fornece StageTimeoutPolicy (frozen dataclass) e helpers deterministicos
para verificar expiracao nas etapas de admissao, envio e reconciliacao.
Nao importa risk_gate nem circuit_breaker — responsabilidade exclusiva
de medir elapsed e emitir telemetria.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.model2.order_layer import OrderLayerInput, OrderLayerDecision

# Defaults seguros (ms): conservadores para evitar falsos positivos em live.
_DEFAULT_ADMISSION_TIMEOUT_MS: int = 5_000
_DEFAULT_SEND_TIMEOUT_MS: int = 10_000
_DEFAULT_RECONCILIATION_TIMEOUT_MS: int = 30_000


@dataclass(frozen=True)
class StageTimeoutPolicy:
    """Limites de timeout configuráveis por etapa de execucao.

    Todos os valores em milissegundos. Defaults conservadores >= 100ms.
    Rejeita valores <= 0 via __post_init__.
    """

    admission_timeout_ms: int = _DEFAULT_ADMISSION_TIMEOUT_MS
    send_timeout_ms: int = _DEFAULT_SEND_TIMEOUT_MS
    reconciliation_timeout_ms: int = _DEFAULT_RECONCILIATION_TIMEOUT_MS

    def __post_init__(self) -> None:
        for field_name in (
            "admission_timeout_ms",
            "send_timeout_ms",
            "reconciliation_timeout_ms",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(
                    f"StageTimeoutPolicy.{field_name} deve ser int > 0, recebeu: {value!r}"
                )


def check_admission_timeout(
    order_input: "OrderLayerInput",
    *,
    policy: StageTimeoutPolicy,
    now_ms: int,
) -> "OrderLayerDecision | None":
    """Verifica se a etapa de admissao expirou.

    Retorna None se dentro do limite; OrderLayerDecision com reason
    TIMEOUT_ADMISSION e target_status CANCELLED se expirado.
    """
    from core.model2.order_layer import (
        OrderLayerDecision,
        TECHNICAL_SIGNAL_STATUS_CANCELLED,
        M2_007_1_RULE_ID,
    )

    elapsed_ms = now_ms - order_input.decision_timestamp
    if elapsed_ms <= policy.admission_timeout_ms:
        return None

    return OrderLayerDecision(
        should_transition=True,
        target_status=TECHNICAL_SIGNAL_STATUS_CANCELLED,
        reason="TIMEOUT_ADMISSION",
        rule_id=M2_007_1_RULE_ID,
        details={
            "elapsed_ms": elapsed_ms,
            "timeout_ms": policy.admission_timeout_ms,
            "reason_code": "TIMEOUT_ADMISSION",
        },
    )


def check_send_timeout(
    *,
    elapsed_ms: int,
    policy: StageTimeoutPolicy,
) -> str | None:
    """Verifica se a etapa de envio de ordem expirou.

    Retorna None se dentro do limite; 'TIMEOUT_SEND' se expirado.
    """
    if elapsed_ms <= policy.send_timeout_ms:
        return None
    return "TIMEOUT_SEND"


def check_reconciliation_timeout(
    *,
    elapsed_ms: int,
    policy: StageTimeoutPolicy,
) -> str | None:
    """Verifica se a etapa de reconciliacao expirou.

    Retorna None se dentro do limite; 'TIMEOUT_RECONCILIATION' se expirado.
    """
    if elapsed_ms <= policy.reconciliation_timeout_ms:
        return None
    return "TIMEOUT_RECONCILIATION"


def emit_timeout_telemetria(
    *,
    stage: str,
    elapsed_ms: int,
    timeout_ms: int,
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emite payload de telemetria de timeout via emit_stage_slo_violation_event.

    Delega para a funcao existente em live_service e enriquece metadata
    com reason_code canonico quando fornecido.
    """
    from core.model2.live_service import emit_stage_slo_violation_event

    extra: dict[str, Any] = dict(metadata or {})
    if reason_code is not None:
        extra["reason_code"] = reason_code

    return emit_stage_slo_violation_event(
        stage=stage,
        latency_ms=elapsed_ms,
        slo_ms=timeout_ms,
        metadata=extra,
    )
