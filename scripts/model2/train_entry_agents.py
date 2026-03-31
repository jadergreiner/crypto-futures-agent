"""Runner diario de treino de entry agents por simbolo."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.episode_loader import load_episodes
from agent.sub_agent_manager import SubAgentManager
from config.settings import M2_SYMBOLS, MODEL2_DB_PATH
from core.model2.cycle_report import (
    RETRAIN_EPISODE_THRESHOLD,
    collect_training_info_for_symbol,
    resolve_retrain_threshold,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Usar constante centralizada de threshold de episódios
MIN_EPISODES_FOR_TRAINING = RETRAIN_EPISODE_THRESHOLD


def _ensure_rl_training_log_schema(conn: sqlite3.Connection) -> None:
    """Garante schema minimo da auditoria global de treino."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episodes_used INTEGER NOT NULL,
            avg_reward REAL,
            completed_at TEXT NOT NULL,
            model_version TEXT,
            status TEXT,
            created_at TEXT,
            completed_at_ms INTEGER
        )
        """
    )
    cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(rl_training_log)").fetchall()
    }
    if "completed_at_ms" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN completed_at_ms INTEGER")
    if "status" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN status TEXT")
    if "avg_reward" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN avg_reward REAL")
    if "model_version" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN model_version TEXT")
    if "created_at" not in cols:
        conn.execute("ALTER TABLE rl_training_log ADD COLUMN created_at TEXT")


def _ensure_rl_training_log_by_symbol_schema(conn: sqlite3.Connection) -> None:
    """Garante schema minimo da auditoria de treino por simbolo."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_training_log_by_symbol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT,
            episodes_used INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            completed_at_ms INTEGER,
            status TEXT,
            model_version TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rl_training_log_by_symbol_lookup
        ON rl_training_log_by_symbol (symbol, timeframe, completed_at_ms DESC, id DESC)
        """
    )
    cols = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(rl_training_log_by_symbol)").fetchall()
    }
    if "timeframe" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN timeframe TEXT")
    if "completed_at_ms" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN completed_at_ms INTEGER")
    if "status" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN status TEXT")
    if "model_version" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN model_version TEXT")
    if "created_at" not in cols:
        conn.execute("ALTER TABLE rl_training_log_by_symbol ADD COLUMN created_at TEXT")


def _record_training_logs(
    *,
    db_path: Path,
    timeframe: str,
    trained_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Registra auditoria de treino global e por simbolo para status operacional."""
    if not trained_results:
        return {"recorded": False, "symbols": []}

    now_utc = datetime.now(timezone.utc)
    now_brt = now_utc.astimezone(timezone(timedelta(hours=-3)))
    completed_at = now_brt.strftime("%Y-%m-%d %H:%M:%S")
    completed_at_ms = int(now_utc.timestamp() * 1000)
    episodes_total = sum(
        int(result.get("episodes_used") or 0)
        for result in trained_results.values()
    )

    with sqlite3.connect(str(db_path), timeout=5) as conn:
        _ensure_rl_training_log_schema(conn)
        _ensure_rl_training_log_by_symbol_schema(conn)
        conn.execute(
            """
            INSERT INTO rl_training_log (
                episodes_used,
                completed_at,
                completed_at_ms,
                status,
                model_version,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(episodes_total),
                completed_at,
                int(completed_at_ms),
                "ok",
                "ppo_incremental_entry_agent",
                completed_at,
            ),
        )

        for symbol, result in trained_results.items():
            conn.execute(
                """
                INSERT INTO rl_training_log_by_symbol (
                    symbol,
                    timeframe,
                    episodes_used,
                    completed_at,
                    completed_at_ms,
                    status,
                    model_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(symbol).upper(),
                    str(timeframe).upper(),
                    int(result.get("episodes_used") or 0),
                    completed_at,
                    int(completed_at_ms),
                    "ok",
                    "ppo_incremental_entry_agent",
                    completed_at,
                ),
            )
        conn.commit()

    return {
        "recorded": True,
        "completed_at": completed_at,
        "completed_at_ms": int(completed_at_ms),
        "episodes_total": int(episodes_total),
        "symbols": sorted(str(symbol).upper() for symbol in trained_results),
    }


def run_train_entry_agents(
    *,
    symbols: list[str] | None = None,
    db_path: str | Path = MODEL2_DB_PATH,
    timeframe: str = "H4",
    dry_run: bool = False,
    total_timesteps: int = 5000,
    continue_on_error: bool = False,
    min_episodes: int = MIN_EPISODES_FOR_TRAINING,
    require_pending_threshold: bool = False,
) -> dict[str, Any]:
    """Executa treino de entry agents por simbolo e salva resumo em JSON."""
    db_path_obj = Path(db_path)
    symbol_list = [
        str(s).upper()
        for s in (symbols if symbols is not None else list(M2_SYMBOLS))
    ]
    output_dir = REPO_ROOT / "results" / "model2" / "runtime"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path_obj),
        "timeframe": timeframe,
        "dry_run": dry_run,
        "total_timesteps": int(total_timesteps),
        "continue_on_error": continue_on_error,
        "require_pending_threshold": bool(require_pending_threshold),
        "results": {},
    }

    manager = SubAgentManager(base_dir=str(REPO_ROOT / "models" / "sub_agents"))
    trained_count = 0
    skipped_count = 0
    error_count = 0
    trained_results: dict[str, dict[str, Any]] = {}

    for symbol in symbol_list:
        try:
            if require_pending_threshold:
                resolved_threshold, resolved_confidence = resolve_retrain_threshold(
                    str(db_path_obj),
                    symbol=symbol,
                    timeframe=timeframe,
                )
                _, pending_episodes = collect_training_info_for_symbol(
                    str(db_path_obj),
                    symbol=symbol,
                    timeframe=timeframe,
                )
                if int(pending_episodes) < int(resolved_threshold):
                    conf_tag = (
                        "N/A"
                        if resolved_confidence is None
                        else f"{float(resolved_confidence):.2%}"
                    )
                    summary["results"][symbol] = {
                        "status": "skipped",
                        "reason": (
                            "insufficient_pending_episodes_after_cutoff: "
                            f"{int(pending_episodes)} < {int(resolved_threshold)}"
                        ),
                        "pending_episodes": int(pending_episodes),
                        "resolved_threshold": int(resolved_threshold),
                        "resolved_confidence": conf_tag,
                    }
                    skipped_count += 1
                    continue

            episodes = load_episodes(
                db_path=db_path_obj,
                symbol=symbol,
                timeframe=timeframe,
                min_episodes=0,
            )
            episode_count = len(episodes)

            if episode_count < int(min_episodes):
                summary["results"][symbol] = {
                    "status": "skipped",
                    "reason": (
                        f"insufficient_episodes: {episode_count} < "
                        f"{int(min_episodes)}"
                    ),
                    "episodes_found": episode_count,
                }
                skipped_count += 1
                continue

            if dry_run:
                summary["results"][symbol] = {
                    "status": "trained",
                    "dry_run": True,
                    "episodes_used": episode_count,
                    "steps_run": int(total_timesteps),
                }
                trained_count += 1
                continue

            train_result = manager.train_entry_agent(
                symbol=symbol,
                episodes=episodes,
                total_timesteps=int(total_timesteps),
            )
            if bool(train_result.get("success")):
                summary["results"][symbol] = {
                    "status": "trained",
                    "episodes_used": episode_count,
                    "steps_run": int(total_timesteps),
                }
                trained_results[symbol] = {
                    "episodes_used": episode_count,
                    "steps_run": int(total_timesteps),
                }
                trained_count += 1
            else:
                reason = str(
                    train_result.get("error")
                    or train_result.get("reason")
                    or "unknown"
                )
                summary["results"][symbol] = {
                    "status": "error",
                    "error": reason,
                    "episodes_found": episode_count,
                }
                error_count += 1
                if not continue_on_error:
                    break
        except Exception as exc:
            summary["results"][symbol] = {
                "status": "error",
                "error": str(exc),
            }
            error_count += 1
            if not continue_on_error:
                break

    if not dry_run and trained_count > 0:
        manager.save_all()
        summary["training_log"] = _record_training_logs(
            db_path=db_path_obj,
            timeframe=timeframe,
            trained_results=trained_results,
        )

    summary["summary_stats"] = {
        "trained": trained_count,
        "skipped": skipped_count,
        "errors": error_count,
    }

    output_file = output_dir / (
        "train_entry_agents_"
        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        + ".json"
    )
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    summary["output_file"] = str(output_file)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Treino diario de entry agents por simbolo"
    )
    parser.add_argument(
        "--symbol",
        action="append",
        help="Simbolo; repetir flag para multiplos",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=["D1", "H4", "H1", "M5"],
    )
    parser.add_argument("--db-path", type=Path, default=MODEL2_DB_PATH)
    parser.add_argument("--total-timesteps", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--min-episodes",
        type=int,
        default=MIN_EPISODES_FOR_TRAINING,
    )
    parser.add_argument(
        "--require-pending-threshold",
        action="store_true",
        help=(
            "Treina apenas quando episodios pendentes apos cutoff atingirem o "
            "threshold resolvido por confianca"
        ),
    )
    args = parser.parse_args()

    symbols = args.symbol if args.symbol else list(M2_SYMBOLS)
    summary = run_train_entry_agents(
        symbols=[str(s).upper() for s in symbols],
        db_path=args.db_path,
        timeframe=args.timeframe,
        dry_run=bool(args.dry_run),
        total_timesteps=int(args.total_timesteps),
        continue_on_error=bool(args.continue_on_error),
        min_episodes=int(args.min_episodes),
        require_pending_threshold=bool(args.require_pending_threshold),
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if int(summary["summary_stats"]["errors"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
