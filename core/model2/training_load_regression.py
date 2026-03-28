"""Harness de regressao de carga moderada para treino incremental (M2-025.12)."""

from __future__ import annotations

from typing import TypedDict

from .training_audit import evaluate_training_trigger_audit


class TrainingLoadRegressionResult(TypedDict):
    """Resultado resumido da regressao de treino incremental em carga moderada."""

    status: str
    cycles: int
    symbols_count: int
    attempts: int
    started: int
    blocked: int
    concurrency_violations: int


def run_incremental_training_load_regression(
    *,
    cycles: int,
    symbols: tuple[str, ...],
    timeframe: str,
) -> TrainingLoadRegressionResult:
    """Executa simulacao deterministica de trigger incremental sob carga moderada.

    A simulacao modela concorrencia controlada por um lock de treinamento:
    enquanto um treino esta "ativo", novos triggers devem ser bloqueados.
    """
    safe_cycles = max(0, int(cycles))
    safe_symbols = tuple(symbol for symbol in symbols if str(symbol).strip())
    attempts = 0
    started = 0
    blocked = 0
    concurrency_violations = 0

    training_running = False
    now_ms = 1_711_000_000_000

    for cycle_idx in range(safe_cycles):
        for symbol in safe_symbols:
            attempts += 1
            decision = evaluate_training_trigger_audit(
                pending_episodes=120,
                retrain_threshold=100,
                is_running=training_running,
                now_ms=now_ms,
                last_completed_at_ms=now_ms - 60_000,
                decision_id=f"M2-025.12-{cycle_idx}-{symbol}",
                timeframe=timeframe,
            )

            if decision["trigger_allowed"]:
                started += 1
                if training_running:
                    concurrency_violations += 1
                training_running = True
            else:
                blocked += 1
                if decision["trigger_reason"] == "training_already_running" and not training_running:
                    concurrency_violations += 1

        # libera lock ao fim do ciclo para permitir novo treino no proximo ciclo
        training_running = False
        now_ms += 300_000

    status = "passed" if concurrency_violations == 0 else "failed"
    return {
        "status": status,
        "cycles": safe_cycles,
        "symbols_count": len(safe_symbols),
        "attempts": attempts,
        "started": started,
        "blocked": blocked,
        "concurrency_violations": concurrency_violations,
    }
