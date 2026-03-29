"""RED->GREEN suite M2-020.11: gate de promocao GO/NO-GO com evidencia minima."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.model2.promotion_gate import PromotionEvaluator
from scripts.model2.healthcheck_live_execution import run_live_healthcheck


def _write_live_dashboard(path: Path, *, timestamp_ms: int, unprotected: int = 0, stale_entries: int = 0, mismatches: int = 0) -> None:
    payload = {
        "timestamp_utc_ms": timestamp_ms,
        "unprotected_filled_count": unprotected,
        "stale_entry_sent_count": stale_entries,
        "open_position_mismatches_count": mismatches,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_m2_020_11_returns_no_go_when_evidence_is_insufficient() -> None:
    evaluator = PromotionEvaluator()

    result = evaluator.evaluate_evidence_gate(
        decision_id="m2-020-11-case-1",
        risk_evidence_ok=False,
        stability_evidence_ok=True,
        consistency_evidence_ok=False,
        evidence_ref="results/model2/runtime/model2_live_dashboard_latest.json",
    )

    assert result.go is False
    assert result.decision == "NO_GO"
    assert result.evidence_sufficient is False
    assert any("risk_evidence_missing" in reason for reason in result.reasons)
    assert any("consistency_evidence_missing" in reason for reason in result.reasons)


def test_m2_020_11_returns_go_when_all_evidence_is_present() -> None:
    evaluator = PromotionEvaluator()

    result = evaluator.evaluate_evidence_gate(
        decision_id="m2-020-11-case-2",
        risk_evidence_ok=True,
        stability_evidence_ok=True,
        consistency_evidence_ok=True,
        evidence_ref="results/model2/runtime/model2_live_dashboard_latest.json",
    )

    assert result.go is True
    assert result.decision == "GO"
    assert result.evidence_sufficient is True
    assert result.reasons == []


def test_m2_020_11_healthcheck_embeds_promotion_gate_decision(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    output_dir = tmp_path / "out"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dashboard = runtime_dir / f"model2_live_dashboard_{run_id}.json"
    _write_live_dashboard(
        dashboard,
        timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
    )

    summary = run_live_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=output_dir,
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    gate = summary.get("promotion_gate")
    assert isinstance(gate, dict)
    assert gate.get("decision") == "GO"
    assert gate.get("evidence_sufficient") is True


def test_m2_020_11_healthcheck_forces_no_go_when_dashboard_is_stale(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    output_dir = tmp_path / "out"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dashboard = runtime_dir / f"model2_live_dashboard_{run_id}.json"
    stale_time = datetime.now(timezone.utc) - timedelta(hours=6)
    _write_live_dashboard(
        dashboard,
        timestamp_ms=int(stale_time.timestamp() * 1000),
    )

    summary = run_live_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=output_dir,
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    gate = summary.get("promotion_gate")
    assert isinstance(gate, dict)
    assert gate.get("decision") == "NO_GO"
    assert gate.get("evidence_sufficient") is False
    reasons = gate.get("reasons")
    assert isinstance(reasons, list)
    assert any("stability_evidence_missing" in reason for reason in reasons)
