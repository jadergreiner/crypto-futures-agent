from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import scripts.model2.daily_pipeline as daily_pipeline
from data.database import DatabaseManager


def test_daily_pipeline_m5_with_real_db_fixture(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source_db = tmp_path / "db" / "crypto_agent.db"
    model2_db = tmp_path / "db" / "modelo2.db"
    legacy_db = tmp_path / "db" / "legacy.db"
    output_dir = tmp_path / "results"
    calls: list[tuple[str, dict[str, Any]]] = []

    # Fixture real de DB legado com schema completo (inclui ohlcv_m5).
    source_db.parent.mkdir(parents=True, exist_ok=True)
    DatabaseManager(str(source_db))

    def _sync_stage(**kwargs: Any) -> dict[str, Any]:
        calls.append(("sync_ohlcv", kwargs))
        db = DatabaseManager(str(kwargs["source_db_path"]))
        db.insert_ohlcv(
            "m5",
            [
                {
                    "timestamp": 1700000000000,
                    "symbol": "BTCUSDT",
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                    "volume": 123.0,
                    "quote_volume": 12361.5,
                    "trades_count": 50,
                }
            ],
        )
        return {"status": "ok", "stage": "sync_ohlcv"}

    def _fake_stage(name: str):  # type: ignore[no-untyped-def]
        def _runner(**kwargs: Any) -> dict[str, Any]:
            calls.append((name, kwargs))
            return {"status": "ok", "stage": name}

        return _runner

    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _sync_stage, raising=False)
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage("migrate"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage("scan"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage("track"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage("validate"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage("resolve"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage("bridge"), raising=False)
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage("persist_training_episodes"),
        raising=False,
    )
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage("train_entry_agents"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage("entry_rl_filter"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage("order_layer"), raising=False)
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage("export_signals"), raising=False)
    monkeypatch.setattr(
        daily_pipeline,
        "run_rl_signal_generation",
        _fake_stage("rl_signal_generation"),
        raising=False,
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage("ensemble_signal_generation"),
        raising=False,
    )
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_stage("export_dashboard"), raising=False)

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=source_db,
        model2_db_path=model2_db,
        legacy_db_path=legacy_db,
        symbols=["BTCUSDT"],
        timeframe="M5",
        scan_candles_limit=30,
        validation_candles_limit=30,
        resolution_candles_limit=30,
        limit=20,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=output_dir,
    )

    assert summary["status"] == "ok"
    assert summary["filters"]["timeframe"] == "M5"
    assert Path(str(summary["output_file"])).exists()

    for stage_name, kwargs in calls:
        if "timeframe" in kwargs:
            assert kwargs["timeframe"] == "M5", f"timeframe inesperado em {stage_name}"

    with sqlite3.connect(str(source_db)) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM ohlcv_m5 WHERE symbol = ?",
            ("BTCUSDT",),
        ).fetchone()
    assert row is not None
    assert int(row[0]) >= 1
