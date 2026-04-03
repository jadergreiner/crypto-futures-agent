import json
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from scripts.model2.operator_cycle_status import (
    _build_symbol_report,
    _check_context_candles_stale_alarm,
    TimeframeCandleStatus,
)

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



# ---------------------------------------------------------------------------
# Testes para _check_context_candles_stale_alarm
# ---------------------------------------------------------------------------

def _brt_display_fmt(dt_utc: datetime) -> str:
    """Formata datetime UTC como string BRT no formato exibido pelo status."""
    from zoneinfo import ZoneInfo
    brt_tz = ZoneInfo("America/Sao_Paulo")
    return dt_utc.astimezone(brt_tz).strftime("%Y-%m-%d %H:%M:%S BRT")


def _make_tf_status(
    timeframe: str,
    age_seconds: float,
    now_utc: datetime,
) -> TimeframeCandleStatus:
    display_time = _brt_display_fmt(now_utc - timedelta(seconds=age_seconds))
    return TimeframeCandleStatus(
        timeframe=timeframe,
        display_time=display_time,
        scan_count=1,
        persisted_count=1,
        state="stale",
    )


def test_sem_alarme_quando_todos_frescos() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        _make_tf_status("D1", 23 * 3600, now),   # 23h < 48h
        _make_tf_status("H4", 7 * 3600, now),     # 7h < 8h
        _make_tf_status("H1", 1 * 3600, now),     # 1h < 2h
        _make_tf_status("M5", 60, now),            # M5 nao monitorado
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert result == "", f"esperado sem alarme, obteve: {result!r}"


def test_alarme_quando_d1_stale() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        _make_tf_status("D1", 49 * 3600, now),   # 49h > 48h
        _make_tf_status("H4", 7 * 3600, now),
        _make_tf_status("H1", 1 * 3600, now),
        _make_tf_status("M5", 60, now),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert "ALERTA-STALE" in result, f"alarme esperado para D1, obteve: {result!r}"
    assert "D1" in result


def test_alarme_quando_h4_stale() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        _make_tf_status("D1", 23 * 3600, now),
        _make_tf_status("H4", 9 * 3600, now),    # 9h > 8h
        _make_tf_status("H1", 1 * 3600, now),
        _make_tf_status("M5", 60, now),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert "ALERTA-STALE" in result, f"alarme esperado para H4, obteve: {result!r}"
    assert "H4" in result


def test_alarme_quando_h1_stale() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        _make_tf_status("D1", 23 * 3600, now),
        _make_tf_status("H4", 7 * 3600, now),
        _make_tf_status("H1", 3 * 3600, now),    # 3h > 2h
        _make_tf_status("M5", 60, now),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert "ALERTA-STALE" in result, f"alarme esperado para H1, obteve: {result!r}"
    assert "H1" in result


def test_alarme_multiplos_tfs_stale() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        _make_tf_status("D1", 50 * 3600, now),   # 50h > 48h
        _make_tf_status("H4", 10 * 3600, now),   # 10h > 8h
        _make_tf_status("H1", 3 * 3600, now),    # 3h > 2h
        _make_tf_status("M5", 60, now),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert "ALERTA-STALE" in result
    assert "D1" in result
    assert "H4" in result
    assert "H1" in result


def test_alarme_quando_display_time_ausente() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    tf_statuses = [
        TimeframeCandleStatus(
            timeframe="H1",
            display_time="N/A",
            scan_count=0,
            persisted_count=0,
            state="absent",
        ),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert "ALERTA-STALE" in result
    assert "H1" in result


def test_m5_nao_incluido_no_alarme() -> None:
    now = datetime(2026, 4, 3, 20, 0, 0, tzinfo=timezone.utc)
    # M5 muito antigo, mas nao deve acionar alarme (sem threshold definido)
    tf_statuses = [
        _make_tf_status("M5", 100 * 3600, now),
    ]
    result = _check_context_candles_stale_alarm(tf_statuses, now_utc=now)
    assert result == "", f"M5 nao deve acionar alarme, obteve: {result!r}"
