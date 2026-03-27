"""RED->GREEN suite for M2-031.12..20 package governance."""

from __future__ import annotations

from datetime import UTC, datetime

from core.dev_cycle_package_governance import (
    build_package_executive_closure,
    build_package_throughput_dashboard,
    build_traceability_checkpoint,
    consolidate_package_handoff_contract,
    evaluate_backlog_sla,
    evaluate_doc_advocate_gate,
    evaluate_package_go_no_go,
    generate_package_resume_runbook,
    run_pm_preflight_check,
)


def test_m2_031_12_consolidate_package_handoff_contract() -> None:
    result = consolidate_package_handoff_contract(
        handoffs=[{"id": "M2-031.12", "objetivo": "ok"}, {"id": "M2-031.13"}],
        required_fields=["id", "objetivo"],
    )
    assert result.valid is False
    assert "M2-031.13" in result.invalid_items


def test_m2_031_13_traceability_checkpoint_requires_tests_code_docs() -> None:
    result = build_traceability_checkpoint(
        [
            {"id": "M2-031.13-A", "tests": ["t.py"], "code": ["c.py"], "docs": ["d.md"]},
            {"id": "M2-031.13-B", "tests": [], "code": ["c.py"], "docs": []},
        ]
    )
    assert result.ready is False
    assert "M2-031.13-B:tests_ausentes" in result.missing_links
    assert "M2-031.13-B:docs_ausentes" in result.missing_links


def test_m2_031_14_doc_advocate_gate_blocks_missing_sync_or_required_docs() -> None:
    result = evaluate_doc_advocate_gate(
        changed_files=["core/dev_cycle_executor.py"],
        existing_docs=["docs/BACKLOG.md"],
        synced_item_ids=["M2-031.14-A"],
        expected_item_ids=["M2-031.14-A", "M2-031.14-B"],
    )
    assert result.blocked is True
    assert "docs/ARQUITETURA_ALVO.md" in result.missing_docs
    assert "M2-031.14-B" in result.missing_sync_items


def test_m2_031_15_throughput_dashboard_counts_wip_completed_and_blocked() -> None:
    dashboard = build_package_throughput_dashboard(
        [
            {"stage": "5.software-engineer", "status": "CONCLUIDO"},
            {"stage": "6.tech-lead", "status": "AGUARDANDO_CORRECAO"},
            {"stage": "6.tech-lead", "status": "EM_ANALISE"},
        ]
    )
    assert dashboard.total_items == 3
    assert dashboard.completed_items == 1
    assert dashboard.blocked_items == 1
    assert dashboard.wip_by_stage["6.tech-lead"] == 2


def test_m2_031_16_backlog_sla_detects_violations_by_status_limit() -> None:
    result = evaluate_backlog_sla(
        items=[
            {"id": "M2-031.16-A", "status": "Em analise", "age_hours": 30},
            {"id": "M2-031.16-B", "status": "CONCLUIDO", "age_hours": 2},
        ],
        sla_hours_by_status={"Em analise": 24, "CONCLUIDO": 999},
        now_utc=datetime.now(tz=UTC),
    )
    assert result.compliant is False
    assert result.violations[0].startswith("M2-031.16-A:sla_estourado_Em analise")


def test_m2_031_17_go_no_go_matrix_returns_no_go_when_any_criterion_fails() -> None:
    decision = evaluate_package_go_no_go(
        {"suite_verde": True, "docs_sync": False, "guardrails_ok": True}
    )
    assert decision.decision == "NO_GO"
    assert decision.failed_criteria == ("docs_sync",)


def test_m2_031_18_pm_preflight_requires_concluded_items_green_suite_clean_tree_and_commit() -> None:
    preflight = run_pm_preflight_check(
        item_statuses={"M2-031.18-A": "CONCLUIDO", "M2-031.18-B": "EM_DESENVOLVIMENTO"},
        suite_passed=True,
        clean_tree=False,
        commit_hash="",
    )
    assert preflight.ready_for_acceptance is False
    assert "arvore_local_suja" in preflight.errors
    assert "commit_hash_ausente" in preflight.errors


def test_m2_031_19_resume_runbook_builds_actionable_steps() -> None:
    steps = generate_package_resume_runbook(
        [
            {
                "item_id": "M2-031.19-A",
                "blocked_stage": "Tech Lead",
                "return_stage": "Software Engineer",
                "reason_code": "tl_devolvido_para_se",
            }
        ]
    )
    assert steps == ("M2-031.19-A:corrigir_Software Engineer:tl_devolvido_para_se",)


def test_m2_031_20_executive_closure_returns_aceite_when_all_items_done() -> None:
    closure = build_package_executive_closure(
        package_id="M2-031",
        item_statuses={"M2-031.20-A": "CONCLUIDO", "M2-031.20-B": "CONCLUIDO"},
        commit_hash="abc123",
        clean_tree=True,
    )
    assert closure.status == "ACEITE"
