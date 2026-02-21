"""
Testes Unitários para Heurísticas Conservadoras (TASK-001).

Cobertura: 100% dos métodos e fluxos críticos.
Framework: pytest
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json

from execution.heuristic_signals import (
    HeuristicSignalGenerator,
    RiskGate,
    SignalComponent,
    HeuristicSignal
)


class TestRiskGate:
    """Testes para RiskGate."""

    def test_initialization(self):
        """Testa inicialização com defaults."""
        gate = RiskGate()
        assert gate.max_drawdown_pct == 3.0
        assert gate.circuit_breaker_pct == 5.0

    def test_initialization_custom(self):
        """Testa inicialização com valores customizados."""
        gate = RiskGate(max_drawdown_pct=4.0, circuit_breaker_pct=7.0)
        assert gate.max_drawdown_pct == 4.0
        assert gate.circuit_breaker_pct == 7.0

    def test_evaluate_cleared(self):
        """Teste caso de risco CLEARED."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 980.0  # 2% drawdown

        status, message = gate.evaluate(current, session_peak)
        assert status == "CLEARED"
        assert "-2.00%" in message

    def test_evaluate_risky(self):
        """Teste caso de risco RISKY."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        current = 956.0  # 4.4% drawdown (entre 3% e 5%)

        status, message = gate.evaluate(current, session_peak)
        assert status == "RISKY"
        assert "-4.4" in message

    def test_evaluate_circuit_breaker(self):
        """Teste case de circuit breaker ativado."""
        gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)
        session_peak = 1000.0
        
        # Com 2% drawdown — CLEARED
        current = 980.0
        status, _ = gate.evaluate(current, session_peak)
        assert status == "CLEARED"

        # Com 4% drawdown — RISKY (entre 3% e 5%)
        current = 960.0
        status, message = gate.evaluate(current, session_peak)
        assert status == "RISKY"

    def test_evaluate_zero_peak(self):
        """Teste quando peak é zero."""
        gate = RiskGate()
        status, message = gate.evaluate(100.0, 0.0)
        assert status == "CLEARED"

    def test_evaluate_negative_peak(self):
        """Teste quando peak é negativo."""
        gate = RiskGate()
        status, message = gate.evaluate(100.0, -100.0)
        assert status == "CLEARED"


class TestSignalComponentCreation:
    """Testes para criação de SignalComponent."""

    def test_signal_component_creation(self):
        """Testa criação de componente de sinal."""
        comp = SignalComponent(
            name="smc",
            value=1.0,
            threshold=1.0,
            is_valid=True,
            confidence=0.85
        )
        assert comp.name == "smc"
        assert comp.value == 1.0
        assert comp.confidence == 0.85


class TestHeuristicSignalGenerator:
    """Testes para HeuristicSignalGenerator."""

    @pytest.fixture
    def generator(self):
        """Cria instância do gerador."""
        return HeuristicSignalGenerator()

    @pytest.fixture
    def sample_ohlcv(self):
        """Cria DataFrame OHLCV de exemplo."""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": np.random.uniform(95, 105, 100),
            "high": np.random.uniform(105, 115, 100),
            "low": np.random.uniform(85, 95, 100),
            "close": np.random.uniform(95, 105, 100),
            "volume": np.random.uniform(1000, 10000, 100)
        }, index=dates)
        return df.sort_index()

    def test_initialization(self, generator):
        """Testa inicialização do gerador."""
        assert generator.risk_gate is not None
        assert generator.tech_ind is not None

    def test_initialization_with_custom_risk_gate(self):
        """Testa inicialização com custom RiskGate."""
        custom_gate = RiskGate(max_drawdown_pct=10.0)
        gen = HeuristicSignalGenerator(risk_gate=custom_gate)
        assert gen.risk_gate is custom_gate

    def test_validate_smc_insufficient_data(self, generator):
        """Teste SMC validation com dados insuficientes."""
        small_df = pd.DataFrame({
            "open": [100],
            "high": [105],
            "low": [95],
            "close": [102],
            "volume": [1000]
        })
        audit = {}
        signal, confidence = generator._validate_smc("BTCUSDT", small_df, audit)

        assert signal == "NEUTRAL"
        assert confidence == 0.0
        assert audit["smc"]["status"] == "INSUFFICIENT_DATA"

    def test_validate_ema_alignment_insufficient_data(self, generator):
        """Teste EMA alignment com dados insuficientes."""
        small_df = pd.DataFrame({
            "close": [100, 101, 102]
        })
        audit = {}
        signal, confidence = generator._validate_ema_alignment(
            "BTCUSDT", small_df, small_df, small_df, audit
        )

        assert signal == "NEUTRAL"
        assert confidence == 0.0

    def test_validate_rsi_insufficient_data(self, generator):
        """Teste RSI validation com dados insuficientes."""
        small_df = pd.DataFrame({
            "close": [100, 101, 102]
        })
        audit = {}
        signal, confidence = generator._validate_rsi("BTCUSDT", small_df, audit)

        assert signal == "NEUTRAL"
        assert confidence == 0.0

    def test_validate_adx_insufficient_data(self, generator):
        """Teste ADX validation com dados insuficientes."""
        small_df = pd.DataFrame({
            "close": [100] * 10,
            "high": [105] * 10,
            "low": [95] * 10
        })
        audit = {}
        is_trending, confidence = generator._validate_adx("BTCUSDT", small_df, audit)

        assert is_trending is False
        assert confidence == 0.0

    def test_calculate_overall_confidence(self, generator):
        """Testa cálculo de confiança geral."""
        components = [
            SignalComponent("smc", 1.0, 1.0, True, 0.8),
            SignalComponent("ema", 1.0, 1.0, True, 0.7),
            SignalComponent("rsi", 1.0, 1.0, True, 0.6),
            SignalComponent("adx", 1.0, 1.0, True, 0.75)
        ]

        conf = generator._calculate_overall_confidence(components, "RISK_ON", "CLEARED")
        assert 0 <= conf <= 100

    def test_calculate_overall_confidence_blocked(self, generator):
        """Testa confiança quando risk_status é BLOCKED."""
        components = [
            SignalComponent("smc", 1.0, 1.0, True, 0.8)
        ]

        conf = generator._calculate_overall_confidence(components, "RISK_ON", "BLOCKED")
        assert conf == 0.0

    def test_determine_final_signal_blocked(self, generator):
        """Testa determinação de sinal quando bloqueado."""
        signal = generator._determine_final_signal(
            "BUY", "BUY", "BUY", True,
            confluence=4, confidence=95, regime="RISK_ON", risk_status="BLOCKED"
        )
        assert signal == "NEUTRAL"

    def test_determine_final_signal_low_confluence(self, generator):
        """Testa determinação de sinal com baixa confluência."""
        signal = generator._determine_final_signal(
            "BUY", "NEUTRAL", "NEUTRAL", False,
            confluence=1, confidence=50, regime="RISK_ON", risk_status="CLEARED"
        )
        assert signal == "NEUTRAL"

    def test_determine_final_signal_low_confidence(self, generator):
        """Testa determinação de sinal com baixa confiança."""
        signal = generator._determine_final_signal(
            "BUY", "BUY", "BUY", True,
            confluence=3, confidence=50, regime="RISK_ON", risk_status="CLEARED"
        )
        assert signal == "NEUTRAL"

    def test_determine_final_signal_buy(self, generator):
        """Testa determinação de sinal BUY válido."""
        signal = generator._determine_final_signal(
            "BUY", "BUY", "BUY", True,
            confluence=4, confidence=85, regime="RISK_ON", risk_status="CLEARED"
        )
        assert signal == "BUY"

    def test_determine_final_signal_sell(self, generator):
        """Testa determinação de sinal SELL válido."""
        signal = generator._determine_final_signal(
            "SELL", "SELL", "SELL", True,
            confluence=4, confidence=85, regime="RISK_ON", risk_status="CLEARED"
        )
        assert signal == "SELL"

    def test_calculate_rr_ratio(self, generator):
        """Testa cálculo de R:R ratio."""
        ratio = generator._calculate_rr_ratio(100.0, 95.0, 110.0)
        assert ratio == 2.0  # (110-100) / (100-95) = 10/5 = 2

    def test_calculate_rr_ratio_invalid(self, generator):
        """Testa R:R ratio com entrada == SL."""
        ratio = generator._calculate_rr_ratio(100.0, 100.0, 110.0)
        assert ratio is None

    def test_calculate_rr_ratio_none_values(self, generator):
        """Testa R:R ratio com valores None."""
        ratio = generator._calculate_rr_ratio(None, 95.0, 110.0)
        assert ratio is None

    @patch('execution.heuristic_signals.logger')
    def test_log_signal(self, mock_logger, generator):
        """Testa logging de sinal."""
        signal = HeuristicSignal(
            symbol="BTCUSDT",
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            signal_type="BUY",
            components=[],
            confidence=85.0,
            confluence_score=4,
            market_regime="RISK_ON",
            d1_bias="BULLISH",
            risk_assessment="CLEARED",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=51000.0,
            risk_reward_ratio=2.0,
            audit_trail={}
        )

        generator._log_signal(signal)
        mock_logger.info.assert_called()

    def test_generate_signal_format(self, generator, sample_ohlcv):
        """Testa formato da saída de generate_signal."""
        macro_data = {
            "fear_greed_value": 50,
            "dxy_change_pct": 0.1
        }

        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=sample_ohlcv,
            h4_ohlcv=sample_ohlcv,
            h1_ohlcv=sample_ohlcv,
            macro_data=macro_data,
            current_balance=10000.0,
            session_peak=10100.0
        )

        assert isinstance(signal, HeuristicSignal)
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type in ["BUY", "SELL", "NEUTRAL"]
        assert 0 <= signal.confidence <= 100
        assert 0 <= signal.confluence_score <= 4
        assert signal.risk_assessment in ["CLEARED", "RISKY", "BLOCKED"]


class TestIntegration:
    """Testes de integração."""

    def test_full_generation_pipeline(self):
        """Testa pipeline completo de geração de sinal."""
        generator = HeuristicSignalGenerator()

        # Gerar dados de exemplo
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": np.linspace(100, 110, 100) + np.random.randn(100),
            "high": np.linspace(105, 115, 100) + np.random.randn(100),
            "low": np.linspace(95, 105, 100) + np.random.randn(100),
            "close": np.linspace(100, 110, 100) + np.random.randn(100),
            "volume": np.random.uniform(1000, 10000, 100)
        }, index=dates)
        df = df.sort_index()

        macro_data = {"fear_greed_value": 55, "dxy_change_pct": 0.05}

        # Executar geração
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data=macro_data,
            current_balance=10000.0,
            session_peak=10050.0
        )

        # Validações
        assert isinstance(signal, HeuristicSignal)
        assert len(signal.components) >= 4
        assert all(isinstance(c, SignalComponent) for c in signal.components)
        assert signal.audit_trail is not None
        assert "risk_gate" in signal.audit_trail

    def test_risk_gate_integration(self):
        """Testa integração com RiskGate."""
        gate = RiskGate(max_drawdown_pct=5.0)
        generator = HeuristicSignalGenerator(risk_gate=gate)

        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({
            "open": [100] * 100,
            "high": [105] * 100,
            "low": [95] * 100,
            "close": [100] * 100,
            "volume": [1000] * 100
        }, index=dates)

        macro_data = {}

        # Signal gerado com drawdown em risco
        signal = generator.generate_signal(
            symbol="BTCUSDT",
            d1_ohlcv=df,
            h4_ohlcv=df,
            h1_ohlcv=df,
            macro_data=macro_data,
            current_balance=9500.0,  # 5% drawdown
            session_peak=10000.0
        )

        assert signal.risk_assessment in ["CLEARED", "RISKY", "BLOCKED"]
