"""Persistence repository for Model 2.0 initial thesis lifecycle."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping

from .scanner import DetectionResult
from .thesis_state import ThesisStatus, is_valid_transition


DEFAULT_EXPIRATION_MS = 24 * 60 * 60 * 1000
INITIAL_EVENT_TYPE = "STATUS_TRANSITION"
INITIAL_TO_STATUS = "IDENTIFICADA"
MONITORING_TO_STATUS = "MONITORANDO"
VALIDATED_TO_STATUS = "VALIDADA"
INVALIDATED_TO_STATUS = "INVALIDADA"
EXPIRED_TO_STATUS = "EXPIRADA"
M2_003_1_RULE_ID = "M2-003.1-RULE-CANDLE-MONITORING"
M2_003_2_RULE_ID = "M2-003.2-RULE-THESIS-VALIDATION"
M2_003_3_RULE_ID_INVALIDATION = "M2-003.3-RULE-THESIS-INVALIDATION"
M2_003_3_RULE_ID_EXPIRATION = "M2-003.3-RULE-THESIS-EXPIRATION"


@dataclass(frozen=True)
class CreateInitialThesisResult:
    """Result of initial thesis persistence."""

    opportunity_id: int
    created_now: bool


@dataclass(frozen=True)
class TransitionToMonitoringResult:
    """Result of status transition to MONITORANDO."""

    opportunity_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class TransitionToValidatedResult:
    """Result of status transition to VALIDADA."""

    opportunity_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class TransitionToInvalidatedResult:
    """Result of status transition to INVALIDADA."""

    opportunity_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class TransitionToExpiredResult:
    """Result of status transition to EXPIRADA."""

    opportunity_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


class Model2ThesisRepository:
    """Repository that writes opportunities and initial events in one transaction."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _extract_rejection_timestamp(self, metadata: Mapping[str, Any]) -> int | None:
        rejection = metadata.get("rejection_candle")
        if not isinstance(rejection, Mapping):
            return None
        raw_value = rejection.get("timestamp")
        try:
            if raw_value is None:
                return None
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _find_existing_opportunity(
        self,
        conn: sqlite3.Connection,
        detection: DetectionResult,
    ) -> int | None:
        target_rejection_ts = self._extract_rejection_timestamp(detection.metadata)
        if target_rejection_ts is None:
            return None

        rows = conn.execute(
            """
            SELECT id, metadata_json
            FROM opportunities
            WHERE symbol = ?
              AND timeframe = ?
              AND thesis_type = ?
            ORDER BY id DESC
            """,
            (detection.symbol, detection.timeframe, detection.thesis_type),
        ).fetchall()

        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"] or "{}")
            except json.JSONDecodeError:
                continue

            current_rejection_ts = self._extract_rejection_timestamp(metadata)
            if current_rejection_ts == target_rejection_ts:
                return int(row["id"])

        return None

    def _insert_opportunity(
        self,
        conn: sqlite3.Connection,
        detection: DetectionResult,
        now_ms: int,
        expires_at_ms: int,
        metadata_json: str,
    ) -> int:
        cursor = conn.execute(
            """
            INSERT INTO opportunities (
                symbol,
                timeframe,
                side,
                thesis_type,
                status,
                zone_low,
                zone_high,
                trigger_price,
                invalidation_price,
                created_at,
                updated_at,
                expires_at,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                detection.symbol,
                detection.timeframe,
                detection.side,
                detection.thesis_type,
                INITIAL_TO_STATUS,
                detection.zone_low,
                detection.zone_high,
                detection.trigger_price,
                detection.invalidation_price,
                now_ms,
                now_ms,
                expires_at_ms,
                metadata_json,
            ),
        )
        return int(cursor.lastrowid)

    def _insert_initial_event(
        self,
        conn: sqlite3.Connection,
        opportunity_id: int,
        detection: DetectionResult,
        now_ms: int,
    ) -> None:
        event_payload = {
            "created_by": "model2_scanner",
            "thesis_type": detection.thesis_type,
            "side": detection.side,
            "trigger_price": detection.trigger_price,
            "invalidation_price": detection.invalidation_price,
        }
        conn.execute(
            """
            INSERT INTO opportunity_events (
                opportunity_id,
                event_type,
                from_status,
                to_status,
                event_timestamp,
                rule_id,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                INITIAL_EVENT_TYPE,
                None,
                INITIAL_TO_STATUS,
                now_ms,
                detection.rule_id,
                json.dumps(event_payload, ensure_ascii=True, sort_keys=True),
            ),
        )

    def create_initial_thesis(
        self,
        detection: DetectionResult,
        now_ms: int,
    ) -> CreateInitialThesisResult:
        """Persist opportunity + initial transition with idempotency guarantee."""

        if not detection.detected:
            raise ValueError("DetectionResult.detected must be True for persistence.")

        expires_at_ms = int(detection.metadata.get("expires_at", now_ms + DEFAULT_EXPIRATION_MS))
        metadata_json = json.dumps(detection.metadata, ensure_ascii=True, sort_keys=True)

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing_id = self._find_existing_opportunity(conn, detection=detection)
                if existing_id is not None:
                    conn.execute("COMMIT")
                    return CreateInitialThesisResult(
                        opportunity_id=existing_id,
                        created_now=False,
                    )

                opportunity_id = self._insert_opportunity(
                    conn=conn,
                    detection=detection,
                    now_ms=now_ms,
                    expires_at_ms=expires_at_ms,
                    metadata_json=metadata_json,
                )
                self._insert_initial_event(
                    conn=conn,
                    opportunity_id=opportunity_id,
                    detection=detection,
                    now_ms=now_ms,
                )
                conn.execute("COMMIT")
                return CreateInitialThesisResult(
                    opportunity_id=opportunity_id,
                    created_now=True,
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def list_identified_opportunities(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return opportunities currently waiting for candle monitoring."""

        query = [
            "SELECT id, symbol, timeframe, side, thesis_type, status, created_at, updated_at, expires_at",
            "FROM opportunities",
            "WHERE status = ?",
        ]
        params: list[Any] = [INITIAL_TO_STATUS]

        if symbol:
            query.append("AND symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND timeframe = ?")
            params.append(timeframe)

        query.append("ORDER BY created_at ASC, id ASC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            return [dict(row) for row in rows]

    def list_monitoring_opportunities(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return opportunities currently waiting for validation rules."""

        query = [
            "SELECT",
            "  o.id, o.symbol, o.timeframe, o.side, o.thesis_type, o.status,",
            "  o.zone_low, o.zone_high, o.trigger_price, o.invalidation_price,",
            "  o.created_at, o.updated_at, o.expires_at, o.metadata_json,",
            "  (",
            "    SELECT MAX(e.event_timestamp)",
            "    FROM opportunity_events e",
            "    WHERE e.opportunity_id = o.id AND e.to_status = ?",
            "  ) AS monitoring_started_at",
            "FROM opportunities o",
            "WHERE o.status = ?",
        ]
        params: list[Any] = [MONITORING_TO_STATUS, MONITORING_TO_STATUS]

        if symbol:
            query.append("AND o.symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND o.timeframe = ?")
            params.append(timeframe)

        query.append("ORDER BY o.updated_at ASC, o.id ASC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            return [dict(row) for row in rows]

    def _insert_status_transition_event(
        self,
        conn: sqlite3.Connection,
        *,
        opportunity_id: int,
        from_status: str | None,
        to_status: str,
        event_timestamp: int,
        rule_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO opportunity_events (
                opportunity_id,
                event_type,
                from_status,
                to_status,
                event_timestamp,
                rule_id,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                INITIAL_EVENT_TYPE,
                from_status,
                to_status,
                event_timestamp,
                rule_id,
                json.dumps(payload, ensure_ascii=True, sort_keys=True),
            ),
        )

    def transition_to_monitoring(
        self,
        *,
        opportunity_id: int,
        now_ms: int,
        rule_id: str = M2_003_1_RULE_ID,
    ) -> TransitionToMonitoringResult:
        """Transition IDENTIFICADA -> MONITORANDO with audit event and idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, symbol, timeframe, status
                    FROM opportunities
                    WHERE id = ?
                    """,
                    (opportunity_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return TransitionToMonitoringResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                current_status = str(row["status"])
                if current_status == MONITORING_TO_STATUS:
                    conn.execute("COMMIT")
                    return TransitionToMonitoringResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="already_monitoring",
                    )

                if not is_valid_transition(current_status, ThesisStatus.MONITORANDO):
                    conn.execute("COMMIT")
                    return TransitionToMonitoringResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="invalid_transition",
                    )

                conn.execute(
                    """
                    UPDATE opportunities
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (MONITORING_TO_STATUS, now_ms, opportunity_id),
                )
                event_payload = {
                    "updated_by": "model2_tracker",
                    "reason": "candle_monitoring_started",
                    "symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                }
                self._insert_status_transition_event(
                    conn,
                    opportunity_id=opportunity_id,
                    from_status=current_status,
                    to_status=MONITORING_TO_STATUS,
                    event_timestamp=now_ms,
                    rule_id=rule_id,
                    payload=event_payload,
                )
                conn.execute("COMMIT")
                return TransitionToMonitoringResult(
                    opportunity_id=opportunity_id,
                    transitioned=True,
                    previous_status=current_status,
                    current_status=MONITORING_TO_STATUS,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def transition_to_validated(
        self,
        *,
        opportunity_id: int,
        now_ms: int,
        rule_id: str = M2_003_2_RULE_ID,
        payload: Mapping[str, Any] | None = None,
    ) -> TransitionToValidatedResult:
        """Transition MONITORANDO -> VALIDADA with audit event and idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, symbol, timeframe, status
                    FROM opportunities
                    WHERE id = ?
                    """,
                    (opportunity_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return TransitionToValidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                current_status = str(row["status"])
                if current_status == VALIDATED_TO_STATUS:
                    conn.execute("COMMIT")
                    return TransitionToValidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="already_validated",
                    )

                if not is_valid_transition(current_status, ThesisStatus.VALIDADA):
                    conn.execute("COMMIT")
                    return TransitionToValidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="invalid_transition",
                    )

                conn.execute(
                    """
                    UPDATE opportunities
                    SET status = ?,
                        updated_at = ?,
                        resolved_at = ?,
                        resolution_reason = ?
                    WHERE id = ?
                    """,
                    (VALIDATED_TO_STATUS, now_ms, now_ms, "validation_confirmed", opportunity_id),
                )
                event_payload = {
                    "updated_by": "model2_validator",
                    "reason": "validation_confirmed",
                    "symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                }
                if payload:
                    event_payload["validation"] = dict(payload)

                self._insert_status_transition_event(
                    conn,
                    opportunity_id=opportunity_id,
                    from_status=current_status,
                    to_status=VALIDATED_TO_STATUS,
                    event_timestamp=now_ms,
                    rule_id=rule_id,
                    payload=event_payload,
                )
                conn.execute("COMMIT")
                return TransitionToValidatedResult(
                    opportunity_id=opportunity_id,
                    transitioned=True,
                    previous_status=current_status,
                    current_status=VALIDATED_TO_STATUS,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def transition_to_invalidated(
        self,
        *,
        opportunity_id: int,
        now_ms: int,
        rule_id: str = M2_003_3_RULE_ID_INVALIDATION,
        payload: Mapping[str, Any] | None = None,
    ) -> TransitionToInvalidatedResult:
        """Transition MONITORANDO -> INVALIDADA with audit event and idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, symbol, timeframe, status
                    FROM opportunities
                    WHERE id = ?
                    """,
                    (opportunity_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return TransitionToInvalidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                current_status = str(row["status"])
                if current_status == INVALIDATED_TO_STATUS:
                    conn.execute("COMMIT")
                    return TransitionToInvalidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="already_invalidated",
                    )

                if not is_valid_transition(current_status, ThesisStatus.INVALIDADA):
                    conn.execute("COMMIT")
                    return TransitionToInvalidatedResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="invalid_transition",
                    )

                conn.execute(
                    """
                    UPDATE opportunities
                    SET status = ?,
                        updated_at = ?,
                        resolved_at = ?,
                        resolution_reason = ?
                    WHERE id = ?
                    """,
                    (INVALIDATED_TO_STATUS, now_ms, now_ms, "premise_broken", opportunity_id),
                )
                event_payload = {
                    "updated_by": "model2_resolver",
                    "reason": "premise_broken",
                    "symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                }
                if payload:
                    event_payload["invalidation"] = dict(payload)

                self._insert_status_transition_event(
                    conn,
                    opportunity_id=opportunity_id,
                    from_status=current_status,
                    to_status=INVALIDATED_TO_STATUS,
                    event_timestamp=now_ms,
                    rule_id=rule_id,
                    payload=event_payload,
                )
                conn.execute("COMMIT")
                return TransitionToInvalidatedResult(
                    opportunity_id=opportunity_id,
                    transitioned=True,
                    previous_status=current_status,
                    current_status=INVALIDATED_TO_STATUS,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def transition_to_expired(
        self,
        *,
        opportunity_id: int,
        now_ms: int,
        rule_id: str = M2_003_3_RULE_ID_EXPIRATION,
        payload: Mapping[str, Any] | None = None,
    ) -> TransitionToExpiredResult:
        """Transition MONITORANDO -> EXPIRADA with audit event and idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, symbol, timeframe, status
                    FROM opportunities
                    WHERE id = ?
                    """,
                    (opportunity_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return TransitionToExpiredResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                current_status = str(row["status"])
                if current_status == EXPIRED_TO_STATUS:
                    conn.execute("COMMIT")
                    return TransitionToExpiredResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="already_expired",
                    )

                if not is_valid_transition(current_status, ThesisStatus.EXPIRADA):
                    conn.execute("COMMIT")
                    return TransitionToExpiredResult(
                        opportunity_id=opportunity_id,
                        transitioned=False,
                        previous_status=current_status,
                        current_status=current_status,
                        reason="invalid_transition",
                    )

                conn.execute(
                    """
                    UPDATE opportunities
                    SET status = ?,
                        updated_at = ?,
                        resolved_at = ?,
                        resolution_reason = ?
                    WHERE id = ?
                    """,
                    (EXPIRED_TO_STATUS, now_ms, now_ms, "time_limit_reached", opportunity_id),
                )
                event_payload = {
                    "updated_by": "model2_resolver",
                    "reason": "time_limit_reached",
                    "symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                }
                if payload:
                    event_payload["expiration"] = dict(payload)

                self._insert_status_transition_event(
                    conn,
                    opportunity_id=opportunity_id,
                    from_status=current_status,
                    to_status=EXPIRED_TO_STATUS,
                    event_timestamp=now_ms,
                    rule_id=rule_id,
                    payload=event_payload,
                )
                conn.execute("COMMIT")
                return TransitionToExpiredResult(
                    opportunity_id=opportunity_id,
                    transitioned=True,
                    previous_status=current_status,
                    current_status=EXPIRED_TO_STATUS,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise
