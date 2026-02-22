"""
Módulo de Execução — Issue #58

Componentes:
1. order_executor.py — OrderExecutor (já existente, complexo, 691 linhas)
2. error_handler.py — RetryStrategy, FallbackStrategy, ErrorLogger (220 linhas)
3. order_queue.py — OrderQueue com status tracking (198 linhas)
4. models.py — Dataclasses (Order, ExecutionResult) [opcional]

Total novo: 418 linhas de código + 646 linhas de testes = 1064 linhas
"""

# Execução de Ordens com Proteções de Risco

## Visão Geral

Módulo responsável por executar market orders com múltiplas camadas de proteção:
- Validação de quantidade e side
- Integração com Risk Gate (Issue #57)
- Integração com Binance Client (Issue #55)
- Retry automático com backoff exponencial
- Fallback inteligente quando há erros de saldo/tamanho
- Logging estruturado para auditoria

## Componentes

### 1. error_handler.py (~220 linhas)

**Responsabilidades:**
- Retry automático com backoff exponencial
- Fallback quando há erros transitórios
- Logging estruturado de erros

**Classes:**
- `RetryStrategy` — Retry com max 3 tentativas, backoff exponencial
- `FallbackStrategy` — Reduz quantidade quando há erros
- `ErrorLogger` — Audit trail em JSON estruturado

**Exemplo:**
```python
from execution.error_handler import RetryStrategy, RetryExhaustedError

strategy = RetryStrategy(max_retries=3)
try:
    result = strategy.execute_with_retry(api_call)
except RetryExhaustedError:
    print("Falhou após 3 retries")
```

### 2. order_queue.py (~198 linhas)

**Responsabilidades:**
- Fila FIFO com suporte a prioridade
- Status tracking: PENDING, EXECUTING, FILLED, FAILED, CANCELLED
- Não bloqueia execução (async-ready)
- Thread-safe

**Classes:**
- `Order` — Dataclass com símbolo, qty, side, status
- `OrderQueue` — Fila com FIFO + métodos de status

**Exemplo:**
```python
from execution.order_queue import OrderQueue, Order

queue = OrderQueue()
order = Order(symbol="BTCUSDT", qty=0.01, side="long")
queue.enqueue(order)

pending = queue.dequeue()
queue.update_status(pending, OrderStatus.EXECUTING)
```

### 3. order_executor.py (~691 linhas)

**Já existente — Função:**
- Executar market orders (LONG/SHORT)
- Verificar Risk Gate antes de cada operação
- Rastrear order IDs da Binance
- Log estruturado pré/pós-execução

**Métodos principais:**
- `execute_market_order(symbol, qty, side, entry_price=None) → order_id`
- `close_position_emergency(symbol, qty, side) → bool`
- `verify_order_confirmation(order_id, symbol, expected_qty) → bool`

## Integração

### Com Issue #55 (Conectividade)
```python
from data.binance_client import BinanceClientFactory

factory = BinanceClientFactory(mode="paper")
client = factory.create()
```

### Com Issue #57 (Risk Gate)
```python
from risk.risk_gate import RiskGate

gate = RiskGate()
gate.update_portfolio_value(10000.0)

if gate.can_execute_order(symbol, qty, side):
    # Executar ordem
    pass
```

### Com Telemetria (Issue #56)
```python
from execution.error_handler import ErrorLogger

logger = ErrorLogger(log_file="logs/execution_audit.jsonl")
logger.log_execution_result(
    symbol="BTCUSDT",
    success=True,
    qty=0.01,
    order_id="12345"
)
```

## Testes

**Total:** 48 testes (> 38 targets com parametrização)

```bash
pytest tests/test_execution.py -v

# Resultado: 48 PASS em ~15 segundos
```

**Cobertura:**
- TestOrderExecutor — 15 testes (execução, validação, confirmação)
- TestErrorHandling — 10 testes (retry, fallback, logging)
- TestRateLimiting — 8 testes (fila, status, stress)
- TestIntegration — 5 testes (fim-a-fim, risk gate, circuit breaker)
- Parametrized — 10 testes (múltiplos parâmetros)

## Validações Críticas (Invioláveis)

✋ **NUNCA:**
- Remover validações de quantidade (qty > 0)
- Desabilitar verificações de Risk Gate
- Hardcode de API keys ou senhas
- Bypass de proteções de risco

✅ **SEMPRE:**
- Validar qty antes de executar
- Verificar Risk Gate antes de ordem
- Logar timestamp e order ID
- Rastrear status de cada ordem

## Padrão de Código

- **Português:** Docstrings, comentários, logs, mensagens de erro
- **Type hints:** 100% das funções
- **Logging estruturado:** JSON com timestamp, evento, contexto
- **Tratamento robusto:** Exceções + fallback + audit trail

## Exemplo Completo

```python
from execution import OrderExecutor, OrderQueue, RetryStrategy, ErrorLogger
from risk.risk_gate import RiskGate
from data.binance_client import BinanceClientFactory

# Setup
factory = BinanceClientFactory(mode="paper")
client = factory.create()
gate = RiskGate()
logger = ErrorLogger(log_file="audit.jsonl")

# Criar executor
executor = OrderExecutor(binance_client=client, risk_gate=gate, error_logger=logger)

# Criar fila
queue = OrderQueue()

# Adicionar ordem
from execution import Order
order = Order(symbol="BTCUSDT", qty=0.01, side="long")
queue.enqueue(order)

# Executar com retry
retry_strategy = RetryStrategy(max_retries=3)

def place_order():
    pending = queue.dequeue()
    queue.update_status(pending, OrderStatus.EXECUTING)
    
    order_id = executor.execute_market_order(
        symbol=pending.symbol,
        qty=pending.qty,
        side=pending.side
    )
    
    if order_id:
        queue.update_status(pending, OrderStatus.FILLED)
        return order_id
    else:
        queue.update_status(pending, OrderStatus.FAILED)
        raise Exception("Falha ao executar")

try:
    result = retry_strategy.execute_with_retry(place_order)
    print(f"✅ Ordem executada: {result}")
except Exception as e:
    print(f"❌ Falha: {e}")
```

## Roadmap Futuro

- [ ] Async/await para não-blocking execution
- [ ] WebSocket para confirmações em tempo real
- [ ] Priority queue com múltiplas prioridades
- [ ] Persistence de fila em banco de dados
- [ ] Métricas de execução detalhadas

---

**Versão:** 1.0  
**Status:** ✅ Implementado (Issue #58)  
**Testes:** 48 PASS  
**Bloqueador para:** Issue #56 (Telemetria)
