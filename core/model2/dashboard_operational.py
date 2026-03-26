"""Dashboard operacional em tempo-real para Model 2.0 (M2-026.4).

Consolida visão operacional: ciclos/hora, oportunidades, episódios,
execuções admitidas/bloqueadas e reconciliação — com filtro por símbolo
e período.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


SEVERITY_ORDER: dict[str, int] = {"CRITICAL": 0, "ERROR": 1, "WARN": 2, "INFO": 3}
MAX_ROWS_PER_QUERY = 100


@dataclass(frozen=True)
class OperationalDashboardSummary:
    """Sumário consolidado do dashboard operacional."""

    timestamp_utc: str
    ciclos_ultima_hora: int
    oportunidades_ativas: int
    episodios_em_progresso: int
    execucoes_admitidas: int
    execucoes_bloqueadas: int
    execucoes_falhas: int
    reconciliation_status: str


def query_operational_status(db_path: str, symbol: Optional[str] = None) -> dict[str, Any]:
    """Retorna sumário operacional consolidado.

    Args:
        db_path: caminho para db/modelo2.db
        symbol: filtrar por símbolo (None = todos)

    Returns:
        dict com métricas operacionais consolidadas
    """
    now_ms = int(time.time() * 1000)
    one_hour_ms = 3_600_000
    cutoff_ms = now_ms - one_hour_ms

    result: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ciclos_ultima_hora": 0,
        "oportunidades_ativas": 0,
        "episodios_em_progresso": 0,
        "execucoes_admitidas": 0,
        "execucoes_bloqueadas": 0,
        "execucoes_falhas": 0,
        "reconciliation_status": "UNKNOWN",
    }

    try:
        with sqlite3.connect(db_path) as conn:
            # Oportunidades ativas
            sym_filter = "AND symbol = ?" if symbol else ""
            params_sym: list[Any] = [symbol] if symbol else []

            opp_row = conn.execute(
                f"""
                SELECT COUNT(*) FROM opportunities
                WHERE status IN ('IDENTIFICADA', 'MONITORANDO')
                {sym_filter}
                """,
                params_sym,
            ).fetchone()
            result["oportunidades_ativas"] = opp_row[0] if opp_row else 0

            # Execuções admitidas/bloqueadas/falhas na última hora
            exec_sym_filter = "AND symbol = ?" if symbol else ""
            exec_params: list[Any] = [cutoff_ms] + ([symbol] if symbol else [])

            exec_rows = conn.execute(
                f"""
                SELECT status, COUNT(*) FROM signal_executions
                WHERE created_at >= ? {exec_sym_filter}
                GROUP BY status
                """,
                exec_params,
            ).fetchall()
            for status, count in exec_rows:
                if status in ("CONSUMED", "ENTRY_FILLED", "PROTECTED", "EXITED"):
                    result["execucoes_admitidas"] = result["execucoes_admitidas"] + count
                elif status in ("BLOCKED", "CANCELLED"):
                    result["execucoes_bloqueadas"] = result["execucoes_bloqueadas"] + count
                elif status == "FAILED":
                    result["execucoes_falhas"] = result["execucoes_falhas"] + count

            # Ciclos operacionais na última hora (via snapshots)
            try:
                snap_row = conn.execute(
                    "SELECT COUNT(*) FROM operational_snapshots WHERE created_at >= ?",
                    (cutoff_ms,),
                ).fetchone()
                result["ciclos_ultima_hora"] = snap_row[0] if snap_row else 0
            except sqlite3.OperationalError:
                result["ciclos_ultima_hora"] = 0

            # Reconciliation: última execução aberta sem exit
            try:
                open_count = conn.execute(
                    "SELECT COUNT(*) FROM signal_executions WHERE status = 'ENTRY_FILLED'",
                ).fetchone()
                result["reconciliation_status"] = "OPEN_POSITIONS" if (open_count and open_count[0] > 0) else "RECONCILED"
            except sqlite3.OperationalError:
                result["reconciliation_status"] = "UNKNOWN"

    except Exception:
        pass

    return result


def query_by_symbol(db_path: str, symbol: str, limit: int = MAX_ROWS_PER_QUERY) -> list[dict[str, Any]]:
    """Retorna oportunidades ativas para um símbolo (max MAX_ROWS_PER_QUERY).

    Args:
        db_path: caminho para o DB
        symbol: símbolo a filtrar (ex: BTCUSDT)
        limit: máximo de linhas retornadas

    Returns:
        lista de oportunidades ativas do símbolo
    """
    rows: list[dict[str, Any]] = []
    effective_limit = min(limit, MAX_ROWS_PER_QUERY)
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT symbol, status, direction, entry_price,
                       target_price, invalidation_price, created_at
                FROM opportunities
                WHERE symbol = ? AND status IN ('IDENTIFICADA', 'MONITORANDO')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (symbol, effective_limit),
            )
            for row in cursor.fetchall():
                rows.append(dict(row))
    except Exception:
        pass
    return rows


def query_by_period(
    db_path: str,
    start: datetime,
    end: datetime,
    symbol: Optional[str] = None,
    limit: int = MAX_ROWS_PER_QUERY,
) -> list[dict[str, Any]]:
    """Retorna eventos operacionais dentro de uma janela temporal.

    Args:
        db_path: caminho para o DB
        start: início da janela (UTC)
        end: fim da janela (UTC)
        symbol: filtrar por símbolo (opcional)
        limit: máximo de linhas retornadas

    Returns:
        lista de eventos dentro da janela
    """
    rows: list[dict[str, Any]] = []
    effective_limit = min(limit, MAX_ROWS_PER_QUERY)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    sym_filter = "AND symbol = ?" if symbol else ""
    params: list[Any] = [start_ms, end_ms] + ([symbol] if symbol else [])

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"""
                SELECT symbol, status, created_at
                FROM signal_executions
                WHERE created_at >= ? AND created_at <= ?
                {sym_filter}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params + [effective_limit],
            )
            for row in cursor.fetchall():
                rows.append(dict(row))
    except Exception:
        pass
    return rows


def sort_alerts_by_severity(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordena alertas por severidade (CRITICAL primeiro).

    Args:
        alerts: lista de dicts com campo 'severity'

    Returns:
        lista ordenada por severidade decrescente
    """
    return sorted(alerts, key=lambda x: SEVERITY_ORDER.get(str(x.get("severity", "INFO")), 99))
