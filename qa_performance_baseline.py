#!/usr/bin/env python
"""Performance baseline validation."""

import time
import pandas as pd
import numpy as np
from execution.heuristic_signals import HeuristicSignalGenerator

gen = HeuristicSignalGenerator()

# Dados típicos
dates = pd.date_range('2024-01-01', periods=100, freq='h')
df = pd.DataFrame({
    'open': np.linspace(100, 110, 100),
    'high': np.linspace(105, 115, 100),
    'low': np.linspace(95, 105, 100),
    'close': np.linspace(100, 110, 100),
    'volume': np.random.uniform(100, 1000, 100)
}, index=dates)

# Medir tempo de geração de sinal (5 runs)
times = []
for i in range(5):
    start = time.time()
    signal = gen.generate_signal(
        symbol='BTCUSDT',
        d1_ohlcv=df,
        h4_ohlcv=df,
        h1_ohlcv=df,
        macro_data={},
        current_balance=10000.0,
        session_peak=10100.0
    )
    elapsed_ms = (time.time() - start) * 1000
    times.append(elapsed_ms)

avg_ms = np.mean(times)
max_ms = np.max(times)
min_ms = np.min(times)

print(f"Performance Baseline Results:")
print(f"  Average: {avg_ms:.2f}ms")
print(f"  Max:     {max_ms:.2f}ms")
print(f"  Min:     {min_ms:.2f}ms")
print(f"  Threshold: <100ms")
print(f"  Status: {'PASS' if avg_ms < 100 else 'FAIL'}")
print(f"\nSignal Details (last run):")
print(f"  Type: {signal.signal_type}")
print(f"  Confidence: {signal.confidence:.1f}%")
print(f"  Risk: {signal.risk_assessment}")
