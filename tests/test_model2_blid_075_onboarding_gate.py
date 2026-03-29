"""Suite BLID-075: gate operacional de onboarding por simbolo."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def _create_model_decisions_table(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_timestamp INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL,
                created_at INTEGER
            )
            """
        )
        conn.commit()


def _insert_decisions(db_path: Path, *, symbol: str, total: int) -> None:
    with sqlite3.connect(db_path) as conn:
        rows = [
            (1774800000000 + idx, symbol, "OPEN_SHORT", 0.75, 1774800000000 + idx)
            for idx in range(total)
        ]
        conn.executemany(
            """
            INSERT INTO model_decisions (
                decision_timestamp, symbol, action, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def test_gate_returns_not_ready_when_validated_signals_below_minimum(tmp_path: Path) -> None:
    from core.model2.onboarding_gate import evaluate_symbol_onboarding_gate

    db_path = tmp_path / "modelo2.db"
    _create_model_decisions_table(db_path)
    _insert_decisions(db_path, symbol="FLUXUSDT", total=19)

    pipeline_file = tmp_path / "pipeline.json"
    training_file = tmp_path / "training.json"
    _write_json(
        pipeline_file,
        {
            "status": "ok",
            "stage_errors": [],
            "stages": {
                "scan": {},
                "track": {},
                "validate": {},
                "resolve": {},
                "bridge": {},
            },
        },
    )
    _write_json(
        training_file,
        {
            "summary_stats": {"trained": 1},
            "results": {"FLUXUSDT": {"status": "trained", "episodes_used": 1000}},
        },
    )

    result = evaluate_symbol_onboarding_gate(
        model2_db_path=db_path,
        symbol="FLUXUSDT",
        min_validated_signals=20,
        pipeline_summary_path=pipeline_file,
        training_summary_path=training_file,
    )

    assert result.ready is False
    assert result.validated_signals == 19
    assert "validated_signals_below_minimum" in result.reasons


def test_gate_returns_not_ready_when_pipeline_missing_required_stage(tmp_path: Path) -> None:
    from core.model2.onboarding_gate import evaluate_symbol_onboarding_gate

    db_path = tmp_path / "modelo2.db"
    _create_model_decisions_table(db_path)
    _insert_decisions(db_path, symbol="FLUXUSDT", total=50)

    pipeline_file = tmp_path / "pipeline.json"
    training_file = tmp_path / "training.json"
    _write_json(
        pipeline_file,
        {
            "status": "ok",
            "stage_errors": [],
            "stages": {
                "scan": {},
                "track": {},
                "validate": {},
                "resolve": {},
            },
        },
    )
    _write_json(
        training_file,
        {
            "summary_stats": {"trained": 1},
            "results": {"FLUXUSDT": {"status": "trained", "episodes_used": 1000}},
        },
    )

    result = evaluate_symbol_onboarding_gate(
        model2_db_path=db_path,
        symbol="FLUXUSDT",
        min_validated_signals=20,
        pipeline_summary_path=pipeline_file,
        training_summary_path=training_file,
    )

    assert result.ready is False
    assert "pipeline_not_ok" in result.reasons


def test_gate_returns_ready_when_all_operational_evidence_is_present(tmp_path: Path) -> None:
    from core.model2.onboarding_gate import evaluate_symbol_onboarding_gate

    db_path = tmp_path / "modelo2.db"
    _create_model_decisions_table(db_path)
    _insert_decisions(db_path, symbol="FLUXUSDT", total=120)

    pipeline_file = tmp_path / "pipeline.json"
    training_file = tmp_path / "training.json"
    _write_json(
        pipeline_file,
        {
            "status": "ok",
            "stage_errors": [],
            "stages": {
                "scan": {},
                "track": {},
                "validate": {},
                "resolve": {},
                "bridge": {},
            },
        },
    )
    _write_json(
        training_file,
        {
            "summary_stats": {"trained": 1},
            "results": {"FLUXUSDT": {"status": "trained", "episodes_used": 1000}},
        },
    )

    result = evaluate_symbol_onboarding_gate(
        model2_db_path=db_path,
        symbol="FLUXUSDT",
        min_validated_signals=20,
        pipeline_summary_path=pipeline_file,
        training_summary_path=training_file,
    )

    assert result.ready is True
    assert result.validated_signals == 120
    assert result.pipeline_ok is True
    assert result.training_ok is True
    assert result.reasons == ()
