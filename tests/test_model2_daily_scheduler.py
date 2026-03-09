import json
from pathlib import Path

import scripts.model2.schedule_daily_pipeline as daily_scheduler


def test_scheduled_execution_runs_pipeline_once_and_releases_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    calls: list[dict[str, object]] = []

    def _fake_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        pipeline_output = tmp_path / "results" / "model2" / "runtime" / "model2_daily_pipeline_fake.json"
        pipeline_output.parent.mkdir(parents=True, exist_ok=True)
        pipeline_output.write_text("{}", encoding="utf-8")
        return {"status": "ok", "output_file": str(pipeline_output)}

    monkeypatch.setattr(daily_scheduler, "run_daily_pipeline", _fake_pipeline)

    lock_file = tmp_path / "results" / "model2" / "runtime" / "pipeline.lock"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    summary = daily_scheduler.run_scheduled_execution(
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
        output_dir=output_dir,
        lock_file=lock_file,
        lock_stale_seconds=3600,
        max_retries=2,
        retry_delay_seconds=1,
        retry_on_partial=False,
    )

    assert summary["status"] == "ok"
    assert len(summary["attempts"]) == 1
    assert len(calls) == 1
    assert not lock_file.exists()
    assert Path(summary["output_file"]).exists()


def test_scheduled_execution_skips_when_lock_is_active(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    called = {"value": False}

    def _fake_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        called["value"] = True
        return {"status": "ok"}

    monkeypatch.setattr(daily_scheduler, "run_daily_pipeline", _fake_pipeline)

    lock_file = tmp_path / "results" / "model2" / "runtime" / "pipeline.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(
        json.dumps({"pid": 999, "acquired_at_utc_ms": daily_scheduler._utc_now_ms()}),
        encoding="utf-8",
    )

    summary = daily_scheduler.run_scheduled_execution(
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
        output_dir=tmp_path / "results" / "model2" / "runtime",
        lock_file=lock_file,
        lock_stale_seconds=3600,
        max_retries=2,
        retry_delay_seconds=1,
        retry_on_partial=False,
    )

    assert summary["status"] == "skipped_locked"
    assert called["value"] is False
    assert lock_file.exists()


def test_scheduled_execution_retries_after_error_and_then_succeeds(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    responses = iter(
        [
            {"status": "error"},
            {"status": "ok", "output_file": str(tmp_path / "results" / "pipeline_ok.json")},
        ]
    )
    sleeps: list[int] = []

    def _fake_pipeline(**kwargs):  # type: ignore[no-untyped-def]
        return next(responses)

    monkeypatch.setattr(daily_scheduler, "run_daily_pipeline", _fake_pipeline)
    monkeypatch.setattr(daily_scheduler.time, "sleep", lambda seconds: sleeps.append(int(seconds)))

    summary = daily_scheduler.run_scheduled_execution(
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
        output_dir=tmp_path / "results" / "model2" / "runtime",
        lock_file=tmp_path / "results" / "model2" / "runtime" / "pipeline.lock",
        lock_stale_seconds=3600,
        max_retries=2,
        retry_delay_seconds=7,
        retry_on_partial=False,
    )

    assert summary["status"] == "ok"
    assert len(summary["attempts"]) == 2
    assert summary["attempts"][0]["result"] == "error"
    assert summary["attempts"][1]["result"] == "ok"
    assert sleeps == [7]


def test_scheduled_execution_removes_stale_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        daily_scheduler,
        "run_daily_pipeline",
        lambda **kwargs: {"status": "ok", "output_file": str(tmp_path / "results" / "pipeline_ok.json")},
    )

    lock_file = tmp_path / "results" / "model2" / "runtime" / "pipeline.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    stale_ms = daily_scheduler._utc_now_ms() - (10 * 60 * 1000)
    lock_file.write_text(
        json.dumps({"pid": 123, "acquired_at_utc_ms": stale_ms}),
        encoding="utf-8",
    )

    summary = daily_scheduler.run_scheduled_execution(
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
        output_dir=tmp_path / "results" / "model2" / "runtime",
        lock_file=lock_file,
        lock_stale_seconds=60,
        max_retries=0,
        retry_delay_seconds=1,
        retry_on_partial=False,
    )

    assert summary["status"] == "ok"
    assert summary["lock"]["stale_lock_removed"] is True
