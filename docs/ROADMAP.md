# 🗺️ Roadmap — Crypto Futures Agent

## Visão Geral

```
v0.1 (Foundation)     ✅ CONCLUÍDO
v0.2 (Pipeline Fix)   ← VOCÊ ESTÁ AQUI
v0.3 (Training Ready)
v0.4 (Backtest)
v0.5 (Paper Trading)
v1.0 (Live MVP)
v1.1+ (Evolução)
```

### Timeline

```
Fev/2026          Mar/2026          Abr/2026          Mai/2026
|--- v0.2 --------|--- v0.3 --------|--- v0.4 --------|--- v0.5 ----→ v1.0
Pipeline Fix       Training Ready    Backtest Real      Paper Trading   Live
```

## Status Atual do Projeto

| Camada | Status | Maturidade |
|--------|--------|------------|
| **Data Collection** (Binance, Sentiment, Macro) | ✅ Implementado | 70% |
| **Database** (SQLite) | ✅ Implementado | 80% |
| **Indicadores Técnicos** (EMAs, RSI, MACD, BB, VP, ADX) | ✅ Implementado | 90% |
| **SMC** (Swings, BOS, CHoCH, OBs, FVGs, Liquidity) | ✅ Implementado | 85% |
| **Multi-Timeframe** (D1 Bias, Market Regime, Correlação) | ✅ Implementado | 80% |
| **Feature Engineering** (104 features) | ✅ Implementado | 75% |
| **RL Environment** (Gymnasium, PPO) | ✅ Estruturado | 50% |
| **Risk Manager** (Position sizing, SL/TP) | ✅ Implementado | 70% |
| **Reward Calculator** | ✅ Implementado | 60% |
| **Trainer** (PPO multi-fase) | ✅ Estruturado | 40% |
| **Backtester** | 🟡 Placeholder | 15% |
| **Walk-Forward** | 🟡 Placeholder | 10% |
| **Execution** (Ordens reais) | 🟡 Parcial | 30% |
| **Monitoring** (Position Monitor) | ✅ Implementado | 70% |
| **Dry-Run Pipeline** | ✅ Funcional | 90% |

> **Nota:** Os blocos 7 (Correlação) e 8 (D1 Context) em `features.py` ainda usam placeholders hardcoded — já existe o `multi_tf_result` sendo passado no dry-run mas o `build_observation` não o consome de fato.
