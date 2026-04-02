"""Suite RED da M2-025.13 para evidencias auditaveis por simbolo em testnet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import scripts.model2.operator_cycle_status as operator_cycle_status
from scripts.model2.go_live_preflight import run_go_live_preflight
from scripts.model2.healthcheck_live_execution import run_live_healthcheck
from scripts.model2.persist_training_episodes import run_persist_training_episodes
from tests.test_model2_m2_018_2_testnet_integration import (
    _prepare_model2_db,
    _stub_ok,
)


def _write_paper_env_with_credentials(env_file: Path) -> None:
    env_file.write_text(
        "TRADING_MODE=paper\n"
        "M2_EXECUTION_MODE=paper\n"
        "M2_LIVE_SYMBOLS=BNBUSDT\n"
        "BINANCE_API_KEY=test_key\n"
        "BINANCE_API_SECRET=test_secret\n"
        "M2_MAX_DAILY_ENTRIES=10\n"
        "M2_MAX_MARGIN_PER_POSITION_USD=1.0\n"
        "M2_MAX_SIGNAL_AGE_MINUTES=240\n"
        "M2_SYMBOL_COOLDOWN_MINUTES=240\n"
        "M2_SHORT_ONLY=true\n"
        "M2_CANARY_LEVERAGE=5\n"
        "M2_FUNDING_RATE_MAX_FOR_SHORT=0.0005\n",
        encoding="utf-8",
    )


def _run_preflight_paper(tmp_path: Path) -> dict[str, Any]:
    db_path = _prepare_model2_db(tmp_path)
    env_file = tmp_path / ".env"
    _write_paper_env_with_credentials(env_file)
    return run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=False,
        continue_on_error=True,
        live_symbols=("BNBUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_ok,
        live_execute_fn=_stub_ok,
        live_reconcile_fn=_stub_ok,
        live_dashboard_fn=_stub_ok,
        live_healthcheck_fn=_stub_ok,
    )


def _write_live_dashboard(runtime_dir: Path, payload: dict[str, Any]) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    dashboard = runtime_dir / "model2_live_dashboard_20260402T120000Z.json"
    dashboard.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return dashboard


# ---------------------------------------------------------------------------
# Unitarios (4)
# ---------------------------------------------------------------------------


def test_preflight_testnet_evidence_includes_symbol_status_map(tmp_path: Path) -> None:
    """R1: preflight paper/testnet deve publicar mapa de status por simbolo."""
    summary = _run_preflight_paper(tmp_path)

    symbol_status = summary["testnet_evidence"]["symbol_status"]

    assert "BNBUSDT" in symbol_status


def test_preflight_symbol_status_includes_capture_decision_episode_training_keys(
    tmp_path: Path,
) -> None:
    """R1/R2: cada simbolo deve expor os 4 gates da trilha operacional."""
    summary = _run_preflight_paper(tmp_path)

    symbol_status = summary["testnet_evidence"]["symbol_status"]["BNBUSDT"]

    assert set(["capture", "decision", "episode", "training", "overall_status"]).issubset(
        symbol_status.keys()
    )


def test_preflight_symbol_gate_blocks_when_full_chain_is_not_proven(tmp_path: Path) -> None:
    """R5: sem evidencia minima por simbolo, o gate deve bloquear em fail-safe."""
    summary = _run_preflight_paper(tmp_path)

    symbol_status = summary["testnet_evidence"]["symbol_status"]["BNBUSDT"]

    assert symbol_status["overall_status"] == "alert"
    assert summary["status"] == "alert"


def test_preflight_correlation_contract_keeps_required_fields(tmp_path: Path) -> None:
    """R1: a correlacao canonica decision/execution deve continuar obrigatoria."""
    summary = _run_preflight_paper(tmp_path)

    required_fields = summary["testnet_evidence"]["decision_execution_correlation"][
        "required_fields"
    ]

    assert required_fields == [
        "decision_id",
        "execution_id",
        "reason_code",
        "severity",
        "recommended_action",
    ]


# ---------------------------------------------------------------------------
# Integracao (4)
# ---------------------------------------------------------------------------


def test_healthcheck_missing_symbol_status_contract_returns_alert(tmp_path: Path) -> None:
    """R3/R5: healthcheck nao pode retornar ok quando falta trilha por simbolo."""
    runtime_dir = tmp_path / "runtime"
    _write_live_dashboard(
        runtime_dir,
        {
            "status": "ok",
            "timestamp_utc_ms": 1_900_000_000_000,
            "unprotected_filled_count": 0,
            "stale_entry_sent_count": 0,
            "open_position_mismatches_count": 0,
        },
    )

    summary = run_live_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    codes = {str(item.get("code")) for item in summary["violations"]}

    assert "missing_symbol_status_contract" in codes
    assert summary["status"] == "alert"


def test_healthcheck_partial_symbol_status_forces_no_go(tmp_path: Path) -> None:
    """R3/R5: qualquer simbolo com cadeia parcial deve resultar em NO_GO."""
    runtime_dir = tmp_path / "runtime"
    _write_live_dashboard(
        runtime_dir,
        {
            "status": "ok",
            "timestamp_utc_ms": 1_900_000_000_000,
            "unprotected_filled_count": 0,
            "stale_entry_sent_count": 0,
            "open_position_mismatches_count": 0,
            "symbol_status": {
                "BNBUSDT": {
                    "capture": "ok",
                    "decision": "ok",
                    "episode": "missing",
                    "training": "missing",
                    "overall_status": "partial",
                }
            },
        },
    )

    summary = run_live_healthcheck(
        runtime_dir=runtime_dir,
        output_dir=runtime_dir,
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    assert summary["status"] == "alert"
    assert summary["promotion_gate"]["go"] is False


def test_persist_training_episodes_summary_includes_training_evidence_by_symbol(
    tmp_path: Path,
) -> None:
    """R2/R4: a persistencia deve expor bloco auditavel de treino por simbolo."""
    db_path = _prepare_model2_db(tmp_path)

    summary = run_persist_training_episodes(
        source_db_path=db_path,
        model2_db_path=db_path,
        symbols=["BNBUSDT"],
        timeframe="M5",
        output_dir=tmp_path / "results",
    )

    training_evidence = summary["training_evidence_by_symbol"]

    assert "BNBUSDT" in training_evidence


def test_persist_training_episodes_symbol_evidence_includes_reward_and_isolation_status(
    tmp_path: Path,
) -> None:
    """R4/R5: cada simbolo deve expor reward, elegibilidade e isolamento de modo."""
    db_path = _prepare_model2_db(tmp_path)

    summary = run_persist_training_episodes(
        source_db_path=db_path,
        model2_db_path=db_path,
        symbols=["BNBUSDT"],
        timeframe="M5",
        output_dir=tmp_path / "results",
    )

    symbol_evidence = summary["training_evidence_by_symbol"]["BNBUSDT"]

    assert set(["episode_id", "reward_source", "eligibility_status", "mode_isolation", "overall_status"]).issubset(
        symbol_evidence.keys()
    )


# ---------------------------------------------------------------------------
# Regressao / risco (3)
# ---------------------------------------------------------------------------


def test_operator_cycle_status_report_includes_evidence_line(tmp_path: Path) -> None:
    """RR-001: o report por simbolo deve exibir linha dedicada de evidencia."""
    db_path = _prepare_model2_db(tmp_path)

    report = operator_cycle_status._build_symbol_report(
        symbol="BNBUSDT",
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=str(db_path),
    )

    assert "  Evidencia :" in report


def test_operator_cycle_status_report_exposes_capture_decision_episode_training_contract(
    tmp_path: Path,
) -> None:
    """RR-002: o report nao pode esconder qual gate falhou na cadeia por simbolo."""
    db_path = _prepare_model2_db(tmp_path)

    report = operator_cycle_status._build_symbol_report(
        symbol="BNBUSDT",
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=str(db_path),
    )

    assert "capture=" in report
    assert "decision=" in report
    assert "episode=" in report
    assert "training=" in report


def test_operator_cycle_status_report_blocks_without_false_ok_when_training_is_missing(
    tmp_path: Path,
) -> None:
    """RR-003: sem treino comprovado, o report deve explicitar bloqueio do gate."""
    db_path = _prepare_model2_db(tmp_path)

    report = operator_cycle_status._build_symbol_report(
        symbol="BNBUSDT",
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=str(db_path),
    )

    assert "evidence_gate=BLOCKED" in report
