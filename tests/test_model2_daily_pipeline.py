import json
from pathlib import Path

import pytest

import scripts.model2.daily_pipeline as daily_pipeline


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
