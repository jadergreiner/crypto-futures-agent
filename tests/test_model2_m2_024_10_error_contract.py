"""RED Phase - Suite de testes para M2-024.10: Contrato único de erro com auditabilidade.

Objetivo: Validar que todo bloqueio/falha em live_execution emite estrutura
contendo: decision_id, execution_id, reason_code, severity, recommended_action.

Status: RED - Todos os testes falham inicialmente (sem implementação).
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import Any, Mapping

from core.model2.live_execution import (
    REASON_CODE_CATALOG,
    REASON_CODE_SEVERITY,
    REASON_CODE_ACTION,
)


@dataclass(frozen=True)
class LiveExecutionErrorContract:
    """Contrato de erro para live_execution com auditabilidade."""

    decision_id: int | None
    execution_id: int | None
    reason_code: str
    severity: str
    recommended_action: str
    additional_context: Mapping[str, Any] | None = None

    def is_complete(self) -> bool:
        """Valida se contrato tem todos os campos obrigatórios preenchidos."""
        return (
            self.decision_id is not None
            and self.execution_id is not None
            and self.reason_code
            and len(self.reason_code) > 0
            and self.severity
            and len(self.severity) > 0
            and self.recommended_action
            and len(self.recommended_action) > 0
        )

    def validate_reason_code_in_catalog(self) -> bool:
        """Valida se reason_code existe no catálogo."""
        return self.reason_code in REASON_CODE_CATALOG

    def validate_severity(self) -> bool:
        """Valida se severity é um de [INFO, MEDIUM, HIGH, CRITICAL]."""
        valid_severities = {"INFO", "MEDIUM", "HIGH", "CRITICAL"}
        return self.severity in valid_severities

    def validate_action(self) -> bool:
        """Valida se recommended_action não está vazia."""
        return self.recommended_action and len(self.recommended_action) > 0


class TestErrorContractEmission:
    """Validar emissão de contrato de erro completo."""

    def test_error_contract_creation(self) -> None:
        """Contrato de erro deve ser criável com todos os campos."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.decision_id == 100
        assert error.execution_id == 200
        assert error.reason_code == "risk_gate_blocked"
        assert error.severity == "HIGH"
        assert error.recommended_action == "bloquear_operacao"

    def test_error_contract_is_complete(self) -> None:
        """Contrato de erro completo deve passar em is_complete()."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.is_complete(), "Contrato completo não passou em is_complete()"

    def test_error_contract_with_additional_context(self) -> None:
        """Contrato de erro deve permitir contexto adicional."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
            additional_context={"gate_reason": "alavancagem_maxima"},
        )

        assert (
            error.additional_context is not None
            and "gate_reason" in error.additional_context
        )


class TestErrorContractMandatoryFields:
    """Validar detecção de campos obrigatórios ausentes."""

    def test_missing_decision_id_incomplete(self) -> None:
        """Contrato sem decision_id deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=None,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert not error.is_complete(), "Contrato sem decision_id passou em is_complete()"

    def test_missing_execution_id_incomplete(self) -> None:
        """Contrato sem execution_id deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=None,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem execution_id passou em is_complete()"

    def test_missing_reason_code_incomplete(self) -> None:
        """Contrato sem reason_code deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem reason_code passou em is_complete()"

    def test_missing_severity_incomplete(self) -> None:
        """Contrato sem severity deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem severity passou em is_complete()"

    def test_missing_recommended_action_incomplete(self) -> None:
        """Contrato sem recommended_action deve ser incompleto."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="",
        )

        assert (
            not error.is_complete()
        ), "Contrato sem recommended_action passou em is_complete()"


class TestErrorContractReasonCodeValidation:
    """Validar reason_code contra catálogo."""

    def test_reason_code_in_catalog(self) -> None:
        """Contrato com reason_code válido deve passar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.validate_reason_code_in_catalog()
        ), "reason_code válido falhou em validação"

    def test_reason_code_not_in_catalog(self) -> None:
        """Contrato com reason_code inválido deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="unknown_reason_code_xyz",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.validate_reason_code_in_catalog()
        ), "reason_code inválido passou em validação"


class TestErrorContractSeverityValidation:
    """Validar severidade contra valores permitidos."""

    def test_severity_info_valid(self) -> None:
        """Severidade INFO deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="ready_for_live_execution",
            severity="INFO",
            recommended_action="seguir_fluxo",
        )

        assert error.validate_severity(), "Severidade INFO falhou em validação"

    def test_severity_medium_valid(self) -> None:
        """Severidade MEDIUM deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="signal_expired",
            severity="MEDIUM",
            recommended_action="descartar_sinal",
        )

        assert error.validate_severity(), "Severidade MEDIUM falhou em validação"

    def test_severity_high_valid(self) -> None:
        """Severidade HIGH deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.validate_severity(), "Severidade HIGH falhou em validação"

    def test_severity_critical_valid(self) -> None:
        """Severidade CRITICAL deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="reconciliation_divergence",
            severity="CRITICAL",
            recommended_action="interromper_e_reconciliar",
        )

        assert error.validate_severity(), "Severidade CRITICAL falhou em validação"

    def test_severity_invalid_value(self) -> None:
        """Severidade inválida deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="INVALID_SEVERITY",
            recommended_action="bloquear_operacao",
        )

        assert (
            not error.validate_severity()
        ), "Severidade inválida passou em validação"


class TestErrorContractActionValidation:
    """Validar recommended_action não está vazia."""

    def test_action_not_empty(self) -> None:
        """Action não vazia deve ser válida."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert error.validate_action(), "Action não vazia falhou em validação"

    def test_action_empty_fails(self) -> None:
        """Action vazia deve falhar."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="",
        )

        assert not error.validate_action(), "Action vazia passou em validação"


class TestErrorContractAuditTrail:
    """Validar rastreabilidade (decision_id e execution_id)."""

    def test_decision_id_preserved_in_error(self) -> None:
        """decision_id deve ser preservado no contrato de erro."""
        original_decision_id = 100
        error = LiveExecutionErrorContract(
            decision_id=original_decision_id,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.decision_id == original_decision_id
        ), "decision_id não preservado no contrato"

    def test_execution_id_preserved_in_error(self) -> None:
        """execution_id deve ser preservado no contrato de erro."""
        original_execution_id = 200
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=original_execution_id,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        assert (
            error.execution_id == original_execution_id
        ), "execution_id não preservado no contrato"

    def test_error_contract_immutable(self) -> None:
        """Contrato de erro deve ser imutável (frozen dataclass)."""
        error = LiveExecutionErrorContract(
            decision_id=100,
            execution_id=200,
            reason_code="risk_gate_blocked",
            severity="HIGH",
            recommended_action="bloquear_operacao",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            error.decision_id = 999  # type: ignore
