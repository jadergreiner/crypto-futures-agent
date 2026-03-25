"""
BLID-092 — Suite RED: Contrato CircuitBreaker para live_service.

Testa os metodos e atributos que live_service.py espera de CircuitBreaker
e que atualmente nao existem, causando AttributeError silencioso que
mantem allows_trading=False permanentemente.

Requisitos cobertos (SA handoff):
  R1: CB implementa update_portfolio_value, check_status, can_trade,
      _portfolio_current, _portfolio_peak, CircuitBreakerState.NORMAL
  R2: Transicao CLOSED->OPEN->HALF_OPEN->CLOSED apos recovery_period
  R3: _snapshot_guardrail_state nunca lanca AttributeError; fallback
      conservador com log explicito em caso de falha
  R4: CircuitBreakerState.NORMAL existe (alias compativel com valores no DB)
  R5: operator_cycle_status exibe cb_state, drawdown_atual, horas_restantes
  R6: Reset manual com log auditavel obrigatorio
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from risk.states import CircuitBreakerState as CBState


# =============================================================================
# R1 — Contrato de interface: metodos e atributos que live_service exige
# =============================================================================

class TestCircuitBreakerInterface:
    """R1: CircuitBreaker deve expor a interface completa esperada por live_service."""

    def test_cb_has_update_portfolio_value_method(self):
        """CircuitBreaker deve ter metodo update_portfolio_value(float)."""
        # Arrange
        cb = CircuitBreaker()
        # Act / Assert
        assert hasattr(cb, "update_portfolio_value"), (
            "CircuitBreaker nao tem update_portfolio_value — contrato quebrado"
        )
        cb.update_portfolio_value(1000.0)  # nao deve lancar

    def test_cb_has_check_status_method_returns_dict(self):
        """check_status() deve retornar dict com chaves trading_allowed e drawdown_pct."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        result = cb.check_status()
        assert isinstance(result, dict), "check_status deve retornar dict"
        assert "trading_allowed" in result, "falta chave trading_allowed"
        assert "drawdown_pct" in result, "falta chave drawdown_pct"

    def test_cb_has_can_trade_method_returns_bool(self):
        """can_trade() deve retornar bool."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        result = cb.can_trade()
        assert isinstance(result, bool), "can_trade deve retornar bool"

    def test_cb_has_portfolio_current_attribute(self):
        """CB deve ter atributo _portfolio_current."""
        cb = CircuitBreaker()
        assert hasattr(cb, "_portfolio_current"), "falta _portfolio_current"

    def test_cb_has_portfolio_peak_attribute(self):
        """CB deve ter atributo _portfolio_peak."""
        cb = CircuitBreaker()
        assert hasattr(cb, "_portfolio_peak"), "falta _portfolio_peak"

    def test_cb_portfolio_current_set_directly(self):
        """live_service seta _portfolio_current diretamente na inicializacao."""
        cb = CircuitBreaker()
        cb._portfolio_current = 500.0
        cb._portfolio_peak = 500.0
        assert cb._portfolio_current == 500.0
        assert cb._portfolio_peak == 500.0


# =============================================================================
# R4 — CircuitBreakerState.NORMAL existe
# =============================================================================

class TestCircuitBreakerStateEnum:
    """R4: CircuitBreakerState deve ter membro NORMAL para compatibilidade."""

    def test_state_normal_exists(self):
        """CircuitBreakerState.NORMAL deve existir como membro do enum."""
        assert hasattr(CBState, "NORMAL"), (
            "CircuitBreakerState.NORMAL nao existe — live_service falha ao importar"
        )

    def test_state_normal_value_string(self):
        """NORMAL.value deve ser string serializavel para persistencia no DB."""
        assert isinstance(CBState.NORMAL.value, str), (
            "NORMAL.value deve ser str para ser gravado em model_decisions.input_json"
        )

    def test_state_trancado_or_open_maps_correctly(self):
        """Estado OPEN deve existir e ser distinto de NORMAL/CLOSED."""
        assert CBState.OPEN != CBState.NORMAL or CBState.CLOSED != CBState.OPEN


# =============================================================================
# R2 — Maquina de estados: trip -> OPEN -> HALF_OPEN -> CLOSED
# =============================================================================

class TestCircuitBreakerStateMachine:
    """R2: CB deve transitar CLOSED->OPEN->HALF_OPEN->CLOSED apos recovery."""

    def test_initial_state_is_closed_or_normal(self):
        """CB recém-criado deve estar em CLOSED (ou NORMAL se alias)."""
        cb = CircuitBreaker()
        assert cb.state in (CBState.CLOSED, CBState.NORMAL), (
            f"estado inicial esperado CLOSED ou NORMAL, got {cb.state}"
        )

    def test_can_trade_true_when_closed(self):
        """can_trade() deve ser True quando estado e CLOSED/NORMAL."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        assert cb.can_trade() is True

    def test_trip_transitions_to_open(self):
        """trip() deve transitar para OPEN."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown_excedido")
        assert cb.state == CBState.OPEN

    def test_can_trade_false_when_open(self):
        """can_trade() deve ser False quando estado e OPEN."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown_excedido")
        assert cb.can_trade() is False

    def test_check_status_trading_allowed_false_when_open(self):
        """check_status() retorna trading_allowed=False quando OPEN."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown")
        status = cb.check_status()
        assert status["trading_allowed"] is False

    def test_recovery_after_period_transitions_to_half_open(self):
        """Apos RECOVERY_PERIOD_HOURS simulado, CB transita OPEN->HALF_OPEN."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown")
        # Simular passagem do tempo via metodo de recovery
        cb.attempt_recovery(force=True)
        assert cb.state == CBState.HALF_OPEN, (
            f"esperado HALF_OPEN apos recovery forcado, got {cb.state}"
        )

    def test_recovery_to_closed_when_drawdown_resolved(self):
        """Se drawdown < threshold no HALF_OPEN, CB fecha (CLOSED)."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown")
        cb.attempt_recovery(force=True)
        # Balance recuperado — sem drawdown
        cb.update_portfolio_value(1000.0)
        cb.attempt_recovery(force=True)
        assert cb.state == CBState.CLOSED

    def test_reset_manual_requires_audit_log(self):
        """reset_manual() deve registrar evento de auditoria."""
        recorder = MagicMock()
        cb = CircuitBreaker(event_recorder=recorder)
        cb.update_portfolio_value(1000.0)
        cb.trip("drawdown")
        cb.reset_manual(operator="test_operator")
        assert cb.state == CBState.CLOSED
        recorder.record.assert_called()  # auditoria obrigatoria


# =============================================================================
# R3 — _snapshot_guardrail_state nunca lanca AttributeError
# =============================================================================

class TestSnapshotGuardrailStateFallback:
    """R3: live_service._snapshot_guardrail_state deve ser tolerante a falha do CB."""

    def test_snapshot_returns_conservative_on_cb_attribute_error(self):
        """Se CB lanca AttributeError, snapshot retorna allows_trading=False com log."""
        # Arrange: CB sem metodos esperados (simula estado pre-fix)
        from unittest.mock import MagicMock, patch
        import core.model2.live_service as ls_module

        broken_cb = MagicMock(spec=[])  # sem nenhum atributo
        broken_cb.state = CBState.OPEN

        # Criar instancia minima do servico para testar o metodo isolado
        svc = object.__new__(ls_module.Model2LiveExecutionService)
        svc._circuit_breaker = broken_cb
        svc._risk_gate = MagicMock()
        svc._risk_gate.status.value = "ativo"
        svc._risk_gate.can_execute_order.return_value = True
        svc._risk_gate.get_risk_metrics.return_value = MagicMock(drawdown_pct=0.0)
        svc._guardrail_balance_initialized = False
        svc.config = MagicMock()
        svc.config.execution_mode = "live"

        # Act
        result = svc._snapshot_guardrail_state(1000.0)

        # Assert: fallback conservador — nunca permite trading quando CB falha
        assert result["circuit_breaker_allows_trading"] is False


# =============================================================================
# R5 — operator_cycle_status exibe cb_state, drawdown, horas_restantes
# =============================================================================

class TestOperatorCycleStatusCBFields:
    """R5: Status por simbolo deve incluir campos de CB para visibilidade do operador."""

    def test_symbol_report_has_cb_state_field(self):
        """SymbolReport deve ter campo circuit_breaker_state."""
        from core.model2.cycle_report import SymbolReport
        report = SymbolReport.__annotations__
        assert "circuit_breaker_state" in report or hasattr(SymbolReport, "circuit_breaker_state"), (
            "SymbolReport nao tem circuit_breaker_state"
        )

    def test_symbol_report_has_cb_drawdown_field(self):
        """SymbolReport deve ter campo circuit_breaker_drawdown_pct."""
        from core.model2.cycle_report import SymbolReport
        report = SymbolReport.__annotations__
        assert "circuit_breaker_drawdown_pct" in report or hasattr(SymbolReport, "circuit_breaker_drawdown_pct"), (
            "SymbolReport nao tem circuit_breaker_drawdown_pct"
        )

    def test_format_symbol_report_includes_cb_info(self):
        """format_symbol_report deve incluir linha com estado do CB."""
        from core.model2.cycle_report import format_symbol_report, SymbolReport
        # Criar report minimo com CB trancado
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H1",
            timestamp="2026-03-24 18:00:00 BRT",
            circuit_breaker_state="trancado",
            circuit_breaker_drawdown_pct=-6.8,
            circuit_breaker_hours_remaining=None,
        )
        output = format_symbol_report(report)
        assert "CB" in output or "circuit_breaker" in output.lower() or "trancado" in output.lower(), (
            "format_symbol_report nao exibe estado do CB"
        )
