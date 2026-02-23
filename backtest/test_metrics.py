"""
Testes para MetricsCalculator — backtest/metrics.py

Cobertura:
- Unit tests (5): Sharpe, Max DD, Win Rate, Profit Factor, Consecutive Losses
- Integration tests (3): calculate_all(), validate_against_thresholds(), helpers
"""

import pytest
import numpy as np
from backtest.metrics import (
    MetricsCalculator, 
    daily_returns_from_trade_history,
    build_equity_curve
)


class TestMetricsCalculator:
    """Testes unitários para MetricsCalculator."""

    def setup_method(self):
        """Setup: criar trade history e daily returns ficticios."""
        # Trade history exemplo: 10 trades, 6 winners + 4 losers
        self.trade_history = [
            {'pnl_abs': 100.0},    # Win 1
            {'pnl_abs': -50.0},    # Loss 1
            {'pnl_abs': 150.0},    # Win 2
            {'pnl_abs': -30.0},    # Loss 2
            {'pnl_abs': 120.0},    # Win 3
            {'pnl_abs': 200.0},    # Win 4
            {'pnl_abs': -60.0},    # Loss 3
            {'pnl_abs': 180.0},    # Win 5
            {'pnl_abs': 90.0},     # Win 6
            {'pnl_abs': -100.0},   # Loss 4
        ]
        
        # Daily returns (10 days)
        self.daily_returns = np.array([0.01, -0.005, 0.015, -0.003, 0.012, 
                                       0.020, -0.006, 0.018, 0.009, -0.010])
        
        self.calculator = MetricsCalculator(
            trade_history=self.trade_history,
            daily_returns=self.daily_returns
        )

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe Ratio calculation."""
        sharpe = self.calculator.calculate_sharpe_ratio()
        
        # Deve retornar um float válido
        assert isinstance(sharpe, float)
        # Sharpe neste caso deve ser > 0
        assert sharpe > 0, f"Sharpe ratio should be > 0, got {sharpe}"

    def test_calculate_sharpe_ratio_empty_returns(self):
        """Test Sharpe Ratio com returns vazios."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([])
        )
        sharpe = calc.calculate_sharpe_ratio()
        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_zero_std(self):
        """Test Sharpe Ratio quando std = 0."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([0.01, 0.01, 0.01])  # Constant
        )
        sharpe = calc.calculate_sharpe_ratio()
        assert sharpe == 0.0

    def test_calculate_max_drawdown(self):
        """Test Max Drawdown calculation."""
        max_dd = self.calculator.calculate_max_drawdown()
        
        # Deve retornar um float > 0
        assert isinstance(max_dd, float)
        assert max_dd >= 0, f"Max drawdown should be >= 0, got {max_dd}"
        assert max_dd < 1, f"Max drawdown should be < 1, got {max_dd}"

    def test_calculate_max_drawdown_empty_returns(self):
        """Test Max Drawdown com returns vazios."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([])
        )
        max_dd = calc.calculate_max_drawdown()
        assert max_dd == 0.0

    def test_calculate_max_drawdown_uptrend(self):
        """Test Max Drawdown em uptrend (sem drawdown)."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([0.01, 0.01, 0.01, 0.01])  # Sempre up
        )
        max_dd = calc.calculate_max_drawdown()
        assert max_dd == 0.0

    def test_calculate_win_rate(self):
        """Test Win Rate calculation."""
        win_rate = self.calculator.calculate_win_rate()
        
        # 6 winners / 10 trades = 0.60 (60%)
        assert isinstance(win_rate, float)
        assert win_rate == 0.6, f"Win rate should be 0.6, got {win_rate}"

    def test_calculate_win_rate_no_trades(self):
        """Test Win Rate com trade history vazio."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([])
        )
        win_rate = calc.calculate_win_rate()
        assert win_rate == 0.0

    def test_calculate_win_rate_all_winners(self):
        """Test Win Rate quando todos os trades ganham."""
        calc = MetricsCalculator(
            trade_history=[
                {'pnl_abs': 100.0},
                {'pnl_abs': 50.0},
                {'pnl_abs': 200.0},
            ],
            daily_returns=np.array([])
        )
        win_rate = calc.calculate_win_rate()
        assert win_rate == 1.0

    def test_calculate_profit_factor(self):
        """Test Profit Factor calculation."""
        pf = self.calculator.calculate_profit_factor()
        
        # Wins: 100 + 150 + 120 + 200 + 180 + 90 = 840
        # Losses: 50 + 30 + 60 + 100 = 240
        # PF = 840 / 240 = 3.5
        assert isinstance(pf, float)
        assert pf == pytest.approx(3.5, rel=0.01)

    def test_calculate_profit_factor_no_trades(self):
        """Test Profit Factor com trade history vazio."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([])
        )
        pf = calc.calculate_profit_factor()
        assert pf == 0.0

    def test_calculate_profit_factor_no_losses(self):
        """Test Profit Factor quando não há losses."""
        calc = MetricsCalculator(
            trade_history=[
                {'pnl_abs': 100.0},
                {'pnl_abs': 50.0},
            ],
            daily_returns=np.array([])
        )
        pf = calc.calculate_profit_factor()
        assert pf == 0.0

    def test_calculate_consecutive_losses(self):
        """Test Consecutive Losses calculation."""
        max_consec = self.calculator.calculate_consecutive_losses()
        
        # Trade history: 10 trades
        # Procurando sequências de losses
        # Max consecutive = 1 (pois losses são isolados)
        assert isinstance(max_consec, int)
        assert max_consec >= 1

    def test_calculate_consecutive_losses_no_trades(self):
        """Test Consecutive Losses com trades vazios."""
        calc = MetricsCalculator(
            trade_history=[],
            daily_returns=np.array([])
        )
        max_consec = calc.calculate_consecutive_losses()
        assert max_consec == 0

    def test_calculate_consecutive_losses_long_sequence(self):
        """Test Consecutive Losses com sequência longa."""
        calc = MetricsCalculator(
            trade_history=[
                {'pnl_abs': 100.0},
                {'pnl_abs': -10.0},  # Loss 1
                {'pnl_abs': -20.0},  # Loss 2
                {'pnl_abs': -30.0},  # Loss 3
                {'pnl_abs': 50.0},
                {'pnl_abs': -5.0},   # Loss 1
            ],
            daily_returns=np.array([])
        )
        max_consec = calc.calculate_consecutive_losses()
        assert max_consec == 3, f"Max consecutive should be 3, got {max_consec}"

    def test_calculate_all(self):
        """Test calculate_all() retorna dict com todas 6 métricas."""
        metrics = self.calculator.calculate_all()
        
        assert isinstance(metrics, dict)
        assert 'sharpe' in metrics
        assert 'max_dd' in metrics
        assert 'win_rate' in metrics
        assert 'profit_factor' in metrics
        assert 'consec_losses' in metrics
        assert len(metrics) == 5

    def test_validate_against_thresholds_pass(self):
        """Test validate_against_thresholds quando métricas passam."""
        metrics = {
            'sharpe': 1.0,      # >= 0.80 ✓
            'max_dd': 0.10,     # <= 0.12 ✓
            'win_rate': 0.60,   # >= 0.45 ✓
            'profit_factor': 2.0,  # >= 1.5 ✓
            'consec_losses': 3,  # <= 5 ✓
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is True

    def test_validate_against_thresholds_fail_sharpe(self):
        """Test validate_against_thresholds quando Sharpe falha."""
        metrics = {
            'sharpe': 0.5,      # < 0.80 ✗
            'max_dd': 0.10,
            'win_rate': 0.60,
            'profit_factor': 2.0,
            'consec_losses': 3,
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is False

    def test_validate_against_thresholds_fail_max_dd(self):
        """Test validate_against_thresholds quando Max DD falha."""
        metrics = {
            'sharpe': 1.0,
            'max_dd': 0.15,     # > 0.12 ✗
            'win_rate': 0.60,
            'profit_factor': 2.0,
            'consec_losses': 3,
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is False

    def test_validate_against_thresholds_fail_win_rate(self):
        """Test validate_against_thresholds quando Win Rate falha."""
        metrics = {
            'sharpe': 1.0,
            'max_dd': 0.10,
            'win_rate': 0.40,   # < 0.45 ✗
            'profit_factor': 2.0,
            'consec_losses': 3,
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is False

    def test_validate_against_thresholds_fail_profit_factor(self):
        """Test validate_against_thresholds quando Profit Factor falha."""
        metrics = {
            'sharpe': 1.0,
            'max_dd': 0.10,
            'win_rate': 0.60,
            'profit_factor': 1.0,  # < 1.5 ✗
            'consec_losses': 3,
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is False

    def test_validate_against_thresholds_fail_consec_losses(self):
        """Test validate_against_thresholds quando Consecutive Losses falha."""
        metrics = {
            'sharpe': 1.0,
            'max_dd': 0.10,
            'win_rate': 0.60,
            'profit_factor': 2.0,
            'consec_losses': 7,  # > 5 ✗
        }
        
        result = self.calculator.validate_against_thresholds(metrics)
        assert result is False


class TestHelperFunctions:
    """Testes para helper functions."""

    def test_daily_returns_from_trade_history(self):
        """Test daily_returns_from_trade_history()."""
        trade_history = [
            {'pnl_abs': 100.0},
            {'pnl_abs': -50.0},
            {'pnl_abs': 150.0},
        ]
        initial_capital = 10000.0
        
        returns = daily_returns_from_trade_history(trade_history, initial_capital)
        
        assert isinstance(returns, np.ndarray)
        assert len(returns) == 3
        assert returns[0] == pytest.approx(0.01)      # 100 / 10000
        assert returns[1] == pytest.approx(-0.005)    # -50 / 10000
        assert returns[2] == pytest.approx(0.015)     # 150 / 10000

    def test_daily_returns_from_trade_history_empty(self):
        """Test daily_returns_from_trade_history() com histórico vazio."""
        returns = daily_returns_from_trade_history([], 10000.0)
        assert len(returns) == 0

    def test_daily_returns_from_trade_history_zero_capital(self):
        """Test daily_returns_from_trade_history() com capital zero."""
        trade_history = [{'pnl_abs': 100.0}]
        returns = daily_returns_from_trade_history(trade_history, 0.0)
        assert len(returns) == 0

    def test_build_equity_curve(self):
        """Test build_equity_curve()."""
        daily_returns = np.array([0.01, -0.005, 0.015])
        initial_capital = 10000.0
        
        equity_curve = build_equity_curve(daily_returns, initial_capital)
        
        assert isinstance(equity_curve, np.ndarray)
        assert len(equity_curve) == 4  # 1 inicial + 3 retornos
        assert equity_curve[0] == pytest.approx(10000.0)  # Inicial

    def test_build_equity_curve_empty(self):
        """Test build_equity_curve() com returns vazios."""
        daily_returns = np.array([])
        initial_capital = 10000.0
        
        equity_curve = build_equity_curve(daily_returns, initial_capital)
        
        assert len(equity_curve) == 1
        assert equity_curve[0] == pytest.approx(10000.0)


class TestIntegration:
    """Testes de integração."""

    def test_full_backtest_workflow(self):
        """Test workflow completo: trade history -> metrics -> validation."""
        # Scenario: Backtesting com 20 trades validados
        trade_history = [
            {'pnl_abs': 100.0},     # 1
            {'pnl_abs': 150.0},     # 2
            {'pnl_abs': -50.0},     # 3
            {'pnl_abs': 200.0},     # 4
            {'pnl_abs': -30.0},     # 5
            {'pnl_abs': 120.0},     # 6
            {'pnl_abs': 180.0},     # 7
            {'pnl_abs': -60.0},     # 8
            {'pnl_abs': 90.0},      # 9
            {'pnl_abs': 110.0},     # 10
            {'pnl_abs': -40.0},     # 11
            {'pnl_abs': 140.0},     # 12
            {'pnl_abs': 160.0},     # 13
            {'pnl_abs': -20.0},     # 14
            {'pnl_abs': 130.0},     # 15
            {'pnl_abs': 170.0},     # 16
            {'pnl_abs': -70.0},     # 17
            {'pnl_abs': 95.0},      # 18
            {'pnl_abs': 125.0},     # 19
            {'pnl_abs': 80.0},      # 20
        ]
        
        daily_returns = daily_returns_from_trade_history(trade_history, 10000.0)
        
        calc = MetricsCalculator(
            trade_history=trade_history,
            daily_returns=daily_returns
        )
        
        # Calculate all metrics
        metrics = calc.calculate_all()
        assert len(metrics) == 5
        
        # All metrics should be numbers
        for key, value in metrics.items():
            assert isinstance(value, (int, float))
        
        # Validate — should work without error
        is_valid = calc.validate_against_thresholds(metrics)
        assert is_valid  # Should pass validation with good metrics


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
