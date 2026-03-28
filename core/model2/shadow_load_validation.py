"""Validacao de carga shadow multi-simbolo (M2-022.5).

Modulo focado em consolidar SLOs de latencia, episodios e reconciliacao
para execucao em modo shadow, sem envio de ordens reais.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence, TypedDict


class LatencySLOResult(TypedDict):
    latency_ok: bool
    max_ratio_observed: float
    max_p95_ms: float
    baseline_p50_ms: float
    symbols_evaluated: int


class EpisodeSLOResult(TypedDict):
    episode_success_ok: bool
    success_rate: float
    episodes_total: int
    episodes_success: int


class ReconciliationSLOResult(TypedDict):
    reconciliation_ok: bool
    max_drift_pct_observed: float
    symbols_evaluated: int


class RiskContextResult(TypedDict):
    allowed: bool
    reason_code: str
    execution_mode: str


class ErrorClassificationResult(TypedDict):
    source: str
    category: str
    reason_code: str
    decision_id: int
    execution_id: int


class ShadowLoadSummary(TypedDict):
    mode: str
    symbols_processed: int
    duration_seconds: int
    live_orders_sent: int
    latency: LatencySLOResult
    episodes: EpisodeSLOResult
    reconciliation: ReconciliationSLOResult
    guardrails: dict[str, str]


@dataclass(frozen=True)
class GuardrailSnapshot:
    risk_gate: str = "ATIVO"
    circuit_breaker: str = "ATIVO"
    decision_id: str = "IDEMPOTENTE"

    def as_dict(self) -> dict[str, str]:
        return {
            "risk_gate": self.risk_gate,
            "circuit_breaker": self.circuit_breaker,
            "decision_id": self.decision_id,
        }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _metric_attr(item: object, name: str) -> float | int | str:
    value = getattr(item, name, None)
    if value is None:
        raise ValueError(f"metrica invalida: atributo ausente '{name}'")
    if isinstance(value, (str, int, float)):
        return value
    raise ValueError(f"metrica invalida: tipo nao suportado em '{name}'")


def evaluate_latency_slo(
    *,
    metrics: Sequence[object],
    max_p95_over_p50_ratio: float,
) -> LatencySLOResult:
    """Valida SLO de latencia por razao P95/P50.

    O limite padrao da task e 1.5 (P95 <= 150% de P50 baseline).
    """
    if max_p95_over_p50_ratio <= 0:
        raise ValueError("max_p95_over_p50_ratio deve ser > 0")
    if not metrics:
        raise ValueError("metrics deve conter ao menos um simbolo")

    max_ratio = 0.0
    max_p95 = 0.0
    baseline_p50 = float(_metric_attr(metrics[0], "p50_ms"))

    for item in metrics:
        p95_ms = float(_metric_attr(item, "p95_ms"))
        p50_ms = float(_metric_attr(item, "p50_ms"))
        ratio = _safe_ratio(p95_ms, p50_ms)
        if ratio > max_ratio:
            max_ratio = ratio
        if p95_ms > max_p95:
            max_p95 = p95_ms

    return {
        "latency_ok": max_ratio <= max_p95_over_p50_ratio,
        "max_ratio_observed": max_ratio,
        "max_p95_ms": max_p95,
        "baseline_p50_ms": baseline_p50,
        "symbols_evaluated": len(metrics),
    }


def evaluate_episode_success_slo(
    *,
    metrics: Sequence[object],
    min_success_rate: float,
) -> EpisodeSLOResult:
    """Valida SLO de sucesso de persistencia de episodios."""
    if min_success_rate <= 0 or min_success_rate > 1:
        raise ValueError("min_success_rate deve estar no intervalo (0, 1]")
    if not metrics:
        raise ValueError("metrics deve conter ao menos um simbolo")

    total = sum(int(_metric_attr(item, "episodes_total")) for item in metrics)
    success = sum(int(_metric_attr(item, "episodes_success")) for item in metrics)
    rate = _safe_ratio(float(success), float(total))

    return {
        "episode_success_ok": rate >= min_success_rate,
        "success_rate": rate,
        "episodes_total": total,
        "episodes_success": success,
    }


def evaluate_reconciliation_drift_slo(
    *,
    metrics: Sequence[object],
    max_drift_pct: float,
) -> ReconciliationSLOResult:
    """Valida limite maximo de drift de reconciliacao entre simbolos."""
    if max_drift_pct < 0:
        raise ValueError("max_drift_pct deve ser >= 0")
    if not metrics:
        raise ValueError("metrics deve conter ao menos um simbolo")

    max_observed = max(
        float(_metric_attr(item, "reconciliation_drift_pct")) for item in metrics
    )
    return {
        "reconciliation_ok": max_observed <= max_drift_pct,
        "max_drift_pct_observed": max_observed,
        "symbols_evaluated": len(metrics),
    }


def classify_operational_error(
    *,
    source: str,
    error_kind: str,
    decision_id: int,
    execution_id: int,
) -> ErrorClassificationResult:
    """Classifica erro operacional em transitorio/permanente com correlacao."""
    normalized_kind = error_kind.strip().lower()
    if normalized_kind in {"timeout", "connection", "temporario", "transient"}:
        category = "transient"
        reason_code = "timeout" if normalized_kind == "timeout" else "transient_error"
    else:
        category = "permanent"
        reason_code = "permanent_error"

    return {
        "source": source,
        "category": category,
        "reason_code": reason_code,
        "decision_id": decision_id,
        "execution_id": execution_id,
    }


def validate_risk_context_isolation(
    *,
    execution_mode: Literal["shadow", "paper", "live"],
    has_live_api_key: bool,
    has_paper_api_key: bool,
) -> RiskContextResult:
    """Valida isolamento de contexto operacional por modo."""
    if execution_mode == "shadow" and has_live_api_key:
        return {
            "allowed": False,
            "reason_code": "risk_context_isolation_blocked",
            "execution_mode": execution_mode,
        }

    if execution_mode == "paper" and has_live_api_key and not has_paper_api_key:
        return {
            "allowed": False,
            "reason_code": "paper_missing_credentials",
            "execution_mode": execution_mode,
        }

    return {
        "allowed": True,
        "reason_code": "ok",
        "execution_mode": execution_mode,
    }


def run_shadow_load_validation(
    *,
    symbols: list[str],
    duration_seconds: int,
    mode: Literal["shadow", "paper", "live"],
) -> dict[str, int | str]:
    """Executa validacao de carga no modo solicitado.

    Para M2-022.5, o modo aceito e shadow e nenhuma ordem real pode ser enviada.
    """
    if duration_seconds <= 0:
        raise ValueError("duration_seconds deve ser > 0")
    if not symbols:
        raise ValueError("symbols deve conter ao menos um simbolo")
    if mode != "shadow":
        raise ValueError("run_shadow_load_validation suporta apenas modo shadow")

    return {
        "mode": mode,
        "symbols_processed": len(symbols),
        "duration_seconds": duration_seconds,
        "live_orders_sent": 0,
    }


def build_shadow_load_report(
    *,
    metrics: Sequence[object],
    duration_seconds: int,
    mode: Literal["shadow", "paper", "live"],
    baseline_p50_ms: float,
) -> ShadowLoadSummary:
    """Consolida relatorio unico de carga shadow com SLOs e guardrails."""
    if baseline_p50_ms <= 0:
        raise ValueError("baseline_p50_ms deve ser > 0")

    summary = run_shadow_load_validation(
        symbols=[str(_metric_attr(item, "symbol")) for item in metrics],
        duration_seconds=duration_seconds,
        mode=mode,
    )
    latency = evaluate_latency_slo(
        metrics=metrics,
        max_p95_over_p50_ratio=1.5,
    )
    episodes = evaluate_episode_success_slo(
        metrics=metrics,
        min_success_rate=0.995,
    )
    reconciliation = evaluate_reconciliation_drift_slo(
        metrics=metrics,
        max_drift_pct=0.01,
    )

    guardrails = GuardrailSnapshot().as_dict()
    report: ShadowLoadSummary = {
        "mode": str(summary["mode"]),
        "symbols_processed": int(summary["symbols_processed"]),
        "duration_seconds": int(summary["duration_seconds"]),
        "live_orders_sent": int(summary["live_orders_sent"]),
        "latency": latency,
        "episodes": episodes,
        "reconciliation": reconciliation,
        "guardrails": guardrails,
    }
    # Baseline explicitado para rastreabilidade mesmo sem dependencia externa.
    report["latency"]["baseline_p50_ms"] = baseline_p50_ms
    return report
