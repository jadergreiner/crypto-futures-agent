import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.model2.healthcheck_daily_schedule as healthcheck


def _write_schedule_report(
    runtime_dir: Path,
    *,
    status: str,
    timestamp_ms: int,
) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = runtime_dir / f"model2_daily_schedule_{run_id}.json"
    payload = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": timestamp_ms,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_healthcheck_is_ok_for_recent_report_with_status_ok(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "results" / "model2" / "runtime"
    now_ms = healthcheck._utc_now_ms()
    _write_schedule_report(runtime_dir, status="ok", timestamp_ms=now_ms)

    summary = healthcheck.run_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        timezone_name="UTC",
        max_age_hours=30,
        require_today=True,
        expected_statuses=["ok"],
        alert_command=None,
    )

    assert summary["status"] == "ok"
    assert summary["violations"] == []
    assert Path(summary["output_file"]).exists()


def test_healthcheck_alerts_when_no_schedule_report_exists(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "results" / "model2" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    summary = healthcheck.run_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        timezone_name="UTC",
        max_age_hours=30,
        require_today=True,
        expected_statuses=["ok"],
        alert_command=None,
    )

    assert summary["status"] == "alert"
    assert summary["violations"][0]["code"] == "missing_schedule_report"


def test_healthcheck_alerts_when_latest_status_is_not_ok(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "results" / "model2" / "runtime"
    now_ms = healthcheck._utc_now_ms()
    _write_schedule_report(runtime_dir, status="partial", timestamp_ms=now_ms)

    summary = healthcheck.run_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        timezone_name="UTC",
        max_age_hours=30,
        require_today=True,
        expected_statuses=["ok"],
        alert_command=None,
    )

    assert summary["status"] == "alert"
    assert any(item["code"] == "unexpected_status" for item in summary["violations"])


def test_healthcheck_alerts_when_report_is_not_from_today(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "results" / "model2" / "runtime"
    yesterday = datetime.now(timezone.utc) - timedelta(days=1, hours=1)
    _write_schedule_report(runtime_dir, status="ok", timestamp_ms=int(yesterday.timestamp() * 1000))

    summary = healthcheck.run_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        timezone_name="UTC",
        max_age_hours=48,
        require_today=True,
        expected_statuses=["ok"],
        alert_command=None,
    )

    assert summary["status"] == "alert"
    assert any(item["code"] == "missing_today_execution" for item in summary["violations"])
