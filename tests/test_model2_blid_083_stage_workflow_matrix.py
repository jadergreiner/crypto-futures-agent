"""RED suite for BLID-083: stage workflow test stratification."""

from __future__ import annotations

import importlib
from typing import Any

import pytest


def _stage_matrix_module() -> Any:
    return importlib.import_module("core.model2.stage_test_matrix")


@pytest.mark.unit
def test_build_workflow_stage_matrix_contains_all_agents() -> None:
    """R1: matrix must expose stage entries from 1.backlog-development to 8.project-manager."""
    # Arrange
    module = _stage_matrix_module()
    build_matrix = getattr(module, "build_workflow_stage_matrix")

    # Act
    matrix = build_matrix()

    # Assert
    expected = {
        "1.backlog-development",
        "2.product-owner",
        "3.solution-architect",
        "4.qa-tdd",
        "5.software-engineer",
        "6.tech-lead",
        "7.doc-advocate",
        "8.project-manager",
    }
    assert expected.issubset(set(matrix.keys()))


@pytest.mark.unit
def test_resolve_stage_profile_backlog_development_returns_fast() -> None:
    """R2: early stage must use fast profile by default."""
    # Arrange
    module = _stage_matrix_module()
    resolve_profile = getattr(module, "resolve_stage_profile")

    # Act
    profile = resolve_profile("1.backlog-development")

    # Assert
    assert profile == "rapido"


@pytest.mark.unit
def test_resolve_stage_profile_project_manager_returns_regression() -> None:
    """R3: final stage must run regression profile before acceptance."""
    # Arrange
    module = _stage_matrix_module()
    resolve_profile = getattr(module, "resolve_stage_profile")

    # Act
    profile = resolve_profile("8.project-manager")

    # Assert
    assert profile == "regressao"


@pytest.mark.unit
def test_build_profile_command_fast_includes_marker_expression() -> None:
    """R4: fast profile must use marker selection and avoid full suite."""
    # Arrange
    module = _stage_matrix_module()
    command_for_profile = getattr(module, "build_profile_command")

    # Act
    command = command_for_profile("rapido")

    # Assert
    assert command.startswith("pytest -q ")
    assert "-m " in command
    assert "unit" in command
    assert "contract" in command


@pytest.mark.unit
def test_build_profile_command_complete_equals_full_suite() -> None:
    """R5: complete profile must preserve baseline full-suite command."""
    # Arrange
    module = _stage_matrix_module()
    command_for_profile = getattr(module, "build_profile_command")

    # Act
    command = command_for_profile("completo")

    # Assert
    assert command == "pytest -q tests/"


@pytest.mark.unit
def test_fast_profile_budget_seconds_is_45() -> None:
    """R6: fast profile SLO target must be fixed at <=45 seconds."""
    # Arrange
    module = _stage_matrix_module()
    budget_seconds = getattr(module, "FAST_PROFILE_BUDGET_SECONDS")

    # Act + Assert
    assert budget_seconds == 45


@pytest.mark.integration
def test_build_stage_command_qa_tdd_includes_contract_risk_docs_gate() -> None:
    """R7: QA-TDD stage command must include mandatory contract/risk/docs gate markers."""
    # Arrange
    module = _stage_matrix_module()
    build_stage_command = getattr(module, "build_stage_command")

    # Act
    command = build_stage_command("4.qa-tdd")

    # Assert
    assert "contract" in command
    assert "risk" in command
    assert "docs" in command


@pytest.mark.integration
def test_build_stage_command_software_engineer_uses_fast_profile_and_stage_selector() -> None:
    """R8: Software Engineer stage should keep fast profile with deterministic selector."""
    # Arrange
    module = _stage_matrix_module()
    build_stage_command = getattr(module, "build_stage_command")

    # Act
    command = build_stage_command("5.software-engineer")

    # Assert
    assert command.startswith("pytest -q ")
    assert "software-engineer" in command


@pytest.mark.integration
def test_build_stage_command_tech_lead_keeps_full_suite_without_k_filter() -> None:
    """R8b: complete profile must not narrow test scope with extra -k filtering."""
    # Arrange
    module = _stage_matrix_module()
    build_stage_command = getattr(module, "build_stage_command")

    # Act
    command = build_stage_command("6.tech-lead")

    # Assert
    assert command == "pytest -q tests/"
    assert ' -k "' not in command


@pytest.mark.integration
def test_validate_gate_execution_missing_docs_marker_returns_false() -> None:
    """R9: gate validation must fail when required docs marker was not executed."""
    # Arrange
    module = _stage_matrix_module()
    validate_gate_execution = getattr(module, "validate_gate_execution")
    executed_markers = {"contract", "risk"}

    # Act
    result = validate_gate_execution("4.qa-tdd", executed_markers)

    # Assert
    assert result is False


@pytest.mark.integration
def test_validate_gate_execution_all_markers_returns_true() -> None:
    """R10: gate validation should pass only when all required markers are present."""
    # Arrange
    module = _stage_matrix_module()
    validate_gate_execution = getattr(module, "validate_gate_execution")
    executed_markers = {"contract", "risk", "docs"}

    # Act
    result = validate_gate_execution("4.qa-tdd", executed_markers)

    # Assert
    assert result is True


@pytest.mark.contract
def test_regression_profile_includes_risk_gate_and_circuit_breaker_targets() -> None:
    """R11: regression profile must enforce explicit risk_gate/circuit_breaker coverage."""
    # Arrange
    module = _stage_matrix_module()
    build_profile_targets = getattr(module, "build_profile_targets")

    # Act
    targets = build_profile_targets("regressao")

    # Assert
    joined = " ".join(targets)
    assert "risk_gate" in joined
    assert "circuit_breaker" in joined


@pytest.mark.contract
def test_stage_matrix_preserves_decision_id_guardrail_metadata() -> None:
    """R12: every stage entry must carry decision_id idempotency guardrail metadata."""
    # Arrange
    module = _stage_matrix_module()
    build_matrix = getattr(module, "build_workflow_stage_matrix")

    # Act
    matrix = build_matrix()

    # Assert
    for stage, config in matrix.items():
        assert config["guardrails"]["decision_id"] == "IDEMPOTENTE", stage


@pytest.mark.contract
def test_unknown_stage_build_stage_command_raises_value_error() -> None:
    """R13: unknown stage must fail-safe with ValueError."""
    # Arrange
    module = _stage_matrix_module()
    build_stage_command = getattr(module, "build_stage_command")

    # Act + Assert
    with pytest.raises(ValueError):
        build_stage_command("9.qa-live")
