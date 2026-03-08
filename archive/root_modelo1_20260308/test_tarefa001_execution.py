#!/usr/bin/env python3
"""
Script de teste para TAREFA-001 - Validação execução.

Testa:
  1. Motor core (HeuristicSignalGenerator)
  2. Indicadores (SMC, Technical, MultiTimeframe)
  3. Risk gates
  4. Geração sinais
"""

import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from execution.heuristic_signals import (
        HeuristicSignalGenerator,
        RiskGate,
        SignalComponent
    )
    from indicators.technical import TechnicalIndicators
    from indicators.multi_timeframe import MultiTimeframeAnalysis
    logger.info("✅ Imports TAREFA-001 bem-sucedidos")
except ImportError as e:
    logger.error(f"❌ Erro importação: {e}")
    sys.exit(1)


def create_sample_ohlcv(periods: int = 100) -> pd.DataFrame:
    """Cria DataFrame OHLCV de exemplo para testes."""
    np.random.seed(42)
    dates = pd.date_range(
        end=datetime.utcnow(),
        periods=periods,
        freq='h'
    )

    close = 100.0 + np.cumsum(
        np.random.randn(periods) * 0.5
    )

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close * 0.99,
        'high': close * 1.02,
        'low': close * 0.98,
        'close': close,
        'volume': np.random.uniform(1000, 5000, periods)
    })

    return df


def test_risk_gate():
    """Testa RiskGate."""
    logger.info("🧪 Testando RiskGate...")

    gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)

    # Teste 1: Sem drawdown (CLEARED)
    status, msg = gate.evaluate(10000, 10000)
    assert status == "CLEARED", f"Expected CLEARED, got {status}"
    logger.info(f"✅ Teste 1 PASS: {status}")

    # Teste 2: Drawdown 4% (RISKY)
    status, msg = gate.evaluate(9600, 10000)
    assert status == "RISKY", f"Expected RISKY, got {status}"
    logger.info(f"✅ Teste 2 PASS: {status}")

    # Teste 3: Drawdown 6% (BLOCKED)
    status, msg = gate.evaluate(9400, 10000)
    assert status == "BLOCKED", f"Expected BLOCKED, got {status}"
    logger.info(f"✅ Teste 3 PASS: {status}")

    logger.info("✅ RiskGate tests OK\n")


def test_technical_indicators():
    """Testa indicadores técnicos."""
    logger.info("🧪 Testando indicadores técnicos...")

    df = create_sample_ohlcv(100)
    ti = TechnicalIndicators()

    # Teste EMA
    ema = ti.calculate_ema(df['close'], 9)
    assert len(ema) == len(df), "EMA length mismatch"
    assert not ema.isna().all(), "EMA all NaN"
    logger.info(f"✅ EMA test OK (último valor: {ema.iloc[-1]:.2f})")

    # Teste RSI
    rsi = ti.calculate_rsi(df['close'], 14)
    assert len(rsi) == len(df), "RSI length mismatch"
    assert not rsi.isna().all(), "RSI all NaN"
    assert (rsi[rsi.notna()] >= 0).all() and (rsi[rsi.notna()] <= 100).all(), \
        "RSI fora do range 0-100"
    logger.info(f"✅ RSI test OK (último valor: {rsi.iloc[-1]:.2f})")

    # Teste ADX
    adx_df = ti.calculate_adx(df, 14)
    assert 'adx_14' in adx_df.columns, "ADX column missing"
    assert len(adx_df) == len(df), "ADX length mismatch"
    logger.info(f"✅ ADX test OK (último valor: {adx_df['adx_14'].iloc[-1]:.2f})")

    # Teste ATR
    atr = ti.calculate_atr(df, 14)
    assert len(atr) == len(df), "ATR length mismatch"
    assert not atr.isna().all(), "ATR all NaN"
    logger.info(f"✅ ATR test OK (último valor: {atr.iloc[-1]:.2f})")

    logger.info("✅ Technical indicators tests OK\n")


def test_signal_generator():
    """Testa gerador de sinais heurísticos."""
    logger.info("🧪 Testando HeuristicSignalGenerator...")

    # Criar dados de teste
    d1_df = create_sample_ohlcv(100)
    h4_df = create_sample_ohlcv(100)
    h1_df = create_sample_ohlcv(100)

    # Criar gerador
    generator = HeuristicSignalGenerator()

    # Gerar sinal
    try:
        signal = generator.generate_signal(
            symbol="ETHUSDT",
            d1_ohlcv=d1_df,
            h4_ohlcv=h4_df,
            h1_ohlcv=h1_df,
            macro_data={"trend": "bullish"},
            current_balance=10000,
            session_peak=10100
        )

        # Validações
        assert signal.symbol == "ETHUSDT", "Symbol mismatch"
        assert signal.signal_type in ["BUY", "SELL", "NEUTRAL"], \
            f"Invalid signal type: {signal.signal_type}"
        assert 0 <= signal.confidence <= 100, \
            f"Confidence fora do range: {signal.confidence}"
        assert signal.risk_assessment in ["CLEARED", "RISKY", "BLOCKED"], \
            f"Invalid risk assessment: {signal.risk_assessment}"
        assert len(signal.components) > 0, "No components"

        logger.info(f"✅ Signal generated:")
        logger.info(f"   Symbol: {signal.symbol}")
        logger.info(f"   Type: {signal.signal_type}")
        logger.info(f"   Confidence: {signal.confidence:.1f}%")
        logger.info(f"   Confluence: {signal.confluence_score}")
        logger.info(f"   Risk: {signal.risk_assessment}")
        logger.info(f"   Components: {len(signal.components)}")

    except Exception as e:
        logger.error(f"❌ Signal generation error: {e}")
        import traceback
        traceback.print_exc()
        raise

    logger.info("✅ Signal generator tests OK\n")


def test_signal_component():
    """Testa dataclass SignalComponent."""
    logger.info("🧪 Testando SignalComponent...")

    comp = SignalComponent(
        name="smc",
        value=0.8,
        threshold=0.7,
        is_valid=True,
        confidence=0.85
    )

    assert comp.name == "smc", "Name mismatch"
    assert comp.is_valid is True, "is_valid mismatch"
    assert 0 <= comp.confidence <= 1, "Confidence out of range"

    logger.info(f"✅ SignalComponent test OK")
    logger.info(f"   Name: {comp.name}")
    logger.info(f"   Value: {comp.value}")
    logger.info(f"   Confidence: {comp.confidence}\n")


def main():
    """Executa todos os testes."""
    logger.info("=" * 60)
    logger.info("TAREFA-001: TESTE DE EXECUÇÃO")
    logger.info("=" * 60 + "\n")

    try:
        test_risk_gate()
        test_signal_component()
        test_technical_indicators()
        test_signal_generator()

        logger.info("=" * 60)
        logger.info("✅ TODOS OS TESTES PASSARAM")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"\n❌ TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
