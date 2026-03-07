# 🗂️ Modelagem de Dados — Crypto Futures Agent

**Versão:** 0.2.0
**Data:** 07 MAR 2026
**Responsável:** Arquiteto (#6), Data (#11)

---

## 🎯 Propósito

Documentar a **estrutura de dados** do projeto: entidades, relacionamentos, schemas SQLite e Parquet, e fluxos de dados críticos.

---

## 📊 ENTIDADES PRINCIPAIS

### 1. **Account** (Conta de Trading)

Representa o estado financeiro da conta na Binance.

```
Table: account
├── account_id (PK)        | UUID | Identificador único
├── exchange              | VARCHAR | "binance"
├── account_type          | VARCHAR | "futures"
├── balance_usd           | DECIMAL | Saldo total em USD
├── free_balance_usd      | DECIMAL | Saldo disponível
├── locked_balance_usd    | DECIMAL | Saldo em ordens abertas
├── equity_usd            | DECIMAL | Equity = balance + unrealized_pnl
├── unrealized_pnl_usd    | DECIMAL | P&L não realizado
├── margin_ratio          | DECIMAL | Usado / Total margin
├── max_leverage          | INT     | Alavancagem máxima permitida
├── fee_taker_pct         | DECIMAL | Taxa de execução (maker)
├── fee_maker_pct         | DECIMAL | Taxa de execução (taker)
├── created_at            | TIMESTAMP | Data criação conta
├── last_sync_at          | TIMESTAMP | Último sync com Binance
└── is_active             | BOOLEAN | Ativa ou não

FK: Nenhuma (agregado raiz)
Relacionamentos: account.account_id → position.account_id
               account.account_id → order.account_id
               account.account_id → trade.account_id
```

**Regras de Negócio Mapeadas:** R2, R3, R5

---

### 2. **Position** (Posição Aberta)

Representa uma posição aberta na Binance.

```
Table: position
├── position_id (PK)      | UUID | Identificador único
├── account_id (FK)       | UUID | Referência para Account
├── symbol                | VARCHAR | Ex: "BTCUSDT"
├── side                  | VARCHAR | "LONG" ou "SHORT"
├── entry_price           | DECIMAL | Preço de entrada
├── entry_time            | TIMESTAMP | Timestamp da entrada
├── quantity              | DECIMAL | Tamanho da posição em cripto
├── notional_usd          | DECIMAL | Tamanho em USD (quantity * entry_price)
├── leverage_used         | DECIMAL | Alavancagem efetiva (notional / margin_used)
├── margin_used_usd       | DECIMAL | Margin bloqueado nesta posição
├── stop_loss_price       | DECIMAL | Preço de SL (obrigatório)
├── take_profit_price     | DECIMAL | Preço de TP (recomendado)
├── current_price         | DECIMAL | Preço último update
├── unrealized_pnl_usd    | DECIMAL | P&L não realizado = quantity × (current - entry)
├── unrealized_roi_pct    | DECIMAL | ROI em % = pnl / margin_used
├── trailing_stop_active  | BOOLEAN | Se trailing stop está ativo
├── trailing_stop_dist    | DECIMAL | Distância do trailing stop
├── is_closed             | BOOLEAN | Se posição foi fechada
├── created_at            | TIMESTAMP | Timestamp abertura
├── updated_at            | TIMESTAMP | Último update
└── closed_at             | TIMESTAMP | Timestamp fechamento (NULL se aberta)

FK: account_id → account.account_id
Índices: account_id, symbol, is_closed
Relacionamentos: position.position_id → order.position_id
               position.position_id → trade.position_id
```

**Regras de Negócio Mapeadas:** R1, R3, R4, R6, R7

---

### 3. **Order** (Ordem de Execução)

Representa uma ordem colocada na Binance.

```
Table: order
├── order_id (PK)         | UUID | Identificador único (nosso sistema)
├── binance_order_id      | BIGINT | ID externo da Binance
├── account_id (FK)       | UUID | Referência para Account
├── position_id (FK)      | UUID | Referência para Position (NULL para SL/TP)
├── symbol                | VARCHAR | Ex: "BTCUSDT"
├── side                  | VARCHAR | "BUY" ou "SELL"
├── order_type            | VARCHAR | "LIMIT" ou "MARKET"
├── quantity              | DECIMAL | Quantidade de cripto
├── price_limit           | DECIMAL | Preço limite (para LIMIT orders)
├── status                | VARCHAR | "PENDING", "FILLED", "CANCELED", "REJECTED"
├── filled_quantity       | DECIMAL | Quantidade preenchida (parcial allowed)
├── filled_price_avg      | DECIMAL | Preço médio preenchimento
├── fee_usd               | DECIMAL | Taxa paga
├── created_at            | TIMESTAMP | Timestamp criação
├── updated_at            | TIMESTAMP | Último status update
└── error_message         | VARCHAR | Se REJECTED, motivo do erro

FK: account_id → account.account_id
FK: position_id → position.position_id (NULLABLE)
Índices: binance_order_id, account_id, status
Relacionamentos: order.order_id → trade.order_id
```

**Regras de Negócio Mapeadas:** R3, R4, R7

---

### 4. **Trade** (Operação Fechada)

Representa uma operação completa (entrada + saída + resultado).

```
Table: trade
├── trade_id (PK)         | UUID | Identificador único
├── account_id (FK)       | UUID | Referência para Account
├── position_id (FK)      | UUID | Referência para Position (fechada)
├── entry_order_id (FK)   | UUID | Order ID da entrada
├── exit_order_id (FK)    | UUID | Order ID da saída
├── symbol                | VARCHAR | Ex: "BTCUSDT"
├── side                  | VARCHAR | "LONG" ou "SHORT"
├── entry_price           | DECIMAL | Preço entrada
├── exit_price            | DECIMAL | Preço saída
├── quantity              | DECIMAL | Tamanho
├── entry_time            | TIMESTAMP | Tempo entrada
├── exit_time             | TIMESTAMP | Tempo saída
├── duration_minutes      | INT | Duração da operação em minutos
├── profit_loss_usd       | DECIMAL | Lucro/Perda em USD (positivo = ganho)
├── profit_loss_pct       | DECIMAL | Lucro/Perda em % do capital
├── r_multiple            | DECIMAL | R-múltiplo = pnl / risk_size
├── risk_usd              | DECIMAL | Risco original (entrada - SL)
├── win                   | BOOLEAN | TRUE se profit_loss_usd > 0
├── close_reason          | VARCHAR | "TP", "SL", "MANUAL", "STOP"
├── smc_signal_quality    | DECIMAL | Qualidade do sinal SMC (0-1.0)
├── ml_confidence         | DECIMAL | Confiança do modelo PPO (0-1.0)
├── tags                  | VARCHAR | "scalp", "swing", "trend", etc
├── created_at            | TIMESTAMP | Timestamp criação (mesmo que entry_time)
└── closed_at             | TIMESTAMP | Timestamp fechamento (mesmo que exit_time)

FK: account_id → account.account_id
FK: position_id → position.position_id
FK: entry_order_id → order.order_id
FK: exit_order_id → order.order_id
Índices: account_id, symbol, win, closed_at
Agregações: SUM(profit_loss_usd), AVG(r_multiple), COUNT(win=true)
Relacionamentos: Used para queries de performance
```

**Regras de Negócio Mapeadas:** R8, R9, R10, R14

---

### 5. **Candle** (Dados de Mercado)

OHLCV (Open, High, Low, Close, Volume) para cada símbolo e timeframe.

```
Table: candle
├── candle_id (PK)        | UUID | Identificador único
├── symbol                | VARCHAR | Ex: "BTCUSDT"
├── timeframe             | VARCHAR | "1h", "4h", "1d"
├── timestamp             | TIMESTAMP | Tempo abertura da vela
├── open                  | DECIMAL | Preço abertura
├── high                  | DECIMAL | Preço máximo
├── low                   | DECIMAL | Preço mínimo
├── close                 | DECIMAL | Preço fechamento
├── volume                | DECIMAL | Volume em cripto
├── volume_quoteAsset     | DECIMAL | Volume em USD (notional)
├── number_of_trades      | INT | Número de trades na vela
├── taker_buy_base_asset  | DECIMAL | Volume comprador
├── taker_buy_quote_asset | DECIMAL | Volume comprador (USD)
└── is_closed             | BOOLEAN | TRUE se vela completa

PK: (symbol, timeframe, timestamp) — Composite
Índices: (symbol, timeframe), timestamp, symbol
Particionamento: POR timeframe (tabelas separadas: candle_1h, candle_4h, candle_1d)
Fonte de dados: Binance REST API + Parquet snapshots
```

**Regras de Negócio Mapeadas:** R11 (multi-timeframe consensus)

---

### 6. **Signal** (Sinal Gerado)

Sinal gerado pelo SMC + ML antes de ordem executada.

```
Table: signal
├── signal_id (PK)        | UUID | Identificador único
├── symbol                | VARCHAR | Ex: "BTCUSDT"
├── timestamp             | TIMESTAMP | Tempo geração sinal
├── signal_type           | VARCHAR | "BUY", "SELL", "HOLD"
├── smc_bias              | VARCHAR | "BULLISH", "BEARISH", "NEUTRAL"
├── order_blocks          | INT | Número de order blocks detectados
├── fvg_level             | DECIMAL | Nível FVG detectado (fair value gap)
├── ml_confidence         | DECIMAL | Confiança modelo MLflow (0-1.0)
├── price_at_signal       | DECIMAL | Preço quando sinal gerado
├── recommended_entry     | DECIMAL | Entrada recomendada
├── recommended_sl        | DECIMAL | SL recomendado
├── recommended_tp        | DECIMAL | TP recomendado
├── expected_rr_ratio     | DECIMAL | Risk-reward ratio esperado
├── was_trade_opened      | BOOLEAN | Se trader abriu posição
├── trade_id (FK)         | UUID | Referência para Trade (se aberta)
├── ignored_reason        | VARCHAR | Motivo se ignorado (R10, R11, etc)
└── created_at            | TIMESTAMP | Timestamp criação

FK: trade_id → trade.trade_id (NULLABLE)
Índices: symbol, timestamp, signal_type
Relacionamento: Registro completo de sinais gerados + aceitos/rejeitados
```

**Regras de Negócio Mapeadas:** R10, R11

---

### 7. **Performance** (Métricas de Performance)

Agregações rolling de performance.

```
Table: performance
├── perf_id (PK)          | UUID | Identificador único
├── account_id (FK)       | UUID | Referência para Account
├── period                | VARCHAR | "daily", "weekly", "monthly"
├── date_start            | DATE | Data início período
├── date_end              | DATE | Data fim período
├── total_trades          | INT | Total operações completadas
├── winning_trades        | INT | Operações ganhas (profit > 0)
├── losing_trades         | INT | Operações perdidas (profit <= 0)
├── win_rate              | DECIMAL | winning_trades / total_trades
├── profit_loss_usd       | DECIMAL | P&L total do período
├── profit_loss_pct       | DECIMAL | P&L em % do capital inicial
├── gross_profit          | DECIMAL | Soma de todos os gains
├── gross_loss            | DECIMAL | Soma de todos os losses
├── profit_factor         | DECIMAL | gross_profit / abs(gross_loss)
├── avg_win_usd           | DECIMAL | Média de trades vencedores
├── avg_loss_usd          | DECIMAL | Média de trades perdedores
├── avg_r_multiple        | DECIMAL | R-múltiplo médio
├── largest_win           | DECIMAL | Maior ganho individual
├── largest_loss          | DECIMAL | Maior perda individual
├── max_consecutive_wins  | INT | Maior sequência vencedora
├── max_consecutive_losses| INT | Maior sequência perdedora
├── drawdown_max          | DECIMAL | Drawdown máximo %
├── drawdown_current      | DECIMAL | Drawdown no fim do período
├── sharpe_ratio          | DECIMAL | Sharpe ratio (se dados suficientes)
├── sortino_ratio         | DECIMAL | Sortino ratio
├── calmar_ratio          | DECIMAL | Calmar ratio = CAGR / max_drawdown
├── recovery_factor       | DECIMAL | Profit / max_drawdown
├── created_at            | TIMESTAMP | Timestamp cálculo
└── updated_at            | TIMESTAMP | Última atualização

FK: account_id → account.account_id
Índices: account_id, period, date_start
Agregações: Calculadas automaticamente ao fim de cada período
```

**Regras de Negócio Mapeadas:** R5, R13, R14, R15

---

## 🔄 FLUXOS DE DADOS CRÍTICOS

### Fluxo 1: Entrada de Dados (Binance → Sistema)

```
Binance REST API
    ↓
[data/binance_client.py] — Fetch candles + account info
    ↓
SQLite (candle_1h, candle_4h, candle_1d)
    ↓
Memory cache (últimas 500 velas por timeframe)
    ↓
[agent/smc_analyzer.py] — Análise SMC (O.B., FVG, BoS)
    ↓
[agent/rl_agent.py] — ML inference (pré-treinado)
    ↓
Signal table (registro)
```

**Frequência:** A cada 4h (ao fechar candle 4h)
**SLA:** < 2s da API até signal generation
**Fallback:** Parquet snapshots se API indisponível > 10h

---

### Fluxo 2: Execução de Ordem

```
Signal (confidence ≥ 0.65)
    ↓
[risk/risk_manager.py] — Validação (R1-R7)
    ↓
[heuristics.py] — Filtros adicionais (R9-R12)
    ↓
IF accept: [execution/order_executor.py] — Place order
    ↓
Order table (status=PENDING)
    ↓
IF filled: Update Position + Performance
    ↓
Position (is_closed=FALSE)
    ↓
[monitoring/performance.py] — Monitor SL/TP
    ↓
IF hit SL/TP: Close position + create Trade + Update Account
    ↓
Trade table (completa com resultado)
```

**Latência:** <100ms (local validation + Binance API)
**Crítico:** Impossível voltar atrás após sendOrder()

---

### Fluxo 3: Sinalização de Risco

```
Position (unrealized PnL)
    ↓
[monitoring/performance.py] — Calcula drawdown
    ↓
IF drawdown ≥ -5%: Alerta AMARELO (logging)
IF drawdown ≥ -8%: Alerta VERMELHO + Telegram notify
IF drawdown ≥ -15%: CIRCUIT BREAKER — parar trades
    ↓
[notifications/telegram_client.py] — Send alert
```

**Frequência:** A cada candle fechado (4h)
**Sensibilidade:** % do capital

---

## 💾 PERSISTÊNCIA: SQLite vs Parquet

### SQLite (Hot Cache — Operacional)

**Tabelas em SQLite:**
- `account` — Estado corrente
- `position` — Posições abertas (query rápida)
- `order` — Ordens últimas 30 dias
- `trade` — Últimas 500 operações (histórico recente)
- `signal` — Últimas 1000 sinais (histórico sinais)
- `performance` — Agregações diárias/mensais
- `candle_*` — Últimas 500 velas por timeframe (3-5 MB total)

**Características:**
- Transações ACID (garantia de consistência)
- Queries estruturadas (índices)
- Acesso <100ms
- Mantém últimas 30 dias + histórico operacional

---

### Parquet (Cold Storage — Snapshots)

**Arquivo:**
- `s3://bucket/parquet/candles_1y.parquet` — 1 ano de dados (4h)
- Compressão zstd (footprint 0.019 GB)
- Append-only (novo snapshot a cada semana)

**Características:**
- Backtesting histórico (1 ano)
- Analytics offline
- Recuperação de disaster
- Latência ~1.25s (aceitável para backtest)

---

## 🎯 Índices Críticos (Performance)

```sql
-- Queries frequentes (production)
CREATE INDEX idx_position_account_open
  ON position(account_id, is_closed)
  WHERE is_closed = FALSE;

CREATE INDEX idx_trade_account_closed
  ON trade(account_id, closed_at DESC);

CREATE INDEX idx_signal_symbol_ts
  ON signal(symbol, timestamp DESC);

CREATE INDEX idx_candle_symbol_tf_ts
  ON candle(symbol, timeframe, timestamp DESC);

CREATE INDEX idx_order_account_status
  ON order(account_id, status);
```

**Particionamento:** Candles por timeframe (3 tabelas separadas)

---

## 🔐 Integridade Referencial

| FK | Tabela | Referência | Delete | Update |
|----|--------|-----------|--------|--------|
| order.account_id | order | account | RESTRICT | CASCADE |
| order.position_id | order | position | SET NULL | CASCADE |
| position.account_id | position | account | RESTRICT | CASCADE |
| trade.account_id | trade | account | RESTRICT | CASCADE |
| trade.entry_order_id | trade | order | RESTRICT | CASCADE |
| trade.exit_order_id | trade | order | RESTRICT | CASCADE |
| signal.trade_id | signal | trade | SET NULL | CASCADE |

---

## 📍 Mapeamento: Esquema → Regras de Negócio

| Entidade | Regras Mapeadas |
|----------|---------|
| Account | R2 (capital mínimo), R5 (drawdown) |
| Position | R1, R3, R4, R6, R7 |
| Order | R3, R4, R7, R8 |
| Trade | R8, R9, R10, R14 |
| Signal | R10, R11 |
| Performance | R5, R13, R14, R15 |

---

## 🚀 Histórico de Mudanças

| Data | Task | Mudança | Status |
|------|------|---------|--------|
| 20 FEV | TASK-011 | Adicionado `candle` (Parquet snapshot) | ✅ |
| 22 FEV | TASK-001 | Consolidação: 7 docs → 1 BACKLOG | ✅ |
| 28 FEV | Issue #67 | Data strategy: 4h candles, 1Y histórico | ✅ |
| 01 MAR | Issue #64 | Adicionado `notification` (Telegram) | ✅ |
| 07 MAR | DOCS | Criada MODELAGEM_DE_DADOS.md | ✅ |

---

## 📚 Referências

- [C4_MODEL.md](C4_MODEL.md) — Arquitetura (nível 2: Containers de dados)
- [ADR_INDEX.md](ADR_INDEX.md) — ADR-002 (Dual Cache Strategy)
- [DIAGRAMAS.md](DIAGRAMAS.md) — ERD (seção 2)
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) — Mapeamentos R1-R15

---

## 🚀 Próximas Melhorias Documentadas

- [ ] Adicionar JSON schema para `signal` e `performance` APIs
- [ ] Documentar callbacks de event listeners (ordem filled)
- [ ] Adicionar exemplos de queries de análise (por símbolos, por dia)
