import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from scripts.model2.operator_cycle_status import _build_symbol_report


def _create_db_with_decision(input_json: dict | None = None) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        "CREATE TABLE model_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "confidence REAL,"
        "input_json TEXT NOT NULL DEFAULT '{}',"
        "created_at TEXT"
        ")"
    )
    payload = json.dumps(input_json or {})
    conn.execute(
        "INSERT INTO model_decisions (symbol, action, confidence, input_json) VALUES (?,?,?,?)",
        ("BTCUSDT", "OPEN_LONG", 0.8, payload),
    )
    conn.commit()
    conn.close()
    return tmp.name


def _create_empty_db() -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return tmp.name


def test_status_line_reflects_true_origin_rl_model():
    db_path = _create_db_with_decision(input_json={"some": "data"})
    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="H4",
        db_path=db_path,
    )
    assert "source=RL_MODEL" in report


def test_status_line_reflects_fallback_contamination():
    db_path = _create_empty_db()
    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="H4",
        db_path=db_path,
    )
    assert "source=FALLBACK" in report


def test_status_line_includes_decision_and_source():
    db_path = _create_db_with_decision()
    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="H4",
        db_path=db_path,
    )
    assert "Decisao  :" in report and "source=" in report

