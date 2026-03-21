"""RL scoring wrapper for Model 2.0 technical signals."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.rl_model_loader import RLModelLoader
from scripts.model2.io_utils import atomic_write_json


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _signal_side_to_feature(signal_side: Any) -> float:
    side = str(signal_side or "").strip().upper()
    if side in {"BUY", "LONG"}:
        return 1.0
    if side in {"SELL", "SHORT"}:
        return -1.0
    return 0.0


def _build_features(row: sqlite3.Row) -> np.ndarray:
    entry = _to_float(row["entry_price"])
    stop = _to_float(row["stop_loss"])
    target = _to_float(row["take_profit"])
    risk = abs(stop - entry)
    reward = abs(entry - target)
    rr = reward / risk if risk > 0 else 0.0
    side_feature = _signal_side_to_feature(row["signal_side"])
    return np.array([entry, stop, target, rr, side_feature], dtype=np.float32)


def run_rl_signal_generation(
    *,
    model2_db_path: Path | str,
    timeframe: str = "H4",
    symbols: list[str] | None = None,
    ppo_checkpoint: Path | str | None = None,
    dry_run: bool = False,
    output_dir: Path | str | None = None,
) -> Dict[str, Any]:
    """Apply RL confidence scoring to technical_signals payload."""

    resolved_db = Path(model2_db_path)
    resolved_output_dir = Path(output_dir) if output_dir else (REPO_ROOT / "results" / "model2" / "runtime")
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    rl_loader = RLModelLoader(checkpoint_path=ppo_checkpoint)
    now_ms = _utc_now_ms()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    query = [
        "SELECT id, symbol, timeframe, signal_side, entry_price, stop_loss, take_profit, payload_json",
        "FROM technical_signals",
        "WHERE timeframe = ?",
        "  AND status IN ('CREATED', 'CONSUMED')",
        "ORDER BY id ASC",
    ]
    params: list[Any] = [str(timeframe)]
    if symbols:
        placeholders = ", ".join("?" for _ in symbols)
        query.insert(3, f"  AND symbol IN ({placeholders})")
        params = [str(timeframe), *[str(item).upper() for item in symbols]]

    processed = 0
    enhanced = 0
    eligible = 0
    items: list[dict[str, Any]] = []

    with sqlite3.connect(resolved_db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("\n".join(query), params).fetchall()

        for row in rows:
            processed += 1
            features = _build_features(row)
            confidence, action = rl_loader.predict_confidence(features=features, signal_side=str(row["signal_side"]))
            is_eligible = confidence >= 0.50
            if is_eligible:
                eligible += 1

            payload = {}
            try:
                payload = json.loads(row["payload_json"] or "{}")
                if not isinstance(payload, dict):
                    payload = {}
            except json.JSONDecodeError:
                payload = {}
            payload["rl"] = {
                "confidence": float(round(confidence, 6)),
                "action": str(action),
                "eligible": bool(is_eligible),
                "fallback": bool(rl_loader.is_fallback),
                "fallback_reason": rl_loader.fallback_reason,
                "scored_at": int(now_ms),
            }

            if not dry_run:
                conn.execute(
                    """
                    UPDATE technical_signals
                    SET payload_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (json.dumps(payload, ensure_ascii=True, sort_keys=True), int(now_ms), int(row["id"])),
                )
                enhanced += 1

            items.append(
                {
                    "signal_id": int(row["id"]),
                    "symbol": str(row["symbol"]),
                    "confidence": float(round(confidence, 6)),
                    "action": str(action),
                    "eligible": bool(is_eligible),
                }
            )

        if not dry_run:
            conn.commit()

    summary = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "model2_db_path": str(resolved_db),
        "timeframe": str(timeframe),
        "symbols": [str(item).upper() for item in symbols] if symbols else [],
        "dry_run": bool(dry_run),
        "ppo_available": not rl_loader.is_fallback,
        "fallback_reason": rl_loader.fallback_reason,
        "signals_processed": int(processed),
        "signals_enhanced": int(enhanced),
        "signals_eligible_threshold": int(eligible),
        "items": items,
    }
    output_file = resolved_output_dir / f"model2_rl_signals_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


if __name__ == "__main__":
    result = run_rl_signal_generation(
        model2_db_path="db/modelo2.db",
        timeframe="H4",
        dry_run=True,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
