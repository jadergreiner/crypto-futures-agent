"""Resumo operacional por simbolo para cada ciclo M2."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera resumo por simbolo a partir dos artefatos do ciclo M2"
    )
    parser.add_argument(
        "--runtime-dir",
        default="results/model2/runtime",
        help="Diretorio com artefatos JSON dos scripts model2.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Simbolo monitorado. Repita a flag para varios simbolos.",
    )
    parser.add_argument(
        "--max-age-minutes",
        type=int,
        default=20,
        help="Idade maxima (min) aceita para considerar artefatos do ciclo.",
    )
    return parser.parse_args()


def _load_latest_json(runtime_dir: Path, prefix: str, max_age_seconds: int) -> dict[str, Any] | None:
    files = sorted(runtime_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None

    newest = files[0]
    file_age_seconds = (datetime.now(timezone.utc).timestamp() - newest.stat().st_mtime)
    if file_age_seconds > max_age_seconds:
        return None

    try:
        return json.loads(newest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _find_scan_item(scan_summary: dict[str, Any] | None, symbol: str) -> dict[str, Any] | None:
    if not scan_summary:
        return None
    items = scan_summary.get("items") or []
    for item in items:
        if str(item.get("symbol") or "").upper() == symbol:
            return item
    return None


def _count_stage_status(
    stage_summary: dict[str, Any] | None,
    *,
    symbol: str,
    status_key: str = "status",
) -> Counter[str]:
    counter: Counter[str] = Counter()
    if not stage_summary:
        return counter
    items = stage_summary.get("items") or []
    for item in items:
        if str(item.get("symbol") or "").upper() != symbol:
            continue
        raw_status = str(item.get(status_key) or "SEM_STATUS").strip().upper()
        counter[raw_status] += 1
    return counter


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "sem_eventos"
    parts = [f"{status}:{counter[status]}" for status in sorted(counter.keys())]
    return ",".join(parts)


def _format_counter_operacional(counter: Counter[str], labels: dict[str, str]) -> str:
    if not counter:
        return "sem eventos"
    parts: list[str] = []
    for status in sorted(counter.keys()):
        nome = labels.get(status, status.lower())
        parts.append(f"{nome}={counter[status]}")
    return ", ".join(parts)


def _build_stage_checklist_text(
    *,
    stage_name: str,
    counter: Counter[str],
    labels: dict[str, str],
) -> str:
    if not counter:
        return f"{stage_name}: sem eventos"
    return f"{stage_name}: {_format_counter_operacional(counter, labels)}"


def _is_risk_block_reason(reason: str) -> bool:
    texto = (reason or "").lower()
    termos_risco = (
        "risk",
        "cooldown",
        "daily",
        "funding",
        "margin",
        "max_signal_age",
        "short_only",
        "symbol_not_allowed",
        "liquid",
        "leverage",
    )
    return any(t in texto for t in termos_risco)


def _humanize_execute_reason(reason: str) -> str:
    reason_norm = (reason or "").strip().lower()
    if not reason_norm:
        return "motivo nao informado"

    reason_map = {
        "already_exists": "entrada ignorada: sinal ja processado",
        "symbol_cooldown_active": "entrada bloqueada: cooldown ativo",
        "risk_gate_rejected": "entrada bloqueada por risco (risk gate)",
        "max_daily_entries_reached": "entrada bloqueada: limite diario atingido",
        "margin_limit_exceeded": "entrada bloqueada por risco: margem acima do limite",
        "signal_too_old": "entrada bloqueada: sinal expirado",
        "short_only_enforced": "entrada bloqueada: modo short-only",
        "symbol_not_allowed": "entrada bloqueada: simbolo fora da lista live",
        "funding_rate_above_threshold": "entrada bloqueada por risco: funding acima do limite",
        "insufficient_balance": "entrada bloqueada por risco: saldo insuficiente",
        "exchange_error": "entrada bloqueada: falha de exchange",
        "invalid_signal": "entrada ignorada: sinal invalido",
    }
    if reason_norm in reason_map:
        return reason_map[reason_norm]

    if "cooldown" in reason_norm:
        return "entrada bloqueada: cooldown ativo"
    if "risk" in reason_norm and "gate" in reason_norm:
        return "entrada bloqueada por risco (risk gate)"
    if "risk" in reason_norm:
        return "entrada bloqueada por risco"
    if "already" in reason_norm and "exist" in reason_norm:
        return "entrada ignorada: sinal ja processado"

    return f"entrada bloqueada: {reason_norm}"


def _scan_status_text(scan_item: dict[str, Any] | None) -> tuple[str, str]:
    if not scan_item:
        return "desconhecido", "sem_registro"

    scan_status = str(scan_item.get("status") or "SEM_STATUS").upper()
    if scan_status == "SKIPPED_NO_CANDLES":
        candles_status = "nao"
    else:
        candles_status = "ok"
    return candles_status, scan_status


def _build_symbol_line(
    *,
    symbol: str,
    scan_summary: dict[str, Any] | None,
    track_summary: dict[str, Any] | None,
    validate_summary: dict[str, Any] | None,
    resolve_summary: dict[str, Any] | None,
    live_execute_summary: dict[str, Any] | None,
) -> str:
    scan_item = _find_scan_item(scan_summary, symbol)
    candles_status, scan_status = _scan_status_text(scan_item)

    track_counts = _count_stage_status(track_summary, symbol=symbol)
    validate_counts = _count_stage_status(validate_summary, symbol=symbol)
    resolve_counts = _count_stage_status(resolve_summary, symbol=symbol)

    execute_staged_counts: Counter[str] = Counter()
    execute_reason_counts: Counter[str] = Counter()
    if live_execute_summary:
        for item in live_execute_summary.get("staged") or []:
            if str(item.get("symbol") or "").upper() != symbol:
                continue
            status = str(item.get("status") or "SEM_STATUS").strip().upper()
            execute_staged_counts[status] += 1
            reason = str(item.get("reason") or "").strip()
            if reason:
                execute_reason_counts[reason] += 1

    scan_labels = {
        "PERSISTED": "tese registrada",
        "DETECTED": "tese detectada",
        "IDEMPOTENT_HIT": "ja registrada",
        "NO_DETECTION": "sem tese",
        "SKIPPED_NO_CANDLES": "sem candles",
        "SEM_REGISTRO": "sem registro no ciclo atual",
        "SEM_STATUS": "sem status no ciclo atual",
    }
    track_labels = {
        "TRANSITIONED": "monitoramento iniciado",
        "DRY_RUN_READY": "pronto (dry-run)",
        "SKIPPED": "nao transicionou",
        "SKIPPED_SHORT_ONLY": "bloqueado short-only",
    }
    validate_labels = {
        "VALIDATED": "validada",
        "NOT_VALIDATED": "avaliada sem validar",
        "DRY_RUN_VALIDATED": "validada (dry-run)",
        "SKIPPED": "nao transicionou",
        "SKIPPED_UNSUPPORTED_TIMEFRAME": "timeframe nao suportado",
    }
    resolve_labels = {
        "INVALIDATED": "invalidada",
        "EXPIRED": "expirada",
        "NO_RESOLUTION": "sem resolucao",
        "DRY_RUN_INVALIDATED": "invalidada (dry-run)",
        "DRY_RUN_EXPIRED": "expirada (dry-run)",
        "SKIPPED": "nao transicionou",
        "SKIPPED_UNSUPPORTED_TIMEFRAME": "timeframe nao suportado",
    }

    candles_operacional = {
        "ok": "candles capturados",
        "nao": "candles nao capturados",
        "desconhecido": "captura de candles sem registro",
    }.get(candles_status, "captura de candles sem registro")

    scan_status_norm = (scan_status or "").upper()

    if scan_status_norm == "SKIPPED_NO_CANDLES":
        modelo_avaliou = "nao"
    elif scan_status_norm in {"SEM_STATUS", "SEM_REGISTRO"}:
        modelo_avaliou = "desconhecido"
    else:
        modelo_avaliou = "sim"

    if not execute_staged_counts:
        entrada_operacional = "entrada sem sinal consumido"
    elif execute_staged_counts.get("READY", 0) > 0 and execute_staged_counts.get("FAILED", 0) == 0:
        entrada_operacional = f"entrada liberada para execucao ({execute_staged_counts.get('READY', 0)})"
    elif execute_staged_counts.get("FAILED", 0) > 0:
        principal_reason = execute_reason_counts.most_common(1)[0][0] if execute_reason_counts else "motivo_indefinido"
        reason_human = _humanize_execute_reason(principal_reason)
        if _is_risk_block_reason(principal_reason) and "risco" not in reason_human:
            entrada_operacional = f"entrada bloqueada por risco ({reason_human})"
        else:
            entrada_operacional = reason_human
    else:
        entrada_operacional = f"entrada em processamento ({_format_counter(execute_staged_counts)})"

    scanner_operacional = scan_labels.get(scan_status_norm, scan_status.lower().replace("_", " "))
    scanner_checklist = f"scanner: {scanner_operacional}"
    track_checklist = _build_stage_checklist_text(
        stage_name="track",
        counter=track_counts,
        labels=track_labels,
    )
    validacao_checklist = _build_stage_checklist_text(
        stage_name="validacao",
        counter=validate_counts,
        labels=validate_labels,
    )
    resolucao_checklist = _build_stage_checklist_text(
        stage_name="resolucao",
        counter=resolve_counts,
        labels=resolve_labels,
    )
    checklist = "; ".join(
        [
            scanner_checklist,
            track_checklist,
            validacao_checklist,
            resolucao_checklist,
        ]
    )

    return (
        f"{symbol} | {candles_operacional}. "
        f"Modelo avaliou: {modelo_avaliou}. "
        f"Checklist: {checklist}. "
        f"Execucao: {entrada_operacional}."
    )


def main() -> int:
    args = _parse_args()
    runtime_dir = Path(args.runtime_dir).resolve()
    symbols = [str(s).upper() for s in (args.symbol or []) if str(s).strip()]

    if not symbols:
        print("Nenhum simbolo informado para resumo operacional.")
        return 0

    if not runtime_dir.exists():
        print(f"Diretorio de runtime nao encontrado: {runtime_dir}")
        for symbol in symbols:
            print(f"{symbol} | status=sem_artefatos")
        return 0

    max_age_seconds = max(60, int(args.max_age_minutes) * 60)
    scan_summary = _load_latest_json(runtime_dir, "model2_scan", max_age_seconds)
    track_summary = _load_latest_json(runtime_dir, "model2_track", max_age_seconds)
    validate_summary = _load_latest_json(runtime_dir, "model2_validate", max_age_seconds)
    resolve_summary = _load_latest_json(runtime_dir, "model2_resolve", max_age_seconds)
    live_execute_summary = _load_latest_json(runtime_dir, "model2_live_execute", max_age_seconds)

    for symbol in symbols:
        line = _build_symbol_line(
            symbol=symbol,
            scan_summary=scan_summary,
            track_summary=track_summary,
            validate_summary=validate_summary,
            resolve_summary=resolve_summary,
            live_execute_summary=live_execute_summary,
        )
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
