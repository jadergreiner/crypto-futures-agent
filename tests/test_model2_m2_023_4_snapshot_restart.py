"""Suite RED/GREEN para M2-023.4 - Snapshot de estado para restart seguro.

Cobre:
    RF-023.4.1  - Snapshot valido retorna valid_snapshot=True
    RF-023.4.2  - Snapshot sem campos obrigatorios retorna valid_snapshot=False
    RF-023.4.3  - has_open_order=True bloqueia send_new_order (anti-duplicidade)
    RF-023.4.4  - Fase ENTRY_FILLED com has_open_order=False nao reordena
    RF-023.4.5  - decision_id exposto no resultado para auditoria
    RF-023.4.6  - phase exposta no resultado
    RF-023.4.7  - heartbeat_ms exposto no resultado
    RF-023.4.8  - replay_mode sempre idempotent_resume
    RF-023.4.9  - Snapshot vazio e fail-safe (sem excecao, valid_snapshot=False)
    RF-023.4.10 - Funcao pura: mesmas entradas produzem mesmo resultado
    RF-023.4.11 - Guardrails risk_gate e circuit_breaker preservados
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# RF-023.4.1 - Snapshot valido retorna valid_snapshot=True
# ---------------------------------------------------------------------------
def test_snapshot_valido_retorna_valid_snapshot_true() -> None:
    """RF-023.4.1: snapshot com os 3 campos obrigatorios deve ser valido."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 42,
        "phase": "ENTRY_FILLED",
        "heartbeat_ms": 1700000000000,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    assert result["valid_snapshot"] is True, (
        "Snapshot com decision_id, phase e heartbeat_ms deve ser valido"
    )


# ---------------------------------------------------------------------------
# RF-023.4.2 - Snapshot sem campos obrigatorios retorna valid_snapshot=False
# ---------------------------------------------------------------------------
def test_snapshot_sem_campos_obrigatorios_invalido() -> None:
    """RF-023.4.2: snapshot sem decision_id deve retornar valid_snapshot=False."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot_sem_id: dict[str, int | str] = {
        "phase": "ENTRY_FILLED",
        "heartbeat_ms": 1700000000000,
    }

    result = plan_restart_from_snapshot(
        snapshot=snapshot_sem_id, has_open_order=False
    )

    assert result["valid_snapshot"] is False, (
        "Snapshot sem decision_id deve ser invalido"
    )


def test_snapshot_sem_phase_invalido() -> None:
    """RF-023.4.2b: snapshot sem phase deve retornar valid_snapshot=False."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot_sem_phase: dict[str, int | str] = {
        "decision_id": 10,
        "heartbeat_ms": 1700000000000,
    }

    result = plan_restart_from_snapshot(
        snapshot=snapshot_sem_phase, has_open_order=False
    )

    assert result["valid_snapshot"] is False, (
        "Snapshot sem phase deve ser invalido"
    )


def test_snapshot_sem_heartbeat_invalido() -> None:
    """RF-023.4.2c: snapshot sem heartbeat_ms deve retornar valid_snapshot=False."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot_sem_hb: dict[str, int | str] = {
        "decision_id": 10,
        "phase": "MONITORING",
    }

    result = plan_restart_from_snapshot(
        snapshot=snapshot_sem_hb, has_open_order=False
    )

    assert result["valid_snapshot"] is False, (
        "Snapshot sem heartbeat_ms deve ser invalido"
    )


# ---------------------------------------------------------------------------
# RF-023.4.3 - has_open_order=True bloqueia send_new_order (anti-duplicidade)
# ---------------------------------------------------------------------------
def test_has_open_order_true_bloqueia_send_new_order() -> None:
    """RF-023.4.3: ordem ja aberta nao deve gerar nova ordem (anti-duplicidade)."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 99,
        "phase": "PROTECTION_ARMED",
        "heartbeat_ms": 1700000000001,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=True)

    assert result["send_new_order"] is False, (
        "has_open_order=True deve garantir send_new_order=False (anti-duplicidade)"
    )


# ---------------------------------------------------------------------------
# RF-023.4.4 - Fase ENTRY_FILLED com has_open_order=False nao reordena
# ---------------------------------------------------------------------------
def test_fase_entry_filled_sem_ordem_nao_reordena() -> None:
    """RF-023.4.4: phase ENTRY_FILLED indica posicao ja existente, sem nova ordem."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 77,
        "phase": "ENTRY_FILLED",
        "heartbeat_ms": 123456,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    assert result["send_new_order"] is False, (
        "ENTRY_FILLED indica posicao ja existente: nao deve reordenar"
    )


# ---------------------------------------------------------------------------
# RF-023.4.5 - decision_id exposto no resultado
# ---------------------------------------------------------------------------
def test_decision_id_exposto_no_resultado() -> None:
    """RF-023.4.5: decision_id do snapshot deve aparecer na saida para auditoria."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 555,
        "phase": "MONITORING",
        "heartbeat_ms": 9999999,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    assert "decision_id" in result, "Campo decision_id ausente no resultado"
    assert result["decision_id"] == 555, (
        f"decision_id deve ser 555, obteve: {result.get('decision_id')}"
    )


# ---------------------------------------------------------------------------
# RF-023.4.6 - phase exposta no resultado
# ---------------------------------------------------------------------------
def test_phase_exposta_no_resultado() -> None:
    """RF-023.4.6: phase do snapshot deve aparecer na saida para auditoria."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 10,
        "phase": "PROTECTION_ARMED",
        "heartbeat_ms": 100,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    assert "phase" in result, "Campo phase ausente no resultado"
    assert result["phase"] == "PROTECTION_ARMED", (
        f"phase deve ser 'PROTECTION_ARMED', obteve: {result.get('phase')}"
    )


# ---------------------------------------------------------------------------
# RF-023.4.7 - heartbeat_ms exposto no resultado
# ---------------------------------------------------------------------------
def test_heartbeat_ms_exposto_no_resultado() -> None:
    """RF-023.4.7: heartbeat_ms do snapshot deve aparecer na saida."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 20,
        "phase": "ENTRY_FILLED",
        "heartbeat_ms": 1700500000000,
    }

    result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)

    assert "heartbeat_ms" in result, "Campo heartbeat_ms ausente no resultado"
    assert result["heartbeat_ms"] == 1700500000000, (
        f"heartbeat_ms incorreto: {result.get('heartbeat_ms')}"
    )


# ---------------------------------------------------------------------------
# RF-023.4.8 - replay_mode sempre idempotent_resume
# ---------------------------------------------------------------------------
def test_replay_mode_sempre_idempotent_resume() -> None:
    """RF-023.4.8: replay_mode deve ser sempre 'idempotent_resume'."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    for phase in ("ENTRY_FILLED", "PROTECTION_ARMED", "MONITORING", "CREATED"):
        snapshot = {
            "decision_id": 1,
            "phase": phase,
            "heartbeat_ms": 100,
        }
        result = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=False)
        assert result["replay_mode"] == "idempotent_resume", (
            f"replay_mode deve ser 'idempotent_resume' para phase={phase}"
        )


# ---------------------------------------------------------------------------
# RF-023.4.9 - Snapshot vazio: fail-safe sem excecao, valid_snapshot=False
# ---------------------------------------------------------------------------
def test_snapshot_vazio_fail_safe_sem_excecao() -> None:
    """RF-023.4.9: snapshot vazio nao deve gerar excecao (fail-safe)."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    try:
        result = plan_restart_from_snapshot(
            snapshot={}, has_open_order=False
        )
        assert isinstance(result, dict), "Resultado deve ser dict"
        assert result.get("valid_snapshot") is False, (
            "Snapshot vazio deve ter valid_snapshot=False"
        )
        assert result.get("send_new_order") is False, (
            "Snapshot vazio deve ter send_new_order=False (fail-safe)"
        )
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"Funcao nao deve lancar excecao com snapshot vazio: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# RF-023.4.10 - Funcao pura: mesmas entradas, mesma saida
# ---------------------------------------------------------------------------
def test_funcao_pura_resultado_deterministico() -> None:
    """RF-023.4.10: mesmas entradas devem produzir mesmo resultado (funcao pura)."""
    from core.model2.resilience_controls import plan_restart_from_snapshot

    snapshot = {
        "decision_id": 33,
        "phase": "ENTRY_FILLED",
        "heartbeat_ms": 5000,
    }

    result_a = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=True)
    result_b = plan_restart_from_snapshot(snapshot=snapshot, has_open_order=True)

    assert result_a == result_b, (
        "Funcao deve ser pura: mesmas entradas devem produzir mesmo resultado"
    )


# ---------------------------------------------------------------------------
# RF-023.4.11 - Guardrails risk_gate e circuit_breaker preservados
# ---------------------------------------------------------------------------
def test_guardrails_risk_gate_circuit_breaker_preservados() -> None:
    """RF-023.4.11: chamada da funcao nao altera risk_gate nem circuit_breaker."""
    from risk import risk_gate, circuit_breaker  # type: ignore[import]
    from core.model2.resilience_controls import plan_restart_from_snapshot

    rg_before = id(risk_gate)
    cb_before = id(circuit_breaker)

    plan_restart_from_snapshot(
        snapshot={"decision_id": 1, "phase": "MONITORING", "heartbeat_ms": 1},
        has_open_order=False,
    )

    assert id(risk_gate) == rg_before, "risk_gate nao deve ser alterado"
    assert id(circuit_breaker) == cb_before, "circuit_breaker nao deve ser alterado"
