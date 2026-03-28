"""Cycle snapshot aggregation for M2-025.10."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CycleSnapshot:
    """Consolidated per-cycle snapshot for operational triage."""

    cycle_id: str
    candle: dict[str, Any]
    decision: dict[str, Any]
    episode: dict[str, Any]
    training: dict[str, Any]
    updated_at: int


class CycleSnapshotRepository:
    """Builds and persists a unique snapshot row keyed by cycle_id."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _safe_json_dict(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return {}
            return dict(parsed) if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _merge_dict(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
        if not override:
            return dict(base)
        merged = dict(base)
        merged.update(dict(override))
        return merged

    def _load_latest_operational(self, conn: sqlite3.Connection, cycle_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        try:
            row = conn.execute(
                """
                SELECT candle_json, decisao_json, episodio_json
                FROM operational_snapshots
                WHERE cycle_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (cycle_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return {}, {}, {}

        if row is None:
            return {}, {}, {}

        return (
            self._safe_json_dict(row["candle_json"]),
            self._safe_json_dict(row["decisao_json"]),
            self._safe_json_dict(row["episodio_json"]),
        )

    def _load_latest_decision(self, conn: sqlite3.Connection, cycle_id: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT
                    md.id AS decision_id,
                    md.action,
                    md.confidence,
                    md.reason_code,
                    md.model_version,
                    md.decision_timestamp,
                    se.id AS execution_id
                FROM opportunities o
                JOIN technical_signals ts ON ts.opportunity_id = o.id
                JOIN signal_executions se ON se.technical_signal_id = ts.id
                JOIN model_decisions md ON md.id = se.decision_id
                WHERE json_extract(o.metadata_json, '$.cycle_id') = ?
                ORDER BY md.decision_timestamp DESC, md.id DESC
                LIMIT 1
                """,
                (cycle_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return {}

        if row is None:
            return {}

        return {
            "decision_id": int(row["decision_id"]),
            "execution_id": int(row["execution_id"]),
            "action": str(row["action"]),
            "confidence": float(row["confidence"]),
            "reason_code": str(row["reason_code"]),
            "model_version": str(row["model_version"]),
            "decision_timestamp": int(row["decision_timestamp"]),
        }

    def _load_latest_training(self, conn: sqlite3.Connection, cycle_id: str) -> dict[str, Any]:
        try:
            row = conn.execute(
                """
                SELECT
                    te.id AS episode_id,
                    te.execution_id,
                    te.label,
                    te.status,
                    te.reward_proxy,
                    te.reward_source,
                    te.reward_lookup_at_ms,
                    te.event_timestamp
                FROM opportunities o
                JOIN technical_signals ts ON ts.opportunity_id = o.id
                JOIN signal_executions se ON se.technical_signal_id = ts.id
                JOIN training_episodes te ON te.execution_id = se.id
                WHERE json_extract(o.metadata_json, '$.cycle_id') = ?
                ORDER BY te.event_timestamp DESC, te.id DESC
                LIMIT 1
                """,
                (cycle_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return {}

        if row is None:
            return {}

        reward_lookup_at_ms = row["reward_lookup_at_ms"]
        reward_proxy = row["reward_proxy"]
        payload: dict[str, Any] = {
            "episode_id": int(row["episode_id"]),
            "execution_id": int(row["execution_id"]),
            "label": str(row["label"]),
            "status": str(row["status"]),
            "event_timestamp": int(row["event_timestamp"]),
            "reward_source": str(row["reward_source"] or "none"),
        }
        if reward_proxy is not None:
            payload["reward_proxy"] = float(reward_proxy)
        if reward_lookup_at_ms is not None:
            payload["reward_lookup_at_ms"] = int(reward_lookup_at_ms)
        return payload

    def _ensure_cycle_snapshot_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cycle_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT NOT NULL UNIQUE,
                candle_json TEXT NOT NULL DEFAULT '{}',
                decisao_json TEXT NOT NULL DEFAULT '{}',
                episodio_json TEXT NOT NULL DEFAULT '{}',
                treino_json TEXT NOT NULL DEFAULT '{}',
                updated_at INTEGER NOT NULL
            )
            """
        )

    def refresh_cycle_snapshot(
        self,
        *,
        cycle_id: str,
        candle: dict[str, Any] | None = None,
        decision: dict[str, Any] | None = None,
        episode: dict[str, Any] | None = None,
        training: dict[str, Any] | None = None,
        now_ms: int | None = None,
    ) -> CycleSnapshot:
        normalized_cycle_id = str(cycle_id).strip()
        if not normalized_cycle_id:
            raise ValueError("cycle_id must be non-empty")

        snapshot_now_ms = int(now_ms) if now_ms is not None else int(time.time() * 1000)
        with self._connect() as conn:
            self._ensure_cycle_snapshot_table(conn)

            current_row = conn.execute(
                """
                SELECT candle_json, decisao_json, episodio_json, treino_json
                FROM cycle_snapshots
                WHERE cycle_id = ?
                LIMIT 1
                """,
                (normalized_cycle_id,),
            ).fetchone()
            persisted_candle = self._safe_json_dict(current_row["candle_json"]) if current_row else {}
            persisted_decision = self._safe_json_dict(current_row["decisao_json"]) if current_row else {}
            persisted_episode = self._safe_json_dict(current_row["episodio_json"]) if current_row else {}
            persisted_training = self._safe_json_dict(current_row["treino_json"]) if current_row else {}

            op_candle, op_decision, op_episode = self._load_latest_operational(conn, normalized_cycle_id)
            db_decision = self._load_latest_decision(conn, normalized_cycle_id)
            db_training = self._load_latest_training(conn, normalized_cycle_id)

            consolidated_candle = self._merge_dict(self._merge_dict(persisted_candle, op_candle), candle)
            consolidated_decision = self._merge_dict(
                self._merge_dict(self._merge_dict(persisted_decision, op_decision), db_decision),
                decision,
            )
            consolidated_episode = self._merge_dict(self._merge_dict(persisted_episode, op_episode), episode)
            consolidated_training = self._merge_dict(
                self._merge_dict(persisted_training, db_training),
                training,
            )

            conn.execute(
                """
                INSERT INTO cycle_snapshots (
                    cycle_id,
                    candle_json,
                    decisao_json,
                    episodio_json,
                    treino_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cycle_id) DO UPDATE SET
                    candle_json = excluded.candle_json,
                    decisao_json = excluded.decisao_json,
                    episodio_json = excluded.episodio_json,
                    treino_json = excluded.treino_json,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_cycle_id,
                    json.dumps(consolidated_candle, ensure_ascii=True, sort_keys=True),
                    json.dumps(consolidated_decision, ensure_ascii=True, sort_keys=True),
                    json.dumps(consolidated_episode, ensure_ascii=True, sort_keys=True),
                    json.dumps(consolidated_training, ensure_ascii=True, sort_keys=True),
                    snapshot_now_ms,
                ),
            )
            conn.commit()

        return CycleSnapshot(
            cycle_id=normalized_cycle_id,
            candle=consolidated_candle,
            decision=consolidated_decision,
            episode=consolidated_episode,
            training=consolidated_training,
            updated_at=snapshot_now_ms,
        )

    def get_cycle_snapshot(self, cycle_id: str) -> CycleSnapshot | None:
        normalized_cycle_id = str(cycle_id).strip()
        if not normalized_cycle_id:
            return None

        with self._connect() as conn:
            try:
                row = conn.execute(
                    """
                    SELECT cycle_id, candle_json, decisao_json, episodio_json, treino_json, updated_at
                    FROM cycle_snapshots
                    WHERE cycle_id = ?
                    LIMIT 1
                    """,
                    (normalized_cycle_id,),
                ).fetchone()
            except sqlite3.OperationalError:
                return None

        if row is None:
            return None

        return CycleSnapshot(
            cycle_id=str(row["cycle_id"]),
            candle=self._safe_json_dict(row["candle_json"]),
            decision=self._safe_json_dict(row["decisao_json"]),
            episode=self._safe_json_dict(row["episodio_json"]),
            training=self._safe_json_dict(row["treino_json"]),
            updated_at=int(row["updated_at"]),
        )
