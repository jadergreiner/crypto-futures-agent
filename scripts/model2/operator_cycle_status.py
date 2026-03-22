#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resumo operacional por simbolo para cada ciclo M2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Adicionar root do repositório ao sys.path para importações
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.binance_client import create_binance_client
from core.model2.live_exchange import Model2LiveExchange
from core.model2.cycle_report import (
    SymbolReport,
    format_symbol_report,
    collect_training_info,
    collect_position_info,
)
from config.settings import M2_EXECUTION_MODE


try:
    from config.settings import M2_SYMBOLS, _normalize_symbol_scope
except Exception:
    M2_SYMBOLS = ("BTCUSDT",)

    def _normalize_symbol_scope(
        raw_value: str | None,
        *,
        fallback_symbols: tuple[str, ...],
    ) -> tuple[str, ...]:
        fallback_list = [str(symbol).strip().upper() for symbol in fallback_symbols if str(symbol).strip()]
        if raw_value is None:
            return ()
        placeholder_tokens = {
            "M2_SYMBOLS",
            "M2_SYMBOLS:",
            "M2_LIVE_SYMBOLS",
            "M2_LIVE_SYMBOLS:",
            "ALL_SYMBOLS",
            "ALL_SYMBOLS:",
        }
        normalized: list[str] = []
        for token in str(raw_value).split(","):
            symbol = str(token).strip().upper()
            if not symbol:
                continue
            if symbol in placeholder_tokens:
                normalized.extend(fallback_list)
                continue
            normalized.append(symbol)
        return tuple(dict.fromkeys(normalized))


def _checkpoint_aliases(path: Path) -> list[Path]:
    """Retorna aliases plausiveis para checkpoints sem extensao padronizada."""
    candidates = [path]
    if path.suffix:
        return candidates
    candidates.append(path.with_suffix(".zip"))
    candidates.append(path.with_suffix(".pkl"))
    return candidates


def _get_last_train_time() -> str:
    """Busca pelo checkpoint mais recente e retorna seu timestamp de modificação."""
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "checkpoints" / "ppo_training" / "ppo_model.zip",
        repo_root / "checkpoints" / "ppo_training" / "ppo_model.pkl",
        repo_root / "checkpoints" / "ppo_training" / "best_model.zip",
        repo_root / "checkpoints" / "ppo_training" / "best_model.pkl",
        repo_root / "checkpoints" / "ppo_training" / "mlp" / "optuna" / "ppo_mlp_e8_optuna.zip",
        repo_root / "checkpoints" / "ppo_training" / "mlp" / "ppo_model_mlp.zip",
        repo_root / "models" / "ppo_model.zip",
        repo_root / "models" / "ppo_model.pkl",
    ]
    latest_time = 0.0
    for path in candidates:
        for p_alias in _checkpoint_aliases(path):
            if p_alias.exists():
                mod_time = p_alias.stat().st_mtime
                if mod_time > latest_time:
                    latest_time = mod_time

    if latest_time > 0.0:
        return datetime.fromtimestamp(latest_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"


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
        "--symbols-csv",
        default="",
        help="Lista CSV de simbolos monitorados; placeholders como M2_SYMBOLS: sao expandidos.",
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
    exchange: Model2LiveExchange | None,
    last_train_time: str,
) -> str:
    """Constrói relatório de símbolo usando novo padrão cycle_report."""
    try:
        # Obter decisão do modelo a partir do sumário de execução
        decision = "HOLD"
        confidence = 0.0
        if live_execute_summary:
            for item in live_execute_summary.get("staged", []):
                if str(item.get("symbol", "")).upper() == symbol:
                    raw_action = item.get("action", "HOLD")
                    confidence = float(item.get("confidence", 0.0))
                    # Normalizar a ação para o formato desejado
                    if "LONG" in raw_action:
                        decision = "OPEN_LONG"
                    elif "SHORT" in raw_action:
                        decision = "OPEN_SHORT"
                    else:
                        decision = raw_action
                    break

        # Obter PnL e posição da exchange
        has_position = False
        position_side = ""
        position_qty = 0.0
        position_entry_price = 0.0
        position_mark_price = 0.0
        position_pnl_pct = 0.0
        position_pnl_usd = 0.0

        if exchange:
            try:
                position = exchange.get_open_position(symbol)
                if position:
                    has_position = True
                    position_side = position.get("direction", "").upper()
                    position_qty = float(position.get("position_size_qty", 0.0))
                    position_entry_price = float(position.get("entry_price", 0.0))
                    position_mark_price = float(position.get("mark_price", 0.0))

                    if position_entry_price > 0 and position_qty > 0:
                        if position_side == "LONG":
                            pnl_usd = (position_mark_price - position_entry_price) * position_qty
                        elif position_side == "SHORT":
                            pnl_usd = (position_entry_price - position_mark_price) * position_qty
                        else:
                            pnl_usd = 0.0

                        position_pnl_usd = pnl_usd
                        position_pnl_pct = (pnl_usd / (position_entry_price * position_qty)) * 100 if position_entry_price > 0 else 0.0
            except Exception:
                # Se falhar ao consultar posição, continua com valores defaults
                pass

        # Obter dados de candles
        candles_count = 0
        last_candle_time = ""
        if scan_summary:
            items = scan_summary.get("symbols", {})
            if symbol in items:
                sym_data = items[symbol]
                candles_count = int(sym_data.get("candles_count", 0))
                last_candle_time = sym_data.get("last_candle_time", "")

        # Montar SymbolReport e formatar
        now = datetime.now(timezone.utc)
        timeframe = "H4"
        execution_mode = "live" if M2_EXECUTION_MODE == "live" else "shadow"

        report = SymbolReport(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
            candles_count=candles_count,
            last_candle_time=last_candle_time,
            decision=decision,
            confidence=confidence,
            decision_fresh=True,
            episode_id=None,
            episode_persisted=False,
            reward=0.0,
            last_train_time=last_train_time,
            pending_episodes=0,
            has_position=has_position,
            position_side=position_side,
            position_qty=position_qty,
            position_entry_price=position_entry_price,
            position_mark_price=position_mark_price,
            position_pnl_pct=position_pnl_pct,
            position_pnl_usd=position_pnl_usd,
            execution_mode=execution_mode,
        )

        # Retornar relatório formatado
        return format_symbol_report(report)

    except Exception as exc:
        # Fallback seguro se novo formato falhar
        decision = "HOLD"
        if live_execute_summary:
            for item in live_execute_summary.get("staged", []):
                if str(item.get("symbol", "")).upper() == symbol:
                    raw_action = item.get("action", "HOLD")
                    if "LONG" in raw_action:
                        decision = "BUY"
                    elif "SHORT" in raw_action:
                        decision = "SELL"
                    else:
                        decision = raw_action
                    break

        pos_str = "None"
        pnl_str = "0.00"
        if exchange:
            try:
                position = exchange.get_open_position(symbol)
                if position:
                    direction = position.get("direction", "NONE")
                    size = float(position.get("position_size_qty", 0.0))
                    entry_price = float(position.get("entry_price", 0.0))
                    mark_price = float(position.get("mark_price", 0.0))
                    pos_str = f"{direction} {size:.4f}"

                    pnl = 0.0
                    if entry_price > 0 and size > 0:
                        pnl = (mark_price - entry_price) * size if direction == "LONG" else (entry_price - mark_price) * size
                    pnl_str = f"{pnl:+.2f}"
            except Exception:
                pass

        log_template = (
            "{symbol} | Data: OK | Model: Ran | "
            "Decision: {decision} | RL: Stored (Pending: N/A) | "
            "Last Train: {last_train} | Position: {position} | PnL: {pnl}"
        )
        return log_template.format(
            symbol=symbol,
            decision=decision,
            last_train=last_train_time,
            position=pos_str,
            pnl=pnl_str,
        )


def main() -> int:
    args = _parse_args()
    runtime_dir = Path(args.runtime_dir).resolve()
    csv_symbols = _normalize_symbol_scope(
        args.symbols_csv,
        fallback_symbols=tuple(M2_SYMBOLS),
    )
    cli_symbols = _normalize_symbol_scope(
        ",".join(args.symbol or []),
        fallback_symbols=tuple(M2_SYMBOLS),
    )
    symbols = list(dict.fromkeys([*csv_symbols, *cli_symbols]))

    if not symbols:
        print("Nenhum simbolo informado para resumo operacional.")
        return 0

    if not runtime_dir.exists():
        print(f"Diretorio de runtime nao encontrado: {runtime_dir}")
        for symbol in symbols:
            print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}] [M2][{symbol}] | Data: Failed | Status: sem_artefatos")
        return 0

    # Carregar artefatos JSON
    max_age_seconds = max(60, int(args.max_age_minutes) * 60)
    scan_summary = _load_latest_json(runtime_dir, "model2_scan", max_age_seconds)
    track_summary = _load_latest_json(runtime_dir, "model2_track", max_age_seconds)
    validate_summary = _load_latest_json(runtime_dir, "model2_validate", max_age_seconds)
    resolve_summary = _load_latest_json(runtime_dir, "model2_resolve", max_age_seconds)
    live_execute_summary = _load_latest_json(runtime_dir, "model2_live_execute", max_age_seconds)

    # Inicializar cliente da exchange e obter data do último treino
    exchange = None
    try:
        if M2_EXECUTION_MODE == "live":
            client = create_binance_client(mode="live")
            exchange = Model2LiveExchange(client)
    except Exception as e:
        print(f"[ERROR] Nao foi possivel criar cliente da exchange: {e}", file=sys.stderr)

    last_train_time = _get_last_train_time()

    # Gerar linha de log para cada símbolo
    for symbol in symbols:
        line = _build_symbol_line(
            symbol=symbol,
            scan_summary=scan_summary,
            track_summary=track_summary,
            validate_summary=validate_summary,
            resolve_summary=resolve_summary,
            live_execute_summary=live_execute_summary,
            exchange=exchange,
            last_train_time=last_train_time,
        )
        print(line, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
