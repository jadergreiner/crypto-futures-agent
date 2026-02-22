# Modulo de Execucao — Documentacao Tecnica

**Status:** Issue #58 — 60% Concluido  
**Ultima Atualizacao:** 2026-02-22  
**Owner:** Persona 1 (Lead Software Engineer)

---

## Visao Geral

O Modulo de Execucao eh responsavel por:

1. **OrderExecutor** — Executa ordens MARKET na Binance Futures com:
   - Timeout de 5 segundos
   - Validacao de RiskGate antes de cada ordem
   - Integracao com RateLimitedCollector para nao exceder rate limits
   - Retry logico via OrderQueue

2. **OrderQueue** — Fila thread-safe para gerenciar execucoes:
   - FIFO (First In, First Out)
   - Retry automatico (max 3 tentativas)
   - Observer pattern para notificacoes
   - Worker thread assincrono

3. **ErrorHandler** — Tratamento estruturado de erros:
   - Classificacao de exception tipos da Binance API
   - Strategy pattern para diferentes tipos de erro
   - Backoff exponencial para retry
   - Logging estruturado em portugues

---

## Arquitetura

```
execution/
├── order_executor.py      # Executor de ordens (400+ linhas)
├── order_queue.py         # Fila thread-safe (370+ linhas)
├── error_handler.py       # Handler de erros (370+ linhas)
├── heuristic_signals.py   # (existente)
└── __init__.py
```

### Diagrama de Sequencia

```
Decisao do Agente
       ↓
OrderExecutor.execute_decision()
       ├─→ RiskGate.validar_ordem()  [BLOQUEIO POR RISCO]
       ├─→ RateLimitedCollector.check_rate_limit()  [THROTTLE]
       └─→ OrderQueue.enqueue(order)
                ↓
           OrderQueue.start_worker()
                ├─→ OrderObserver.on_order_processing()
                ├─→ ErrorHandler.handle_with_retry()
                │       ├─→ REST API POST /order
                │       ├─→ Retry (max 3x com backoff)
                │       └─→ Timeout 5s se nao responder
                ├─→ OrderObserver.on_order_executed()
                └─→ Log estruturado (timestamp, symbol, side, qty)
```

---

## Componentes Principais

### 1. OrderExecutor (`order_executor.py`)

Classe principal que orquestra execucao de ordens.

```python
from execution.order_executor import OrderExecutor

executor = OrderExecutor(client, db, mode="paper")

result = executor.execute_decision(
    position={
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "position_size_qty": 0.5,
        "mark_price": 50000.0,
    },
    decision={
        "agent_action": "CLOSE",
        "decision_confidence": 0.95,
    },
)

# result = {
#     "executed": True,
#     "action": "CLOSE",
#     "symbol": "BTCUSDT",
#     "side": "SELL",
#     "quantity": 0.5,
#     "order_response": {...},
#     "reason": "Ordem executada com sucesso",
#     "mode": "paper",
# }
```

**Safety Guards (7 camadas):**

1. `reduceOnly=True` — Binance rejeita se tentaria abrir nova posicao
2. Whitelist de simbolos — Apenas simbolos autorizados
3. Threshold de confianza — `decision_confidence >= 0.70`
4. Whitelist de acoes — Apenas `CLOSE` e `REDUCE_50`
5. Cooldown por simbolo — Max 1 execucao a cada 15 minutos
6. Limite diario — Max 6 execucoes por dia
7. Retry logico — Tentativas automaticas via OrderQueue

**Modo Paper vs Live:**

- Ambos enviam ordens REAIS para simbolos autorizados
- Diferenca eh no contexto de operacao e logging
- Nenhuma ordem eh bloqueada por modo; apenas por guards

### 2. OrderQueue (`order_queue.py`)

Fila thread-safe para gerenciar execucoes asincronas.

```python
from execution.order_queue import OrderQueue, Order, OrderObserver

queue = OrderQueue(max_queue_size=50)

# Registrar executor
def my_executor(order):
    # Executa ordem real via Binance API
    return {"orderId": 123, "status": "FILLED"}

queue.register_executor(my_executor)

# Registrar observer (notificacoes)
class MyObserver(OrderObserver):
    def on_order_queued(self, order):
        print(f"Ordem enfileirada: {order.order_id}")

    def on_order_executed(self, order, result):
        print(f"Ordem executada: {result}")

    def on_order_failed(self, order, error):
        print(f"Ordem falhou: {error}")

observer = MyObserver()
queue.subscribe(observer)

# Enfileirar ordem
order = Order(
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.1,
    order_type="MARKET",
)
queue.enqueue(order)

# Iniciar worker
queue.start_worker()

# Obter estatisticas
stats = queue.get_statistics()
# {
#     "total_orders": 1,
#     "executed": 1,
#     "failed": 0,
#     "pending": 0,
#     "success_rate": 1.0,
# }

queue.stop_worker()
```

**Retry Logic:**

- Max 3 tentativas por ordem
- Backoff exponencial: 1s, 2s, 4s
- Se falhar permanentemente, tenta proxima ordem na fila

### 3. ErrorHandler (`error_handler.py`)

Handler central para todos os erros.

```python
from execution.error_handler import ErrorHandler, ErrorType

handler = ErrorHandler()

# Usar handle_with_retry
def api_call():
    # Chamada para Binance API
    pass

success, result, error_info = handler.handle_with_retry(
    operation=api_call,
    operation_name="OrderExecutor.execute_market_order",
    context={
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.1,
    }
)

if not success:
    # error_info = {
    #     "error_type": "network_error",
    #     "error_message": "...",
    #     "error_details": "...",
    #     "attempt": 3,
    #     "timestamp": "2026-02-22T...",
    # }
    pass
```

**Tipos de Erro Suportados:**

| Tipo | Severidade | Retry? | Max Tentativas | Backoff |
|------|-----------|--------|----------------|---------|
| API_ERROR | Media | Sim | 3 | 1-8s exponencial |
| NETWORK_ERROR | Alta | Sim | 5 | 2-16s exponencial |
| TIMEOUT_ERROR | Media | Sim | 3 | 1-4s exponencial |
| RATE_LIMIT_ERROR | Critica | Sim | 3 | 60-300s exponencial |
| INSUFFICIENT_BALANCE | Alta | Nao | 0 | — |
| INVALID_ORDER | Alta | Nao | 0 | — |
| UNKNOWN_ERROR | Media | Sim | 2 | 2-8s exponencial |

---

## Integracao com Outros Modulos

### Integracao com RiskGate (Issue #57)

**CRITICO:** Toda ordem passa por RiskGate antes de execucao.

```python
from risk.risk_gate import RiskGate

risk_gate = RiskGate()

# Em OrderExecutor.execute_decision()
pode_executar = risk_gate.validar_ordem(
    symbol=position["symbol"],
    side=side_from_action,
    quantity=ordem_quantity,
    saldo_atual=saldo,
)

if not pode_executar:
    return {
        "executed": False,
        "reason": "Ordem bloqueada por RiskGate",
    }
```

**Protecoes Inviolaveis:**
- Stop Loss (-3%) SEMPRE ativo
- Circuit Breaker (-3.1%) monitorado
- Nenhuma ordem ultrapassar drawdown maximo

### Integracao com RateLimitedCollector (Issue #55)

**OBRIGATORIO:** Respeitar rate limits da Binance (<1200 req/min).

```python
from data.rate_limited_collector import RateLimitedBinanceCollector

collector = RateLimitedBinanceCollector(
    client,
    rate_limit_max_per_minute=1200,
    use_adaptive=True,
)

# Em OrderExecutor antes de executar
collector._check_rate_limit()  # Bloqueia se necessario
# Fazer requisicao para API Binance
collector.record_successful_request()

# Se erro 429:
collector.record_rate_limit_error()
```

---

## Testes

### Cobertura de Testes

**Arquivo:** `tests/test_execution.py`  
**Total:** 47+ casos de teste (excede 38+ requerido)  
**Tipos:** Unitario, Integracao, Parametrizado

### Rodando Testes

```bash
cd /repo/crypto-futures-agent

# Rodar todos os testes
pytest tests/test_execution.py -v

# Rodar com cobertura
pytest tests/test_execution.py --cov=execution --cov-report=html

# Rodar teste especifico
pytest tests/test_execution.py::TestErrorHandler::test_handle_with_retry_success -v

# Rodar com output detalhado de logs
pytest tests/test_execution.py -vv -s
```

### Fixture Principais

| Fixture | Descricao |
|---------|-----------|
| `mock_client` | Mock do cliente Binance SDK |
| `temp_db` | Banco de dados temporario |
| `order_executor` | OrderExecutor em modo paper |
| `order_queue` | OrderQueue vazio |
| `error_handler` | ErrorHandler com estrategias |
| `mock_binance_api` | Mock realista da API Binance |

### Matriz de Cobertura (Resumo)

```
ErrorHandler — 14 testes
  ├─ Init + Classificacao: T001-T005
  ├─ Backoff exponencial: T006-T009
  ├─ Retry logic: T010-T014
  └─ Edge cases: T045

OrderQueue — 15 testes
  ├─ Init + Order creation: T015-T017
  ├─ Enqueue + Observers: T018-T022
  ├─ Retry + Retrieval: T023-T029
  └─ Statistics: T028

Integracao — 2 testes
  ├─ Mock API: T030
  └─ Timeout scenario: T031

Parametrizado — 13 testes
  ├─ Error type policy: T032-T037
  ├─ Queue sizes: T038-T040
  ├─ Order variations: T041-T044
  └─ Misc: T046-T047
```

---

## Criteria de Aceite (Issue #58)

**Status:** 60% Concluido (S1-S3 Implementados)

| ID | Criterio | Status | Evidencia |
|----|----------|--------|-----------|
| S1 | OrderExecutor executa MARKET com timeout 5s | ✅ | `order_executor.py`:400+ linhas |
| S2 | ErrorHandler capture APIError/NetworkError | ✅ | `error_handler.py`:370+ linhas |
| S3 | OrderQueue com retry (max 3) | ✅ | `order_queue.py`:370+ linhas |
| S4 | 500+ linhas testes parametrizados | ✅ | `test_execution.py`:600+ linhas |
| S5 | Integracao RiskGate + RateLimiter validada | 🟡 | Integrado, testes basicos OK |

---

## Deployment e Operacao

### Modo Paper (Testing)

```python
executor = OrderExecutor(client, db, mode="paper")
# Ordens REAIS sao enviadas para simbolos autorizados
# Modo eh apenas contexto de logging
```

### Modo Live (Producao)

```python
executor = OrderExecutor(client, db, mode="live")
# Ordens REAIS sao enviadas para simbolos autorizados
# 7 safety guards SEMPRE ativos
```

### Monitoring

```python
# Verificar historico de execucoes
from data.database import DatabaseManager
db = DatabaseManager("/path/to/db.sqlite")

execucoes = db.query(
    "SELECT * FROM execution_history WHERE date > '2026-02-20' LIMIT 10"
)

# Verificar estatisticas da fila
stats = queue.get_statistics()
print(f"Taxa de sucesso: {stats['success_rate']:.1%}")
print(f"Pendentes: {stats['pending']}")
```

---

## Troubleshooting

| Problema | Causa | Solucao |
|----------|-------|---------|
| Orders timeout | API Binance lenta | Aumentar timeout, verificar conectividade |
| Rate limit 429 | Muitas requisicoes | RateLimitedCollector throttle 30s+ |
| Ordem bloqueada | RiskGate acionado | Verificar drawdown, pos market price |
| Worker nao processa | Executor nao registrado | Chamar `queue.register_executor()` |
| Erro "insufficient balance" | Saldo insuficiente | Verificar `get_account()` resposta |

---

## Dependencias

```python
# Core
from execution.order_executor import OrderExecutor
from execution.order_queue import OrderQueue, Order
from execution.error_handler import ErrorHandler

# Integracao
from risk.risk_gate import RiskGate
from data.rate_limited_collector import RateLimitedBinanceCollector
from data.database import DatabaseManager

# Padroes
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

# Stdlib
import threading
import time
import logging
```

---

## Historico de Mudancas

| Data | Versao | Mudanca |
|------|--------|---------|
| 2026-02-22 | 0.1.0 | Implementacao inicial Issue #58 |

---

## Referencias

- [Issue #58 Specification](../../docs/ISSUE_58_DELIVERABLES.md)
- [Risk Gate (Issue #57)](../../risk/risk_gate.py)
- [RateLimitedCollector (Issue #55)](../../data/rate_limited_collector.py)
- [Best Practices](../../BEST_PRACTICES.md)
- [Copilot Instructions](.github/copilot-instructions.md)
