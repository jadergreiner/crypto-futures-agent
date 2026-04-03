"""Controles de resiliencia para pacote M2-023.2..023.10 + M2-027.2.

Funcoes puras e deterministicas para suportar contratos de testes.
Nao desabilita risk_gate/circuit_breaker; apenas fornece avaliadores.

M2-023.8: execute_with_category_retry aprimorado com:
- actual_attempts: tentativas reais realizadas
- backoff com time.sleep entre retries transientes
- contadores acumulados por categoria (_retry_counters)
- build_retry_category_report: relatorio operacional de contagens
- reset_retry_counters: limpeza de estado para testes
- reason_code no resultado para auditabilidade (ADR-009)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from statistics import mean
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# M2-023.8: contadores acumulados de retry por categoria (module-level)
# ---------------------------------------------------------------------------
_retry_counters: dict[str, int] = {}

# Categorias que permitem retry (ADR-004)
_RETRYABLE_CATEGORIES: frozenset[str] = frozenset({"timeout", "transient"})

# Backoff padrao entre tentativas transientes (segundos)
_DEFAULT_BACKOFF: tuple[float, ...] = (1.0, 2.0, 4.0)


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def evaluate_position_drift_gate(
    current_state: dict[str, float],
    observed_state: dict[str, float],
    threshold_pct: float,
    decision_id: int,
) -> dict[str, object]:
    current_qty = float(current_state.get("position_qty", 0.0))
    observed_qty = float(observed_state.get("position_qty", 0.0))
    baseline = max(abs(current_qty), 1e-9)
    drift_pct = abs(observed_qty - current_qty) / baseline
    allow = drift_pct <= float(threshold_pct)
    return {
        "allow": allow,
        "reason_code": None if allow else "position_drift_blocked",
        "decision_id": int(decision_id),
        "drift_pct": drift_pct,
    }


def evaluate_latency_degradation(
    metrics: dict[str, int],
    p95_limit_ms: int,
    p99_limit_ms: int,
    recent_window: list[dict[str, int]] | None = None,
    stable_window_count: int = 3,
) -> dict[str, object]:
    """Avalia politica de degradacao por latencia P95/P99.

    Entrada no modo degradado: p95_ms > p95_limit_ms ou
    p99_ms > p99_limit_ms.
    Saida do modo degradado: janela de 'stable_window_count' medicoes
    consecutivas todas abaixo dos limites. Se 'recent_window' estiver
    vazia ou for None, exit_ready=False.
    """
    p95 = _to_int(metrics.get("p95_ms", 0))
    p99 = _to_int(metrics.get("p99_ms", 0))
    degraded = p95 > int(p95_limit_ms) or p99 > int(p99_limit_ms)

    window = recent_window if recent_window is not None else []
    if len(window) >= int(stable_window_count):
        tail = window[-int(stable_window_count):]
        exit_ready: bool = all(
            _to_int(m.get("p95_ms", 0)) <= int(p95_limit_ms)
            and _to_int(m.get("p99_ms", 0)) <= int(p99_limit_ms)
            for m in tail
        )
    else:
        exit_ready = False

    return {
        "mode": "degraded" if degraded else "normal",
        "entry_reason": "latency_slo_breached" if degraded else None,
        "p95_ms": p95,
        "p99_ms": p99,
        "exit_ready": exit_ready,
    }


def plan_restart_from_snapshot(
    snapshot: dict[str, int | str],
    has_open_order: bool,
) -> dict[str, object]:
    """Planeja retomada segura a partir de snapshot de estado operacional.

    Valida o snapshot e determina se uma nova ordem deve ser enviada,
    garantindo idempotencia no restart sem duplicidade de execucao.

    Fases que indicam posicao ja executada (nao geram nova ordem):
    ENTRY_FILLED, PROTECTION_ARMED, MONITORING, CLOSING.

    Funcao pura e deterministica (M2-023.4, ADR-002/004/009).
    Fail-safe: campos ausentes nao lancam excecao.

    Args:
        snapshot: dict com 'decision_id', 'phase' e 'heartbeat_ms'.
        has_open_order: True se ja existe ordem aberta rastreada.

    Returns:
        Dict com: replay_mode, valid_snapshot, send_new_order,
        decision_id, phase, heartbeat_ms.
    """
    decision_id = snapshot.get("decision_id")
    phase = str(snapshot.get("phase", ""))
    heartbeat_ms = snapshot.get("heartbeat_ms")

    # Snapshot valido exige os tres campos preenchidos
    valid_snapshot = bool(decision_id and phase and heartbeat_ms)

    # Fases que indicam posicao ja existente: nao reenviar ordem
    _executed_phases = frozenset(
        {"ENTRY_FILLED", "PROTECTION_ARMED", "MONITORING", "CLOSING"}
    )
    phase_already_executed = phase in _executed_phases

    # Fail-safe: nao enviar nova ordem se snapshot invalido, ordem ja aberta
    # ou fase indica posicao ja executada
    send_new_order = (
        valid_snapshot
        and not has_open_order
        and not phase_already_executed
    )

    return {
        "replay_mode": "idempotent_resume",
        "valid_snapshot": valid_snapshot,
        "send_new_order": send_new_order,
        "decision_id": int(decision_id) if decision_id else 0,
        "phase": phase,
        "heartbeat_ms": int(heartbeat_ms) if heartbeat_ms else 0,
    }


def prioritize_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    priority_rank = {"CRITICAL": 0, "HIGH": 1, "WARN": 2}
    return sorted(events, key=lambda e: priority_rank.get(str(e.get("priority")), 9))


def query_risk_gate_audit_by_decision_id(
    trail: list[dict[str, object]],
    decision_id: int,
) -> list[dict[str, object]]:
    return [event for event in trail if _to_int(event.get("decision_id"), -1) == int(decision_id)]


def cross_validate_signal_context_position(
    signal: dict[str, object],
    context: dict[str, object],
    position: dict[str, object],
    decision_id: int = 0,
) -> dict[str, object]:
    """Validacao cruzada de sinal, contexto e posicao antes da admissao.

    Bloqueia admissao quando:
    1. Sinal contradiz tendencia de mercado (LONG+DOWN ou SHORT+UP).
    2. Posicao ja esta aberta na mesma direcao (evita double-exposure).

    Funcao pura e deterministica (M2-023.7, ADR-002/004/009).
    Fail-safe: campos ausentes nao lancam excecao; assume sem conflito.

    Args:
        signal: dict com 'side' (LONG|SHORT) e metadados do sinal.
        context: dict com 'trend' (UP|DOWN) do contexto de mercado.
        position: dict com 'is_open' (bool) e 'side' (LONG|SHORT) da posicao.
        decision_id: identificador da decisao para auditabilidade (ADR-004).

    Returns:
        Dict com: allow (bool), reason_code (str|None), decision_id (int).
    """
    side = str(signal.get("side", "")).upper()
    trend = str(context.get("trend", "")).upper()
    is_open = bool(position.get("is_open", False))
    position_side = str(position.get("side", "")).upper()

    # Verificar double-exposure: posicao ja aberta na mesma direcao
    if is_open and side in ("LONG", "SHORT") and side == position_side:
        return {
            "allow": False,
            "reason_code": "position_already_open",
            "decision_id": int(decision_id),
        }

    # Verificar contradicao critica entre sinal e tendencia de mercado
    trend_conflict = (
        (side == "LONG" and trend == "DOWN")
        or (side == "SHORT" and trend == "UP")
    )
    if trend_conflict:
        return {
            "allow": False,
            "reason_code": "cross_validation_conflict",
            "decision_id": int(decision_id),
        }

    return {
        "allow": True,
        "reason_code": None,
        "decision_id": int(decision_id),
    }


def execute_with_category_retry(
    fn: Callable[[], object],
    category: str,
    max_attempts: int,
    backoff_seconds: tuple[float, ...] | None = None,
) -> dict[str, object]:
    """Executa fn() com politica de retry orientada a categoria de erro.

    Categorias retentaveis (transient/timeout): retry ate max_attempts com
    backoff exponencial entre tentativas.
    Categoria permanent: interrompe apos 1 tentativa (sem retry).

    Acumula contadores globais por categoria para relatorio operacional
    via build_retry_category_report() (M2-023.8, ADR-009).

    Args:
        fn: callable sem argumentos a executar.
        category: categoria do erro esperado (transient/timeout/permanent).
        max_attempts: maximo de tentativas permitidas.
        backoff_seconds: delays entre tentativas (default: _DEFAULT_BACKOFF).

    Returns:
        Dict com: ok, error, category, should_retry, actual_attempts,
        max_attempts, reason_code.
    """
    normalized = str(category or "unknown").strip().lower()
    should_retry = normalized in _RETRYABLE_CATEGORIES
    max_att = max(1, int(max_attempts)) if should_retry else 1
    bo = backoff_seconds if backoff_seconds is not None else _DEFAULT_BACKOFF

    last_error: str | None = None
    actual_attempts = 0

    for attempt_idx in range(max_att):
        actual_attempts += 1
        try:
            fn()
            # Sucesso: acumula tentativas na categoria e retorna
            _retry_counters[normalized] = (
                _retry_counters.get(normalized, 0) + actual_attempts
            )
            logger.debug(
                "execute_with_category_retry: ok em %d/%d tentativas "
                "[categoria=%s]",
                actual_attempts, max_att, normalized,
            )
            return {
                "ok": True,
                "error": None,
                "category": normalized,
                "should_retry": should_retry,
                "actual_attempts": actual_attempts,
                "max_attempts": max_att,
                "reason_code": None,
            }
        except Exception as exc:  # noqa: BLE001 - contrato de retry fail-safe
            last_error = str(exc)
            logger.debug(
                "execute_with_category_retry: falha tentativa %d/%d "
                "[categoria=%s]: %s",
                actual_attempts, max_att, normalized, exc,
            )
            # Aplica backoff se ha proxima tentativa retentavel
            if should_retry and attempt_idx < max_att - 1:
                delay = bo[min(attempt_idx, len(bo) - 1)]
                time.sleep(delay)

    # Exauriu tentativas: acumula e retorna resultado de falha
    _retry_counters[normalized] = (
        _retry_counters.get(normalized, 0) + actual_attempts
    )
    # Reason code: permanent usa codigo bloqueante; transient usa timeout
    reason_code = (
        "permanent_error"
        if normalized == "permanent"
        else "transient_error"
    )
    logger.warning(
        "execute_with_category_retry: falha final apos %d tentativas "
        "[categoria=%s reason=%s]: %s",
        actual_attempts, normalized, reason_code, last_error,
    )
    return {
        "ok": False,
        "error": last_error,
        "category": normalized,
        "should_retry": should_retry,
        "actual_attempts": actual_attempts,
        "max_attempts": max_att,
        "reason_code": reason_code,
    }


def build_retry_category_report() -> dict[str, int]:
    """Retorna relatorio operacional de tentativas acumuladas por categoria.

    Usado para auditoria e monitoramento de loops de retry no ciclo live
    (M2-023.8, ADR-009). Nao altera nem reseta o estado acumulado.

    Returns:
        Dict {categoria: total_de_tentativas} acumulado desde o ultimo reset.
    """
    return dict(_retry_counters)


def reset_retry_counters() -> None:
    """Zera contadores acumulados de retry por categoria.

    Uso tipico: testes unitarios que precisam de estado limpo entre casos,
    ou reinicio do ciclo operacional no inicio de cada sessao live.
    """
    _retry_counters.clear()


def compute_reconciliation_health_indicators(
    samples: list[dict[str, object]],
) -> dict[str, float]:
    if not samples:
        return {"drift_mean": 0.0, "confirmation_p95_ms": 0.0, "adjustment_rate": 0.0}
    drifts = [_to_float(item.get("drift")) for item in samples]
    confirms = sorted(_to_float(item.get("confirm_ms")) for item in samples)
    adjusted_count = sum(1 for item in samples if bool(item.get("adjusted", False)))
    p95_index = max(0, min(len(confirms) - 1, int((len(confirms) - 1) * 0.95)))
    return {
        "drift_mean": mean(drifts),
        "confirmation_p95_ms": confirms[p95_index],
        "adjustment_rate": adjusted_count / float(len(samples)),
    }


def check_reconciliation_health_alerts(
    metrics: dict[str, float],
    thresholds: dict[str, float],
) -> list[dict[str, object]]:
    """Verifica indicadores de saude de reconciliacao e emite alertas.

    Compara cada metrica com o limite correspondente e retorna uma lista
    de alertas para cada indicador que ultrapassar o limite configurado.

    Funcao pura e deterministica (M2-023.9, ADR-002/009).
    Fail-safe: metricas ou limites ausentes nao geram alertas nem excecao.

    Mapeamento de metricas para limites:
        - drift_mean       → drift_mean_limit
        - confirmation_p95_ms → p95_limit_ms
        - adjustment_rate  → adjustment_rate_limit

    Args:
        metrics: dict com valores numericos das metricas de reconciliacao.
            Chaves esperadas: drift_mean, confirmation_p95_ms, adjustment_rate.
        thresholds: dict com os limites maximos aceitaveis por metrica.
            Chaves esperadas: drift_mean_limit, p95_limit_ms,
            adjustment_rate_limit.

    Returns:
        Lista de dicts com os campos por alerta:
            - severity: str ('WARN')
            - indicator_name: str (nome da metrica)
            - value: float (valor atual)
            - threshold_exceeded: float (limite que foi ultrapassado)
    """
    _INDICATOR_THRESHOLD_MAP: dict[str, str] = {
        "drift_mean": "drift_mean_limit",
        "confirmation_p95_ms": "p95_limit_ms",
        "adjustment_rate": "adjustment_rate_limit",
    }
    alerts: list[dict[str, object]] = []
    try:
        for indicator, threshold_key in _INDICATOR_THRESHOLD_MAP.items():
            if indicator not in metrics:
                continue
            if threshold_key not in thresholds:
                continue
            value = _to_float(metrics.get(indicator))
            limit = _to_float(thresholds.get(threshold_key))
            if value > limit:
                alerts.append({
                    "severity": "WARN",
                    "indicator_name": indicator,
                    "value": value,
                    "threshold_exceeded": limit,
                })
    except Exception:
        return []
    return alerts


def validate_contingency_runbook(runbook_path: Path) -> dict[str, object]:
    if not runbook_path.exists():
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    try:
        content = runbook_path.read_text(encoding="utf-8").strip()
    except OSError:
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    if not content:
        return {"ready": False, "reason_code": "runbook_missing_or_invalid"}
    return {"ready": True, "reason_code": None}


def validate_schema_tables(
    existing_tables: set[str],
    required_tables: set[str],
) -> dict[str, object]:
    missing = sorted(required_tables - existing_tables)
    if missing:
        return {"ok": False, "reason_code": "schema_divergence", "missing_tables": missing}
    return {"ok": True, "reason_code": None, "missing_tables": []}


_RISK_GATE_REASON_CODES = frozenset({
    "risk_gate_blocked",
    "risk_gate_drawdown",
    "risk_gate_size_limit",
    "risk_gate_daily_limit",
})


def build_risk_gate_audit_trail(
    db_path: str,
    decision_id: int,
) -> list[dict[str, Any]]:
    """Constroi trilha auditavel de bloqueios do risk_gate para um decision_id.

    Consulta `signal_executions` e `signal_execution_events` no banco
    canonico M2 filtrando por `decision_id` e `failure_reason` indicativo
    de bloqueio pelo risk_gate (M2-023.6, ADR-002/007).

    Fail-safe: retorna lista vazia sem lancar excecao em caso de DB ausente,
    tabela inexistente ou qualquer erro de consulta.

    Args:
        db_path: Caminho absoluto para o banco modelo2.db.
        decision_id: Identificador da decisao a auditar.

    Returns:
        Lista de dicts com os campos:
            - execution_id: int
            - decision_id: int
            - reason_code: str (ex.: 'risk_gate_blocked')
            - symbol: str
            - timestamp_ms: int
            - metadata: dict (payload_json do evento, se disponivel)
    """
    trail: list[dict[str, Any]] = []
    try:
        if not Path(db_path).exists():
            return trail

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    se.id           AS execution_id,
                    se.decision_id  AS decision_id,
                    COALESCE(se.failure_reason, se.gate_reason) AS reason_code,
                    se.symbol       AS symbol,
                    COALESCE(
                        see.event_timestamp,
                        se.created_at,
                        0
                    )               AS timestamp_ms,
                    COALESCE(see.payload_json, '{}') AS payload_json
                FROM signal_executions se
                LEFT JOIN signal_execution_events see
                    ON see.signal_execution_id = se.id
                WHERE se.decision_id = ?
                  AND (
                      se.failure_reason LIKE '%risk_gate%'
                      OR se.gate_reason LIKE '%risk_gate%'
                  )
                ORDER BY timestamp_ms ASC
                """,
                (int(decision_id),),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            reason: str = str(row["reason_code"] or "risk_gate_blocked")
            # Normalizar reason_code para catalogo canonico. Reason codes
            # desconhecidos (ex.: variantes historicas ou de modulos externos)
            # sao mapeados para 'risk_gate_blocked' como fallback seguro para
            # que a trilha permaneca consultavel sem quebrar contratos.
            if reason not in _RISK_GATE_REASON_CODES:
                reason = "risk_gate_blocked"
            try:
                metadata: dict[str, Any] = json.loads(str(row["payload_json"] or "{}"))
            except Exception:
                metadata = {}
            trail.append({
                "execution_id": int(row["execution_id"]),
                "decision_id": int(row["decision_id"]),
                "reason_code": reason,
                "symbol": str(row["symbol"] or ""),
                "timestamp_ms": int(row["timestamp_ms"] or 0),
                "metadata": metadata,
            })

    except Exception:
        # Fail-safe intencional (ADR-002): nunca propagar excecao.
        trail = []

    return trail
