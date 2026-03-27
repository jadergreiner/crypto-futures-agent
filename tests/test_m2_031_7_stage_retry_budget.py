"""RED->GREEN suite for M2-031.7 controlled retry by stage."""

from __future__ import annotations

import json
from pathlib import Path


def test_executor_retries_transient_failure_and_succeeds(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    attempts = {"s1": 0}

    def _stage_transient(_: dict[str, object]) -> dict[str, object]:
        attempts["s1"] += 1
        if attempts["s1"] == 1:
            raise TimeoutError("exchange timeout")
        return {"decision": "OK"}

    stages = [("Backlog Development", _stage_transient)]
    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(
        item_id="M2-031.7",
        stages=stages,
        retry_budget_by_stage={"Backlog Development": 1},
    )

    assert result["status"] == "CONCLUIDO"
    assert attempts["s1"] == 2
    assert any("RETRY_TRANSITORIO 1/1" in line for line in result["progress"])


def test_executor_stops_when_transient_retry_budget_is_exhausted(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    attempts = {"s1": 0}

    def _stage_timeout(_: dict[str, object]) -> dict[str, object]:
        attempts["s1"] += 1
        raise TimeoutError("exchange timeout")

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(
        item_id="M2-031.7",
        stages=[("Backlog Development", _stage_timeout)],
        retry_budget_by_stage={"Backlog Development": 1},
    )

    assert result["status"] == "AGUARDANDO_CORRECAO"
    assert result["blocked_stage"] == "Backlog Development"
    assert attempts["s1"] == 2
    assert checkpoint_path.exists() is True


def test_executor_does_not_retry_on_devolvido_decision(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    attempts = {"s1": 0}

    def _stage_devolvido(_: dict[str, object]) -> dict[str, object]:
        attempts["s1"] += 1
        return {"decision": "DEVOLVIDO_PARA_REVISAO", "motivo": "guardrail ausente"}

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(
        item_id="M2-031.7",
        stages=[("Backlog Development", _stage_devolvido)],
        retry_budget_by_stage={"Backlog Development": 3},
    )

    assert result["status"] == "AGUARDANDO_CORRECAO"
    assert attempts["s1"] == 1


def test_executor_resume_skips_stage_already_completed(tmp_path: Path) -> None:
    from core.dev_cycle_executor import DevCycleExecutor

    checkpoint_path = tmp_path / "dev_cycle_checkpoint.json"
    checkpoint_payload = {
        "item_id": "M2-031.7",
        "next_stage_index": 0,
        "status": "AGUARDANDO_CORRECAO",
        "updated_at": "2026-03-27T21:00:00+00:00",
        "progress": [],
        "stage_outputs": {
            "Backlog Development": {
                "decision": "OK",
                "handoff": {},
                "motivo": "",
                "elapsed_ms": 10,
            }
        },
    }
    checkpoint_path.write_text(json.dumps(checkpoint_payload, ensure_ascii=True), encoding="utf-8")

    calls: list[str] = []

    def _stage1(_: dict[str, object]) -> dict[str, object]:
        calls.append("s1")
        return {"decision": "OK"}

    def _stage2(_: dict[str, object]) -> dict[str, object]:
        calls.append("s2")
        return {"decision": "OK"}

    executor = DevCycleExecutor(checkpoint_path=checkpoint_path, audit_log_path=None)
    result = executor.run(
        item_id="M2-031.7",
        stages=[
            ("Backlog Development", _stage1),
            ("Product Owner", _stage2),
        ],
        resume=True,
    )

    assert result["status"] == "CONCLUIDO"
    assert calls == ["s2"]
