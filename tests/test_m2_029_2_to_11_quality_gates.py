"""RED->GREEN suite for M2-029.2..11 quality gates."""

from __future__ import annotations

import pytest

from core.dev_cycle_quality_gates import (
    audit_blid_traceability,
    audit_tl_reproduction_script,
    build_mypy_strict_scope_plan,
    evaluate_minimum_coverage_gate,
    evaluate_paper_to_live_matrix,
    evaluate_shadow_to_paper_matrix,
    run_guardrail_diff_preflight,
    run_package_regression_audit,
    validate_slash_and_handoff_contracts,
    validate_unified_payload_contract,
)


def test_m2_029_2_coverage_gate_fails_modules_below_threshold() -> None:
    result = evaluate_minimum_coverage_gate(
        coverage_by_module={"risk": 82.0, "execution": 70.0, "reconciliation": 91.0},
        threshold_by_module={"risk": 80.0, "execution": 75.0, "reconciliation": 90.0},
    )
    assert result.passed is False
    assert result.failed_modules == ("execution",)


def test_m2_029_3_build_mypy_scope_plan_includes_changed_and_critical_targets() -> None:
    plan = build_mypy_strict_scope_plan(
        changed_files=["core/dev_cycle_executor.py", "tests/x.py"],
        critical_contracts=["core/handoff_payload_validator.py"],
    )
    assert plan.targets == ("core/dev_cycle_executor.py", "core/handoff_payload_validator.py")
    assert plan.command.startswith("mypy --strict ")


def test_m2_029_4_unified_payload_contract_validates_required_and_size() -> None:
    result = validate_unified_payload_contract(
        stage_payloads={"2.product-owner": {"id": "A", "score": "4.0"}},
        required_fields_by_stage={"2.product-owner": ("id", "score", "objetivo")},
        max_chars_by_stage={"2.product-owner": 200},
    )
    assert result.valid is False
    assert "2.product-owner:campo_obrigatorio_ausente_objetivo" in result.errors


def test_m2_029_5_traceability_audit_detects_missing_docs_link() -> None:
    result = audit_blid_traceability(
        [{"id": "BLID-1", "tests": ["t.py"], "code": ["c.py"], "docs": []}]
    )
    assert result.valid is False
    assert result.missing_links == ("BLID-1:docs",)


def test_m2_029_6_tl_reproduction_audit_requires_all_steps() -> None:
    result = audit_tl_reproduction_script(available_steps=["pytest_scope", "mypy_scope"])
    assert result.ready is False
    assert "diff_guardrails" in result.missing_steps


def test_m2_029_7_guardrail_preflight_blocks_sensitive_disable_patterns() -> None:
    result = run_guardrail_diff_preflight(diff_text="risk_gate disabled and decision_id removed")
    assert result.blocked is True
    assert "risk_gate_desabilitado" in result.reasons
    assert "decision_id_idempotencia_quebrada" in result.reasons


def test_m2_029_8_shadow_to_paper_matrix_returns_no_go_when_metric_below_threshold() -> None:
    decision = evaluate_shadow_to_paper_matrix(
        metrics={"win_rate": 0.48, "sharpe": 0.9, "drawdown_ok": 1.0},
        thresholds={"win_rate": 0.5, "sharpe": 0.8},
    )
    assert decision.decision == "NO_GO"
    assert decision.failed_metrics == ("win_rate",)


def test_m2_029_9_paper_to_live_matrix_requires_fail_safe_ok() -> None:
    decision = evaluate_paper_to_live_matrix(
        metrics={"win_rate": 0.7, "sharpe": 1.2},
        thresholds={"win_rate": 0.5, "sharpe": 1.0},
        fail_safe_ok=False,
    )
    assert decision.decision == "NO_GO"
    assert decision.failed_metrics == ("fail_safe",)


def test_m2_029_10_regression_audit_reports_missing_checks() -> None:
    result = run_package_regression_audit(checks={"unit": True, "integration": False, "risk": False})
    assert result.ready is False
    assert result.missing_checks == ("integration", "risk")


def test_m2_029_11_slash_and_handoff_contracts_detect_invalid_payload() -> None:
    result = validate_slash_and_handoff_contracts(
        slash_inputs={"/tech-lead": "", "product-owner": "ok"},
        handoff_payloads={"po_sa": {"id": "A"}},
        required_handoff_keys={"po_sa": ("id", "objetivo")},
    )
    assert result.valid is False
    assert "slash_payload_vazio:/tech-lead" in result.errors
    assert "slash_invalido:product-owner" in result.errors
    assert "handoff_campo_ausente:po_sa:objetivo" in result.errors


def test_m2_029_3_mypy_scope_fails_safe_when_no_targets() -> None:
    with pytest.raises(ValueError, match="mypy_scope_vazio"):
        build_mypy_strict_scope_plan(changed_files=["README.md"], critical_contracts=[])
