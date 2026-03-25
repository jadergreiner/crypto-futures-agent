"""Testes RED para M2-024.5 - Timeout padrao por etapa de execucao.

Fase: RED — devem FALHAR antes da implementacao.
Cobre: StageTimeoutPolicy, reason_codes TIMEOUT_*, gate admissao, telemetria.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from core.model2.order_layer import OrderLayerInput


# ---------------------------------------------------------------------------
# R1 — StageTimeoutPolicy (frozen dataclass)
# ---------------------------------------------------------------------------

class TestStageTimeoutPolicy:
    """R1: StageTimeoutPolicy com limites_ms por etapa e defaults seguros."""

    def test_policy_instancia_com_defaults_seguros(self) -> None:
        """StageTimeoutPolicy deve instanciar com valores default nao-zero."""
        from core.model2.execution_timeout import StageTimeoutPolicy

        policy = StageTimeoutPolicy()
        assert policy.admission_timeout_ms > 0
        assert policy.send_timeout_ms > 0
        assert policy.reconciliation_timeout_ms > 0

    def test_policy_e_frozen_dataclass(self) -> None:
        """StageTimeoutPolicy deve ser imutavel (frozen dataclass)."""
        from core.model2.execution_timeout import StageTimeoutPolicy
        from dataclasses import FrozenInstanceError

        policy = StageTimeoutPolicy()
        with pytest.raises(FrozenInstanceError):
            policy.admission_timeout_ms = 9999  # type: ignore[misc]

    def test_policy_aceita_valores_customizados(self) -> None:
        """StageTimeoutPolicy deve aceitar limites_ms customizados."""
        from core.model2.execution_timeout import StageTimeoutPolicy

        policy = StageTimeoutPolicy(
            admission_timeout_ms=500,
            send_timeout_ms=2000,
            reconciliation_timeout_ms=5000,
        )
        assert policy.admission_timeout_ms == 500
        assert policy.send_timeout_ms == 2000
        assert policy.reconciliation_timeout_ms == 5000

    def test_policy_rejeita_timeout_zero_ou_negativo(self) -> None:
        """StageTimeoutPolicy deve rejeitar limites <= 0."""
        from core.model2.execution_timeout import StageTimeoutPolicy

        with pytest.raises((ValueError, TypeError)):
            StageTimeoutPolicy(admission_timeout_ms=0)

    def test_policy_defaults_sao_valores_seguros_minimos(self) -> None:
        """Defaults devem ser >= 100ms para nao causar falsos positivos."""
        from core.model2.execution_timeout import StageTimeoutPolicy

        policy = StageTimeoutPolicy()
        assert policy.admission_timeout_ms >= 100
        assert policy.send_timeout_ms >= 100
        assert policy.reconciliation_timeout_ms >= 100


# ---------------------------------------------------------------------------
# R2 — REASON_CODE_CATALOG com TIMEOUT_*
# ---------------------------------------------------------------------------

class TestTimeoutReasonCodes:
    """R2: Reason_codes TIMEOUT_ADMISSION/SEND/RECONCILIATION no catalogo."""

    def test_timeout_admission_no_catalogo(self) -> None:
        """TIMEOUT_ADMISSION deve estar em REASON_CODE_CATALOG."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "TIMEOUT_ADMISSION" in REASON_CODE_CATALOG

    def test_timeout_send_no_catalogo(self) -> None:
        """TIMEOUT_SEND deve estar em REASON_CODE_CATALOG."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "TIMEOUT_SEND" in REASON_CODE_CATALOG

    def test_timeout_reconciliation_no_catalogo(self) -> None:
        """TIMEOUT_RECONCILIATION deve estar em REASON_CODE_CATALOG."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        assert "TIMEOUT_RECONCILIATION" in REASON_CODE_CATALOG

    def test_timeout_codes_tem_severity_high(self) -> None:
        """Todos TIMEOUT_* devem ter severity HIGH."""
        from core.model2.live_execution import REASON_CODE_SEVERITY

        for code in ("TIMEOUT_ADMISSION", "TIMEOUT_SEND", "TIMEOUT_RECONCILIATION"):
            assert REASON_CODE_SEVERITY.get(code) == "HIGH", f"{code} deve ser HIGH"

    def test_timeout_codes_tem_action_bloquear(self) -> None:
        """Todos TIMEOUT_* devem ter action bloquear_operacao."""
        from core.model2.live_execution import REASON_CODE_ACTION

        for code in ("TIMEOUT_ADMISSION", "TIMEOUT_SEND", "TIMEOUT_RECONCILIATION"):
            assert REASON_CODE_ACTION.get(code) == "bloquear_operacao", (
                f"{code} deve mapear para bloquear_operacao"
            )


# ---------------------------------------------------------------------------
# R3 — Gate de admissao em order_layer
# ---------------------------------------------------------------------------

class TestOrderLayerAdmissionTimeout:
    """R3: Gate de admissao com bloqueio auditavel por timeout."""

    def _make_input(self, decision_timestamp_ms: int, now_ms: int) -> "OrderLayerInput":
        """Cria OrderLayerInput com timestamps controlados."""
        from core.model2.order_layer import OrderLayerInput

        return OrderLayerInput(
            signal_id=1,
            opportunity_id=10,
            symbol="BTCUSDT",
            timeframe="5m",
            signal_side="SHORT",
            entry_type="MARKET",
            entry_price=50000.0,
            stop_loss=51000.0,
            take_profit=48000.0,
            status="CREATED",
            signal_timestamp=now_ms - 1000,
            payload={"decision_origin": "model"},
            decision_timestamp=decision_timestamp_ms,
            decision_id=42,
        )

    def test_admissao_dentro_do_timeout_retorna_consumed(self) -> None:
        """Admissao dentro do limite nao deve ser bloqueada por timeout."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_admission_timeout
        from core.model2.order_layer import TECHNICAL_SIGNAL_STATUS_CONSUMED

        now_ms = 1_000_000
        policy = StageTimeoutPolicy(admission_timeout_ms=5000)
        inp = self._make_input(decision_timestamp_ms=now_ms - 100, now_ms=now_ms)
        result = check_admission_timeout(inp, policy=policy, now_ms=now_ms)
        assert result is None  # None = sem bloqueio por timeout

    def test_admissao_expirada_retorna_reason_timeout_admission(self) -> None:
        """Admissao expirada deve retornar reason_code TIMEOUT_ADMISSION."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_admission_timeout

        now_ms = 1_000_000
        policy = StageTimeoutPolicy(admission_timeout_ms=500)
        inp = self._make_input(decision_timestamp_ms=now_ms - 1000, now_ms=now_ms)
        result = check_admission_timeout(inp, policy=policy, now_ms=now_ms)
        assert result is not None
        assert result.reason == "TIMEOUT_ADMISSION"

    def test_admissao_expirada_bloqueia_transicao(self) -> None:
        """Admissao expirada deve produzir should_transition=True com CANCELLED."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_admission_timeout
        from core.model2.order_layer import TECHNICAL_SIGNAL_STATUS_CANCELLED

        now_ms = 1_000_000
        policy = StageTimeoutPolicy(admission_timeout_ms=500)
        inp = self._make_input(decision_timestamp_ms=now_ms - 2000, now_ms=now_ms)
        result = check_admission_timeout(inp, policy=policy, now_ms=now_ms)
        assert result is not None
        assert result.should_transition is True
        assert result.target_status == TECHNICAL_SIGNAL_STATUS_CANCELLED

    def test_evaluate_signal_integra_timeout_admission(self) -> None:
        """evaluate_signal_for_order_layer deve rejeitar sinal com admissao expirada."""
        from core.model2.execution_timeout import StageTimeoutPolicy
        from core.model2.order_layer import OrderLayerInput, evaluate_signal_for_order_layer
        from core.model2.order_layer import TECHNICAL_SIGNAL_STATUS_CANCELLED

        now_ms = 1_000_000
        policy = StageTimeoutPolicy(admission_timeout_ms=100)
        inp = OrderLayerInput(
            signal_id=2,
            opportunity_id=20,
            symbol="BTCUSDT",
            timeframe="5m",
            signal_side="SHORT",
            entry_type="MARKET",
            entry_price=50000.0,
            stop_loss=51000.0,
            take_profit=48000.0,
            status="CREATED",
            signal_timestamp=now_ms - 500,
            payload={"decision_origin": "model"},
            decision_timestamp=now_ms - 5000,
            decision_id=43,
        )
        decision = evaluate_signal_for_order_layer(
            inp,
            authorized_symbols={"BTCUSDT"},
            timeout_policy=policy,
            now_ms=now_ms,
        )
        assert decision.target_status == TECHNICAL_SIGNAL_STATUS_CANCELLED
        assert "TIMEOUT_ADMISSION" in decision.reason


# ---------------------------------------------------------------------------
# R4 — Gate de envio/reconciliacao em live_service
# ---------------------------------------------------------------------------

class TestLiveServiceTimeoutCodes:
    """R4: reason_codes de timeout disponiveis para live_service usar."""

    def test_timeout_send_disponivel_no_catalogo(self) -> None:
        """TIMEOUT_SEND deve estar acessivel via REASON_CODE_CATALOG."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        entry = REASON_CODE_CATALOG.get("TIMEOUT_SEND")
        assert entry is not None
        assert "timeout" in entry.lower()

    def test_timeout_reconciliation_disponivel_no_catalogo(self) -> None:
        """TIMEOUT_RECONCILIATION deve estar acessivel via REASON_CODE_CATALOG."""
        from core.model2.live_execution import REASON_CODE_CATALOG

        entry = REASON_CODE_CATALOG.get("TIMEOUT_RECONCILIATION")
        assert entry is not None
        assert "timeout" in entry.lower()

    def test_check_send_timeout_dentro_do_limite(self) -> None:
        """check_send_timeout retorna None quando dentro do limite."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_send_timeout

        policy = StageTimeoutPolicy(send_timeout_ms=5000)
        result = check_send_timeout(elapsed_ms=100, policy=policy)
        assert result is None

    def test_check_send_timeout_expirado(self) -> None:
        """check_send_timeout retorna reason TIMEOUT_SEND quando expirado."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_send_timeout

        policy = StageTimeoutPolicy(send_timeout_ms=500)
        result = check_send_timeout(elapsed_ms=1000, policy=policy)
        assert result == "TIMEOUT_SEND"

    def test_check_reconciliation_timeout_dentro_do_limite(self) -> None:
        """check_reconciliation_timeout retorna None quando dentro do limite."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_reconciliation_timeout

        policy = StageTimeoutPolicy(reconciliation_timeout_ms=10_000)
        result = check_reconciliation_timeout(elapsed_ms=500, policy=policy)
        assert result is None

    def test_check_reconciliation_timeout_expirado(self) -> None:
        """check_reconciliation_timeout retorna TIMEOUT_RECONCILIATION quando expirado."""
        from core.model2.execution_timeout import StageTimeoutPolicy, check_reconciliation_timeout

        policy = StageTimeoutPolicy(reconciliation_timeout_ms=1000)
        result = check_reconciliation_timeout(elapsed_ms=5000, policy=policy)
        assert result == "TIMEOUT_RECONCILIATION"


# ---------------------------------------------------------------------------
# R5 — Telemetria via emit_stage_slo_violation_event
# ---------------------------------------------------------------------------

class TestTimeoutTelemetria:
    """R5: Telemetria emitida via emit_stage_slo_violation_event ao expirar."""

    def test_emit_timeout_telemetria_admissao(self) -> None:
        """emit_timeout_telemetria deve usar emit_stage_slo_violation_event."""
        from core.model2.execution_timeout import emit_timeout_telemetria

        payload = emit_timeout_telemetria(
            stage="admissao",
            elapsed_ms=2000,
            timeout_ms=500,
        )
        assert payload["event_type"] == "stage_slo_violation"
        assert payload["stage"] == "admissao"
        assert payload["latency_ms"] == 2000
        assert payload["slo_ms"] == 500

    def test_emit_timeout_telemetria_envio(self) -> None:
        """Telemetria para etapa envio deve ter stage='envio'."""
        from core.model2.execution_timeout import emit_timeout_telemetria

        payload = emit_timeout_telemetria(
            stage="envio",
            elapsed_ms=3000,
            timeout_ms=2000,
        )
        assert payload["stage"] == "envio"
        assert payload["latency_ms"] > payload["slo_ms"]

    def test_emit_timeout_telemetria_reconciliacao(self) -> None:
        """Telemetria para etapa reconciliacao deve ter stage='reconciliacao'."""
        from core.model2.execution_timeout import emit_timeout_telemetria

        payload = emit_timeout_telemetria(
            stage="reconciliacao",
            elapsed_ms=15_000,
            timeout_ms=10_000,
        )
        assert payload["stage"] == "reconciliacao"
        assert "timestamp" in payload

    def test_emit_timeout_telemetria_inclui_reason_code(self) -> None:
        """Payload de telemetria deve incluir reason_code canonico."""
        from core.model2.execution_timeout import emit_timeout_telemetria

        payload = emit_timeout_telemetria(
            stage="admissao",
            elapsed_ms=1000,
            timeout_ms=500,
            reason_code="TIMEOUT_ADMISSION",
        )
        assert payload.get("metadata", {}).get("reason_code") == "TIMEOUT_ADMISSION"


# ---------------------------------------------------------------------------
# Invariantes de risco — guardrails nao podem ser bypassados por timeout
# ---------------------------------------------------------------------------

class TestTimeoutGuardrailsNaoBypassados:
    """Guardrails: risk_gate e circuit_breaker nao podem ser bypassados por timeout."""

    def test_timeout_policy_nao_tem_referencia_a_risk_gate(self) -> None:
        """StageTimeoutPolicy nao deve importar nem alterar risk_gate."""
        import importlib
        import ast
        import pathlib

        src = pathlib.Path("core/model2/execution_timeout.py")
        if not src.exists():
            pytest.skip("modulo ainda nao existe (RED esperado)")
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imports = [
            node.module if isinstance(node, ast.ImportFrom) else ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        assert not any("risk_gate" in (m or "") for m in imports), (
            "execution_timeout.py nao deve importar risk_gate"
        )

    def test_timeout_policy_nao_tem_referencia_a_circuit_breaker(self) -> None:
        """StageTimeoutPolicy nao deve importar nem alterar circuit_breaker."""
        import ast
        import pathlib

        src = pathlib.Path("core/model2/execution_timeout.py")
        if not src.exists():
            pytest.skip("modulo ainda nao existe (RED esperado)")
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imports = [
            node.module if isinstance(node, ast.ImportFrom) else ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        assert not any("circuit_breaker" in (m or "") for m in imports), (
            "execution_timeout.py nao deve importar circuit_breaker"
        )
