"""Suite RED M2-025.12: regressao de treino incremental em carga moderada.

Objetivo:
- R1: contrato de auditoria deve incluir decision_id e chave de concorrencia.
- R2: trigger deve aceitar decision_id e expor chave idempotente deterministica.
- R3: trigger do live_service deve receber decision_id explicitamente.
- R4: deve existir harness de regressao para carga moderada reutilizavel no CI.
"""

from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path
from types import SimpleNamespace


def _create_minimal_training_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rl_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                completed_at TEXT,
                completed_at_ms INTEGER,
                episodes_used INTEGER,
                status TEXT
            )
            """
        )
        conn.commit()


def test_training_audit_schema_requires_decision_id_and_concurrency_key_columns(
    tmp_path: Path,
) -> None:
    """R1: schema da auditoria precisa colunas para idempotencia e anti-concorrencia."""
    from core.model2.training_audit import ensure_rl_training_audit_schema

    db_path = tmp_path / "m2_025_12_schema.db"
    _create_minimal_training_tables(db_path)

    with sqlite3.connect(db_path) as conn:
        ensure_rl_training_audit_schema(conn)
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(rl_training_audit)").fetchall()
        }

    assert "decision_id" in columns
    assert "concurrency_key" in columns


def test_record_training_audit_event_requires_decision_id_and_concurrency_key(
    tmp_path: Path,
) -> None:
    """R1: evento auditavel deve persistir decision_id/concurrency_key."""
    from core.model2.training_audit import record_training_audit_event

    db_path = tmp_path / "m2_025_12_event.db"
    _create_minimal_training_tables(db_path)

    with sqlite3.connect(db_path) as conn:
        record_training_audit_event(
            conn,
            triggered_at_ms=1_711_000_000_000,
            trigger_reason="threshold_reached",
            episodes_count=120,
            model_id_before="ppo_v1",
            model_id_after="ppo_v2",
            avg_reward_delta=0.14,
            status="started",
            decision_id="dec-001",
            concurrency_key="train-H4",
        )

        row = conn.execute(
            """
            SELECT decision_id, concurrency_key
            FROM rl_training_audit
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "dec-001"
    assert row[1] == "train-H4"


def test_evaluate_training_trigger_audit_returns_idempotency_key_with_decision_id() -> None:
    """R2: avaliacao do trigger deve ser deterministica por decision_id."""
    from core.model2.training_audit import evaluate_training_trigger_audit

    result = evaluate_training_trigger_audit(
        pending_episodes=150,
        retrain_threshold=100,
        is_running=False,
        now_ms=1_711_000_000_000,
        last_completed_at_ms=1_710_999_000_000,
        decision_id="dec-777",
        timeframe="H4",
    )

    assert result["trigger_allowed"] is True
    assert result["idempotency_key"] == "dec-777:H4"


def test_live_service_trigger_signature_exposes_decision_id_parameter() -> None:
    """R3: assinatura do trigger no live_service deve receber decision_id explicito."""
    from core.model2.live_service import Model2LiveExecutionService

    signature = inspect.signature(
        Model2LiveExecutionService._trigger_incremental_training_if_needed
    )
    assert "decision_id" in signature.parameters


def test_live_service_trigger_signature_exposes_concurrency_label_parameter() -> None:
    """R3: assinatura do trigger no live_service deve receber rotulo de concorrencia."""
    from core.model2.live_service import Model2LiveExecutionService

    signature = inspect.signature(
        Model2LiveExecutionService._trigger_incremental_training_if_needed
    )
    assert "concurrency_label" in signature.parameters


def test_training_load_regression_harness_exists_for_ci_execution() -> None:
    """R4: deve existir harness dedicado para regressao de carga moderada em CI."""
    from core.model2.training_load_regression import run_incremental_training_load_regression

    result = run_incremental_training_load_regression(
        cycles=20,
        symbols=("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"),
        timeframe="H4",
    )

    assert result["concurrency_violations"] == 0
    assert result["status"] == "passed"


def test_log_operational_status_builds_decision_id_fallback_when_metadata_absent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """R3: quando metadata nao traz decision_id, trigger deve receber fallback deterministico."""
    from core.model2.live_service import Model2LiveExecutionService
    from core.model2.model_decision import ACTION_HOLD, ModelDecision

    captured: dict[str, str | None] = {"decision_id": None}

    monkeypatch.setattr(
        "core.model2.live_service.collect_training_info",
        lambda db_path: ("nunca", 0),
    )
    monkeypatch.setattr(
        "core.model2.live_service.collect_training_info_for_symbol",
        lambda db_path, symbol, timeframe: ("nunca", 0),
    )
    monkeypatch.setattr(
        "core.model2.live_service.collect_position_info",
        lambda symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )
    monkeypatch.setattr(
        "core.model2.live_service.format_symbol_report",
        lambda report: "ok",
    )

    service = Model2LiveExecutionService(
        repository=SimpleNamespace(),
        config=SimpleNamespace(execution_mode="shadow", db_path=str(tmp_path / "modelo2.db")),
    )

    def _capture_trigger(**kwargs):
        captured["decision_id"] = kwargs.get("decision_id")

    monkeypatch.setattr(service, "_trigger_incremental_training_if_needed", _capture_trigger)

    service._log_operational_status(
        "BTCUSDT",
        ModelDecision(
            action=ACTION_HOLD,
            confidence=0.5,
            size_fraction=0.0,
            sl_target=None,
            tp_target=None,
            reason_code="test",
            decision_timestamp=1_700_000_000_000,
            symbol="BTCUSDT",
            model_version="m2-inference-v1",
            metadata={},
        ),
        timeframe="H4",
    )

    assert captured["decision_id"] == "BTCUSDT:H4:1700000000000"
