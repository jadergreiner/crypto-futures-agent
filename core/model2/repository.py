"""Persistence repository for Model 2.0 initial thesis lifecycle."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Mapping, cast

from .order_layer import (
    OrderLayerInput,
    evaluate_signal_for_order_layer,
    TECHNICAL_SIGNAL_STATUS_CANCELLED,
    TECHNICAL_SIGNAL_STATUS_CONSUMED,
    TECHNICAL_SIGNAL_STATUS_CREATED,
)
from .signal_adapter import ADAPTER_EXPORT_KEY, ADAPTER_LAST_ERROR_KEY
from .scanner import DetectionResult
from .signal_bridge import build_standard_signal, SignalBridgeInput
from .thesis_state import ThesisStatus, is_valid_transition
from .live_execution import (
    ENTRY_ORDER_TYPE_MARKET,
    M2_009_1_RULE_ID,
    OFFICIAL_SIGNAL_EXECUTION_STATUSES,
    SIGNAL_EXECUTION_STATUS_BLOCKED,
    SIGNAL_EXECUTION_STATUS_CANCELLED,
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
    SIGNAL_EXECUTION_STATUS_EXITED,
    SIGNAL_EXECUTION_STATUS_FAILED,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
    SIGNAL_EXECUTION_STATUS_READY,
    is_valid_signal_execution_transition,
    LiveExecutionGateDecision,
)


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


@dataclass(frozen=True)
class CreateStandardSignalResult:
    """Result of standard signal creation from VALIDADA thesis."""

    opportunity_id: int
    signal_id: int | None
    created: bool
    reason: str
    current_status: str | None


@dataclass(frozen=True)
class ConsumeTechnicalSignalResult:
    """Result of order-layer consumption of a technical signal."""

    signal_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class MarkTechnicalSignalExportResult:
    """Result of adapter export marker update in technical_signals payload."""

    signal_id: int
    updated: bool
    reason: str


@dataclass(frozen=True)
class MarkTechnicalSignalExportErrorResult:
    """Result of adapter export error marker update in technical_signals payload."""

    signal_id: int
    updated: bool
    reason: str


@dataclass(frozen=True)
class CreateSignalExecutionResult:
    """Result of initial live execution candidate creation."""

    execution_id: int | None
    created: bool
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class TransitionSignalExecutionResult:
    """Result of a signal execution status transition."""

    execution_id: int
    transitioned: bool
    previous_status: str | None
    current_status: str | None
    reason: str


@dataclass(frozen=True)
class CreateModelDecisionResult:
    """Resultado da persistencia de uma decisao model-driven."""

    decision_id: int


class Model2ThesisRepository:
    """Repository that writes opportunities and initial events in one transaction."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _safe_json_dict(raw_value: Any) -> dict[str, Any]:
        try:
            payload = json.loads(raw_value or "{}")
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            return payload
        return {}

    @staticmethod
    def _merge_json_payload(
        current_payload: Mapping[str, Any] | None,
        updates: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        payload = dict(current_payload) if isinstance(current_payload, Mapping) else {}
        if not updates:
            return payload
        for key, value in updates.items():
            if isinstance(value, Mapping) and isinstance(payload.get(key), Mapping):
                current_value = payload.get(key)
                merged = dict(cast(Mapping[str, Any], current_value))
                merged.update(dict(value))
                payload[key] = merged
            else:
                payload[key] = value
        return payload

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
        if cursor.lastrowid is None:
            raise RuntimeError("Falha ao inserir opportunity: lastrowid ausente.")
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

    def list_validated_opportunities(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return opportunities currently in VALIDADA status."""

        query = [
            "SELECT",
            "  id, symbol, timeframe, side, thesis_type, status,",
            "  zone_low, zone_high, trigger_price, invalidation_price,",
            "  created_at, updated_at, resolved_at, metadata_json",
            "FROM opportunities",
            "WHERE status = ?",
        ]
        params: list[Any] = [VALIDATED_TO_STATUS]

        if symbol:
            query.append("AND symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND timeframe = ?")
            params.append(timeframe)

        query.append("ORDER BY resolved_at ASC, id ASC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            return [dict(row) for row in rows]

    def list_created_technical_signals(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return technical signals currently waiting for order-layer consumption."""

        query = [
            "SELECT",
            "  id, opportunity_id, symbol, timeframe, signal_side, entry_type,",
            "  entry_price, stop_loss, take_profit, signal_timestamp,",
            "  status, rule_id, payload_json, created_at, updated_at",
            "FROM technical_signals",
            "WHERE status = ?",
        ]
        params: list[Any] = [TECHNICAL_SIGNAL_STATUS_CREATED]

        if symbol:
            query.append("AND symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND timeframe = ?")
            params.append(timeframe)

        query.append("ORDER BY signal_timestamp ASC, id ASC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            return [dict(row) for row in rows]

    def list_consumed_technical_signals(
        self,
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return technical signals in CONSUMED status (eligible for legacy adapter)."""

        query = [
            "SELECT",
            "  id, opportunity_id, symbol, timeframe, signal_side, entry_type,",
            "  entry_price, stop_loss, take_profit, signal_timestamp,",
            "  status, rule_id, payload_json, created_at, updated_at",
            "FROM technical_signals",
            "WHERE status = ?",
        ]
        params: list[Any] = [TECHNICAL_SIGNAL_STATUS_CONSUMED]

        if symbol:
            query.append("AND symbol = ?")
            params.append(symbol)
        if timeframe:
            query.append("AND timeframe = ?")
            params.append(timeframe)

        query.append("ORDER BY signal_timestamp ASC, id ASC")
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

    def create_standard_signal_from_validated(
        self,
        *,
        opportunity_id: int,
        now_ms: int,
    ) -> CreateStandardSignalResult:
        """Create a standard signal for a VALIDADA opportunity with idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT
                        id, symbol, timeframe, side, status, zone_low, zone_high,
                        trigger_price, invalidation_price, metadata_json
                    FROM opportunities
                    WHERE id = ?
                    """,
                    (opportunity_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return CreateStandardSignalResult(
                        opportunity_id=opportunity_id,
                        signal_id=None,
                        created=False,
                        reason="not_found",
                        current_status=None,
                    )

                current_status = str(row["status"])
                existing = conn.execute(
                    "SELECT id FROM technical_signals WHERE opportunity_id = ?",
                    (opportunity_id,),
                ).fetchone()
                if existing is not None:
                    conn.execute("COMMIT")
                    return CreateStandardSignalResult(
                        opportunity_id=opportunity_id,
                        signal_id=int(existing["id"]),
                        created=False,
                        reason="already_exists",
                        current_status=current_status,
                    )

                try:
                    metadata = json.loads(row["metadata_json"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}

                bridge_result = build_standard_signal(
                    SignalBridgeInput(
                        opportunity_id=int(row["id"]),
                        symbol=str(row["symbol"]),
                        timeframe=str(row["timeframe"]),
                        side=str(row["side"]),
                        status=current_status,
                        zone_low=float(row["zone_low"]),
                        zone_high=float(row["zone_high"]),
                        trigger_price=float(row["trigger_price"]),
                        invalidation_price=float(row["invalidation_price"]),
                        metadata=metadata,
                        signal_timestamp=now_ms,
                    )
                )

                if not bridge_result.eligible:
                    conn.execute("COMMIT")
                    return CreateStandardSignalResult(
                        opportunity_id=opportunity_id,
                        signal_id=None,
                        created=False,
                        reason=bridge_result.reason,
                        current_status=current_status,
                    )

                cursor = conn.execute(
                    """
                    INSERT INTO technical_signals (
                        opportunity_id,
                        symbol,
                        timeframe,
                        signal_side,
                        entry_type,
                        entry_price,
                        stop_loss,
                        take_profit,
                        signal_timestamp,
                        status,
                        rule_id,
                        payload_json,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity_id,
                        str(row["symbol"]),
                        str(row["timeframe"]),
                        bridge_result.signal_side,
                        bridge_result.entry_type,
                        bridge_result.entry_price,
                        bridge_result.stop_loss,
                        bridge_result.take_profit,
                        now_ms,
                        bridge_result.status,
                        bridge_result.rule_id,
                        json.dumps(bridge_result.payload, ensure_ascii=True, sort_keys=True),
                        now_ms,
                        now_ms,
                    ),
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("Falha ao inserir technical_signal: lastrowid ausente.")
                signal_id = int(cursor.lastrowid)
                conn.execute("COMMIT")
                return CreateStandardSignalResult(
                    opportunity_id=opportunity_id,
                    signal_id=signal_id,
                    created=True,
                    reason="ok",
                    current_status=current_status,
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def consume_created_signal_for_order_layer(
        self,
        *,
        signal_id: int,
        now_ms: int,
        short_only: bool = False,
    ) -> ConsumeTechnicalSignalResult:
        """Consume CREATED technical signal and persist order-layer decision."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT
                        id, opportunity_id, symbol, timeframe, signal_side, entry_type,
                        entry_price, stop_loss, take_profit, signal_timestamp,
                        status, payload_json
                    FROM technical_signals
                    WHERE id = ?
                    """,
                    (signal_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return ConsumeTechnicalSignalResult(
                        signal_id=signal_id,
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                previous_status = str(row["status"])
                if previous_status == TECHNICAL_SIGNAL_STATUS_CONSUMED:
                    conn.execute("COMMIT")
                    return ConsumeTechnicalSignalResult(
                        signal_id=signal_id,
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason="already_consumed",
                    )
                if previous_status == TECHNICAL_SIGNAL_STATUS_CANCELLED:
                    conn.execute("COMMIT")
                    return ConsumeTechnicalSignalResult(
                        signal_id=signal_id,
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason="already_cancelled",
                    )

                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except json.JSONDecodeError:
                    payload = {}

                decision = evaluate_signal_for_order_layer(
                    OrderLayerInput(
                        signal_id=int(row["id"]),
                        opportunity_id=int(row["opportunity_id"]),
                        symbol=str(row["symbol"]),
                        timeframe=str(row["timeframe"]),
                        signal_side=str(row["signal_side"]),
                        entry_type=str(row["entry_type"]),
                        entry_price=float(row["entry_price"]),
                        stop_loss=float(row["stop_loss"]),
                        take_profit=float(row["take_profit"]),
                        status=previous_status,
                        signal_timestamp=int(row["signal_timestamp"]),
                        payload=payload,
                        decision_timestamp=now_ms,
                    ),
                    short_only=bool(short_only),
                )

                if not decision.should_transition:
                    conn.execute("COMMIT")
                    return ConsumeTechnicalSignalResult(
                        signal_id=signal_id,
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason=decision.reason,
                    )

                updated_payload = dict(payload) if isinstance(payload, dict) else {}
                updated_payload["order_layer"] = {
                    "reason": decision.reason,
                    "rule_id": decision.rule_id,
                    "target_status": decision.target_status,
                    "details": dict(decision.details),
                }

                conn.execute(
                    """
                    UPDATE technical_signals
                    SET status = ?, payload_json = ?, updated_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        decision.target_status,
                        json.dumps(updated_payload, ensure_ascii=True, sort_keys=True),
                        now_ms,
                        signal_id,
                        previous_status,
                    ),
                )
                if conn.total_changes == 0:
                    refreshed = conn.execute(
                        "SELECT status FROM technical_signals WHERE id = ?",
                        (signal_id,),
                    ).fetchone()
                    refreshed_status = str(refreshed["status"]) if refreshed is not None else None
                    conn.execute("COMMIT")
                    return ConsumeTechnicalSignalResult(
                        signal_id=signal_id,
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=refreshed_status,
                        reason="concurrent_update",
                    )

                conn.execute("COMMIT")
                return ConsumeTechnicalSignalResult(
                    signal_id=signal_id,
                    transitioned=True,
                    previous_status=previous_status,
                    current_status=decision.target_status,
                    reason=decision.reason,
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_technical_signal_exported_to_trade_signals(
        self,
        *,
        signal_id: int,
        legacy_trade_signal_id: int,
        now_ms: int,
        rule_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> MarkTechnicalSignalExportResult:
        """Persist export marker in technical_signals payload_json for adapter idempotency."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, payload_json
                    FROM technical_signals
                    WHERE id = ?
                    """,
                    (signal_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return MarkTechnicalSignalExportResult(
                        signal_id=signal_id,
                        updated=False,
                        reason="not_found",
                    )

                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except json.JSONDecodeError:
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}

                export_meta = payload.get(ADAPTER_EXPORT_KEY)
                if isinstance(export_meta, dict):
                    existing_id = export_meta.get("legacy_trade_signal_id")
                    if existing_id is not None and int(existing_id) == int(legacy_trade_signal_id):
                        conn.execute("COMMIT")
                        return MarkTechnicalSignalExportResult(
                            signal_id=signal_id,
                            updated=False,
                            reason="already_marked",
                        )

                payload[ADAPTER_EXPORT_KEY] = {
                    "exported": True,
                    "legacy_trade_signal_id": int(legacy_trade_signal_id),
                    "exported_at": int(now_ms),
                    "rule_id": str(rule_id),
                    "metadata": dict(metadata) if metadata else {},
                }
                if ADAPTER_LAST_ERROR_KEY in payload[ADAPTER_EXPORT_KEY]:
                    del payload[ADAPTER_EXPORT_KEY][ADAPTER_LAST_ERROR_KEY]
                conn.execute(
                    """
                    UPDATE technical_signals
                    SET payload_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(payload, ensure_ascii=True, sort_keys=True),
                        int(now_ms),
                        int(signal_id),
                    ),
                )
                conn.execute("COMMIT")
                return MarkTechnicalSignalExportResult(
                    signal_id=signal_id,
                    updated=True,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_technical_signal_export_error(
        self,
        *,
        signal_id: int,
        now_ms: int,
        rule_id: str,
        error_message: str,
    ) -> MarkTechnicalSignalExportErrorResult:
        """Persist latest export error marker in technical_signals payload_json."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, payload_json
                    FROM technical_signals
                    WHERE id = ?
                    """,
                    (signal_id,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return MarkTechnicalSignalExportErrorResult(
                        signal_id=signal_id,
                        updated=False,
                        reason="not_found",
                    )

                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except json.JSONDecodeError:
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}

                export_meta = payload.get(ADAPTER_EXPORT_KEY)
                if not isinstance(export_meta, dict):
                    export_meta = {"exported": False}

                last_error = export_meta.get(ADAPTER_LAST_ERROR_KEY)
                attempts = 1
                if isinstance(last_error, dict):
                    previous_attempts = last_error.get("attempts")
                    try:
                        if previous_attempts is None:
                            attempts = 1
                        else:
                            attempts = max(1, int(previous_attempts) + 1)
                    except (TypeError, ValueError):
                        attempts = 1

                export_meta[ADAPTER_LAST_ERROR_KEY] = {
                    "at": int(now_ms),
                    "rule_id": str(rule_id),
                    "message": str(error_message),
                    "attempts": attempts,
                }
                payload[ADAPTER_EXPORT_KEY] = export_meta

                conn.execute(
                    """
                    UPDATE technical_signals
                    SET payload_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps(payload, ensure_ascii=True, sort_keys=True),
                        int(now_ms),
                        int(signal_id),
                    ),
                )
                conn.execute("COMMIT")
                return MarkTechnicalSignalExportErrorResult(
                    signal_id=signal_id,
                    updated=True,
                    reason="ok",
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def list_signal_executions(
        self,
        *,
        statuses: tuple[str, ...] | list[str] | None = None,
        execution_mode: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return signal executions filtered by status and scope."""

        query = [
            "SELECT",
            "  se.id, se.technical_signal_id, se.opportunity_id, se.symbol, se.timeframe, se.signal_side,",
            "  se.execution_mode, se.status, se.entry_order_type, se.gate_reason, se.decision_id, se.exchange_order_id,",
            "  se.client_order_id, se.requested_qty, se.filled_qty, se.filled_price, se.stop_order_id,",
            "  se.take_profit_order_id, se.entry_sent_at, se.entry_filled_at, se.protected_at,",
            "  se.exited_at, se.exit_reason, se.exit_price, se.failure_reason, se.payload_json,",
            "  se.created_at, se.updated_at, ts.entry_price AS entry_price,",
            "  ts.stop_loss AS stop_loss, ts.take_profit AS take_profit,",
            "  ts.signal_timestamp AS signal_timestamp",
            "FROM signal_executions se",
            "JOIN technical_signals ts ON ts.id = se.technical_signal_id",
            "WHERE 1 = 1",
        ]
        params: list[Any] = []

        if statuses:
            placeholders = ", ".join(["?"] * len(statuses))
            query.append(f"AND se.status IN ({placeholders})")
            params.extend([str(status) for status in statuses])
        if execution_mode:
            query.append("AND se.execution_mode = ?")
            params.append(str(execution_mode))
        if symbol:
            query.append("AND se.symbol = ?")
            params.append(str(symbol))
        if timeframe:
            query.append("AND se.timeframe = ?")
            params.append(str(timeframe))

        query.append("ORDER BY se.created_at ASC, se.id ASC")
        query.append("LIMIT ?")
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(" ".join(query), params).fetchall()
            return [dict(row) for row in rows]

    def get_signal_execution(self, execution_id: int) -> dict[str, Any] | None:
        """Return a single signal execution row."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    se.id, se.technical_signal_id, se.opportunity_id, se.symbol, se.timeframe, se.signal_side,
                    se.execution_mode, se.status, se.entry_order_type, se.gate_reason, se.decision_id, se.exchange_order_id,
                    se.client_order_id, se.requested_qty, se.filled_qty, se.filled_price, se.stop_order_id,
                    se.take_profit_order_id, se.entry_sent_at, se.entry_filled_at, se.protected_at,
                    se.exited_at, se.exit_reason, se.exit_price, se.failure_reason, se.payload_json,
                    se.created_at, se.updated_at, ts.entry_price AS entry_price,
                    ts.stop_loss AS stop_loss, ts.take_profit AS take_profit,
                    ts.signal_timestamp AS signal_timestamp
                FROM signal_executions se
                JOIN technical_signals ts ON ts.id = se.technical_signal_id
                WHERE se.id = ?
                """,
                (int(execution_id),),
            ).fetchone()
            return dict(row) if row is not None else None

    def count_live_entries_today(
        self,
        *,
        execution_mode: str,
        now_ms: int,
    ) -> int:
        """Count live/shadow execution rows created since UTC day start."""

        day_start_ms = (int(now_ms) // 86_400_000) * 86_400_000
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM signal_executions
                WHERE execution_mode = ?
                  AND created_at >= ?
                  AND status NOT IN (?, ?)
                """,
                (
                    str(execution_mode),
                    int(day_start_ms),
                    SIGNAL_EXECUTION_STATUS_BLOCKED,
                    SIGNAL_EXECUTION_STATUS_CANCELLED,
                ),
            ).fetchone()
            return int(row[0]) if row is not None else 0

    def has_recent_live_entry_for_symbol(
        self,
        *,
        symbol: str,
        execution_mode: str,
        now_ms: int,
        cooldown_window_ms: int,
    ) -> bool:
        """Return whether the symbol has a recent live execution candidate."""

        threshold = int(now_ms) - int(cooldown_window_ms)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM signal_executions
                WHERE symbol = ?
                  AND execution_mode = ?
                  AND created_at >= ?
                  AND status NOT IN (?, ?, ?)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (
                    str(symbol),
                    str(execution_mode),
                    int(threshold),
                    SIGNAL_EXECUTION_STATUS_BLOCKED,
                    SIGNAL_EXECUTION_STATUS_CANCELLED,
                    SIGNAL_EXECUTION_STATUS_FAILED,
                ),
            ).fetchone()
            return row is not None

    def count_active_live_executions_for_symbol(
        self,
        *,
        symbol: str,
        execution_mode: str,
    ) -> int:
        """Count active live execution rows for a symbol."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM signal_executions
                WHERE symbol = ?
                  AND execution_mode = ?
                  AND status IN (?, ?, ?, ?)
                """,
                (
                    str(symbol),
                    str(execution_mode),
                    SIGNAL_EXECUTION_STATUS_READY,
                    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
                    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
                    SIGNAL_EXECUTION_STATUS_PROTECTED,
                ),
            ).fetchone()
            return int(row[0]) if row is not None else 0

    def _table_has_column(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        except sqlite3.Error:
            return False
        return any(str(row[1]).lower() == str(column_name).lower() for row in rows)

    def get_latest_funding_rate(self, *, symbol: str) -> float | None:
        """Return latest funding rate for symbol when funding tables are available."""
        table_candidates = ("funding_rates_api", "funding_rates_history")
        timestamp_candidates = ("timestamp_utc", "timestamp")
        with self._connect() as conn:
            for table_name in table_candidates:
                if not self._table_has_column(conn, table_name, "funding_rate"):
                    continue

                order_column = None
                for candidate in timestamp_candidates:
                    if self._table_has_column(conn, table_name, candidate):
                        order_column = candidate
                        break
                if order_column is None:
                    order_column = "id"

                try:
                    row = conn.execute(
                        f"""
                        SELECT funding_rate
                        FROM {table_name}
                        WHERE symbol = ?
                        ORDER BY {order_column} DESC
                        LIMIT 1
                        """,
                        (str(symbol),),
                    ).fetchone()
                except sqlite3.Error:
                    continue
                if row is None:
                    continue
                try:
                    return float(row[0])
                except (TypeError, ValueError):
                    continue
        return None

    def get_latest_basis_value(self, *, symbol: str) -> float | None:
        """Return latest basis metric for symbol when available in funding tables."""
        table_candidates = ("funding_rates_api", "funding_rates_history")
        basis_columns = ("basis", "basis_value", "basis_pct")
        timestamp_candidates = ("timestamp_utc", "timestamp")
        with self._connect() as conn:
            for table_name in table_candidates:
                basis_column = None
                for column_name in basis_columns:
                    if self._table_has_column(conn, table_name, column_name):
                        basis_column = column_name
                        break
                if basis_column is None:
                    continue

                order_column = None
                for candidate in timestamp_candidates:
                    if self._table_has_column(conn, table_name, candidate):
                        order_column = candidate
                        break
                if order_column is None:
                    order_column = "id"

                try:
                    row = conn.execute(
                        f"""
                        SELECT {basis_column}
                        FROM {table_name}
                        WHERE symbol = ?
                        ORDER BY {order_column} DESC
                        LIMIT 1
                        """,
                        (str(symbol),),
                    ).fetchone()
                except sqlite3.Error:
                    continue
                if row is None:
                    continue
                try:
                    return float(row[0])
                except (TypeError, ValueError):
                    continue
        return None

    def get_live_performance_snapshot(
        self,
        *,
        execution_mode: str,
        limit: int = 20,
    ) -> dict[str, float]:
        """Return lightweight performance snapshot used by BBAPT sizing."""

        capped_limit = max(1, int(limit))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status
                FROM signal_executions
                WHERE execution_mode = ?
                  AND status IN (?, ?, ?)
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (
                    str(execution_mode),
                    SIGNAL_EXECUTION_STATUS_FAILED,
                    SIGNAL_EXECUTION_STATUS_EXITED,
                    SIGNAL_EXECUTION_STATUS_CANCELLED,
                    capped_limit,
                ),
            ).fetchall()

        statuses = [str(row[0]) for row in rows]
        if not statuses:
            return {
                "recent_total": 0.0,
                "recent_failure_ratio": 0.0,
                "loss_streak": 0.0,
            }

        losses = [status for status in statuses if status == SIGNAL_EXECUTION_STATUS_FAILED]
        streak = 0
        for status in statuses:
            if status == SIGNAL_EXECUTION_STATUS_FAILED:
                streak += 1
                continue
            break
        return {
            "recent_total": float(len(statuses)),
            "recent_failure_ratio": float(len(losses) / len(statuses)),
            "loss_streak": float(streak),
        }

    def _insert_signal_execution_event(
        self,
        conn: sqlite3.Connection,
        *,
        execution_id: int,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        event_timestamp: int,
        rule_id: str,
        payload: Mapping[str, Any] | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO signal_execution_events (
                signal_execution_id,
                event_type,
                from_status,
                to_status,
                event_timestamp,
                rule_id,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(execution_id),
                str(event_type),
                from_status,
                to_status,
                int(event_timestamp),
                str(rule_id),
                json.dumps(dict(payload) if payload else {}, ensure_ascii=True, sort_keys=True),
            ),
        )

    def _transition_signal_execution(
        self,
        *,
        execution_id: int,
        expected_statuses: tuple[str, ...],
        target_status: str,
        now_ms: int,
        rule_id: str,
        reason: str,
        event_type: str = "STATUS_TRANSITION",
        metadata: Mapping[str, Any] | None = None,
        field_updates: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    """
                    SELECT id, status, payload_json
                    FROM signal_executions
                    WHERE id = ?
                    """,
                    (int(execution_id),),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return TransitionSignalExecutionResult(
                        execution_id=int(execution_id),
                        transitioned=False,
                        previous_status=None,
                        current_status=None,
                        reason="not_found",
                    )

                previous_status = str(row["status"])
                if previous_status == target_status:
                    conn.execute("COMMIT")
                    return TransitionSignalExecutionResult(
                        execution_id=int(execution_id),
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason=f"already_{target_status.lower()}",
                    )

                if previous_status not in expected_statuses:
                    conn.execute("COMMIT")
                    return TransitionSignalExecutionResult(
                        execution_id=int(execution_id),
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason="invalid_transition",
                    )

                if not is_valid_signal_execution_transition(previous_status, target_status):
                    conn.execute("COMMIT")
                    return TransitionSignalExecutionResult(
                        execution_id=int(execution_id),
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=previous_status,
                        reason="invalid_transition",
                    )

                payload = self._safe_json_dict(row["payload_json"])
                next_payload = self._merge_json_payload(
                    payload,
                    {
                        "live_execution": {
                            "last_reason": str(reason),
                            "last_rule_id": str(rule_id),
                            "last_transition_at": int(now_ms),
                        },
                        **(dict(metadata) if metadata else {}),
                    },
                )
                updates = {
                    "status": str(target_status),
                    "updated_at": int(now_ms),
                    "payload_json": json.dumps(next_payload, ensure_ascii=True, sort_keys=True),
                }
                if field_updates:
                    updates.update(dict(field_updates))

                assignments = ", ".join(f"{column} = ?" for column in updates.keys())
                values = list(updates.values())
                values.extend([int(execution_id), previous_status])
                conn.execute(
                    f"""
                    UPDATE signal_executions
                    SET {assignments}
                    WHERE id = ? AND status = ?
                    """,
                    values,
                )
                if conn.total_changes == 0:
                    refreshed = conn.execute(
                        "SELECT status FROM signal_executions WHERE id = ?",
                        (int(execution_id),),
                    ).fetchone()
                    refreshed_status = str(refreshed["status"]) if refreshed is not None else None
                    conn.execute("COMMIT")
                    return TransitionSignalExecutionResult(
                        execution_id=int(execution_id),
                        transitioned=False,
                        previous_status=previous_status,
                        current_status=refreshed_status,
                        reason="concurrent_update",
                    )

                self._insert_signal_execution_event(
                    conn,
                    execution_id=int(execution_id),
                    event_type=event_type,
                    from_status=previous_status,
                    to_status=target_status,
                    event_timestamp=int(now_ms),
                    rule_id=str(rule_id),
                    payload={
                        "reason": str(reason),
                        "metadata": dict(metadata) if metadata else {},
                    },
                )
                conn.execute("COMMIT")
                return TransitionSignalExecutionResult(
                    execution_id=int(execution_id),
                    transitioned=True,
                    previous_status=previous_status,
                    current_status=target_status,
                    reason=str(reason),
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def create_signal_execution_candidate(
        self,
        *,
        technical_signal_id: int,
        opportunity_id: int,
        symbol: str,
        timeframe: str,
        signal_side: str,
        signal_timestamp: int,
        gate_decision: LiveExecutionGateDecision,
        execution_mode: str,
        now_ms: int,
        decision_id: int | None = None,
        decision_trace: Mapping[str, Any] | None = None,
    ) -> CreateSignalExecutionResult:
        """Create a live execution candidate row from a CONSUMED technical signal."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                signal_row = conn.execute(
                    """
                    SELECT id, opportunity_id, symbol, timeframe, signal_side, status, entry_price, stop_loss, take_profit
                    FROM technical_signals
                    WHERE id = ?
                    """,
                    (int(technical_signal_id),),
                ).fetchone()
                if signal_row is None:
                    conn.execute("COMMIT")
                    return CreateSignalExecutionResult(
                        execution_id=None,
                        created=False,
                        current_status=None,
                        reason="signal_not_found",
                    )

                existing = conn.execute(
                    """
                    SELECT id, status
                    FROM signal_executions
                    WHERE technical_signal_id = ?
                    """,
                    (int(technical_signal_id),),
                ).fetchone()
                if existing is not None:
                    conn.execute("COMMIT")
                    return CreateSignalExecutionResult(
                        execution_id=int(existing["id"]),
                        created=False,
                        current_status=str(existing["status"]),
                        reason="already_exists",
                    )

                if str(signal_row["status"]) != TECHNICAL_SIGNAL_STATUS_CONSUMED:
                    conn.execute("COMMIT")
                    return CreateSignalExecutionResult(
                        execution_id=None,
                        created=False,
                        current_status=None,
                        reason="status_not_consumed",
                    )

                payload = {
                    "signal_snapshot": {
                        "technical_signal_id": int(signal_row["id"]),
                        "symbol": str(signal_row["symbol"]),
                        "timeframe": str(signal_row["timeframe"]),
                        "signal_side": str(signal_side),
                        "source_signal_side": str(signal_row["signal_side"]),
                        "entry_price": float(signal_row["entry_price"]),
                        "stop_loss": float(signal_row["stop_loss"]),
                        "take_profit": float(signal_row["take_profit"]),
                        "signal_timestamp": int(signal_timestamp),
                    },
                    "gate": {
                        "allow_execution": bool(gate_decision.allow_execution),
                        "reason": str(gate_decision.reason),
                        "rule_id": str(gate_decision.rule_id),
                        "details": dict(gate_decision.details),
                    },
                    "live_execution": {
                        "created_by": "model2_live_gate",
                        "created_rule_id": M2_009_1_RULE_ID,
                    },
                }
                if decision_trace:
                    payload["model_decision"] = dict(decision_trace)

                cursor = conn.execute(
                    """
                    INSERT INTO signal_executions (
                        technical_signal_id,
                        opportunity_id,
                        symbol,
                        timeframe,
                        signal_side,
                        execution_mode,
                        status,
                        entry_order_type,
                        gate_reason,
                        decision_id,
                        payload_json,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(technical_signal_id),
                        int(opportunity_id),
                        str(symbol),
                        str(timeframe),
                        str(signal_side),
                        str(execution_mode),
                        str(gate_decision.target_status),
                        ENTRY_ORDER_TYPE_MARKET,
                        str(gate_decision.reason),
                        int(decision_id) if decision_id is not None else None,
                        json.dumps(payload, ensure_ascii=True, sort_keys=True),
                        int(now_ms),
                        int(now_ms),
                    ),
                )
                raw_execution_id = cursor.lastrowid
                if raw_execution_id is None:
                    raise RuntimeError("falha ao obter execution_id apos insert")
                execution_id = int(raw_execution_id)
                self._insert_signal_execution_event(
                    conn,
                    execution_id=execution_id,
                    event_type="STATUS_TRANSITION",
                    from_status=None,
                    to_status=str(gate_decision.target_status),
                    event_timestamp=int(now_ms),
                    rule_id=str(gate_decision.rule_id),
                    payload={
                        "reason": str(gate_decision.reason),
                        "details": dict(gate_decision.details),
                    },
                )
                conn.execute("COMMIT")
                return CreateSignalExecutionResult(
                    execution_id=execution_id,
                    created=True,
                    current_status=str(gate_decision.target_status),
                    reason=str(gate_decision.reason),
                )
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def create_model_decision(
        self,
        *,
        decision_timestamp: int,
        symbol: str,
        action: str,
        confidence: float,
        size_fraction: float,
        sl_target: float | None,
        tp_target: float | None,
        model_version: str,
        reason_code: str,
        inference_latency_ms: int,
        input_payload: Mapping[str, Any] | None = None,
        output_payload: Mapping[str, Any] | None = None,
        created_at: int,
    ) -> CreateModelDecisionResult:
        """Persist decisao model-driven para trilha auditavel de inferencia."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO model_decisions (
                        decision_timestamp,
                        symbol,
                        action,
                        confidence,
                        size_fraction,
                        sl_target,
                        tp_target,
                        model_version,
                        reason_code,
                        inference_latency_ms,
                        input_json,
                        output_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(decision_timestamp),
                        str(symbol),
                        str(action),
                        float(confidence),
                        float(size_fraction),
                        float(sl_target) if sl_target is not None else None,
                        float(tp_target) if tp_target is not None else None,
                        str(model_version),
                        str(reason_code),
                        int(inference_latency_ms),
                        json.dumps(dict(input_payload) if input_payload else {}, ensure_ascii=True, sort_keys=True),
                        json.dumps(dict(output_payload) if output_payload else {}, ensure_ascii=True, sort_keys=True),
                        int(created_at),
                    ),
                )
                conn.execute("COMMIT")
                raw_decision_id = cursor.lastrowid
                if raw_decision_id is None:
                    raise RuntimeError("falha ao obter decision_id apos insert")
                return CreateModelDecisionResult(decision_id=int(raw_decision_id))
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def record_signal_execution_event(
        self,
        *,
        execution_id: int,
        now_ms: int,
        from_status: str | None,
        to_status: str | None,
        event_type: str,
        rule_id: str,
        payload: Mapping[str, Any] | None,
    ) -> None:
        """Append a non-transition event for an execution row."""

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT id FROM signal_executions WHERE id = ?",
                    (int(execution_id),),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return
                self._insert_signal_execution_event(
                    conn,
                    execution_id=int(execution_id),
                    event_type=str(event_type),
                    from_status=from_status,
                    to_status=to_status,
                    event_timestamp=int(now_ms),
                    rule_id=str(rule_id),
                    payload=payload,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def mark_signal_execution_entry_sent(
        self,
        *,
        execution_id: int,
        now_ms: int,
        requested_qty: float,
        exchange_order_id: str,
        client_order_id: str,
        rule_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        """Transition READY -> ENTRY_SENT with exchange order metadata."""

        return self._transition_signal_execution(
            execution_id=int(execution_id),
            expected_statuses=(SIGNAL_EXECUTION_STATUS_READY,),
            target_status=SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
            now_ms=int(now_ms),
            rule_id=str(rule_id),
            reason="entry_sent",
            metadata=metadata,
            field_updates={
                "requested_qty": float(requested_qty),
                "exchange_order_id": str(exchange_order_id) if exchange_order_id else None,
                "client_order_id": str(client_order_id),
                "entry_sent_at": int(now_ms),
            },
        )

    def mark_signal_execution_entry_filled(
        self,
        *,
        execution_id: int,
        now_ms: int,
        filled_qty: float,
        filled_price: float,
        rule_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        """Transition READY|ENTRY_SENT -> ENTRY_FILLED."""

        return self._transition_signal_execution(
            execution_id=int(execution_id),
            expected_statuses=(
                SIGNAL_EXECUTION_STATUS_READY,
                SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
            ),
            target_status=SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
            now_ms=int(now_ms),
            rule_id=str(rule_id),
            reason="entry_filled",
            metadata=metadata,
            field_updates={
                "filled_qty": float(filled_qty),
                "filled_price": float(filled_price),
                "entry_filled_at": int(now_ms),
            },
        )

    def mark_signal_execution_protected(
        self,
        *,
        execution_id: int,
        now_ms: int,
        stop_order_id: str,
        take_profit_order_id: str,
        rule_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        """Transition ENTRY_FILLED -> PROTECTED."""

        return self._transition_signal_execution(
            execution_id=int(execution_id),
            expected_statuses=(SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,),
            target_status=SIGNAL_EXECUTION_STATUS_PROTECTED,
            now_ms=int(now_ms),
            rule_id=str(rule_id),
            reason="protection_armed",
            metadata=metadata,
            field_updates={
                "stop_order_id": str(stop_order_id) if stop_order_id else None,
                "take_profit_order_id": str(take_profit_order_id) if take_profit_order_id else None,
                "protected_at": int(now_ms),
            },
        )

    def mark_signal_execution_failed(
        self,
        *,
        execution_id: int,
        now_ms: int,
        reason: str,
        rule_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        """Transition an active execution row to FAILED."""

        return self._transition_signal_execution(
            execution_id=int(execution_id),
            expected_statuses=(
                SIGNAL_EXECUTION_STATUS_READY,
                SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
                SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
                SIGNAL_EXECUTION_STATUS_PROTECTED,
            ),
            target_status=SIGNAL_EXECUTION_STATUS_FAILED,
            now_ms=int(now_ms),
            rule_id=str(rule_id),
            reason=str(reason),
            metadata=metadata,
            field_updates={"failure_reason": str(reason)},
        )

    def mark_signal_execution_exited(
        self,
        *,
        execution_id: int,
        now_ms: int,
        exit_reason: str,
        rule_id: str,
        exit_price: float | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransitionSignalExecutionResult:
        """Transition ENTRY_FILLED|PROTECTED -> EXITED."""

        updates: dict[str, Any] = {
            "exit_reason": str(exit_reason),
            "exited_at": int(now_ms),
        }
        if exit_price is not None:
            updates["exit_price"] = float(exit_price)
        return self._transition_signal_execution(
            execution_id=int(execution_id),
            expected_statuses=(
                SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
                SIGNAL_EXECUTION_STATUS_PROTECTED,
            ),
            target_status=SIGNAL_EXECUTION_STATUS_EXITED,
            now_ms=int(now_ms),
            rule_id=str(rule_id),
            reason=str(exit_reason),
            metadata=metadata,
            field_updates=updates,
        )
