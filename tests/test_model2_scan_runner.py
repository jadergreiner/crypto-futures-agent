import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import scripts.model2.scan as scan_module
from core.model2.model_decision import ModelDecision
from core.model2.model_inference_service import InferenceServiceResult
from core.model2.scanner import DetectionResult, M2_002_RULE_ID, M2_002_THESIS_TYPE
from scripts.model2.migrate import run_up


def _prepare_model2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _prepare_source_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "source.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path):
        pass
    return db_path


def _sample_candles() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"timestamp": 1_700_000_000_000, "open": 0.1000, "high": 0.1010, "low": 0.0990, "close": 0.1005, "volume": 1000.0},
            {"timestamp": 1_700_000_300_000, "open": 0.1005, "high": 0.1020, "low": 0.1000, "close": 0.1015, "volume": 1100.0},
            {"timestamp": 1_700_000_600_000, "open": 0.1015, "high": 0.1030, "low": 0.1010, "close": 0.1020, "volume": 1200.0},
        ]
    )


def _sample_detection(symbol: str = "BTCUSDT") -> DetectionResult:
    return DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe="M5",
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=0.1010,
        zone_high=0.1030,
        trigger_price=0.1012,
        invalidation_price=0.1030,
        metadata={
            "rejection_candle": {"timestamp": 1_700_000_600_000},
        },
        rule_id=M2_002_RULE_ID,
    )


def test_detect_model_first_opportunity_gera_detection_com_modelo(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeService:
        def infer(self, model_input):  # type: ignore[no-untyped-def]
            return InferenceServiceResult(
                accepted=True,
                decision=ModelDecision(
                    action="OPEN_LONG",
                    confidence=0.72,
                    size_fraction=1.0,
                    sl_target=0.0990,
                    tp_target=0.1050,
                    reason_code="inference_from_symbol_model_agreement_raw",
                    decision_timestamp=model_input.decision_timestamp,
                    symbol=model_input.symbol,
                    model_version="m2-model-first-scan-v1",
                    metadata={
                        "model_first": True,
                        "rl_fallback": False,
                        "rl_action": "LONG",
                    },
                ),
                model_version="m2-model-first-scan-v1",
                inference_latency_ms=3,
                reason="decision_payload_valid",
                rule_id="M2-020.2-RULE-DECOUPLED-INFERENCE-SERVICE",
                details={},
            )

    result = scan_module._detect_model_first_opportunity(
        symbol="ALGOUSDT",
        timeframe="M5",
        candles_df=_sample_candles(),
        indicators=[{"rsi": 54.0, "macd_line": 0.1, "macd_signal": 0.05, "atr": 0.0020}],
        smc={"structure": {"type": "bullish"}},
        scan_timestamp=1_700_000_700_000,
        inference_service=_FakeService(),
        confidence_threshold=0.55,
    )

    assert result is not None
    assert result.side == "LONG"
    assert result.thesis_type == scan_module.M2_020_2_SCAN_THESIS_TYPE
    assert result.rule_id == scan_module.M2_020_2_SCAN_RULE_ID
    assert result.metadata["source"] == "rl_model_first_scan"
    assert result.metadata["model_decision"]["confidence"] == 0.72


def test_resolve_model_first_confidence_threshold_prioriza_simbolo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scan_module, "M2_020_2_SCAN_THRESHOLD", 0.55)
    monkeypatch.setattr(
        scan_module,
        "M2_020_2_SCAN_THRESHOLD_BY_SYMBOL",
        {"ALGOUSDT": 0.35},
    )

    assert scan_module._resolve_model_first_confidence_threshold("ALGOUSDT") == 0.35
    assert scan_module._resolve_model_first_confidence_threshold("BTCUSDT") == 0.55


def test_detect_model_first_opportunity_rejeita_abaixo_do_threshold_por_simbolo() -> None:
    class _FakeService:
        def infer(self, model_input):  # type: ignore[no-untyped-def]
            return InferenceServiceResult(
                accepted=True,
                decision=ModelDecision(
                    action="OPEN_SHORT",
                    confidence=0.38,
                    size_fraction=1.0,
                    sl_target=0.1040,
                    tp_target=0.0980,
                    reason_code="inference_from_symbol_model_agreement_raw",
                    decision_timestamp=model_input.decision_timestamp,
                    symbol=model_input.symbol,
                    model_version="m2-model-first-scan-v1",
                    metadata={
                        "model_first": True,
                        "rl_fallback": False,
                        "rl_action": "SHORT",
                    },
                ),
                model_version="m2-model-first-scan-v1",
                inference_latency_ms=3,
                reason="decision_payload_valid",
                rule_id="M2-020.2-RULE-DECOUPLED-INFERENCE-SERVICE",
                details={},
            )

    result = scan_module._detect_model_first_opportunity(
        symbol="ALGOUSDT",
        timeframe="M5",
        candles_df=_sample_candles(),
        indicators=[{"atr": 0.0020}],
        smc={"structure": {"type": "range"}},
        scan_timestamp=1_700_000_700_000,
        inference_service=_FakeService(),
        confidence_threshold=0.40,
    )

    assert result is None


def test_run_scan_model_first_persiste_oportunidade_validada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model2_db = _prepare_model2_db(tmp_path)
    source_db = _prepare_source_db(tmp_path)

    monkeypatch.setattr(scan_module, "M2_MODEL_FIRST_SCAN_SYMBOLS", ("ALGOUSDT",))
    monkeypatch.setattr(scan_module, "M2_020_2_SCAN_THRESHOLD", 0.55)
    monkeypatch.setattr(scan_module, "M2_020_2_SCAN_THRESHOLD_BY_SYMBOL", {"ALGOUSDT": 0.35})
    monkeypatch.setattr(scan_module, "_load_candles", lambda **_: _sample_candles())
    monkeypatch.setattr(scan_module, "_load_indicators", lambda **_: [{"atr": 0.0020}])
    monkeypatch.setattr(scan_module.SmartMoneyConcepts, "calculate_all_smc", lambda *_: {"structure": {"type": "bullish"}})
    monkeypatch.setattr(
        scan_module,
        "detect_initial_short_failure",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("fluxo deterministico nao deve rodar")),
    )

    detection = DetectionResult(
        detected=True,
        symbol="ALGOUSDT",
        timeframe="M5",
        side="LONG",
        thesis_type=scan_module.M2_020_2_SCAN_THESIS_TYPE,
        zone_low=0.0990,
        zone_high=0.1050,
        trigger_price=0.1020,
        invalidation_price=0.0990,
        metadata={
            "source": "rl_model_first_scan",
            "model_decision": {"confidence": 0.72, "reason_code": "ok"},
            "rejection_candle": {"timestamp": 1_700_000_600_000},
        },
        rule_id=scan_module.M2_020_2_SCAN_RULE_ID,
    )
    monkeypatch.setattr(scan_module, "_detect_model_first_opportunity", lambda **_: detection)

    summary = scan_module.run_scan(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbols=["ALGOUSDT"],
        timeframe="M5",
        candles_limit=120,
        dry_run=False,
        output_dir=tmp_path / "results",
    )

    assert summary["detections"] == 1
    assert summary["persisted_now"] == 1
    assert summary["items"][0]["status"] == "PERSISTED_MODEL_FIRST_VALIDATED"
    assert summary["items"][0]["model_first_confidence_threshold"] == 0.35

    with sqlite3.connect(model2_db) as conn:
        row = conn.execute(
            "SELECT status, side, thesis_type FROM opportunities WHERE symbol = ?",
            ("ALGOUSDT",),
        ).fetchone()

    assert row == ("VALIDADA", "LONG", scan_module.M2_020_2_SCAN_THESIS_TYPE)


def test_run_scan_preserva_fluxo_deterministico_para_outros_simbolos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model2_db = _prepare_model2_db(tmp_path)
    source_db = _prepare_source_db(tmp_path)

    monkeypatch.setattr(scan_module, "M2_MODEL_FIRST_SCAN_SYMBOLS", ("ALGOUSDT",))
    monkeypatch.setattr(scan_module, "_load_candles", lambda **_: _sample_candles())
    monkeypatch.setattr(scan_module, "_load_indicators", lambda **_: [])
    monkeypatch.setattr(scan_module.SmartMoneyConcepts, "calculate_all_smc", lambda *_: {})
    monkeypatch.setattr(
        scan_module,
        "_detect_model_first_opportunity",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("model_first nao deve rodar")),
    )
    monkeypatch.setattr(scan_module, "detect_initial_short_failure", lambda *_args, **_kwargs: _sample_detection())

    summary = scan_module.run_scan(
        source_db_path=source_db,
        model2_db_path=model2_db,
        symbols=["BTCUSDT"],
        timeframe="M5",
        candles_limit=120,
        dry_run=False,
        output_dir=tmp_path / "results",
    )

    assert summary["detections"] == 1
    assert summary["persisted_now"] == 1
    assert summary["items"][0]["status"] == "PERSISTED"

    with sqlite3.connect(model2_db) as conn:
        row = conn.execute(
            "SELECT status, side, thesis_type FROM opportunities WHERE symbol = ?",
            ("BTCUSDT",),
        ).fetchone()

    assert row == ("IDENTIFICADA", "SHORT", M2_002_THESIS_TYPE)