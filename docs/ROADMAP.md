# 🗺️ Roadmap — Crypto Futures Agent

## Visão Geral

```
v0.1 (Foundation)         ✅ CONCLUÍDO (12/02/2026)
v0.2 (Pipeline Fix)       ✅ CONCLUÍDO (15/02/2026)
v0.2.1 (Admin. Posições)  ✅ CONCLUÍDO (20/02/2026)
v0.3 (Training Ready)     � **CRÍTICA TODAY** (20/02 18:45-23:59 BRT) ⚡ PARAR LIVE
v0.4 (Backtest)           ← PRÓXIMO PASSO (início 21/02 após v0.3)
v0.5 (Paper Trading)      📅 Planejado (Abr/2026)
v1.0 (Live MVP)           📅 Planejado (Mai/2026)
v1.1+ (Evolução)          📅 Roadmap Continuo
```

### Timeline — Crítica (v0.3 HOJE)

```
Fev/2026                          Mar/2026          Abr/2026          Mai/2026
|--- v0.2/0.2.1 ---|⚡ v0.3 ⚡|--|--- v0.4 --------|--- v0.5 --------|→ v1.0
Pipeline + Admin.  CRÍTICA        Backtest Real    Paper Trading    Live
                   TODAY
                 (18-24h)
```

**v0.3 Execução Crítica (20/02/2026 18:45-23:59 BRT):**
- 🔴 STOP LIVE (Head de Finanças decisão)
- ⚡ Validar training pipeline (10k steps em 3 símbolos)
- ✅ Confirmar CV < 1.5 + WinRate > 45%
- ✅ Debug signal generation (0 sinais = problema)
- ✅ Resolver XIAUSDT error
- 🟢 Retomar LIVE com confiança (após validação)

## Status Atual do Projeto

| Camada | Status | Maturidade |
|--------|--------|------------|
| **Data Collection** (Binance, Sentiment, Macro) | ✅ Implementado | 70% |
| **Database** (SQLite) | ✅ Implementado | 80% |
| **Indicadores Técnicos** (EMAs, RSI, MACD, BB, VP, ADX) | ✅ Implementado | 90% |
| **SMC** (Swings, BOS, CHoCH, OBs, FVGs, Liquidity) | ✅ Implementado | 85% |
| **Multi-Timeframe** (D1 Bias, Market Regime, Correlação) | ✅ Implementado | 80% |
| **Feature Engineering** (104 features) | ✅ Implementado | 90% |
| **Configuração de Pares** (16 USDT com playbooks) | ✅ Implementado | 100% |
| **RL Environment** (Gymnasium, PPO) | ✅ Estruturado | 50% |
| **Risk Manager** (Position sizing, SL/TP) | ✅ Implementado | 70% |
| **Reward Calculator** | ✅ Implementado | 70% |
| **Trainer** (PPO multi-fase) | ✅ Estruturado | 40% |
| **Backtester** | 🟡 Placeholder | 15% |
| **Walk-Forward** | 🟡 Placeholder | 10% |
| **Execution** (Ordens reais) | 🟡 Parcial | 30% |
| **Monitoring** (Position Monitor) | ✅ Implementado | 70% |
| **Dry-Run Pipeline** | ✅ Funcional | 90% |
| **Sincronização Documentação** | ✅ Implementado | 100% |
