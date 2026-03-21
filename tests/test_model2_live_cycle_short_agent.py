from pathlib import Path

import scripts.model2.live_cycle_short_agent as short_cycle


def test_short_agent_cycle_runs_all_stages_in_order(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    def _sync(**kwargs):  # type: ignore[no-untyped-def]
        timeframe = str(kwargs.get("timeframe"))
        calls.append("sync_h4" if timeframe == "H4" else "sync_m5")
        return {"status": "ok", "timeframe": timeframe}

    def _pipeline(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("daily_pipeline")
        return {"status": "ok"}

    def _live(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("live_cycle")
        return {"status": "ok", "execute": {"staged": [], "processed_ready": []}}

    def _persist(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("persist_training")
        return {"status": "ok", "episodes_inserted": 0}

    def _health(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("healthcheck")
        return {"status": "ok", "violations": []}

    monkeypatch.setattr(short_cycle, "run_sync_market_context", _sync)
    monkeypatch.setattr(short_cycle, "run_daily_pipeline", _pipeline)
    monkeypatch.setattr(short_cycle, "run_live_cycle", _live)
    monkeypatch.setattr(short_cycle, "run_persist_training_episodes", _persist)
    monkeypatch.setattr(short_cycle, "run_live_healthcheck", _health)

    summary = short_cycle.run_short_agent_cycle(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "model2_short.db",
        output_dir=tmp_path / "runtime",
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="H4",
        execution_mode="live",
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        funding_rate_max_for_short=0.0005,
        leverage=3,
        limit=200,
        sync_h4_candles_limit=4,
        sync_m5_candles_limit=4,
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        retention_days=30,
        continue_on_error=True,
        include_persist_training=True,
        include_healthcheck=True,
        max_health_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
    )

    assert calls == [
        "sync_h4",
        "sync_m5",
        "daily_pipeline",
        "live_cycle",
        "persist_training",
        "healthcheck",
    ]
    assert summary["status"] == "ok"
    assert summary["stage_errors"] == []
    assert Path(summary["output_file"]).exists()


def test_short_agent_cycle_marks_partial_and_continues_on_stage_error(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    def _sync(**kwargs):  # type: ignore[no-untyped-def]
        timeframe = str(kwargs.get("timeframe"))
        calls.append("sync_h4" if timeframe == "H4" else "sync_m5")
        return {"status": "ok"}

    def _pipeline_error(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("daily_pipeline")
        raise RuntimeError("pipeline boom")

    def _live(**kwargs):  # type: ignore[no-untyped-def]
        calls.append("live_cycle")
        return {"status": "ok"}

    monkeypatch.setattr(short_cycle, "run_sync_market_context", _sync)
    monkeypatch.setattr(short_cycle, "run_daily_pipeline", _pipeline_error)
    monkeypatch.setattr(short_cycle, "run_live_cycle", _live)

    summary = short_cycle.run_short_agent_cycle(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "model2_short.db",
        output_dir=tmp_path / "runtime",
        symbols=["BTCUSDT"],
        timeframe="H4",
        execution_mode="live",
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        funding_rate_max_for_short=0.0005,
        leverage=3,
        limit=200,
        sync_h4_candles_limit=4,
        sync_m5_candles_limit=4,
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        retention_days=30,
        continue_on_error=True,
        include_persist_training=False,
        include_healthcheck=False,
        max_health_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
    )

    assert calls == ["sync_h4", "sync_m5", "daily_pipeline", "live_cycle"]
    assert summary["status"] == "partial"
    assert len(summary["stage_errors"]) == 1
    assert summary["stage_errors"][0]["stage"] == "daily_pipeline"
    assert Path(summary["output_file"]).exists()
