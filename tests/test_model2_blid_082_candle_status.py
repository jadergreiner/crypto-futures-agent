"""Suite RED para BLID-082.

Valida contrato de exibicao de candles no bloco [M2][SYM]:
- Com candle fresco: deve explicitar Candle Atualizado.
- Sem candle fresco: deve explicitar estado stale sem sucesso ambiguo.
- Comportamento consistente entre fluxos live/shadow.
- Fail-safe preservado em falhas de formatacao.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

import core.model2.live_service as live_service_module
import scripts.model2.operator_cycle_status as operator_cycle_status
from core.model2.cycle_report import SymbolReport, format_symbol_report
from core.model2.model_decision import ModelDecision


ServiceFactory = Callable[[Path], live_service_module.Model2LiveExecutionService]


def _criar_decisao(symbol: str = "BTCUSDT") -> ModelDecision:
    return ModelDecision(
        action="OPEN_LONG",
        confidence=0.81,
        size_fraction=0.25,
        sl_target=49000.0,
        tp_target=52000.0,
        reason_code="qa_red",
        decision_timestamp=1_742_668_800_000,
        symbol=symbol,
        model_version="qa-red",
        metadata={},
    )


@pytest.fixture  # type: ignore[misc]
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
            max_signal_age_ms=60_000,
            symbol_cooldown_ms=0,
            funding_rate_max_for_short=0.05,
            leverage=2,
            db_path=str(db_path),
        )
        return live_service_module.Model2LiveExecutionService(
            repository=Mock(),
            config=config,
            exchange=None,
            alert_publisher=_FakeAlerts(),
        )

    return _factory


def test_format_symbol_report_com_candle_fresco_exibe_candle_atualizado() -> None:
    """Com dado fresco, o texto deve explicitar Candle Atualizado."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 19:03:56 BRT",
        candles_count=12,
        last_candle_time="2026-03-22 19:00:00 BRT",
        decision="OPEN_LONG",
        confidence=0.81,
        decision_fresh=True,
    )

    output = format_symbol_report(report)

    assert "Candle Atualizado" in output
    assert "2026-03-22 19:00:00 BRT" in output


def test_format_symbol_report_sem_candle_fresco_exibe_stale_sem_sucesso() -> None:
    """Sem dado fresco, o texto deve explicitar stale sem marcador de sucesso."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 19:03:56 BRT",
        candles_count=0,
        last_candle_time="",
        decision="HOLD",
        confidence=0.5,
        decision_fresh=False,
    )

    output = format_symbol_report(report)

    assert "stale" in output.lower()
    assert "✓" not in output


def test_format_symbol_report_preserva_blocos_decisao_episodio_treino_posicao() -> None:
    """Contrato de estrutura dos demais campos deve ser preservado."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 19:03:56 BRT",
        candles_count=0,
        last_candle_time="",
        decision="HOLD",
        confidence=0.0,
        decision_fresh=False,
        episode_id=7,
        episode_persisted=True,
        reward=0.2,
        last_train_time="2026-03-22 18:00:00",
        pending_episodes=2,
        has_position=False,
    )

    output = format_symbol_report(report)

    assert "Decisao  :" in output
    assert "Episodio :" in output
    assert "Treino   :" in output
    assert "Posicao  :" in output


def test_format_symbol_report_com_timestamp_vazio_nao_trata_como_fresco() -> None:
    """Timestamp vazio nao pode representar candle fresco."""
    report = SymbolReport(
        symbol="BTCUSDT",
        timeframe="H4",
        timestamp="2026-03-22 19:03:56 BRT",
        candles_count=10,
        last_candle_time="",
        decision="OPEN_LONG",
        confidence=0.8,
        decision_fresh=False,
    )

    output = format_symbol_report(report)

    assert "stale" in output.lower()


def test_log_operational_status_sem_candle_fresco_mantem_fail_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """No fluxo live_service, ausencia de candle fresco deve permanecer nao fresca."""
    db_path = tmp_path / "modelo2.db"
    service = service_factory(db_path)
    captured: dict[str, SymbolReport] = {}

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-22 18:00:00", 0),
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
    )

    assert captured["report"].decision_fresh is False


def test_build_symbol_line_shadow_sem_candles_exibe_estado_stale() -> None:
    """No fluxo operator shadow sem candles, status deve explicitar stale."""
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
        last_train_time="2026-03-22 18:00:00",
    )

    assert "stale" in line.lower()
    assert "✓" not in line


def test_build_symbol_line_live_com_candle_fresco_exibe_candle_atualizado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No fluxo operator live com candle fresco, deve explicitar Candle Atualizado."""
    monkeypatch.setattr(operator_cycle_status, "M2_EXECUTION_MODE", "live")

    line = operator_cycle_status._build_symbol_line(
        symbol="BTCUSDT",
        scan_summary={
            "symbols": {
                "BTCUSDT": {
                    "candles_count": 5,
                    "last_candle_time": "2026-03-22 19:00:00 BRT",
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
        last_train_time="2026-03-22 18:00:00",
    )

    assert "Candle Atualizado" in line
    assert "2026-03-22 19:00:00 BRT" in line


def test_log_operational_status_falha_formatacao_aciona_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    service_factory: ServiceFactory,
) -> None:
    """Falha de formatacao deve acionar fallback seguro do live_service."""
    db_path = tmp_path / "modelo2.db"
    service = service_factory(db_path)
    fallback = Mock()

    monkeypatch.setattr(
        live_service_module,
        "collect_training_info",
        lambda _db: ("2026-03-22 18:00:00", 0),
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
    monkeypatch.setattr(
        live_service_module,
        "format_symbol_report",
        lambda _report: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(service, "_log_operational_status_fallback", fallback)

    service._log_operational_status(
        symbol="BTCUSDT",
        decision=_criar_decisao(),
        candles_count=0,
        last_candle_time="",
    )

    fallback.assert_called_once()
