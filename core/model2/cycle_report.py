"""Relatorio estruturado do ciclo M2 model-driven.

Centraliza coleta de metricas e formatacao da mensagem de status
por simbolo, aderente a arquitetura onde o modelo toma a decisao.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Optional, Sequence, cast

logger = logging.getLogger(__name__)

# Limite de episodios para disparo de retreino
RETRAIN_EPISODE_THRESHOLD = 100


@dataclass
class SymbolReport:
    """Dados do ciclo para um simbolo."""

    symbol: str
    timeframe: str
    timestamp: str  # horario do ciclo

    # Candles
    candles_count: int = 0
    last_candle_time: str = ""

    # Decisao do modelo
    decision: str = "INDEFINIDA"
    confidence: float = 0.0
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


def format_symbol_report(r: SymbolReport) -> str:
    """Formata relatorio de um simbolo em bloco legivel."""
    sep = "─" * 48
    icon = _decision_icon(r.decision)

    # Linha de candles
    candle_info = (
        f"{r.candles_count} capturados"
        f" (ultimo: {r.last_candle_time or 'N/A'})"
    )
    fresh_tag = " ✓" if r.decision_fresh else " ⚠"

    # Linha de decisao
    conf_str = f"{r.confidence:.0%}" if r.confidence else "N/A"
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

    lines = [
        sep,
        f"  {r.symbol} | {r.timeframe} | {r.timestamp} {mode_tag}",
        sep,
        f"  Candles  : {candle_info}{fresh_tag}",
        f"  Decisao  : {decision_line}",
        f"  Episodio : {episode_line}",
        f"  Treino   : {train_line}",
        f"  Posicao  : {position_line}",
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
        # Episodios pendentes (apos ultimo treino)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM rl_episodes "
                "WHERE created_at > COALESCE("
                "  (SELECT MAX(completed_at) FROM rl_training_log), "
                "  '1970-01-01')"
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
