# 📡 OpenAPI Specification — Crypto Futures Agent

**Versão:** 0.3.0
**OpenAPI:** 3.0.0
**Data:** 28 FEV 2026

---

## Contexto

O Crypto Futures Agent expõe uma API interna (via Python) para:
- Gerenciar posições abertas
- Executar sinais manualmente
- Consultar cache de dados históricos
- Obter métricas de risco em tempo real

**Nota:** Esta especificação é **proposta para futura implementação** de
REST endpoints (Flask/FastAPI).

---

## OpenAPI 3.0.0 Specification

```yaml
openapi: 3.0.0
info:
  title: Crypto Futures Agent API
  version: 0.3.0
  description: |
    API para gerenciamento de trading automático com análise SMC + ML.
    Suporta Paper Trading + Live Trading modes.
  license:
    name: MIT

servers:
  - url: http://localhost:8000/api/v1
    description: Desenvolvimento local
  - url: https://api.cryptofutures.local/v1
    description: Produção (futuro)

tags:
  - name: Positions
    description: Gerenciar posições abertas/fechadas
  - name: Orders
    description: Colocação e cancelamento de ordens
  - name: Signals
    description: Consultar sinais detectados
  - name: Data
    description: Histórico e cache de dados
  - name: Risk
    description: Métricas de risco e treasury
  - name: Backtesting
    description: Simulação histórica

paths:
  /positions:
    get:
      tags:
        - Positions
      summary: Listar posições abertas
      description: Retorna todas as posições abertas com P&L atual
      responses:
        '200':
          description: Lista de posições
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Position'
        '401':
          description: Não autenticado

  /positions/{position_id}:
    get:
      tags:
        - Positions
      summary: Obter detalhes de uma posição
      parameters:
        - name: position_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Posição encontrada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Position'
        '404':
          description: Posição não encontrada

    delete:
      tags:
        - Positions
      summary: Fechar posição manualmente
      parameters:
        - name: position_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Posição fechada com sucesso
        '400':
          description: Erro ao fechar (ex: já fechada)

  /orders:
    post:
      tags:
        - Orders
      summary: Colocar ordem manualmente
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                symbol:
                  type: string
                  example: BTCUSDT
                side:
                  type: string
                  enum: [BUY, SELL]
                quantity:
                  type: number
                  example: 0.1
                entry_price:
                  type: number
                  example: 67500.00
                stop_loss_pct:
                  type: number
                  example: 0.02
                take_profit_pct:
                  type: number
                  example: 0.06
      responses:
        '201':
          description: Ordem criada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Position'
        '400':
          description: Erro de validação (ex: capital insuficiente)
        '403':
          description: Circuit breaker ativo

  /signals:
    get:
      tags:
        - Signals
      summary: Listar sinais detectados (últimas 24h)
      parameters:
        - name: symbol
          in: query
          schema:
            type: string
            example: BTCUSDT
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, traded, ignored]
      responses:
        '200':
          description: Lista de sinais
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Signal'

  /data/klines/{symbol}:
    get:
      tags:
        - Data
      summary: Obter candles históricos (cached)
      parameters:
        - name: symbol
          in: path
          required: true
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
      responses:
        '200':
          description: Candles retornados
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Kline'
        '404':
          description: Símbolo não em cache

  /risk/metrics:
    get:
      tags:
        - Risk
      summary: Métricas de risco em tempo real
      responses:
        '200':
          description: Métricas atualizadas
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RiskMetrics'

  /risk/circuit-breaker:
    get:
      tags:
        - Risk
      summary: Status do circuit breaker
      responses:
        '200':
          description: Status atual
          content:
            application/json:
              schema:
                type: object
                properties:
                  active:
                    type: boolean
                  reason:
                    type: string
                  threshold:
                    type: number

  /backtest/run:
    post:
      tags:
        - Backtesting
      summary: Executar backtesting
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                symbol:
                  type: string
                start_date:
                  type: string
                  format: date-time
                end_date:
                  type: string
                  format: date-time
      responses:
        '200':
          description: Backtesting concluído
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BacktestResult'
        '400':
          description: Parâmetros inválidos

components:
  schemas:
    Position:
      type: object
      properties:
        position_id:
          type: string
          example: pos_1234567890
        symbol:
          type: string
          example: BTCUSDT
        side:
          type: string
          enum: [LONG, SHORT]
        status:
          type: string
          enum: [OPENING, OPEN, CLOSING, CLOSED]
        quantity:
          type: number
          example: 0.1
        entry_price:
          type: number
          example: 67500.00
        current_price:
          type: number
          example: 68000.00
        entry_time:
          type: string
          format: date-time
        exit_time:
          type: string
          format: date-time
          nullable: true
        stop_loss:
          type: number
          example: 66150.00
        take_profit:
          type: number
          example: 71550.00
        current_pnl:
          type: number
          example: 500.00
        current_pnl_pct:
          type: number
          example: 0.75
        margin_used:
          type: number
          example: 1350.00

    Signal:
      type: object
      properties:
        signal_id:
          type: string
        symbol:
          type: string
        signal_type:
          type: string
          enum: [BUY, SELL, NEUTRAL]
        timeframe:
          type: string
          enum: [D1, H4, H1]
        detected_time:
          type: string
          format: date-time
        order_block_low:
          type: number
        order_block_high:
          type: number
        ppo_confidence:
          type: number
          minimum: 0.0
          maximum: 1.0
        status:
          type: string
          enum: [pending, traded, ignored]

    Kline:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        open:
          type: number
        high:
          type: number
        low:
          type: number
        close:
          type: number
        volume:
          type: number
        quote_volume:
          type: number
        trades:
          type: integer

    RiskMetrics:
      type: object
      properties:
        capital:
          type: number
          example: 10000.00
        balance:
          type: number
          example: 9500.00
        equity:
          type: number
          example: 9750.00
        margin_used:
          type: number
          example: 3000.00
        margin_ratio:
          type: number
          example: 3.25
        portfolio_pnl:
          type: number
          example: -250.00
        portfolio_pnl_pct:
          type: number
          example: -2.5
        max_drawdown:
          type: number
          example: -5.0
        open_positions:
          type: integer
          example: 3
        max_positions:
          type: integer
          example: 5

    BacktestResult:
      type: object
      properties:
        symbol:
          type: string
        period:
          type: string
          example: 2025-02-28 to 2026-02-28
        trades:
          type: integer
        wins:
          type: integer
        losses:
          type: integer
        win_rate:
          type: number
          example: 0.65
        sharpe_ratio:
          type: number
          example: 1.25
        max_drawdown:
          type: number
          example: -8.5
        calmar_ratio:
          type: number
          example: 0.85
        profit_factor:
          type: number
          example: 2.1
        total_return:
          type: number
          example: 12500.00
        total_return_pct:
          type: number
          example: 125.0

  securitySchemes:
    api_key:
      type: apiKey
      name: X-API-Key
      in: header

security:
  - api_key: []
```

---

## Exemplos de Uso

### Exemplo 1: Listar Posições Abertas

```bash
curl -X GET http://localhost:8000/api/v1/positions \
  -H "X-API-Key: your-api-key"
```

**Resposta:**
```json
[
  {
    "position_id": "pos_001",
    "symbol": "BTCUSDT",
    "side": "LONG",
    "status": "OPEN",
    "quantity": 0.1,
    "entry_price": 67500.00,
    "current_price": 68000.00,
    "current_pnl": 500.00,
    "current_pnl_pct": 0.75
  }
]
```

### Exemplo 2: Consultar Métricas de Risco

```bash
curl -X GET http://localhost:8000/api/v1/risk/metrics \
  -H "X-API-Key: your-api-key"
```

**Resposta:**
```json
{
  "capital": 10000.00,
  "balance": 9500.00,
  "equity": 9750.00,
  "margin_ratio": 3.25,
  "portfolio_pnl": -250.00,
  "max_drawdown": -5.0,
  "open_positions": 3
}
```

---

## Autenticação

Todos os endpoints requerem header:
```
X-API-Key: <chave-secreta>
```

**Geração de chave:**
```python
# config/api_keys.py
API_KEYS = {
  "dev": "sk_test_1234567890abcdef",
  "prod": "sk_live_fedcba0987654321"
}
```

---

## Rate Limiting

- **Limite:** 1000 requests por minuto (por API key)
- **Resposta:** Header `X-RateLimit-Remaining`
- **Excesso:** HTTP 429 (Too Many Requests)

---

## Versionamento

- **Atual:** v1 (`/api/v1/*`)
- **Futuro:** v2 com breaking changes (mantém v1 ativo)
- **Deprecação:** 6 meses de aviso antes de remover versão

---

## Status de Implementação

| Endpoint | Status | Prioridade |
|----------|--------|-----------|
| GET /positions | Planejado | 🟢 Alta |
| POST /orders | Planejado | 🟢 Alta |
| GET /signals | Planejado | 🟡 Média |
| GET /data/klines | Planejado | 🟡 Média |
| GET /risk/metrics | Planejado | 🔴 Crítica |
| POST /backtest/run | Planejado | 🟡 Média |

---

## Referências

- [RFC 6750: OAuth 2.0 Bearer Token](https://tools.ietf.org/html/rfc6750)
- [OpenAPI 3.0.0 Spec](https://spec.openapis.org/oas/v3.0.0)
- [Data Models](data_models.md)

