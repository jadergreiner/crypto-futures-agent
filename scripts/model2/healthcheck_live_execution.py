"""Healthcheck for Model 2.0 live execution dashboard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def _load_latest_live_dashboard(runtime_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    files = sorted(runtime_dir.glob("model2_live_dashboard_*.json"), key=lambda item: item.stat().st_mtime)
    if not files:
        return None, None
    latest = files[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        payload = None
    return latest, payload if isinstance(payload, dict) else None


def _run_alert_command(command: str, summary: dict[str, Any]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)
    except Exception as exc:
        return {"command": command, "status": "error", "error": str(exc)}
    return {
        "command": command,
        "status": "ok" if completed.returncode == 0 else "error",
        "return_code": int(completed.returncode),
        "stdout": completed.stdout[-500:] if completed.stdout else "",
        "stderr": completed.stderr[-500:] if completed.stderr else "",
        "triggered_by": summary.get("status"),
    }


def run_live_healthcheck(
    *,
    runtime_dir: str | Path,
    output_dir: str | Path,
    max_age_hours: int,
    max_unprotected_filled: int,
    max_stale_entry_sent: int,
    max_position_mismatches: int,
    alert_command: str | None,
) -> dict[str, Any]:
    resolved_runtime_dir = _resolve_repo_path(runtime_dir)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    latest_path, latest_payload = _load_latest_live_dashboard(resolved_runtime_dir)
    now_ms = _utc_now_ms()
    violations: list[dict[str, Any]] = []

    if latest_path is None:
        violations.append(
            {
                "code": "missing_live_dashboard",
                "message": "No model2_live_dashboard_*.json report found in runtime directory.",
            }
        )
    elif latest_payload is None:
        violations.append(
            {
                "code": "invalid_live_dashboard",
                "message": f"Latest live dashboard is not valid JSON: {latest_path}",
            }
        )
    else:
        timestamp_ms = int(latest_payload.get("timestamp_utc_ms") or int(latest_path.stat().st_mtime * 1000))
        age_hours = max(0.0, (now_ms - timestamp_ms) / 3_600_000)
        if age_hours > float(max_age_hours):
            violations.append(
                {
                    "code": "stale_dashboard",
                    "message": f"Latest live dashboard age {age_hours:.2f}h exceeds max_age_hours={max_age_hours}.",
                    "age_hours": round(age_hours, 2),
                }
            )

        if int(latest_payload.get("unprotected_filled_count") or 0) > int(max_unprotected_filled):
            violations.append(
                {
                    "code": "unprotected_positions",
                    "message": "Live dashboard reports too many filled positions without protection.",
                    "unprotected_filled_count": int(latest_payload.get("unprotected_filled_count") or 0),
                }
            )
        if int(latest_payload.get("stale_entry_sent_count") or 0) > int(max_stale_entry_sent):
            violations.append(
                {
                    "code": "stale_entries",
                    "message": "Live dashboard reports stale ENTRY_SENT executions.",
                    "stale_entry_sent_count": int(latest_payload.get("stale_entry_sent_count") or 0),
                }
            )
        if int(latest_payload.get("open_position_mismatches_count") or 0) > int(max_position_mismatches):
            violations.append(
                {
                    "code": "position_mismatches",
                    "message": "Live dashboard reports exchange/database position mismatches.",
                    "open_position_mismatches_count": int(latest_payload.get("open_position_mismatches_count") or 0),
                }
            )

    status = "ok" if not violations else "alert"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary: dict[str, Any] = {
        "status": status,
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "runtime_dir": str(resolved_runtime_dir),
        "max_age_hours": int(max_age_hours),
        "max_unprotected_filled": int(max_unprotected_filled),
        "max_stale_entry_sent": int(max_stale_entry_sent),
        "max_position_mismatches": int(max_position_mismatches),
        "latest_live_dashboard_file": str(latest_path) if latest_path else None,
        "violations": violations,
    }
    if status == "alert" and alert_command:
        summary["alert_command_result"] = _run_alert_command(alert_command, summary)

    output_file = resolved_output_dir / f"model2_live_healthcheck_{run_id}.json"
    summary_with_output = dict(summary)
    summary_with_output["output_file"] = str(output_file)
    output_file.write_text(json.dumps(summary_with_output, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Healthcheck for Model 2.0 live execution.")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-age-hours", type=int, default=2)
    parser.add_argument("--max-unprotected-filled", type=int, default=0)
    parser.add_argument("--max-stale-entry-sent", type=int, default=0)
    parser.add_argument("--max-position-mismatches", type=int, default=0)
    parser.add_argument("--alert-command", default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_live_healthcheck(
        runtime_dir=args.runtime_dir,
        output_dir=args.output_dir,
        max_age_hours=int(args.max_age_hours),
        max_unprotected_filled=int(args.max_unprotected_filled),
        max_stale_entry_sent=int(args.max_stale_entry_sent),
        max_position_mismatches=int(args.max_position_mismatches),
        alert_command=args.alert_command,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
