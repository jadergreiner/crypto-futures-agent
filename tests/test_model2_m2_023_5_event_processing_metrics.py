"""Suite RED — M2-023.5: Metricas de processamento por classe de evento.

Cobre record_event_processing_time, get_event_processing_metrics e
reset_event_processing_times em core/model2/resilience_controls.py.

Criterio 3 de M2-023.5: metricas mostram tempo de tratamento por classe.
prioritize_events ja cobre criterios 1 e 2 (testados em suite batch).

ADRs: ADR-002 (safety envelope), ADR-009 (auditabilidade).
Guardrails: risk_gate e circuit_breaker nao sao mockados.

Casos:
    RF-023.5.1 — sem registros, get_event_processing_metrics retorna {}
    RF-023.5.2 — registro CRITICAL acumula em metricas
    RF-023.5.3 — registro HIGH acumula separadamente de CRITICAL
    RF-023.5.4 — multiplos registros da mesma classe calculam mean correto
    RF-023.5.5 — campo count reflete quantidade de registros por classe
    RF-023.5.6 — reset_event_processing_times limpa estado para testes
    RF-023.5.7 — classes desconhecidas sao aceitas sem excecao (fail-safe)
    RF-023.5.8 — elapsed_ms negativo ou zero e aceito sem excecao
    RF-023.5.9 — prioritize_events (criterios 1+2): CRITICAL < HIGH < WARN
    RF-023.5.10 — metricas de classes distintas sao independentes entre si
"""

from __future__ import annotations

import importlib
from typing import Any


def _load_target_module() -> Any:
    return importlib.import_module("core.model2.resilience_controls")


# ---------------------------------------------------------------------------
# RF-023.5.1
# ---------------------------------------------------------------------------
def test_sem_registros_get_metricas_retorna_dict_vazio() -> None:
    """Sem registros, get_event_processing_metrics retorna {}."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    result = mod.get_event_processing_metrics()

    assert isinstance(result, dict)
    assert result == {}


# ---------------------------------------------------------------------------
# RF-023.5.2
# ---------------------------------------------------------------------------
def test_registro_critical_acumula_nas_metricas() -> None:
    """record_event_processing_time CRITICAL aparece em metricas."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("CRITICAL", 50.0)
    metrics = mod.get_event_processing_metrics()

    assert "CRITICAL" in metrics
    assert metrics["CRITICAL"]["mean_ms"] == 50.0
    assert metrics["CRITICAL"]["count"] == 1


# ---------------------------------------------------------------------------
# RF-023.5.3
# ---------------------------------------------------------------------------
def test_registro_high_acumula_separado_de_critical() -> None:
    """Registros HIGH e CRITICAL ficam em classes separadas."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("CRITICAL", 30.0)
    mod.record_event_processing_time("HIGH", 80.0)
    metrics = mod.get_event_processing_metrics()

    assert "CRITICAL" in metrics
    assert "HIGH" in metrics
    assert metrics["CRITICAL"]["mean_ms"] == 30.0
    assert metrics["HIGH"]["mean_ms"] == 80.0


# ---------------------------------------------------------------------------
# RF-023.5.4
# ---------------------------------------------------------------------------
def test_multiplos_registros_mesma_classe_calculam_mean() -> None:
    """Varios registros na mesma classe retornam a media correta."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("WARN", 100.0)
    mod.record_event_processing_time("WARN", 200.0)
    mod.record_event_processing_time("WARN", 300.0)
    metrics = mod.get_event_processing_metrics()

    assert metrics["WARN"]["mean_ms"] == 200.0


# ---------------------------------------------------------------------------
# RF-023.5.5
# ---------------------------------------------------------------------------
def test_count_reflete_quantidade_de_registros_por_classe() -> None:
    """Campo count reflete quantas medicoes foram registradas."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("HIGH", 10.0)
    mod.record_event_processing_time("HIGH", 20.0)
    metrics = mod.get_event_processing_metrics()

    assert metrics["HIGH"]["count"] == 2


# ---------------------------------------------------------------------------
# RF-023.5.6
# ---------------------------------------------------------------------------
def test_reset_limpa_estado_entre_testes() -> None:
    """reset_event_processing_times zera todos os registros acumulados."""
    mod = _load_target_module()
    mod.record_event_processing_time("CRITICAL", 999.0)
    mod.reset_event_processing_times()

    result = mod.get_event_processing_metrics()

    assert result == {}


# ---------------------------------------------------------------------------
# RF-023.5.7
# ---------------------------------------------------------------------------
def test_classe_desconhecida_e_aceita_sem_excecao() -> None:
    """Classes fora do catalogo nao lancam excecao (fail-safe)."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("UNKNOWN_CLASS", 10.0)
    metrics = mod.get_event_processing_metrics()

    assert "UNKNOWN_CLASS" in metrics
    assert metrics["UNKNOWN_CLASS"]["count"] == 1


# ---------------------------------------------------------------------------
# RF-023.5.8
# ---------------------------------------------------------------------------
def test_elapsed_ms_zero_ou_negativo_aceito_sem_excecao() -> None:
    """elapsed_ms zero ou negativo e aceito sem lancar excecao."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("CRITICAL", 0.0)
    mod.record_event_processing_time("HIGH", -5.0)
    metrics = mod.get_event_processing_metrics()

    assert "CRITICAL" in metrics
    assert "HIGH" in metrics


# ---------------------------------------------------------------------------
# RF-023.5.9 — prioritize_events criterios 1+2 (regressao)
# ---------------------------------------------------------------------------
def test_prioritize_events_ordem_critical_high_warn() -> None:
    """prioritize_events garante CRITICAL < HIGH < WARN (criterios 1+2)."""
    mod = _load_target_module()
    events = [
        {"priority": "WARN", "id": "w1"},
        {"priority": "CRITICAL", "id": "c1"},
        {"priority": "HIGH", "id": "h1"},
    ]

    ordered = mod.prioritize_events(events)

    assert [e["id"] for e in ordered] == ["c1", "h1", "w1"]


# ---------------------------------------------------------------------------
# RF-023.5.10
# ---------------------------------------------------------------------------
def test_metricas_de_classes_distintas_sao_independentes() -> None:
    """Registros de classes diferentes nao interferem mutuamente."""
    mod = _load_target_module()
    mod.reset_event_processing_times()

    mod.record_event_processing_time("CRITICAL", 10.0)
    mod.record_event_processing_time("HIGH", 50.0)
    mod.record_event_processing_time("CRITICAL", 20.0)
    metrics = mod.get_event_processing_metrics()

    assert metrics["CRITICAL"]["mean_ms"] == 15.0
    assert metrics["HIGH"]["mean_ms"] == 50.0
    assert metrics["CRITICAL"]["count"] == 2
    assert metrics["HIGH"]["count"] == 1
