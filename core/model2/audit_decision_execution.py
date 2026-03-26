"""Auditoria imutável de correlação decision_id ↔ execution_id para M2-026.3."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class AuditDecisionExecution:
    """Registro imutável de correlação decision ↔ execution ↔ signal.

    Campos obrigatórios:
    - decision_id: identificador único da decisão (FK)
    - execution_id: identificador único da tentativa de execução (FK)
    - signal_id: identificador do sinal técnico (FK)
    - timestamp_utc: quando a auditoria foi registrada
    - decision_status: status da decisão na época do registro
    - execution_status: status da execução na época do registro
    - error_reason: razão do erro, se houver (do REASON_CODE_CATALOG)
    - additional_context: metadados adicionais para análise
    """

    decision_id: int
    execution_id: int
    signal_id: int
    timestamp_utc: datetime
    decision_status: str
    execution_status: str
    error_reason: Optional[str] = None
    additional_context: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validação de campos obrigatórios."""
        if self.decision_id <= 0:
            raise ValueError("decision_id deve ser positivo")
        if self.execution_id <= 0:
            raise ValueError("execution_id deve ser positivo")
        if self.signal_id <= 0:
            raise ValueError("signal_id deve ser positivo")


class AuditDecisionExecutionRepository:
    """Repositório INSERT-only para tabela audit_decision_execution.

    Guardrail: UPDATE e DELETE não são permitidos.
    Toda tentativa lança NotImplementedError.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def insert_audit_record(self, record: AuditDecisionExecution) -> bool:
        """Insere registro de auditoria imutável. Retorna True em sucesso."""
        context_json: Optional[str] = None
        if record.additional_context is not None:
            context_json = json.dumps(record.additional_context)

        ts_str = record.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_decision_execution
                        (decision_id, execution_id, signal_id, timestamp_utc,
                         decision_status, execution_status, error_reason,
                         additional_context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.decision_id,
                        record.execution_id,
                        record.signal_id,
                        ts_str,
                        record.decision_status,
                        record.execution_status,
                        record.error_reason,
                        context_json,
                    ),
                )
                conn.commit()
        except sqlite3.Error:
            return False
        return True

    def query_by_decision_id(
        self, decision_id: int
    ) -> list[AuditDecisionExecution]:
        """Retorna todos os registros correlacionados a um decision_id."""
        rows: list[AuditDecisionExecution] = []
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """
                SELECT decision_id, execution_id, signal_id, timestamp_utc,
                       decision_status, execution_status, error_reason,
                       additional_context
                FROM audit_decision_execution
                WHERE decision_id = ?
                ORDER BY id ASC
                """,
                (decision_id,),
            )
            for row in cursor.fetchall():
                rows.append(self._row_to_record(row))
        return rows

    def query_by_execution_id(
        self, execution_id: int
    ) -> list[AuditDecisionExecution]:
        """Retorna todos os registros correlacionados a um execution_id."""
        rows: list[AuditDecisionExecution] = []
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """
                SELECT decision_id, execution_id, signal_id, timestamp_utc,
                       decision_status, execution_status, error_reason,
                       additional_context
                FROM audit_decision_execution
                WHERE execution_id = ?
                ORDER BY id ASC
                """,
                (execution_id,),
            )
            for row in cursor.fetchall():
                rows.append(self._row_to_record(row))
        return rows

    def update_audit_record(self, **_kwargs: Any) -> None:
        """Guardrail: UPDATE não permitido em audit_decision_execution."""
        raise NotImplementedError("UPDATE não permitido em audit_decision_execution")

    def delete_audit_record(self, **_kwargs: Any) -> None:
        """Guardrail: DELETE não permitido em audit_decision_execution."""
        raise NotImplementedError("DELETE não permitido em audit_decision_execution")

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> AuditDecisionExecution:
        (
            decision_id,
            execution_id,
            signal_id,
            timestamp_utc_str,
            decision_status,
            execution_status,
            error_reason,
            additional_context_json,
        ) = row

        ts = datetime.fromisoformat(
            timestamp_utc_str.replace("Z", "+00:00")
        ).replace(tzinfo=timezone.utc)

        ctx: Optional[dict[str, Any]] = None
        if additional_context_json:
            ctx = json.loads(additional_context_json)

        return AuditDecisionExecution(
            decision_id=decision_id,
            execution_id=execution_id,
            signal_id=signal_id,
            timestamp_utc=ts,
            decision_status=decision_status,
            execution_status=execution_status,
            error_reason=error_reason,
            additional_context=ctx,
        )
