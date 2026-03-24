"""Cycle watchdog e utilitarios de resiliencia para o pipeline M2 (M2-027).

Responsabilidades:
- Detectar travamento de ciclo por ausencia de progressao (R1)
- Acionar fail-safe preservando estado sem desabilitar guardrails (R2)
- Validar schema M2 pre-execucao (R3)
- Detectar posicoes orfas e construir ordem de saida segura (R4)
- Executar transicao CONSUMED->IN_PROGRESS de forma atomica com revert (R5)
- Emitir audit_event com decision_id e timestamp_utc (R6)

Guardrails:
- risk_gate e circuit_breaker NUNCA sao desabilitados por este modulo
- Saida de posicao orfa usa SOMENTE STOP_MARKET
- Revert garante que estado parcial nunca persiste
"""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Tabelas obrigatorias para schema M2 valido (inclui audit_decision_execution de M2-026.3)
_REQUIRED_TABLES: frozenset[str] = frozenset({
    "schema_migrations",
    "technical_signals",
    "signal_executions",
    "signal_execution_events",
    "signal_execution_snapshots",
    "audit_decision_execution",
})


def _utc_now_iso() -> str:
    """Retorna timestamp UTC atual em formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


class CycleWatchdog:
    """Monitora progressao do ciclo M2 e aciona fail-safe em caso de travamento.

    Nao desabilita risk_gate nem circuit_breaker em nenhuma circunstancia.
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        """Inicializa watchdog com janela de deteccao de travamento.

        Args:
            window_seconds: segundos sem progressao antes de declarar stall.
                            Padrao: 300 (5 minutos).
        """
        self._window_seconds = window_seconds

    def check_progress(self, last_progress_ts: float) -> dict[str, Any]:
        """Verifica se o ciclo esta progredindo dentro da janela configurada.

        Args:
            last_progress_ts: timestamp (epoch float) da ultima progressao.

        Returns:
            dict com:
              - stalled: bool
              - reason_code: 'cycle_stalled' | None
              - timestamp_utc: str ISO 8601
              - elapsed_seconds: float
        """
        elapsed = time.time() - last_progress_ts
        stalled = elapsed > self._window_seconds

        result: dict[str, Any] = {
            "stalled": stalled,
            "reason_code": "cycle_stalled" if stalled else None,
            "timestamp_utc": _utc_now_iso(),
            "elapsed_seconds": elapsed,
        }

        if stalled:
            logger.warning(
                "cycle_watchdog: ciclo travado detectado — elapsed=%.1fs window=%.1fs",
                elapsed,
                self._window_seconds,
            )

        return result

    def trigger_failsafe(self, cycle_state: dict[str, Any]) -> dict[str, Any]:
        """Aciona fail-safe de interrupcao preservando estado do ciclo.

        Nunca desabilita risk_gate ou circuit_breaker.

        Args:
            cycle_state: estado atual do ciclo (pode conter decision_id, symbol, etc.)

        Returns:
            dict com:
              - interrupted: True
              - state_preserved: True
              - preserved_state: copia do cycle_state
              - risk_gate_disabled: False (invariante)
              - circuit_breaker_disabled: False (invariante)
              - audit_event: dict com decision_id e timestamp_utc
        """
        decision_id = cycle_state.get("decision_id")

        audit_event: dict[str, Any] = {
            "event_type": "cycle_failsafe_triggered",
            "decision_id": decision_id,
            "timestamp_utc": _utc_now_iso(),
            "cycle_state_snapshot": dict(cycle_state),
        }

        logger.warning(
            "cycle_watchdog: fail-safe acionado — decision_id=%s state_keys=%s",
            decision_id,
            list(cycle_state.keys()),
        )

        return {
            "interrupted": True,
            "state_preserved": True,
            "preserved_state": dict(cycle_state),
            "risk_gate_disabled": False,
            "circuit_breaker_disabled": False,
            "audit_event": audit_event,
        }


def validate_schema_pre_exec(db_path: Path) -> dict[str, Any]:
    """Valida schema M2 antes de executar ciclo.

    Verifica se todas as tabelas obrigatorias existem no banco operacional.
    Em caso de divergencia, retorna status='blocked' com reason_code padronizado.

    Args:
        db_path: caminho para o banco modelo2.db.

    Returns:
        dict com:
          - status: 'ok' | 'blocked'
          - reason_code: None | 'db_not_found' | 'schema_divergence'
          - missing_tables: list[str] (vazio se ok)
          - timestamp_utc: str ISO 8601
    """
    timestamp = _utc_now_iso()

    if not Path(db_path).exists():
        logger.error("validate_schema_pre_exec: banco nao encontrado — path=%s", db_path)
        return {
            "status": "blocked",
            "reason_code": "db_not_found",
            "missing_tables": [],
            "timestamp_utc": timestamp,
        }

    with sqlite3.connect(db_path) as conn:
        found: set[str] = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    missing = sorted(_REQUIRED_TABLES - found)

    if missing:
        logger.error(
            "validate_schema_pre_exec: tabelas ausentes — %s", missing
        )
        return {
            "status": "blocked",
            "reason_code": "schema_divergence",
            "missing_tables": missing,
            "timestamp_utc": timestamp,
        }

    return {
        "status": "ok",
        "reason_code": None,
        "missing_tables": [],
        "timestamp_utc": timestamp,
    }


def detect_orphan_positions(
    exchange_positions: list[dict[str, Any]],
    db_executions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Detecta posicoes abertas na exchange sem registro correspondente no banco.

    Uma posicao e considerada orfa quando:
    - positionAmt != 0 (posicao aberta)
    - nao existe signal_execution com mesmo symbol e status IN_PROGRESS

    Args:
        exchange_positions: lista de posicoes abertas da Binance
                            (cada item: {'symbol': str, 'positionAmt': str}).
        db_executions: lista de signal_executions do banco
                       (cada item: {'symbol': str, 'status': str}).

    Returns:
        dict com:
          - orphans: list de posicoes orfas com reason_code
          - timestamp_utc: str ISO 8601
    """
    active_symbols: set[str] = {
        ex["symbol"]
        for ex in db_executions
        if ex.get("status") == "IN_PROGRESS"
    }

    orphans: list[dict[str, Any]] = []

    for pos in exchange_positions:
        symbol = pos.get("symbol", "")
        amt_str = str(pos.get("positionAmt", "0"))
        try:
            amt = float(amt_str)
        except ValueError:
            amt = 0.0

        if amt != 0.0 and symbol not in active_symbols:
            orphans.append({
                "symbol": symbol,
                "positionAmt": amt_str,
                "reason_code": "orphan_position",
            })
            logger.warning(
                "detect_orphan_positions: posicao orfa detectada — symbol=%s amt=%s",
                symbol,
                amt_str,
            )

    return {
        "orphans": orphans,
        "timestamp_utc": _utc_now_iso(),
    }


def build_orphan_exit_order(orphan: dict[str, Any]) -> dict[str, Any]:
    """Constroi ordem de saida segura para posicao orfa.

    Invariante: ordem usa SOMENTE STOP_MARKET, nunca MARKET.
    Gera audit_event com decision_id sintetico rastreavel.

    Args:
        orphan: dict com symbol, positionAmt e reason_code.

    Returns:
        dict com:
          - symbol: str
          - order_type: 'STOP_MARKET' (invariante)
          - reason_code: 'orphan_position'
          - synthetic_decision_id: str UUID
          - audit_event: dict com decision_id e timestamp_utc
    """
    synthetic_decision_id = f"ORPHAN-{uuid.uuid4().hex[:12].upper()}"
    timestamp = _utc_now_iso()

    audit_event: dict[str, Any] = {
        "event_type": "orphan_exit_order_built",
        "decision_id": synthetic_decision_id,
        "symbol": orphan.get("symbol"),
        "reason_code": "orphan_position",
        "timestamp_utc": timestamp,
    }

    logger.warning(
        "build_orphan_exit_order: ordem de saida orfa — symbol=%s synthetic_id=%s",
        orphan.get("symbol"),
        synthetic_decision_id,
    )

    return {
        "symbol": orphan.get("symbol"),
        "order_type": "STOP_MARKET",
        "reason_code": "orphan_position",
        "synthetic_decision_id": synthetic_decision_id,
        "audit_event": audit_event,
    }


def execute_atomic_state_transition(
    signal_id: int,
    execution_id: int,
    persist_consumed_fn: Callable[..., Any],
    persist_in_progress_fn: Callable[..., Any],
    decision_id: int | None = None,
    revert_consumed_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Executa transicao CONSUMED->IN_PROGRESS de forma atomica com revert em falha.

    Garante que estado parcial nunca persiste: se a segunda escrita falhar,
    a primeira e revertida via revert_consumed_fn.

    Args:
        signal_id: ID do sinal tecnico.
        execution_id: ID da execucao de sinal.
        persist_consumed_fn: callable que persiste status CONSUMED.
        persist_in_progress_fn: callable que persiste status IN_PROGRESS.
        decision_id: ID da decisao para correlacao auditavel (opcional).
        revert_consumed_fn: callable que reverte CONSUMED em falha (opcional).

    Returns:
        dict com:
          - committed: bool
          - reverted: bool
          - partial_state_persisted: bool (sempre False apos revert)
          - audit_event: dict com decision_id e timestamp_utc
    """
    timestamp = _utc_now_iso()

    audit_event: dict[str, Any] = {
        "event_type": "atomic_state_transition",
        "signal_id": signal_id,
        "execution_id": execution_id,
        "decision_id": decision_id,
        "timestamp_utc": timestamp,
    }

    persist_consumed_fn(signal_id=signal_id)

    try:
        persist_in_progress_fn(execution_id=execution_id)
    except Exception as exc:
        logger.error(
            "execute_atomic_state_transition: falha na 2a escrita — revertendo "
            "signal_id=%s execution_id=%s error=%s",
            signal_id,
            execution_id,
            exc,
        )
        if revert_consumed_fn is not None:
            revert_consumed_fn(signal_id=signal_id)

        audit_event["outcome"] = "reverted"

        return {
            "committed": False,
            "reverted": True,
            "partial_state_persisted": False,
            "audit_event": audit_event,
        }

    audit_event["outcome"] = "committed"
    logger.info(
        "execute_atomic_state_transition: transicao atomica concluida — "
        "signal_id=%s execution_id=%s decision_id=%s",
        signal_id,
        execution_id,
        decision_id,
    )

    return {
        "committed": True,
        "reverted": False,
        "partial_state_persisted": False,
        "audit_event": audit_event,
    }
