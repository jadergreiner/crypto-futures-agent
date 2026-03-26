"""Observability materializations for Model 2.0 dashboard and audit snapshots."""

from __future__ import annotations

import sqlite3
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .signal_adapter import ADAPTER_EXPORT_KEY, ADAPTER_LAST_ERROR_KEY
from .thesis_state import OFFICIAL_THESIS_STATUSES

FINAL_STATUSES = ("VALIDADA", "INVALIDADA", "EXPIRADA")

# M2-024.6 — etapas validas para telemetria de latencia
VALID_LATENCY_STAGES: frozenset[str] = frozenset(
    {"scan", "validate", "signal", "order", "execute"}
)

_logger = logging.getLogger(__name__)


def registrar_latencia(
    *,
    simbolo: str,
    etapa: str,
    resultado: str,
    latencia_ms: int,
    db_path: str | None = None,
) -> None:
    """Registra latencia de uma etapa do pipeline para um simbolo.

    Args:
        simbolo: simbolo negociado (ex: BTCUSDT)
        etapa: etapa do pipeline; deve ser uma de VALID_LATENCY_STAGES
        resultado: descricao do resultado (ex: sucesso, erro)
        latencia_ms: duracao da etapa em milissegundos
        db_path: caminho para o DB modelo2; usa padrao se None
    """
    if etapa not in VALID_LATENCY_STAGES:
        raise ValueError(
            f"Etapa '{etapa}' invalida. Validas: {sorted(VALID_LATENCY_STAGES)}"
        )
    if db_path is None:
        try:
            from config.settings import MODEL2_DB_PATH
            db_path = str(MODEL2_DB_PATH)
        except Exception:
            db_path = "db/modelo2.db"

    ts = int(time.time() * 1000)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO execution_latencies (symbol, stage, result_code, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (simbolo, etapa, resultado, latencia_ms, ts),
        )
        conn.commit()
    except Exception:
        _logger.warning(
            "Falha ao registrar latencia %s/%s %dms — ignorando",
            simbolo, etapa, latencia_ms,
        )
    finally:
        conn.close()


# M2-024.9 — snapshot operacional por ciclo
@dataclass
class OperationalSnapshot:
    """Snapshot consolidado de um ciclo operacional do pipeline M2."""

    candle_fresco: dict[str, Any]
    decisao: dict[str, Any]
    episodio: dict[str, Any]
    execucao: dict[str, Any]
    reconciliacao: dict[str, Any]
    cycle_id: str | None = field(default=None)


@dataclass(frozen=True)
class DashboardSnapshot:
    """Computed dashboard snapshot payload."""

    count_by_status: dict[str, int]
    avg_resolution_ms: float | None
    avg_resolution_ms_by_final_status: dict[str, float | None]
    stored_rows: int
    purged_rows: int


@dataclass(frozen=True)
class AuditSnapshot:
    """Computed audit snapshot payload."""

    rows: list[dict[str, Any]]
    stored_rows: int
    purged_rows: int


@dataclass(frozen=True)
class SignalFlowSnapshot:
    """Computed signal-flow snapshot payload (M2-007.3)."""

    created_count: int
    consumed_count: int
    cancelled_count: int
    exported_count: int
    consumed_not_exported_count: int
    export_error_count: int
    export_rate: float | None
    avg_created_to_consumed_ms: float | None
    avg_consumed_to_exported_ms: float | None
    avg_created_to_exported_ms: float | None
    stored_rows: int
    purged_rows: int


@dataclass(frozen=True)
class LiveExecutionSnapshot:
    """Computed live-execution snapshot payload (M2-010.2)."""

    ready_count: int
    blocked_count: int
    entry_sent_count: int
    entry_filled_count: int
    protected_count: int
    exited_count: int
    failed_count: int
    cancelled_count: int
    unprotected_filled_count: int
    stale_entry_sent_count: int
    open_position_mismatches_count: int
    avg_signal_to_entry_sent_ms: float | None
    avg_entry_sent_to_filled_ms: float | None
    avg_filled_to_protected_ms: float | None
    stored_rows: int
    purged_rows: int


class Model2ObservabilityService:
    """Creates queryable observability snapshots with retention policy."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _retention_threshold(snapshot_timestamp: int, retention_days: int) -> int:
        window_ms = int(retention_days) * 24 * 60 * 60 * 1000
        return int(snapshot_timestamp) - window_ms

    def refresh_dashboard_snapshot(
        self,
        *,
        run_id: str,
        snapshot_timestamp: int,
        retention_days: int = 30,
    ) -> DashboardSnapshot:
        with self._connect() as conn:
            counts = {status: 0 for status in OFFICIAL_THESIS_STATUSES}
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM opportunities
                GROUP BY status
                """
            ).fetchall()
            for row in rows:
                status = str(row["status"])
                if status in counts:
                    counts[status] = int(row["total"])

            avg_overall_row = conn.execute(
                """
                SELECT AVG(resolved_at - created_at)
                FROM opportunities
                WHERE status IN ('VALIDADA', 'INVALIDADA', 'EXPIRADA')
                  AND resolved_at IS NOT NULL
                  AND resolved_at >= created_at
                """
            ).fetchone()
            avg_overall = (
                float(avg_overall_row[0])
                if avg_overall_row is not None and avg_overall_row[0] is not None
                else None
            )

            avg_rows = conn.execute(
                """
                SELECT status, AVG(resolved_at - created_at) AS avg_ms
                FROM opportunities
                WHERE status IN ('VALIDADA', 'INVALIDADA', 'EXPIRADA')
                  AND resolved_at IS NOT NULL
                  AND resolved_at >= created_at
                GROUP BY status
                """
            ).fetchall()
            avg_by_status: dict[str, float | None] = {status: None for status in FINAL_STATUSES}
            for row in avg_rows:
                status = str(row["status"])
                if status in avg_by_status and row["avg_ms"] is not None:
                    avg_by_status[status] = float(row["avg_ms"])

            conn.execute("BEGIN IMMEDIATE")
            try:
                created_at = int(snapshot_timestamp)
                stored_rows = 0
                for status in OFFICIAL_THESIS_STATUSES:
                    conn.execute(
                        """
                        INSERT INTO opportunity_dashboard_snapshots (
                            run_id,
                            snapshot_timestamp,
                            status,
                            opportunity_count,
                            avg_resolution_ms,
                            avg_resolution_ms_overall,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            int(snapshot_timestamp),
                            status,
                            int(counts[status]),
                            avg_by_status.get(status),
                            avg_overall,
                            created_at,
                        ),
                    )
                    stored_rows += 1

                threshold = self._retention_threshold(snapshot_timestamp, retention_days)
                purged_rows = conn.execute(
                    "DELETE FROM opportunity_dashboard_snapshots WHERE snapshot_timestamp < ?",
                    (threshold,),
                ).rowcount
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return DashboardSnapshot(
            count_by_status=counts,
            avg_resolution_ms=avg_overall,
            avg_resolution_ms_by_final_status=avg_by_status,
            stored_rows=stored_rows,
            purged_rows=int(purged_rows),
        )

    def refresh_audit_snapshot(
        self,
        *,
        run_id: str,
        snapshot_timestamp: int,
        retention_days: int = 30,
        opportunity_id: int | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
        limit: int = 1000,
    ) -> AuditSnapshot:
        query = [
            "SELECT",
            "  e.id AS event_id, e.opportunity_id,",
            "  o.symbol, o.timeframe,",
            "  e.event_type, e.from_status, e.to_status,",
            "  e.event_timestamp, e.rule_id, e.payload_json",
            "FROM opportunity_events e",
            "JOIN opportunities o ON o.id = e.opportunity_id",
            "WHERE 1 = 1",
        ]
        params: list[Any] = []
        if opportunity_id is not None:
            query.append("AND e.opportunity_id = ?")
            params.append(int(opportunity_id))
        if symbol:
            query.append("AND o.symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND o.timeframe = ?")
            params.append(timeframe)
        if start_ts is not None:
            query.append("AND e.event_timestamp >= ?")
            params.append(int(start_ts))
        if end_ts is not None:
            query.append("AND e.event_timestamp <= ?")
            params.append(int(end_ts))

        query.append("ORDER BY e.event_timestamp DESC, e.id DESC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            materialized_rows: list[dict[str, Any]] = []
            for row in rows:
                materialized_rows.append(
                    {
                        "event_id": int(row["event_id"]),
                        "opportunity_id": int(row["opportunity_id"]),
                        "symbol": str(row["symbol"]),
                        "timeframe": str(row["timeframe"]),
                        "event_type": str(row["event_type"]),
                        "from_status": row["from_status"],
                        "to_status": str(row["to_status"]),
                        "event_timestamp": int(row["event_timestamp"]),
                        "rule_id": str(row["rule_id"]),
                        "payload_json": str(row["payload_json"]),
                    }
                )

            conn.execute("BEGIN IMMEDIATE")
            try:
                created_at = int(snapshot_timestamp)
                for item in materialized_rows:
                    conn.execute(
                        """
                        INSERT INTO opportunity_audit_snapshots (
                            run_id,
                            snapshot_timestamp,
                            event_id,
                            opportunity_id,
                            symbol,
                            timeframe,
                            event_type,
                            from_status,
                            to_status,
                            event_timestamp,
                            rule_id,
                            payload_json,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            int(snapshot_timestamp),
                            int(item["event_id"]),
                            int(item["opportunity_id"]),
                            item["symbol"],
                            item["timeframe"],
                            item["event_type"],
                            item["from_status"],
                            item["to_status"],
                            int(item["event_timestamp"]),
                            item["rule_id"],
                            item["payload_json"],
                            created_at,
                        ),
                    )

                threshold = self._retention_threshold(snapshot_timestamp, retention_days)
                purged_rows = conn.execute(
                    "DELETE FROM opportunity_audit_snapshots WHERE snapshot_timestamp < ?",
                    (threshold,),
                ).rowcount
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return AuditSnapshot(
            rows=materialized_rows,
            stored_rows=len(materialized_rows),
            purged_rows=int(purged_rows),
        )

    @staticmethod
    def _payload_dict(raw_payload: Any) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_payload or "{}")
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            return parsed
        return {}

    @staticmethod
    def _to_int_or_none(value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_avg(values: list[int]) -> float | None:
        if not values:
            return None
        return float(sum(values)) / float(len(values))

    def refresh_signal_flow_snapshot(
        self,
        *,
        run_id: str,
        snapshot_timestamp: int,
        retention_days: int = 30,
    ) -> SignalFlowSnapshot:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, status, signal_timestamp, payload_json
                FROM technical_signals
                """
            ).fetchall()

            created_count = 0
            consumed_count = 0
            cancelled_count = 0
            exported_count = 0
            export_error_count = 0
            created_to_consumed_durations: list[int] = []
            consumed_to_exported_durations: list[int] = []
            created_to_exported_durations: list[int] = []

            for row in rows:
                status = str(row["status"])
                signal_ts = int(row["signal_timestamp"])
                payload = self._payload_dict(row["payload_json"])
                order_layer = payload.get("order_layer")
                adapter = payload.get(ADAPTER_EXPORT_KEY)

                if status == "CREATED":
                    created_count += 1
                elif status == "CONSUMED":
                    consumed_count += 1
                elif status == "CANCELLED":
                    cancelled_count += 1

                decision_ts = None
                if isinstance(order_layer, dict):
                    details = order_layer.get("details")
                    if isinstance(details, dict):
                        decision_ts = self._to_int_or_none(details.get("decision_timestamp"))
                    if decision_ts is None:
                        decision_ts = self._to_int_or_none(order_layer.get("decision_timestamp"))

                exported_at = None
                adapter_exported = False
                if isinstance(adapter, dict):
                    adapter_exported = bool(adapter.get("exported") is True)
                    exported_at = self._to_int_or_none(adapter.get("exported_at"))
                    if adapter.get(ADAPTER_LAST_ERROR_KEY) is not None:
                        export_error_count += 1

                if adapter_exported:
                    exported_count += 1

                if status == "CONSUMED" and decision_ts is not None and decision_ts >= signal_ts:
                    created_to_consumed_durations.append(decision_ts - signal_ts)
                if (
                    status == "CONSUMED"
                    and exported_at is not None
                    and decision_ts is not None
                    and exported_at >= decision_ts
                ):
                    consumed_to_exported_durations.append(exported_at - decision_ts)
                if status == "CONSUMED" and exported_at is not None and exported_at >= signal_ts:
                    created_to_exported_durations.append(exported_at - signal_ts)

            consumed_not_exported_count = max(0, consumed_count - exported_count)
            export_rate = (
                (float(exported_count) / float(consumed_count))
                if consumed_count > 0
                else None
            )
            avg_created_to_consumed_ms = self._safe_avg(created_to_consumed_durations)
            avg_consumed_to_exported_ms = self._safe_avg(consumed_to_exported_durations)
            avg_created_to_exported_ms = self._safe_avg(created_to_exported_durations)

            conn.execute("BEGIN IMMEDIATE")
            try:
                created_at = int(snapshot_timestamp)
                conn.execute(
                    """
                    INSERT INTO signal_flow_snapshots (
                        run_id,
                        snapshot_timestamp,
                        created_count,
                        consumed_count,
                        cancelled_count,
                        exported_count,
                        consumed_not_exported_count,
                        export_error_count,
                        export_rate,
                        avg_created_to_consumed_ms,
                        avg_consumed_to_exported_ms,
                        avg_created_to_exported_ms,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        int(snapshot_timestamp),
                        int(created_count),
                        int(consumed_count),
                        int(cancelled_count),
                        int(exported_count),
                        int(consumed_not_exported_count),
                        int(export_error_count),
                        export_rate,
                        avg_created_to_consumed_ms,
                        avg_consumed_to_exported_ms,
                        avg_created_to_exported_ms,
                        created_at,
                    ),
                )
                threshold = self._retention_threshold(snapshot_timestamp, retention_days)
                purged_rows = conn.execute(
                    "DELETE FROM signal_flow_snapshots WHERE snapshot_timestamp < ?",
                    (threshold,),
                ).rowcount
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return SignalFlowSnapshot(
            created_count=created_count,
            consumed_count=consumed_count,
            cancelled_count=cancelled_count,
            exported_count=exported_count,
            consumed_not_exported_count=consumed_not_exported_count,
            export_error_count=export_error_count,
            export_rate=export_rate,
            avg_created_to_consumed_ms=avg_created_to_consumed_ms,
            avg_consumed_to_exported_ms=avg_consumed_to_exported_ms,
            avg_created_to_exported_ms=avg_created_to_exported_ms,
            stored_rows=1,
            purged_rows=int(purged_rows),
        )

    def refresh_live_execution_snapshot(
        self,
        *,
        run_id: str,
        snapshot_timestamp: int,
        retention_days: int = 30,
    ) -> LiveExecutionSnapshot:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    status,
                    created_at,
                    entry_sent_at,
                    entry_filled_at,
                    protected_at,
                    payload_json
                FROM signal_executions
                """
            ).fetchall()

            ready_count = 0
            blocked_count = 0
            entry_sent_count = 0
            entry_filled_count = 0
            protected_count = 0
            exited_count = 0
            failed_count = 0
            cancelled_count = 0
            unprotected_filled_count = 0
            stale_entry_sent_count = 0
            open_position_mismatches_count = 0
            signal_to_entry_sent_durations: list[int] = []
            entry_sent_to_filled_durations: list[int] = []
            filled_to_protected_durations: list[int] = []

            for row in rows:
                status = str(row["status"])
                payload = self._payload_dict(row["payload_json"])
                signal_snapshot = payload.get("signal_snapshot")
                signal_timestamp = None
                if isinstance(signal_snapshot, dict):
                    signal_timestamp = self._to_int_or_none(signal_snapshot.get("signal_timestamp"))
                reconcile_payload = payload.get("reconcile")

                if status == "READY":
                    ready_count += 1
                elif status == "BLOCKED":
                    blocked_count += 1
                elif status == "ENTRY_SENT":
                    entry_sent_count += 1
                elif status == "ENTRY_FILLED":
                    entry_filled_count += 1
                    unprotected_filled_count += 1
                elif status == "PROTECTED":
                    protected_count += 1
                elif status == "EXITED":
                    exited_count += 1
                elif status == "FAILED":
                    failed_count += 1
                elif status == "CANCELLED":
                    cancelled_count += 1

                entry_sent_at = self._to_int_or_none(row["entry_sent_at"])
                entry_filled_at = self._to_int_or_none(row["entry_filled_at"])
                protected_at = self._to_int_or_none(row["protected_at"])
                if signal_timestamp is not None and entry_sent_at is not None and entry_sent_at >= signal_timestamp:
                    signal_to_entry_sent_durations.append(entry_sent_at - signal_timestamp)
                if entry_sent_at is not None and entry_filled_at is not None and entry_filled_at >= entry_sent_at:
                    entry_sent_to_filled_durations.append(entry_filled_at - entry_sent_at)
                if entry_filled_at is not None and protected_at is not None and protected_at >= entry_filled_at:
                    filled_to_protected_durations.append(protected_at - entry_filled_at)
                if status == "ENTRY_SENT" and entry_sent_at is not None and (snapshot_timestamp - entry_sent_at) > 30_000:
                    stale_entry_sent_count += 1

                if isinstance(reconcile_payload, dict) and reconcile_payload.get("result") == "position_mismatch":
                    open_position_mismatches_count += 1

            avg_signal_to_entry_sent_ms = self._safe_avg(signal_to_entry_sent_durations)
            avg_entry_sent_to_filled_ms = self._safe_avg(entry_sent_to_filled_durations)
            avg_filled_to_protected_ms = self._safe_avg(filled_to_protected_durations)

            conn.execute("BEGIN IMMEDIATE")
            try:
                created_at = int(snapshot_timestamp)
                conn.execute(
                    """
                    INSERT INTO signal_execution_snapshots (
                        run_id,
                        snapshot_timestamp,
                        ready_count,
                        blocked_count,
                        entry_sent_count,
                        entry_filled_count,
                        protected_count,
                        exited_count,
                        failed_count,
                        cancelled_count,
                        unprotected_filled_count,
                        stale_entry_sent_count,
                        open_position_mismatches_count,
                        avg_signal_to_entry_sent_ms,
                        avg_entry_sent_to_filled_ms,
                        avg_filled_to_protected_ms,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        int(snapshot_timestamp),
                        int(ready_count),
                        int(blocked_count),
                        int(entry_sent_count),
                        int(entry_filled_count),
                        int(protected_count),
                        int(exited_count),
                        int(failed_count),
                        int(cancelled_count),
                        int(unprotected_filled_count),
                        int(stale_entry_sent_count),
                        int(open_position_mismatches_count),
                        avg_signal_to_entry_sent_ms,
                        avg_entry_sent_to_filled_ms,
                        avg_filled_to_protected_ms,
                        created_at,
                    ),
                )
                threshold = self._retention_threshold(snapshot_timestamp, retention_days)
                purged_rows = conn.execute(
                    "DELETE FROM signal_execution_snapshots WHERE snapshot_timestamp < ?",
                    (threshold,),
                ).rowcount
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return LiveExecutionSnapshot(
            ready_count=ready_count,
            blocked_count=blocked_count,
            entry_sent_count=entry_sent_count,
            entry_filled_count=entry_filled_count,
            protected_count=protected_count,
            exited_count=exited_count,
            failed_count=failed_count,
            cancelled_count=cancelled_count,
            unprotected_filled_count=unprotected_filled_count,
            stale_entry_sent_count=stale_entry_sent_count,
            open_position_mismatches_count=open_position_mismatches_count,
            avg_signal_to_entry_sent_ms=avg_signal_to_entry_sent_ms,
            avg_entry_sent_to_filled_ms=avg_entry_sent_to_filled_ms,
            avg_filled_to_protected_ms=avg_filled_to_protected_ms,
            stored_rows=1,
            purged_rows=int(purged_rows),
        )

    def record_cycle_snapshot(self, snapshot: OperationalSnapshot) -> None:
        """Persiste snapshot operacional de um ciclo no DB.

        M2-024.9: snapshot unico por ciclo com todos os campos operacionais.
        """
        ts = int(time.time() * 1000)
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO operational_snapshots
                    (cycle_id, candle_json, decisao_json, episodio_json,
                     execucao_json, reconciliacao_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.cycle_id,
                    json.dumps(snapshot.candle_fresco, ensure_ascii=True),
                    json.dumps(snapshot.decisao, ensure_ascii=True),
                    json.dumps(snapshot.episodio, ensure_ascii=True),
                    json.dumps(snapshot.execucao, ensure_ascii=True),
                    json.dumps(snapshot.reconciliacao, ensure_ascii=True),
                    ts,
                ),
            )
            conn.commit()
        finally:
            conn.close()
