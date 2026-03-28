"""Suite RED M2-025.7: retry seguro para leitura de mercado.

Objetivo:
- Definir contrato de RetryPolicy para falhas transitorias de leitura.
- Exigir fallback conservador ao esgotar budget de retry.
- Garantir reason_code canonico no contrato de execucao.

Status esperado nesta fase: RED (falhas antes da implementacao).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class TestRetryPolicyContract:
    """R1: contrato de RetryPolicy (imutavel e configuravel)."""

    def test_retry_policy_is_frozen_dataclass(self) -> None:
        """RetryPolicy deve ser dataclass frozen para evitar mutacoes em runtime."""
        from core.model2.market_reader import RetryPolicy

        policy = RetryPolicy(max_retries=3, backoff_base_ms=100, max_budget_ms=500)
        with pytest.raises(FrozenInstanceError):
            policy.max_retries = 4

    def test_retry_policy_keeps_configured_values(self) -> None:
        """RetryPolicy deve preservar os valores configurados no construtor."""
        from core.model2.market_reader import RetryPolicy

        policy = RetryPolicy(max_retries=4, backoff_base_ms=250, max_budget_ms=2_000)
        assert policy.max_retries == 4
        assert policy.backoff_base_ms == 250
        assert policy.max_budget_ms == 2_000


class TestRetryClassificationContract:
    """R2: classificacao de falhas transitorias vs permanentes."""

    def test_classify_market_read_exception_returns_transient_for_timeout(self) -> None:
        """TimeoutError deve ser classificado como transient."""
        from core.model2.market_reader import classify_market_read_exception

        assert classify_market_read_exception(TimeoutError("timeout")) == "transient"

    def test_classify_market_read_exception_returns_permanent_for_value_error(self) -> None:
        """ValueError deve ser classificado como permanent."""
        from core.model2.market_reader import classify_market_read_exception

        assert classify_market_read_exception(ValueError("bad payload")) == "permanent"


class TestReadMarketWithRetryContract:
    """R3/R4: comportamento de retry com budget e fallback conservador."""

    def test_read_market_with_retry_retries_transient_until_success(self) -> None:
        """Falha transitoria seguida de sucesso deve consumir retry e retornar payload."""
        from core.model2.market_reader import RetryPolicy, read_market_with_retry

        read_once = MagicMock(
            side_effect=[ConnectionError("temporary"), {"price": 100.0, "symbol": "BTCUSDT"}]
        )
        policy = RetryPolicy(max_retries=3, backoff_base_ms=1, max_budget_ms=100)
        result = read_market_with_retry(reader=read_once, policy=policy, sleep_fn=lambda _: None)

        assert read_once.call_count == 2
        assert result["symbol"] == "BTCUSDT"
        assert result["reason_code"] == ""

    def test_read_market_with_retry_does_not_retry_permanent_error(self) -> None:
        """Falha permanente deve abortar sem retries adicionais (fail-safe)."""
        from core.model2.market_reader import RetryPolicy, read_market_with_retry

        always_bad = MagicMock(side_effect=ValueError("invalid response"))
        policy = RetryPolicy(max_retries=3, backoff_base_ms=1, max_budget_ms=100)
        result = read_market_with_retry(reader=always_bad, policy=policy, sleep_fn=lambda _: None)

        assert always_bad.call_count == 1
        assert result["fallback"] is True
        assert result["conservative"] is True
        assert result["reason_code"] == "MARKET_READ_PERMANENT_FAILURE"

    def test_read_market_with_retry_returns_conservative_fallback_when_budget_exhausted(self) -> None:
        """Ao esgotar budget/tentativas, retorno deve ser fallback conservador."""
        from core.model2.market_reader import RetryPolicy, read_market_with_retry

        always_transient = MagicMock(side_effect=ConnectionError("network down"))
        policy = RetryPolicy(max_retries=3, backoff_base_ms=1, max_budget_ms=1)
        result = read_market_with_retry(reader=always_transient, policy=policy, sleep_fn=lambda _: None)

        assert result["fallback"] is True
        assert result["conservative"] is True
        assert result["reason_code"] == "MARKET_READ_RETRY_EXHAUSTED"


class TestReasonCodeCatalogForM20257:
    """R5: reason_code canonico deve existir no catalogo de execucao."""

    def test_reason_code_market_read_retry_exhausted_exists_in_catalog(self) -> None:
        """REASON_CODE_CATALOG deve ter MARKET_READ_RETRY_EXHAUSTED."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "MARKET_READ_RETRY_EXHAUSTED" in REASON_CODE_CATALOG

    def test_reason_code_market_read_retry_exhausted_has_severity_and_action(self) -> None:
        """reason_code novo deve possuir severidade e acao recomendada."""
        from core.model2.live_execution import REASON_CODE_ACTION, REASON_CODE_SEVERITY

        assert REASON_CODE_SEVERITY["MARKET_READ_RETRY_EXHAUSTED"] == "HIGH"
        assert REASON_CODE_ACTION["MARKET_READ_RETRY_EXHAUSTED"] == "bloquear_operacao"

    def test_reason_code_market_read_permanent_failure_exists_in_catalog(self) -> None:
        """Falha permanente de leitura deve ter reason_code canonico proprio."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "MARKET_READ_PERMANENT_FAILURE" in REASON_CODE_CATALOG


class TestLiveServiceIntegrationContract:
    """R6: live_service deve integrar leitura com retry sem bypass de guardrails."""

    def test_live_service_exposes_market_read_with_retry_hook(self) -> None:
        """Servico live deve expor hook dedicado de leitura de mercado com retry."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = LiveExecutionService.__new__(LiveExecutionService)
        assert hasattr(service, "_read_market_state_with_retry")

    def test_live_service_market_read_hook_preserves_decision_id(self) -> None:
        """Hook de leitura deve preservar decision_id para idempotencia auditavel."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = LiveExecutionService.__new__(LiveExecutionService)
        payload = service._read_market_state_with_retry(  # type: ignore[attr-defined]
            symbol="BTCUSDT",
            decision_id=12345,
        )
        assert payload["decision_id"] == 12345

    def test_build_gate_input_calls_market_read_retry_hook(self) -> None:
        """Fluxo de gate deve usar hook de leitura com retry no caminho operacional."""
        from core.model2.live_service import Model2LiveExecutionService as LiveExecutionService

        service = LiveExecutionService.__new__(LiveExecutionService)
        service.exchange = None  # type: ignore[attr-defined]
        service.config = SimpleNamespace(  # type: ignore[attr-defined]
            execution_mode="shadow",
            short_only=False,
            funding_rate_max_for_short=0.05,
            live_symbols=("BTCUSDT",),
            authorized_symbols=("BTCUSDT",),
            max_margin_per_position_usd=100.0,
            max_daily_entries=5,
            symbol_cooldown_ms=60_000,
            max_signal_age_ms=300_000,
        )
        service.repository = MagicMock()  # type: ignore[attr-defined]
        service.repository.get_latest_funding_rate.return_value = None  # type: ignore[attr-defined]
        service.repository.get_latest_basis_value.return_value = None  # type: ignore[attr-defined]
        service.repository.count_live_entries_today.return_value = 0  # type: ignore[attr-defined]
        service.repository.count_active_live_executions_for_symbol.return_value = 0  # type: ignore[attr-defined]
        service.repository.has_recent_live_entry_for_symbol.return_value = False  # type: ignore[attr-defined]
        service._snapshot_guardrail_state = MagicMock(return_value={  # type: ignore[attr-defined]
            "risk_gate_status": "active",
            "risk_gate_allows_order": True,
            "risk_gate_drawdown_pct": 0.0,
            "circuit_breaker_state": "closed",
            "circuit_breaker_allows_trading": True,
            "circuit_breaker_drawdown_pct": 0.0,
        })
        service._read_market_state_with_retry = MagicMock(return_value={"symbol": "BTCUSDT"})  # type: ignore[attr-defined]

        candidate = {
            "id": 1,
            "opportunity_id": 10,
            "symbol": "BTCUSDT",
            "timeframe": "H4",
            "signal_side": "SHORT",
            "status": "CONSUMED",
            "signal_timestamp": 1_700_000_000_000,
            "payload_json": "{}",
            "decision_id": 999,
        }
        _ = service._build_gate_input(candidate, now_ms=1_700_000_100_000)  # type: ignore[attr-defined]
        service._read_market_state_with_retry.assert_called_once_with(  # type: ignore[attr-defined]
            symbol="BTCUSDT",
            decision_id=999,
        )
