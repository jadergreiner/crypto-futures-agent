"""RED suite para pacote M2-023.2..023.10 + M2-027.2.

Cada teste mapeia 1 requisito do handoff SA->QA.
Estado esperado nesta fase: falhar inicialmente (RED).
"""

from __future__ import annotations

from pathlib import Path
import importlib
from types import ModuleType


def _load_target_module() -> ModuleType:
    return importlib.import_module("core.model2.resilience_controls")


def test_drift_gate_pre_admissao_drift_alto_bloqueia_com_reason_code() -> None:
    # Arrange
    mod = _load_target_module()
    current = {"position_qty": 1.0, "entry_price": 100.0}
    observed = {"position_qty": 1.4, "entry_price": 100.0}

    # Act
    result = mod.evaluate_position_drift_gate(
        current_state=current,
        observed_state=observed,
        threshold_pct=0.2,
        decision_id=101,
    )

    # Assert
    assert result["allow"] is False
    assert result["reason_code"] == "position_drift_blocked"
    assert result["decision_id"] == 101


def test_degradacao_latencia_p95_p99_acima_limite_entra_degraded() -> None:
    # Arrange
    mod = _load_target_module()
    metrics = {"p95_ms": 3500, "p99_ms": 8000}

    # Act
    state = mod.evaluate_latency_degradation(metrics, p95_limit_ms=2000, p99_limit_ms=5000)

    # Assert
    assert state["mode"] == "degraded"
    assert state["entry_reason"] == "latency_slo_breached"


def test_snapshot_restart_estado_valido_nao_reenvia_ordem() -> None:
    # Arrange
    mod = _load_target_module()
    snapshot = {"decision_id": 77, "phase": "ENTRY_FILLED", "heartbeat_ms": 123456}

    # Act
    plan = mod.plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    # Assert
    assert plan["replay_mode"] == "idempotent_resume"
    assert plan["send_new_order"] is False


def test_fila_priorizada_eventos_criticos_processa_antes_warn() -> None:
    # Arrange
    mod = _load_target_module()
    events = [
        {"priority": "WARN", "id": "w1"},
        {"priority": "CRITICAL", "id": "c1"},
        {"priority": "HIGH", "id": "h1"},
    ]

    # Act
    ordered = mod.prioritize_events(events)

    # Assert
    assert [e["id"] for e in ordered] == ["c1", "h1", "w1"]


def test_auditoria_risk_gate_consulta_por_decision_id_retorna_trilha() -> None:
    # Arrange
    mod = _load_target_module()
    trail = [
        {"decision_id": 501, "reason_code": "size_limit"},
        {"decision_id": 999, "reason_code": "ok"},
    ]

    # Act
    filtered = mod.query_risk_gate_audit_by_decision_id(trail, decision_id=501)

    # Assert
    assert len(filtered) == 1
    assert filtered[0]["reason_code"] == "size_limit"


def test_validacao_cruzada_sinal_contraditorio_bloqueia_fail_safe() -> None:
    # Arrange
    mod = _load_target_module()
    signal = {"side": "LONG", "confidence": 0.9}
    context = {"trend": "DOWN"}
    position = {"is_open": False}

    # Act
    result = mod.cross_validate_signal_context_position(signal, context, position)

    # Assert
    assert result["allow"] is False
    assert result["reason_code"] == "cross_validation_conflict"


def test_retry_por_categoria_falha_permanente_nao_reexecuta() -> None:
    # Arrange
    mod = _load_target_module()
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise ValueError("permanent")

    # Act
    out = mod.execute_with_category_retry(fn, category="permanent", max_attempts=4)

    # Assert
    assert out["ok"] is False
    assert calls["n"] == 1


def test_indicadores_reconciliacao_payload_contem_metricas_chave() -> None:
    # Arrange
    mod = _load_target_module()
    samples = [
        {"drift": 0.1, "confirm_ms": 1200, "adjusted": True},
        {"drift": 0.2, "confirm_ms": 1400, "adjusted": False},
    ]

    # Act
    payload = mod.compute_reconciliation_health_indicators(samples)

    # Assert
    assert "drift_mean" in payload
    assert "confirmation_p95_ms" in payload
    assert "adjustment_rate" in payload


def test_runbook_contingencia_arquivo_ausente_retorna_nao_pronto() -> None:
    # Arrange
    mod = _load_target_module()
    runbook = Path("docs/RUNBOOK_M2_CONTINGENCIA.md")

    # Act
    result = mod.validate_contingency_runbook(runbook)

    # Assert
    assert result["ready"] is False
    assert result["reason_code"] == "runbook_missing_or_invalid"


def test_schema_pre_exec_tabela_obrigatoria_ausente_bloqueia_ciclo() -> None:
    # Arrange
    mod = _load_target_module()
    fake_tables = {"technical_signals", "signal_executions"}

    # Act
    result = mod.validate_schema_tables(
        existing_tables=fake_tables,
        required_tables={"schema_migrations", "technical_signals", "signal_executions"},
    )

    # Assert
    assert result["ok"] is False
    assert result["reason_code"] == "schema_divergence"
