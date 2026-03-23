"""RED Phase - Suite de testes para M2-024.2: Catálogo canônico de reason_code com severidade.

Objetivo: Validar que todo reason_code possui severidade e ação recomendada vinculadas,
e que falhas em campos obrigatórios são detectadas.

Status: RED - Todos os testes falham inicialmente (sem implementação).
"""

from __future__ import annotations

import pytest

from core.model2.live_execution import (
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
    REASON_CODE_ACTION,
)


class TestReasonCodeCatalogCompleteness:
    """Validar cobertura e completude do catálogo de reason_codes."""

    def test_reason_code_catalog_not_empty(self) -> None:
        """Catálogo de reason_codes não deve estar vazio."""
        assert len(REASON_CODE_CATALOG) > 0, "REASON_CODE_CATALOG vazio"

    def test_all_reason_codes_have_severity(self) -> None:
        """Todo reason_code deve ter severidade vinculada."""
        for code_key in REASON_CODE_CATALOG.keys():
            assert (
                code_key in REASON_CODE_SEVERITY
            ), f"reason_code '{code_key}' sem severidade em REASON_CODE_SEVERITY"

    def test_all_reason_codes_have_action(self) -> None:
        """Todo reason_code deve ter ação recomendada vinculada."""
        for code_key in REASON_CODE_CATALOG.keys():
            assert (
                code_key in REASON_CODE_ACTION
            ), f"reason_code '{code_key}' sem ação em REASON_CODE_ACTION"

    def test_severity_is_valid(self) -> None:
        """Toda severidade deve ser um valor válido."""
        valid_severities = {"INFO", "MEDIUM", "HIGH", "CRITICAL"}
        for code_key, severity in REASON_CODE_SEVERITY.items():
            assert (
                severity in valid_severities
            ), f"reason_code '{code_key}' com severidade inválida: {severity}"

    def test_action_is_not_empty(self) -> None:
        """Toda ação recomendada deve estar preenchida."""
        for code_key, action in REASON_CODE_ACTION.items():
            assert (
                action and len(action.strip()) > 0
            ), f"reason_code '{code_key}' com ação vazia"


class TestReasonCodeCatalogContent:
    """Validar conteúdo específico do catálogo (casos críticos)."""

    def test_reason_code_catalog_value_not_empty(self) -> None:
        """Todo reason_code_value no catálogo deve estar preenchido."""
        for code_key, code_value in REASON_CODE_CATALOG.items():
            assert (
                code_value and len(code_value.strip()) > 0
            ), f"reason_code '{code_key}' com valor vazio no catálogo"

    def test_reason_code_critical_entries_present(self) -> None:
        """Entradas críticas devem estar no catálogo (risk_gate, circuit_breaker, etc)."""
        critical_codes = [
            "risk_gate_blocked",
            "circuit_breaker_blocked",
            "reconciliation_divergence",
        ]
        for code in critical_codes:
            assert code in REASON_CODE_CATALOG, f"Código crítico '{code}' ausente no catálogo"

    def test_critical_reason_codes_have_high_severity(self) -> None:
        """Códigos críticos (risk_gate_blocked, circuit_breaker_blocked, reconciliation_divergence) devem ter severidade HIGH ou CRITICAL."""
        critical_codes = {
            "risk_gate_blocked": {"HIGH", "CRITICAL"},
            "circuit_breaker_blocked": {"HIGH", "CRITICAL"},
            "reconciliation_divergence": {"CRITICAL"},
        }
        for code, expected_severities in critical_codes.items():
            actual_severity = REASON_CODE_SEVERITY.get(code)
            assert (
                actual_severity in expected_severities
            ), f"Código crítico '{code}' com severidade inesperada: {actual_severity}"

    def test_reason_code_catalog_keys_are_strings(self) -> None:
        """Todas as chaves do catálogo devem ser strings."""
        for key in REASON_CODE_CATALOG.keys():
            assert isinstance(key, str), f"Chave não é string: {key} ({type(key)})"

    def test_reason_code_catalog_values_are_strings(self) -> None:
        """Todos os valores do catálogo devem ser strings."""
        for code_key, code_value in REASON_CODE_CATALOG.items():
            assert isinstance(
                code_value, str
            ), f"Valor de '{code_key}' não é string: {code_value} ({type(code_value)})"

    def test_reason_code_severity_values_are_strings(self) -> None:
        """Todos os valores de severidade devem ser strings."""
        for code_key, severity in REASON_CODE_SEVERITY.items():
            assert isinstance(
                severity, str
            ), f"Severidade de '{code_key}' não é string: {severity} ({type(severity)})"

    def test_reason_code_action_values_are_strings(self) -> None:
        """Todos os valores de ação devem ser strings."""
        for code_key, action in REASON_CODE_ACTION.items():
            assert isinstance(
                action, str
            ), f"Ação de '{code_key}' não é string: {action} ({type(action)})"


class TestReasonCodeCatalogConsistency:
    """Validar consistência e simetria do catálogo."""

    def test_no_reason_code_in_severity_without_catalog_entry(self) -> None:
        """Não deve haver severidade para code não no catálogo."""
        for code_key in REASON_CODE_SEVERITY.keys():
            assert (
                code_key in REASON_CODE_CATALOG
            ), f"Severidade para '{code_key}' sem entrada no catálogo"

    def test_no_reason_code_in_action_without_catalog_entry(self) -> None:
        """Não deve haver ação para code não no catálogo."""
        for code_key in REASON_CODE_ACTION.keys():
            assert (
                code_key in REASON_CODE_CATALOG
            ), f"Ação para '{code_key}' sem entrada no catálogo"

    def test_ready_for_live_execution_has_info_severity(self) -> None:
        """'ready_for_live_execution' deve ter severidade INFO."""
        assert (
            REASON_CODE_SEVERITY.get("ready_for_live_execution") == "INFO"
        ), "ready_for_live_execution com severidade != INFO"

    def test_catalog_has_minimum_20_entries(self) -> None:
        """Catálogo deve ter no mínimo 20 entry points para cobertura adequada."""
        assert (
            len(REASON_CODE_CATALOG) >= 20
        ), f"Catálogo com menos de 20 entries: {len(REASON_CODE_CATALOG)}"


class TestReasonCodeMissingFields:
    """Validar detecção de campos obrigatórios ausentes."""

    def test_missing_reason_code_catalog(self) -> None:
        """Se REASON_CODE_CATALOG estiver vazio, deve falhar."""
        assert (
            REASON_CODE_CATALOG is not None and len(REASON_CODE_CATALOG) > 0
        ), "REASON_CODE_CATALOG vazio ou None"

    def test_missing_reason_code_severity(self) -> None:
        """Se REASON_CODE_SEVERITY estiver vazio, deve falhar (para codes do catálogo)."""
        assert (
            REASON_CODE_SEVERITY is not None and len(REASON_CODE_SEVERITY) > 0
        ), "REASON_CODE_SEVERITY vazio ou None"

    def test_missing_reason_code_action(self) -> None:
        """Se REASON_CODE_ACTION estiver vazio, deve falhar (para codes do catálogo)."""
        assert (
            REASON_CODE_ACTION is not None and len(REASON_CODE_ACTION) > 0
        ), "REASON_CODE_ACTION vazio ou None"
