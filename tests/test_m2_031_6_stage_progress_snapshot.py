"""RED->GREEN suite for M2-031.6 stage progress snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.dev_cycle_package_planner import (
    append_stage_progress_snapshot,
    build_stage_progress_snapshot,
)


def test_build_stage_progress_snapshot_normalizes_main_fields() -> None:
    snapshot = build_stage_progress_snapshot(
        item_id="  M2-031.6  ",
        stage=" 6.TECH-LEAD ",
        status=" concluido ",
        decision=" aprovado ",
        note="  reproduzido localmente  ",
    )

    assert snapshot.item_id == "M2-031.6"
    assert snapshot.stage == "6.tech-lead"
    assert snapshot.status == "CONCLUIDO"
    assert snapshot.decision == "APROVADO"
    assert snapshot.note == "reproduzido localmente"
    assert snapshot.updated_at


def test_build_stage_progress_snapshot_rejects_invalid_required_fields() -> None:
    with pytest.raises(ValueError, match="item_id_invalido"):
        build_stage_progress_snapshot(item_id=" ", stage="5.software-engineer", status="ok", decision="ok")

    with pytest.raises(ValueError, match="stage_invalido"):
        build_stage_progress_snapshot(item_id="M2-031.6", stage=" ", status="ok", decision="ok")

    with pytest.raises(ValueError, match="status_invalido"):
        build_stage_progress_snapshot(item_id="M2-031.6", stage="5.software-engineer", status=" ", decision="ok")

    with pytest.raises(ValueError, match="decision_invalida"):
        build_stage_progress_snapshot(item_id="M2-031.6", stage="5.software-engineer", status="ok", decision=" ")


def test_append_stage_progress_snapshot_writes_jsonl_row(tmp_path: Path) -> None:
    output = tmp_path / "runtime" / "stage_progress.jsonl"
    snapshot = build_stage_progress_snapshot(
        item_id="M2-031.6",
        stage="5.software-engineer",
        status="concluido",
        decision="ok",
        note="green concluido",
    )

    append_stage_progress_snapshot(output_path=output, snapshot=snapshot)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["item_id"] == "M2-031.6"
    assert row["stage"] == "5.software-engineer"
    assert row["status"] == "CONCLUIDO"
    assert row["decision"] == "OK"
    assert row["note"] == "green concluido"
    assert row["updated_at"]


def test_append_stage_progress_snapshot_appends_without_overwriting(tmp_path: Path) -> None:
    output = tmp_path / "runtime" / "stage_progress.jsonl"

    first = build_stage_progress_snapshot(
        item_id="M2-031.6",
        stage="4.qa-tdd",
        status="concluido",
        decision="ok",
    )
    second = build_stage_progress_snapshot(
        item_id="M2-031.6",
        stage="5.software-engineer",
        status="concluido",
        decision="ok",
    )

    append_stage_progress_snapshot(output_path=output, snapshot=first)
    append_stage_progress_snapshot(output_path=output, snapshot=second)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    row1 = json.loads(lines[0])
    row2 = json.loads(lines[1])
    assert row1["stage"] == "4.qa-tdd"
    assert row2["stage"] == "5.software-engineer"
