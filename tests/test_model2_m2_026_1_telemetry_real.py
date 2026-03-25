"""RED Phase - Suite real M2-026.1: RiskGateBlockEvent + RiskGateTelemetryRecorder.

Objetivo: Validar implementacao real (nao-mock) dos componentes de telemetria
de bloqueio do risk_gate: dataclass frozen, recorder append-only e query_by_reason.

Status: RED — falha por ImportError (modulo nao existe ainda).
Referencia: docs/BACKLOG.md (M2-026.1)
"""

from __future__ import annotations

import pytest


# R1 — RiskGateBlockEvent frozen dataclass
class TestRiskGateBlockEvent:
    """R1: frozen dataclass com campos obrigatorios tipados."""

    def test_block_event_criado_com_campos_obrigatorios(self) -> None:
        """R1.1: RiskGateBlockEvent instanciado com todos os campos."""
        # Arrange / Act
        from core.model2.risk_gate_telemetry import RiskGateBlockEvent  # RED
        event = RiskGateBlockEvent(
            reason_code="SIZE_EXCEEDS_LIMIT",
            condition="position_size > max_exposure",
            limit_value=1.0,
            actual_value=1.5,
            decision_id=123,
            timestamp_ms=1_700_000_000_000,
        )
        # Assert
        assert event.reason_code == "SIZE_EXCEEDS_LIMIT"
        assert event.decision_id == 123
        assert event.limit_value == 1.0
        assert event.actual_value == 1.5

    def test_block_event_e_imutavel(self) -> None:
        """R1.2: frozen=True impede modificacao pos-criacao."""
        from core.model2.risk_gate_telemetry import RiskGateBlockEvent  # RED
        event = RiskGateBlockEvent(
            reason_code="STOP_LOSS_TOO_LOOSE",
            condition="stop_loss_pct > min_stop",
            limit_value=-0.08,
            actual_value=-0.05,
            decision_id=456,
            timestamp_ms=1_700_000_000_001,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.reason_code = "OUTRO"  # type: ignore[misc]

    def test_block_event_reason_code_em_catalog(self) -> None:
        """R1.3: reason_code do evento esta no REASON_CODE_CATALOG."""
        from core.model2.risk_gate_telemetry import RiskGateBlockEvent  # RED
        from core.model2.live_execution import REASON_CODE_CATALOG
        event = RiskGateBlockEvent(
            reason_code="SIZE_EXCEEDS_LIMIT",
            condition="size check",
            limit_value=1.0,
            actual_value=2.0,
            decision_id=1,
            timestamp_ms=1_700_000_000_002,
        )
        assert event.reason_code in REASON_CODE_CATALOG

    def test_block_event_campos_com_tipos_corretos(self) -> None:
        """R1.4: Campos tipados: reason_code str, values float, decision_id int."""
        from core.model2.risk_gate_telemetry import RiskGateBlockEvent  # RED
        event = RiskGateBlockEvent(
            reason_code="risk_gate_blocked",
            condition="drawdown exceeded",
            limit_value=-3.0,
            actual_value=-3.5,
            decision_id=999,
            timestamp_ms=1_700_000_000_003,
        )
        assert isinstance(event.reason_code, str)
        assert isinstance(event.limit_value, float)
        assert isinstance(event.actual_value, float)
        assert isinstance(event.decision_id, int)
        assert isinstance(event.timestamp_ms, int)


# R2 — RiskGateTelemetryRecorder append-only
class TestRiskGateTelemetryRecorder:
    """R2: recorder com record() e query_by_reason()."""

    def test_recorder_vazio_retorna_zero_eventos(self) -> None:
        """R2.1: Recorder novo tem lista vazia."""
        from core.model2.risk_gate_telemetry import RiskGateTelemetryRecorder  # RED
        recorder = RiskGateTelemetryRecorder()
        assert recorder.total_events() == 0

    def test_recorder_registra_evento_e_incrementa_contagem(self) -> None:
        """R2.2: Apos record(), total_events() == 1."""
        from core.model2.risk_gate_telemetry import (  # RED
            RiskGateBlockEvent,
            RiskGateTelemetryRecorder,
        )
        recorder = RiskGateTelemetryRecorder()
        event = RiskGateBlockEvent(
            reason_code="SIZE_EXCEEDS_LIMIT",
            condition="size check",
            limit_value=1.0,
            actual_value=1.5,
            decision_id=10,
            timestamp_ms=1_700_000_000_010,
        )
        recorder.record(event)
        assert recorder.total_events() == 1

    def test_query_by_reason_retorna_count_e_percentual(self) -> None:
        """R2.3: query_by_reason() retorna dict com count e percentage por reason_code."""
        from core.model2.risk_gate_telemetry import (  # RED
            RiskGateBlockEvent,
            RiskGateTelemetryRecorder,
        )
        recorder = RiskGateTelemetryRecorder()
        for i in range(4):
            recorder.record(RiskGateBlockEvent(
                reason_code="SIZE_EXCEEDS_LIMIT",
                condition="size",
                limit_value=1.0,
                actual_value=1.5,
                decision_id=i,
                timestamp_ms=1_700_000_000_000 + i,
            ))
        recorder.record(RiskGateBlockEvent(
            reason_code="STOP_LOSS_TOO_LOOSE",
            condition="sl",
            limit_value=-0.08,
            actual_value=-0.05,
            decision_id=99,
            timestamp_ms=1_700_000_000_099,
        ))
        result = recorder.query_by_reason()
        # Assert structure
        assert "SIZE_EXCEEDS_LIMIT" in result
        assert result["SIZE_EXCEEDS_LIMIT"]["count"] == 4
        assert result["SIZE_EXCEEDS_LIMIT"]["percentage"] == pytest.approx(80.0)
        assert result["STOP_LOSS_TOO_LOOSE"]["count"] == 1
        assert result["STOP_LOSS_TOO_LOOSE"]["percentage"] == pytest.approx(20.0)

    def test_recorder_lista_imutavel_externamente(self) -> None:
        """R2.4: Retorno de eventos nao permite mutacao da lista interna."""
        from core.model2.risk_gate_telemetry import (  # RED
            RiskGateBlockEvent,
            RiskGateTelemetryRecorder,
        )
        recorder = RiskGateTelemetryRecorder()
        event = RiskGateBlockEvent(
            reason_code="SIZE_EXCEEDS_LIMIT",
            condition="c",
            limit_value=1.0,
            actual_value=2.0,
            decision_id=5,
            timestamp_ms=1_700_000_000_005,
        )
        recorder.record(event)
        # Mutacao da copia nao afeta interno
        events_copy = recorder.all_events()
        events_copy.clear()
        assert recorder.total_events() == 1


# R3 — Hook em live_service (integracao minima)
class TestRiskGateTelemetryHook:
    """R3: live_service expoe recorder acessivel apos bloqueio."""

    def test_live_service_tem_atributo_risk_gate_telemetry(self) -> None:
        """R3.1: LiveService inicializado possui _risk_gate_telemetry."""
        from core.model2.risk_gate_telemetry import RiskGateTelemetryRecorder
        from core.model2.live_service import Model2LiveExecutionService
        svc = Model2LiveExecutionService.__new__(Model2LiveExecutionService)
        svc._risk_gate_telemetry = RiskGateTelemetryRecorder()
        assert hasattr(svc, "_risk_gate_telemetry")
        assert isinstance(svc._risk_gate_telemetry, RiskGateTelemetryRecorder)

    def test_get_risk_gate_telemetry_recorder_disponivel(self) -> None:
        """R3.2: Modulo expoe get_risk_gate_telemetry_recorder() factory."""
        from core.model2.risk_gate_telemetry import (  # RED
            RiskGateTelemetryRecorder,
            get_risk_gate_telemetry_recorder,
        )
        recorder = get_risk_gate_telemetry_recorder()
        assert isinstance(recorder, RiskGateTelemetryRecorder)
