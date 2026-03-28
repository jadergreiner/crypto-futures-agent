"""Suite RED M2-025.11: frescor e lacuna de dados no detector.

Objetivo:
- Validar frescor de candles no contexto do DetectorInput
- Detectar lacuna por janela configuravel
- Garantir fail-safe auditavel na ausencia de dados

Status: RED - testes devem falhar antes da implementacao.
"""

from __future__ import annotations


from core.model2.scanner import DetectorInput


def _smc_base() -> dict[str, object]:
    return {
        "structure": {"type": "range"},
        "order_blocks": [],
        "fvgs": [],
    }


def _detector_input(candles: list[dict[str, object]], *, scan_ts: int) -> DetectorInput:
    return DetectorInput(
        symbol="BTCUSDT",
        timeframe="H4",
        candles=candles,
        indicators=[],
        smc=_smc_base(),
        scan_timestamp=scan_ts,
    )


class TestM202511DataFreshnessContract:
    """RED: contrato de frescor/lacuna para entrada do scanner."""

    def test_validate_detector_input_returns_absent_when_candles_empty(self) -> None:
        """R1: candles vazios devem retornar estado absent por fail-safe."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(candles=[], scan_ts=1_700_000_000_000)

        result = validate_detector_input_data_freshness(detector_input)

        assert result["is_fresh"] is False
        assert result["candle_state"] == "absent"
        assert result["gap_reason"] == "absent"

    def test_validate_detector_input_returns_stale_when_last_candle_outside_window(self) -> None:
        """R2: ultimo candle fora da janela deve retornar stale."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(
            candles=[
                {"timestamp": 1_700_000_000_000, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
                {"timestamp": 1_700_000_300_000, "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0},
                {"timestamp": 1_700_000_600_000, "open": 2.0, "high": 3.0, "low": 1.8, "close": 2.7},
            ],
            scan_ts=1_700_001_500_001,
        )

        result = validate_detector_input_data_freshness(
            detector_input,
            freshness_window_ms=300_000,
            gap_window_ms=300_000,
        )

        assert result["is_fresh"] is False
        assert result["candle_state"] == "stale"
        assert result["gap_reason"] == "stale"
        assert result["has_gap"] is True

    def test_validate_detector_input_returns_fresh_when_last_candle_inside_window(self) -> None:
        """R3: ultimo candle dentro da janela deve retornar fresh sem gap."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(
            candles=[
                {"timestamp": 1_700_000_000_000, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
                {"timestamp": 1_700_000_300_000, "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0},
                {"timestamp": 1_700_000_600_000, "open": 2.0, "high": 3.0, "low": 1.8, "close": 2.7},
            ],
            scan_ts=1_700_000_700_000,
        )

        result = validate_detector_input_data_freshness(
            detector_input,
            freshness_window_ms=300_000,
            gap_window_ms=300_000,
        )

        assert result["is_fresh"] is True
        assert result["candle_state"] == "fresh"
        assert result["has_gap"] is False
        assert result["gap_reason"] == ""

    def test_validate_detector_input_uses_configurable_gap_window(self) -> None:
        """R4: janela menor deve acusar gap onde janela maior nao acusa."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(
            candles=[
                {"timestamp": 1_700_000_000_000, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
                {"timestamp": 1_700_000_100_000, "open": 1.5, "high": 2.5, "low": 1.0, "close": 2.0},
                {"timestamp": 1_700_000_200_000, "open": 2.0, "high": 3.0, "low": 1.8, "close": 2.7},
            ],
            scan_ts=1_700_000_450_000,
        )

        strict_window = validate_detector_input_data_freshness(
            detector_input,
            freshness_window_ms=600_000,
            gap_window_ms=200_000,
        )
        relaxed_window = validate_detector_input_data_freshness(
            detector_input,
            freshness_window_ms=600_000,
            gap_window_ms=300_000,
        )

        assert strict_window["has_gap"] is True
        assert strict_window["gap_reason"] == "stale"
        assert relaxed_window["has_gap"] is False
        assert relaxed_window["gap_reason"] == ""

    def test_validate_detector_input_fail_safe_when_timestamp_invalid(self) -> None:
        """R5: timestamp invalido nunca gera excecao; retorna absent conservador."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(
            candles=[
                {"timestamp": "invalido", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
            ],
            scan_ts=1_700_000_500_000,
        )

        result = validate_detector_input_data_freshness(detector_input)

        assert result["is_fresh"] is False
        assert result["candle_state"] == "absent"
        assert result["gap_reason"] == "absent"

    def test_validate_detector_input_result_has_required_fields(self) -> None:
        """R6: contrato deve expor campos obrigatorios para auditoria."""
        from core.model2.scanner import validate_detector_input_data_freshness

        detector_input = _detector_input(candles=[], scan_ts=1_700_000_000_000)
        result = validate_detector_input_data_freshness(detector_input)

        required = {
            "is_fresh",
            "candle_state",
            "freshness_reason",
            "has_gap",
            "gap_reason",
            "gap_ms",
            "alert_message",
            "last_candle_ts_ms",
        }
        assert required.issubset(result.keys())
