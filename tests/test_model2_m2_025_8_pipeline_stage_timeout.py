"""Suite RED M2-025.8: timeout por etapa critica do pipeline de dados.

Objetivo:
- Definir TimeoutPolicy imutavel com budget_ms por etapa.
- Exigir wrappers de timeout para scanner e validator.
- Exigir telemetria auditavel de expiracao via observability.

Fase esperada: RED (falhas antes da implementacao).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest


class TestTimeoutPolicyContract:
    """R1: contrato de TimeoutPolicy por etapa."""

    def test_timeout_policy_is_frozen_dataclass(self) -> None:
        """TimeoutPolicy deve ser imutavel em runtime."""
        from core.model2.pipeline_timeout import TimeoutPolicy

        policy = TimeoutPolicy(
            collect_timeout_ms=3_000,
            validate_timeout_ms=2_000,
            consolidate_timeout_ms=4_000,
        )
        with pytest.raises(FrozenInstanceError):
            policy.collect_timeout_ms = 500  # type: ignore[misc]

    def test_timeout_policy_keeps_stage_budgets(self) -> None:
        """TimeoutPolicy deve preservar budget_ms configurado por etapa."""
        from core.model2.pipeline_timeout import TimeoutPolicy

        policy = TimeoutPolicy(
            collect_timeout_ms=1_500,
            validate_timeout_ms=2_500,
            consolidate_timeout_ms=3_500,
        )
        assert policy.collect_timeout_ms == 1_500
        assert policy.validate_timeout_ms == 2_500
        assert policy.consolidate_timeout_ms == 3_500

    def test_timeout_policy_rejects_non_positive_budgets(self) -> None:
        """TimeoutPolicy deve rejeitar timeout <= 0 em qualquer etapa."""
        from core.model2.pipeline_timeout import TimeoutPolicy

        with pytest.raises((TypeError, ValueError)):
            TimeoutPolicy(collect_timeout_ms=0, validate_timeout_ms=2_000, consolidate_timeout_ms=3_000)


class TestStageTimeoutChecks:
    """R2: checagem deterministica de expiracao por etapa."""

    def test_check_collect_timeout_within_budget_returns_none(self) -> None:
        """Coleta dentro do budget nao deve retornar reason_code."""
        from core.model2.pipeline_timeout import TimeoutPolicy, check_collect_timeout

        policy = TimeoutPolicy(collect_timeout_ms=1_000, validate_timeout_ms=1_000, consolidate_timeout_ms=1_000)
        assert check_collect_timeout(elapsed_ms=200, policy=policy) is None

    def test_check_validate_timeout_expired_returns_reason(self) -> None:
        """Validacao expirada deve retornar TIMEOUT_VALIDATE."""
        from core.model2.pipeline_timeout import TimeoutPolicy, check_validate_timeout

        policy = TimeoutPolicy(collect_timeout_ms=1_000, validate_timeout_ms=500, consolidate_timeout_ms=1_000)
        assert check_validate_timeout(elapsed_ms=900, policy=policy) == "TIMEOUT_VALIDATE"

    def test_check_consolidate_timeout_expired_returns_reason(self) -> None:
        """Consolidacao expirada deve retornar TIMEOUT_CONSOLIDATE."""
        from core.model2.pipeline_timeout import TimeoutPolicy, check_consolidate_timeout

        policy = TimeoutPolicy(collect_timeout_ms=1_000, validate_timeout_ms=1_000, consolidate_timeout_ms=300)
        assert check_consolidate_timeout(elapsed_ms=600, policy=policy) == "TIMEOUT_CONSOLIDATE"


class TestScannerValidatorTimeoutWrappers:
    """R3/R4: wrappers de scanner e validator com timeout auditavel."""

    def test_wrap_scanner_with_timeout_short_circuits_on_expiry(self) -> None:
        """Scanner deve ser bloqueado quando coleta expirar antes da execucao."""
        from core.model2.pipeline_timeout import TimeoutPolicy, wrap_scanner_with_timeout

        scanner_fn = MagicMock(return_value={"detected": True})
        telemetry_fn = MagicMock()
        policy = TimeoutPolicy(collect_timeout_ms=500, validate_timeout_ms=1_000, consolidate_timeout_ms=1_000)

        result = wrap_scanner_with_timeout(
            scanner_fn=scanner_fn,
            scanner_input={"symbol": "BTCUSDT", "cycle_id": "c-1"},
            policy=policy,
            started_at_ms=1_000,
            now_ms=2_000,
            telemetry_fn=telemetry_fn,
        )

        assert result["timed_out"] is True
        assert result["reason_code"] == "TIMEOUT_COLLECT"
        scanner_fn.assert_not_called()
        telemetry_fn.assert_called_once()

    def test_wrap_validator_with_timeout_short_circuits_on_expiry(self) -> None:
        """Validator deve ser bloqueado quando etapa de validacao expirar."""
        from core.model2.pipeline_timeout import TimeoutPolicy, wrap_validator_with_timeout

        validator_fn = MagicMock(return_value={"is_validated": True})
        telemetry_fn = MagicMock()
        policy = TimeoutPolicy(collect_timeout_ms=1_000, validate_timeout_ms=200, consolidate_timeout_ms=1_000)

        result = wrap_validator_with_timeout(
            validator_fn=validator_fn,
            validation_input={"opportunity_id": 7, "decision_id": 99},
            policy=policy,
            started_at_ms=5_000,
            now_ms=5_400,
            telemetry_fn=telemetry_fn,
        )

        assert result["timed_out"] is True
        assert result["reason_code"] == "TIMEOUT_VALIDATE"
        assert result["decision_id"] == 99
        validator_fn.assert_not_called()
        telemetry_fn.assert_called_once()


class TestObservabilityTimeoutTelemetry:
    """R5: telemetria de expiracao via observability.py."""

    def test_emit_stage_timeout_telemetry_returns_auditable_payload(self) -> None:
        """Payload deve carregar stage, reason_code, elapsed e budget."""
        from core.model2.observability import emit_stage_timeout_telemetry

        payload = emit_stage_timeout_telemetry(
            symbol="BTCUSDT",
            stage="collect",
            elapsed_ms=1_800,
            budget_ms=500,
            cycle_id="c-77",
            reason_code="TIMEOUT_COLLECT",
        )
        assert payload["event_type"] == "stage_timeout_expired"
        assert payload["stage"] == "collect"
        assert payload["elapsed_ms"] == 1_800
        assert payload["budget_ms"] == 500
        assert payload["reason_code"] == "TIMEOUT_COLLECT"
        assert payload["cycle_id"] == "c-77"

    def test_emit_stage_timeout_telemetry_records_timeout_latency(self) -> None:
        """Observability deve registrar latencia com result_code timeout_expired."""
        from core.model2 import observability

        recorder = MagicMock()
        original = observability.registrar_latencia
        observability.registrar_latencia = recorder
        try:
            _ = observability.emit_stage_timeout_telemetry(
                symbol="ETHUSDT",
                stage="validate",
                elapsed_ms=900,
                budget_ms=600,
                cycle_id="c-88",
                reason_code="TIMEOUT_VALIDATE",
            )
        finally:
            observability.registrar_latencia = original

        recorder.assert_called_once_with(
            simbolo="ETHUSDT",
            etapa="validate",
            resultado="timeout_expired",
            latencia_ms=900,
        )
