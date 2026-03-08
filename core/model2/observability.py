"""Observability materializations for Model 2.0 dashboard and audit snapshots."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from .thesis_state import OFFICIAL_THESIS_STATUSES

FINAL_STATUSES = ("VALIDADA", "INVALIDADA", "EXPIRADA")


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
