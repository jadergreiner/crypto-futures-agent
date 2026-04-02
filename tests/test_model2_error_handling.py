"""Suite QA-TDD para M2-022.4 - padronizacao de erros e timeouts."""

from __future__ import annotations

import pytest

from core.model2.live_execution import (
    REASON_CODE_ACTION,
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
)


class _UnhandledOperationalError(Exception):
    """Erro propositalmente nao mapeado para validar fallback fail-safe."""


def test_timeout_policy_defaults_are_explicit_for_api_db_and_live() -> None:
    """API, DB e live devem expor budgets explicitos de timeout."""
    from core.model2.error_handling import ErrorTimeoutPolicy, resolve_timeout_seconds

    policy = ErrorTimeoutPolicy()

    assert policy.api_timeout_seconds > 0
    assert policy.db_timeout_seconds > 0
    assert policy.live_timeout_seconds > 0
    assert resolve_timeout_seconds(source="api", policy=policy) == policy.api_timeout_seconds
    assert resolve_timeout_seconds(source="db", policy=policy) == policy.db_timeout_seconds
    assert resolve_timeout_seconds(source="live", policy=policy) == policy.live_timeout_seconds


@pytest.mark.parametrize(
    ("error", "expected_category", "expected_reason_code", "expected_retry"),
    [
        (TimeoutError("api demorou"), "timeout", "timeout", True),
        (ConnectionError("socket reset"), "transient", "transient_error", True),
        (ValueError("payload invalido"), "validation", "validation_error", False),
        (RuntimeError("falha permanente"), "permanent", "permanent_error", False),
        (_UnhandledOperationalError("nao mapeado"), "unknown", "unknown_execution_error", False),
    ],
)
def test_classify_execution_error_maps_five_categories_deterministically(
    error: Exception,
    expected_category: str,
    expected_reason_code: str,
    expected_retry: bool,
) -> None:
    """As 5 categorias canonicas devem produzir contrato deterministico."""
    from core.model2.error_handling import classify_execution_error

    ctx = classify_execution_error(
        error,
        source="api",
        operation="fetch_account",
        decision_id=12345,
        execution_id=987,
    )

    assert ctx["category"] == expected_category
    assert ctx["reason_code"] == expected_reason_code
    assert ctx["should_retry"] is expected_retry
    assert ctx["decision_id"] == 12345
    assert ctx["execution_id"] == 987


def test_build_error_event_preserves_correlation_and_catalog_metadata() -> None:
    """decision_id/execution_id devem seguir ate o evento auditavel."""
    from core.model2.error_handling import build_error_event, classify_execution_error

    ctx = classify_execution_error(
        TimeoutError("timeout em send_order"),
        source="live",
        operation="send_order",
        decision_id=77,
        execution_id=88,
    )
    event = build_error_event(ctx)

    assert event["decision_id"] == 77
    assert event["execution_id"] == 88
    assert event["reason_code"] in REASON_CODE_CATALOG
    assert event["severity"] == REASON_CODE_SEVERITY[event["reason_code"]]
    assert event["recommended_action"] == REASON_CODE_ACTION[event["reason_code"]]


def test_shadow_load_validation_keeps_audit_context_for_timeout() -> None:
    """Integracao: camada de validacao shadow deve manter correlacao auditavel."""
    from core.model2.shadow_load_validation import classify_operational_error

    payload = classify_operational_error(
        source="api",
        error_kind="timeout",
        decision_id=55,
        execution_id=66,
    )

    assert payload["category"] == "transient"
    assert payload["reason_code"] == "timeout"
    assert payload["decision_id"] == 55
    assert payload["execution_id"] == 66


def test_live_service_unknown_error_uses_standardized_fail_safe_contract() -> None:
    """Live service deve normalizar falha desconhecida com contrato unico."""
    from core.model2.live_service import Model2LiveExecutionService

    payload = Model2LiveExecutionService.classify_unknown_execution_error(
        _UnhandledOperationalError("boom"),
        decision_id=9001,
        execution_id=42,
    )

    assert payload["reason_code"] == "unknown_execution_error"
    assert payload["decision_id"] == 9001
    assert payload["execution_id"] == 42
    assert payload["recommended_action"] == "bloquear_operacao"
