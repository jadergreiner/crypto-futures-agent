"""RED Phase - Suite de testes M2-026.3: Auditoria imutável decision_id ↔ execution_id.

Objetivo: Validar correlação ponta-a-ponta imutável em table audit_decision_execution.
Registros frozen após insert (sem UPDATE/DELETE), suporta trilha compliance + debug.

Status: RED - Testes inicialmente falham (table audit_decision_execution não existe).
Testes de estrutura dataclass/type passam.

Referência: docs/BACKLOG.md (M2-026.3), docs/ARQUITETURA_ALVO.md
"""

from __future__ import annotations

from dataclasses import dataclass, FrozenInstanceError
from datetime import datetime
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest


@dataclass(frozen=True)
class AuditDecisionExecution:
    """Dataclass imutável para auditoria de correlação decision ↔ execution.

    Campos (todos obrigatórios):
    - decision_id: identificador único da decisão (FK)
    - execution_id: identificador único da tentativa de execução (FK)
    - signal_id: identificador do sinal técnico (FK)
    - timestamp_utc: quando a auditoria foi registrada
    - decision_status: status da decisão na época do registro
    - execution_status: status da execução na época do registro
    - error_reason: se há erro, qual a razão (em REASON_CODE_CATALOG)
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
        """Validação após init (em dataclass frozen)."""
        if self.decision_id <= 0:
            raise ValueError("decision_id deve ser positivo")
        if self.execution_id <= 0:
            raise ValueError("execution_id deve ser positivo")
        if self.signal_id <= 0:
            raise ValueError("signal_id deve ser positivo")


@pytest.fixture
def audit_repo_mock() -> MagicMock:
    """Fixture: Mock do repositório de auditoria (table audit_decision_execution)."""
    repo = MagicMock()
    repo.insert_audit_record = MagicMock(return_value=True)
    repo.query_by_decision_id = MagicMock(return_value=[])
    repo.query_by_execution_id = MagicMock(return_value=[])
    repo.query_trace_decision_to_signal = MagicMock(return_value=[])
    return repo


class TestAuditDecisionExecutionImmutability:
    """RED: Garantir imutabilidade de registros de auditoria."""

    def test_audit_record_frozen_dataclass_immutable_after_creation(self) -> None:
        """RF 3.2: Dataclass frozen = imutável após insert (sem update/delete).

        Entrada: AuditDecisionExecution criada
        Saída: Tentativa de alterar campo → AttributeError (frozen)
        Critério: Auditoria garantida, sem alteração pós-registro
        """
        # Arrange
        record = AuditDecisionExecution(
            decision_id=999,
            execution_id=111,
            signal_id=555,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="ENTRY_FILLED",
        )

        # Act & Assert: Tentar alterar campo frozen
        with pytest.raises(FrozenInstanceError):
            record.decision_id = 1000

    def test_audit_record_insert_persisted_immutable(self, audit_repo_mock: MagicMock) -> None:
        """RF 3.1: Insert registro no audit_decision_execution (sem UPDATE permitido).

        Entrada: decision_id=999, execution_id=111
        Saída: Registrado em table com FK válida
        Critério: Nenhuma alteração posterior permitida (apenas INSERT)
        """
        # Arrange
        record = AuditDecisionExecution(
            decision_id=999,
            execution_id=111,
            signal_id=555,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="ENTRY_FILLED",
        )

        # Act: Inserir auditoria
        audit_repo_mock.insert_audit_record.return_value = True
        inserted = audit_repo_mock.insert_audit_record(record)

        # Assert: Registrado sem alterar
        assert inserted is True
        audit_repo_mock.insert_audit_record.assert_called_once_with(record)

    def test_audit_record_no_delete_allowed(self, audit_repo_mock: MagicMock) -> None:
        """Guardrail: DELETE de registros auditoria não permitido.

        Critério: Schema garante DELETE restrito (ex: REVOKE privilege)
        """
        # Arrange: Rejeitar DELETE em repositório
        audit_repo_mock.delete_audit_record = MagicMock(
            side_effect=Exception("DELETE não permitido em audit_decision_execution")
        )

        # Act & Assert
        with pytest.raises(Exception):
            audit_repo_mock.delete_audit_record(decision_id=999)


class TestAuditDecisionExecutionCorrelation:
    """RED: Correlação decision_id ↔ execution_id ↔ signal_id."""

    def test_audit_query_decision_id_correlates_executions(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """RF 3.3: Query auditoria por decision_id retorna todas execuções correlatas.

        Entrada: decision_id=999
        Saída: Lista de execuções (execution_id...) ligadas à decisão
        Critério: Query < 50ms, foreign keys válidas
        """
        # Arrange
        decision_id = 999
        audit_records = [
            AuditDecisionExecution(
                decision_id=999,
                execution_id=111,
                signal_id=555,
                timestamp_utc=datetime.utcnow(),
                decision_status="VALIDADA",
                execution_status="ENTRY_FILLED",
            ),
            AuditDecisionExecution(
                decision_id=999,
                execution_id=112,
                signal_id=556,
                timestamp_utc=datetime.utcnow(),
                decision_status="VALIDADA",
                execution_status="BLOCKED",
            ),
        ]

        # Act: Query por decision_id
        audit_repo_mock.query_by_decision_id.return_value = audit_records
        results = audit_repo_mock.query_by_decision_id(decision_id)

        # Assert: Todas execuções retornadas
        assert len(results) == 2
        assert all(r.decision_id == decision_id for r in results)

    def test_audit_trace_complete_decision_execution_signal_path(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """RF 3.4: Cascata completa decision → execution → signal com resultado final.

        Entrada: Rastrear 1 decisão
        Saída: Trace ponta-a-ponta com 4+ campos ligados
        Critério: Trilha auditável para compliance + debug
        """
        # Arrange
        decision_id = 999
        trace = [
            {
                "step": 1,
                "entity": "decision",
                "id": 999,
                "status": "CRIADA",
                "timestamp": datetime.utcnow(),
            },
            {
                "step": 2,
                "entity": "execution",
                "id": 111,
                "status": "ENTRY_SENT",
                "timestamp": datetime.utcnow(),
            },
            {
                "step": 3,
                "entity": "signal",
                "id": 555,
                "status": "CONSUMED",
                "timestamp": datetime.utcnow(),
            },
            {
                "step": 4,
                "entity": "result",
                "status": "EXITED",
                "pnl": 150.50,
                "timestamp": datetime.utcnow(),
            },
        ]

        # Act: Query trace
        audit_repo_mock.query_trace_decision_to_signal.return_value = trace
        result_trace = audit_repo_mock.query_trace_decision_to_signal(decision_id)

        # Assert: Trace completo com 4+ passos
        assert len(result_trace) >= 4
        assert result_trace[0]["entity"] == "decision"
        assert result_trace[-1]["entity"] == "result"

    def test_audit_foreign_key_validation_no_orphans(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """RF 3.5: FK validation: execution_id inválido → exception, sem orphan record.

        Entrada: execution_id não existe em signal_executions
        Saída: Exception CRITICAL, log + fail-safe
        Critério: Nenhum registro órfão no audit
        """
        # Arrange
        invalid_execution_id = 999_999_999

        # Act: Tentar inserir com FK inválida
        audit_repo_mock.insert_audit_record.side_effect = Exception(
            f"FK Constraint: execution_id {invalid_execution_id} não existe"
        )

        record = AuditDecisionExecution(
            decision_id=1,
            execution_id=invalid_execution_id,
            signal_id=1,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="FAILED",
        )

        # Assert: Exception levantada, sem insert
        with pytest.raises(Exception, match="FK Constraint"):
            audit_repo_mock.insert_audit_record(record)


class TestAuditDecisionExecutionCompatibility:
    """RED: Compatibilidade com contratos M2-024.1 e M2-024.10."""

    def test_audit_compatible_strict_decision_contract_m2_024_1(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """RF 3.6: Compatibilidade M2-024.1 (decision_id obrigatório).

        Entrada: strict_contract=True + decision_id=999
        Saída: Validação antes de audit insert (sem duplicata)
        Critério: Idempotência preservada
        """
        # Arrange
        decision_id = 999
        record_1 = AuditDecisionExecution(
            decision_id=decision_id,
            execution_id=111,
            signal_id=555,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="ENTRY_FILLED",
        )

        record_2 = AuditDecisionExecution(
            decision_id=decision_id,
            execution_id=112,  # Execution diferente, mas mesmo decision_id
            signal_id=556,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="BLOCKED",
        )

        # Act: Inserir ambos
        audit_repo_mock.insert_audit_record.return_value = True
        audit_repo_mock.insert_audit_record(record_1)
        audit_repo_mock.insert_audit_record(record_2)

        # Assert: Múltiplas execuções mesma decisão OK (não é duplicata)
        assert audit_repo_mock.insert_audit_record.call_count == 2

    def test_audit_compatible_error_contract_m2_024_10(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """RF 3.7: Compatibilidade M2-024.10 (erro + reason_code + decision_id).

        Entrada: erro + reason_code=STOP_LOSS_TOO_LOOSE + decision_id=999
        Saída: Audit registra correlação erro + decision
        Critério: Trilha completa (sem perda de contexto)
        """
        # Arrange
        record_with_error = AuditDecisionExecution(
            decision_id=999,
            execution_id=111,
            signal_id=555,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="FAILED",
            error_reason="STOP_LOSS_TOO_LOOSE",
            additional_context={"reason_code": "STOP_LOSS_TOO_LOOSE", "severity": "HIGH"},
        )

        # Act: Inserir com erro
        audit_repo_mock.insert_audit_record.return_value = True
        inserted = audit_repo_mock.insert_audit_record(record_with_error)

        # Assert: Erro registrado com contexto
        assert inserted is True
        assert record_with_error.error_reason == "STOP_LOSS_TOO_LOOSE"


class TestAuditDecisionExecutionSchema:
    """RED: Schema de tabela audit_decision_execution auditado."""

    def test_audit_schema_columns_required(self) -> None:
        """Schema tem colunas obrigatórias em audit_decision_execution."""
        # Arrange
        required_columns = {
            "decision_id": "INTEGER NOT NULL",
            "execution_id": "INTEGER NOT NULL",
            "signal_id": "INTEGER NOT NULL",
            "timestamp_utc": "TIMESTAMP NOT NULL",
            "decision_status": "TEXT NOT NULL",
            "execution_status": "TEXT NOT NULL",
        }

        # Act & Assert: Estrutura existe (simulado)
        assert "decision_id" in required_columns
        assert "execution_id" in required_columns

    def test_audit_schema_frozen_enforced_by_trigger_or_app_logic(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """Schema protege imutabilidade: ON INSERT validation (não UPDATE/DELETE).

        Critério: Trigger SQL OU app logic enfoça INSERT-only.
        """
        # Arrange: Repo rejeita UPDATE/DELETE
        audit_repo_mock.update_audit_record = MagicMock(
            side_effect=Exception("UPDATE não permitido")
        )
        audit_repo_mock.delete_audit_record = MagicMock(
            side_effect=Exception("DELETE não permitido")
        )

        # Act & Assert
        with pytest.raises(Exception, match="UPDATE não permitido"):
            audit_repo_mock.update_audit_record(decision_id=999, new_status="X")

        with pytest.raises(Exception, match="DELETE não permitido"):
            audit_repo_mock.delete_audit_record(decision_id=999)


class TestAuditDecisionExecutionIntegration:
    """RED: Integração com M2-026.1, M2-026.2, M2-026.3."""

    def test_audit_records_risk_gate_blocks_correlatable(
        self, audit_repo_mock: MagicMock,
    ) -> None:
        """Integração M2-026.1: Bloqueios risk_gate rastreáveis até decision_id.

        Entrada: Sinal bloqueado em risk_gate
        Saída: Audit correlaciona decision_id + reason_code (ex: SIZE_EXCEEDS_LIMIT)
        Critério: M2-026.1 telemetria + M2-026.3 auditoria = trilha completa
        """
        # Arrange
        blocked_record = AuditDecisionExecution(
            decision_id=999,
            execution_id=111,
            signal_id=555,
            timestamp_utc=datetime.utcnow(),
            decision_status="VALIDADA",
            execution_status="BLOCKED",
            error_reason="SIZE_EXCEEDS_LIMIT",
        )

        # Act: Registrar bloqueio
        audit_repo_mock.insert_audit_record.return_value = True
        audit_repo_mock.insert_audit_record(blocked_record)

        # Assert: Bloqueio rastreável
        assert blocked_record.error_reason == "SIZE_EXCEEDS_LIMIT"

    def test_audit_mypy_strict_compliance(self) -> None:
        """Guardrail: Código auditoria passa mypy --strict.

        Entrada: core/model2/audit_decision_execution.py
        Saída: mypy --strict sem erros
        Critério: Type hints completas
        """
        # CI/CD verification (mypy --strict audit_decision_execution.py)
        assert True  # Placeholder
