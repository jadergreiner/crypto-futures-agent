"""Persist cycle episodes for downstream model training datasets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DB_PATH, MODEL2_DB_PATH
from scripts.model2.feature_enricher import FeatureEnricher
from scripts.model2.binance_funding_api_client import BinanceFundingAPIClient

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
TIMEFRAME_TO_TABLE = {
    "D1": "ohlcv_d1",
    "H4": "ohlcv_h4",
    "H1": "ohlcv_h1",
}


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _safe_json_dict(raw_value: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


_MS_PER_CANDLE: dict[str, int] = {
    "H4": 14_400_000,
    "H1": 3_600_000,
    "D1": 86_400_000,
}

_LOOKUP_N: dict[str, int] = {
    "H4": 4,
    "H1": 24,
    "D1": 3,
}


def _ms_per_candle(timeframe: str) -> int:
    return _MS_PER_CANDLE[timeframe]


def _lookup_at_ms(event_timestamp_ms: int, timeframe: str) -> int:
    return event_timestamp_ms + _LOOKUP_N[timeframe] * _ms_per_candle(timeframe)


def _reward_counterfactual(
    side: str, close_t: float, close_tN: float | None
) -> tuple[float | None, str, str]:
    if close_tN is None or close_t <= 0:
        return None, "pending", "none"
    raw = (close_tN - close_t) / close_t
    # Lógica inversa ao PnL: bloqueou LONG e mercado subiu = oportunidade perdida
    if str(side).upper() == "LONG":
        reward = -raw
    else:
        reward = raw
    if reward > 0:
        return reward, "hold_correct", "counterfactual"
    return reward, "hold_opportunity_missed", "counterfactual"


def _reward_label(
    side: str, entry_price: float | None, exit_price: float | None
) -> tuple[float | None, str, str]:
    if entry_price is None or exit_price is None or entry_price <= 0:
        return None, "pending", "none"

    if str(side).upper() == "SHORT":
        reward = (entry_price - exit_price) / entry_price
    else:
        reward = (exit_price - entry_price) / entry_price

    if reward > 0:
        return reward, "win", "pnl_realized"
    if reward < 0:
        return reward, "loss", "pnl_realized"
    return reward, "breakeven", "pnl_realized"


def _latest_candle(conn: sqlite3.Connection, symbol: str, timeframe: str) -> dict[str, Any] | None:
    table = TIMEFRAME_TO_TABLE[timeframe]
    row = conn.execute(
        f"""
        SELECT timestamp, open, high, low, close, volume
        FROM {table}
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (symbol,),
    ).fetchone()
    if row is None:
        return None
    return {
        "timestamp": int(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
    }


def _counts_by_status(conn: sqlite3.Connection, table_name: str, symbol: str, timeframe: str | None = None) -> dict[str, int]:
    try:
        if timeframe is None:
            rows = conn.execute(
                f"SELECT status, COUNT(*) FROM {table_name} WHERE symbol = ? GROUP BY status",
                (symbol,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT status, COUNT(*) FROM {table_name} WHERE symbol = ? AND timeframe = ? GROUP BY status",
                (symbol, timeframe),
            ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {str(status): int(count) for status, count in rows}


def _ensure_training_episodes_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS training_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_key TEXT NOT NULL UNIQUE,
            cycle_run_id TEXT NOT NULL,
            execution_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            status TEXT NOT NULL,
            event_timestamp INTEGER NOT NULL,
            label TEXT NOT NULL,
            reward_proxy REAL,
            reward_source TEXT NOT NULL DEFAULT 'none',
            reward_lookup_at_ms INTEGER,
            features_json TEXT NOT NULL,
            target_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_episodes_symbol_ts ON training_episodes(symbol, event_timestamp DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_episodes_cycle ON training_episodes(cycle_run_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_episodes_lookup ON training_episodes(reward_lookup_at_ms) WHERE reward_lookup_at_ms IS NOT NULL"
    )


def _load_cursor(cursor_file: Path) -> int:
    if not cursor_file.exists():
        return 0
    try:
        payload = json.loads(cursor_file.read_text(encoding="utf-8"))
        return int(payload.get("last_updated_at_ms", 0))
    except Exception:
        return 0


def _save_cursor(cursor_file: Path, updated_at_ms: int) -> None:
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_updated_at_ms": int(updated_at_ms)}
    cursor_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def flush_deferred_rewards(
    model2_db_path: str | Path,
    source_db_path: str | Path,
    now_ms: int,
) -> dict[str, Any]:
    """Preenche reward_proxy diferido para episodios BLOCKED com candle T+N disponivel."""
    resolved_model2 = _resolve_repo_path(model2_db_path)
    resolved_source = _resolve_repo_path(source_db_path)

    flushed = 0
    pending = 0
    skipped = 0

    with sqlite3.connect(resolved_model2) as m2_conn, \
         sqlite3.connect(resolved_source) as src_conn:
        m2_conn.row_factory = sqlite3.Row

        rows = m2_conn.execute(
            """
            SELECT id, episode_key, symbol, timeframe, features_json,
                   reward_lookup_at_ms, event_timestamp
            FROM training_episodes
            WHERE reward_proxy IS NULL
              AND reward_lookup_at_ms IS NOT NULL
              AND reward_lookup_at_ms <= ?
            """,
            (now_ms,),
        ).fetchall()

        for row in rows:
            episode_id = int(row["id"])
            symbol = str(row["symbol"])
            timeframe = str(row["timeframe"])
            lookup_ms = int(row["reward_lookup_at_ms"])
            event_ts = int(row["event_timestamp"])
            features = _safe_json_dict(row["features_json"])

            signal_side = str(features.get("signal_side", "LONG"))
            close_t_raw = features.get("close_t")

            # Fallback: busca close_t do candle base na source DB
            if close_t_raw is None or float(close_t_raw) <= 0:
                table_name = TIMEFRAME_TO_TABLE.get(timeframe)
                if table_name:
                    base_row = src_conn.execute(
                        f"SELECT close FROM {table_name} WHERE symbol = ? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
                        (symbol, event_ts),
                    ).fetchone()
                    close_t_raw = float(base_row[0]) if base_row else 0.0
                else:
                    close_t_raw = 0.0

            close_t = float(close_t_raw)

            table = TIMEFRAME_TO_TABLE.get(timeframe)
            if table is None:
                skipped += 1
                continue

            candle_row = src_conn.execute(
                f"SELECT close FROM {table} WHERE symbol = ? AND timestamp = ? LIMIT 1",
                (symbol, lookup_ms),
            ).fetchone()

            if candle_row is None:
                pending += 1
                continue

            close_tN = float(candle_row[0])
            reward, label, reward_source = _reward_counterfactual(signal_side, close_t, close_tN)

            if reward is None:
                pending += 1
                continue

            m2_conn.execute(
                """
                UPDATE training_episodes
                SET reward_proxy = ?, label = ?, reward_source = ?
                WHERE id = ?
                """,
                (reward, label, reward_source, episode_id),
            )
            flushed += 1

        m2_conn.commit()

    return {"flushed": flushed, "pending": pending, "skipped": skipped}


def _latest_execution_episode_by_symbol(
    conn: sqlite3.Connection,
    *,
    symbols: list[str],
    timeframe: str,
) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        row = conn.execute(
            """
            SELECT episode_key, execution_id, label, reward_proxy, status, event_timestamp
            FROM training_episodes
            WHERE symbol = ?
              AND timeframe = ?
              AND execution_id > 0
            ORDER BY event_timestamp DESC, id DESC
            LIMIT 1
            """,
            (symbol, timeframe),
        ).fetchone()
        if row is None:
            continue
        snapshots[str(symbol)] = {
            "episode_key": str(row[0]),
            "execution_id": int(row[1]),
            "label": str(row[2]),
            "reward_proxy": (float(row[3]) if row[3] is not None else None),
            "status": str(row[4]),
            "event_timestamp": int(row[5]),
        }
    return snapshots


def run_persist_training_episodes(
    *,
    source_db_path: str | Path,
    model2_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    output_dir: str | Path,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    # Inicializar Binance Funding API Client (integração Phase D.3)
    try:
        funding_api_client = BinanceFundingAPIClient(db_path=str(resolved_model2_db), use_mock=False)
    except Exception:
        # Fallback se API indisponível
        funding_api_client = None

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_ms = _utc_now_ms()
    cursor_file = resolved_output_dir / "model2_training_episodes_cursor.json"
    last_cursor_ms = _load_cursor(cursor_file)
    latest_execution_episode_by_symbol: dict[str, dict[str, Any]] = {}

    with sqlite3.connect(resolved_source_db) as source_conn, sqlite3.connect(resolved_model2_db) as model2_conn:
        source_conn.row_factory = sqlite3.Row
        model2_conn.row_factory = sqlite3.Row
        _ensure_training_episodes_table(model2_conn)

        symbol_filter = list(dict.fromkeys(symbols))
        if not symbol_filter:
            rows = model2_conn.execute(
                "SELECT DISTINCT symbol FROM signal_executions ORDER BY symbol"
            ).fetchall()
            symbol_filter = [str(row[0]) for row in rows]

        placeholders = ", ".join(["?"] * len(symbol_filter)) if symbol_filter else ""
        query = [
            "SELECT",
            "  se.id, se.symbol, se.timeframe, se.signal_side, se.status, se.updated_at,",
            "  se.entry_filled_at, se.exited_at, se.exit_price, se.payload_json,",
            "  ts.entry_price, ts.stop_loss, ts.take_profit, ts.signal_timestamp",
            "FROM signal_executions se",
            "JOIN technical_signals ts ON ts.id = se.technical_signal_id",
            "WHERE se.updated_at > ?",
        ]
        params: list[Any] = [int(last_cursor_ms)]

        if symbol_filter:
            query.append(f"AND se.symbol IN ({placeholders})")
            params.extend(symbol_filter)
        query.append("AND se.timeframe = ?")
        params.append(timeframe)
        query.append("ORDER BY se.updated_at ASC, se.id ASC")

        execution_rows = model2_conn.execute(" ".join(query), params).fetchall()

        jsonl_path = resolved_output_dir / f"model2_training_episodes_{run_id}.jsonl"
        jsonl_lines: list[str] = []
        inserted_rows = 0
        max_seen_updated_at = int(last_cursor_ms)

        for row in execution_rows:
            execution_id = int(row["id"])
            symbol = str(row["symbol"])
            status = str(row["status"])
            updated_at = int(row["updated_at"])
            max_seen_updated_at = max(max_seen_updated_at, updated_at)
            payload = _safe_json_dict(row["payload_json"])
            signal_snapshot = payload.get("signal_snapshot") if isinstance(payload.get("signal_snapshot"), dict) else {}
            gate_payload = payload.get("gate") if isinstance(payload.get("gate"), dict) else {}
            latest_candle = _latest_candle(source_conn, symbol=symbol, timeframe=timeframe)

            entry_price = float(row["entry_price"]) if row["entry_price"] is not None else None
            exit_price = float(row["exit_price"]) if row["exit_price"] is not None else None

            if status == "BLOCKED":
                episode_key = f"hold:{execution_id}:{updated_at}"
                reward_proxy = None
                label = "pending"
                reward_source = "none"
                reward_lookup_at_ms: int | None = _lookup_at_ms(updated_at, str(row["timeframe"]))
            else:
                episode_key = f"exec:{execution_id}:{updated_at}"
                reward_proxy, label, reward_source = _reward_label(
                    side=str(row["signal_side"]),
                    entry_price=entry_price,
                    exit_price=exit_price,
                )
                reward_lookup_at_ms = None

            episode = {
                "episode_key": episode_key,
                "cycle_run_id": run_id,
                "execution_id": execution_id,
                "symbol": symbol,
                "timeframe": str(row["timeframe"]),
                "status": status,
                "event_timestamp": updated_at,
                "label": label,
                "reward_proxy": reward_proxy,
                "features": {
                    "latest_candle": latest_candle,
                    "signal_snapshot": signal_snapshot,
                    "gate": gate_payload,
                },
                "target": {
                    "final_status": status,
                    "entry_filled_at": row["entry_filled_at"],
                    "exited_at": row["exited_at"],
                    "exit_price": exit_price,
                    "signal_timestamp": row["signal_timestamp"],
                    "stop_loss": row["stop_loss"],
                    "take_profit": row["take_profit"],
                },
            }

            # Enriquecer features com volatilidade e multi-timeframe
            try:
                enriched_features = FeatureEnricher.enrich_features(
                    conn=source_conn,
                    symbol=symbol,
                    timeframe=str(row["timeframe"]),
                    base_features=episode["features"],
                )
                episode["features"] = enriched_features
            except Exception as e:
                # Log mas não falhe se enriquecimento falhar
                pass

            # Enriquecer com funding rates + open interest (Phase D.3)
            if funding_api_client:
                try:
                    episode["features"] = FeatureEnricher.enrich_with_funding_data(
                        enriched_features=episode["features"],
                        symbol=symbol,
                        funding_collector=funding_api_client
                    )
                except Exception as e:
                    # Graceful fallback se funding data indisponível
                    pass

            model2_conn.execute(
                """
                INSERT OR IGNORE INTO training_episodes (
                    episode_key,
                    cycle_run_id,
                    execution_id,
                    symbol,
                    timeframe,
                    status,
                    event_timestamp,
                    label,
                    reward_proxy,
                    reward_source,
                    reward_lookup_at_ms,
                    features_json,
                    target_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode["episode_key"],
                    run_id,
                    execution_id,
                    symbol,
                    str(row["timeframe"]),
                    status,
                    updated_at,
                    label,
                    reward_proxy,
                    reward_source,
                    reward_lookup_at_ms,
                    json.dumps(episode["features"], ensure_ascii=True, sort_keys=True),
                    json.dumps(episode["target"], ensure_ascii=True, sort_keys=True),
                    now_ms,
                ),
            )

            jsonl_lines.append(json.dumps(episode, ensure_ascii=True, sort_keys=True))
            inserted_rows += 1

        context_episodes = 0
        for symbol in symbol_filter:
            context_episode = {
                "episode_key": f"context:{run_id}:{symbol}",
                "cycle_run_id": run_id,
                "execution_id": 0,
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "CYCLE_CONTEXT",
                "event_timestamp": now_ms,
                "label": "context",
                "reward_proxy": None,
                "features": {
                    "latest_candle": _latest_candle(source_conn, symbol=symbol, timeframe=timeframe),
                    "opportunities_by_status": _counts_by_status(model2_conn, "opportunities", symbol, timeframe),
                    "technical_signals_by_status": _counts_by_status(model2_conn, "technical_signals", symbol, timeframe),
                    "signal_executions_by_status": _counts_by_status(model2_conn, "signal_executions", symbol, timeframe),
                },
                "target": {
                    "objective": "support_training_dataset_with_cycle_state",
                },
            }

            # Enriquecer features de contexto também
            try:
                enriched_features = FeatureEnricher.enrich_features(
                    conn=source_conn,
                    symbol=symbol,
                    timeframe=timeframe,
                    base_features=context_episode["features"],
                )
                context_episode["features"] = enriched_features
            except Exception:
                # Log mas não falhe
                pass

            # Enriquecer com funding rates + open interest (Phase D.3)
            if funding_api_client:
                try:
                    context_episode["features"] = FeatureEnricher.enrich_with_funding_data(
                        enriched_features=context_episode["features"],
                        symbol=symbol,
                        funding_collector=funding_api_client
                    )
                except Exception:
                    # Graceful fallback
                    pass

            model2_conn.execute(
                """
                INSERT OR IGNORE INTO training_episodes (
                    episode_key,
                    cycle_run_id,
                    execution_id,
                    symbol,
                    timeframe,
                    status,
                    event_timestamp,
                    label,
                    reward_proxy,
                    reward_source,
                    features_json,
                    target_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context_episode["episode_key"],
                    run_id,
                    0,
                    symbol,
                    timeframe,
                    "CYCLE_CONTEXT",
                    now_ms,
                    "context",
                    None,
                    "none",
                    json.dumps(context_episode["features"], ensure_ascii=True, sort_keys=True),
                    json.dumps(context_episode["target"], ensure_ascii=True, sort_keys=True),
                    now_ms,
                ),
            )
            jsonl_lines.append(json.dumps(context_episode, ensure_ascii=True, sort_keys=True))
            context_episodes += 1

        model2_conn.commit()
        latest_execution_episode_by_symbol = _latest_execution_episode_by_symbol(
            model2_conn,
            symbols=symbol_filter,
            timeframe=timeframe,
        )

    jsonl_path.write_text("\n".join(jsonl_lines) + ("\n" if jsonl_lines else ""), encoding="utf-8")
    if execution_rows:
        _save_cursor(cursor_file, max_seen_updated_at)

    summary = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "timeframe": timeframe,
        "symbols": symbol_filter,
        "cursor_start_ms": int(last_cursor_ms),
        "cursor_end_ms": int(max_seen_updated_at) if execution_rows else int(last_cursor_ms),
        "execution_episodes_persisted": int(inserted_rows),
        "context_episodes_persisted": int(context_episodes),
        "latest_execution_episode_by_symbol": latest_execution_episode_by_symbol,
        "jsonl_file": str(jsonl_path),
        "cursor_file": str(cursor_file),
    }
    summary_path = resolved_output_dir / f"model2_training_episodes_{run_id}.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    summary["output_file"] = str(summary_path)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persist cycle episodes for model training")
    parser.add_argument("--source-db-path", default=DB_PATH, help="Legacy/source SQLite with OHLCV tables.")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH, help="Model2 SQLite path.")
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol filter. Repeat flag for multiple symbols.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=sorted(TIMEFRAME_TO_TABLE.keys()),
        help="Timeframe for episode extraction and latest candle snapshot.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for artifacts.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_persist_training_episodes(
        source_db_path=args.source_db_path,
        model2_db_path=args.model2_db_path,
        symbols=list(args.symbol or []),
        timeframe=args.timeframe,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
