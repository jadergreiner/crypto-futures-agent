"""
Circuit Breaker para o agente de negociacao M2.

Implementa a maquina de estados CLOSED -> OPEN -> HALF_OPEN -> CLOSED
com rastreamento de drawdown de portfolio e integracao com EventRecorder.

Contrato exigido por live_service:
  - update_portfolio_value(v: float) -> None
  - check_status() -> dict  (chaves: trading_allowed, drawdown_pct, state)
  - can_trade() -> bool
  - _portfolio_current: float
  - _portfolio_peak: float
  - state: CircuitBreakerState
  - trip(reason: str) -> None
  - attempt_recovery(force: bool) -> None
  - reset_manual(operator: str) -> None
"""

from __future__ import annotations

import logging
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional

from monitoring.events import EventRecorder, CircuitBreakerTransition
from risk.states import CircuitBreakerState

logger = logging.getLogger(__name__)

# Limiar de drawdown que dispara o CB (em %)
_CB_DRAWDOWN_THRESHOLD = -3.1

# M2-024.7: tamanho da janela deslizante por classe de falha
_DEFAULT_WINDOW_SIZE = 100
# M2-024.7: limite de falhas da mesma classe para abrir o CB
_DEFAULT_FAILURE_CLASS_THRESHOLD = 3


class FailureClass(Enum):
    """Classes de falha para circuit breaker granular (M2-024.7)."""

    EXCHANGE_ERROR = "EXCHANGE_ERROR"
    TIMEOUT = "TIMEOUT"
    VALIDATION_FAIL = "VALIDATION_FAIL"


class CircuitBreaker:
    """
    Circuit Breaker com maquina de estados e rastreamento de drawdown.

    Estados:
        CLOSED    -- normal, trading permitido
        OPEN      -- travado por drawdown, trading bloqueado
        HALF_OPEN -- em tentativa de recuperacao

    Transicoes:
        CLOSED    -> OPEN      : quando drawdown <= _CB_DRAWDOWN_THRESHOLD
        OPEN      -> HALF_OPEN : via attempt_recovery() ou reset_manual()
        HALF_OPEN -> CLOSED    : se drawdown recuperado (> threshold)
        HALF_OPEN -> OPEN      : se drawdown ainda critico
    """

    def __init__(
        self,
        event_recorder: Optional[EventRecorder] = None,
        drawdown_threshold: float = _CB_DRAWDOWN_THRESHOLD,
        cooldown_by_class: Optional[Dict[FailureClass, int]] = None,
        failure_class_threshold: int = _DEFAULT_FAILURE_CLASS_THRESHOLD,
        window_size: int = _DEFAULT_WINDOW_SIZE,
    ) -> None:
        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._event_recorder = event_recorder
        self._drawdown_threshold = drawdown_threshold
        self._portfolio_current: float = 0.0
        self._portfolio_peak: float = 0.0
        # M2-024.7: rastreamento por classe de falha
        self._cooldown_by_class: Dict[FailureClass, int] = cooldown_by_class or {}
        self._failure_class_threshold = failure_class_threshold
        self._window_size = window_size
        self._failure_windows: Dict[FailureClass, deque[int]] = {
            fc: deque(maxlen=window_size) for fc in FailureClass
        }
        self._open_classes: set[FailureClass] = set()

    # ------------------------------------------------------------------
    # Interface de portfolio
    # ------------------------------------------------------------------

    def update_portfolio_value(self, value: float) -> None:
        """Atualiza valor corrente e rastreia pico para calculo de drawdown."""
        self._portfolio_current = value
        if value > self._portfolio_peak:
            self._portfolio_peak = value

    # ------------------------------------------------------------------
    # Consulta de estado
    # ------------------------------------------------------------------

    def register_failure(
        self, *, failure_class: FailureClass, reason: str
    ) -> None:
        """Registra uma falha por classe na janela deslizante (M2-024.7).

        Abre o breaker para a classe se o threshold for atingido.
        """
        import time as _time

        ts = int(_time.time() * 1000)
        window = self._failure_windows[failure_class]
        window.append(ts)
        count = len(window)

        logger.debug(
            "Falha registrada: classe=%s reason=%s contagem=%d",
            failure_class.value, reason, count,
        )

        if count >= self._failure_class_threshold:
            if failure_class not in self._open_classes:
                self._open_classes.add(failure_class)
                logger.warning(
                    "CB ABERTO para classe %s: %d falhas na janela",
                    failure_class.value, count,
                )

    def is_open_for_class(self, failure_class: FailureClass) -> bool:
        """Retorna True se o CB esta aberto para a classe de falha especifica."""
        return failure_class in self._open_classes

    def can_trade(self) -> bool:
        """Retorna True apenas quando estado e CLOSED e nenhuma classe esta aberta."""
        if self._open_classes:
            return False
        return self.state == CircuitBreakerState.CLOSED

    def check_status(self) -> dict[str, Any]:
        """
        Retorna dicionario de status do CB.

        Chaves: trading_allowed (bool), drawdown_pct (float | None), state (str)
        """
        drawdown = self._calculate_drawdown()
        return {
            "trading_allowed": self.can_trade(),
            "drawdown_pct": drawdown,
            "state": self.state.value,
        }

    # ------------------------------------------------------------------
    # Transicoes de estado
    # ------------------------------------------------------------------

    def trip(self, reason: str) -> None:
        """Forca transicao para OPEN (disparo do CB)."""
        if self.state != CircuitBreakerState.OPEN:
            from_state = self.state
            self.state = CircuitBreakerState.OPEN
            logger.critical(
                "CB DISPARADO: %s | drawdown=%.2f%% | de=%s para=%s",
                reason,
                self._calculate_drawdown() or 0.0,
                from_state.value,
                self.state.value,
            )
            if self._event_recorder:
                self._event_recorder.record(
                    CircuitBreakerTransition(
                        from_state=from_state,
                        to_state=self.state,
                        reason=reason,
                    )
                )

    def attempt_recovery(self, *, force: bool = False) -> None:
        """
        Tenta transicao OPEN -> HALF_OPEN -> CLOSED.

        Se force=True, avanca o estado independentemente do drawdown atual
        (usado em testes e em reset controlado pelo operador).
        """
        prev_state: CircuitBreakerState = self.state

        if self.state == CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.HALF_OPEN
            logger.warning(
                "CB HALF_OPEN: iniciando tentativa de recuperacao (force=%s)", force
            )
            if self._event_recorder:
                self._event_recorder.record(
                    CircuitBreakerTransition(
                        from_state=prev_state,
                        to_state=self.state,
                        reason="attempt_recovery",
                    )
                )
            return

        if self.state == CircuitBreakerState.HALF_OPEN:
            drawdown = self._calculate_drawdown()
            recuperado = force or (drawdown is None) or (drawdown > self._drawdown_threshold)
            if recuperado:
                self.state = CircuitBreakerState.CLOSED
                logger.info(
                    "CB FECHADO: drawdown=%.2f%% acima do limiar %.2f%%",
                    drawdown or 0.0,
                    self._drawdown_threshold,
                )
            else:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "CB RE-DISPARADO no HALF_OPEN: drawdown=%.2f%% ainda critico",
                    drawdown,
                )
            if self._event_recorder:
                self._event_recorder.record(
                    CircuitBreakerTransition(
                        from_state=prev_state,
                        to_state=self.state,
                        reason="recovery_confirmed" if recuperado else "recovery_failed",
                    )
                )

    def reset_manual(self, *, operator: str) -> None:
        """
        Reset manual com confirmacao auditavel obrigatoria.

        Requer identificacao do operador. Registra evento via EventRecorder.
        Deve ser usado apenas por operador humano com autorizacao explicita.
        """
        from_state = self.state
        self.state = CircuitBreakerState.CLOSED
        logger.critical(
            "CB RESET MANUAL por operador='%s' | estado anterior=%s",
            operator,
            from_state.value,
        )
        if self._event_recorder:
            self._event_recorder.record(
                CircuitBreakerTransition(
                    from_state=from_state,
                    to_state=self.state,
                    reason=f"reset_manual:operador={operator}",
                )
            )

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _calculate_drawdown(self) -> Optional[float]:
        """Calcula drawdown percentual em relacao ao pico. Retorna None se pico=0."""
        if self._portfolio_peak == 0.0:
            return None
        return (
            (self._portfolio_current - self._portfolio_peak) / self._portfolio_peak
        ) * 100.0
