"""Treina head de protecao (SL/TP) por simbolo usando training_episodes."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from core.model2.protection_head import train_protection_head


def _to_float(raw: Any, default: float = 0.0) -> float:
    try:
        if raw is None:
            return float(default)
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _safe_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _as_dict(raw: Any) -> dict[str, Any]:
    return dict(raw) if isinstance(raw, dict) else {}


def _build_feature_vector(
    features_json: dict[str, Any],
    target_json: dict[str, Any],
) -> NDArray[np.float64] | None:
    snapshot = _as_dict(features_json.get("signal_snapshot"))
    candle = _as_dict(features_json.get("latest_candle"))
    funding = _as_dict(features_json.get("funding_rates"))
    oi = _as_dict(features_json.get("open_interest"))

    entry = _to_float(snapshot.get("entry_price"), 0.0)
    stop = _to_float(target_json.get("stop_loss"), _to_float(snapshot.get("stop_loss"), 0.0))
    take = _to_float(target_json.get("take_profit"), _to_float(snapshot.get("take_profit"), 0.0))
    if entry <= 0 or stop <= 0 or take <= 0:
        return None

    risk = abs(stop - entry)
    reward = abs(take - entry)
    if risk <= 0:
        return None

    rr = reward / risk
    close = _to_float(candle.get("close"), entry)
    high = _to_float(candle.get("high"), close)
    low = _to_float(candle.get("low"), close)
    range_pct = abs(high - low) / max(1e-9, close)
    funding_latest = _to_float(funding.get("latest_rate"), 0.0)
    oi_current = _to_float(oi.get("current_oi"), 0.0)

    return np.array(
        [
            entry,
            stop,
            take,
            rr,
            close,
            range_pct,
            funding_latest,
            oi_current,
        ],
        dtype=float,
    )


def _build_targets(reward_proxy: float) -> tuple[float, float]:
    # Reward positivo tende a aceitar alvo mais longo e stop mais justo.
    clipped = max(-0.01, min(0.01, float(reward_proxy)))
    sl_mult = max(0.80, min(1.20, 1.0 - (40.0 * clipped)))
    tp_mult = max(0.70, min(1.80, 1.0 + (80.0 * clipped)))
    return float(sl_mult), float(tp_mult)


def _train_for_symbol(*, db_path: Path, symbol: str, min_samples: int) -> tuple[int, Path | None]:
    features_rows: list[NDArray[np.float64]] = []
    target_rows: list[tuple[float, float]] = []

    with sqlite3.connect(str(db_path), timeout=5) as conn:
        rows = conn.execute(
            """
            SELECT reward_proxy, features_json, target_json
            FROM training_episodes
            WHERE symbol = ?
              AND reward_proxy IS NOT NULL
              AND features_json IS NOT NULL
              AND target_json IS NOT NULL
            ORDER BY id DESC
            """,
            (symbol,),
        ).fetchall()

    for reward_proxy, features_raw, target_raw in rows:
        features_json = _safe_json(features_raw)
        target_json = _safe_json(target_raw)
        feature_vec = _build_feature_vector(features_json, target_json)
        if feature_vec is None:
            continue
        sl_mult, tp_mult = _build_targets(_to_float(reward_proxy, 0.0))
        features_rows.append(feature_vec)
        target_rows.append((sl_mult, tp_mult))

    if len(features_rows) < int(min_samples):
        return len(features_rows), None

    features = np.vstack(features_rows)
    targets = np.asarray(target_rows, dtype=float)
    model = train_protection_head(features=features, targets=targets)

    out_dir = Path("models") / "protection_heads"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{symbol.upper()}_protection_head.json"
    out_path.write_text(json.dumps(model.to_json_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
    return len(features_rows), out_path


def run_train_protection_heads(
    *,
    db_path: str | Path,
    symbols: list[str] | None = None,
    min_samples: int = 50,
) -> dict[str, Any]:
    resolved_db = Path(str(db_path))
    if not resolved_db.exists():
        return {
            "status": "error",
            "error": f"db_nao_encontrado: {resolved_db}",
            "trained": 0,
            "skipped": 0,
            "results": {},
        }

    symbol_scope = [str(item).strip().upper() for item in list(symbols or []) if str(item).strip()]
    if not symbol_scope:
        with sqlite3.connect(str(resolved_db), timeout=5) as conn:
            rows = conn.execute(
                "SELECT DISTINCT symbol FROM training_episodes WHERE reward_proxy IS NOT NULL"
            ).fetchall()
        symbol_scope = [str(row[0]).strip().upper() for row in rows if row and str(row[0]).strip()]

    if not symbol_scope:
        return {
            "status": "ok",
            "trained": 0,
            "skipped": 0,
            "results": {},
            "message": "nenhum_simbolo_elegivel",
        }

    results: dict[str, Any] = {}
    trained = 0
    skipped = 0
    for symbol in symbol_scope:
        samples, out = _train_for_symbol(db_path=resolved_db, symbol=symbol, min_samples=int(min_samples))
        if out is None:
            skipped += 1
            results[symbol] = {
                "status": "skipped",
                "samples": int(samples),
                "reason": "insufficient_samples",
            }
            continue
        trained += 1
        results[symbol] = {
            "status": "trained",
            "samples": int(samples),
            "output_path": str(out),
        }

    return {
        "status": "ok",
        "trained": int(trained),
        "skipped": int(skipped),
        "results": results,
        "min_samples": int(min_samples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Treino do head de protecao por simbolo (SL/TP)")
    parser.add_argument("--db-path", default="db/modelo2.db")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--min-samples", type=int, default=50)
    args = parser.parse_args()

    summary = run_train_protection_heads(
        db_path=Path(str(args.db_path)),
        symbols=[str(item) for item in list(args.symbol)],
        min_samples=int(args.min_samples),
    )

    if summary.get("status") == "error":
        print(f"[ERRO] {summary.get('error')}")
        return 1

    raw_results = summary.get("results")
    results = raw_results if isinstance(raw_results, dict) else {}
    for symbol, item in results.items():
        if not isinstance(item, dict):
            continue
        if item.get("status") == "trained":
            print(f"[OK] {symbol}: modelo salvo em {item.get('output_path')} com {item.get('samples')} amostras")
        else:
            print(f"[SKIP] {symbol}: amostras insuficientes ({item.get('samples')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
