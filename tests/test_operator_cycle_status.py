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
        "output_json TEXT NOT NULL DEFAULT '{}',"
        "input_json TEXT NOT NULL DEFAULT '{}',"
        "created_at TEXT"
        ")"
    )
    payload = json.dumps(input_json or {})
    output_payload = json.dumps({})
    conn.execute(
        "INSERT INTO model_decisions (symbol, action, confidence, output_json, input_json) VALUES (?,?,?,?,?)",
        ("BTCUSDT", "OPEN_LONG", 0.8, output_payload, payload),
    )
    conn.commit()
    conn.close()
    return tmp.name


def _create_db_with_custom_decision(
    *,
    action: str = "HOLD",
    confidence: float | None = 0.0,
    input_json: dict | None = None,
    output_json: dict | None = None,
) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        "CREATE TABLE model_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "symbol TEXT NOT NULL,"
        "action TEXT NOT NULL,"
        "confidence REAL,"
        "model_version TEXT,"
        "reason_code TEXT,"
        "decision_timestamp INTEGER,"
        "input_json TEXT NOT NULL DEFAULT '{}',"
        "output_json TEXT NOT NULL DEFAULT '{}',"
        "created_at TEXT"
        ")"
    )
    conn.execute(
        "INSERT INTO model_decisions (symbol, action, confidence, model_version, reason_code, decision_timestamp, input_json, output_json, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "BTCUSDT",
            action,
            confidence,
            "m2-inference-v1",
            "inference_hold_raw_confidence",
            1774823203270,
            json.dumps(input_json or {}),
            json.dumps(output_json or {}),
            "2026-04-01 09:26:49",
        ),
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
    assert "source=FALLBACK_STATUS_SEM_DECISION_TRACE" in report


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


def test_status_line_exibe_zero_porcento_quando_confianca_zero() -> None:
    db_path = _create_db_with_custom_decision(confidence=0.0)
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
    assert "confianca: 0%" in report
    assert "confianca: N/A" not in report


def test_status_line_exibe_na_quando_confianca_ausente() -> None:
    db_path = _create_db_with_custom_decision(confidence=None)
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
    assert "confianca: N/A" in report


def test_status_line_reflects_fallback_modelo_rl_quando_output_json_indica_rl_fallback() -> None:
    db_path = _create_db_with_custom_decision(
        confidence=0.7,
        output_json={"metadata": {"rl_fallback": True}},
    )
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
    assert "source=FALLBACK_MODELO_RL" in report

