"""Relatorio estruturado do ciclo M2 model-driven.

Centraliza coleta de metricas e formatacao da mensagem de status
por simbolo, aderente a arquitetura onde o modelo toma a decisao.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Literal, Optional, Sequence, TypedDict, cast

logger = logging.getLogger(__name__)

# Limite de episodios para disparo de retreino
RETRAIN_EPISODE_THRESHOLD = 100
DEFAULT_REPORT_FRESHNESS_WINDOW_MS = 7 * 24 * 60 * 60 * 1000


CandleState = Literal["fresh", "stale", "absent"]


class CandleFreshnessContract(TypedDict):
    """Contrato canonico de frescor de candle."""

    candle_state: CandleState
    freshness_reason: str
    display_time: str
    decision_fresh: bool


@dataclass
class SymbolReport:
    """Dados do ciclo para um simbolo."""

    symbol: str
    timeframe: str
    timestamp: str  # horario do ciclo

    # Candles
    candles_count: int = 0
    last_candle_time: str = ""
    candle_state: str = ""
    freshness_reason: str = ""

    # Decisao do modelo
    decision: str = "INDEFINIDA"
    confidence: float | None = 0.0
    decision_fresh: bool = False  # modelo usou dados atualizados?

    # Episodio/Reward
    episode_id: Optional[int] = None
    episode_persisted: bool = False
    reward: float = 0.0

    # Treinamento
    last_train_time: str = "nunca"
    pending_episodes: int = 0
    retrain_threshold: int = RETRAIN_EPISODE_THRESHOLD

    # Posicao na Binance
    has_position: bool = False
    position_side: str = ""        # LONG / SHORT
    position_qty: float = 0.0
    position_entry_price: float = 0.0
    position_mark_price: float = 0.0
    position_pnl_pct: float = 0.0
    position_pnl_usd: float = 0.0

    # Modo de execucao
    execution_mode: str = "shadow"

    # Circuit Breaker / Risk Gate — visibilidade para o operador
    circuit_breaker_state: str = ""
    circuit_breaker_drawdown_pct: float | None = None
    circuit_breaker_hours_remaining: float | None = None
    risk_gate_status: str = ""
    short_only_active: bool = False
    daily_entries_today: int = 0
    daily_entries_max: int = 0


def resolve_candle_freshness_contract(
    *,
    last_candle_time: str,
    signal_age_ms: int | None,
    max_signal_age_ms: int,
    now_utc: datetime | None = None,
) -> CandleFreshnessContract:
    """Resolve estado canonico de frescor de candle com fail-safe."""
    normalized_time = str(last_candle_time).strip()
    if not normalized_time:
        return {
            "candle_state": "absent",
            "freshness_reason": "missing_timestamp",
            "display_time": "N/A",
            "decision_fresh": False,
        }

    parsed_time = _parse_candle_timestamp(normalized_time)
    if parsed_time is None:
        return {
            "candle_state": "absent",
            "freshness_reason": "invalid_timestamp",
            "display_time": normalized_time,
            "decision_fresh": False,
        }

    age_ms = signal_age_ms
    if age_ms is None:
        current_time = now_utc or datetime.now(timezone.utc)
        age_ms = max(0, int((current_time - parsed_time).total_seconds() * 1000))

    if age_ms <= int(max_signal_age_ms):
        return {
            "candle_state": "fresh",
            "freshness_reason": "within_window",
            "display_time": normalized_time,
            "decision_fresh": True,
        }

    return {
        "candle_state": "stale",
        "freshness_reason": "outside_window",
        "display_time": normalized_time,
        "decision_fresh": False,
    }


def format_symbol_report(r: SymbolReport) -> str:
    """Formata relatorio de um simbolo em bloco legivel."""
    sep = "─" * 48
    icon = _decision_icon(r.decision)

    freshness = _resolve_report_freshness(r)

    # Linha de candles
    candle_info = (
        f"{r.candles_count} capturados"
        f" (ultimo: {r.last_candle_time or 'N/A'})"
    )
    fresh_tag = " ✓" if freshness["decision_fresh"] else " ⚠"
    candle_status = _format_candle_status(freshness)

    # Linha de decisao
    conf_str = f"{r.confidence:.0%}" if r.confidence is not None else "N/A"
    decision_line = f"{icon} {r.decision} (confianca: {conf_str})"

    # Linha de episodio/reward
    ep_label = f"#{r.episode_id}" if r.episode_id else "N/A"
    ep_status = "persistido" if r.episode_persisted else "nao persistido"
    reward_sign = "+" if r.reward >= 0 else ""
    episode_line = (
        f"{ep_label} {ep_status} | reward: {reward_sign}{r.reward:.4f}"
    )

    # Linha de treino
    pend = r.pending_episodes
    thresh = r.retrain_threshold
    pct_ready = pend / thresh if thresh > 0 else 0
    bar = _progress_bar(pct_ready, width=10)
    train_line = (
        f"ultimo: {r.last_train_time} | "
        f"pendentes: {pend}/{thresh} {bar}"
    )

    # Linha de posicao
    if r.has_position:
        pnl_sign = "+" if r.position_pnl_pct >= 0 else ""
        pnl_usd_sign = "+" if r.position_pnl_usd >= 0 else ""
        position_line = (
            f"{r.position_side} {r.position_qty} "
            f"@ {r.position_entry_price:.2f} | "
            f"PnL: {pnl_sign}{r.position_pnl_pct:.2f}% "
            f"({pnl_usd_sign}${r.position_pnl_usd:.2f})"
        )
    else:
        position_line = "SEM POSICAO"

    # Modo
    mode_tag = (
        f"[{r.execution_mode.upper()}]"
        if r.execution_mode != "live"
        else "[LIVE]"
    )

    # Linha de Risk (CB + risk gate)
    risk_parts: list[str] = []
    cb_state = r.circuit_breaker_state or ""
    if cb_state in ("trancado", "open"):
        dd_str = (
            f"{r.circuit_breaker_drawdown_pct:.2f}%"
            if r.circuit_breaker_drawdown_pct is not None
            else "N/A"
        )
        risk_parts.append(f"[CB TRANCADO] drawdown={dd_str}")
    elif cb_state in ("half_open",):
        risk_parts.append("[CB HALF_OPEN]")
    elif cb_state:
        risk_parts.append(f"CB={cb_state}")
    if r.short_only_active:
        risk_parts.append("[LONG BLOQUEADO - short_only]")
    if r.daily_entries_max > 0:
        risk_parts.append(f"entradas hoje: {r.daily_entries_today}/{r.daily_entries_max}")
    risk_line = "  ".join(risk_parts) if risk_parts else "OK"

    lines = [
        sep,
        f"  {r.symbol} | {r.timeframe} | {r.timestamp} {mode_tag}",
        sep,
        f"  Candles  : {candle_info}{fresh_tag} | {candle_status}",
        f"  Decisao  : {decision_line}",
        f"  Episodio : {episode_line}",
        f"  Treino   : {train_line}",
        f"  Posicao  : {position_line}",
        f"  Risk     : {risk_line}",
        sep,
    ]
    return "\n".join(lines)


def format_cycle_summary(
    reports: Sequence[SymbolReport],
    cycle_number: int,
    next_cycle_time: str,
) -> str:
    """Formata resumo completo do ciclo com todos os simbolos."""
    now_sp = datetime.now(timezone.utc).astimezone(ZoneInfo("America/Sao_Paulo"))
    header = (
        f"\n{'=' * 48}\n"
        f"  CICLO #{cycle_number} | "
        f"{now_sp.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        f"{'=' * 48}"
    )

    body_parts = [header]
    for r in reports:
        body_parts.append(format_symbol_report(r))

    # Contadores globais
    total = len(reports)
    holds = sum(1 for r in reports if r.decision == "HOLD")
    opens = sum(
        1 for r in reports
        if r.decision in ("OPEN_LONG", "OPEN_SHORT")
    )
    positions = sum(1 for r in reports if r.has_position)
    total_pnl = sum(r.position_pnl_usd for r in reports if r.has_position)

    footer_lines = [
        f"  Resumo: {total} simbolos | "
        f"{opens} sinais | {holds} HOLD | "
        f"{positions} posicoes abertas",
    ]
    if positions > 0:
        pnl_sign = "+" if total_pnl >= 0 else ""
        footer_lines.append(
            f"  PnL total aberto: {pnl_sign}${total_pnl:.2f}"
        )
    footer_lines.append(
        f"  Proximo ciclo: {next_cycle_time}"
    )
    footer_lines.append("=" * 48)

    body_parts.append("\n".join(footer_lines))
    return "\n".join(body_parts)


def _resolve_report_freshness(r: SymbolReport) -> CandleFreshnessContract:
    explicit_state = str(getattr(r, "candle_state", "")).strip().lower()
    explicit_reason = str(getattr(r, "freshness_reason", "")).strip()
    if explicit_state in {"fresh", "stale", "absent"}:
        return {
            "candle_state": cast(CandleState, explicit_state),
            "freshness_reason": explicit_reason or "legacy_explicit_state",
            "display_time": r.last_candle_time or "N/A",
            "decision_fresh": explicit_state == "fresh",
        }

    if r.decision_fresh:
        return {
            "candle_state": "fresh",
            "freshness_reason": "legacy_decision_fresh",
            "display_time": r.last_candle_time or "N/A",
            "decision_fresh": True,
        }

    if str(r.last_candle_time).strip():
        return {
            "candle_state": "stale",
            "freshness_reason": "legacy_missing_contract",
            "display_time": r.last_candle_time,
            "decision_fresh": False,
        }

    return {
        "candle_state": "stale",
        "freshness_reason": "legacy_missing_contract",
        "display_time": "N/A",
        "decision_fresh": False,
    }


def _format_candle_status(freshness: CandleFreshnessContract) -> str:
    if freshness["candle_state"] == "fresh":
        return f"Candle Atualizado: {freshness['display_time']}"
    if freshness["candle_state"] == "stale":
        if freshness["display_time"] != "N/A":
            return f"stale: ultimo candle em {freshness['display_time']}"
        return "stale: sem candle atualizado"
    return "absent: sem candle utilizavel (stale)"


def _parse_candle_timestamp(raw_value: str) -> datetime | None:
    normalized = str(raw_value).strip()
    if not normalized:
        return None

    formats = (
        ("%Y-%m-%d %H:%M:%S UTC", timezone.utc),
        ("%Y-%m-%d %H:%M UTC", timezone.utc),
        ("%Y-%m-%d %H:%M:%S BRT", ZoneInfo("America/Sao_Paulo")),
        ("%Y-%m-%d %H:%M BRT", ZoneInfo("America/Sao_Paulo")),
        ("%Y-%m-%d %H:%M:%S", timezone.utc),
        ("%Y-%m-%d %H:%M", timezone.utc),
    )
    for fmt, tzinfo in formats:
        try:
            parsed = datetime.strptime(normalized, fmt).replace(tzinfo=tzinfo)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


# Helpers de coleta de dados


def collect_training_info(
    db_path: str,
) -> tuple[str, int]:
    """Retorna (data ultimo treino, episodios pendentes).

    Busca na tabela rl_training_log e rl_episodes.
    Fallback seguro se tabelas nao existirem.
    """
    last_train = "nunca"
    pending = 0
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        # Ultimo treinamento
        try:
            row = conn.execute(
                "SELECT MAX(completed_at) FROM rl_training_log"
            ).fetchone()
            if row and row[0]:
                last_train = row[0]
        except sqlite3.OperationalError:
            pass
        # Episodios com reward disponivel para treino (apos ultimo retreino)
        # Conta apenas episodios com reward_proxy preenchido (resultado real de trade)
        # que ainda nao foram consumidos em um ciclo de retreino.
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM training_episodes "
                "WHERE reward_proxy IS NOT NULL "
                "  AND UPPER(COALESCE(status, '')) NOT IN ('CYCLE_CONTEXT', 'PENDING') "
                "  AND created_at > COALESCE("
                "  (SELECT MAX(completed_at) FROM rl_training_log), "
                "  0)"
            ).fetchone()
            if row:
                pending = row[0]
        except sqlite3.OperationalError:
            pass
        conn.close()
    except Exception as exc:
        logger.warning("Falha ao coletar info de treino: %s", exc)
    return last_train, pending


def collect_position_info(
    symbol: str,
    exchange_client: object | None = None,
) -> dict[str, Any]:
    """Coleta posicao aberta na Binance para o simbolo.

    Retorna dict com campos do SymbolReport (position_*).
    """
    info: dict[str, Any] = {
        "has_position": False,
        "position_side": "",
        "position_qty": 0.0,
        "position_entry_price": 0.0,
        "position_mark_price": 0.0,
        "position_pnl_pct": 0.0,
        "position_pnl_usd": 0.0,
    }
    if exchange_client is None:
        return info
    try:
        positions = _fetch_positions(exchange_client, symbol)
        for pos in positions:
            qty = abs(float(pos.get("positionAmt", 0)))
            if qty <= 0:
                continue
            entry = float(pos.get("entryPrice", 0))
            mark = float(pos.get("markPrice", 0))
            unrealized = float(pos.get("unRealizedProfit", 0))
            side = "LONG" if float(pos.get("positionAmt", 0)) > 0 else "SHORT"
            pnl_pct = (
                ((mark - entry) / entry * 100) if entry > 0 else 0.0
            )
            if side == "SHORT":
                pnl_pct = -pnl_pct
            info = {
                "has_position": True,
                "position_side": side,
                "position_qty": qty,
                "position_entry_price": entry,
                "position_mark_price": mark,
                "position_pnl_pct": pnl_pct,
                "position_pnl_usd": unrealized,
            }
            break
    except Exception as exc:
        logger.warning(
            "Falha ao coletar posicao %s: %s", symbol, exc
        )
    return info


def _fetch_positions(
    client: object, symbol: str
) -> list[dict[str, Any]]:
    """Abstrai busca de posicoes em diferentes clientes."""
    # ccxt
    if hasattr(client, "fetch_positions"):
        raw = cast(list[dict[str, Any]], client.fetch_positions([symbol]))
        return [
            {
                "positionAmt": p.get("contracts", 0)
                * (1 if p.get("side") == "long" else -1),
                "entryPrice": p.get("entryPrice", 0),
                "markPrice": p.get("markPrice", 0),
                "unRealizedProfit": p.get("unrealizedPnl", 0),
            }
            for p in raw
        ]
    # binance-connector / client.futures_position_information
    if hasattr(client, "futures_position_information"):
        return cast(
            list[dict[str, Any]],
            client.futures_position_information(symbol=symbol),
        )
    # fallback: client generico com get_position
    if hasattr(client, "get_position"):
        return [cast(dict[str, Any], client.get_position(symbol))]
    return []


def _decision_icon(decision: str) -> str:
    """Icone visual para a decisao do modelo."""
    icons = {
        "OPEN_LONG": "🟢",
        "OPEN_SHORT": "🔴",
        "HOLD": "⏸",
        "REDUCE": "🟡",
        "CLOSE": "⛔",
    }
    return icons.get(decision, "❓")


def _progress_bar(pct: float, width: int = 10) -> str:
    """Barra de progresso simples."""
    filled = int(min(pct, 1.0) * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"
