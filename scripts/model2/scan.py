"""Model 2.0 opportunity scanner runner (isolated from legacy flow)."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

pd = importlib.import_module("pandas")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.time_utils import ts_ms_to_brt_str
from config.settings import (
    DB_PATH,
    M2_MODEL_FIRST_SCAN_MIN_CONFIDENCE,
    M2_MODEL_FIRST_SCAN_MIN_CONFIDENCE_BY_SYMBOL,
    M2_MODEL_FIRST_SCAN_SYMBOLS,
    M2_SYMBOLS,
    MODEL2_DB_PATH,
)
from core.model2 import (
    ACTION_OPEN_LONG,
    ACTION_OPEN_SHORT,
    DetectorInput,
    DetectionResult,
    Model2ThesisRepository,
    ModelDecisionInput,
    ModelInferenceService,
    TechnicalSignalInferenceProvider,
    detect_initial_short_failure,
)
from core.model2.ohlcv_cache import OhlcvCacheProvider, build_cache_key
from indicators.smc import SmartMoneyConcepts
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
TIMEFRAME_TO_TABLE = {
    "D1": "ohlcv_d1",
    "H4": "ohlcv_h4",
    "H1": "ohlcv_h1",
    "M5": "ohlcv_m5",
}
M2_020_2_SCAN_RULE_ID = "M2-020.2-RULE-RL-MODEL-FIRST-SCAN"
M2_020_2_SCAN_THESIS_TYPE = "DECISAO_MODELO_RL"
M2_020_2_SCAN_THRESHOLD = float(M2_MODEL_FIRST_SCAN_MIN_CONFIDENCE)
M2_020_2_SCAN_THRESHOLD_BY_SYMBOL = dict(M2_MODEL_FIRST_SCAN_MIN_CONFIDENCE_BY_SYMBOL)


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_first_float(*values: Any) -> float | None:
    for value in values:
        parsed = _safe_float(value)
        if parsed is not None:
            return parsed
    return None


def _resolve_model_first_confidence_threshold(symbol: str) -> float:
    """Resolve threshold do model-first priorizando configuracao por simbolo."""
    normalized_symbol = str(symbol).strip().upper()
    if normalized_symbol in M2_020_2_SCAN_THRESHOLD_BY_SYMBOL:
        return float(M2_020_2_SCAN_THRESHOLD_BY_SYMBOL[normalized_symbol])
    return float(M2_020_2_SCAN_THRESHOLD)


def _infer_base_risk_distance(
    *,
    close_price: float,
    latest_candle: dict[str, Any],
    latest_indicator: dict[str, Any],
) -> float:
    high_price = _pick_first_float(latest_candle.get("high"), close_price) or close_price
    low_price = _pick_first_float(latest_candle.get("low"), close_price) or close_price
    candle_range = max(0.0, high_price - low_price)

    atr_distance = _pick_first_float(
        latest_indicator.get("atr"),
        latest_indicator.get("atr_14"),
        latest_indicator.get("atr14"),
    )
    if atr_distance is None:
        atr_normalized = _pick_first_float(
            latest_indicator.get("atr_normalized"),
            latest_indicator.get("atr_normalized_pct"),
        )
        if atr_normalized is not None and atr_normalized > 0:
            atr_distance = close_price * (
                atr_normalized / 100.0 if atr_normalized > 1.0 else atr_normalized
            )

    return max(close_price * 0.003, candle_range, atr_distance or 0.0)


def _build_model_first_market_state(
    *,
    symbol: str,
    timeframe: str,
    candles_df: Any,
    indicators: list[dict[str, Any]],
    smc: dict[str, Any],
    scan_timestamp: int,
) -> ModelDecisionInput | None:
    if candles_df.empty:
        return None

    latest_candle = dict(candles_df.iloc[-1].to_dict())
    latest_indicator = dict(indicators[-1]) if indicators else {}
    close_price = _pick_first_float(
        latest_candle.get("close"),
        latest_candle.get("open"),
    )
    if close_price is None or close_price <= 0:
        return None

    risk_distance = _infer_base_risk_distance(
        close_price=close_price,
        latest_candle=latest_candle,
        latest_indicator=latest_indicator,
    )
    stop_loss = close_price - risk_distance
    take_profit = close_price + risk_distance
    volume = _pick_first_float(latest_candle.get("volume"), 0.0) or 0.0
    signal_timestamp = int(latest_candle.get("timestamp") or scan_timestamp)
    structure = smc.get("structure") or smc.get("market_structure") or {}
    market_structure = "unknown"
    if isinstance(structure, dict):
        market_structure = str(structure.get("type") or "unknown")

    market_state = {
        "symbol": symbol,
        "timeframe": timeframe,
        "signal_side": "",
        "signal_timestamp": signal_timestamp,
        "entry_price": close_price,
        "close_price": close_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "volume": volume,
        "rsi": _pick_first_float(
            latest_indicator.get("rsi"),
            latest_indicator.get("rsi_14"),
        ),
        "macd_line": _pick_first_float(
            latest_indicator.get("macd_line"),
            latest_indicator.get("macd"),
        ),
        "macd_signal": _pick_first_float(latest_indicator.get("macd_signal")),
        "atr_normalized": _pick_first_float(
            latest_indicator.get("atr_normalized"),
            latest_indicator.get("atr_normalized_pct"),
        ),
        "market_context": {
            "close_price": close_price,
            "h1_close": close_price,
            "h4_close": close_price,
            "d1_close": close_price,
            "market_structure": market_structure,
        },
    }
    return ModelDecisionInput(
        symbol=symbol,
        timeframe=timeframe,
        decision_timestamp=scan_timestamp,
        model_version="m2-model-first-scan-v1",
        market_state=market_state,
        position_state={},
        risk_state={
            "signal_age_ms": max(0, scan_timestamp - signal_timestamp),
        },
    )


def _detect_model_first_opportunity(
    *,
    symbol: str,
    timeframe: str,
    candles_df: Any,
    indicators: list[dict[str, Any]],
    smc: dict[str, Any],
    scan_timestamp: int,
    inference_service: ModelInferenceService,
    confidence_threshold: float,
) -> DetectionResult | None:
    model_input = _build_model_first_market_state(
        symbol=symbol,
        timeframe=timeframe,
        candles_df=candles_df,
        indicators=indicators,
        smc=smc,
        scan_timestamp=scan_timestamp,
    )
    if model_input is None:
        return None

    inference_result = inference_service.infer(model_input)
    if not inference_result.accepted or inference_result.decision is None:
        return None

    decision = inference_result.decision
    decision_metadata = dict(decision.metadata)
    if bool(decision_metadata.get("rl_fallback")):
        return None
    if float(decision.confidence) < float(confidence_threshold):
        return None

    if decision.action == ACTION_OPEN_LONG:
        side = "LONG"
    elif decision.action == ACTION_OPEN_SHORT:
        side = "SHORT"
    else:
        return None

    latest_candle = dict(candles_df.iloc[-1].to_dict())
    entry_price = _pick_first_float(
        model_input.market_state.get("entry_price"),
        latest_candle.get("close"),
    )
    stop_loss = _safe_float(decision.sl_target)
    take_profit = _safe_float(decision.tp_target)
    if (
        entry_price is None
        or stop_loss is None
        or take_profit is None
        or entry_price <= 0
    ):
        return None

    zone_low = min(entry_price, stop_loss, take_profit)
    zone_high = max(entry_price, stop_loss, take_profit)
    trigger_price = entry_price
    invalidation_price = stop_loss
    rejection_candle = {
        "timestamp": int(latest_candle.get("timestamp") or scan_timestamp),
        "open": _pick_first_float(latest_candle.get("open"), entry_price),
        "high": _pick_first_float(latest_candle.get("high"), entry_price),
        "low": _pick_first_float(latest_candle.get("low"), entry_price),
        "close": _pick_first_float(latest_candle.get("close"), entry_price),
        "volume": _pick_first_float(latest_candle.get("volume"), 0.0),
    }
    metadata = {
        "source": "rl_model_first_scan",
        "technical_zone": {
            "source": "rl_model",
            "zone_id": None,
            "timestamp": rejection_candle["timestamp"],
            "zone_low": zone_low,
            "zone_high": zone_high,
            "status": "MODEL_FIRST",
        },
        "rejection_candle": rejection_candle,
        "context": {
            "market_structure": str(
                (model_input.market_state.get("market_context") or {}).get(
                    "market_structure",
                    "unknown",
                )
            ),
            "model_first": True,
        },
        "model_decision": {
            "action": decision.action,
            "confidence": float(decision.confidence),
            "reason_code": decision.reason_code,
            "model_version": decision.model_version,
            "metadata": decision_metadata,
        },
        "parameters": {
            "confidence_threshold": float(confidence_threshold),
            "scan_timestamp": int(scan_timestamp),
        },
    }
    return DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe=timeframe,
        side=side,
        thesis_type=M2_020_2_SCAN_THESIS_TYPE,
        zone_low=zone_low,
        zone_high=zone_high,
        trigger_price=trigger_price,
        invalidation_price=invalidation_price,
        metadata=metadata,
        rule_id=M2_020_2_SCAN_RULE_ID,
    )


def _load_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, limit: int) -> Any:
    table_name = TIMEFRAME_TO_TABLE[timeframe]
    query = (
        f"SELECT timestamp, open, high, low, close, volume "
        f"FROM {table_name} WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?"
    )
    rows = conn.execute(query, (symbol, limit)).fetchall()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df.sort_values("timestamp").reset_index(drop=True)


def _load_candles_cached(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    limit: int,
    cache_provider: OhlcvCacheProvider,
) -> Any:
    def _loader(target_symbol: str, target_timeframe: str, target_limit: int) -> list[dict[str, Any]]:
        raw_records = _load_candles(
            conn=conn,
            symbol=target_symbol,
            timeframe=target_timeframe,
            limit=target_limit,
        ).to_dict(orient="records")
        return cast(list[dict[str, Any]], raw_records)

    key = build_cache_key(symbol=symbol, timeframe=timeframe, limit=limit)
    result = cache_provider.get_many([(symbol, timeframe, limit)], _loader)[key]
    if not result.candles:
        return pd.DataFrame()
    candles_df = pd.DataFrame(result.candles)
    if "timestamp" in candles_df.columns:
        candles_df = candles_df.sort_values("timestamp").reset_index(drop=True)
    return candles_df


def _load_indicators(conn: sqlite3.Connection, symbol: str, timeframe: str, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT *
        FROM indicadores_tecnico
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (symbol, timeframe, limit),
    ).fetchall()
    if not rows:
        return []
    return [dict(row) for row in reversed(rows)]


def _ensure_model2_schema(conn: sqlite3.Connection) -> None:
    required_tables = {"schema_migrations", "opportunities", "opportunity_events"}
    found_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = sorted(required_tables - found_tables)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Model2 schema is missing required tables: "
            f"{joined}. Run 'python scripts/model2/migrate.py up' first."
        )


def run_scan(
    source_db_path: str | Path,
    model2_db_path: str | Path,
    symbols: list[str],
    timeframe: str,
    candles_limit: int,
    dry_run: bool,
    output_dir: str | Path,
    cache_provider: OhlcvCacheProvider | None = None,
) -> dict[str, Any]:
    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_model2_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)

    if timeframe not in TIMEFRAME_TO_TABLE:
        raise ValueError(f"Unsupported timeframe {timeframe}. Supported: {sorted(TIMEFRAME_TO_TABLE)}")

    with sqlite3.connect(resolved_model2_db) as model2_conn:
        _ensure_model2_schema(model2_conn)

    source_conn = sqlite3.connect(resolved_source_db)
    source_conn.row_factory = sqlite3.Row
    repository = Model2ThesisRepository(str(resolved_model2_db))

    scanned = 0
    detected = 0
    persisted = 0
    items: list[dict[str, Any]] = []
    model_first_symbols = {str(symbol).strip().upper() for symbol in M2_MODEL_FIRST_SCAN_SYMBOLS}
    model_first_service = ModelInferenceService(
        provider=TechnicalSignalInferenceProvider(model_first=True)
    ) if model_first_symbols else None

    try:
        for symbol in symbols:
            scanned += 1
            entry: dict[str, Any] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "NO_DETECTION",
            }

            candles_df = _load_candles(
                conn=source_conn,
                symbol=symbol,
                timeframe=timeframe,
                limit=candles_limit,
            ) if cache_provider is None else _load_candles_cached(
                conn=source_conn,
                symbol=symbol,
                timeframe=timeframe,
                limit=candles_limit,
                cache_provider=cache_provider,
            )
            if candles_df.empty:
                entry["status"] = "SKIPPED_NO_CANDLES"
                items.append(entry)
                continue

            # Registra metadados de candles para operator_cycle_status
            entry["candles_count"] = len(candles_df)
            if "timestamp" in candles_df.columns and len(candles_df) > 0:
                last_ts = candles_df.iloc[-1]["timestamp"]
                try:
                    entry["last_candle_time"] = ts_ms_to_brt_str(int(last_ts))
                except Exception:
                    entry["last_candle_time"] = str(last_ts)

            indicators = _load_indicators(
                conn=source_conn,
                symbol=symbol,
                timeframe=timeframe,
                limit=candles_limit,
            )
            smc = SmartMoneyConcepts.calculate_all_smc(candles_df)
            scan_timestamp = _utc_now_ms()

            if symbol.upper() in model_first_symbols and model_first_service is not None:
                confidence_threshold = _resolve_model_first_confidence_threshold(symbol)
                result = _detect_model_first_opportunity(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles_df=candles_df,
                    indicators=indicators,
                    smc=smc,
                    scan_timestamp=scan_timestamp,
                    inference_service=model_first_service,
                    confidence_threshold=confidence_threshold,
                )
                entry["model_first_confidence_threshold"] = confidence_threshold
            else:
                detector_input = DetectorInput(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles_df.to_dict(orient="records"),
                    indicators=indicators,
                    smc=smc,
                    scan_timestamp=scan_timestamp,
                )
                result = detect_initial_short_failure(detector_input)

            if result is None:
                items.append(entry)
                continue

            detected += 1
            is_model_first_result = str(result.rule_id) == M2_020_2_SCAN_RULE_ID
            entry["status"] = "DETECTED_MODEL_FIRST" if is_model_first_result else "DETECTED"
            entry["thesis_type"] = result.thesis_type
            entry["side"] = result.side
            entry["trigger_price"] = result.trigger_price
            entry["invalidation_price"] = result.invalidation_price
            if is_model_first_result:
                model_decision = dict(result.metadata.get("model_decision") or {})
                entry["decision_source"] = "rl_model_first"
                entry["decision_confidence"] = model_decision.get("confidence")
                entry["decision_reason"] = model_decision.get("reason_code")
            if not dry_run:
                save_result = repository.create_initial_thesis(result, now_ms=_utc_now_ms())
                if save_result.created_now:
                    persisted += 1
                    entry["status"] = "PERSISTED_MODEL_FIRST" if is_model_first_result else "PERSISTED"
                else:
                    entry["status"] = "IDEMPOTENT_MODEL_FIRST" if is_model_first_result else "IDEMPOTENT_HIT"
                entry["opportunity_id"] = save_result.opportunity_id

                if is_model_first_result:
                    monitoring_result = repository.transition_to_monitoring(
                        opportunity_id=save_result.opportunity_id,
                        now_ms=_utc_now_ms(),
                        rule_id=M2_020_2_SCAN_RULE_ID,
                    )
                    validation_result = repository.transition_to_validated(
                        opportunity_id=save_result.opportunity_id,
                        now_ms=_utc_now_ms(),
                        rule_id=M2_020_2_SCAN_RULE_ID,
                        payload={
                            "source": "rl_model_first_scan",
                            "side": result.side,
                            "confidence": (result.metadata.get("model_decision") or {}).get("confidence"),
                        },
                    )
                    entry["monitoring_reason"] = monitoring_result.reason
                    entry["validation_reason"] = validation_result.reason
                    if validation_result.current_status == "VALIDADA":
                        entry["status"] = (
                            "PERSISTED_MODEL_FIRST_VALIDATED"
                            if save_result.created_now
                            else "IDEMPOTENT_MODEL_FIRST_VALIDATED"
                        )

            items.append(entry)
    finally:
        source_conn.close()

    # Indice por simbolo usado pelo operator_cycle_status
    symbols_index: dict[str, dict[str, Any]] = {}
    for item in items:
        sym = str(item.get("symbol") or "").upper()
        if sym:
            symbols_index[sym] = {
                "candles_count": int(item.get("candles_count", 0)),
                "last_candle_time": str(item.get("last_candle_time", "")),
                "status": item.get("status", ""),
            }

    summary = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "model2_db_path": str(resolved_model2_db),
        "timeframe": timeframe,
        "dry_run": dry_run,
        "symbols_scanned": scanned,
        "detections": detected,
        "persisted_now": persisted,
        "items": items,
        "symbols": symbols_index,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"model2_scan_{run_id}.json"
    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 opportunity scanner")
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Input SQLite with OHLCV/indicators (legacy analytics DB)",
    )
    parser.add_argument(
        "--model2-db-path",
        default=MODEL2_DB_PATH,
        help="Target Model 2.0 SQLite path (opportunities/events)",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol to scan. Repeat to pass multiple values. Defaults to M2_SYMBOLS.",
    )
    parser.add_argument(
        "--timeframe",
        default="H4",
        choices=sorted(TIMEFRAME_TO_TABLE.keys()),
        help="Decision timeframe for the pattern detector.",
    )
    parser.add_argument(
        "--candles-limit",
        type=int,
        default=120,
        help="Number of latest candles loaded per symbol.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detection without persisting opportunities/events.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used for scanner run summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    symbols = args.symbol or list(M2_SYMBOLS)
    summary = run_scan(
        source_db_path=args.source_db_path,
        model2_db_path=args.model2_db_path,
        symbols=symbols,
        timeframe=args.timeframe,
        candles_limit=args.candles_limit,
        dry_run=bool(args.dry_run),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

