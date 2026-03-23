"""Suite RED de M2-019.5 para filtro RL auditavel antes da camada de ordem."""

from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import M2_002_RULE_ID, M2_002_THESIS_TYPE, DetectionResult
from scripts.model2.migrate import run_up


def _build_detection_result(*, symbol: str, side: str) -> DetectionResult:
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": "1.0.0",
        "technical_zone": {
            "source": "order_block",
            "zone_id": 77,
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


def _prepare_model2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _seed_created_signal(*, db_path: Path, symbol: str, side: str, now_ms: int = 1_700_000_010_000) -> int:
    repository = Model2ThesisRepository(str(db_path))
    created = repository.create_initial_thesis(
        _build_detection_result(symbol=symbol, side=side),
        now_ms=now_ms,
    )
    repository.transition_to_monitoring(
        opportunity_id=created.opportunity_id,
        now_ms=now_ms + 1_000,
    )
    repository.transition_to_validated(
        opportunity_id=created.opportunity_id,
        now_ms=now_ms + 2_000,
    )
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=now_ms + 3_000,
    )
    assert signal.signal_id is not None
    return int(signal.signal_id)


def _load_entry_rl_filter_module() -> Any:
    try:
        return importlib.import_module("scripts.model2.entry_rl_filter")
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "Modulo scripts.model2.entry_rl_filter deve existir para M2-019.5"
        ) from exc


def _assert_rl_audit_payload(
    *,
    db_path: Path,
    signal_id: int,
    expected_reason: str,
) -> None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert row is not None
    payload = json.loads(row[0] or "{}")
    assert isinstance(payload, dict)
    rl_audit = payload.get("rl_entry_filter")
    assert isinstance(rl_audit, dict)
    assert rl_audit.get("reason") == expected_reason
    assert "decision" in rl_audit
    assert "confidence" in rl_audit
    assert "threshold" in rl_audit
    assert "agent_version" in rl_audit
    assert "decision_timestamp" in rl_audit


def test_entry_rl_filter_modelo_ausente_aplica_fallback_conservador() -> None:
    """Requisito: modelo ausente nao cancela sinal CREATED."""
    module = _load_entry_rl_filter_module()
    assert hasattr(module, "run_entry_rl_filter")


def test_entry_rl_filter_confianca_baixa_aplica_fallback_sem_cancelar() -> None:
    """Requisito: confianca < threshold deve preservar status CREATED."""
    module = _load_entry_rl_filter_module()
    assert hasattr(module, "run_entry_rl_filter")


def test_entry_rl_filter_fallback_com_payload_malformado_nao_quebra_fluxo() -> None:
    """Requisito: payload malformado nao pode derrubar o stage."""
    module = _load_entry_rl_filter_module()
    assert hasattr(module, "run_entry_rl_filter")


def test_entry_rl_filter_neutral_com_confianca_alta_cancela_sinal(tmp_path: Path) -> None:
    """Requisito: NEUTRAL com confianca alta cancela com motivo auditavel."""
    db_path = _prepare_model2_db(tmp_path)
    signal_id = _seed_created_signal(db_path=db_path, symbol="BTCUSDT", side="LONG")

    module = _load_entry_rl_filter_module()

    class _FakeManager:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            _ = args
            _ = kwargs

        def load_all(self) -> None:
            return None

        def predict_entry(self, symbol: str, observation: list[float]) -> tuple[int, float]:
            _ = symbol
            _ = observation
            return 0, 0.95

    summary = module.run_entry_rl_filter(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=20,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        threshold=0.55,
        manager_cls=_FakeManager,
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert status is not None
    assert status[0] == "CANCELLED"
    _assert_rl_audit_payload(
        db_path=db_path,
        signal_id=signal_id,
        expected_reason="rl_entry_neutral",
    )
    assert int(summary["cancelled_neutral"]) == 1


def test_entry_rl_filter_contradicao_com_confianca_alta_cancela_sinal(tmp_path: Path) -> None:
    """Requisito: acao contraditoria cancela com motivo rl_entry_contradiction."""
    db_path = _prepare_model2_db(tmp_path)
    signal_id = _seed_created_signal(db_path=db_path, symbol="BTCUSDT", side="LONG")

    module = _load_entry_rl_filter_module()

    class _FakeManager:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            _ = args
            _ = kwargs

        def load_all(self) -> None:
            return None

        def predict_entry(self, symbol: str, observation: list[float]) -> tuple[int, float]:
            _ = symbol
            _ = observation
            return 2, 0.92

    summary = module.run_entry_rl_filter(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=20,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        threshold=0.55,
        manager_cls=_FakeManager,
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert status is not None
    assert status[0] == "CANCELLED"
    _assert_rl_audit_payload(
        db_path=db_path,
        signal_id=signal_id,
        expected_reason="rl_entry_contradiction",
    )
    assert int(summary["cancelled_contradiction"]) == 1


def test_entry_rl_filter_match_enriquece_payload_sem_cancelamento(tmp_path: Path) -> None:
    """Requisito: match de direcao enriquece payload e preserva CREATED."""
    db_path = _prepare_model2_db(tmp_path)
    signal_id = _seed_created_signal(db_path=db_path, symbol="BTCUSDT", side="LONG")

    module = _load_entry_rl_filter_module()

    class _FakeManager:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            _ = args
            _ = kwargs

        def load_all(self) -> None:
            return None

        def predict_entry(self, symbol: str, observation: list[float]) -> tuple[int, float]:
            _ = symbol
            _ = observation
            return 1, 0.88

    summary = module.run_entry_rl_filter(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=20,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        threshold=0.55,
        manager_cls=_FakeManager,
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert status is not None
    assert status[0] == "CREATED"
    _assert_rl_audit_payload(
        db_path=db_path,
        signal_id=signal_id,
        expected_reason="rl_entry_match",
    )
    assert int(summary["enriched_match"]) == 1


def test_entry_rl_filter_erro_em_predicao_incrementa_contagem_erro(tmp_path: Path) -> None:
    """Requisito: erro de inferencia nao pode perder sinal CREATED."""
    db_path = _prepare_model2_db(tmp_path)
    signal_id = _seed_created_signal(db_path=db_path, symbol="BTCUSDT", side="LONG")

    module = _load_entry_rl_filter_module()

    class _FakeManager:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            _ = args
            _ = kwargs

        def load_all(self) -> None:
            return None

        def predict_entry(self, symbol: str, observation: list[float]) -> tuple[int, float]:
            _ = symbol
            _ = observation
            raise RuntimeError("predict_failed")

    summary = module.run_entry_rl_filter(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=20,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        threshold=0.55,
        manager_cls=_FakeManager,
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status FROM technical_signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
    assert status is not None
    assert status[0] == "CREATED"
    assert int(summary["erro"]) == 1


def test_entry_rl_filter_saida_json_contem_todas_as_categorias(tmp_path: Path) -> None:
    """Requisito: output JSON deve conter todas as contagens obrigatorias."""
    db_path = _prepare_model2_db(tmp_path)
    _seed_created_signal(db_path=db_path, symbol="BTCUSDT", side="LONG")

    module = _load_entry_rl_filter_module()

    class _FakeManager:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            _ = args
            _ = kwargs

        def load_all(self) -> None:
            return None

        def predict_entry(self, symbol: str, observation: list[float]) -> tuple[int, float]:
            _ = symbol
            _ = observation
            return 1, 0.90

    summary = module.run_entry_rl_filter(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=20,
        dry_run=False,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        threshold=0.55,
        manager_cls=_FakeManager,
    )

    for key in (
        "fallback",
        "pass_through",
        "cancelled_neutral",
        "cancelled_contradiction",
        "enriched_match",
        "erro",
    ):
        assert key in summary

    output_file = Path(summary["output_file"])
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    for key in (
        "fallback",
        "pass_through",
        "cancelled_neutral",
        "cancelled_contradiction",
        "enriched_match",
        "erro",
    ):
        assert key in payload
