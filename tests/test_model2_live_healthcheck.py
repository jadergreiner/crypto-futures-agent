import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.model2.healthcheck_live_execution import run_live_healthcheck


def _write_live_dashboard(runtime_dir: Path, *, filename: str, payload: dict) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    target = runtime_dir / filename
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return target


def test_run_live_healthcheck_alerts_on_unprotected_positions(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "results" / "model2" / "runtime"
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    dashboard_path = _write_live_dashboard(
        runtime_dir,
        filename="model2_live_dashboard_20260309T000000Z.json",
        payload={
            "status": "ok",
            "timestamp_utc_ms": now_ms,
            "unprotected_filled_count": 1,
            "stale_entry_sent_count": 0,
            "open_position_mismatches_count": 0,
        },
    )

    summary = run_live_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    assert summary["status"] == "alert"
    assert summary["latest_live_dashboard_file"] == str(dashboard_path)
    assert summary["violations"][0]["code"] == "unprotected_positions"
    assert Path(summary["output_file"]).exists()
