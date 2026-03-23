"""Suite RED para M2-025.1.

Valida o contrato canonico de frescor de candle por simbolo:
- estados permitidos: fresh, stale e absent
- paridade de regra entre shadow e live
- fail-safe para timestamp vazio, zero ou invalido
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import Mock

import pytest

import core.model2.cycle_report as cycle_report
import core.model2.live_service as live_service_module
import scripts.model2.operator_cycle_status as operator_cycle_status
from core.model2.cycle_report import SymbolReport, format_symbol_report
from core.model2.model_decision import ModelDecision


ServiceFactory = Callable[[Path], live_service_module.Model2LiveExecutionService]


def _criar_decisao(symbol: str = "BTCUSDT") -> ModelDecision:
    return ModelDecision(
        action="OPEN_LONG",
        confidence=0.73,
        size_fraction=0.25,
        sl_target=49000.0,
        tp_target=52000.0,
        reason_code="qa-red-m2-025-1",
        decision_timestamp=1_742_668_800_000,
        symbol=symbol,
        model_version="qa-red",
        metadata={},
    )


@pytest.fixture
def service_factory(monkeypatch: pytest.MonkeyPatch) -> ServiceFactory:
    class _FakeLoader:
        checkpoint_timestamp = None

    class _FakeInferenceService:
        model_version = "qa-red"

    class _FakeAlerts:
        def publish_critical(self, event_type: str, details: dict[str, Any]) -> None:
            return None

    monkeypatch.setattr(live_service_module, "RLModelLoader", _FakeLoader)
    monkeypatch.setattr(
        live_service_module,
        "ModelInferenceService",
        _FakeInferenceService,
    )
    monkeypatch.setattr(
        live_service_module,
        "Model2LiveAlertPublisher",
        _FakeAlerts,
    )

    def _factory(db_path: Path) -> live_service_module.Model2LiveExecutionService:
        config = SimpleNamespace(
            execution_mode="shadow",
            live_symbols=("BTCUSDT",),
            authorized_symbols=("BTCUSDT",),
            short_only=False,
            max_daily_entries=10,
            max_margin_per_position_usd=100.0,
            max_signal_age_ms=300_000,
            symbol_cooldown_ms=0,
            funding_rate_max_for_short=0.05,
            leverage=2,
            db_path=str(db_path),
        )
        return live_service_module.Model2LiveExecutionService(
            repository=Mock(),
            config=cast(Any, config),
            exchange=None,
            alert_publisher=cast(Any, _FakeAlerts()),
        )

    return _factory


def test_resolve_candle_freshness_contract_timestamp_recente_retorna_fresh() -> None:
    """Timestamp recente deve produzir estado fresh com reason canonico."""
    resolver = getattr(cycle_report, "resolve_candle_freshness_contract", None)

    assert callable(resolver), (
        "Esperado helper resolve_candle_freshness_contract em cycle_report"
    )

    contract = cast(Any, resolver)(
        last_candle_time="2026-03-23 10:00:00 UTC",
        signal_age_ms=60_000,
        max_signal_age_ms=300_000,
    )

    assert contract["candle_state"] == "fresh"
    assert contract["freshness_reason"] == "within_window"
    assert contract["decision_fresh"] is True


def test_resolve_candle_freshness_contract_timestamp_antigo_retorna_stale() -> None:
    """Timestamp fora da janela deve produzir stale sem perder horario."""
    resolver = getattr(cycle_report, "resolve_candle_freshness_contract", None)

    assert callable(resolver), (
        "Esperado helper resolve_candle_freshness_contract em cycle_report"
    )

    contract = cast(Any, resolver)(
        last_candle_time="2026-03-23 10:00:00 UTC",
        signal_age_ms=900_000,
        max_signal_age_ms=300_000,
    )

    assert contract["candle_state"] == "stale"
    assert contract["freshness_reason"] == "outside_window"
    assert contract["display_time"] == "2026-03-23 10:00:00 UTC"
    assert contract["decision_fresh"] is False


def test_resolve_candle_freshness_contract_timestamp_vazio_retorna_absent() -> None:
    """Timestamp vazio deve cair em absent por fail-safe."""
    resolver = getattr(cycle_report, "resolve_candle_freshness_contract", None)

    assert callable(resolver), (
        "Esperado helper resolve_candle_freshness_contract em cycle_report"
    )

    contract = cast(Any, resolver)(
        last_candle_time="",
        signal_age_ms=0,
        max_signal_age_ms=300_000,
    )

    assert contract["candle_state"] == "absent"
    assert contract["freshness_reason"] == "missing_timestamp"
    assert contract["decision_fresh"] is False


def test_resolve_candle_freshness_contract_timestamp_invalido_retorna_absent() -> None:
    """Timestamp invalido nao pode ser promovido a fresh."""
    resolver = getattr(cycle_report, "resolve_candle_freshness_contract", None)

    assert callable(resolver), (
        "Esperado helper resolve_candle_freshness_contract em cycle_report"
    )

    contract = cast(Any, resolver)(
        last_candle_time="horario-invalido",
        signal_age_ms=1,
        max_signal_age_ms=300_000,
    )

    assert contract["candle_state"] == "absent"
    assert contract["freshness_reason"] == "invalid_timestamp"
    assert contract["decision_fresh"] is False


def test_symbol_report_expoe_candle_state_e_freshness_reason() -> None:
    """SymbolReport deve carregar estado e motivo do contrato de frescor."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-23 10:05:00 UTC",
    )

    assert hasattr(report, "candle_state"), (
        "Esperado atributo candle_state em SymbolReport"
    )
    assert hasattr(report, "freshness_reason"), (
        "Esperado atributo freshness_reason em SymbolReport"
    )


def test_format_symbol_report_estado_absent_exibe_ausencia_sem_sucesso() -> None:
    """Estado absent deve explicitar ausencia de candle e sem marcador de sucesso."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-23 10:05:00 UTC",
        candles_count=0,
        last_candle_time="",
        decision="HOLD",
        confidence=0.0,
        decision_fresh=False,
    )
    setattr(report, "candle_state", "absent")
    setattr(report, "freshness_reason", "missing_timestamp")

    output = format_symbol_report(report)

    assert "absent" in output.lower()
    assert "sem candle utilizavel" in output.lower()
    assert "✓" not in output


def test_format_symbol_report_estado_stale_exibe_ultimo_horario_sem_fresh() -> None:
    """Estado stale deve manter ultimo horario e remover ambiguidade de sucesso."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-23 10:05:00 UTC",
        candles_count=1,
        last_candle_time="2020-01-01 00:00:00 UTC",
        decision="HOLD",
        confidence=0.0,
        decision_fresh=False,
    )
    setattr(report, "candle_state", "stale")
    setattr(report, "freshness_reason", "outside_window")

    output = format_symbol_report(report)

    assert "stale" in output.lower()
    assert "2020-01-01 00:00:00 UTC" in output
    assert "✓" not in output


def test_log_operational_status_sem_timestamp_propaga_estado_absent_no_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """Live service deve propagar absent quando nao houver candle utilizavel."""
    db_path = tmp_path / "modelo2.db"
    service = service_factory(db_path)
    captured: dict[str, SymbolReport] = {}

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-23 09:00:00", 0),
    )
    monkeypatch.setattr(
        live_service_module,
        "collect_position_info",
        lambda _symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )

    def _capture(report: SymbolReport) -> str:
        captured["report"] = report
        return "ok"

    monkeypatch.setattr(live_service_module, "format_symbol_report", _capture)

    service._log_operational_status(
        symbol="BTCUSDT",
        decision=_criar_decisao(),
        candles_count=0,
        last_candle_time="",
        decision_fresh=None,
    )

    report = captured["report"]
    assert getattr(report, "candle_state", None) == "absent"
    assert getattr(report, "freshness_reason", None) == "missing_timestamp"


def test_log_operational_status_timestamp_antigo_propaga_estado_stale_no_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """Live service deve distinguir stale de absent quando houver horario antigo."""
    db_path = tmp_path / "modelo2.db"
    service = service_factory(db_path)
    captured: dict[str, SymbolReport] = {}

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-23 09:00:00", 0),
    )
    monkeypatch.setattr(
        live_service_module,
        "collect_position_info",
        lambda _symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )

    def _capture(report: SymbolReport) -> str:
        captured["report"] = report
        return "ok"

    monkeypatch.setattr(live_service_module, "format_symbol_report", _capture)

    service._log_operational_status(
        symbol="BTCUSDT",
        decision=_criar_decisao(),
        candles_count=1,
        last_candle_time="2020-01-01 00:00:00 UTC",
        decision_fresh=False,
    )

    report = captured["report"]
    assert getattr(report, "candle_state", None) == "stale"
    assert getattr(report, "freshness_reason", None) == "outside_window"


def test_build_symbol_line_shadow_sem_timestamp_exibe_estado_absent() -> None:
    """Operator shadow deve explicitar absent quando nao houver candle utilizavel."""
    line = operator_cycle_status._build_symbol_line(
        symbol="BTCUSDT",
        scan_summary={
            "symbols": {
                "BTCUSDT": {
                    "candles_count": 0,
                    "last_candle_time": "",
                }
            }
        },
        track_summary=None,
        validate_summary=None,
        resolve_summary=None,
        live_execute_summary={
            "staged": [
                {"symbol": "BTCUSDT", "action": "HOLD", "confidence": 0.0}
            ]
        },
        exchange=None,
        last_train_time="2026-03-23 09:00:00",
    )

    assert "absent" in line.lower()
    assert "✓" not in line


def test_build_symbol_line_live_timestamp_antigo_exibe_estado_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator live deve tratar timestamp antigo como stale e nao fresh."""
    monkeypatch.setattr(operator_cycle_status, "M2_EXECUTION_MODE", "live")

    line = operator_cycle_status._build_symbol_line(
        symbol="BTCUSDT",
        scan_summary={
            "symbols": {
                "BTCUSDT": {
                    "candles_count": 1,
                    "last_candle_time": "2020-01-01 00:00:00 UTC",
                }
            }
        },
        track_summary=None,
        validate_summary=None,
        resolve_summary=None,
        live_execute_summary={
            "staged": [
                {
                    "symbol": "BTCUSDT",
                    "action": "OPEN_LONG",
                    "confidence": 0.7,
                }
            ]
        },
        exchange=None,
        last_train_time="2026-03-23 09:00:00",
    )

    assert "stale" in line.lower()
    assert "2020-01-01 00:00:00 UTC" in line
    assert "Candle Atualizado" not in line
