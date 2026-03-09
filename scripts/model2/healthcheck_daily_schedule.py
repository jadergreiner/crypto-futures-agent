"""Healthcheck for Model 2.0 scheduled daily pipeline runs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _load_latest_schedule_report(runtime_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    files = sorted(runtime_dir.glob("model2_daily_schedule_*.json"), key=lambda item: item.stat().st_mtime)
    if not files:
        return None, None

    latest = files[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        payload = None
    if isinstance(payload, dict):
        return latest, payload
    return latest, None


def _extract_report_timestamp_ms(report_payload: dict[str, Any], report_path: Path) -> int:
    timestamp = report_payload.get("timestamp_utc_ms")
    try:
        if timestamp is not None:
            return int(timestamp)
    except (TypeError, ValueError):
        pass
    return int(report_path.stat().st_mtime * 1000)


def _run_alert_command(command: str, summary: dict[str, Any]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return {
            "command": command,
            "status": "error",
            "error": str(exc),
        }

    return {
        "command": command,
        "status": "ok" if completed.returncode == 0 else "error",
        "return_code": int(completed.returncode),
        "stdout": completed.stdout[-500:] if completed.stdout else "",
        "stderr": completed.stderr[-500:] if completed.stderr else "",
        "triggered_by": summary.get("status"),
    }


def run_healthcheck(
    *,
    runtime_dir: str | Path,
    output_dir: str | Path,
    timezone_name: str,
    max_age_hours: int,
    require_today: bool,
    expected_statuses: list[str],
    alert_command: str | None,
) -> dict[str, Any]:
    resolved_runtime_dir = _resolve_repo_path(runtime_dir)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    latest_path, latest_payload = _load_latest_schedule_report(resolved_runtime_dir)
    violations: list[dict[str, Any]] = []
    latest_status: str | None = None
    latest_timestamp_ms: int | None = None

    now_ms = _utc_now_ms()
    now_tz = datetime.now(ZoneInfo(timezone_name))
    expected = [item.strip() for item in expected_statuses if item and item.strip()]
    if not expected:
        expected = ["ok"]

    if latest_path is None:
        violations.append(
            {
                "code": "missing_schedule_report",
                "message": "No model2_daily_schedule_*.json report found in runtime directory.",
            }
        )
    elif latest_payload is None:
        violations.append(
            {
                "code": "invalid_schedule_report",
                "message": f"Latest schedule report is not valid JSON: {latest_path}",
            }
        )
    else:
        latest_status = str(latest_payload.get("status") or "")
        latest_timestamp_ms = _extract_report_timestamp_ms(latest_payload, latest_path)
        age_ms = max(0, now_ms - latest_timestamp_ms)
        age_hours = age_ms / 3_600_000

        if latest_status not in expected:
            violations.append(
                {
                    "code": "unexpected_status",
                    "message": f"Latest schedule status '{latest_status}' is outside expected {expected}.",
                    "latest_status": latest_status,
                }
            )

        if age_hours > float(max_age_hours):
            violations.append(
                {
                    "code": "stale_report",
                    "message": (
                        f"Latest schedule report age {age_hours:.2f}h exceeds max_age_hours={max_age_hours}."
                    ),
                    "age_hours": round(age_hours, 2),
                }
            )

        if require_today:
            latest_dt = datetime.fromtimestamp(latest_timestamp_ms / 1000, tz=timezone.utc).astimezone(
                ZoneInfo(timezone_name)
            )
            if latest_dt.date().isoformat() != now_tz.date().isoformat():
                violations.append(
                    {
                        "code": "missing_today_execution",
                        "message": (
                            "Latest schedule execution is not from current day in configured timezone."
                        ),
                        "latest_date": latest_dt.date().isoformat(),
                        "today_date": now_tz.date().isoformat(),
                    }
                )

    status = "ok" if not violations else "alert"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary: dict[str, Any] = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "runtime_dir": str(resolved_runtime_dir),
        "timezone": timezone_name,
        "max_age_hours": int(max_age_hours),
        "require_today": bool(require_today),
        "expected_statuses": expected,
        "latest_schedule_report_file": str(latest_path) if latest_path else None,
        "latest_schedule_status": latest_status,
        "latest_schedule_timestamp_utc_ms": latest_timestamp_ms,
        "violations": violations,
    }

    alert_result = None
    if status == "alert" and alert_command:
        alert_result = _run_alert_command(alert_command, summary)
        summary["alert_command_result"] = alert_result

    output_file = resolved_output_dir / f"model2_daily_healthcheck_{run_id}.json"
    summary_with_output = dict(summary)
    summary_with_output["output_file"] = str(output_file)
    output_file.write_text(json.dumps(summary_with_output, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Healthcheck for Model 2.0 scheduled daily pipeline.")
    parser.add_argument(
        "--runtime-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory containing model2_daily_schedule_*.json outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for healthcheck summaries.",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone used to validate daily execution freshness.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=30,
        help="Maximum accepted age in hours for latest schedule report.",
    )
    parser.add_argument(
        "--require-today",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require at least one schedule execution report in current day.",
    )
    parser.add_argument(
        "--expected-status",
        action="append",
        default=[],
        help="Accepted schedule status values (repeatable). Default: ok.",
    )
    parser.add_argument(
        "--alert-command",
        default=None,
        help="Optional shell command executed only when healthcheck status=alert.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_healthcheck(
        runtime_dir=args.runtime_dir,
        output_dir=args.output_dir,
        timezone_name=args.timezone,
        max_age_hours=int(args.max_age_hours),
        require_today=bool(args.require_today),
        expected_statuses=list(args.expected_status or []),
        alert_command=args.alert_command,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
