import json
from pathlib import Path

import pytest

import scripts.model2.daily_pipeline as daily_pipeline
from data.database import DatabaseManager


def _fake_stage(calls: list[tuple[str, dict[str, object]]], name: str):  # type: ignore[no-untyped-def]
    def _runner(**kwargs):  # type: ignore[no-untyped-def]
        calls.append((name, kwargs))
        return {"status": "ok", "stage_name": name}

    return _runner


def test_daily_pipeline_runs_all_stages_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"))
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage(calls, "scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage(calls, "persist_training_episodes"),
    )
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage(calls, "ensemble_signal_generation"),
    )
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_stage(calls, "export_dashboard"))
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_stage(calls, "daily_report"))

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="H4",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    assert [name for name, _ in calls] == [
        "sync_ohlcv",
        "migrate",
        "scan",
        "track",
        "validate",
        "resolve",
        "bridge",
        "persist_training_episodes",
        "flush_deferred_rewards",
        "train_entry_agents",
        "entry_rl_filter",
        "order_layer",
        "export_signals",
        "rl_signal_generation",
        "ensemble_signal_generation",
        "export_dashboard",
        "daily_report",
    ]
    assert calls[2][1]["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert calls[3][1]["symbol"] is None
    assert summary["status"] == "ok"
    assert summary["stage_errors"] == []
    assert "export_dashboard" in summary["stages"]

    output_file = Path(summary["output_file"])
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["filters"]["symbols"] == ["BTCUSDT", "ETHUSDT"]


def test_daily_pipeline_skips_dashboard_stage_on_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"))
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage(calls, "scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage(calls, "persist_training_episodes"),
    )
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage(calls, "ensemble_signal_generation"),
    )
    monkeypatch.setattr(
        daily_pipeline,
        "run_export_dashboard",
        lambda **_: (_ for _ in ()).throw(AssertionError("export_dashboard should be skipped")),
    )
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_stage(calls, "daily_report"))

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="H4",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=True,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    assert [name for name, _ in calls] == [
        "sync_ohlcv",
        "migrate",
        "scan",
        "track",
        "validate",
        "resolve",
        "bridge",
        "persist_training_episodes",
        "flush_deferred_rewards",
        "train_entry_agents",
        "entry_rl_filter",
        "order_layer",
        "export_signals",
        "rl_signal_generation",
        "ensemble_signal_generation",
        "daily_report",
    ]
    assert summary["status"] == "ok"
    assert summary["stages"]["export_dashboard"]["status"] == "skipped_dry_run"


def test_daily_pipeline_fails_fast_when_continue_on_error_is_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"))

    def _raise_scan_error(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(("scan", kwargs))
        raise RuntimeError("scan boom")

    monkeypatch.setattr(daily_pipeline, "run_scan", _raise_scan_error)
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage(calls, "persist_training_episodes"),
    )
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage(calls, "ensemble_signal_generation"),
    )
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_stage(calls, "export_dashboard"))
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_stage(calls, "daily_report"))

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="H4",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    assert [name for name, _ in calls] == ["sync_ohlcv", "migrate", "scan", "daily_report"]
    assert summary["status"] == "error"
    assert len(summary["stage_errors"]) == 1
    assert summary["stage_errors"][0]["stage"] == "scan"


def test_daily_pipeline_continues_after_error_when_flag_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"))

    def _raise_scan_error(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(("scan", kwargs))
        raise RuntimeError("scan boom")

    monkeypatch.setattr(daily_pipeline, "run_scan", _raise_scan_error)
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_persist_training_episodes",
        _fake_stage(calls, "persist_training_episodes"),
    )
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(
        daily_pipeline,
        "run_ensemble_signal_generation",
        _fake_stage(calls, "ensemble_signal_generation"),
    )
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_stage(calls, "export_dashboard"))
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_stage(calls, "daily_report"))

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="H4",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=True,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    assert [name for name, _ in calls] == [
        "sync_ohlcv",
        "migrate",
        "scan",
        "track",
        "validate",
        "resolve",
        "bridge",
        "persist_training_episodes",
        "flush_deferred_rewards",
        "train_entry_agents",
        "entry_rl_filter",
        "order_layer",
        "export_signals",
        "rl_signal_generation",
        "ensemble_signal_generation",
        "export_dashboard",
        "daily_report",
    ]
    assert summary["status"] == "partial"
    assert len(summary["stage_errors"]) == 1
    assert summary["stage_errors"][0]["stage"] == "scan"


def test_daily_pipeline_benchmark_records_baseline_and_flags_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage_elapsed_first = {
        "sync_ohlcv": 40,
        "migrate": 30,
        "scan": 100,
        "track": 60,
        "validate": 80,
        "resolve": 50,
        "bridge": 70,
        "persist_training_episodes": 20,
        "flush_deferred_rewards": 20,
        "train_entry_agents": 20,
        "entry_rl_filter": 20,
        "order_layer": 90,
        "export_signals": 20,
        "rl_signal_generation": 20,
        "ensemble_signal_generation": 20,
        "export_dashboard": 20,
        "daily_report": 20,
    }
    stage_elapsed_second = dict(stage_elapsed_first)
    stage_elapsed_second["scan"] = 250

    state = {"run": 0}

    def _fake_run_stage(*, stage_name, stage_callable, stage_kwargs):  # type: ignore[no-untyped-def]
        del stage_callable
        del stage_kwargs
        if state["run"] == 0:
            elapsed = stage_elapsed_first[stage_name]
        else:
            elapsed = stage_elapsed_second[stage_name]
        return {"status": "ok", "stage_elapsed_ms": elapsed}, None

    monkeypatch.setattr(daily_pipeline, "_run_stage", _fake_run_stage)

    first = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="M5",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    first_benchmark = first["stages"]["performance_benchmark"]
    assert first_benchmark["status"] == "ok"
    assert first_benchmark["stages"]["scan"]["baseline_created"] is True
    assert first_benchmark["stages"]["scan"]["baseline_p95_ms"] == 100.0
    assert first_benchmark["has_regression_alerts"] is False

    state["run"] = 1
    second = daily_pipeline.run_daily_pipeline(
        source_db_path=tmp_path / "db" / "source.db",
        model2_db_path=tmp_path / "db" / "modelo2.db",
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["BTCUSDT"],
        timeframe="M5",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    second_benchmark = second["stages"]["performance_benchmark"]
    assert second_benchmark["status"] == "ok"
    assert second_benchmark["stages"]["scan"]["baseline_created"] is False
    assert second_benchmark["stages"]["scan"]["baseline_p95_ms"] == 100.0
    assert second_benchmark["stages"]["scan"]["has_regression_alert"] is True
    assert second_benchmark["has_regression_alerts"] is True
    assert any(
        alert.get("benchmark_stage") == "scan"
        for alert in second_benchmark["alerts"]
    )
    assert second_benchmark["stages"]["signal_bridge"]["sample_stage"] == "bridge"


def test_daily_pipeline_stage_0_sincroniza_source_e_model2_quando_dbs_diferem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    source_db = tmp_path / "db" / "source.db"
    model2_db = tmp_path / "db" / "modelo2.db"

    monkeypatch.setattr(daily_pipeline, "sync_ohlcv_from_binance", _fake_stage(calls, "sync_ohlcv"))
    monkeypatch.setattr(daily_pipeline, "run_up", _fake_stage(calls, "migrate"))
    monkeypatch.setattr(daily_pipeline, "run_scan", _fake_stage(calls, "scan"))
    monkeypatch.setattr(daily_pipeline, "run_tracking", _fake_stage(calls, "track"))
    monkeypatch.setattr(daily_pipeline, "run_validation", _fake_stage(calls, "validate"))
    monkeypatch.setattr(daily_pipeline, "run_resolution", _fake_stage(calls, "resolve"))
    monkeypatch.setattr(daily_pipeline, "run_bridge", _fake_stage(calls, "bridge"))
    monkeypatch.setattr(daily_pipeline, "run_persist_training_episodes", _fake_stage(calls, "persist_training_episodes"))
    monkeypatch.setattr(daily_pipeline, "flush_deferred_rewards", _fake_stage(calls, "flush_deferred_rewards"))
    monkeypatch.setattr(daily_pipeline, "run_train_entry_agents", _fake_stage(calls, "train_entry_agents"))
    monkeypatch.setattr(daily_pipeline, "run_entry_rl_filter", _fake_stage(calls, "entry_rl_filter"))
    monkeypatch.setattr(daily_pipeline, "run_order_layer", _fake_stage(calls, "order_layer"))
    monkeypatch.setattr(daily_pipeline, "run_export_signals", _fake_stage(calls, "export_signals"))
    monkeypatch.setattr(daily_pipeline, "run_rl_signal_generation", _fake_stage(calls, "rl_signal_generation"))
    monkeypatch.setattr(daily_pipeline, "run_ensemble_signal_generation", _fake_stage(calls, "ensemble_signal_generation"))
    monkeypatch.setattr(daily_pipeline, "run_export_dashboard", _fake_stage(calls, "export_dashboard"))
    monkeypatch.setattr(daily_pipeline, "run_daily_report", _fake_stage(calls, "daily_report"))

    def _bootstrap_fake(**_: object) -> list[dict[str, object]]:
        rows = [
            {
                "symbol": "ALGOUSDT",
                "timeframe": "D1",
                "timestamp": 1743465600000,
                "open": 0.5,
                "high": 0.52,
                "low": 0.49,
                "close": 0.51,
                "volume": 1000.0,
                "quote_volume": 510.0,
                "trades_count": 10,
            }
        ]
        DatabaseManager(str(model2_db)).insert_ohlcv(
            "d1",
            [{key: value for key, value in row.items() if key != "timeframe"} for row in rows],
        )
        return rows

    monkeypatch.setattr(daily_pipeline, "run_bootstrap_algousdt", _bootstrap_fake)

    summary = daily_pipeline.run_daily_pipeline(
        source_db_path=source_db,
        model2_db_path=model2_db,
        legacy_db_path=tmp_path / "db" / "legacy.db",
        symbols=["ALGOUSDT"],
        timeframe="D1",
        scan_candles_limit=120,
        validation_candles_limit=240,
        resolution_candles_limit=240,
        limit=200,
        dry_run=False,
        continue_on_error=False,
        retention_days=30,
        output_dir=tmp_path / "results",
    )

    source_rows = DatabaseManager(str(source_db)).get_ohlcv("d1", "ALGOUSDT")
    model2_rows = DatabaseManager(str(model2_db)).get_ohlcv("d1", "ALGOUSDT")

    assert len(source_rows) == 1
    assert len(model2_rows) == 1
    assert summary["stages"]["bootstrap_stage_0"]["status"] == "ok"
    assert summary["stages"]["bootstrap_stage_0"]["source_db_synced"] is True
    assert [name for name, _ in calls][:4] == [
        "sync_ohlcv",
        "migrate",
        "scan",
        "track",
    ]
