# 📊 Módulo de Backtesting — Crypto Futures Agent

**Versão:** 1.0.0 (S2-3 Gates 2+3 ✅ Complete)
**Última atualização:** 23 FEV 2026 01:30 UTC ([SYNC] Gate 4 Documentation)
**Autor:** Squad S2-3 Multidisciplinar (Arch #6, Audit #8, Data #11, Quality #12, Doc Advocate #17, The Brain #3)
**Status:** 🟢 Production Ready — Gates 2+3 Approved

---

## 📖 Índice

1. [Visão Geral](#visão-geral)
2. [🚀 S2-3 Squad Kickoff Status](#-s2-3-squad-kickoff-status)
3. [Instalação & Setup](#instalação--setup)
4. [Como Usar](#como-usar)
5. [Interpretando Resultados](#interpretando-resultados)
6. [Troubleshooting](#troubleshooting)
7. [Referência de API](#referência-de-api)

---

## 🎯 Visão Geral

O **Backtesting Engine** simula operações de trading usando dados históricos reais
de 60 símbolos crypto (BTC, ETH, ALT coins) da Binance Futures.

**Características principais:**
- ✅ Simulação realística com Risk Gate 1.0 (stop loss -3%)
- ✅ Cálculo de PnL realized + unrealized
- ✅ Métricas: Drawdown, Sharpe Ratio, Profit Factor, Calmar Ratio
- ✅ Walk-Forward Testing (train/validation split)
- ✅ Cache em Parquet (6+ meses histórico)
- ✅ Suporte a múltiplas estratégias

---

## 🚀 S2-3 Squad Kickoff Status

**Data:** 22 FEV 2026 14:30 UTC
**Squad:** Arch (#6), Audit (#8), Data (#11), Quality (#12), Doc Advocate (#17), The Brain (#3)
**Escopo:** 4 Gates de validação, 9h wall-time, deadline 24 FEV 18:00 UTC

### ✅ Deliverables Kickoff (22 FEV 14:30 UTC)

- ✅ [ARCH_S2_3_BACKTESTING.md](../docs/ARCH_S2_3_BACKTESTING.md) — Design + 4 Gates
- ✅ [S2_3_DELIVERABLE_SPEC.md](../docs/S2_3_DELIVERABLE_SPEC.md) — 13-item checklist
- ✅ [TEST_PLAN_S2_3.md](../docs/TEST_PLAN_S2_3.md) — 8 testes + fixtures
- ✅ Diretórios criados: `backtest/{core,data,strategies,validation,tests,logs}/`
- ✅ `__init__.py` + skeleton exports
- ✅ STATUS_ENTREGAS.md § S2-3 atualizado
- ✅ PRD.md e SYNCHRONIZATION.md alinhados ao kickoff
- ✅ SYNCHRONIZATION.md § [SYNC] kickoff registrado

### 🔄 Próximos Passos (23-24 FEV)

| Data | Squad | Task | Status |
|------|-------|------|--------|
| **23 FEV** | Arch (#6) | Implementar `core/backtest_engine.py` | ⏳ |
| **23 FEV** | Data (#11) | Implementar `data/data_provider.py` | ⏳ |
| **23 FEV** | Quality (#12) | Criar fixtures + test stubs | ⏳ |
| **23 FEV** | The Brain (#3) | Validar SMC strategy spec | ⏳ |
| **24 FEV** | All | Submeter PRs + Gates validation | ⏳ |
| **24 FEV 18:00 UTC** | Angel (#1) | Sign-off final GO/NO-GO | ⏳ |

### 📊 4 Gates de Aceite

| Gate | Owner | Critério | Docs |
|------|-------|----------|------|
| 1. Dados Históricos | Data (#11) | 60 símbolos, 6-12M, sem gaps ✅ | [Link](../docs/S2_3_DELIVERABLE_SPEC.md#gate-1-dados-históricos-) |
| 2. Engine Core | Arch (#6) | Exec, PnL, RiskGate -3% ✅ | [Link](../docs/S2_3_DELIVERABLE_SPEC.md#gate-2-engine-de-backtesting-) |
| 3. Testes | Quality (#12) | 8 PASS, coverage ≥80% ✅ | [Link](../docs/S2_3_DELIVERABLE_SPEC.md#gate-3-validação--testes-) |
| 4. Documentação | Audit (#8) | Docstrings, README, DECISIONS ✅ | [Link](../docs/S2_3_DELIVERABLE_SPEC.md#gate-4-documentação-) |

**Desbloqueios após GO:**
- 🔴 S2-1/S2-2 (SMC Strategy Implementation)
- 🔴 TASK-005 (PPO Training final validation)
- 🔴 Go-Live Operacional (Production Release)

Ref completa: [ARCH_S2_3_BACKTESTING.md](../docs/ARCH_S2_3_BACKTESTING.md)

---

## � Métricas de Desempenho — As 6 Pilares da Validação

O módulo implementa 6 métricas validadas pela indústria para decisão go/no-go trading.
Todas as 6 métricas devem passar seus respectivos gates para liberação ao live trading.

### 1️⃣ Sharpe Ratio — Retorno Ajustado por Risco (Gate: ≥ 0.80)

**O que mede:** Quanto retorno obtém por unidade de risco (volatilidade).
**Fórmula:** `(Retorno Anual - Taxa Livre de Risco) / Volatilidade`

```python
from backtest.metrics import MetricsCalculator

calc = MetricsCalculator(trade_history, initial_capital=10000)
sharpe = calc.calculate_sharpe_ratio(risk_free_rate=0.02)
# Resultado exemplo: 1.15 ✅ PASS (acima de 0.80)
```

**Interpretação:**
- Sharpe < 0.50: Risco não compensa o retorno
- Sharpe 0.80-1.00: Aceitável para trading automático
- Sharpe ≥ 1.20: Excelente (raro em crypto)

---

### 2️⃣ Max Drawdown — Maior Queda (Gate: ≤ 12%)

**O que mede:** Maior queda pico-a-vale da equity curve (drawdown máximo).
**Fórmula:** `(Pico - Vale) / Pico`

```python
max_dd = calc.calculate_max_drawdown()
# Resultado exemplo: 8.5% ✅ PASS (abaixo de 12%)
```

**Interpretação:**
- MaxDD < 5%: Muito conservador (pouco leverage)
- MaxDD 8-12%: Agressivo mas tolerável
- MaxDD > 15%: Rejeitar (risco demais)

---

### 3️⃣ Win Rate — Taxa de Vitória (Gate: ≥ 45%)

**O que mede:** Porcentagem de trades lucrativos.
**Fórmula:** `Trades Lucrativos / Total de Trades`

```python
wr = calc.calculate_win_rate()
# Resultado exemplo: 60% ✅ PASS (acima de 45%)
```

**Interpretação:**
- WR < 40%: Estratégia não-lucrativa por frequência
- WR 45-55%: Viável se Profit Factor > 1.8
- WR > 60%: Excelente (difícil em crypto)

---

### 4️⃣ Profit Factor — Ganhos vs Perdas (Gate: ≥ 1.5)

**O que mede:** Razão entre soma de ganhos e soma de perdas absolutas.
**Fórmula:** `Soma Ganhos / Soma Perdas (abs)`

```python
pf = calc.calculate_profit_factor()
# Resultado exemplo: 1.8 ✅ PASS (acima de 1.5)
# Significa: 80% mais lucro do que perda
```

**Interpretação:**
- PF < 1.3: Perdas demasiado grandes
- PF 1.5-1.8: Bom equilíbrio lucro/perda
- PF > 2.0: Excelente assimetria

---

### 5️⃣ Consecutive Losses — Max Streak de Perdas (Gate: ≤ 5)

**O que mede:** Maior sequência de trades perdedores consecutivos.
**Relevância:** Indicador de ruin (psychological ou material).

```python
max_loss_streak = calc.calculate_consecutive_losses()
# Resultado exemplo: 2 ✅ PASS (abaixo de 5)
```

**Interpretação:**
- Max ≤ 2: Muito raro (edge forte)
- Max 3-5: Normal (aceitável)
- Max > 7: Risco de ruin alto

---

### 6️⃣ Validation — Agregador de Gates

**O que faz:** Valida TODAS as 5 métricas contra thresholds mínimos.

```python
metrics = {
    'sharpe': 1.15,
    'max_dd': 0.085,  # 8.5%
    'win_rate': 0.60,  # 60%
    'profit_factor': 1.8,
    'consecutive_losses': 2,
}

is_valid = calc.validate_against_thresholds(metrics)
# Resultado: True ✅ (TODAS as 5 métricas passaram)
```

**Thresholds Gate (Mínimos de Aceitação):**

| Métrica | Gate Min/Max | Target Ótimo | Exemplo PASS |
|---------|-----------   |--------------|-------------|
| Sharpe Ratio | ≥ 0.80 | ≥ 1.20 | ✅ 1.15 |
| Max Drawdown | ≤ 12% | ≤ 10% | ✅ 8.5% |
| Win Rate | ≥ 45% | ≥ 55% | ✅ 60% |
| Profit Factor | ≥ 1.5 | ≥ 2.0 | ✅ 1.8 |
| Consecutive Losses | ≤ 5 | ≤ 3 | ✅ 2 |

---

## 🚀 Uso Completo — Exemplo End-to-End

```python
from backtest.metrics import MetricsCalculator

# 1. Simular histórico de trades
trade_history = [
    {'entry': 1000.0, 'exit': 1050.0, 'qty': 1},  # +50
    {'entry': 1050.0, 'exit': 1030.0, 'qty': 1},  # -20
    {'entry': 1030.0, 'exit': 1080.0, 'qty': 1},  # +50
    {'entry': 1080.0, 'exit': 1070.0, 'qty': 1},  # -10
]

# 2. Criar calculadora com capital inicial
calc = MetricsCalculator(
    trade_history=trade_history,
    initial_capital=10000  # USDT
)

# 3. Calcular cada métrica
sharpe = calc.calculate_sharpe_ratio(risk_free_rate=0.02)
max_dd = calc.calculate_max_drawdown()
wr = calc.calculate_win_rate()
pf = calc.calculate_profit_factor()
mcl = calc.calculate_consecutive_losses()

print(f"Sharpe: {sharpe:.2f}")          # 1.15
print(f"Max DD: {max_dd:.1%}")          # 8.5%
print(f"Win Rate: {wr:.1%}")            # 75.0%
print(f"Profit Factor: {pf:.2f}")       # 3.50
print(f"Max Losses: {mcl}")             # 1

# 4. Validar todos os gates
metrics = {
    'sharpe': sharpe,
    'max_dd': max_dd,
    'win_rate': wr,
    'profit_factor': pf,
    'consecutive_losses': mcl,
}

if calc.validate_against_thresholds(metrics):
    print("\n✅ ESTRATÉGIA APROVADA — Libera live trading")
else:
    print("\n❌ MÉTRICAS REJEITADAS — Volta ao drawing board")
```

---

---

## 🔧 Instalação & Setup

### Pré-requisitos

```bash
# Python 3.9+
python --version

# Dependências (instale via pip)
pip install -r requirements.txt
```

### Arquivo de Configuração

Editar `config/backtest_config.py`:

```python
# Período histórico (validado: 6+ meses de dados)
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

# Símbolos (máx. 60)
SYMBOLS = [
    "BTOMSDT", "ETHUSDT", "ADAUSDT", ...
]

# Capital inicial
INITIAL_CAPITAL = 1000.0  # USD

# Risk Gate (inviolável)
MAX_DRAWDOWN = -0.03  # -3%
STOP_LOSS_PCT = -0.03  # -3%
```

### Dados Históricos

Dados são carregados automaticamente de `backtest/cache/`:

---

## �🔧 Instalação & Setup

### Pré-requisitos

```bash
# Python 3.9+
python --version

# Dependências (instale via pip)
pip install -r requirements.txt
```

### Arquivo de Configuração

Editar `config/backtest_config.py`:

```python
# Período histórico (validado: 6+ meses de dados)
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

# Símbolos (máx. 60)
SYMBOLS = [
    "BTOMSDT", "ETHUSDT", "ADAUSDT", ...
]

# Capital inicial
INITIAL_CAPITAL = 1000.0  # USD

# Risk Gate (inviolável)
MAX_DRAWDOWN = -0.03  # -3%
STOP_LOSS_PCT = -0.03  # -3%
```

### Dados Históricos

Dados são carregados automaticamente de `backtest/cache/`:

```
backtest/cache/
├── BTCUSDT_4h.parquet      # BTC 4h histórico
├── ETHUSDT_4h.parquet
└── ... (60 símbolos)
```

Para atualizar cache:

```bash
python backtest/data_cache.py --refresh --symbols all
```

---

## 🚀 Como Usar

### 1. Backtest Básico (Paper Strategy)

```python
from backtest.backtester import Backtester
from backtest.backtest_environment import BacktestEnvironment

# Inicializar environment
env = BacktestEnvironment(
    start_date="2025-01-01",
    end_date="2025-12-31",
    initial_capital=1000.0
)

# Criar backtester
bt = Backtester(env)

# Executar backtest
results = bt.run_backtest()

# Verificar resultados
print(f"Total Return: {results['total_return']:.2f}%")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

**Saída esperada:**
```
Total Return: 15.32%
Max Drawdown: -8.45%
Sharpe Ratio: 0.87
Calmar Ratio: 1.81
Profit Factor: 1.62
```

---

### 2. Backtest com Modelo RL

```bash
# Via CLI
python main.py --backtest \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --model models/crypto_agent_ppo_final.zip
```

Resultados salvos em `backtest_results/`:
```
backtest_results/
├── equity_curve.csv     # Evolução do capital
├── trades.csv           # Todas as ordens executadas
└── metrics.json         # Métricas resumidas
```

---

### 3. Walk-Forward Testing

Valida performance em múltiplas janelas temporais:

```python
from backtest.walk_forward import WalkForwardBacktest

wf = WalkForwardBacktest(
    train_period=90,        # Dias para treinar
    test_period=30,         # Dias para testar
    walk_step=15            # Deslocamento entre janelas
)

results = wf.run()

# Resultado por janela
for i, window in enumerate(results):
    print(f"Janela {i}: Sharpe={window['sharpe']:.2f}, PnL={window['pnl']:.2f}%")
```

---

## 📊 Interpretando Resultados

### Métricas Principais

| Métrica | Fórmula | Alvo | Interpretação |
|---------|---------|------|:---|
| **Total Return** | (Final Capital - Initial) / Initial | > 30% | Retorno acumulado |
| **Max Drawdown** | Min equity / Peak equity | ≤ -15% | Pior período (sempre ≥ -3% Risk) |
| **Sharpe Ratio** | (média retorno - rf) / desvio | ≥ 1.0 | Retorno ajustado ao risco |
| **Profit Factor** | Ganhos totais / Perdas totais | ≥ 1.5 | Razão de ganhos vs perdas |
| **Calmar Ratio** | Total Return / |Max Drawdown| | ≥ 2.0 | Eficiência de capital |

### Exemplo de Leitura

```json
{
  "total_return": 24.5,
  "max_drawdown": -12.3,
  "sharpe_ratio": 1.15,
  "profit_factor": 1.72,
  "calmar_ratio": 1.99,
  "num_trades": 157,
  "win_rate": 0.58
}
```

**Interpretação:**
- ✅ Retorno de 24.5% é bom
- ✅ Drawdown -12.3% está dentro do limite de -15%
- ✅ Sharpe 1.15 é adequado (≥ 1.0)
- ⚠️ Profit Factor 1.72 está ok (precisa ≥ 1.5)
- ✅ Calmar 1.99 está perto do alvo (≥ 2.0)

---

### Equity Curve

Gráfico mostra evolução do capital (salvο em `backtest_results/equity_curve.png`):

```
Capital ($)
    1500 |                    ╱╲
    1300 |           ╱╲      ╱  ╲___
    1100 |     ╱╲   ╱  ╲____╱
     900 |____╱  ╲_╱
     700 |
          Jan  Feb  Mar  Apr  May  Jun
```

**O que procurar:**
- Curva sempre crescente = estratégia consistente
- Quedas = períodos de loss (regressão OK se controlado)
- Picos e vales = volatilidade de equity

---

### Trade Log

Arquivo `trades.csv` com histórico completo:

```csv
date,symbol,side,price,quantity,pnl,realized_pnl,status
2025-01-15,BTCUSDT,BUY,42500.00,0.01,250.0,0,OPEN
2025-01-16,BTCUSDT,SELL,42750.00,0.01,250.0,250.0,CLOSED
2025-01-20,ETHUSDT,BUY,2350.00,0.50,-45.0,-45.0,CLOSED
...
```

**Análise rápida:**
```bash
# Win rate
awk -F, '$7 > 0' trades.csv | wc -l  # Trades com ganho

# Loss trades
awk -F, '$7 < 0' trades.csv | wc -l  # Trades com perda
```

---

## 🔧 Troubleshooting

### ❌ Erro: "Cache files not found"

```
FileNotFoundError: backtest/cache/ não encontrado
```

**Solução:**
```bash
python backtest/data_cache.py --refresh --symbols all
# Aguarde 5-10 minutos enquanto dados são baixados
```

---

### ❌ Erro: "Insufficient historical data"

```
ValueError: Necessário mínimo 6 meses de dados, obtive 3 meses
```

**Solução:**
- Aumentar `START_DATE`: `"2024-09-01"` em vez de `"2025-01-01"`
- OU reduzir período de backtest

---

### ❌ Erro: "Risk Gate violation detected"

```
RuntimeError: Stop Loss aplicado em -3% durante backtest (comportamento esperado)
```

**Interpretação:** Position foi fechada por proteção de risco. Normal.

---

### ⚠️ Performance Lenta (> 30s para 6 meses)

**Otimizações:**
```python
# Usar menos símbolos
SYMBOLS = ["BTCUSDT", "ETHUSDT"]  # em vez de 60

# Reduzir período
START_DATE = "2025-09-01"  # em vez de 01-01

# Usar parquet indexado (automático)
```

---

## 📚 Referência de API

### Class: `Backtester`

```python
class Backtester:
    def __init__(self, environment, model=None):
        """
        Inicializa backtester.

        Args:
            environment: BacktestEnvironment instance
            model: Modelo RL (opcional, default: random actions)
        """

    def run_backtest(self, verbose=True):
        """
        Executa backtest completo.

        Returns:
            dict: Métricas (total_return, max_drawdown, sharpe_ratio, etc)
        """

    def get_equity_curve(self):
        """Retorna array de equity por timestamp"""
```

### Class: `BacktestEnvironment`

```python
class BacktestEnvironment:
    def __init__(self, start_date, end_date, initial_capital):
        """Inicializa environment"""

    def step(self, action):
        """
        Executa um step de trading.

        Args:
            action: 0=hold, 1=buy, 2=sell

        Returns:
            (observation, reward, done, info)
        """

    def reset(self):
        """Reseta environment para início do período"""
```

### Class: `BacktestMetrics`

```python
class BacktestMetrics:
    @staticmethod
    def calculate_sharpe(returns, risk_free_rate=0.02):
        """Calcula Sharpe Ratio"""

    @staticmethod
    def calculate_drawdown(equity_curve):
        """Calcula Max Drawdown e Drawdown Duration"""

    @staticmethod
    def calculate_profit_factor(trades):
        """Calcula Profit Factor (Ganhos/Perdas)"""
```

---

## 📝 Exemplos Completos

### Exemplo 1: Backtest com Relatório HTML

```python
from backtest.backtester import Backtester
from backtest.backtest_environment import BacktestEnvironment
import json

env = BacktestEnvironment("2025-06-01", "2025-12-31", 1000)
bt = Backtester(env)
results = bt.run_backtest()

# Salvar relatório
with open("backtest_results/report.json", "w") as f:
    json.dump(results, f, indent=2)

print("✅ Relatório salvo em backtest_results/report.json")
```

---

### Exemplo 2: Comparar Múltiplas Estratégias

```python
strategies = {
    "random": None,
    "buy_hold": "models/buy_hold.zip",
    "rl_ppo": "models/crypto_agent_ppo_final.zip"
}

results_all = {}

for name, model_path in strategies.items():
    env = BacktestEnvironment("2025-01-01", "2025-12-31", 1000)
    bt = Backtester(env, model=model_path)
    results = bt.run_backtest()
    results_all[name] = results

    print(f"{name}: Sharpe={results['sharpe_ratio']:.2f}, "
          f"Return={results['total_return']:.2f}%")
```

---

## ⚠️ Validação de Risk Gate

Sempre verificar que Risk Gate 1.0 está ativo:

```python
from risk.risk_gate import RiskGate

rg = RiskGate()
print(f"Stop Loss: {rg.stop_loss}%")  # Deve ser -3.0%
print(f"Circuit Breaker: {rg.circuit_breaker}%")  # Deve ser -3.0%

# Never disable
# rg.disable()  # ❌ PROIBIDO
```

---

## 📞 Suporte

- **Issues:** GitHub Issues > Issue #59
- **Docs:** [docs/ISSUE_59_QA_GATES_S2_3_BACKTESTING.md](../docs/ISSUE_59_QA_GATES_S2_3_BACKTESTING.md)
- **Contact:** Backend Lead

---

*Mantido e atualizado pelo Backend/RL Team*

