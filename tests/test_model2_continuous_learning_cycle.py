from __future__ import annotations

import sqlite3
from pathlib import Path

from core.model2.model_degradation_monitor import ModelDegradationThresholds
from scripts.model2.continuous_learning_cycle import (
    _build_drift_report_for_symbol,
    _decision_probe_for_symbol,
    run_continuous_learning_cycle_once,
)


def _prepare_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS technical_signals (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                timeframe TEXT,
                status TEXT,
                signal_side TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                signal_timestamp INTEGER,
                payload_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS training_episodes (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                timeframe TEXT,
                label TEXT,
                created_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_decisions (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                confidence REAL,
                decision_timestamp INTEGER
            )
            """
        )
        conn.commit()


def test_decision_probe_skips_when_no_signal(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    _prepare_db(db_path)

    result = _decision_probe_for_symbol(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        model_first=True,
    )

    assert result["status"] == "skipped_no_signal"


def test_drift_report_marks_degraded_when_confidence_and_hit_rate_low(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    _prepare_db(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            "INSERT INTO training_episodes(symbol, timeframe, label, created_at) VALUES (?, ?, ?, ?)",
            [
                ("BTCUSDT", "H4", "loss", 1000),
                ("BTCUSDT", "H4", "loss", 1001),
                ("BTCUSDT", "H4", "loss", 1002),
                ("BTCUSDT", "H4", "loss", 1003),
            ],
        )
        conn.executemany(
            "INSERT INTO model_decisions(symbol, confidence, decision_timestamp) VALUES (?, ?, ?)",
            [
                ("BTCUSDT", 0.20, 1100),
                ("BTCUSDT", 0.22, 1101),
                ("BTCUSDT", 0.21, 1102),
                ("BTCUSDT", 0.19, 1103),
            ],
        )
        conn.commit()

    with sqlite3.connect(str(db_path)) as conn:
        report = _build_drift_report_for_symbol(
            conn=conn,
            symbol="BTCUSDT",
            timeframe="H4",
            thresholds=ModelDegradationThresholds(
                min_avg_confidence=0.45,
                min_hit_rate=0.40,
                min_hit_rate_delta=-0.10,
                evaluation_window=10,
                min_samples=3,
            ),
        )

    assert report["symbol"] == "BTCUSDT"
    assert report["is_degraded"] is True
    assert report["trigger_reason"] in {"confidence_below_threshold", "hit_rate_below_threshold", "hit_rate_regression"}


def test_continuous_cycle_runs_decision_and_drift_without_collection_retrain(tmp_path: Path) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    source_db = tmp_path / "db" / "crypto_agent.db"
    source_db.parent.mkdir(parents=True, exist_ok=True)
    source_db.write_text("", encoding="utf-8")
    _prepare_db(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO technical_signals(
                id, symbol, timeframe, status, signal_side, entry_price,
                stop_loss, take_profit, signal_timestamp, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "BTCUSDT",
                "H4",
                "CREATED",
                "SHORT",
                100.0,
                110.0,
                95.0,
                1_700_000_000_000,
                "{}",
            ),
        )
        conn.commit()

    summary = run_continuous_learning_cycle_once(
        source_db_path=source_db,
        model2_db_path=db_path,
        symbols=["BTCUSDT"],
        timeframe="H4",
        output_dir=tmp_path / "results",
        enable_collection=False,
        enable_persist=False,
        enable_retrain=False,
        enable_decision_probe=True,
        enable_drift_report=True,
    )

    assert summary["status"] in {"ok", "partial"}
    assert "BTCUSDT" in summary["decisions"]
    assert "BTCUSDT" in summary["drift_report"]
    assert Path(summary["output_file"]).exists()
