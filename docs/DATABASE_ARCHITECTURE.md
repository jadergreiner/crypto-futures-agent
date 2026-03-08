# Arquitetura de Database

## Fonte Única e Verdadeira: crypto_futures.db

### Visão Geral

- **Localização:** `db/crypto_futures.db`
- **Tipo:** SQLite 3
- **Responsabilidade Principal:** Operações de trading, trilha de auditoria,
  histórico de decisões do agente
- **Status Consolidação:** 2026-03-07 (crypto_agent.db descontinuado)

### Esquema de Alto Nível

#### Tabelas Principais de Trading

| Tabela | Propósito | PK | Atualizado por |
|--------|-----------|-----|-----------------|
| trade_log | Ciclo vida da posição | trade_id | position_monitor.py |
| execution_log | Auditoria de execução | id | order_executor.py |
| position_snapshots | Histórico de decisões | id | position_monitor.py |
| trade_signals | Identificação de sinais | id | signal_generator.py |

#### Tabelas de Dados de Mercado

| Tabela | Propósito | Fonte | TTL |
|--------|-----------|-------|-----|
| ohlcv_h1, h4, d1 | Dados OHLCV | Binance API | Real-time |
| indicadores_tecnico | Indicadores técnicos | position_monitor.py | Por ciclo |
| sentimento_mercado | Sentimento de mercado | Binance API | Por ciclo |
| smc_* | Estrutura SMC | position_monitor.py | Por ciclo |

### Esquema Detalhado das Tabelas

#### trade_log

Registro completo de cada posição de trading, desde abertura até
fechamento com cálculo de PnL.

**Responsabilidade:** monitoring/position_monitor.py
**Padrão Acesso:** INSERT (entrada) + UPDATE (saída)
**Lido por:** audit_trail.py, scripts/audit_24h_operations.py, RL training

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| trade_id | INT PK | ID único |
| timestamp_entrada | INT | Unix ms UTC (entrada) |
| timestamp_saida | INT | Unix ms UTC (saída, NULL se aberto) |
| symbol | TEXT | Ex: "OGUSDT" |
| direcao | TEXT | "LONG" ou "SHORT" |
| entry_price | REAL | Preço de entrada |
| exit_price | REAL | Preço de saída (NULL se aberto) |
| stop_loss | REAL | Nível de stop loss |
| take_profit | REAL | Nível de take profit |
| pnl_usdt | REAL | PnL em USD (NULL se aberto) |
| pnl_pct | REAL | PnL em percentual (NULL se aberto) |
| leverage | INT | Alavancagem utilizada |
| liquidation_price | REAL | Preço de liquidação |
| motivo_saida | TEXT | "SL_HIT", "TP_HIT", "MANUAL_CLOSE" |
| binance_order_id | TEXT | ID do pedido Binance |
| binance_sl_order_id | TEXT | ID do SL em Binance |
| binance_tp_order_id | TEXT | ID do TP em Binance |

#### execution_log

Registro de cada tentativa de execução (abertura, fechamento, proteção).

**Responsabilidade:** execution/order_executor.py
**Padrão Acesso:** INSERT (após tentativa)
**Lido por:** audit_trail.py, risk_gate.py, scripts

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INT PK | ID único |
| timestamp | INT | Unix ms UTC |
| symbol | TEXT | Símbolo do ativo |
| action | TEXT | "OPEN", "CLOSE", "REDUCE_50", "SET_SL" |
| executed | INT | 1 (sucesso) ou 0 (bloqueado) |
| mode | TEXT | "paper" ou "live" |
| reason | TEXT | Motivo se bloqueado |
| order_id | TEXT | ID Binance se executado |
| fill_price | REAL | Preço do preenchimento |
| fill_quantity | REAL | Quantidade preenchida |

#### position_snapshots

Snapshot de cada decisão do agente, incluindo estado completo da posição,
indicadores técnicos e decisão tomada. Usado para treinamento de RL.

**Responsabilidade:** monitoring/position_monitor.py
**Padrão Acesso:** INSERT (a cada ciclo ~1-2 por minuto)
**Lido por:** RL training, audits, análises

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | INT PK | ID único |
| timestamp | INT | Unix ms UTC |
| symbol | TEXT | Símbolo do ativo |
| direction | TEXT | "LONG" ou "SHORT" |
| mark_price | REAL | Preço de marcação |
| rsi_14 | REAL | RSI(14) neste momento |
| ema_17, ema_34, ema_72, ema_144 | REAL | EMAs |
| agent_action | TEXT | Ação decidida |
| decision_confidence | REAL | Confiança 0.0-1.0 |
| risk_score | REAL | Pontuação de risco |
| reward_calculated | REAL | Recompensa (RL) |

### Mapa de Acesso Módulo → Database

| Módulo | Tabelas | Tipo | Frequência |
|--------|---------|------|-----------|
| monitoring/position_monitor.py | trade_log, execution_log | RW | A cada ciclo |
| execution/order_executor.py | execution_log, trade_log | W, U | Por execução |
| risk/risk_gate.py | execution_log | R | Por decisão |
| logs/audit_trail.py | trade_log, execution_log | R | Sob demanda |
| scripts/audit_24h_operations.py | All | R | Sob demanda |

### Banco Descontinuado

- **crypto_agent.db:** Consolidado em 2026-03-07
  - Antigas tabelas: execution_log (128 registros), trade_signals (11),
    position_snapshots (13.756)
  - Status: Arquivo morto (leitura apenas)

### Politica de Retenção

| Tabela | Retenção | Estratégia |
|--------|----------|-----------|
| trade_log | Permanente | Snapshot mensal em Parquet |
| execution_log | 90 dias online | Particionado por data |
| position_snapshots | 7 dias online | Archive semanal |
| trade_signals | 30 dias online | Archive por símbolo |

### Validação de Integridade

Execute diariamente:

```bash
sqlite3 db/crypto_futures.db "PRAGMA integrity_check;"
```

Para relatório completo:

```bash
python scripts/hooks/validate_integrity_on_backlog_task.py
```

### Backup e Recuperação

```bash
# Backup diário
sqlite3 db/crypto_futures.db \
  ".backup db/crypto_futures.db.backup_$(date +%Y%m%d)"

# Recuperação
cp db/crypto_futures.db.backup_YYYYMMDD db/crypto_futures.db
```

### Monitoramento

- **Tamanho:** Alerta se > 500 MB
- **Orfãos:** Verificar execuções sem trade correspondente
- **Trades Obsoletos:** Alerta se > 30 dias aberto
- **Staleness:** Alerta se nenhum trade_log em 24h

### Artefatos RL (TASK-005 v2)

Além do SQLite, o pipeline RL persiste artefatos JSON operacionais:

- `logs/ppo_task005/training_log.json`
  - checkpoint metrics com fórmula unificada
  - campos: `vol_floor`, `num_trades_evaluated`, `metric_sanity_passed`, `stop_reason`

- `validation/task005_validation_results.json`
  - validação final baseada em `raw_pnl/equity` (não em shaped reward)

- `validation/task005_phase3_final_report.json`
  - decisão GO/NO-GO + aprovação por personas

**Nota:** Estes artefatos não substituem o banco transacional; funcionam como trilha de auditoria do ciclo de treino.

---

**Última atualização:** 2026-03-07 (sync TASK-005 v2)
**Responsável:** Database Architecture Board
**Status:** Em produção (SINGLE SOURCE OF TRUTH)
