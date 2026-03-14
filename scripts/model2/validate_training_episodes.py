"""Valida acurácia de labels em episódios de treinamento vs outcomes reais."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH


@dataclass
class EpisodeValidation:
    """Resultado de validação de um episódio."""

    episode_key: str
    symbol: str
    label: str
    labeled_reward: float | None
    actual_filled_price: float | None
    actual_exit_price: float | None
    actual_reward: float | None
    label_correct: bool | None
    status: str  # "VALID", "MISMATCH", "PENDING", "CONTEXT"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    if isinstance(value, Path):
        return value
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _calculate_actual_reward(
    side: str, entry_price: float | None, exit_price: float | None
) -> tuple[float | None, str]:
    """Calcula reward e label a partir de prices reais."""
    if entry_price is None or exit_price is None or entry_price <= 0:
        return None, "pending"

    if str(side).upper() == "SHORT":
        reward = (entry_price - exit_price) / entry_price
    else:
        reward = (exit_price - entry_price) / entry_price

    if reward > 0:
        return reward, "win"
    if reward < 0:
        return reward, "loss"
    return reward, "breakeven"


def _validate_episodes(
    model2_db_path: str | Path,
    symbol_filter: list[str] | None = None,
    limit: int = 10000,
) -> dict[str, Any]:
    """Valida episódios de treinamento."""
    resolved_db = _resolve_repo_path(model2_db_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now_ms = _utc_now_ms()

    validations: list[EpisodeValidation] = []
    stats = defaultdict(int)
    label_accuracy = defaultdict(lambda: {"correct": 0, "total": 0})

    with sqlite3.connect(resolved_db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query episódios de execução (não context)
        query = [
            "SELECT",
            "  te.episode_key,",
            "  te.symbol,",
            "  te.label,",
            "  te.reward_proxy,",
            "  te.status,",
            "  se.signal_side,",
            "  se.filled_price,",
            "  se.exit_price",
            "FROM training_episodes te",
            "LEFT JOIN signal_executions se ON se.id = te.execution_id",
            "WHERE te.label != 'context'",
        ]
        params: list[Any] = []

        if symbol_filter:
            placeholders = ", ".join(["?"] * len(symbol_filter))
            query.append(f"AND te.symbol IN ({placeholders})")
            params.extend(symbol_filter)

        query.append("ORDER BY te.event_timestamp DESC")
        query.append(f"LIMIT {int(limit)}")

        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()

        for row in rows:
            episode_key = str(row["episode_key"])
            symbol = str(row["symbol"])
            label = str(row["label"]) if row["label"] else "unknown"
            labeled_reward = (
                float(row["reward_proxy"]) if row["reward_proxy"] is not None else None
            )
            signal_side = str(row["signal_side"]) if row["signal_side"] else "UNKNOWN"
            entry_price = (
                float(row["filled_price"]) if row["filled_price"] is not None else None
            )
            exit_price = float(row["exit_price"]) if row["exit_price"] is not None else None
            status = str(row["status"]) if row["status"] else "unknown"

            # Calcular reward real
            actual_reward, actual_label = _calculate_actual_reward(
                signal_side, entry_price, exit_price
            )

            # Validar correspondência
            label_correct = None
            validation_status = "PENDING"

            if label == "context":
                validation_status = "CONTEXT"
            elif label == "pending" or actual_label == "pending":
                validation_status = "PENDING"
            else:
                label_correct = label == actual_label
                validation_status = "VALID" if label_correct else "MISMATCH"

            validation = EpisodeValidation(
                episode_key=episode_key,
                symbol=symbol,
                label=label,
                labeled_reward=labeled_reward,
                actual_filled_price=entry_price,
                actual_exit_price=exit_price,
                actual_reward=actual_reward,
                label_correct=label_correct,
                status=validation_status,
            )

            validations.append(validation)
            stats[validation_status] += 1

            # Atualizar acurácia por label
            if validation_status == "VALID":
                label_accuracy[label]["total"] += 1
                if label_correct:
                    label_accuracy[label]["correct"] += 1
            elif validation_status == "MISMATCH":
                label_accuracy[label]["total"] += 1
                if label_correct:
                    label_accuracy[label]["correct"] += 1

    # Calcular taxa de acurácia geral
    total_valid = stats["VALID"] + stats["MISMATCH"]
    total_correct = sum(1 for v in validations if v.label_correct is True)
    overall_accuracy = total_correct / total_valid if total_valid > 0 else 0.0

    # Resumir acurácia por label
    accuracy_by_label = {}
    for label, counts in label_accuracy.items():
        if counts["total"] > 0:
            accuracy_by_label[label] = {
                "correct": counts["correct"],
                "total": counts["total"],
                "accuracy": counts["correct"] / counts["total"],
            }

    # Manter apenas últimos 100 para relatório
    sample_validations = validations[:100]

    summary = {
        "status": "ok",
        "run_id": run_id,
        "timestamp_utc_ms": now_ms,
        "model2_db_path": str(resolved_db),
        "symbol_filter": symbol_filter,
        "limit": limit,
        "stats": dict(stats),
        "overall_accuracy": overall_accuracy,
        "accuracy_by_label": accuracy_by_label,
        "sample_mismatches": [
            asdict(v) for v in sample_validations if v.status == "MISMATCH"
        ][:10],
        "validation_count": len(validations),
        "sample_count": len(sample_validations),
    }

    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida acurácia de labels em episódios de treinamento"
    )
    parser.add_argument(
        "--model2-db-path",
        type=str,
        default=str(MODEL2_DB_PATH),
        help="Caminho para DB do Model2 (default: $MODEL2_DB_PATH)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        action="append",
        dest="symbol",
        help="Filtro por símbolo (pode ser repetido)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Limite de episódios a validar (default: 10000)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = _validate_episodes(
        model2_db_path=args.model2_db_path,
        symbol_filter=list(dict.fromkeys(args.symbol or [])),
        limit=args.limit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
