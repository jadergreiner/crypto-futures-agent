# 📊 Backtesting Engine — Manual Operacional

**Versão:** 1.0  
**Última atualização:** 2026-02-22  
**Autor:** Backend/RL Team

---

## 📖 Índice

1. [Visão Geral](#visão-geral)
2. [Instalação & Setup](#instalação--setup)
3. [Como Usar](#como-usar)
4. [Interpretando Resultados](#interpretando-resultados)
5. [Troubleshooting](#troubleshooting)
6. [Referência de API](#referência-de-api)

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

