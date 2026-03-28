#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resumo operacional por simbolo para cada ciclo M2."""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, cast

# Forçar UTF-8 no stdout para suportar emojis e caracteres Unicode no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adicionar root do repositório ao sys.path para importações
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.time_utils import now_brt_str, posix_to_brt_str
from core.model2.io_retry import read_json_with_retry
from core.model2.cycle_report import (
    DEFAULT_REPORT_FRESHNESS_WINDOW_MS,
    SymbolReport,
    collect_training_info,
    collect_training_info_for_symbol,
    format_symbol_report,
    resolve_candle_freshness_contract,
)
from core.model2.training_audit import summarize_training_audit_window
from config.settings import M2_EXECUTION_MODE

try:
    from data.binance_client import create_binance_client
    from core.model2.live_exchange import Model2LiveExchange
    _EXCHANGE_AVAILABLE = True
except Exception:
    _EXCHANGE_AVAILABLE = False

try:
    from config.settings import M2_SYMBOLS, _normalize_symbol_scope
except Exception:
    M2_SYMBOLS = ("BTCUSDT",)

    def _normalize_symbol_scope(
        raw_value: str | None,
        *,
        fallback_symbols: Iterable[str],
    ) -> tuple[str, ...]:
        fallback_list = [str(s).strip().upper() for s in fallback_symbols if str(s).strip()]
        if raw_value is None:
            return ()
        placeholder_tokens = {
            "M2_SYMBOLS", "M2_SYMBOLS:", "M2_LIVE_SYMBOLS", "M2_LIVE_SYMBOLS:",
            "ALL_SYMBOLS", "ALL_SYMBOLS:",
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


# ---------------------------------------------------------------------------
# Helpers de artefatos JSON
# ---------------------------------------------------------------------------

def _load_latest_json(runtime_dir: Path, prefix: str, max_age_seconds: int) -> dict[str, Any] | None:
    files = sorted(runtime_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    newest = files[0]
    age = (datetime.now(timezone.utc).timestamp() - newest.stat().st_mtime)
    if age > max_age_seconds:
        return None
    result = read_json_with_retry(str(newest), fail_safe=True)
    if not result or not isinstance(result, dict):
        return None
    return result


def _load_latest_json_by_timeframe(
    runtime_dir: Path, prefix: str, timeframe: str, max_age_seconds: int
) -> dict[str, Any] | None:
    """Carrega o JSON mais recente de um prefix filtrado pelo timeframe."""
    files = sorted(runtime_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        age = (datetime.now(timezone.utc).timestamp() - f.stat().st_mtime)
        if age > max_age_seconds:
            break  # Ordenados por mtime, os mais velhos não precisam ser checados
        result = read_json_with_retry(str(f), fail_safe=True)
        if not result or not isinstance(result, dict):
            continue
        if str(result.get("timeframe", "")).upper() == timeframe.upper():
            return result
    return None


# ---------------------------------------------------------------------------
# Helpers de checkpoint / último treino
# ---------------------------------------------------------------------------

def _checkpoint_aliases(path: Path) -> list[Path]:
    candidates = [path]
    if path.suffix:
        return candidates
    candidates.append(path.with_suffix(".zip"))
    candidates.append(path.with_suffix(".pkl"))
    return candidates


def _get_last_train_time_from_checkpoint() -> str:
    """Fallback: mtime do checkpoint mais recente."""
    candidates = [
        REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.pkl",
        REPO_ROOT / "checkpoints" / "ppo_training" / "best_model.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "best_model.pkl",
        REPO_ROOT / "checkpoints" / "ppo_training" / "mlp" / "optuna" / "ppo_mlp_e8_optuna.zip",
        REPO_ROOT / "checkpoints" / "ppo_training" / "mlp" / "ppo_model_mlp.zip",
        REPO_ROOT / "models" / "ppo_model.zip",
        REPO_ROOT / "models" / "ppo_model.pkl",
    ]
    latest_time = 0.0
    for path in candidates:
        for alias in _checkpoint_aliases(path):
            if alias.exists():
                t = alias.stat().st_mtime
                if t > latest_time:
                    latest_time = t
    return posix_to_brt_str(latest_time) if latest_time > 0.0 else "N/A"


# ---------------------------------------------------------------------------
# Helpers de DB
# ---------------------------------------------------------------------------

def _get_model2_db_path() -> str:
    return str(REPO_ROOT / "db" / "modelo2.db")


def _query_confidence_from_db(symbol: str, db_path: str) -> float | None:
    """Busca a confiança da decisão mais recente do modelo para o símbolo."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT confidence FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass
    return None


def _query_last_decision_from_db(symbol: str, db_path: str) -> tuple[str, float]:
    """Retorna (action, confidence) da decisão mais recente no DB."""
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT action, confidence FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row:
            action = str(row[0] or "HOLD")
            confidence = float(row[1]) if row[1] is not None else 0.0
            return action, confidence
    except Exception:
        pass
    return "HOLD", 0.0


def _query_risk_state_from_db(symbol: str, db_path: str) -> dict[str, Any] | None:
    """Extrai campos de risk_state do input_json da decisao mais recente.

    Retorna dict com os campos presentes em input_json, ou None se nao houver
    dados (DB inexistente, tabela ausente, symbol sem decisao).
    Nunca levanta excecao.
    """
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT input_json FROM model_decisions "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        raw = row[0]
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return None


def _query_episode_info(symbol: str, db_path: str) -> tuple[int | None, bool, float]:
    """Retorna (episode_id, persisted, reward) do ultimo episodio real do simbolo.

    Filtra episodios de contexto (CYCLE_CONTEXT) e pendentes sem reward.
    Exibe apenas episodios de execucao real com reward_proxy preenchido.
    """
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            row = conn.execute(
                "SELECT id, status, reward_proxy FROM training_episodes "
                "WHERE symbol = ? AND reward_proxy IS NOT NULL "
                "AND status NOT IN ('CYCLE_CONTEXT') "
                "AND (execution_id > 0 OR status = 'HOLD_DECISION') "
                "ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()
        if row:
            ep_id = int(row[0])
            persisted = str(row[1] or "").upper() not in ("", "PENDING", "CONTEXT", "CYCLE_CONTEXT")
            reward = float(row[2])
            return ep_id, persisted, reward
    except Exception:
        pass
    return None, False, 0.0


# ---------------------------------------------------------------------------
# Construção do relatório por símbolo
# ---------------------------------------------------------------------------

def _get_candle_info_for_timeframe(
    scan_summary: dict[str, Any] | None, symbol: str
) -> tuple[int, str]:
    """Extrai (candles_count, last_candle_time) do sumário de scan para um símbolo."""
    if not scan_summary:
        return 0, ""
    symbols_dict = scan_summary.get("symbols") or {}
    if isinstance(symbols_dict, dict):
        sym_data = symbols_dict.get(symbol) or {}
        if isinstance(sym_data, dict):
            return (
                int(sym_data.get("candles_count", 0)),
                str(sym_data.get("last_candle_time", "")),
            )
    # fallback: items lista
    items = scan_summary.get("items") or []
    for item in items:
        if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol:
            return (
                int(item.get("candles_count", 0)),
                str(item.get("last_candle_time", "")),
            )
    return 0, ""


def _build_symbol_report(
    *,
    symbol: str,
    scan_h4: dict[str, Any] | None,
    scan_h1: dict[str, Any] | None,
    live_execute_summary: dict[str, Any] | None,
    exchange: Any | None,
    last_train_time: str,
    pending_episodes: int,
    db_path: str,
) -> str:
    """Constrói bloco de status rico para um símbolo com H4 + H1."""
    from core.model2.time_utils import now_brt_str as _now_brt

    sep = "─" * 56
    mode_tag = f"[{M2_EXECUTION_MODE.upper()}]"

    # --- Candles H4 ---
    h4_count, h4_time = _get_candle_info_for_timeframe(scan_h4, symbol)
    # --- Candles H1 ---
    h1_count, h1_time = _get_candle_info_for_timeframe(scan_h1, symbol)

    def _fmt_candle(count: int, last_time: str, tf: str) -> str:
        if not last_time:
            return f"{tf}: stale/absent (sem dados)"
        contract = resolve_candle_freshness_contract(
            last_candle_time=last_time,
            signal_age_ms=None,
            max_signal_age_ms=DEFAULT_REPORT_FRESHNESS_WINDOW_MS,
        )
        state = contract["candle_state"]
        if state == "fresh":
            return f"{tf}: {last_time} ({count} candles) [Candle Atualizado ✓]"
        return f"{tf}: {last_time} ({count} candles) [{state}]"

    candles_line = "  ".join([
        _fmt_candle(h4_count, h4_time, "H4"),
        _fmt_candle(h1_count, h1_time, "H1"),
        "M5: N/A",  # M5 não é rodado no pipeline atual
    ])

    # --- Decisão e confiança ---
    # Prioridade: model_decisions DB > live_execute JSON
    action_db, confidence_db = _query_last_decision_from_db(symbol, db_path)
    decision = action_db
    confidence: float = confidence_db

    # Verificar se live_execute traz decisão mais recente
    if live_execute_summary:
        for item in live_execute_summary.get("staged", []):
            if str(item.get("symbol", "")).upper() == symbol:
                raw_action = str(item.get("action", "HOLD"))
                if "LONG" in raw_action:
                    decision = "OPEN_LONG"
                elif "SHORT" in raw_action:
                    decision = "OPEN_SHORT"
                else:
                    decision = raw_action
                break

    icons = {"OPEN_LONG": "🟢", "OPEN_SHORT": "🔴", "HOLD": "⏸", "REDUCE": "🟡", "CLOSE": "⛔"}
    icon = icons.get(decision, "❓")
    conf_str = f"{confidence:.0%}" if confidence else "N/A"
    decision_line = f"{icon} {decision} (confianca: {conf_str})"

    # --- Episódio / Reward ---
    ep_id, ep_persisted, reward = _query_episode_info(symbol, db_path)
    ep_label = f"#{ep_id}" if ep_id else "N/A"
    ep_status = "persistido" if ep_persisted else "nao persistido"
    reward_sign = "+" if reward >= 0 else ""
    episode_line = f"{ep_label} {ep_status} | reward: {reward_sign}{reward:.4f}"

    # --- Treino ---
    from core.model2.cycle_report import RETRAIN_EPISODE_THRESHOLD, _progress_bar
    thresh = RETRAIN_EPISODE_THRESHOLD
    pct = pending_episodes / thresh if thresh > 0 else 0.0
    bar = _progress_bar(pct, width=10)
    episodes_restantes = max(0, thresh - pending_episodes)
    train_line = (
        f"ultimo: {last_train_time} | "
        f"pendentes: {pending_episodes}/{thresh} {bar} "
        f"(faltam {episodes_restantes} para retreino)"
    )
    audit_train_line = "aud24h: started=0 | running_block=0 | conclusivo=nao"
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            summary = summarize_training_audit_window(
                conn,
                since_ms=now_ms - (24 * 60 * 60 * 1000),
            )
            audit_train_line = (
                f"aud24h: started={int(summary['started_events'])} | "
                f"running_block={int(summary['blocked_running_events'])} | "
                f"conclusivo={'sim' if bool(summary['conclusive']) else 'nao'}"
            )
    except Exception:
        pass

    # --- Risk State ---
    risk_state = _query_risk_state_from_db(symbol, db_path)

    def _build_risk_line(rs: dict[str, Any] | None, current_action: str) -> str:
        if rs is None:
            return "N/A"
        cb_state = str(rs.get("circuit_breaker_state", "N/A"))
        rg_status = str(rs.get("risk_gate_status", "N/A"))
        short_only = rs.get("short_only", False)
        recent = rs.get("recent_entries_today")
        max_daily = rs.get("max_daily_entries")

        parts: list[str] = [f"CB:{cb_state}", f"RG:{rg_status}"]

        if cb_state not in ("normal", "N/A"):
            parts.append("[CB TRANCADO]")

        if short_only:
            parts.append(f"short_only:{short_only}")
            if current_action == "OPEN_LONG":
                parts.append("[LONG BLOQUEADO - short_only]")

        if recent is not None and max_daily is not None:
            entry_str = f"entradas hoje: {recent}/{max_daily}"
            if int(recent) >= int(max_daily):
                entry_str += " [LIMITE ATINGIDO]"
            parts.append(entry_str)

        return " | ".join(parts)

    risk_line = _build_risk_line(risk_state, decision)

    # --- Posição Binance ---
    has_position = False
    position_line = "SEM POSICAO"
    if exchange:
        try:
            position = exchange.get_open_position(symbol)
            if position and float(position.get("position_size_qty", 0)) != 0:
                has_position = True
                direction = str(position.get("direction", "")).upper()
                qty = float(position.get("position_size_qty", 0))
                entry = float(position.get("entry_price", 0))
                mark = float(position.get("mark_price", 0))
                margin = float(position.get("initial_margin", position.get("margin", 0)))
                leverage = position.get("leverage", "N/A")

                if entry > 0 and qty > 0:
                    if direction == "LONG":
                        pnl_usd = (mark - entry) * qty
                    else:
                        pnl_usd = (entry - mark) * qty
                    pnl_pct = (pnl_usd / (entry * qty)) * 100 if entry > 0 else 0.0
                else:
                    pnl_usd = 0.0
                    pnl_pct = 0.0

                pnl_sign = "+" if pnl_pct >= 0 else ""
                usd_sign = "+" if pnl_usd >= 0 else ""
                position_line = (
                    f"{direction} {qty} @ {entry:.4f} | mark: {mark:.4f} | "
                    f"margem: ${margin:.2f} | alavancagem: {leverage}x | "
                    f"PnL: {pnl_sign}{pnl_pct:.2f}% ({usd_sign}${pnl_usd:.2f})"
                )
        except Exception:
            pass

    lines = [
        sep,
        f"  {symbol} | {_now_brt()} {mode_tag}",
        sep,
        f"  Candles  : {candles_line}",
        f"  Decisao  : {decision_line}",
        f"  Episodio : {episode_line}",
        f"  Treino   : {train_line} | {audit_train_line}",
        f"  Posicao  : {position_line}",
        f"  Risk     : {risk_line}",
        sep,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alias de compatibilidade com testes legados
# ---------------------------------------------------------------------------

def _build_symbol_line(
    *,
    symbol: str,
    scan_summary: dict[str, Any] | None,
    track_summary: dict[str, Any] | None,
    validate_summary: dict[str, Any] | None,
    resolve_summary: dict[str, Any] | None,
    live_execute_summary: dict[str, Any] | None,
    exchange: Any | None,
    last_train_time: str,
) -> str:
    """Compatibilidade: mapeia interface legada para _build_symbol_report."""
    return _build_symbol_report(
        symbol=symbol,
        scan_h4=scan_summary,
        scan_h1=scan_summary,
        live_execute_summary=live_execute_summary,
        exchange=exchange,
        last_train_time=last_train_time,
        pending_episodes=0,
        db_path=_get_model2_db_path(),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera resumo por simbolo a partir dos artefatos do ciclo M2"
    )
    parser.add_argument("--runtime-dir", default="results/model2/runtime")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--symbols-csv", default="")
    parser.add_argument("--max-age-minutes", type=int, default=60)
    parser.add_argument(
        "--training-timeframe",
        default="H4",
        choices=["D1", "H4", "H1", "M5", "ALL"],
        help="Timeframe usado para contagem de pendencias de retreino (ALL = todos).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runtime_dir = Path(args.runtime_dir).resolve()
    csv_symbols = _normalize_symbol_scope(args.symbols_csv, fallback_symbols=tuple(M2_SYMBOLS))
    cli_symbols = _normalize_symbol_scope(",".join(args.symbol or []), fallback_symbols=tuple(M2_SYMBOLS))
    symbols = list(dict.fromkeys([*csv_symbols, *cli_symbols]))

    if not symbols:
        print("Nenhum simbolo informado para resumo operacional.")
        return 0

    if not runtime_dir.exists():
        print(f"Diretorio de runtime nao encontrado: {runtime_dir}")
        for sym in symbols:
            print(f"[{now_brt_str()}] [M2][{sym}] | Status: sem_artefatos")
        return 0

    max_age_seconds = max(60, int(args.max_age_minutes) * 60)

    # Carregar artefatos por timeframe
    scan_h4 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "H4", max_age_seconds)
    scan_h1 = _load_latest_json_by_timeframe(runtime_dir, "model2_scan", "H1", max_age_seconds)
    live_execute_summary = _load_latest_json(runtime_dir, "model2_live_execute", max_age_seconds)

    # DB path
    db_path = _get_model2_db_path()

    # Treino (global): fallback para simbolos sem log dedicado
    training_timeframe = None if str(args.training_timeframe).upper() == "ALL" else str(args.training_timeframe).upper()
    global_last_train_time, global_pending_episodes = collect_training_info(
        db_path,
        timeframe=training_timeframe,
    )
    if global_last_train_time == "nunca":
        global_last_train_time = _get_last_train_time_from_checkpoint()

    # Exchange (todos os modos — para posições reais na Binance)
    exchange = None
    if _EXCHANGE_AVAILABLE:
        try:
            client = create_binance_client(mode="live")
            exchange = Model2LiveExchange(client)
        except Exception as e:
            print(f"[WARN] Exchange nao disponivel: {e}", file=sys.stderr)

    for symbol in symbols:
        symbol_last_train, symbol_pending = collect_training_info_for_symbol(
            db_path,
            symbol=symbol,
            timeframe=training_timeframe,
        )
        if symbol_last_train == "nunca":
            symbol_last_train = global_last_train_time
            symbol_pending = global_pending_episodes

        line = _build_symbol_report(
            symbol=symbol,
            scan_h4=scan_h4,
            scan_h1=scan_h1,
            live_execute_summary=live_execute_summary,
            exchange=exchange,
            last_train_time=symbol_last_train,
            pending_episodes=symbol_pending,
            db_path=db_path,
        )
        print(line, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
