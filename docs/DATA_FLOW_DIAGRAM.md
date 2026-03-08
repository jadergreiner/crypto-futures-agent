# Fluxo de Dados - Ciclo Operacional do Agente

## Visão Geral

O agente executa um ciclo contínuo (~1-2 por minuto) de monitoramento
de posições e tomada de decisões. Cada ciclo escreve em múltiplas
tabelas, construindo trilha de auditoria completa.

## Diagrama de Ciclo Operacional

```
┌─────────────────────────────────────────────────────────────┐
│          CICLO DO AGENTE (a cada 1-2 min)                  │
└─────────────────────────────────────────────────────────────┘

[1. Buscar Dados de Mercado]
  ├─ Binance API (position_monitor.py)
  │  └─ Posições abertas, preço de marcação, indicadores
  ├─ INSERT/UPDATE: ohlcv_h1, ohlcv_h4
  └─ INSERT: indicadores_tecnico, sentimento_mercado

[2. Analisar Posição]
  ├─ READ: trade_log (histórico)
  ├─ Calcular: RSI, EMA, MACD, SMC
  └─ INSERT: smc_market_structure

[3. Inserir Snapshot]
  └─ INSERT position_snapshots
    (Todos dados + contexto de decisão para RL)

[4. Tomar Decisão]
  ├─ decision_logic.evaluate_position()
  │  └─ Retorna: HOLD, CLOSE, REDUCE_50
  └─ UPDATE position_snapshots: agent_action, confidence

[5. Executar Decisão]
  ├─ IF agent_action == HOLD: SKIP
  ├─ ELSE: order_executor.execute()
  │  ├─ INSERT execution_log (antes do pedido)
  │  ├─ Enviar MARKET order à Binance
  │  └─ UPDATE execution_log (fill_price, reason)
  └─ INSERT execution_log (executed=1 ou 0)

[6. Monitorar Fechamento]
  ├─ monitor_positions.py (a cada ~10s)
  │  ├─ Detecta mudanças em Binance
  │  ├─ Se timestamp_saida = NULL e posição fechada:
  │  │  └─ Calcular PnL, atualizar trade_log
  │  └─ UPDATE trade_log: timestamp_saida, pnl_usdt
  └─ Position marcada como FECHADA

[7. Auditoria e Relatórios]
  └─ scripts/audit_24h_operations.py (sob demanda)
    ├─ READ: trade_log, execution_log
    ├─ AGREGAR: PnL, taxa de vitória, riscos
    └─ EXPORTAR: JSON + CSV
```

## Fluxo por Tabela

### trade_log - Fluxo Completo

```
INSERT (Entrada):
  timestamp_entrada = AGORA
  entry_price = Binance mark_price
  stop_loss, take_profit = Decisão do agente
  symbol, direcao, leverage, margin_type
       ↓
HOLD (Posição aberta):
  Trade existe em Binance
  Position updated em cada ciclo
  timestamp_saida = NULL
       ↓
UPDATE (Saída):
  timestamp_saida = Quando fechada
  exit_price = Fill price
  pnl_usdt, pnl_pct = Calculados
  motivo_saida = "SL_HIT", "TP_HIT", "MANUAL"
       ↓
READ (Auditoria):
  audit_trail.py: Reconstruir histórico PnL
  RL training: Extrair sinal de recompensa
```

### execution_log - Fluxo de Execução

```
INSERT (Antes do envio):
  timestamp = AGORA
  action = "OPEN", "CLOSE", "REDUCE_50"
  executed = 0 (assumptions)
       ↓
BINANCE RESPONSE:
  Ordem aceita ou rejeitada
  Se preenchida: fill_price, fill_qty
       ↓
UPDATE (Após resposta):
  executed = 1 ou 0
  fill_price, reason (se bloqueado)
       ↓
READ (Auditoria):
  risk_gate.py: COUNT execuções bem sucedidas (hoje)
  scripts: Analisar padrões de execução
  forensics: Debug por que trades não fecharam
```

### position_snapshots - Histórico de Decisões

```
INSERT (A cada ciclo):
  timestamp = AGORA
  Todos dados da posição (mark_price, etc)
  Todos indicadores (RSI, EMA, MACD)
  agent_action = Ação decidida
  decision_confidence, risk_score
  reward_calculated = NULL (calculado depois)
       ↓
UPDATE (Opcional, após fechamento):
  reward_calculated = Recompensa real (RL)
  outcome_label = "WIN", "LOSS", "NEUTRAL"
       ↓
READ (RL Training & Análise):
  RL training: Extrair tuplas (state, action, reward)
  Auditoria: Analisar qualidade de decisões
```

### TASK-005 v2 - Fluxo de Treinamento/Validação RL

```
[A. Dataset]
  data/trades_history_generator.py
    ├─ Gera >=500 trades sintéticos
    └─ Valida baseline (win_rate, profit_factor, balance LONG/SHORT)
         ↓
[B. Ambiente RL]
  agent/rl/training_env.py
    ├─ step() retorna shaped_reward (treino PPO)
    └─ info expõe raw_pnl/equity/closed_trade (métricas reais)
         ↓
[C. Métricas Unificadas]
  agent/rl/metrics_utils.py
    ├─ Sharpe com volatility floor
    ├─ Profit Factor com cap/sanity
    └─ Drawdown/WinRate/Consecutive losses
         ↓
[D. Treino]
  agent/rl/training_loop.py
    ├─ Checkpoints
    ├─ Artefatos: vol_floor, num_trades_evaluated, metric_sanity_passed
    └─ stop_reason explícito
         ↓
[E. Validação Final]
  agent/rl/final_validation.py
    └─ Mesmo cálculo de métricas do treino (single source of truth)
```

**Regra operacional v2:** `shaped_reward` nunca é usado como métrica de GO/NO-GO.

## Ponto Crítico: Sincronização de Fechamento

Este é o ponto onde execution_log e trade_log devem sincronizar:

```
Execução de Ordem (execution_log):
  action="CLOSE", executed=1, fill_price=100.50
       ↓↓↓ [SINCRONIZAÇÃO CRÍTICA] ↓↓↓
  ⏱️  Buffer: Monitor aguarda detectar em Binance
       ↓
Atualização de Fechamento (trade_log):
  timestamp_saida = timestamp da execução
  exit_price = fill_price
  pnl_usdt = (exit_price - entry_price) * qty

  ⚠️ SE ESTA SINCRONIZAÇÃO NÃO OCORRER:
     - trade_log.timestamp_saida fica NULL
     - Trade aparece como "ABETO" em auditorias
     - PnL fica 0 (dados faltando)
     - INCONSISTÊNCIA CRÍTICA!
```

**Responsável:** scripts/monitor_positions.py
**Gatilho:** Posição não mais em resposta Binance (WebSocket)
**Verificação:** trade_log deve atualizar em < 60s após execution_log

### Exemplo de Ciclo Completo

```
T=00:00 - Ciclo #1
  ├─ Busca dados Binance: OGUSDT em 123.45
  ├─ INSERT position_snapshot (id=501, agent_action=HOLD)
  └─ Decisão: HOLD (confiança 0.78)

T=00:01 - Ciclo #2
  ├─ Busca dados Binance: OGUSDT em 123.50
  ├─ INSERT position_snapshot (id=502, agent_action=CLOSE)
  ├─ Decisão: CLOSE (preço atingiu TP)
  └─ INSERT execution_log (id=1000, action=CLOSE, executed=0)

T=00:01:05 - Resposta Binance
  ├─ Ordem CLOSE preenchida em 123.49
  └─ UPDATE execution_log (id=1000, executed=1, fill_price=123.49)

T=00:01:15 - Monitor Detecta
  ├─ monitor_positions.py vê posição fechada
  ├─ Calcula PnL = (123.49 - entry) * qty
  └─ UPDATE trade_log (timestamp_saida, exit_price, pnl_usdt)

T=00:05 - Auditoria
  └─ audit_24h_operations.py lê trade_log completo
    ├─ PnL = -$45.20 (-0.5%)
    └─ Duração = 5 minutos
```

---

**Última atualização:** 2026-03-07
**Responsável:** Architecture Lead
**Frequência Ciclo:** 1-2 minutos
**Monitor Intervalo:** ~10 segundos
