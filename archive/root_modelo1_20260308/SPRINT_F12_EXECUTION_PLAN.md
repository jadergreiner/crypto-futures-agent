# 🚀 SPRINT F-12 EXECUTION PLAN — Agentes Autônomos

**Data**: 20/02/2026 22:00 UTC
**Status**: KICKOFF
**Personas**: 2 agentes autônomos paralelos

---

## 👥 ESTRUTURA DE TRABALHO

### **PERSONA 1: ESP-ENG (Engenheiro Senior)**
- **Responsável**: Arquitetura, código production, performance, testes
- **Track**: F-12a, F-12b, F-12c, F-12d, F-12e
- **Deliverables**: BacktestEnvironment, Cache, StateMachine, Reporter, Tests

### **PERSONA 2: ESP-ML (Especialista ML)**
- **Responsável**: Métricas, reward validation, dados, walk-forward
- **Track**: Data pipeline, metrics engine, walk-forward design, reward review
- **Deliverables**: Dados prontos, métricas validadas, F-12f, Metrics engine

---

## ⚠️ ESTADO ATUAL (PRE-CHECK)

| Componente | Status | Ação |
|-----------|--------|------|
| BacktestEnvironment | ⚠️ 60% (duplicações) | **REFACTOR** |
| Cache Parquet | ❌ 0% | **START** |
| TradeStateMachine | ❌ 0% | **START** |
| Reporter | ❌ 0% | **START** |
| Unit Tests | ❌ 10% (skeleton) | **COMPLETE** |
| Walk-Forward | ❌ 0% | **START** |
| Data Validation | ⚠️ 50% (parcial) | **COMPLETE** |
| Reward Review | 🔴 **BLOCKER** | **VALIDATE FIRST** |

---

## 🔴 BLOCKER CRÍTICO: REWARD FUNCTION

**Status**: VALIDAÇÃO NECESSÁRIA
**Ação**: ESP-ML deve validar `agent/reward.py` HOJE (segunda 20/02 antes de
começar código)

**Checklist Reward Validation**:
- [ ] `PNL_SCALE = 10.0` → Apropriado para backtesting?
- [ ] `R_BONUS_THRESHOLD_HIGH = 3.0` → Atingível com dados reais?
- [ ] `HOLD_BASE_BONUS = 0.05` → Direciona para "deixar lucros correr"?
- [ ] `INVALID_ACTION_PENALTY = -0.5` → Suficiente para desencorajar ações
ruins?
- [ ] Comparar histórico v0.2 trades vs. estes componentes

**Aprovação**: "✅ Reward OK para backtesting" OU "🔴 Precisa ajuste"

---

## 📋 TAREFAS DETALHADAS

### **TERÇA 21/02 — TURNO 1 (08:00-16:00 UTC)**

#### **ESP-ENG: F-12a Refactor + F-12b Skeleton**

**Tarefa 1: Refactor BacktestEnvironment (4h)**

```python
# OBJETIVO: Limpar duplicações, deixar estrutura clara
# INPUT: backtest/backtest_environment.py (atual 344 linha com lixo)
# OUTPUT: backtest_environment.py CLEAN (150-200 linhas)
# ESTRUTURA:
#   ├─ Class BacktestEnvironment (herda CryptoFuturesEnv)
#   ├─ __init__() — inicialização determinística
#   ├─ reset() — reset com start_step determinístico
#   ├─ step() — reutiliza super().step() completamente (1 linha!)
#   ├─ render() — debug output
#   └─ get_backtest_summary() — sumário básico

# CHECKLIST:
# [ ] Remover duplicações de métodos (step, reset)
# [ ] Herança: reutiliza 99% de CryptoFuturesEnv
# [ ] Determinismo: seed=42 padrão, ignorar randomização
# [ ] Imports limpos
# [ ] Testes básicos de init/reset/step
```bash

**Tarefa 2: F-12b Cache Parquet Skeleton (3h)**

```python
# OBJETIVO: Estrutura para 3-tier data pipeline
# INPUT: data/database.py (SQLite) + histórico Binance
# OUTPUT: backtest/data_cache.py (novo arquivo)

# ESTRUTURA:
#   ├─ Class ParquetCache
#   │  ├─ __init__(db_path, cache_dir)
#   │  ├─ load_ohlcv_for_symbol(symbol, start_date, end_date)
#   │  │  └─ SQLite → Pandas → Parquet (cache)
#   │  ├─ get_cached_data(symbol) — retorna np.ndarray
#   │  └─ validate_candle_continuity() — check gaps
#   └─ Helper functions
#      ├─ timestamp_to_parquet_path()
#      └─ merge_timeframes() — combina H1, H4, D1 se necessário

# CHECKLIST:
# [ ] Skeleton com métodos assinados (docstrings)
# [ ] Imports: pandas, pyarrow/parquet, sqlite3
# [ ] Error handling para dados faltantes
# [ ] TODO comments para implementação ESP-ML
```bash

**Tarefa 3: Checkpoint 16:00 UTC**
- Code review F-12a refactor
- Design review F-12b skeleton
- Standup com ESP-ML

#### **ESP-ML: Data Validation + Reward Review**

**Tarefa 1: Validar OHLCV Integridade (3h)**

```python
# OBJETIVO: Confirmar que dados históricos no DB estão OK
# INPUT: db/crypto_futures.db (SQLite) — tables ohlcv_h4, ohlcv_d1
# OUTPUT: validation_report_OHLCV.md

# CHECKLIST:
# [ ] Para cada symbol em config/symbols.py:
#     ├─ Query: COUNT(*) das candles H4 últimos 12 meses
#     ├─ Validar: sem gaps > 4h (H4 continuous)
#     ├─ Validar: OHLC sanity (high >= max(open,close), low <= min(open,close))
#     ├─ Validar: volume > 0
#     └─ Registrar em report: "✅ BTCUSDT: 2350 candles (12 months, 0 gaps)"
# [ ] Min threshold: 300 candles = ~3 months. Se < 300 → ⚠️ Warning
# [ ] Se > 1 symbol < 300 → 🔴 BLOCKER (historico insuficiente)
```bash

**Tarefa 2: Reward Function Review (2h)**

```python
# OBJETIVO: Validar agent/reward.py está pronto para backtesting
# INPUT: agent/reward.py
# OUTPUT: "✅ Reward OK" OR "🔴 Needs fix"

# CHECKLIST:
# [ ] Ler agent/reward.py completamente
# [ ] Validar 3 componentes:
#     1. r_pnl: Escala apropriada? (PNL_SCALE = 10.0)
#     2. r_hold_bonus: Incentiva "deixar lucros" assimetricamente?
#     3. r_invalid_action: Penalidade suficiente?
# [ ] Comparar vs. histórico v0.2 trades (se existe)
# [ ] Validar: nenhuma ação está com reward > REWARD_CLIP
# [ ] Assinar OFF: "✅ Reward validado, pronto para backtest"
```json

**Tarefa 3: Standup 16:00 UTC**
- Compartilhar validation_report_OHLCV.md
- Compartilhar Reward review sign-off
- Sinalizar bloqueadores (se houver)

---

### **QUARTA 22/02 — TURNO 2 (16:00-23:59 UTC)**

#### **ESP-ENG: F-12c + F-12d + F-12e skeleton**

**Tarefa 1: F-12c TradeStateMachine (5h)**

```python
# ARQUIVO: backtest/trade_state_machine.py (NOVO)
# OBJETIVO: State machine que rastreia posições + calcula PnL com fees

# ESTRUCTURA:
#   ├─ STATES: IDLE, LONG, SHORT, CLOSING
#   ├─ Class TradeStateMachine
#   │  ├─ __init__()
#   │  ├─ open_position(direction, entry_price, size, sl, tp) → LONG/SHORT
#   │  ├─ check_exit_conditions(current_price, ohlc) → Bool (SL/TP hit?)
#   │  ├─ close_position(exit_price, reason) → (pnl, r_multiple, fees)
#   │  ├─ get_current_state() → Dict (IDLE/LONG/SHORT + metrics)
#   │  └─ get_trade_history() → List[Dict]
#   └─ Helper methods
#      ├─ _calculate_pnl(direction, entry, exit, size)
#      ├─ _calculate_r_multiple(pnl, initial_risk)
#      ├─ _apply_fees(size, exit_price) → fee_amount
#      └─ _check_consecutive_losses() → int

# CHECKLIST:
# [ ] State enum (IDLE, LONG, SHORT)
# [ ] Position dict: {direction, entry_price, size, initial_stop, take_profit}
# [ ] Fee calculation: 0.04% maker + 0.04% taker por lado
# [ ] PnL com fees = (gross_pnl - entry_fees - exit_fees)
# [ ] Consecutive losses: contagem acumulativa
# [ ] Unit test draft: test_pnl_long_position, test_fees_calculation
```bash

**Tarefa 2: F-12d Reporter — Skeleton (2h)**

```python
# ARQUIVO: backtest/reporter.py (NOVO)
# OBJETIVO: Gerar TXT + JSON output

# STRUCTURE:
#   ├─ Class BacktestReporter
#   │  ├─ __init__(backtest_results)
#   │  ├─ generate_text_report() → str (legível)
#   │  ├─ generate_json_report() → Dict (estruturado)
#   │  ├─ save_reports(output_dir) → (txt_path, json_path)
#   │  └─ validate_against_thresholds() → Bool
#   └─ Helper methods
#      ├─ _format_metrics_table()
#      ├─ _format_trades_table()
#      └─ _render_status_emoji()

# EXEMPLO TXT OUTPUT:
# ╔════════════════════════════════════════════════════════════╗
# ║        BACKTEST REPORT: BTCUSDT (2025-01-01 ~ 2026-02-20)  ║
# ╚════════════════════════════════════════════════════════════╝
#
# PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────
# Sharpe Ratio:               1.24  ✅ (target ≥ 0.80)
# Max Drawdown:             12.3%  ✅ (target ≤ 12%)
# Win Rate:                  48%   ✅ (target ≥ 45%)
# Profit Factor:             1.8   ✅ (target ≥ 1.5)
# Consecutive Losses:         4    ✅ (target ≤ 5)
#
# EQUITY SUMMARY
# ─────────────────────────────────────────────────────────────
# Initial Capital:      $10,000
# Final Capital:        $12,450
# Total Return:          +24.5%
# Peak Capital:         $15,200
#
# TRADES SUMMARY
# ─────────────────────────────────────────────────────────────
# Total Trades:              127
# Winning Trades:             61 (48.0%)
# Losing Trades:              66 (52.0%)
# Avg Win:                 $315
# Avg Loss:               -$245
# Payoff Ratio:            1.29x
#
# ✅ APPROVED FOR PAPER TRADING

# CHECKLIST:
# [ ] Métodos assinados
# [ ] Template TXT com emojis + grid
# [ ] JSON com estrutura validável
# [ ] validate_against_thresholds() → True/False
```bash

**Tarefa 3: F-12e Unit Tests Skeleton (1h)**

```python
# ARQUIVO: tests/test_backtester.py (NOVO)
# OBJETIVO: 8 testes obrigatórios

# TESTES:
# [ ] test_determinism_same_seed_same_output
# [ ] test_backtest_env_reset_deterministic
# [ ] test_position_open_long
# [ ] test_position_open_short
# [ ] test_pnl_calculation_with_fees
# [ ] test_sl_tp_triggers_accurate
# [ ] test_consecutive_losses_count
# [ ] test_reporter_json_valid

# Cada test() com:
#   ├─ Setup fixture: BacktestEnvironment + dados dummy
#   ├─ Execute action
#   └─ Assert result

# CHECKLIST:
# [ ] Imports OK (pytest, numpy, pandas)
# [ ] Fixtures criadas
# [ ] Test signatures OK (def test_xxx)
# [ ] Cada test ~10-20 linhas
```bash

#### **ESP-ML: Metrics Engine + Walk-Forward Skeleton**

**Tarefa 1: Implemetar Metrics Engine (4h)**

```python
# ARQUIVO: backtest/metrics.py (NOVO)
# OBJETIVO: Calcular 6 métricas de performance

# MÉTRICAS OBRIGATÓRIAS:
#   1. Sharpe Ratio = (mean_return - risk_free) / std_return
#   2. Max Drawdown = max(peak - current) / peak
#   3. Win Rate = winning_trades / total_trades
#   4. Profit Factor = sum(wins) / abs(sum(losses))
#   5. Consecutive Losses = max sequence de perdas
#   6. (Bonus) Recovery Factor = total_pnl / max_drawdown

# CLASS MetricsCalculator:
#   ├─ __init__(trade_history, daily_returns)
#   ├─ calculate_sharpe(risk_free_rate=0.0) → float
#   ├─ calculate_max_drawdown() → float
#   ├─ calculate_win_rate() → float
#   ├─ calculate_profit_factor() → float
#   ├─ calculate_consecutive_losses() → int
#   ├─ calculate_all() → Dict[str, float]
#   └─ validate(metrics) → Bool (vs. thresholds)

# THRESHOLDS:
#   sharpe >= 0.80
#   max_dd <= 0.12
#   win_rate >= 0.45
#   profit_factor >= 1.5
#   consec_losses <= 5

# CHECKLIST:
# [ ] Numpy vectorization (não loops)
# [ ] Tratamento de edge cases (0 trades, etc)
# [ ] Docstrings com fórmulas
# [ ] Helper functions para daily returns
```bash

**Tarefa 2: F-12f Walk-Forward Skeleton (3h)**

```python
# ARQUIVO: backtest/walk_forward.py (NOVO)
# OBJETIVO: Validar que modelo generaliza entre períodos

# STRATEGY:
#   Particionar dados históricos em janelas:
#   ├─ Window 1: Train 2025-01-01~2025-02-28 | Test 2025-03-01~2025-03-15
#   ├─ Window 2: Train 2025-02-01~2025-03-31 | Test 2025-04-01~2025-04-15
#   ├─ Window 3: Train 2025-03-01~2025-04-30 | Test 2025-05-01~2025-05-15
#   └─ Window 4: Train 2025-04-01~2025-05-31 | Test 2025-06-01~2025-06-15
#
#   Para cada window:
#   ├─ Load BacktestEnvironment(historical_data[train_period])
#   ├─ Run backtest → get metrics
#   ├─ Comparar: test_metrics vs. train_metrics
#   └─ Valida: Sharpe, DD estáveis ±10%

# CLASS WalkForwardAnalyzer:
#   ├─ __init__(total_data, num_windows=4, train_size_pct=0.6)
#   ├─ split_windows() → List[Dict{train_dates, test_dates}]
#   ├─ run_walk_forward(model_path) → List[metrics_per_window]
#   ├─ analyze_stability() → Bool (±10% variation)
#   └─ generate_report() → str

# OUTPUT ESPERADO:
# Walk-Forward Results:
# ─────────────────────────────────────────
# Window  | Train Sharpe | Test Sharpe | Δ%  | Status
# ─────────────────────────────────────────
# 1       | 1.15         | 1.10        | -4%  | ✅ OK
# 2       | 1.08         | 1.04        | -4%  | ✅ OK
# 3       | 1.20         | 1.18        | -2%  | ✅ OK
# 4       | 1.12         | 1.09        | -3%  | ✅ OK
# ─────────────────────────────────────────
# Average Sharpe (all windows): 1.10 ±0.06
# ✅ STABLE (variation < 10%)

# CHECKLIST:
# [ ] Window partition logic
# [ ] Data slicing por data (start_date, end_date)
# [ ] Loop através de windows
# [ ] Cálculo de variation %
# [ ] Report generation
```bash

**Tarefa 3: Standup 22:00 UTC**
- Compartilhar código F-12c, F-12d, F-12e skeletons
- Compartilhar código metrics.py + walk_forward.py skeletons
- Sinalizar pontos de integração com ESP-ENG

---

### **QUINTA 23/02 — VALIDAÇÃO FINAL (08:00-16:00 UTC)**

#### **ESP-ENG: Completar Tests + Manual Validation**

```text
08:00-12:00 (4h):
  ├─ Completar F-12e (8 testes)
  ├─ Run: pytest -v tests/test_backtester.py → 8/8 PASSED
  ├─ Manual backtest: BTCUSDT vs. Excel (1 trade calculado manualmente)
  └─ 12:00 Checkpoint: Todos os testes passam

12:00-16:00 (4h):
  ├─ Integração: BacktestEnvironment + TradeStateMachine + Reporter
  ├─ Manual backtest 3 símbolos: BTC, ETH, SOL (10 candles cada)
  ├─ Validar output TXT + JSON
  └─ 16:00 GREEN LIGHT: "Arquitetura OK, ready para métricas"
```json

#### **ESP-ML: Walk-Forward Validation + Final Sign-Off**

```text
08:00-12:00 (4h):
  ├─ Completar metrics.py
  ├─ Teste manual: 1 trade, Sharpe = manualmente
  ├─ Walk-Forward skeleton: 1 window (BTC, jan período)
  └─ 12:00 Checkpoint: Métricas OK, Walk-Forward engine ready

12:00-16:00 (4h):
  ├─ Run walk-forward BTC completo (4 windows)
  ├─ Validar: Sharpe variation < 10%
  ├─ Gerar rapport walk-forward
  └─ 16:00 GREEN LIGHT: "ML validation OK, ready para release"
```json

---

## 📊 MATRIZ DE DEPENDÊNCIAS

```text
                ESP-ENG Track          |          ESP-ML Track
                                       |
F-12a (RefactBE) ──┐                  |
F-12b (Cache) ─────┼─→ Input data     |
                   |   pipeline ◄─────┼── Data Validation
F-12c (StateMach)  |                  |
F-12d (Reporter) ──┼─→ Metrics calc ◄─┼── Metrics Engine
                   |                  |
F-12e (Tests) ─────┼─→ Integration ◄──┼── Walk-Forward
                   |                  |
Deliverable:      |                  Deliverable:
- Code clean      |                  - Metrics validated
- Tests OK        |                  - Walk-Forward engine
- Manual OK       |                  - Report: "Generalization ✅"
```json

---

## ✅ DEFINIÇÃO DE PRONTO (DoD)

### ESP-ENG DoD:

- [ ] BacktestEnvironment refactored (clean, reutiliza 99% super.step())
- [ ] Cache Parquet skeleton (métodos assinados, TODO comments)
- [ ] TradeStateMachine completo (fees, PnL, consecutive losses)
- [ ] Reporter skeleton (TXT + JSON templates)
- [ ] 8 unit tests escritos e **TODOS PASSANDO**
- [ ] Manual backtest BTCUSDT: 1 trade validado vs. Excel
- [ ] Manual backtest 3 símbolos: BTC, ETH, SOL output OK
- [ ] Código comentado em português
- [ ] Zero erros ao rodar: `pytest -v tests/test_backtester.py`

### ESP-ML DoD:

- [ ] OHLCV validation report: zero gaps, >300 candles/symbol
- [ ] Reward function review: "✅ OK for backtesting"
- [ ] Metrics engine completo: Sharpe, DD, WR, PF, CL calculadas corretamente
- [ ] 1 manual test: 1 trade Sharpe = validado vs. `(return - 0) / std`
- [ ] Walk-Forward engine implementado: 4 windows, Sharpe stable ±10%
- [ ] Walk-Forward report para BTCUSDT: "Generalization ✅"
- [ ] Código comentado em português
- [ ] Integração com ESP-ENG code testada

---

## 🎯 CRITÉRIO DE SUCESSO

**Release v0.4 GO IFF:**
- ✅ 8/8 tests passing
- ✅ Sharpe ≥ 0.80 em backtest (target 1.20)
- ✅ Max DD ≤ 12% em backtest (warning > 10%)
- ✅ Win Rate ≥ 45%
- ✅ Profit Factor ≥ 1.5
- ✅ Consecutive Losses ≤ 5
- ✅ Walk-Forward Sharpe variation < 10%
- ✅ Code review + merge-ready
- ✅ Documentação sincronizada (`docs/SYNCHRONIZATION.md`)

**Release v0.4 NO-GO IF:**
- ❌ Qualquer teste falhando
- ❌ Sharpe < 0.60 (signala problem sistemático)
- ❌ Walk-Forward Sharpe variation > 20% (overfitting)
- ❌ Code review bloqueado

---

## 📞 ESCALAÇÃO

**Quando contatar PO/Head Finanças**:
1. Reward function precisa mudança (impacta timeline)
2. OHLCV histórico < 300 candles para symbol (dados insuficientes)
3. Sharpe final < 0.5 (problema systemático no modelo)
4. Walk-Forward failure (overfitting detectado)

**Quando contatar CTO**:
1. Performance backtest > 300s (otimização numpy)
2. Code review bloqueador (arquitetura debate)
3. Integração ESP-ENG ↔ ESP-ML issue

---

**Status**: ✅ PLAN READY FOR EXECUTION
**Start Date**: Segunda 20/02 22:00 UTC
**Target Release**: Quinta 23/02 16:00 UTC
**Buffer**: Sexta 24/02 (plano B)

🚀 **READY TO GO**
