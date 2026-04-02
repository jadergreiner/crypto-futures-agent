"""Suite RED — M2-022.3: isolamento de risco por contexto operacional.

Rastreabilidade RF/RNF -> ADR -> testes:
- RF-001 -> modos canonicos `shadow`, `paper`, `live` com fail-safe auditavel
- RF-002 -> bloqueio de contexto inconsistente entre credenciais e modo
- RF-003 -> envelope de risco diferenciado por contexto operacional
- RF-004 -> separacao de limites por simbolo/carteira com escopo por modo
- RF-005 -> trilha auditavel com `decision_id`, `reason_code`, `severity`
- RNF-001 -> sem bypass de `risk_gate` ou `circuit_breaker`
- RNF-002 -> sem alteracao de schema

ADRs: ADR-002, ADR-004, ADR-007, ADR-009.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.model2.live_execution import LiveExecutionGateInput, evaluate_live_execution_gate
from core.model2.live_service import Model2LiveExecutionService
from core.model2.shadow_load_validation import validate_risk_context_isolation
from risk.circuit_breaker import CircuitBreaker
from risk.risk_gate import RiskGate
from scripts.model2.go_live_preflight import _check_guardrails_functional


def _base_gate_input(**overrides: object) -> LiveExecutionGateInput:
    base = LiveExecutionGateInput(
        technical_signal_id=10,
        opportunity_id=20,
        symbol="BTCUSDT",
        timeframe="M5",
        signal_side="SHORT",
        technical_signal_status="CONSUMED",
        signal_timestamp=1_700_000_000_000,
        short_only=False,
        funding_rate=-0.0001,
        basis_value=0.001,
        funding_rate_max_for_short=0.0005,
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        available_balance_usd=150.0,
        max_margin_per_position_usd=15.0,
        recent_entries_today=0,
        max_daily_entries=3,
        symbol_active_execution_count=0,
        open_position_qty=0.0,
        open_position_side="",
        cooldown_active=False,
        signal_age_ms=30_000,
        max_signal_age_ms=240_000,
        risk_gate_status="ativo",
        risk_gate_allows_order=True,
        risk_gate_drawdown_pct=0.0,
        circuit_breaker_state="normal",
        circuit_breaker_allows_trading=True,
        circuit_breaker_drawdown_pct=0.0,
        decision_id=101,
        execution_id=202,
    )
    return LiveExecutionGateInput(**{**base.__dict__, **overrides})


def _service_for_mode(execution_mode: str) -> Model2LiveExecutionService:
    service = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
    service.config = SimpleNamespace(
        execution_mode=execution_mode,
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        short_only=False,
        max_daily_entries=3,
        max_margin_per_position_usd=15.0,
        max_signal_age_ms=240_000,
        symbol_cooldown_ms=120_000,
        funding_rate_max_for_short=0.0005,
    )
    service.exchange = None
    service.repository = SimpleNamespace(
        count_live_entries_today=lambda **kwargs: 2 if kwargs["execution_mode"] == "paper" else 0,
        count_active_live_executions_for_symbol=(
            lambda **kwargs: 1 if kwargs["execution_mode"] == "paper" else 0
        ),
        has_recent_live_entry_for_symbol=lambda **kwargs: False,
        get_latest_funding_rate=lambda **kwargs: None,
        get_latest_basis_value=lambda **kwargs: None,
    )
    service._risk_gate = RiskGate()
    service._circuit_breaker = CircuitBreaker()
    service._guardrail_balance_initialized = False
    service._fetch_available_balance_with_retry = lambda exchange: None
    service._read_market_state_with_retry = lambda **kwargs: {"symbol": kwargs["symbol"]}
    service._extract_funding_and_basis = (
        lambda candidate, market_state=None: (None, None)
    )
    return service


def _candidate() -> dict[str, Any]:
    return {
        "id": 10,
        "opportunity_id": 20,
        "symbol": "BTCUSDT",
        "timeframe": "M5",
        "signal_side": "SHORT",
        "status": "CONSUMED",
        "signal_timestamp": 1_700_000_000_000,
        "decision_id": 101,
        "payload_json": "{}",
    }


# ---------------------------------------------------------------------------
# Unitarios (6)
# ---------------------------------------------------------------------------


def test_gate_accepts_paper_as_canonical_execution_mode_with_audit_fields() -> None:
    """RF-001: `paper` deve ser canônico, auditável e sem cair em shadow."""
    decision = evaluate_live_execution_gate(
        _base_gate_input(
            execution_mode="paper",
            available_balance_usd=None,
        )
    )

    assert decision.allow_execution is True
    assert decision.reason == "ready_for_live_execution"
    assert decision.details["execution_mode"] == "paper"
    assert decision.details["decision_id"] == 101
    assert decision.details["execution_id"] == 202


def test_gate_blocks_invalid_execution_mode_with_fail_safe_audit_fields() -> None:
    """RF-001: modo fora do contrato deve bloquear com trilha auditavel."""
    decision = evaluate_live_execution_gate(
        _base_gate_input(execution_mode="sandbox")
    )

    assert decision.allow_execution is False
    assert decision.reason == "unsupported_execution_mode"
    assert decision.details["reason_code"] == "unsupported_execution_mode"
    assert decision.details["severity"] in {"HIGH", "CRITICAL"}
    assert decision.details["recommended_action"] == "bloquear_operacao"


def test_validate_risk_context_isolation_blocks_shadow_with_live_credentials() -> None:
    """RF-002: shadow nao pode compartilhar credenciais/contexto live."""
    result = validate_risk_context_isolation(
        execution_mode="shadow",
        has_live_api_key=True,
        has_paper_api_key=False,
    )

    assert result["allowed"] is False
    assert result["reason_code"] == "risk_context_isolation_blocked"


def test_validate_risk_context_isolation_blocks_paper_without_paper_credentials() -> None:
    """RF-002: paper deve bloquear quando só existir contexto de live."""
    result = validate_risk_context_isolation(
        execution_mode="paper",
        has_live_api_key=True,
        has_paper_api_key=False,
    )

    assert result["allowed"] is False
    assert result["reason_code"] == "paper_missing_credentials"


def test_build_config_preserves_paper_without_shadow_fallback() -> None:
    """RF-003: build_config deve manter `paper` explícito no contrato."""
    config = Model2LiveExecutionService.build_config(
        execution_mode="paper",
        live_symbols=("btcusdt",),
        short_only=False,
        max_daily_entries=3,
        max_margin_per_position_usd=15.0,
        max_signal_age_ms=240_000,
        symbol_cooldown_ms=120_000,
        funding_rate_max_for_short=0.0005,
    )

    assert config.execution_mode == "paper"
    assert config.live_symbols == ("BTCUSDT",)
    assert config.authorized_symbols == ("BTCUSDT",)


def test_gate_blocks_wallet_daily_limit_per_execution_mode() -> None:
    """RF-004: limite diario por carteira/modo deve bloquear antes da ordem."""
    decision = evaluate_live_execution_gate(
        _base_gate_input(
            execution_mode="paper",
            available_balance_usd=None,
            recent_entries_today=3,
            max_daily_entries=3,
        )
    )

    assert decision.allow_execution is False
    assert decision.reason == "daily_entry_limit_reached"
    assert decision.details["recent_entries_today"] == 3
    assert decision.details["max_daily_entries"] == 3
    assert decision.details["execution_mode"] == "paper"


# ---------------------------------------------------------------------------
# Integracao (3)
# ---------------------------------------------------------------------------


def test_live_service_build_gate_input_preserves_paper_scoping() -> None:
    """INT-001: `live_service` deve manter contagem e modo em escopo `paper`."""
    service = _service_for_mode("paper")

    gate_input = service._build_gate_input(_candidate(), now_ms=1_700_000_060_000)

    assert gate_input.execution_mode == "paper"
    assert gate_input.recent_entries_today == 2
    assert gate_input.symbol_active_execution_count == 1


def test_live_service_snapshot_guardrail_state_exposes_context_envelope() -> None:
    """INT-002: snapshot deve diferenciar `shadow`, `paper` e `live`."""
    shadow_service = _service_for_mode("shadow")
    paper_service = _service_for_mode("paper")
    live_service = _service_for_mode("live")

    shadow_state = shadow_service._snapshot_guardrail_state(None)
    paper_state = paper_service._snapshot_guardrail_state(None)
    live_state = live_service._snapshot_guardrail_state(250.0)

    assert shadow_state["context_envelope"] == "shadow_no_real_order"
    assert paper_state["context_envelope"] == "paper_testnet_validated"
    assert live_state["context_envelope"] == "live_full_guardrails"


def test_live_service_snapshot_guardrail_state_live_without_balance_is_fail_safe() -> None:
    """INT-003: live sem saldo deve continuar conservador e bloquear a ordem."""
    service = _service_for_mode("live")

    state = service._snapshot_guardrail_state(None)

    assert state["risk_gate_status"] == "unavailable"
    assert state["risk_gate_allows_order"] is False
    assert state["circuit_breaker_allows_trading"] is False


# ---------------------------------------------------------------------------
# Regressao / risco (3)
# ---------------------------------------------------------------------------


def test_preflight_guardrails_functional_keeps_risk_gate_and_circuit_breaker_active() -> None:
    """RR-001: preflight deve continuar provando que os guardrails estão ativos."""
    result = _check_guardrails_functional()

    assert result["ok"] is True
    assert result["details"]["risk_gate"]["instantiated"] is True
    assert result["details"]["circuit_breaker"]["instantiated"] is True


def test_blocked_gate_decision_keeps_decision_execution_and_audit_fields() -> None:
    """RR-002: qualquer bloqueio deve preservar correlacao e severidade."""
    decision = evaluate_live_execution_gate(
        _base_gate_input(execution_mode="invalido")
    )

    assert decision.details["reason_code"] == "unsupported_execution_mode"
    assert "severity" in decision.details
    assert "recommended_action" in decision.details


def test_validate_risk_context_isolation_allows_live_when_context_matches() -> None:
    """RR-003: live continua permitido quando o contexto operacional é coerente."""
    result = validate_risk_context_isolation(
        execution_mode="live",
        has_live_api_key=True,
        has_paper_api_key=False,
    )

    assert result["allowed"] is True
    assert result["reason_code"] == "ok"
