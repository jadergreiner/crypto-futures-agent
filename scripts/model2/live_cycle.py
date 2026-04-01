"""Model 2.0 live operational cycle runner."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import (
    M2_CANARY_LEVERAGE,
    M2_EXECUTION_MODE,
    M2_FUNDING_RATE_MAX_FOR_SHORT,
    M2_LIVE_SYMBOLS,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SHORT_ONLY,
    M2_SYMBOL_COOLDOWN_MINUTES,
    MODEL2_DB_PATH,
)
from core.model2.dashboard_operational import query_operational_status
from scripts.model2.live_dashboard import run_live_dashboard
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _status_operacional(dashboard_summary: dict[str, Any]) -> str:
    unprotected = int(dashboard_summary.get("unprotected_filled_count") or 0)
    failed = int(dashboard_summary.get("failed_count") or 0)
    blocked = int(dashboard_summary.get("blocked_count") or 0)
    ready = int(dashboard_summary.get("ready_count") or 0)

    if unprotected > 0:
        return "ALERTA_CRITICO"
    if failed > 0:
        return "ALERTA"
    if ready > 0:
        return "ATENCAO"
    if blocked > 0:
        return "MONITORAR"
    return "ESTAVEL"


def _format_symbol_lines(
    *,
    live_symbols: list[str],
    execute_summary: dict[str, Any],
) -> list[str]:
    staged = execute_summary.get("staged", [])
    processed = execute_summary.get("processed_ready", [])

    staged_map = {
        str(item.get("symbol") or "").upper(): item
        for item in staged
        if isinstance(item, dict)
    }
    processed_map = {
        str(item.get("symbol") or "").upper(): item
        for item in processed
        if isinstance(item, dict)
    }

    lines: list[str] = []
    for symbol in live_symbols:
        normalized_symbol = str(symbol).upper()
        if normalized_symbol in processed_map:
            item = processed_map[normalized_symbol]
            status = str(item.get("status") or "PROCESSADO")
            lines.append(f"    - {normalized_symbol}: pronto processado ({status})")
            continue
        if normalized_symbol in staged_map:
            item = staged_map[normalized_symbol]
            status = str(item.get("status") or "STAGED")
            reason = str(item.get("reason") or "").strip()
            suffix = f" | motivo={reason}" if reason else ""
            lines.append(f"    - {normalized_symbol}: staged ({status}){suffix}")
            continue
        lines.append(f"    - {normalized_symbol}: sem oportunidade pronta nesta janela")
    return lines


def _build_filtered_metrics(
    *,
    model2_db_path: str | Path,
    symbols: list[str],
) -> dict[str, dict[str, Any]]:
    filtered: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        normalized_symbol = str(symbol).strip().upper()
        if not normalized_symbol:
            continue
        filtered[normalized_symbol] = query_operational_status(
            str(model2_db_path),
            symbol=normalized_symbol,
        )
    return filtered


def _format_filtered_metric_lines(
    filtered_metrics: dict[str, dict[str, Any]],
) -> list[str]:
    if not filtered_metrics:
        return ["    - sem filtro de simbolo aplicado"]

    lines: list[str] = []
    for symbol, metrics in filtered_metrics.items():
        lines.append(
            "    - "
            f"{symbol}: admitidas={int(metrics.get('execucoes_admitidas', 0) or 0)} | "
            f"bloqueadas={int(metrics.get('execucoes_bloqueadas', 0) or 0)} | "
            f"falhas={int(metrics.get('execucoes_falhas', 0) or 0)} | "
            f"oportunidades_ativas={int(metrics.get('oportunidades_ativas', 0) or 0)} | "
            f"reconciliation={metrics.get('reconciliation_status', 'UNKNOWN')}"
        )
    return lines


def run_live_cycle(
    *,
    model2_db_path: str | Path,
    symbol: str | None,
    timeframe: str | None,
    limit: int,
    output_dir: str | Path,
    execution_mode: str,
    live_symbols: tuple[str, ...],
    max_daily_entries: int,
    max_margin_per_position_usd: float,
    max_signal_age_minutes: int,
    symbol_cooldown_minutes: int,
    short_only: bool,
    funding_rate_max_for_short: float,
    leverage: int,
) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    execute_summary = run_live_execute(
        model2_db_path=model2_db_path,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        output_dir=output_dir,
        execution_mode=execution_mode,
        live_symbols=live_symbols,
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_minutes=max_signal_age_minutes,
        symbol_cooldown_minutes=symbol_cooldown_minutes,
        short_only=short_only,
        funding_rate_max_for_short=funding_rate_max_for_short,
        leverage=leverage,
    )
    reconcile_summary = run_live_reconcile(
        model2_db_path=model2_db_path,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        output_dir=output_dir,
        execution_mode=execution_mode,
        live_symbols=live_symbols,
        max_daily_entries=max_daily_entries,
        max_margin_per_position_usd=max_margin_per_position_usd,
        max_signal_age_minutes=max_signal_age_minutes,
        symbol_cooldown_minutes=symbol_cooldown_minutes,
        short_only=short_only,
        funding_rate_max_for_short=funding_rate_max_for_short,
        leverage=leverage,
    )
    dashboard_summary = run_live_dashboard(
        model2_db_path=model2_db_path,
        output_dir=output_dir,
        retention_days=30,
    )

    return {
        "status": "ok",
        "run_id": run_id,
        "execution_mode": execution_mode,
        "short_only": bool(short_only),
        "leverage": int(leverage),
        "funding_rate_max_for_short": float(funding_rate_max_for_short),
        "execute": execute_summary,
        "reconcile": reconcile_summary,
        "dashboard": dashboard_summary,
    }


def render_live_cycle_summary(
    run_id: str,
    execution_mode: str,
    summary: dict[str, Any],
    output_dir: str | Path,
    model2_db_path: str | Path,
) -> str:
    """Renderiza resumo textual orientado ao operador."""
    execute_summary = summary.get("execute", {})
    reconcile_summary = summary.get("reconcile", {})
    dashboard_summary = summary.get("dashboard", {})

    live_symbols = [str(symbol).upper() for symbol in execute_summary.get("live_symbols", [])]
    symbol_filter = execute_summary.get("filters", {}).get("symbol") or "todos"
    timeframe_filter = execute_summary.get("filters", {}).get("timeframe") or "todos"
    execute_output = execute_summary.get("output_file") or "N/A"
    reconcile_output = reconcile_summary.get("output_file") or "N/A"
    dashboard_output = dashboard_summary.get("output_file") or "N/A"

    staged_count = len(execute_summary.get("staged", []))
    processed_ready_count = len(execute_summary.get("processed_ready", []))
    reconciled_count = len(reconcile_summary.get("reconciled", []))

    ready_count = int(dashboard_summary.get("ready_count", 0) or 0)
    blocked_count = int(dashboard_summary.get("blocked_count", 0) or 0)
    failed_count = int(dashboard_summary.get("failed_count", 0) or 0)
    protected_count = int(dashboard_summary.get("protected_count", 0) or 0)
    exited_count = int(dashboard_summary.get("exited_count", 0) or 0)
    unprotected_count = int(dashboard_summary.get("unprotected_filled_count", 0) or 0)
    entry_sent_count = int(dashboard_summary.get("entry_sent_count", 0) or 0)
    entry_filled_count = int(dashboard_summary.get("entry_filled_count", 0) or 0)

    status_operacional = _status_operacional(dashboard_summary)
    symbol_lines = _format_symbol_lines(
        live_symbols=live_symbols,
        execute_summary=execute_summary,
    )
    filtered_metrics = _build_filtered_metrics(
        model2_db_path=model2_db_path,
        symbols=live_symbols if live_symbols else ([str(symbol_filter)] if symbol_filter != "todos" else []),
    )
    filtered_metric_lines = _format_filtered_metric_lines(filtered_metrics)

    alertas: list[str] = []
    if unprotected_count > 0:
        alertas.append(f"unprotected_filled={unprotected_count}")
    if failed_count > 0:
        alertas.append(f"failed={failed_count}")
    if blocked_count > 0:
        alertas.append(f"blocked={blocked_count}")
    if not alertas:
        alertas.append("nenhum alerta critico no snapshot")

    lines = [
        "=" * 64,
        f"LIVE CYCLE | run_id={run_id} | modo={execution_mode}",
        "=" * 64,
        f"STATUS OPERACIONAL: {status_operacional}",
        f"ESCOPO: symbol={symbol_filter} | timeframe={timeframe_filter}",
        f"UNIVERSO ATIVO: {', '.join(live_symbols) if live_symbols else 'N/A'}",
        "",
        "EXECUCAO:",
        (
            f"  staged={staged_count} | ready_processado={processed_ready_count} | "
            f"reconciled={reconciled_count}"
        ),
        (
            f"  entry_sent={entry_sent_count} | entry_filled={entry_filled_count} | "
            f"protected={protected_count} | exited={exited_count}"
        ),
        "",
        "DASHBOARD GLOBAL:",
        f"  ready={ready_count} | blocked={blocked_count} | failed={failed_count}",
        f"  unprotected_filled={unprotected_count}",
        f"  alertas={'; '.join(alertas)}",
        "",
        "METRICAS FILTRADAS DO ESCOPO:",
        *filtered_metric_lines,
        "",
        "SITUACAO POR SIMBOLO:",
        *symbol_lines,
        "",
        "ARTEFATOS:",
        f"  execute={execute_output}",
        f"  reconcile={reconcile_output}",
        f"  dashboard={dashboard_output}",
        f"  output_dir={Path(output_dir)}",
        "=" * 64,
    ]
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 live cycle runner")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--execution-mode", default=M2_EXECUTION_MODE)
    parser.add_argument("--live-symbol", action="append", default=[])
    parser.add_argument("--max-daily-entries", type=int, default=M2_MAX_DAILY_ENTRIES)
    parser.add_argument("--max-margin-per-position-usd", type=float, default=M2_MAX_MARGIN_PER_POSITION_USD)
    parser.add_argument("--max-signal-age-minutes", type=int, default=M2_MAX_SIGNAL_AGE_MINUTES)
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=M2_SYMBOL_COOLDOWN_MINUTES)
    parser.add_argument("--short-only", action="store_true", default=M2_SHORT_ONLY)
    parser.add_argument("--funding-rate-max-for-short", type=float, default=M2_FUNDING_RATE_MAX_FOR_SHORT)
    parser.add_argument("--leverage", type=int, default=M2_CANARY_LEVERAGE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    live_symbols = tuple(symbol.upper() for symbol in (args.live_symbol or M2_LIVE_SYMBOLS) if symbol)
    try:
        summary = run_live_cycle(
            model2_db_path=args.model2_db_path,
            symbol=args.symbol,
            timeframe=args.timeframe,
            limit=int(args.limit),
            output_dir=args.output_dir,
            execution_mode=args.execution_mode,
            live_symbols=live_symbols,
            max_daily_entries=int(args.max_daily_entries),
            max_margin_per_position_usd=float(args.max_margin_per_position_usd),
            max_signal_age_minutes=int(args.max_signal_age_minutes),
            symbol_cooldown_minutes=int(args.symbol_cooldown_minutes),
            short_only=bool(args.short_only),
            funding_rate_max_for_short=float(args.funding_rate_max_for_short),
            leverage=int(args.leverage),
        )
        # Renderizar summary estruturado
        structured_output = render_live_cycle_summary(
            run_id=summary.get("run_id", ""),
            execution_mode=summary.get("execution_mode", ""),
            summary=summary,
            output_dir=args.output_dir,
            model2_db_path=args.model2_db_path,
        )
        if structured_output:
            print(structured_output, flush=True)
    except Exception as exc:
        tb = traceback.format_exc()
        summary = {
            "status": "error",
            "error": str(exc),
            "traceback": tb,
        }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
