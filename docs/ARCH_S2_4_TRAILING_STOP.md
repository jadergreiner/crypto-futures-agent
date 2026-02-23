# 🏗️ Arquitetura — Trailing Stop Loss (S2-4)

**Owner:** Arch (#6)  
**Relação:** SPEC_S2_4_TRAILING_STOP_LOSS.md  
**Última Atualização:** 2026-02-22 23:55 UTC

---

## 📐 Componentes & Diagrama

```
┌──────────────────────────────────────────────────────────┐
│                    EXECUTION LOOP (100ms)                 │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. Fetch Current Price (Binance WebSocket)          │  │
│  └────────────────┬────────────────────────────────────┘  │
│                   ↓                                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 2. Calculate Real-Time PnL                          │  │
│  │    profit_pct = (price - entry) / entry             │  │
│  └────────────────┬────────────────────────────────────┘  │
│                   ↓                                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 3. RiskGate Check (Integrated)                      │  │
│  │    ├─ TSL Active? → Update trailing_high/stop      │  │
│  │    ├─ TSL Filter? → Check price vs trailing_stop   │  │
│  │    └─ SL Filter? → Check price vs entry × 0.97     │  │
│  └────────────────┬────────────────────────────────────┘  │
│                   ↓                                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 4. Execute (if triggered)                           │  │
│  │    ├─ Market Close Order                            │  │
│  │    ├─ Update DB (PnL, close_reason)                 │  │
│  │    └─ Log & Telemetry                               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## 🔌 Integração em Risk Gate

### Hierarquia de Proteção

```python
class RiskGate:
    def check_position(self, position: Position) -> ProtectionSignal:
        """
        Executa checks em ordem de PRECEDÊNCIA.
        Primeira proteção ativa que trigger = executa.
        """
        
        # 1️⃣  HARDCODED CIRCUIT BREAKER (inviolável)
        if self._check_liquidation_risk(position):
            return ProtectionSignal.LIQUIDATION_BRAKE
        
        # 2️⃣  TRAILING STOP (ativo se lucro >= threshold)
        if position.trailing_active and self._check_trailing_stop(position):
            return ProtectionSignal.TRAILING_STOP_HIT
        
        # 3️⃣  STATIC STOP LOSS (por padrão sempre ativo)
        if self._check_static_stop_loss(position):
            return ProtectionSignal.STATIC_SL_HIT
        
        # 4️⃣  TAKE PROFIT (ativo)
        if self._check_take_profit(position):
            return ProtectionSignal.TAKE_PROFIT_HIT
        
        # 5️⃣  TIMEOUT (2 horas)
        if self._check_timeout(position):
            return ProtectionSignal.TIMEOUT_HIT
        
        # Nenhuma proteção ativada
        return ProtectionSignal.CONTINUE
    
    def _check_trailing_stop(self, position: Position) -> bool:
        """TSL activation logic."""
        if not position.trailing_active:
            return False  # TSL não está ativo
        
        # Verificar se preço caiu abaixo do trailing stop
        return position.current_price <= position.trailing_stop_price
```

---

## 📦 Módulo TSL Core

### Arquivo: `risk/trailing_stop.py`

```python
# Estrutura simplificada
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TrailingStopConfig:
    """Parâmetros TSL (carregados de settings.py)."""
    activation_threshold: float = 1.5          # R units
    stop_distance_pct: float = 0.10            # 10%
    update_interval_ms: int = 100
    enabled: bool = True

class TrailingStopManager:
    """Gerencia lógica de trailing stop."""
    
    def __init__(self, config: TrailingStopConfig):
        self.config = config
    
    def evaluate(self, position: Position) -> Position:
        """Avalia e atualiza estado TSL da posição."""
        
        if not self.config.enabled:
            return position
        
        # Calcular lucro atual
        profit_pct = (position.current_price - position.entry_price) / position.entry_price
        profit_r = profit_pct / (position.risk_r or 0.03)  # Normalizar para R
        
        # 1. Verificar ativação
        if not position.trailing_active and profit_r >= self.config.activation_threshold:
            position.trailing_active = True
            position.trailing_high = position.current_price
            position.trailing_activated_at = datetime.now()
        
        # 2. Se ativo, atualizar high e calcular stop
        if position.trailing_active:
            # Manter registro do maior preço
            if position.current_price > (position.trailing_high or 0):
                position.trailing_high = position.current_price
            
            # Calcular nível de stop (mantém distância %)
            position.trailing_stop_price = position.trailing_high * (1 - self.config.stop_distance_pct)
        
        # 3. Se lucro volta negativo, desativar TSL
        if position.trailing_active and profit_pct < 0:
            position.trailing_active = False
        
        return position
    
    def has_triggered(self, position: Position) -> bool:
        """Verifica se TSL foi acionada."""
        if not position.trailing_active:
            return False
        
        return position.current_price <= position.trailing_stop_price
```

---

## 🔄 Fluxo de Integração

### 1. Na Inicialização da Posição

```python
# execution/position_manager.py
def open_position(self, order_params: OrderParams) -> Position:
    position = Position(
        entry_price=order_params.entry_price,
        quantity=order_params.quantity,
        # ... outros campos
        trailing_active=False,
        trailing_high=0.0,
        trailing_stop_price=0.0,
        trailing_activation_threshold=settings.TRAILING_ACTIVATION_THRESHOLD,
    )
    
    # Salvar no DB
    self.db.add_position(position)
    
    return position
```

### 2. No Loop de Monitoramento

```python
# execution/monitor_positions.py
def scan_all_positions(self):
    """Chamado a cada 100ms."""
    
    for position in self.db.get_open_positions():
        # 1. Atualizar preço atual (WebSocket)
        position.current_price = self.data_client.get_current_price(position.symbol)
        
        # 2. Avaliar TSL
        position = self.tsl_manager.evaluate(position)
        
        # 3. Passar para RiskGate
        signal = self.risk_gate.check_position(position)
        
        # 4. Executar se needed
        if signal != ProtectionSignal.CONTINUE:
            self._execute_close(position, reason=signal)
```

### 3. no Database

```sql
-- Schema atualización
ALTER TABLE trade_log ADD COLUMN (
    trailing_activation_threshold DECIMAL(10, 2),
    trailing_active BOOLEAN DEFAULT FALSE,
    trailing_high DECIMAL(16, 8),
    trailing_stop_price DECIMAL(16, 8),
    trailing_activated_at TIMESTAMP,
    trailing_stop_executed_at TIMESTAMP,
    trailing_exit_reason VARCHAR(50)
);

-- Índices para performance
CREATE INDEX idx_trailing_active ON trade_log(trailing_active);
CREATE INDEX idx_trailing_symbol_active ON trade_log(symbol, trailing_active);
```

---

## 🔀 State Machine – Trailing Stop

```
╔═══════════════════════════════════════════════════════╗
║            TRAILING STOP STATE MACHINE                 ║
╚═══════════════════════════════════════════════════════╝

    [INACTIVE]
        ↓
        │ profit >= threshold?
        ↓
    [ACTIVE]
        ├─→ price ↑ → update trailing_high → [ACTIVE]
        │
        ├─→ price ≤ trailing_stop → [TRIGGERED] → CLOSE
        │
        └─→ profit < 0 → [INACTIVE] (volta ao SL estático)

Flow Transition:
- INACTIVE → ACTIVE: profit_r >= activation_threshold
- ACTIVE → ACTIVE: price > trailing_high (update only)
- ACTIVE → INACTIVE: profit_pct < 0 (revert to static SL)
- ACTIVE → TRIGGERED: price <= trailing_stop_price (execute close)
```

---

## 🧪 Test Strategy

### Unit Tests (test_trailing_stop.py)

```python
def test_tsl_activation():
    """TSL ativa quando lucro >= threshold."""
    # Setup
    config = TrailingStopConfig(activation_threshold=1.5)
    tsl = TrailingStopManager(config)
    position = Position(entry_price=100, current_price=115)
    
    # Execute
    position = tsl.evaluate(position)
    
    # Assert
    assert position.trailing_active is True

def test_tsl_high_tracking():
    """Rastreia o maior preço."""
    # ... teste lógica de update do high
    
def test_tsl_stop_calculation():
    """Calcula stop com distância %."""
    # ... teste cálculo do stop_price

def test_tsl_deactivation_on_loss():
    """Desativa se voltar a perda."""
    # ... teste desativação quando lucro < 0
```

### Integration Tests (test_tsl_integration.py)

```python
def test_tsl_with_execution():
    """TSL dentro do fluxo de execução completo."""
    # Montar posição aberta
    # Simular preço subindo 20%
    # Verificar TSL ativa
    # Simular preço caindo → close
    # Validar PnL e logs
    
def test_tsl_coexistence_with_sl():
    """TSL + SL (-3%) não conflitam."""
    # ... teste precedência de proteções

def test_tsl_db_persistence():
    """Dados TSL salvos e recuperados corretamente."""
    # ...
```

---

## 📊 Performance & Constraints

| Item | Alvo | Justificativa |
|------|------|---------------|
| **Update interval** | 100ms | Woll WebSocket cadence |
| **DB Write latency** | < 50ms | Não bloqueia next check |
| **API Call latency** | < 300ms | SLA Binance REST |
| **Memory per position** | < 2KB | 10k posições = 20MB |
| **CPU (per loop)** | < 5ms | Permite 20 pos/core |

---

## 🔐 Safety & Inviolability

### Garantias de Segurança

1. **TSL nunca pode desabilitar SL:** TSL é uma _camada adicional_, não substituição
2. **Sem race conditions:** Usa DB locks para updates simultâneos
3. **Auditoria:** Toda ativação/deativação registrada com timestamp
4. **Fallback:** Se TSL falha, SL (-3%) sempre ativa

### Marker INVIOLÁVEL

```python
# risk/riskgate.py
class RiskGate:
    # ⚠️  INVIOLÁVEL — Nunca removam ou desabilitem esta proteção
    def _check_static_stop_loss(self, position: Position) -> bool:
        """Static SL permanece SEMPRE ativo como fallback."""
        if not self.static_sl_enabled:
            raise RuntimeError("❌ CRITICAL: Static SL desabilitado!")
        return position.current_price <= position.entry_price * 0.97
```

---

## 🚀 Deployment

### Ordem de Implementação

1. **Baixo risk:** Criar TSL Manager standalone (testável isoladamente)
2. **Integração:** Integrar em RiskGate (com feature flag)
3. **Testes:** Rodar 12 testes + backtesting
4. **Gradual rollout:** Feature flag para controlar ativação

### Feature Flag

```python
# config/settings.py
TRAILING_STOP_ENABLED = True  # Toggle TSL on/off sem código
TRAILING_STOP_DRY_RUN = False  # Log sem executar ordens
```

---

*Arquitetura revisada e aprovada por Arch (#6). Pronta para desenvolvimento.*
