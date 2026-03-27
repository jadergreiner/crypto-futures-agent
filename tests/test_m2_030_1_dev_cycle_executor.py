"""RED suite for M2-030.1 - unified dev-cycle executor with audit trail."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_executor_runs_all_stages_in_sequence(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    audit_log_path = tmp_path / "dev_cycle_audit.jsonl"
    calls: list[str] = []

    def _stage(name: str):
        def _run(context: dict[str, object]) -> dict[str, object]:
            calls.append(name)
            return {"decision": "OK", "handoff": f"{name}-done"}

        return _run

    stages = [
        ("Backlog Development", _stage("s1")),
        ("Product Owner", _stage("s2")),
        ("Solution Architect", _stage("s3")),
        ("QA-TDD", _stage("s4")),
        ("Software Engineer", _stage("s5")),
        ("Tech Lead", _stage("s6")),
        ("Doc Advocate", _stage("s7")),
        ("Project Manager", _stage("s8")),
    ]

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=audit_log_path)
    result = executor.run(item_id="M2-030.1", stages=stages)

    assert result["status"] == "CONCLUIDO"
    assert calls == ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
    assert checkpoint_path.exists() is False
    assert result["progress"][0] == "[STAGE 1/8] Backlog Development - iniciando..."
    assert result["progress"][-1] == "[STAGE 8/8] Project Manager - CONCLUIDO"


def test_executor_stops_and_persists_checkpoint_on_devolvido(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"

    def _ok(_: dict[str, object]) -> dict[str, object]:
        return {"decision": "OK"}

    def _devolvido(_: dict[str, object]) -> dict[str, object]:
        return {"decision": "DEVOLVIDO_PARA_REVISAO", "motivo": "guardrail ausente"}

    stages = [
        ("Backlog Development", _ok),
        ("Product Owner", _ok),
        ("Solution Architect", _devolvido),
        ("QA-TDD", _ok),
        ("Software Engineer", _ok),
        ("Tech Lead", _ok),
        ("Doc Advocate", _ok),
        ("Project Manager", _ok),
    ]

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(item_id="M2-030.1", stages=stages)

    assert result["status"] == "AGUARDANDO_CORRECAO"
    assert result["blocked_stage"] == "Solution Architect"
    assert checkpoint_path.exists() is True

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["next_stage_index"] == 2
    assert checkpoint["status"] == "AGUARDANDO_CORRECAO"


def test_executor_resume_restarts_from_failed_stage(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    calls: list[str] = []

    def _ok(name: str):
        def _run(_: dict[str, object]) -> dict[str, object]:
            calls.append(name)
            return {"decision": "OK"}

        return _run

    def _devolvido(_: dict[str, object]) -> dict[str, object]:
        calls.append("s3-block")
        return {"decision": "DEVOLVIDO_PARA_REVISAO", "motivo": "corrigir handoff"}

    stages_first = [
        ("Backlog Development", _ok("s1")),
        ("Product Owner", _ok("s2")),
        ("Solution Architect", _devolvido),
        ("QA-TDD", _ok("s4")),
        ("Software Engineer", _ok("s5")),
        ("Tech Lead", _ok("s6")),
        ("Doc Advocate", _ok("s7")),
        ("Project Manager", _ok("s8")),
    ]
    stages_resume = [
        ("Backlog Development", _ok("s1-resume")),
        ("Product Owner", _ok("s2-resume")),
        ("Solution Architect", _ok("s3-resume")),
        ("QA-TDD", _ok("s4-resume")),
        ("Software Engineer", _ok("s5-resume")),
        ("Tech Lead", _ok("s6-resume")),
        ("Doc Advocate", _ok("s7-resume")),
        ("Project Manager", _ok("s8-resume")),
    ]

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    blocked = executor.run(item_id="M2-030.1", stages=stages_first)
    assert blocked["status"] == "AGUARDANDO_CORRECAO"

    resumed = executor.run(item_id="M2-030.1", stages=stages_resume, resume=True)
    assert resumed["status"] == "CONCLUIDO"
    assert calls == [
        "s1",
        "s2",
        "s3-block",
        "s3-resume",
        "s4-resume",
        "s5-resume",
        "s6-resume",
        "s7-resume",
        "s8-resume",
    ]
    assert checkpoint_path.exists() is False


def test_executor_records_audit_events_per_stage(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    audit_log_path = tmp_path / "dev_cycle_audit.jsonl"

    def _ok(_: dict[str, object]) -> dict[str, object]:
        return {"decision": "OK"}

    stages = [
        ("Backlog Development", _ok),
        ("Product Owner", _ok),
        ("Solution Architect", _ok),
        ("QA-TDD", _ok),
        ("Software Engineer", _ok),
        ("Tech Lead", _ok),
        ("Doc Advocate", _ok),
        ("Project Manager", _ok),
    ]

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=audit_log_path)
    executor.run(item_id="M2-030.1", stages=stages)

    lines = audit_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 16
    first = json.loads(lines[0])
    last = json.loads(lines[-1])
    assert first["item_id"] == "M2-030.1"
    assert first["event"] == "stage_started"
    assert last["event"] == "stage_completed"
    assert last["stage"] == "Project Manager"


def test_executor_resume_without_checkpoint_fails_safe(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "nao_existe.json"
    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)

    with pytest.raises(ValueError, match="checkpoint_inexistente"):
        executor.run(item_id="M2-030.1", stages=[], resume=True)
