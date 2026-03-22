"""Runner diario de treino de entry agents por simbolo."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.episode_loader import load_episodes
from agent.sub_agent_manager import SubAgentManager
from config.settings import M2_SYMBOLS, MODEL2_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MIN_EPISODES_FOR_TRAINING = 20


def run_train_entry_agents(
    *,
    symbols: list[str] | None = None,
    db_path: str | Path = MODEL2_DB_PATH,
    timeframe: str = "H4",
    dry_run: bool = False,
    total_timesteps: int = 5000,
    continue_on_error: bool = False,
    min_episodes: int = MIN_EPISODES_FOR_TRAINING,
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
        "results": {},
    }

    manager = SubAgentManager(base_dir=str(REPO_ROOT / "models" / "sub_agents"))
    trained_count = 0
    skipped_count = 0
    error_count = 0

    for symbol in symbol_list:
        try:
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
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if int(summary["summary_stats"]["errors"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
