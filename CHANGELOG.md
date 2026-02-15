# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Unreleased] — v0.2 (Pipeline Fix)

### A fazer
- 🐛 **FIX:** Integrar `multi_tf_result` no `build_observation` (Blocos 7 e 8 eram placeholders)
- 🐛 **FIX:** Corrigir lógica de R-multiple no `RewardCalculator` (elif nunca atingido)
- 🐛 **FIX:** Sincronizar `get_feature_names()` com `build_observation()`
- ✨ **FEAT:** Adicionar testes unitários para `FeatureEngineer`
- ✨ **FEAT:** Adicionar testes unitários para `MultiTimeframeAnalysis`

## [0.1.0] — 2026-02-15 (Foundation)

### Adicionado
- Arquitetura completa em camadas (data → indicators → features → agent → execution)
- Coleta de dados Binance (OHLCV H1/H4/D1)
- 22+ indicadores técnicos (EMAs, RSI, MACD, BB, VP, OBV, ATR, ADX)
- Smart Money Concepts completo (Swings, BOS, CHoCH, OBs, FVGs, Liquidity, Premium/Discount)
- Análise multi-timeframe (D1 Bias, Market Regime, Correlação/Beta BTC)
- Feature Engineering (104 features normalizadas)
- Gymnasium Environment estruturado (PPO, 5 ações)
- Risk Manager com regras invioláveis
- Reward Calculator multi-componente
- Database SQLite
- Coleta de sentimento (Funding Rate, OI, Long/Short Ratio)
- Coleta de dados macro (Fear&Greed, DXY, BTC Dominance)
- Dry-run pipeline com dados sintéticos
- Position Monitor
- Scheduler básico
- Logging estruturado
