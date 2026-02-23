# 🎯 S2-1/S2-2 Smart Money Concepts Implementation — Order Blocks & Break of Structure

**Feature Set:** S2-1 (Order Blocks) + S2-2 (Break of Structure)  
**Owner:** Arch (#6) — Software Architecture  
**Timeline:** 23-24 FEV 2026  
**Estimate:** 6-8h total (S2-1: 3-4h, S2-2: 3-4h)  
**Status:** 🚀 READY TO START (unblocked post-Gate 3)  

---

## 🎓 SMC Concepts — Quick Primer

### Order Blocks (OB)
**What:** Price levels where institucional "Smart Money" entered antes de move significativo.

**Signal:** When price returns to OB level after breaking it, there's rejection (potential reversal).

**Detection Règle:**
1. Identify swing high (local max) + swing low (local min)
2. Look for candle pattern: engulfing ou piercing below swing low
3. Mark level as Order Block
4. If price returns to OB after break, trigger BUY signal (for long setup)

**Code Logic:**
```python
def find_order_blocks(ohlcv_data, lookback=20, threshold=0.02):
    """
    Detecta Order Blocks em OHLCV data.
    
    Returns: List of OB levels com timestamp
    """
    obs = []
    
    for i in range(lookback, len(ohlcv_data)):
        window = ohlcv_data[i-lookback:i]
        swing_low = min(c['low'] for c in window)
        swing_high = max(c['high'] for c in window)
        
        current = ohlcv_data[i]
        
        # Check se price quebrou swing low com close < low from prev candle
        if (current['close'] < swing_low * (1 - threshold) and 
            current['low'] < window[-1]['low']):
            
            # Mark OB at swing_low level
            obs.append({
                'level': swing_low,
                'timestamp': i,
                'type': 'bullish',  # potencial reversal up
                'strength': current['volume'] / np.median([c['volume'] for c in window])
            })
    
    return obs
```

---

### Break of Structure (BoS)
**What:** When price breaks AND CLOSES outside do swing level (structurally).

**Signal:** BoS sinaliza cambio de regime — antes era range, agora trend.

**Detection Rule:**
1. Identify swing high + swing low
2. Check if close crosses level (not just wick)
3. Confirm com próximo candle (não reversal imediato)
4. Trigger trend signal (BUY if break above, SELL if break below)

**Code Logic:**
```python
def find_break_of_structure(ohlcv_data, lookback=20, confirm_candles=2):
    """
    Detecta Break of Structure events.
    
    Returns: List of BoS with direction
    """
    bos_events = []
    
    for i in range(lookback + confirm_candles, len(ohlcv_data)):
        window = ohlcv_data[i-lookback:i]
        swing_low = min(c['low'] for c in window)
        swing_high = max(c['high'] for c in window)
        
        # Check swing break
        for j in range(i, min(i + confirm_candles, len(ohlcv_data))):
            candle = ohlcv_data[j]
            
            if candle['close'] > swing_high:
                # Bullish BoS
                bos_events.append({
                    'level': swing_high,
                    'timestamp': j,
                    'direction': 'bullish',
                    'confirmed': j > i + confirm_candles,
                })
                break
            elif candle['close'] < swing_low:
                # Bearish BoS
                bos_events.append({
                    'level': swing_low,
                    'timestamp': j,
                    'direction': 'bearish',
                    'confirmed': j > i + confirm_candles,
                })
                break
    
    return bos_events
```

---

## 📋 Implementation Roadmap

### Phase 1: S2-1 Order Blocks (6h)

**Owner:** Arch (#6) + Data (#11)

#### T21.1 — Create Order Block Detector

**File:** `strategy/order_blocks.py`

```python
import numpy as np
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class OrderBlock:
    level: float
    timestamp: int
    type: str  # 'bullish' or 'bearish'
    strength: float  # 0.0-1.0 (volume-based)
    confirmed: bool  # been respected at least once

class OrderBlockDetector:
    def __init__(self, lookback=20, volume_threshold=0.5):
        self.lookback = lookback
        self.volume_threshold = volume_threshold
        self.active_blocks = []
    
    def detect(self, ohlcv_data: List[Dict]) -> List[OrderBlock]:
        """Detecta Order Blocks no histórico OHLCV."""
        blocks = []
        
        for i in range(self.lookback, len(ohlcv_data)):
            window = ohlcv_data[i - self.lookback:i]
            swing_low = min(c['low'] for c in window)
            swing_high = max(c['high'] for c in window)
            
            current = ohlcv_data[i]
            prev = ohlcv_data[i - 1]
            
            # Detectar bullish OB (penetração abaixo swing low)
            if current['close'] < swing_low and prev['low'] > swing_low:
                volume_ratio = current['volume'] / np.median([c['volume'] for c in window])
                
                ob = OrderBlock(
                    level=swing_low,
                    timestamp=i,
                    type='bullish',
                    strength=min(volume_ratio, 1.0),
                    confirmed=False
                )
                blocks.append(ob)
                self.active_blocks.append(ob)
        
        # Check para confirmação (price retornou ao OB level)
        for ob in self.active_blocks:
            if current['high'] >= ob.level:
                ob.confirmed = True
        
        return blocks
    
    def get_nearest_block(self, current_price: float) -> OrderBlock:
        """Retorna OB mais próximo do preço atual."""
        if not self.active_blocks:
            return None
        
        return min(
            self.active_blocks,
            key=lambda ob: abs(current_price - ob.level)
        )
```

**Checklist:**
- [ ] OrderBlock dataclass defined
- [ ] OrderBlockDetector class implemented
- [ ] detect() method finds swing levels
- [ ] confirmed flag updated on price return
- [ ] get_nearest_block() helper implemented

**Time:** 2h

---

#### T21.2 — Create Tests for Order Blocks

**File:** `tests/test_order_blocks.py`

```python
import pytest
from strategy.order_blocks import OrderBlockDetector, OrderBlock

def test_detect_bullish_order_block():
    """Testa detecção de OB bullish."""
    ohlcv = [
        {'open': 100, 'high': 105, 'low': 98, 'close': 102, 'volume': 100},
        # ... 20 more candles
        {'open': 101, 'high': 103, 'low': 97, 'close': 96, 'volume': 150},  # penetra baixo
    ]
    
    detector = OrderBlockDetector(lookback=20)
    blocks = detector.detect(ohlcv)
    
    assert len(blocks) > 0
    assert blocks[0].type == 'bullish'
    assert blocks[0].level == min(c['low'] for c in ohlcv[:-1])

def test_order_block_confirmation():
    """Testa confirmação OB quando price retorna."""
    ohlcv = [...] # mock data
    
    detector = OrderBlockDetector()
    blocks = detector.detect(ohlcv)
    
    assert blocks[0].confirmed == True

def test_nearest_block():
    """Testa seleção do OB mais próximo."""
    # ...
    pass
```

**Checklist:**
- [ ] 3+ test functions (bullish, confirmation, nearest)
- [ ] All tests PASS
- [ ] Coverage > 85%

**Time:** 1h

---

#### T21.3 — Integrate with Execution Engine

**File:** `execution/smc_signals.py`

```python
from strategy.order_blocks import OrderBlockDetector
from risk.risk_gate import RiskGate
from execution.order_manager import OrderManager

class SMCSignalGenerator:
    """Gera sinais de entrada baseado em Order Blocks."""
    
    def __init__(self):
        self.ob_detector = OrderBlockDetector(lookback=20)
        self.risk_gate = RiskGate(max_drawdown=-0.03)
        self.order_manager = OrderManager()
    
    def generate_signal(self, ohlcv_data, current_price):
        """
        Gera sinal de entrada se:
        1. OB detectado e confirmado
        2. Preço voltou ao nível do OB
        3. Risk Gate OK (não em drawdown)
        """
        
        # Detecta OB
        blocks = self.ob_detector.detect(ohlcv_data)
        
        if not blocks:
            return None
        
        # Nearest OB
        nearest_ob = self.ob_detector.get_nearest_block(current_price)
        
        if not nearest_ob.confirmed:
            return None
        
        # Risk check
        if self.risk_gate.is_breached():
            return None
        
        # Generate BUY signal
        return {
            'action': 'BUY',
            'entry': current_price,
            'stop_loss': nearest_ob.level - 0.02 * nearest_ob.level,  # 2% below OB
            'take_profit': current_price + 0.05 * current_price,  # 5% profit target
            'ordblock_level': nearest_ob.level,
        }
```

**Checklist:**
- [ ] SMCSignalGenerator class
- [ ] RiskGate integration
- [ ] generate_signal() método retorna BUY/SELL/NONE
- [ ] Integration tested em execution flow

**Time:** 1h

---

### Phase 2: S2-2 Break of Structure (6h)

**Owner:** Arch (#6) + Quality (#12)

#### T22.1 — Create BoS Detector

**File:** `strategy/break_of_structure.py`

```python
@dataclass
class BreakOfStructure:
    level: float
    timestamp: int
    direction: str  # 'bullish' or 'bearish'
    confirmed: bool
    volume_ratio: float

class BreakOfStructureDetector:
    def __init__(self, lookback=20, confirm_candles=2):
        self.lookback = lookback
        self.confirm_candles = confirm_candles
    
    def detect(self, ohlcv_data: List[Dict]) -> List[BreakOfStructure]:
        """Detecta BoS events."""
        bos_list = []
        
        for i in range(self.lookback, len(ohlcv_data)):
            window = ohlcv_data[i - self.lookback:i]
            swing_high = max(c['high'] for c in window)
            swing_low = min(c['low'] for c in window)
            
            current = ohlcv_data[i]
            
            # Check bullish BoS (close above swing high)
            if current['close'] > swing_high and current['high'] > swing_high:
                # Confirma com próximas 2 candles
                confirmed = True
                for j in range(1, self.confirm_candles):
                    if i + j < len(ohlcv_data):
                        next_candle = ohlcv_data[i + j]
                        if next_candle['close'] < swing_high:
                            confirmed = False
                            break
                
                vol_ratio = current['volume'] / np.median([c['volume'] for c in window])
                
                bos = BreakOfStructure(
                    level=swing_high,
                    timestamp=i,
                    direction='bullish',
                    confirmed=confirmed,
                    volume_ratio=min(vol_ratio, 1.0)
                )
                bos_list.append(bos)
            
            # Similar untuk bearish BoS
            # ...
        
        return bos_list
```

**Checklist:**
- [ ] BreakOfStructure dataclass
- [ ] BreakOfStructureDetector class
- [ ] detect() for both bullish + bearish
- [ ] confirmation logic (2-candle rule)

**Time:** 2h

---

#### T22.2 — Tests for BoS

**File:** `tests/test_break_of_structure.py`

**10+ test cases:**
- bullish BoS detection
- bearish BoS detection
- confirmation logic
- volume validation
- edge cases (wicks vs closes)

**Checklist:**
- [ ] 10+ tests
- [ ] All PASS
- [ ] Coverage > 85%

**Time:** 1.5h

---

#### T22.3 — Integrate BoS with SMC Signal Generator

**File:** `execution/smc_signals.py` (extend from S2-1)

```python
class SMCSignalGenerator:
    def __init__(self):
        self.ob_detector = OrderBlockDetector()
        self.bos_detector = BreakOfStructureDetector()
        self.risk_gate = RiskGate()
    
    def generate_signal(self, ohlcv_data, current_price):
        """
        Gera sinal combinando Order Blocks + BoS:
        
        Entry quando:
        1. BoS confirmado (mudança de regime)
        2. + Confirmação via Order Block
        3. + Risk Gate OK
        """
        
        # Detecta BoS
        bos_events = self.bos_detector.detect(ohlcv_data)
        if not bos_events or not bos_events[-1].confirmed:
            return None
        
        # Detecta OB
        blocks = self.ob_detector.detect(ohlcv_data)
        if not blocks:
            return None
        
        latest_bos = bos_events[-1]
        latest_ob = self.ob_detector.get_nearest_block(current_price)
        
        # Risk check
        if self.risk_gate.is_breached():
            return None
        
        # Generate signal (BoS direction + OB confirmation)
        if latest_bos.direction == 'bullish':
            return {
                'action': 'BUY',
                'entry': current_price,
                'stop_loss': latest_bos.level - 0.02 * latest_bos.level,
                'take_profit': current_price + 0.08 * current_price,  # BoS target: 8%
                'signal_type': 'BoS + OB',
                'confidence': min(latest_bos.volume_ratio, latest_ob.strength),
            }
        # Similar para bearish
        # ...
```

**Checklist:**
- [ ] SMCSignalGenerator updated
- [ ] Integrates OB + BoS logic
- [ ] Returns BUY/SELL/NONE
- [ ] Execution engine accepts signals

**Time:** 1.5h

---

### Phase 3: Testing & Validation (2h)

#### T23.1 — End-to-End SMC Test

**File:** `tests/test_smc_e2e.py`

```python
def test_smc_full_workflow():
    """
    Testa workflow completo:
    1. Load OHLCV data
    2. Detecta OB + BoS
    3. Gera signals
    4. Execute trades  
    5. Valida resultados
    """
    
    # Load test data (6 months × 60 symbols subset)
    ohlcv = load_test_data('data/test_6month_btc.json')
    
    # Initialize SMC
    smc = SMCSignalGenerator()
    
    # Generate signals
    signals = []
    for i, candle in enumerate(ohlcv):
        signal = smc.generate_signal(ohlcv[:i+1], candle['close'])
        if signal:
            signals.append(signal)
    
    # Validate signal quality
    assert len(signals) > 10  # Should find signals
    assert all(s['action'] in ['BUY', 'SELL'] for s in signals)
    
    # Execute trades
    risk_gate = RiskGate()
    executed_trades = []
    
    for signal in signals:
        if risk_gate.check_entry(signal):
            executed_trades.append(signal)
    
    # Calculate metrics on executed trades
    calc = MetricsCalculator(executed_trades, initial_capital=10000)
    
    # Validar que estratégia SMC produz Sharpe > 0.5
    sharpe = calc.calculate_sharpe_ratio()
    assert sharpe > 0.5, f"SMC strategy Sharpe {sharpe} < 0.5"
    
    print(f"✅ SMC E2E Test PASS")
    print(f"   Signals: {len(signals)}, Executed: {len(executed_trades)}")
    print(f"   Sharpe: {sharpe:.2f}")
```

**Checklist:**
- [ ] E2E test loads real data
- [ ] Generates 10+ signals
- [ ] Executes trades successfully
- [ ] Calculates metrics

**Time:** 1h

---

## 📊 Deliverables & Files

| Component | File | Owner | Status |
|-----------|------|-------|--------|
| **S2-1** | strategy/order_blocks.py | Arch #6 | 📋 |
| **S2-1** | tests/test_order_blocks.py | Quality #12 | 📋 |
| **S2-1/S2-2** | execution/smc_signals.py | Arch #6 | 📋 |
| **S2-2** | strategy/break_of_structure.py | Arch #6 | 📋 |
| **S2-2** | tests/test_break_of_structure.py | Quality #12 | 📋 |
| **Integration** | tests/test_smc_e2e.py | Quality #12 | 📋 |

---

## ✅ Success Criteria

All of below must PASS:
1. ✅ Order Blocks detected correctly (test_detect_bullish_order_block)
2. ✅ BoS events detected correctly (test_detect_bullish_bos)
3. ✅ SMC signals generated (test_smc_full_workflow)
4. ✅ Trades executed successfully
5. ✅ Strategy Sharpe > 0.5 (backtesting)
6. ✅ All tests PASS (30+ tests total)
7. ✅ Coverage > 85% (strategy & execution modules)

---

**Created:** 23 FEV 01:45 UTC  
**Owner:** Arch (#6) — Architecture Lead  
**Timeline:** 23-24 FEV PARALLEL EXECUTION  
**Ready to start:** ✅ YES (post-Gate 3 unblocked)
