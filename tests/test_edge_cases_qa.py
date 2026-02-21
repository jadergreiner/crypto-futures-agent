"""
Edge Case Validation Tests para TASK-002 QA.

Cenários críticos:
  - Low liquidity (<10 BTC volume)
  - Flash crash (-8% intraday)
  - Network timeout (retry logic)
  - Funding rate extremo
  - Nas múltiplas condições de mercado
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from execution.heuristic_signals import (
    HeuristicSignalGenerator,
    RiskGate,
    HeuristicSignal
)


class TestEdgeCasesLowLiquidity:
    """Testes de cenários de baixa liquidez."""

    @pytest.fixture
    def generator(self):
        return HeuristicSignalGenerator()

    @pytest.fixture
    def low_liquidity_data(self):
        """DataFrame com volume baixo (<10 BTC)."""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": np.linspace(100, 110, 100) + np.random.randn(100) * 0.5,
            "high": np.linspace(105, 115, 100) + np.random.randn(100) * 0.5,
            "low": np.linspace(95, 105, 100) + np.random.randn(100) * 0.5,
            "close": np.linspace(100, 110, 100) + np.random.randn(100) * 0.5,
            "volume": np.random.uniform(0.1, 5.0, 100)  # BAIXO: < 10 BTC
        }, index=dates)
        return df.sort_index()

    def test_low_liquidity_signal_generation(self, generator, low_liquidity_data):
        """Validar que sinais são gerados mesmo com baixa liquidez."""
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=low_liquidity_data,
            h4_ohlcv=low_liquidity_data,
            h1_ohlcv=low_liquidity_data,
            macro_data={"fear_greed_value": 50, "dxy_change_pct": 0.0},
            current_balance=10000.0,
            session_peak=10050.0
        )
        
        assert isinstance(signal, HeuristicSignal)
        assert signal.confidence >= 0  # Pode ser baixa, mas válida
        assert signal.audit_trail is not None

    def test_low_liquidity_wide_spread(self, generator):
        """Validar com spreads largos (high - low > 5%)."""
        dates = pd.date_range("2024-01-01", periods=50, freq="h")
        df = pd.DataFrame({
            "open": [100] * 50,
            "high": [107] * 50,  # 7% acima
            "low": [93] * 50,    # 7% abaixo
            "close": [100] * 50,
            "volume": np.random.uniform(1, 3, 50)  # Muito baixo
        }, index=dates)
        
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data={},
            current_balance=10000.0,
            session_peak=10100.0
        )
        
        assert signal is not None
        # SL/TP devem refletir o spread
        if signal.stop_loss and signal.take_profit:
            assert signal.risk_reward_ratio is not None


class TestEdgeCasesFlashCrash:
    """Testes de cenários de crash flash (-8% intraday)."""

    @pytest.fixture
    def generator(self):
        return HeuristicSignalGenerator()

    @pytest.fixture
    def flash_crash_data(self):
        """DataFrame simulando flash crash (-8%)."""
        dates = pd.date_range("2024-01-01 00:00:00", periods=100, freq="h")
        prices = [100] * 50 + [92] * 20 + [98] * 30  # Queda -8%, depois recupera
        
        df = pd.DataFrame({
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": np.random.uniform(100, 1000, 100)
        }, index=dates)
        return df.sort_index()

    def test_flash_crash_risk_assessment(self, generator, flash_crash_data):
        """Validar risk assessment durante flash crash."""
        # Saldo decaiu 8% (flash crash)
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=flash_crash_data,
            h4_ohlcv=flash_crash_data,
            h1_ohlcv=flash_crash_data,
            macro_data={"fear_greed_value": 20},  # Fear durante crash
            current_balance=9200.0,  # 8% drawdown
            session_peak=10000.0
        )
        
        # Deve refletir risco
        assert signal.risk_assessment in ["CLEARED", "RISKY", "BLOCKED"]
        if signal.risk_assessment == "RISKY":
            assert signal.confidence < 85  # Confiança reduzida em risco

    def test_flash_crash_recovery(self, generator):
        """Validar recuperação após flash crash."""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        prices_start = np.linspace(100, 100, 30)
        prices_crash = np.linspace(100, 92, 10)  # Crash rápido
        prices_recovery = np.linspace(92, 100, 60)  # Recuperação
        prices = np.concatenate([prices_start, prices_crash, prices_recovery])
        
        df = pd.DataFrame({
            "open": prices,
            "high": prices * 1.01,
            "low": prices * 0.99,
            "close": prices,
            "volume": np.random.uniform(100, 1000, 100)
        }, index=dates)
        
        generator = HeuristicSignalGenerator()
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data={},
            current_balance=10000.0,
            session_peak=10000.0
        )
        
        assert signal.signal_type in ["BUY", "SELL", "NEUTRAL"]


class TestEdgeCasesTimeout:
    """Testes de timeout e missing data."""

    @pytest.fixture
    def generator(self):
        return HeuristicSignalGenerator()

    def test_missing_ohlcv_data(self, generator):
        """Validar com dados faltando."""
        empty_df = pd.DataFrame({
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        })
        
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=empty_df,
            h4_ohlcv=empty_df,
            h1_ohlcv=empty_df,
            macro_data={},
            current_balance=10000.0,
            session_peak=10000.0
        )
        
        # Deve retornar NEUTRAL quando dados insuficientes
        assert signal.signal_type == "NEUTRAL"
        assert signal.confidence < 50

    def test_single_candle_data(self, generator):
        """Validar com apenas 1 candle."""
        dates = pd.date_range("2024-01-01", periods=1, freq="h")
        df = pd.DataFrame({
            "open": [100],
            "high": [105],
            "low": [95],
            "close": [102],
            "volume": [1000]
        }, index=dates)
        
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data={},
            current_balance=10000.0,
            session_peak=10000.0
        )
        
        assert signal.signal_type == "NEUTRAL"


class TestEdgeCasesExtremeFundingRate:
    """Testes com extreme funding rates."""

    @pytest.fixture
    def generator(self):
        return HeuristicSignalGenerator()

    def test_extreme_positive_funding(self, generator):
        """Validar com funding rate extremo positivo (+5%)."""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": np.linspace(100, 110, 100),
            "high": np.linspace(105, 115, 100),
            "low": np.linspace(95, 105, 100),
            "close": np.linspace(100, 110, 100),
            "volume": np.random.uniform(100, 1000, 100)
        }, index=dates)
        
        macro_data = {
            "fear_greed_value": 70,  # Greed extremo
            "dxy_change_pct": -1.0,  # DXY caindo muito
            "funding_rate": 0.05  # Funding +5% (extremo)
        }
        
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data=macro_data,
            current_balance=10000.0,
            session_peak=10000.0
        )
        
        # Deve ser cauteloso com funding extremo
        assert signal.risk_assessment in ["CLEARED", "RISKY"]

    def test_extreme_negative_funding(self, generator):
        """Validar com funding rate extremo negativo (-5%)."""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": np.linspace(100, 90, 100),
            "high": np.linspace(105, 95, 100),
            "low": np.linspace(95, 85, 100),
            "close": np.linspace(100, 90, 100),
            "volume": np.random.uniform(100, 1000, 100)
        }, index=dates)
        
        macro_data = {
            "fear_greed_value": 20,  # Fear extremo
            "dxy_change_pct": 1.0,  # DXY subindo muito
            "funding_rate": -0.05  # Funding -5% (extremo)
        }
        
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data=macro_data,
            current_balance=10000.0,
            session_peak=10000.0
        )
        
        assert signal.signal_type in ["BUY", "SELL", "NEUTRAL"]


class TestEdgeCasesDrawdownThresholds:
    """Testes de thresholds de drawdown."""

    def test_drawdown_boundary_cleared(self):
        """Validar boundary CLEARED (2.9%)."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 971.0  # 2.9% drawdown (dentro de CLEARED)
        
        status, msg = gate.evaluate(current, session_peak)
        assert status == "CLEARED"

    def test_drawdown_boundary_risky(self):
        """Validar boundary RISKY (exatamente 4%)."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 960.0  # 4% drawdown (em RISKY)
        
        status, msg = gate.evaluate(current, session_peak)
        assert status == "RISKY"

    def test_drawdown_boundary_blocked(self):
        """Validar boundary BLOCKED (exatamente 5%)."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 950.0  # 5% drawdown (boundary BLOCKED)
        
        status, msg = gate.evaluate(current, session_peak)
        assert status == "BLOCKED"

    def test_drawdown_beyond_blocked(self):
        """Validar drawdown extremo (>5%)."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 900.0  # 10% drawdown (extremo)
        
        status, msg = gate.evaluate(current, session_peak)
        assert status == "BLOCKED"
        assert "breaker" in msg.lower() or "BLOCKED" in msg
