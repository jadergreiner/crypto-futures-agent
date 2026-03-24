"""Observabilidade de transições do circuit_breaker com eventos imutáveis.

Módulo de auditoria para registrar transições de estado CLOSED→OPEN→HALF_OPEN→CLOSED
do circuit_breaker com contexto completo: timestamp UTC, failure_count, window_start,
reactivation_time_utc e motivo.

Garante imutabilidade: registros frozen, estrutura append-only (SEM DELETE/UPDATE).

Referência: docs/BACKLOG.md (M2-026.2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class CircuitBreakerTransition:
    """Evento imutável de transição do circuit_breaker.

    Atributos:
        timestamp_utc: Momento exato da transição (UTC).
        from_state: Estado anterior ('CLOSED', 'OPEN', 'HALF_OPEN').
        to_state: Estado novo.
        failure_count: Número de falhas acumuladas.
        window_start_utc: Início da janela deslizante de falhas (opcional).
        reactivation_time_utc: Hora prevista para reativação se OPEN (opcional).
        reason: Motivo textual da transição (ex: 'threshold_exceeded', 'timeout_expired').
    """

    timestamp_utc: datetime
    from_state: str  # CLOSED, OPEN, HALF_OPEN
    to_state: str
    failure_count: int
    window_start_utc: Optional[datetime]
    reactivation_time_utc: Optional[datetime]
    reason: str


class CircuitBreakerEventRecorder:
    """Registrador de transições de circuit_breaker. Append-only (imutável)."""

    def __init__(self) -> None:
        """Inicializa recorder em memória. Events são imutáveis."""
        self._events: list[CircuitBreakerTransition] = []
        self._symbol_states: dict[str, str] = {}  # symbol -> current_state

    def record_transition(
        self,
        symbol: Optional[str],
        from_state: str,
        to_state: str,
        failure_count: int = 0,
        window_start_utc: Optional[datetime] = None,
        reactivation_time_utc: Optional[datetime] = None,
        reason: str = "",
    ) -> None:
        """Registra transição. Estrutura é imutável (dataclass frozen=True).

        Args:
            symbol: Símbolo operado (opcional; None = global).
            from_state: Estado anterior.
            to_state: Estado novo.
            failure_count: Contador de falhas na janela.
            window_start_utc: Início da janela deslizante.
            reactivation_time_utc: Hora prevista para reativação (se OPEN).
            reason: Motivo textual da transição.
        """
        event = CircuitBreakerTransition(
            timestamp_utc=datetime.utcnow(),
            from_state=from_state,
            to_state=to_state,
            failure_count=failure_count,
            window_start_utc=window_start_utc,
            reactivation_time_utc=reactivation_time_utc,
            reason=reason,
        )
        self._events.append(event)

        # Rastrear estado atual por símbolo (para query rápida)
        if symbol:
            self._symbol_states[symbol] = to_state

    def get_current_state(self, symbol: Optional[str] = None) -> Optional[str]:
        """Retorna estado atual do circuit_breaker para símbolo (ou global).

        Args:
            symbol: Símbolo (None = global).

        Returns:
            Estado ('CLOSED', 'OPEN', 'HALF_OPEN') ou None se não existir.
        """
        key = symbol or "global"
        return self._symbol_states.get(key)

    def get_history_24h(
        self, symbol: Optional[str] = None
    ) -> list[CircuitBreakerTransition]:
        """Retorna histórico de transições das últimas 24h.

        Args:
            symbol: Filtrar por símbolo (None = todos).

        Returns:
            Lista de eventos ordenada por timestamp DESC.
        """
        now_utc = datetime.utcnow()
        cutoff = now_utc - timedelta(hours=24)

        # Para implementação futura com DB, ajustar filter
        # Por enquanto, retorna eventos em memória
        filtered = [
            e for e in self._events
            if e.timestamp_utc >= cutoff
        ]

        # Ordenar DESC por timestamp (mais recentes primeiro)
        sorted_events = sorted(
            filtered,
            key=lambda e: e.timestamp_utc,
            reverse=True
        )
        return sorted_events

    def get_all_events(self) -> list[CircuitBreakerTransition]:
        """Retorna todos os eventos registrados (imutáveis, append-only).

        Returns:
            Lista completa de transições.
        """
        return list(self._events)

    def get_reactivation_time(self, symbol: Optional[str] = None) -> Optional[datetime]:
        """Retorna hora prevista de reativação se estado for OPEN.

        Args:
            symbol: Símbolo.

        Returns:
            reactivation_time_utc do evento mais recente (ou None).
        """
        events = self.get_history_24h(symbol)
        if events:
            # Evento mais recente (índice 0 após DESC sort)
            return events[0].reactivation_time_utc
        return None


# Singleton global para registro de eventos (pode ser injetado em testes)
_circuit_breaker_recorder: CircuitBreakerEventRecorder | None = None


def get_circuit_breaker_recorder() -> CircuitBreakerEventRecorder:
    """Retorna singleton do registrador de eventos.

    Returns:
        Instância global de CircuitBreakerEventRecorder.
    """
    global _circuit_breaker_recorder
    if _circuit_breaker_recorder is None:
        _circuit_breaker_recorder = CircuitBreakerEventRecorder()
    return _circuit_breaker_recorder


def reset_circuit_breaker_recorder_for_testing() -> None:
    """Reseta o singleton para testes (cleanup)."""
    global _circuit_breaker_recorder
    _circuit_breaker_recorder = None
