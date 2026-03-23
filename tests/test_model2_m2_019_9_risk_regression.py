"""Regressoes de risco para M2-019.9 com foco em fail-safe e idempotencia."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import M2_002_RULE_ID, M2_002_THESIS_TYPE, DetectionResult
from scripts.model2.migrate import run_up
from scripts.model2.order_layer import run_order_layer


def _build_detection_result(*, symbol: str, side: str = "SHORT") -> DetectionResult:
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": "1.0.0",
        "technical_zone": {
            "source": "order_block",
            "zone_id": 7,
            "timestamp": 1_699_999_999_000,
            "zone_low": 100.0,
            "zone_high": 110.0,
            "status": "FRESH",
        },
        "rejection_candle": {
            "timestamp": 1_700_000_000_000,
            "open": 100.0,
            "high": 111.0,
            "low": 97.0,
            "close": 98.0,
        },
        "context": {"market_structure": "range", "is_non_bullish_context": True},
        "parameters": {
            "requires_zone_intersection": True,
            "requires_visible_rejection": True,
            "requires_trigger_break": True,
        },
    }
    return DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe="H4",
        side=side,
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )


def _prepare_db_with_created_signal(tmp_path: Path, *, symbol: str, side: str) -> tuple[Path, int]:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)

    repository = Model2ThesisRepository(str(db_path))
    created = repository.create_initial_thesis(
        _build_detection_result(symbol=symbol, side=side),
        now_ms=1_700_000_010_000,
    )
    repository.transition_to_monitoring(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_020_000,
    )
    repository.transition_to_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_030_000,
    )
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_040_000,
    )
    assert signal.signal_id is not None
    return db_path, int(signal.signal_id)


def test_risco_guardrails_arquivos_ativos_existem_no_repositorio() -> None:
    """Requisito: risk_gate e circuit_breaker devem permanecer ativos no projeto."""
    assert Path("risk/risk_gate.py").exists()
    assert Path("risk/circuit_breaker.py").exists()


def test_order_layer_fail_safe_ambiguidade_cancela_sinal_nao_autorizado(tmp_path: Path) -> None:
    """Requisito: em ambiguidade operacional, aplicar cancelamento conservador."""
    db_path, signal_id = _prepare_db_with_created_signal(
        tmp_path,
        symbol="M2ZZZUSDT",
        side="SHORT",
    )

    summary = run_order_layer(
        model2_db_path=db_path,
        symbol="M2ZZZUSDT",
        timeframe="H4",
        limit=10,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
    )

    assert summary["cancelled_now"] == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, payload_json FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "CANCELLED"
    payload = json.loads(row[1] or "{}")
    assert payload.get("order_layer", {}).get("reason") == "symbol_not_authorized"


def test_order_layer_erro_nao_perde_status_created_em_dry_run(tmp_path: Path) -> None:
    """Requisito: validacao sem mutacao preserva CREATED para analise posterior."""
    db_path, signal_id = _prepare_db_with_created_signal(
        tmp_path,
        symbol="BTCUSDT",
        side="SHORT",
    )

    summary = run_order_layer(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=10,
        dry_run=True,
        output_dir=tmp_path / "results" / "model2" / "runtime",
    )

    assert summary["eligible_created_signals"] == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "CREATED"


def test_order_layer_consumo_e_idempotente_em_execucao_repetida(tmp_path: Path) -> None:
    """Requisito: consumo por camada de ordem deve respeitar idempotencia."""
    db_path, _ = _prepare_db_with_created_signal(
        tmp_path,
        symbol="BTCUSDT",
        side="SHORT",
    )

    first = run_order_layer(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=10,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
    )
    second = run_order_layer(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=10,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
    )

    assert first["consumed_now"] == 1
    assert second["consumed_now"] == 0
    assert second["eligible_created_signals"] == 0
