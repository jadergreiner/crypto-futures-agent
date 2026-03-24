"""RED Phase - Suite M2-027: Resiliencia e Fail-safe de Pipeline.

Cobre:
  R1: cycle_watchdog detecta ausencia de progressao em janela configuravel.
  R2: Fail-safe de interrupcao preserva estado sem corromper execucao em curso.
  R3: Schema M2 validado pre-ciclo; divergencia bloqueia com reason_code.
  R4: Posicoes orfas detectadas; saida segura com ORPHAN_POSITION.
  R5: Transicao CONSUMED->IN_PROGRESS atomica; revert logico em falha.
  R6: Eventos registrados em audit trail com decision_id e timestamp UTC.

Status: RED - testes devem FALHAR antes da implementacao.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# R1/R2 - cycle_watchdog (modulo a criar: core/model2/cycle_watchdog.py)
# ---------------------------------------------------------------------------

class TestCycleWatchdog:
    """R1/R2: Watchdog detecta travamento e aciona fail-safe."""

    def test_watchdog_detects_stalled_cycle_emits_reason_code(self) -> None:
        """R1: Ausencia de progressao por > window_seconds emite reason_code.

        Arrange: watchdog configurado com window=0 (janela expirada imediatamente)
        Act: check_progress() com last_progress_ts no passado
        Assert: resultado contem reason_code='cycle_stalled' e timestamp UTC
        """
        # Arrange
        from core.model2.cycle_watchdog import CycleWatchdog  # nao existe ainda

        wdog = CycleWatchdog(window_seconds=0)
        last_ts = time.time() - 10  # claramente expirado

        # Act
        result = wdog.check_progress(last_progress_ts=last_ts)

        # Assert
        assert result["stalled"] is True
        assert result["reason_code"] == "cycle_stalled"
        assert "timestamp_utc" in result

    def test_watchdog_healthy_cycle_returns_no_stall(self) -> None:
        """R1: Ciclo com progressao recente NAO e detectado como travado.

        Arrange: window=300, last_progress_ts = agora
        Act: check_progress()
        Assert: stalled=False
        """
        from core.model2.cycle_watchdog import CycleWatchdog

        wdog = CycleWatchdog(window_seconds=300)
        last_ts = time.time()

        result = wdog.check_progress(last_progress_ts=last_ts)

        assert result["stalled"] is False

    def test_watchdog_failsafe_preserves_state_on_interrupt(self) -> None:
        """R2: Fail-safe de interrupcao preserva contexto sem corromper estado.

        Arrange: watchdog com estado de ciclo em progresso
        Act: trigger_failsafe()
        Assert: resultado contem 'state_preserved'=True e 'interrupted'=True
        """
        from core.model2.cycle_watchdog import CycleWatchdog

        wdog = CycleWatchdog(window_seconds=0)
        cycle_state = {"symbol": "BTCUSDT", "step": "execute", "decision_id": 42}

        result = wdog.trigger_failsafe(cycle_state=cycle_state)

        assert result["interrupted"] is True
        assert result["state_preserved"] is True
        assert result["preserved_state"]["decision_id"] == 42

    def test_watchdog_failsafe_does_not_disable_risk_gate(self) -> None:
        """R2: Fail-safe NAO desabilita risk_gate ou circuit_breaker.

        Arrange: watchdog instanciado
        Act: trigger_failsafe()
        Assert: 'risk_gate_disabled'=False no resultado
        """
        from core.model2.cycle_watchdog import CycleWatchdog

        wdog = CycleWatchdog(window_seconds=0)

        result = wdog.trigger_failsafe(cycle_state={})

        assert result.get("risk_gate_disabled") is False
        assert result.get("circuit_breaker_disabled") is False

    def test_watchdog_failsafe_emits_audit_event(self) -> None:
        """R6: Fail-safe emite evento com decision_id e timestamp_utc para audit.

        Arrange: ciclo com decision_id=99
        Act: trigger_failsafe()
        Assert: audit_event contem decision_id e timestamp_utc
        """
        from core.model2.cycle_watchdog import CycleWatchdog

        wdog = CycleWatchdog(window_seconds=0)
        cycle_state = {"decision_id": 99}

        result = wdog.trigger_failsafe(cycle_state=cycle_state)

        assert "audit_event" in result
        assert result["audit_event"]["decision_id"] == 99
        assert "timestamp_utc" in result["audit_event"]


# ---------------------------------------------------------------------------
# R3 - Schema pre-execucao (novo helper em go_live_preflight ou live_service)
# ---------------------------------------------------------------------------

class TestSchemaPreExecValidation:
    """R3: Validacao de schema M2 bloqueia ciclo se houver divergencia."""

    def test_schema_validation_passes_with_all_required_tables(self, tmp_path: Any) -> None:
        """R3: Schema completo retorna status='ok' e nao bloqueia ciclo.

        Arrange: DB temporario com todas as tabelas obrigatorias
        Act: validate_schema_pre_exec(db_path)
        Assert: result['status']='ok'
        """
        import sqlite3
        from core.model2.cycle_watchdog import validate_schema_pre_exec  # nao existe ainda

        db_path = tmp_path / "modelo2_test.db"
        required_tables = [
            "schema_migrations", "technical_signals", "signal_executions",
            "signal_execution_events", "signal_execution_snapshots",
            "audit_decision_execution",
        ]
        with sqlite3.connect(db_path) as conn:
            for table in required_tables:
                conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")

        result = validate_schema_pre_exec(db_path=db_path)

        assert result["status"] == "ok"

    def test_schema_validation_blocks_missing_table(self, tmp_path: Any) -> None:
        """R3: Tabela obrigatoria ausente bloqueia com reason_code padronizado.

        Arrange: DB sem tabela audit_decision_execution
        Act: validate_schema_pre_exec(db_path)
        Assert: result['status']='blocked', reason_code='schema_divergence'
        """
        import sqlite3
        from core.model2.cycle_watchdog import validate_schema_pre_exec

        db_path = tmp_path / "modelo2_partial.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE schema_migrations (id INTEGER PRIMARY KEY)")

        result = validate_schema_pre_exec(db_path=db_path)

        assert result["status"] == "blocked"
        assert result["reason_code"] == "schema_divergence"

    def test_schema_validation_missing_db_blocks(self, tmp_path: Any) -> None:
        """R3: DB ausente bloqueia com reason_code='db_not_found'.

        Arrange: caminho inexistente
        Act: validate_schema_pre_exec(db_path)
        Assert: reason_code='db_not_found'
        """
        from core.model2.cycle_watchdog import validate_schema_pre_exec

        db_path = tmp_path / "nao_existe.db"
        result = validate_schema_pre_exec(db_path=db_path)

        assert result["status"] == "blocked"
        assert result["reason_code"] == "db_not_found"


# ---------------------------------------------------------------------------
# R4 - Posicoes orfas (novo detector)
# ---------------------------------------------------------------------------

class TestOrphanPositionDetection:
    """R4: Posicoes orfas detectadas e saida segura acionada."""

    def test_orphan_position_detected_when_no_signal_execution(self) -> None:
        """R4: Posicao aberta na Binance sem signal_execution gera ORPHAN_POSITION.

        Arrange: exchange retorna posicao BTCUSDT; signal_executions vazio
        Act: detect_orphan_positions(exchange_positions, db_executions)
        Assert: resultado contem orphan com reason_code='orphan_position'
        """
        from core.model2.cycle_watchdog import detect_orphan_positions  # nao existe ainda

        exchange_positions = [{"symbol": "BTCUSDT", "positionAmt": "0.01"}]
        db_executions: list[dict[str, Any]] = []

        result = detect_orphan_positions(
            exchange_positions=exchange_positions,
            db_executions=db_executions,
        )

        assert len(result["orphans"]) == 1
        assert result["orphans"][0]["reason_code"] == "orphan_position"
        assert result["orphans"][0]["symbol"] == "BTCUSDT"

    def test_no_orphan_when_position_matched_to_execution(self) -> None:
        """R4: Posicao com signal_execution correspondente NAO e orfa.

        Arrange: exchange position BTCUSDT; db_execution com BTCUSDT IN_PROGRESS
        Act: detect_orphan_positions(...)
        Assert: orphans = []
        """
        from core.model2.cycle_watchdog import detect_orphan_positions

        exchange_positions = [{"symbol": "BTCUSDT", "positionAmt": "0.01"}]
        db_executions = [{"symbol": "BTCUSDT", "status": "IN_PROGRESS"}]

        result = detect_orphan_positions(
            exchange_positions=exchange_positions,
            db_executions=db_executions,
        )

        assert result["orphans"] == []

    def test_orphan_position_reason_code_in_catalog(self) -> None:
        """R4: reason_code 'orphan_position' existe no REASON_CODE_CATALOG.

        Assert: catalog contem 'orphan_position'
        """
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "orphan_position" in REASON_CODE_CATALOG

    def test_orphan_exit_uses_stop_market_not_market(self) -> None:
        """R4 invariante: saida de posicao orfa usa STOP_MARKET, nunca MARKET.

        Arrange: orphan detectado
        Act: build_orphan_exit_order(orphan)
        Assert: order_type='STOP_MARKET'
        """
        from core.model2.cycle_watchdog import build_orphan_exit_order

        orphan = {"symbol": "BTCUSDT", "positionAmt": "0.01", "reason_code": "orphan_position"}

        order = build_orphan_exit_order(orphan=orphan)

        assert order["order_type"] == "STOP_MARKET"
        assert order["order_type"] != "MARKET"

    def test_orphan_exit_emits_audit_event_with_synthetic_decision_id(self) -> None:
        """R6: Saida orfa gera audit_event com decision_id sintetico e timestamp_utc.

        Arrange: orphan sem decision_id real
        Act: build_orphan_exit_order(orphan)
        Assert: audit_event.decision_id nao e None; timestamp_utc presente
        """
        from core.model2.cycle_watchdog import build_orphan_exit_order

        orphan = {"symbol": "ETHUSDT", "positionAmt": "-0.1", "reason_code": "orphan_position"}

        order = build_orphan_exit_order(orphan=orphan)

        assert "audit_event" in order
        assert order["audit_event"]["decision_id"] is not None
        assert "timestamp_utc" in order["audit_event"]


# ---------------------------------------------------------------------------
# R5 - Consistencia transacional CONSUMED->IN_PROGRESS
# ---------------------------------------------------------------------------

class TestTransactionalConsistency:
    """R5: Transicao CONSUMED->IN_PROGRESS atomica com revert em falha."""

    def test_atomic_transition_succeeds_both_writes(self) -> None:
        """R5: Quando ambas as escritas funcionam, transicao persiste.

        Arrange: mock de persist_consumed e persist_in_progress sem erros
        Act: execute_atomic_state_transition(signal_id, execution_id)
        Assert: result['committed'] = True; nenhum revert
        """
        from core.model2.cycle_watchdog import execute_atomic_state_transition

        mock_persist_consumed = MagicMock(return_value=True)
        mock_persist_in_progress = MagicMock(return_value=True)

        result = execute_atomic_state_transition(
            signal_id=1,
            execution_id=10,
            persist_consumed_fn=mock_persist_consumed,
            persist_in_progress_fn=mock_persist_in_progress,
        )

        assert result["committed"] is True
        assert result.get("reverted") is False

    def test_atomic_transition_reverts_when_second_write_fails(self) -> None:
        """R5: Falha na 2a escrita (IN_PROGRESS) dispara revert do CONSUMED.

        Arrange: persist_consumed ok; persist_in_progress lanca excecao
        Act: execute_atomic_state_transition(...)
        Assert: result['reverted']=True; result['committed']=False
        """
        from core.model2.cycle_watchdog import execute_atomic_state_transition

        mock_persist_consumed = MagicMock(return_value=True)
        mock_persist_in_progress = MagicMock(side_effect=RuntimeError("db error"))
        mock_revert = MagicMock(return_value=True)

        result = execute_atomic_state_transition(
            signal_id=1,
            execution_id=10,
            persist_consumed_fn=mock_persist_consumed,
            persist_in_progress_fn=mock_persist_in_progress,
            revert_consumed_fn=mock_revert,
        )

        assert result["reverted"] is True
        assert result["committed"] is False
        mock_revert.assert_called_once()

    def test_atomic_transition_records_audit_event(self) -> None:
        """R6: Transicao atomica registra audit_event com decision_id e timestamp_utc.

        Arrange: transicao bem sucedida com decision_id=55
        Act: execute_atomic_state_transition(decision_id=55, ...)
        Assert: result['audit_event']['decision_id']=55; timestamp_utc presente
        """
        from core.model2.cycle_watchdog import execute_atomic_state_transition

        result = execute_atomic_state_transition(
            signal_id=2,
            execution_id=20,
            decision_id=55,
            persist_consumed_fn=MagicMock(return_value=True),
            persist_in_progress_fn=MagicMock(return_value=True),
        )

        assert "audit_event" in result
        assert result["audit_event"]["decision_id"] == 55
        assert "timestamp_utc" in result["audit_event"]

    def test_atomic_transition_no_partial_state_on_revert(self) -> None:
        """R5 invariante: estado parcial nunca persiste apos revert.

        Arrange: segunda escrita falha; revert chamado
        Act: execute_atomic_state_transition(...)
        Assert: result['partial_state_persisted']=False
        """
        from core.model2.cycle_watchdog import execute_atomic_state_transition

        result = execute_atomic_state_transition(
            signal_id=3,
            execution_id=30,
            persist_consumed_fn=MagicMock(return_value=True),
            persist_in_progress_fn=MagicMock(side_effect=RuntimeError("fail")),
            revert_consumed_fn=MagicMock(return_value=True),
        )

        assert result.get("partial_state_persisted") is False
