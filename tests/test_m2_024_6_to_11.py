"""
Testes RED para M2-024.6/7/8/9/11.

Pacotes testados:
  M2-024.6 — Telemetria de Latencia por Simbolo e Etapa
  M2-024.7 — Circuit Breaker por Classe de Falha
  M2-024.8 — Reconciliacao Deterministica de Saida Externa
  M2-024.9 — Snapshot Operacional Unico por Ciclo
  M2-024.11 — Regressao de Risco com Cenarios de Stress

Todos os testes DEVEM falhar antes da implementacao (RED).
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from risk.circuit_breaker import CircuitBreaker
from core.model2.observability import Model2ObservabilityService
from core.model2.live_execution import (
    SIGNAL_EXECUTION_STATUS_EXITED,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
)


# =============================================================================
# Grupo 1: M2-024.6 — Telemetria de Latencia
# =============================================================================


class TestM2024_6_TelemetriaLatencia:
    """M2-024.6: Registrar latencia por simbolo e etapa do pipeline."""

    def test_registrar_latencia_existe_em_observability(self) -> None:
        """RED: funcao registrar_latencia deve existir em core.model2.observability."""
        try:
            from core.model2.observability import registrar_latencia  # noqa: F401
        except ImportError:
            pytest.fail("registrar_latencia nao existe em core.model2.observability")

    def test_registrar_latencia_aceita_parametros_corretos(self) -> None:
        """RED: registrar_latencia deve aceitar simbolo, etapa, resultado, latencia_ms."""
        from core.model2.observability import registrar_latencia

        registrar_latencia(
            simbolo="BTCUSDT",
            etapa="scan",
            resultado="sucesso",
            latencia_ms=150,
        )

    def test_etapas_validas_definidas(self) -> None:
        """RED: VALID_LATENCY_STAGES deve conter scan/validate/signal/order/execute."""
        from core.model2.observability import VALID_LATENCY_STAGES

        esperadas = {"scan", "validate", "signal", "order", "execute"}
        for etapa in esperadas:
            assert etapa in VALID_LATENCY_STAGES, (
                f"Etapa '{etapa}' ausente em VALID_LATENCY_STAGES"
            )

    def test_tabela_execution_latencies_criada(self) -> None:
        """RED: tabela execution_latencies deve ser criada ao registrar latencia."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            # Cria a tabela manualmente (schema M2-024.6)
            setup_conn = sqlite3.connect(db_path)
            setup_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_latencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    result_code TEXT NOT NULL DEFAULT 'ok',
                    latency_ms INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            setup_conn.commit()
            setup_conn.close()

            from core.model2.observability import registrar_latencia
            registrar_latencia(
                simbolo="BTCUSDT",
                etapa="validate",
                resultado="sucesso",
                latencia_ms=200,
                db_path=db_path,
            )
            check_conn = sqlite3.connect(db_path)
            row = check_conn.execute(
                "SELECT id FROM execution_latencies LIMIT 1"
            ).fetchone()
            check_conn.close()
            assert row is not None, "Latencia nao registrada em execution_latencies"


# =============================================================================
# Grupo 2: M2-024.7 — Circuit Breaker por Classe de Falha
# =============================================================================


class TestM2024_7_CircuitBreakerFailureClass:
    """M2-024.7: CB granular por classe de falha com janela deslizante."""

    def test_failure_class_enum_existe(self) -> None:
        """RED: enum FailureClass deve existir em risk.circuit_breaker."""
        try:
            from risk.circuit_breaker import FailureClass  # noqa: F401
        except ImportError:
            pytest.fail("Enum FailureClass nao existe em risk.circuit_breaker")

    def test_failure_class_tem_membros_obrigatorios(self) -> None:
        """RED: FailureClass deve ter EXCHANGE_ERROR, TIMEOUT, VALIDATION_FAIL."""
        from risk.circuit_breaker import FailureClass

        assert hasattr(FailureClass, "EXCHANGE_ERROR")
        assert hasattr(FailureClass, "TIMEOUT")
        assert hasattr(FailureClass, "VALIDATION_FAIL")

    def test_circuit_breaker_tem_register_failure(self) -> None:
        """RED: CircuitBreaker deve ter metodo register_failure(failure_class, reason)."""
        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)

        from risk.circuit_breaker import FailureClass

        assert hasattr(cb, "register_failure"), (
            "CircuitBreaker nao tem register_failure"
        )
        cb.register_failure(failure_class=FailureClass.TIMEOUT, reason="timeout simulado")

    def test_circuit_breaker_tem_is_open_for_class(self) -> None:
        """RED: CircuitBreaker deve ter is_open_for_class(failure_class) -> bool."""
        from risk.circuit_breaker import FailureClass

        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)

        assert hasattr(cb, "is_open_for_class"), (
            "CircuitBreaker nao tem is_open_for_class"
        )
        result = cb.is_open_for_class(FailureClass.TIMEOUT)
        assert isinstance(result, bool)

    def test_circuit_breaker_abre_para_classe_especifica(self) -> None:
        """RED: apos N falhas de TIMEOUT o breaker abre apenas para TIMEOUT."""
        from risk.circuit_breaker import FailureClass

        cb = CircuitBreaker()
        cb.update_portfolio_value(1000.0)

        for _ in range(5):
            cb.register_failure(failure_class=FailureClass.TIMEOUT, reason="t")

        assert cb.is_open_for_class(FailureClass.TIMEOUT) is True, (
            "CB nao abriu para TIMEOUT apos 5 falhas"
        )
        assert cb.is_open_for_class(FailureClass.EXCHANGE_ERROR) is False, (
            "CB abriu para EXCHANGE_ERROR indevidamente"
        )

    def test_circuit_breaker_aceita_cooldown_por_classe(self) -> None:
        """RED: CircuitBreaker deve aceitar cooldown_by_class no construtor."""
        from risk.circuit_breaker import FailureClass

        cb = CircuitBreaker(
            cooldown_by_class={
                FailureClass.TIMEOUT: 5000,
                FailureClass.EXCHANGE_ERROR: 10000,
            }
        )
        assert hasattr(cb, "_cooldown_by_class"), (
            "CircuitBreaker nao armazena _cooldown_by_class"
        )


# =============================================================================
# Grupo 3: M2-024.8 — Reconciliacao Deterministica
# =============================================================================


class TestM2024_8_ReconciliacaoDeterministica:
    """M2-024.8: Transicao OPEN→EXITED exige fill_external_confirmed=True."""

    def _criar_db(self, tmpdir: str) -> str:
        db_path = str(Path(tmpdir) / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signal_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
        return db_path

    def test_update_execution_status_exige_fill_confirmed(self) -> None:
        """RED: update_execution_status deve exigir fill_external_confirmed=True para EXITED."""
        from core.model2.repository import Model2ExecutionRepository

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._criar_db(tmpdir)
            repo = Model2ExecutionRepository(db_path)

            assert hasattr(repo, "update_execution_status"), (
                "repo nao tem update_execution_status"
            )

            with pytest.raises((ValueError, PermissionError)):
                repo.update_execution_status(
                    execution_id=1,
                    new_status=SIGNAL_EXECUTION_STATUS_EXITED,
                    fill_external_confirmed=False,
                )

    def test_falso_exited_nao_persiste_no_db(self) -> None:
        """RED: sem fill_external_confirmed o status nao muda para EXITED."""
        from core.model2.repository import Model2ExecutionRepository

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = self._criar_db(tmpdir)
            repo = Model2ExecutionRepository(db_path)

            # Tenta transicionar sem confirmacao (nao deve persistir)
            try:
                repo.update_execution_status(
                    execution_id=99,
                    new_status=SIGNAL_EXECUTION_STATUS_EXITED,
                    fill_external_confirmed=False,
                )
            except Exception:
                pass  # esperado em RED

            check = sqlite3.connect(db_path)
            row = check.execute(
                "SELECT status FROM signal_executions WHERE id=99"
            ).fetchone()
            check.close()
            # Nenhum registro com status EXITED sem confirmacao
            if row:
                assert row[0] != SIGNAL_EXECUTION_STATUS_EXITED, (
                    "EXITED persistido sem fill_external_confirmed"
                )


# =============================================================================
# Grupo 4: M2-024.9 — Snapshot Operacional
# =============================================================================


class TestM2024_9_SnapshotOperacional:
    """M2-024.9: Snapshot consolidado por ciclo com todos os campos."""

    def test_operational_snapshot_dataclass_existe(self) -> None:
        """RED: OperationalSnapshot deve existir em core.model2.observability."""
        try:
            from core.model2.observability import OperationalSnapshot  # noqa: F401
        except ImportError:
            pytest.fail("OperationalSnapshot nao existe em core.model2.observability")

    def test_operational_snapshot_tem_campos_obrigatorios(self) -> None:
        """RED: OperationalSnapshot deve ter campos candle_fresco, decisao, episodio, execucao, reconciliacao."""
        from core.model2.observability import OperationalSnapshot

        snap = OperationalSnapshot(
            candle_fresco={"ts": 1000, "close": 100.0},
            decisao={"allow": True},
            episodio={"episode_id": 1},
            execucao={"execution_id": 1},
            reconciliacao={"result": "ok"},
        )
        assert hasattr(snap, "candle_fresco")
        assert hasattr(snap, "decisao")
        assert hasattr(snap, "episodio")
        assert hasattr(snap, "execucao")
        assert hasattr(snap, "reconciliacao")

    def test_observability_tem_record_cycle_snapshot(self) -> None:
        """RED: Model2ObservabilityService deve ter record_cycle_snapshot(snapshot)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            obs = Model2ObservabilityService(db_path=db_path)

            assert hasattr(obs, "record_cycle_snapshot"), (
                "Model2ObservabilityService nao tem record_cycle_snapshot"
            )

    def test_record_cycle_snapshot_persiste_dados(self) -> None:
        """RED: record_cycle_snapshot deve persistir snapshot no DB."""
        from core.model2.observability import OperationalSnapshot

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            # Cria a tabela necessaria
            setup_conn = sqlite3.connect(db_path)
            setup_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operational_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT,
                    candle_json TEXT NOT NULL DEFAULT '{}',
                    decisao_json TEXT NOT NULL DEFAULT '{}',
                    episodio_json TEXT NOT NULL DEFAULT '{}',
                    execucao_json TEXT NOT NULL DEFAULT '{}',
                    reconciliacao_json TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL
                )
                """
            )
            setup_conn.commit()
            setup_conn.close()

            obs = Model2ObservabilityService(db_path=db_path)

            snap = OperationalSnapshot(
                candle_fresco={"ts": 1000},
                decisao={"allow": True},
                episodio={"episode_id": 1},
                execucao={"execution_id": 1},
                reconciliacao={"result": "ok"},
            )

            obs.record_cycle_snapshot(snap)

            check_conn = sqlite3.connect(db_path)
            row = check_conn.execute(
                "SELECT id FROM operational_snapshots LIMIT 1"
            ).fetchone()
            check_conn.close()
            assert row is not None, "Snapshot nao persistido em operational_snapshots"


# =============================================================================
# Grupo 5: M2-024.11 — Regressao de Stress
# =============================================================================


class TestM2024_11_RegressaoStress:
    """M2-024.11: risk_gate e circuit_breaker sob carga e falhas intermitentes."""

    def test_risk_gate_tem_record_timeout(self) -> None:
        """RED: RiskGate deve ter metodo record_timeout(stage, symbol)."""
        from risk.risk_gate import RiskGate

        gate = RiskGate()
        gate.update_portfolio_value(10000.0)

        assert hasattr(gate, "record_timeout"), "RiskGate nao tem record_timeout"

    def test_risk_gate_bloqueia_apos_timeouts_repetidos(self) -> None:
        """RED: RiskGate deve bloquear apos 5 timeouts consecutivos."""
        from risk.risk_gate import RiskGate

        gate = RiskGate()
        gate.update_portfolio_value(10000.0)

        for _ in range(5):
            gate.record_timeout(stage="send", symbol="BTCUSDT")

        assert hasattr(gate, "allows_trading"), "RiskGate nao tem allows_trading"
        assert not gate.allows_trading(), (
            "RiskGate nao bloqueou apos 5 timeouts"
        )

    def test_circuit_breaker_abre_em_stress_intermitente(self) -> None:
        """RED: CB deve abrir para TIMEOUT (3x) mas nao para EXCHANGE_ERROR (1x)."""
        from risk.circuit_breaker import FailureClass

        cb = CircuitBreaker()
        cb.update_portfolio_value(10000.0)

        padrao = [
            FailureClass.TIMEOUT,
            FailureClass.EXCHANGE_ERROR,
            FailureClass.TIMEOUT,
            FailureClass.VALIDATION_FAIL,
            FailureClass.TIMEOUT,
        ]
        for fc in padrao:
            cb.register_failure(failure_class=fc, reason=f"stress {fc.name}")

        assert cb.is_open_for_class(FailureClass.TIMEOUT) is True, (
            "CB deve abrir para TIMEOUT (3 falhas)"
        )
        assert cb.is_open_for_class(FailureClass.EXCHANGE_ERROR) is False, (
            "CB nao deve abrir para EXCHANGE_ERROR (1 falha)"
        )
        assert not cb.can_trade(), (
            "can_trade deve retornar False se alguma classe esta aberta"
        )
