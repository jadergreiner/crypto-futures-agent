"""Suite RED M2-025.6: Correlacao episodio treino e execucao por cycle_id.

Objetivo: garantir rastreabilidade auditavel entre scanner e persistencia,
sem migracao de schema, reutilizando metadata existente.

Status: RED - testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectionResult,
    DetectorInput,
    detect_initial_short_failure,
)
from scripts.model2.migrate import run_up


def _base_smc(structure: str = "range") -> dict:
    return {
        "structure": {"type": structure},
        "order_blocks": [
            {
                "timestamp": 1_700_000_000_000,
                "zone_low": 100.0,
                "zone_high": 110.0,
                "type": "bearish",
                "status": "FRESH",
                "zone_id": 9,
            }
        ],
        "fvgs": [],
    }


def _candles_valid_pattern() -> list[dict]:
    return [
        {"timestamp": 1, "open": 97.0, "high": 99.0, "low": 95.0, "close": 98.0},
        {"timestamp": 2, "open": 100.0, "high": 111.0, "low": 97.0, "close": 98.0},
        {"timestamp": 3, "open": 98.0, "high": 99.0, "low": 96.0, "close": 97.0},
    ]


def _prepare_model2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _build_detection_result(*, cycle_id: str | None) -> DetectionResult:
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
        "context": {
            "market_structure": "range",
            "is_non_bullish_context": True,
        },
        "parameters": {
            "requires_zone_intersection": True,
            "requires_visible_rejection": True,
            "requires_trigger_break": True,
        },
    }
    return DetectionResult(
        detected=True,
        symbol="BTCUSDT",
        timeframe="H4",
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
        cycle_id=cycle_id,
    )


def test_detect_initial_short_failure_propagates_cycle_id_to_result_and_metadata() -> None:
    """R1: scanner deve propagar cycle_id para DetectionResult e metadata."""
    detector_input = DetectorInput(
        symbol="BTCUSDT",
        timeframe="H4",
        candles=_candles_valid_pattern(),
        indicators=[],
        smc=_base_smc(),
        scan_timestamp=1_700_000_001_000,
        cycle_id="CYCLE-20260328-0001",
    )

    result = detect_initial_short_failure(detector_input)

    assert result is not None
    assert result.cycle_id == "CYCLE-20260328-0001"
    assert result.metadata["cycle_id"] == "CYCLE-20260328-0001"


def test_detection_result_supports_optional_cycle_id_without_breaking_legacy() -> None:
    """R2: DetectionResult aceita cycle_id=None para compatibilidade legado."""
    detection = _build_detection_result(cycle_id=None)

    assert detection.detected is True
    assert detection.cycle_id is None


def test_create_initial_thesis_persists_cycle_id_into_metadata_json(tmp_path: Path) -> None:
    """R3: repository persiste cycle_id em metadata_json sem mudar schema."""
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result(cycle_id="CYCLE-20260328-0002")

    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)

    assert created.created_now is True
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT metadata_json FROM opportunities WHERE id = ?",
            (created.opportunity_id,),
        ).fetchone()
        assert row is not None
        metadata = json.loads(row[0] or "{}")
        assert metadata["cycle_id"] == "CYCLE-20260328-0002"


def test_create_initial_thesis_without_cycle_id_keeps_backward_compatibility(
    tmp_path: Path,
) -> None:
    """R4: fluxo sem cycle_id continua funcional e sem regressao."""
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result(cycle_id=None)

    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)

    assert created.created_now is True
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT metadata_json FROM opportunities WHERE id = ?",
            (created.opportunity_id,),
        ).fetchone()
        assert row is not None
        metadata = json.loads(row[0] or "{}")
        assert "cycle_id" not in metadata


def test_create_initial_thesis_remains_idempotent_with_same_cycle_id(tmp_path: Path) -> None:
    """R5: idempotencia permanece com cycle_id presente."""
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result(cycle_id="CYCLE-20260328-0003")

    first = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    second = repository.create_initial_thesis(detection, now_ms=1_700_000_020_000)

    assert first.created_now is True
    assert second.created_now is False
    assert first.opportunity_id == second.opportunity_id

