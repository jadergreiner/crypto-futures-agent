import json
import sqlite3
from pathlib import Path

import pytest

from config.execution_config import AUTHORIZED_SYMBOLS
from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import (
    M2_002_RULE_ID,
    M2_002_THESIS_TYPE,
    DetectionResult,
)
from scripts.model2.migrate import run_up


def _build_detection_result(
    rejection_ts: int = 1_700_000_000_000,
    symbol: str = "BTCUSDT",
) -> DetectionResult:
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
            "timestamp": rejection_ts,
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
        symbol=symbol,
        timeframe="H4",
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )


def _prepare_model2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def test_create_initial_thesis_persists_opportunity_and_event(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()

    save_result = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)

    assert save_result.created_now is True
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, side, thesis_type, metadata_json FROM opportunities WHERE id = ?",
            (save_result.opportunity_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "IDENTIFICADA"
        assert row[1] == "SHORT"
        assert row[2] == M2_002_THESIS_TYPE
        metadata = json.loads(row[3])
        assert metadata["rejection_candle"]["timestamp"] == 1_700_000_000_000

        event = conn.execute(
            """
            SELECT event_type, from_status, to_status, rule_id
            FROM opportunity_events
            WHERE opportunity_id = ?
            """,
            (save_result.opportunity_id,),
        ).fetchone()
        assert event is not None
        assert event[0] == "STATUS_TRANSITION"
        assert event[1] is None
        assert event[2] == "IDENTIFICADA"
        assert event[3] == M2_002_RULE_ID


def test_create_initial_thesis_is_idempotent_on_natural_key(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()

    first = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    second = repository.create_initial_thesis(detection, now_ms=1_700_000_020_000)

    assert first.created_now is True
    assert second.created_now is False
    assert first.opportunity_id == second.opportunity_id
    with sqlite3.connect(db_path) as conn:
        opportunities_count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        events_count = conn.execute("SELECT COUNT(*) FROM opportunity_events").fetchone()[0]
    assert opportunities_count == 1
    assert events_count == 1


def test_create_initial_thesis_rolls_back_on_event_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result(rejection_ts=1_700_000_030_000)

    def _raise_event_error(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced_event_error")

    monkeypatch.setattr(repository, "_insert_initial_event", _raise_event_error)

    with pytest.raises(RuntimeError, match="forced_event_error"):
        repository.create_initial_thesis(detection, now_ms=1_700_000_040_000)

    with sqlite3.connect(db_path) as conn:
        opportunities_count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        events_count = conn.execute("SELECT COUNT(*) FROM opportunity_events").fetchone()[0]
    assert opportunities_count == 0
    assert events_count == 0


def test_create_standard_signal_from_validated_is_idempotent(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()
    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=1_700_000_020_000)
    repository.transition_to_validated(opportunity_id=created.opportunity_id, now_ms=1_700_000_030_000)

    first = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_040_000,
    )
    second = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_050_000,
    )

    assert first.created is True
    assert first.reason == "ok"
    assert first.signal_id is not None
    assert second.created is False
    assert second.reason == "already_exists"
    assert second.signal_id == first.signal_id

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM technical_signals").fetchone()[0]
        assert count == 1


def test_create_standard_signal_from_validated_rejects_non_validated_status(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()
    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)

    result = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_020_000,
    )

    assert result.created is False
    assert result.reason == "status_not_validada"
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM technical_signals").fetchone()[0]
    assert count == 0


def test_consume_created_signal_for_order_layer_transitions_to_consumed(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()
    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=1_700_000_020_000)
    repository.transition_to_validated(opportunity_id=created.opportunity_id, now_ms=1_700_000_030_000)
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_040_000,
    )
    assert signal.signal_id is not None

    consumed = repository.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_050_000,
    )
    second = repository.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_060_000,
    )

    assert consumed.transitioned is True
    assert consumed.current_status == "CONSUMED"
    assert consumed.reason == "decision_recorded_no_real_order"
    assert second.transitioned is False
    assert second.reason == "already_consumed"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, payload_json FROM technical_signals WHERE id = ?",
            (int(signal.signal_id),),
        ).fetchone()
        assert row is not None
        assert row[0] == "CONSUMED"
        assert "would_send_real_order" in (row[1] or "")


def test_consume_created_signal_for_order_layer_cancels_unauthorized_symbol(tmp_path: Path) -> None:
    raw_symbol = "M2ZZZUSDT"
    assert raw_symbol not in AUTHORIZED_SYMBOLS
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result(symbol=raw_symbol)
    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=1_700_000_020_000)
    repository.transition_to_validated(opportunity_id=created.opportunity_id, now_ms=1_700_000_030_000)
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_040_000,
    )
    assert signal.signal_id is not None

    consumed = repository.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_050_000,
    )

    assert consumed.transitioned is True
    assert consumed.current_status == "CANCELLED"
    assert consumed.reason == "symbol_not_authorized"


def test_list_consumed_technical_signals_and_mark_export(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository = Model2ThesisRepository(str(db_path))
    detection = _build_detection_result()
    created = repository.create_initial_thesis(detection, now_ms=1_700_000_010_000)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=1_700_000_020_000)
    repository.transition_to_validated(opportunity_id=created.opportunity_id, now_ms=1_700_000_030_000)
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=1_700_000_040_000,
    )
    assert signal.signal_id is not None
    repository.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_050_000,
    )

    consumed = repository.list_consumed_technical_signals(symbol="BTCUSDT", timeframe="H4", limit=10)
    assert len(consumed) == 1
    assert int(consumed[0]["id"]) == int(signal.signal_id)

    err1 = repository.mark_technical_signal_export_error(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_055_000,
        rule_id="M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
        error_message="temporary lock",
    )
    err2 = repository.mark_technical_signal_export_error(
        signal_id=int(signal.signal_id),
        now_ms=1_700_000_056_000,
        rule_id="M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
        error_message="temporary lock",
    )
    assert err1.updated is True
    assert err2.updated is True

    marked = repository.mark_technical_signal_exported_to_trade_signals(
        signal_id=int(signal.signal_id),
        legacy_trade_signal_id=321,
        now_ms=1_700_000_060_000,
        rule_id="M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
        metadata={"test": True},
    )
    second = repository.mark_technical_signal_exported_to_trade_signals(
        signal_id=int(signal.signal_id),
        legacy_trade_signal_id=321,
        now_ms=1_700_000_070_000,
        rule_id="M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL",
        metadata={"test": True},
    )

    assert marked.updated is True
    assert second.reason == "already_marked"
    with sqlite3.connect(db_path) as conn:
        payload_raw = conn.execute(
            "SELECT payload_json FROM technical_signals WHERE id = ?",
            (int(signal.signal_id),),
        ).fetchone()[0]
    assert '"legacy_trade_signal_id": 321' in (payload_raw or "")
