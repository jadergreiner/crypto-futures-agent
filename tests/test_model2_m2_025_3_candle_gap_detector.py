"""Suite RED M2-025.3: Detector de lacuna de candles por janela.

Objetivo: Detectar lacunas por simbolo e timeframe com alerta quando
houver janela sem atualizacao.

Status: RED — testes devem falhar antes da implementacao.
"""

from __future__ import annotations

import time

import pytest


class TestCandleGapDetectorContract:
    """RED: Contrato do detector de lacuna."""

    def test_detect_gap_returns_gap_when_ts_too_old(self) -> None:
        """R1: Lacuna detectada quando ultimo candle eh mais antigo que janela."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        old_ts = now_ms - 300_001  # mais de 5 min atras

        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=old_ts,
            gap_window_ms=300_000,
        )

        assert result["has_gap"] is True
        assert result["symbol"] == "BTCUSDT"
        assert result["timeframe"] == "1m"
        assert "gap_ms" in result
        assert result["gap_ms"] > 0

    def test_detect_gap_no_gap_when_recent(self) -> None:
        """R2: Sem lacuna quando ultimo candle eh recente."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        recent_ts = now_ms - 30_000  # 30s atras

        result = detect_candle_gap(
            symbol="ETHUSDT",
            timeframe="1m",
            last_candle_ts_ms=recent_ts,
            gap_window_ms=300_000,
        )

        assert result["has_gap"] is False
        assert result["gap_ms"] == 0

    def test_detect_gap_absent_when_ts_none(self) -> None:
        """R3: Lacuna ABSENT quando timestamp ausente (None)."""
        from core.model2.cycle_report import detect_candle_gap

        result = detect_candle_gap(
            symbol="SOLUSDT",
            timeframe="1m",
            last_candle_ts_ms=None,
            gap_window_ms=300_000,
        )

        assert result["has_gap"] is True
        assert result["gap_reason"] == "absent"

    def test_detect_gap_includes_alert_message(self) -> None:
        """R4: Resultado inclui mensagem de alerta quando gap detectado."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        old_ts = now_ms - 600_000  # 10 min atras

        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=old_ts,
            gap_window_ms=300_000,
        )

        assert result["has_gap"] is True
        assert "alert_message" in result
        assert len(result["alert_message"]) > 0

    def test_detect_gap_default_window_300s(self) -> None:
        """R5: Janela padrao de 300s quando nao especificada."""
        from core.model2.cycle_report import detect_candle_gap, DEFAULT_GAP_WINDOW_MS

        assert DEFAULT_GAP_WINDOW_MS == 300_000

    def test_detect_gap_result_has_required_fields(self) -> None:
        """R6: Resultado sempre tem campos obrigatorios."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=now_ms,
            gap_window_ms=300_000,
        )

        required = {"has_gap", "symbol", "timeframe", "gap_ms", "gap_reason", "alert_message"}
        assert required.issubset(result.keys())

    def test_detect_gap_does_not_block_operation(self) -> None:
        """Guardrail: Detector de lacuna nao levanta excecao em nenhum cenario."""
        from core.model2.cycle_report import detect_candle_gap

        # Nem mesmo com inputs inesperados deve levantar excecao
        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=None,
            gap_window_ms=0,
        )

        assert isinstance(result, dict)
        assert "has_gap" in result

    def test_detect_gap_gap_reason_stale_when_old(self) -> None:
        """R7: gap_reason == 'stale' quando ts existe mas eh antigo."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        old_ts = now_ms - 500_000

        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=old_ts,
            gap_window_ms=300_000,
        )

        assert result["gap_reason"] == "stale"

    def test_detect_gap_no_reason_when_fresh(self) -> None:
        """R8: gap_reason vazio quando fresco."""
        from core.model2.cycle_report import detect_candle_gap

        now_ms = int(time.time() * 1000)
        recent_ts = now_ms - 10_000

        result = detect_candle_gap(
            symbol="BTCUSDT",
            timeframe="1m",
            last_candle_ts_ms=recent_ts,
            gap_window_ms=300_000,
        )

        assert result["gap_reason"] == ""
        assert result["alert_message"] == ""
