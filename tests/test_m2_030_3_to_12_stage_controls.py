"""RED->GREEN suite for M2-030.3..12 stage controls."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.dev_cycle_stage_controls import (
    build_daily_executive_snapshot,
    build_evidence_checkpoint,
    build_tl_local_reproduction,
    evaluate_resume_mode,
    evaluate_stage_status_sla,
    resolve_devolution_matrix,
    run_documentation_gate,
    run_guardrail_diff_gate,
    run_stage8_preacceptance,
    validate_slash_command_contract,
    validate_stage_handoff_schema,
)


def test_m2_030_3_validate_stage_handoff_schema_detects_missing_fields() -> None:
    result = validate_stage_handoff_schema(stage="2.product-owner", payload={"id": "M2-030.3"})
    assert result.valid is False
    assert "score" in result.missing_fields


def test_m2_030_4_evaluate_resume_mode_returns_blocked_stage_when_corrected_handoff_exists() -> None:
    result = evaluate_resume_mode(blocked_stage="Tech Lead", corrected_handoff={"id": "M2-030.4"})
    assert result.can_resume is True
    assert result.restart_stage == "Tech Lead"


def test_m2_030_5_resolve_devolution_matrix_maps_known_routes() -> None:
    result = resolve_devolution_matrix(
        stage="Project Manager",
        decision="DEVOLVER_PARA_AJUSTE",
        motivo="ajuste de doc pendente",
    )
    assert result.return_stage == "Doc Advocate"


def test_m2_030_6_build_tl_local_reproduction_generates_scoped_commands() -> None:
    plan = build_tl_local_reproduction(
        item_id="M2-030.6",
        changed_files=["core/dev_cycle_executor.py", "tests/test_m2_031_8_blocking_matrix.py"],
    )
    assert plan.commands[0].startswith("pytest -q tests/test_m2_031_8_blocking_matrix.py")
    assert "mypy --strict core/dev_cycle_executor.py" in plan.commands[1]


def test_m2_030_7_run_guardrail_diff_gate_blocks_missing_evidence() -> None:
    result = run_guardrail_diff_gate(diff_text="risk_gate changed", evidences_by_guardrail={})
    assert result.blocked is True
    assert "risk_gate" in result.missing_evidences


def test_m2_030_8_build_evidence_checkpoint_requires_tests_code_docs() -> None:
    result = build_evidence_checkpoint(
        [{"id": "M2-030.8", "tests": ["a"], "code": ["b"], "docs": []}]
    )
    assert result.ready is False


def test_m2_030_9_run_documentation_gate_blocks_missing_sync_item() -> None:
    result = run_documentation_gate(
        changed_files=["core/dev_cycle_executor.py"],
        existing_docs=["docs/BACKLOG.md", "docs/SYNCHRONIZATION.md", "docs/ARQUITETURA_ALVO.md"],
        synced_item_ids=["M2-030.9-A"],
        expected_item_ids=["M2-030.9-A", "M2-030.9-B"],
    )
    assert result.blocked is True
    assert "M2-030.9-B" in result.missing_sync_items


def test_m2_030_10_run_stage8_preacceptance_blocks_when_tree_is_dirty() -> None:
    result = run_stage8_preacceptance(
        item_statuses={"M2-030.10": "CONCLUIDO"},
        suite_passed=True,
        clean_tree=False,
        commit_hash="abc",
    )
    assert result.ready_for_acceptance is False
    assert "arvore_local_suja" in result.errors


def test_m2_030_11_validate_slash_command_contract_rejects_unknown_or_empty_payload() -> None:
    unknown = validate_slash_command_contract(command="/unknown", payload="x")
    assert unknown.valid is False
    empty = validate_slash_command_contract(command="/tech-lead", payload=" ")
    assert empty.valid is False


def test_m2_030_12_build_daily_executive_snapshot_and_sla_summary() -> None:
    snapshot = build_daily_executive_snapshot(
        rows=[
            {"id": "A", "status": "CONCLUIDO"},
            {"id": "B", "status": "AGUARDANDO_CORRECAO", "reason": "guardrail"},
            {"id": "C", "status": "PRONTO"},
        ],
        snapshot_date=datetime(2026, 3, 27, tzinfo=UTC),
    )
    assert snapshot.completed_items == 1
    assert snapshot.blocked_items == 1
    assert snapshot.next_ready_items == ("C",)

    sla = evaluate_stage_status_sla(
        items=[{"id": "A", "status": "Em analise", "age_hours": 25}],
        sla_hours_by_status={"Em analise": 24},
        now_utc=datetime(2026, 3, 27, tzinfo=UTC),
    )
    assert sla.compliant is False


def test_m2_030_3_rejects_invalid_stage() -> None:
    with pytest.raises(ValueError, match="stage_invalido"):
        validate_stage_handoff_schema(stage="1.backlog-development", payload={})
