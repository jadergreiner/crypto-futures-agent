"""Testes para modulo cycle_report.py."""

import pytest
from core.model2.cycle_report import (
    SymbolReport,
    format_symbol_report,
    format_cycle_summary,
    _decision_icon,
    _progress_bar,
)


class TestSymbolReport:
    """Testes para dataclass SymbolReport."""

    def test_creation_minimal(self):
        """SymbolReport criado com campos minimos."""
        r = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03"
        )
        assert r.symbol == "BTCUSDT"
        assert r.timeframe == "H4"
        assert r.decision == "INDEFINIDA"
        assert r.pending_episodes == 0

    def test_creation_full(self):
        """SymbolReport com todos os campos."""
        r = SymbolReport(
            symbol="ETHUSDT",
            timeframe="H1",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            last_candle_time="2026-03-22 08:00 UTC",
            decision="OPEN_LONG",
            confidence=0.89,
            decision_fresh=True,
            episode_id=1850,
            episode_persisted=True,
            reward=0.0120,
            last_train_time="2026-03-15 17:22:40",
            pending_episodes=37,
            has_position=True,
            position_side="LONG",
            position_qty=0.05,
            position_entry_price=1823.40,
            position_mark_price=1847.10,
            position_pnl_pct=1.23,
            position_pnl_usd=11.20,
            execution_mode="shadow"
        )
        assert r.symbol == "ETHUSDT"
        assert r.confidence == 0.89
        assert r.position_pnl_pct == 1.23


class TestDecisionIcon:
    """Testes para funcao _decision_icon."""

    def test_open_long(self):
        """Icone para OPEN_LONG."""
        assert _decision_icon("OPEN_LONG") == "🟢"

    def test_open_short(self):
        """Icone para OPEN_SHORT."""
        assert _decision_icon("OPEN_SHORT") == "🔴"

    def test_hold(self):
        """Icone para HOLD."""
        assert _decision_icon("HOLD") == "⏸"

    def test_unknown(self):
        """Icone para decisao desconhecida."""
        assert _decision_icon("UNKNOWN") == "❓"


class TestProgressBar:
    """Testes para funcao _progress_bar."""

    def test_empty(self):
        """Barra vazia (0%)."""
        bar = _progress_bar(0.0, width=10)
        assert bar == "[░░░░░░░░░░]"

    def test_full(self):
        """Barra cheia (100%)."""
        bar = _progress_bar(1.0, width=10)
        assert bar == "[██████████]"

    def test_half(self):
        """Barra meia (50%)."""
        bar = _progress_bar(0.5, width=10)
        assert bar == "[█████░░░░░]"


class TestFormatSymbolReport:
    """Testes para funcao format_symbol_report."""

    def test_format_hold_no_position(self):
        """Formata relatorio de HOLD sem posicao."""
        r = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            last_candle_time="2026-03-22 08:00 UTC",
            decision="HOLD",
            confidence=0.72,
            episode_id=1847,
            reward=-0.0030,
            last_train_time="2026-03-15 17:22:40",
            pending_episodes=37,
            execution_mode="shadow"
        )
        output = format_symbol_report(r)
        assert "BTCUSDT" in output
        assert "⏸" in output
        assert "HOLD" in output
        assert "SEM POSICAO" in output
        assert "37/100" in output

    def test_format_open_long_with_position(self):
        """Formata relatorio de OPEN_LONG com posicao aberta."""
        r = SymbolReport(
            symbol="ETHUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            candles_count=500,
            decision="OPEN_LONG",
            confidence=0.89,
            episode_id=1850,
            reward=0.0120,
            has_position=True,
            position_side="LONG",
            position_qty=0.05,
            position_entry_price=1823.40,
            position_mark_price=1847.10,
            position_pnl_pct=1.23,
            position_pnl_usd=11.20,
            execution_mode="shadow"
        )
        output = format_symbol_report(r)
        assert "ETHUSDT" in output
        assert "🟢" in output
        assert "OPEN_LONG" in output
        assert "LONG" in output
        assert "0.05" in output
        assert "1.23" in output

    def test_output_structure(self):
        """Valida estrutura do output (separadores, linhas)."""
        r = SymbolReport(
            symbol="TEST",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03"
        )
        output = format_symbol_report(r)
        lines = output.split("\n")
        # Deve ter separador superior, dados, separador inferior
        assert lines[0].startswith("─")
        assert lines[-1].startswith("─")
        assert len(lines) >= 8  # pelo menos header + 6 campos + 2 separadores


class TestFormatCycleSummary:
    """Testes para funcao format_cycle_summary."""

    def test_cycle_summary_single_symbol(self):
        """Formata resumo com um simbolo."""
        r1 = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-03-22 08:54:03",
            decision="HOLD"
        )
        output = format_cycle_summary([r1], cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "CICLO #47" in output
        assert "Resumo: 1 simbolos" in output
        assert "1 HOLD" in output

    def test_cycle_summary_multiple_symbols(self):
        """Formata resumo com múltiplos símbolos."""
        reports = [
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="HOLD"
            ),
            SymbolReport(
                symbol="ETHUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                decision="OPEN_LONG"
            ),
        ]
        output = format_cycle_summary(reports, cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "CICLO #47" in output
        assert "Resumo: 2 simbolos" in output
        assert "1 sinais" in output
        assert "1 HOLD" in output

    def test_cycle_summary_with_pnl(self):
        """Formata resumo com PnL total."""
        reports = [
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="H4",
                timestamp="2026-03-22 08:54:03",
                has_position=True,
                position_pnl_usd=50.0
            ),
        ]
        output = format_cycle_summary(reports, cycle_number=47, next_cycle_time="2026-03-22 09:00")
        assert "PnL total" in output
        assert "$50.00" in output or "50.0" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
