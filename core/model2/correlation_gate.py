"""Gate de concentracao de correlacao de portfolio para M2-028.5."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

_ACTIVE_STATUSES = ("READY", "ENTRY_SENT", "ENTRY_FILLED", "PROTECTED")


@dataclass(frozen=True)
class CorrelationGateDecision:
    """Decisao emitida pelo gate de correlacao de portfolio."""

    allowed: bool
    reason: str
    blocked_group: str   # "classificacao:<nome>" ou "btc_correlation_high"
    open_count: int
    max_per_group: int


class CorrelationGate:
    """Bloqueia admissoes quando concentracao em ativos correlacionados excede o limite configurado.

    Dois criterios de agrupamento sao avaliados de forma independente:
    1. Mesma ``classificacao`` (campo do symbols.py, ex.: ``alta_cap``, ``large_cap_l1``).
    2. Alta correlacao BTC: simbolos com ``correlacao_btc`` (max quando lista) >= threshold.

    A decisao de bloqueio e emitida quando o numero de posicoes abertas no grupo ja
    atingiu ``max_positions_per_corr_group``.
    """

    def __init__(
        self,
        *,
        max_positions_per_corr_group: int,
        btc_correlation_high_threshold: float,
        symbols_config: dict[str, dict[str, Any]],
        db_conn_factory: Callable[[], sqlite3.Connection],
    ) -> None:
        self._max = int(max_positions_per_corr_group)
        self._btc_threshold = float(btc_correlation_high_threshold)
        self._cfg = symbols_config
        self._factory = db_conn_factory

    def evaluate(
        self, *, symbol: str, execution_mode: str
    ) -> CorrelationGateDecision | None:
        """Avalia se o simbolo entrante excederia o limite de concentracao por grupo.

        Retorna ``None`` se o gate passa; caso contrario retorna
        ``CorrelationGateDecision(allowed=False)``.
        """
        conn = self._factory()

        # Verifica por classificacao
        classificacao = self._cfg.get(symbol, {}).get("classificacao")
        if classificacao:
            peers = [s for s, v in self._cfg.items() if v.get("classificacao") == classificacao]
            count = self._count_open(peers, execution_mode, conn)
            if count >= self._max:
                return CorrelationGateDecision(
                    allowed=False,
                    reason="PORTFOLIO_CORRELATION_LIMIT",
                    blocked_group=f"classificacao:{classificacao}",
                    open_count=count,
                    max_per_group=self._max,
                )

        # Verifica por correlacao BTC alta
        if self._is_high_btc_correlation(symbol):
            high_btc_peers = [s for s in self._cfg if self._is_high_btc_correlation(s)]
            count = self._count_open(high_btc_peers, execution_mode, conn)
            if count >= self._max:
                return CorrelationGateDecision(
                    allowed=False,
                    reason="PORTFOLIO_CORRELATION_LIMIT",
                    blocked_group="btc_correlation_high",
                    open_count=count,
                    max_per_group=self._max,
                )

        return None

    # ------------------------------------------------------------------
    # Auxiliares internos
    # ------------------------------------------------------------------

    def _is_high_btc_correlation(self, symbol: str) -> bool:
        corr = self._cfg.get(symbol, {}).get("correlacao_btc", 0.0)
        max_corr: float = max(float(c) for c in corr) if isinstance(corr, list) else float(corr)
        return max_corr >= self._btc_threshold

    def _count_open(
        self,
        symbols: list[str],
        execution_mode: str,
        conn: sqlite3.Connection,
    ) -> int:
        """Conta simbolos distintos com posicao ativa no grupo, filtrando por execution_mode."""
        if not symbols:
            return 0
        status_placeholders = ",".join("?" * len(_ACTIVE_STATUSES))
        symbol_placeholders = ",".join("?" * len(symbols))
        row = conn.execute(
            f"SELECT COUNT(DISTINCT symbol) FROM signal_executions "
            f"WHERE execution_mode = ? "
            f"AND status IN ({status_placeholders}) "
            f"AND symbol IN ({symbol_placeholders})",
            (execution_mode, *_ACTIVE_STATUSES, *symbols),
        ).fetchone()
        return int(row[0]) if row else 0
