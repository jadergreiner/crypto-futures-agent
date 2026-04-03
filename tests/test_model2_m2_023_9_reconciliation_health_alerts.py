"""Suite RED — M2-023.9: Indicadores de saude de reconciliacao.

Cobre check_reconciliation_health_alerts(metrics, thresholds) em
core/model2/resilience_controls.py.

ADRs: ADR-002 (safety envelope), ADR-009 (auditabilidade ponta a ponta).
Guardrails: risk_gate e circuit_breaker nao sao mockados.

Casos:
    RF-023.9.1 — metricas e limites vazios retornam lista vazia (fail-safe)
    RF-023.9.2 — drift_mean acima do limite gera alerta com severity WARN
    RF-023.9.3 — confirmation_p95_ms acima do limite gera alerta
    RF-023.9.4 — adjustment_rate acima do limite gera alerta
    RF-023.9.5 — todas as metricas abaixo dos limites nao geram alertas
    RF-023.9.6 — multiplos limites ultrapassados geram multiplos alertas
    RF-023.9.7 — alerta contem campos obrigatorios: severity, indicator_name,
                 value, threshold_exceeded
    RF-023.9.8 — limites ausentes (None) nao geram alertas para o indicador
    RF-023.9.9 — metricas ausentes no dict nao lancam excecao (fail-safe)
    RF-023.9.10 — thresholds podem ser configurados externamente (nao hardcoded)
"""

from __future__ import annotations

import importlib
from typing import Any


def _load_target_module() -> Any:
    return importlib.import_module("core.model2.resilience_controls")


# ---------------------------------------------------------------------------
# RF-023.9.1
# ---------------------------------------------------------------------------
def test_metricas_e_limites_vazios_retornam_lista_vazia() -> None:
    """Fail-safe: sem metricas e sem limites, nenhum alerta gerado."""
    mod = _load_target_module()

    result = mod.check_reconciliation_health_alerts({}, {})

    assert isinstance(result, list)
    assert result == []


# ---------------------------------------------------------------------------
# RF-023.9.2
# ---------------------------------------------------------------------------
def test_drift_mean_acima_do_limite_gera_alerta_warn() -> None:
    """drift_mean > drift_mean_limit dispara alerta WARN."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.5, "confirmation_p95_ms": 500.0,
               "adjustment_rate": 0.1}
    thresholds = {"drift_mean_limit": 0.3}

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert len(alerts) >= 1
    drift_alerts = [a for a in alerts if a["indicator_name"] == "drift_mean"]
    assert len(drift_alerts) == 1
    assert drift_alerts[0]["severity"] == "WARN"


# ---------------------------------------------------------------------------
# RF-023.9.3
# ---------------------------------------------------------------------------
def test_confirmation_p95_acima_do_limite_gera_alerta() -> None:
    """confirmation_p95_ms > p95_limit_ms dispara alerta."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.1, "confirmation_p95_ms": 2000.0,
               "adjustment_rate": 0.05}
    thresholds = {"p95_limit_ms": 1500.0}

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert len(alerts) >= 1
    p95_alerts = [a for a in alerts
                  if a["indicator_name"] == "confirmation_p95_ms"]
    assert len(p95_alerts) == 1


# ---------------------------------------------------------------------------
# RF-023.9.4
# ---------------------------------------------------------------------------
def test_adjustment_rate_acima_do_limite_gera_alerta() -> None:
    """adjustment_rate > adjustment_rate_limit dispara alerta."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.05, "confirmation_p95_ms": 800.0,
               "adjustment_rate": 0.6}
    thresholds = {"adjustment_rate_limit": 0.4}

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert len(alerts) >= 1
    rate_alerts = [a for a in alerts
                   if a["indicator_name"] == "adjustment_rate"]
    assert len(rate_alerts) == 1


# ---------------------------------------------------------------------------
# RF-023.9.5
# ---------------------------------------------------------------------------
def test_metricas_abaixo_dos_limites_nao_geram_alertas() -> None:
    """Todos os indicadores dentro dos limites: lista vazia."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.1, "confirmation_p95_ms": 800.0,
               "adjustment_rate": 0.2}
    thresholds = {
        "drift_mean_limit": 0.5,
        "p95_limit_ms": 1500.0,
        "adjustment_rate_limit": 0.5,
    }

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert alerts == []


# ---------------------------------------------------------------------------
# RF-023.9.6
# ---------------------------------------------------------------------------
def test_multiplos_limites_ultrapassados_geram_multiplos_alertas() -> None:
    """Dois indicadores acima do limite geram dois alertas distintos."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.9, "confirmation_p95_ms": 3000.0,
               "adjustment_rate": 0.1}
    thresholds = {
        "drift_mean_limit": 0.3,
        "p95_limit_ms": 1500.0,
        "adjustment_rate_limit": 0.5,
    }

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    indicator_names = [a["indicator_name"] for a in alerts]
    assert "drift_mean" in indicator_names
    assert "confirmation_p95_ms" in indicator_names
    assert len(alerts) == 2


# ---------------------------------------------------------------------------
# RF-023.9.7
# ---------------------------------------------------------------------------
def test_alerta_contem_campos_obrigatorios() -> None:
    """Cada alerta contem severity, indicator_name, value, threshold_exceeded."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.8}
    thresholds = {"drift_mean_limit": 0.3}

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert len(alerts) == 1
    alert = alerts[0]
    assert "severity" in alert
    assert "indicator_name" in alert
    assert "value" in alert
    assert "threshold_exceeded" in alert
    assert alert["indicator_name"] == "drift_mean"
    assert alert["value"] == 0.8
    assert alert["threshold_exceeded"] == 0.3


# ---------------------------------------------------------------------------
# RF-023.9.8
# ---------------------------------------------------------------------------
def test_limite_ausente_nao_gera_alerta_para_indicador() -> None:
    """Sem limite configurado para um indicador, nenhum alerta e gerado."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.9, "confirmation_p95_ms": 5000.0}
    thresholds = {"drift_mean_limit": 0.3}  # sem p95_limit_ms

    alerts = mod.check_reconciliation_health_alerts(metrics, thresholds)

    indicator_names = [a["indicator_name"] for a in alerts]
    assert "confirmation_p95_ms" not in indicator_names
    assert "drift_mean" in indicator_names


# ---------------------------------------------------------------------------
# RF-023.9.9
# ---------------------------------------------------------------------------
def test_metrica_ausente_no_dict_nao_lanca_excecao() -> None:
    """Metrica ausente no dict de metricas: sem excecao, alerta ignorado."""
    mod = _load_target_module()
    metrics: dict[str, float] = {}  # nenhuma metrica presente
    thresholds = {
        "drift_mean_limit": 0.3,
        "p95_limit_ms": 1500.0,
        "adjustment_rate_limit": 0.5,
    }

    result = mod.check_reconciliation_health_alerts(metrics, thresholds)

    assert isinstance(result, list)
    assert result == []


# ---------------------------------------------------------------------------
# RF-023.9.10
# ---------------------------------------------------------------------------
def test_thresholds_configurados_externamente() -> None:
    """Limites sao configurados pelo chamador, nao hardcoded na funcao."""
    mod = _load_target_module()
    metrics = {"drift_mean": 0.4}

    # Limite conservador: dispara alerta
    alertas_com = mod.check_reconciliation_health_alerts(
        metrics, {"drift_mean_limit": 0.2}
    )
    # Limite permissivo: sem alerta
    alertas_sem = mod.check_reconciliation_health_alerts(
        metrics, {"drift_mean_limit": 0.8}
    )

    assert len(alertas_com) == 1
    assert alertas_sem == []
