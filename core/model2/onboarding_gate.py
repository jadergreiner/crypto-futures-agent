"""Gate operacional para fechamento de onboarding de simbolo no M2."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_PIPELINE_STAGES: tuple[str, ...] = (
    "scan",
    "track",
    "validate",
    "resolve",
    "bridge",
)


@dataclass(frozen=True)
class SymbolOnboardingGateResult:
    """Resultado consolidado do gate operacional de onboarding."""

    symbol: str
    min_validated_signals: int
    validated_signals: int
    pipeline_ok: bool
    training_ok: bool
    ready: bool
    reasons: tuple[str, ...]
    evidence: dict[str, Any]


def _read_json_file(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        raw = file_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def count_validated_signals(*, model2_db_path: str | Path, symbol: str) -> int:
    """Conta sinais validados por simbolo usando `model_decisions` como fonte canonica."""

    db_path = Path(model2_db_path)
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM model_decisions
            WHERE symbol = ?
              AND action <> 'HOLD'
            """,
            (symbol,),
        ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def _is_pipeline_ok(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    if str(payload.get("status", "")).lower() != "ok":
        return False
    stage_errors = payload.get("stage_errors")
    if isinstance(stage_errors, list) and stage_errors:
        return False
    stages = payload.get("stages")
    if not isinstance(stages, dict):
        return False
    stage_keys = set(stages.keys())
    return set(REQUIRED_PIPELINE_STAGES).issubset(stage_keys)


def _is_training_ok(payload: dict[str, Any], *, symbol: str) -> bool:
    if not payload:
        return False
    summary_stats = payload.get("summary_stats")
    if not isinstance(summary_stats, dict):
        return False
    if int(summary_stats.get("trained", 0)) < 1:
        return False
    results = payload.get("results")
    if not isinstance(results, dict):
        return False
    symbol_result = results.get(symbol)
    if not isinstance(symbol_result, dict):
        return False
    if str(symbol_result.get("status", "")).lower() != "trained":
        return False
    return int(symbol_result.get("episodes_used", 0)) > 0


def evaluate_symbol_onboarding_gate(
    *,
    model2_db_path: str | Path,
    symbol: str,
    min_validated_signals: int = 20,
    pipeline_summary_path: str | Path | None = None,
    training_summary_path: str | Path | None = None,
) -> SymbolOnboardingGateResult:
    """Avalia prontidao operacional de onboarding para um simbolo."""

    reasons: list[str] = []

    validated_signals = count_validated_signals(
        model2_db_path=model2_db_path,
        symbol=symbol,
    )
    if validated_signals < int(min_validated_signals):
        reasons.append("validated_signals_below_minimum")

    pipeline_payload = _read_json_file(pipeline_summary_path)
    pipeline_ok = _is_pipeline_ok(pipeline_payload)
    if not pipeline_ok:
        reasons.append("pipeline_not_ok")

    training_payload = _read_json_file(training_summary_path)
    training_ok = _is_training_ok(training_payload, symbol=symbol)
    if not training_ok:
        reasons.append("training_not_ok")

    ready = not reasons
    evidence: dict[str, Any] = {
        "model2_db_path": str(model2_db_path),
        "pipeline_summary_path": str(pipeline_summary_path) if pipeline_summary_path else "",
        "training_summary_path": str(training_summary_path) if training_summary_path else "",
    }
    return SymbolOnboardingGateResult(
        symbol=symbol,
        min_validated_signals=int(min_validated_signals),
        validated_signals=validated_signals,
        pipeline_ok=pipeline_ok,
        training_ok=training_ok,
        ready=ready,
        reasons=tuple(reasons),
        evidence=evidence,
    )
