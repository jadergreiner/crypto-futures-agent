"""RED->GREEN suite for M2-029.12..15 + M2-030.13..15 + M2-027.3..5."""

from __future__ import annotations

from datetime import UTC, datetime

from core.dev_cycle_acceptance_pack import (
    build_daily_cycle_snapshot,
    build_final_acceptance_runbook,
    build_orchestration_decision_runbook,
    build_pre_merge_risk_report,
    build_status_transition_sla_report,
    evaluate_documentation_impact,
    evaluate_orphan_exit_guard,
    govern_backlog_status_sla,
    validate_package_runbook_governance,
    validate_transactional_consistency,
)


def test_m2_029_12_build_daily_cycle_snapshot() -> None:
    snapshot = build_daily_cycle_snapshot(
        rows=[
            {"id": "A", "stage": "6.tech-lead", "status": "AGUARDANDO_CORRECAO"},
            {"id": "B", "stage": "8.project-manager", "status": "PRONTO"},
        ],
        snapshot_at=datetime(2026, 3, 27, tzinfo=UTC),
    )
    assert snapshot.snapshot_date == "2026-03-27"
    assert snapshot.blocked_items == ("A",)
    assert snapshot.ready_items == ("B",)


def test_m2_029_13_govern_backlog_status_sla_detects_violation() -> None:
    result = govern_backlog_status_sla(
        items=[{"id": "X", "status": "Em analise", "age_hours": 30}],
        limits_by_status={"Em analise": 24},
    )
    assert result.compliant is False
    assert result.violations == ("X:Em analise:30>24",)


def test_m2_029_14_evaluate_documentation_impact_blocks_missing_required_docs() -> None:
    result = evaluate_documentation_impact(
        changed_files=["core/dev_cycle_executor.py", "scripts/model2/run.py"],
        docs_present=["docs/BACKLOG.md", "docs/SYNCHRONIZATION.md"],
    )
    assert result.blocked is True
    assert "docs/ARQUITETURA_ALVO.md" in result.missing_docs
    assert "docs/REGRAS_DE_NEGOCIO.md" in result.missing_docs


def test_m2_029_15_build_final_acceptance_runbook_requires_all_checks() -> None:
    result = build_final_acceptance_runbook(
        checks={"validar_backlog_concluido": True, "validar_suite_verde": False}
    )
    assert result.ready is False
    assert "validar_suite_verde" in result.missing


def test_m2_030_13_build_status_transition_sla_report_uses_default_limits() -> None:
    result = build_status_transition_sla_report(
        items=[{"id": "A", "status": "EM_DESENVOLVIMENTO", "age_hours": 72}]
    )
    assert result.compliant is False


def test_m2_030_14_build_pre_merge_risk_report_scores_residual_and_failing_checks() -> None:
    report = build_pre_merge_risk_report(
        residual_risks=["risk_a", "risk_b"],
        failing_checks=["check_1"],
    )
    assert report.risk_score == 5.0
    assert "check_1" in report.highlights


def test_m2_030_15_build_orchestration_decision_runbook_returns_devolver_when_any_gate_fails() -> None:
    runbook = build_orchestration_decision_runbook(preflight_ok=True, docs_ok=False, clean_tree=True)
    assert runbook.decision == "DEVOLVER"


def test_m2_027_3_evaluate_orphan_exit_guard_blocks_without_external_fill_confirmation() -> None:
    result = evaluate_orphan_exit_guard(has_orphan_position=True, has_external_fill_confirmation=False)
    assert result.blocked is True


def test_m2_027_4_validate_transactional_consistency_detects_state_divergence() -> None:
    result = validate_transactional_consistency(
        order_layer_state="ENTRY_FILLED",
        live_execution_state="EXITED",
    )
    assert result.consistent is False


def test_m2_027_5_validate_package_runbook_governance_requires_core_sections() -> None:
    result = validate_package_runbook_governance(sections=("objetivo", "guardrails"))
    assert result.complete is False
    assert result.missing_sections == ("rollback", "aceite")
