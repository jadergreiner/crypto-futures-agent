"""Telemetria de bloqueios do risk_gate — M2-026.1.

Registra cada bloqueio do risk_gate com reason_code, condicao,
limites e decision_id para observabilidade auditavel em memoria.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskGateBlockEvent:
    """Evento imutavel de bloqueio do risk_gate.

    Captura o contexto completo de um bloqueio para auditoria:
    reason_code canonico, condicao textual, limite configurado,
    valor real que violou o limite, decision_id de correlacao
    e timestamp em milissegundos UTC.
    """

    reason_code: str
    condition: str
    limit_value: float
    actual_value: float
    decision_id: int
    timestamp_ms: int


class RiskGateTelemetryRecorder:
    """Recorder append-only de eventos de bloqueio do risk_gate.

    Armazena eventos em memoria para consulta rapida por reason_code.
    Nao persiste em banco — telemetria operacional por ciclo.
    """

    def __init__(self) -> None:
        self._events: list[RiskGateBlockEvent] = []

    def record(self, event: RiskGateBlockEvent) -> None:
        """Registrar evento de bloqueio (append-only)."""
        self._events.append(event)
        logger.info(
            "[M2-026.1] risk_gate bloqueio registrado: reason=%s decision_id=%s",
            event.reason_code,
            event.decision_id,
        )

    def total_events(self) -> int:
        """Retornar total de eventos registrados."""
        return len(self._events)

    def all_events(self) -> list[RiskGateBlockEvent]:
        """Retornar copia da lista de eventos (nao expoe referencia interna)."""
        return list(self._events)

    def query_by_reason(self) -> dict[str, dict[str, float]]:
        """Agregar eventos por reason_code com count e percentual.

        Retorna:
            dict[reason_code, {"count": int, "percentage": float}]
        """
        total = len(self._events)
        if total == 0:
            return {}

        counts: dict[str, int] = {}
        for event in self._events:
            counts[event.reason_code] = counts.get(event.reason_code, 0) + 1

        return {
            reason: {
                "count": float(count),
                "percentage": (count / total) * 100.0,
            }
            for reason, count in counts.items()
        }


def get_risk_gate_telemetry_recorder() -> RiskGateTelemetryRecorder:
    """Factory: retornar nova instancia de RiskGateTelemetryRecorder."""
    return RiskGateTelemetryRecorder()
