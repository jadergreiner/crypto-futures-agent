# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Unreleased] — v0.3 (Training Ready)

### A fazer
- Implementar `step()` completo no `CryptoFuturesEnv`
- Implementar `_get_observation()` usando `FeatureEngineer`
- Pipeline de dados para treinamento
- Script de treinamento funcional
- Reward shaping refinado

## [0.2.0] — 2026-02-15 (Pipeline Fix)

### Corrigido
- 🐛 **FIX:** Integrado `multi_tf_result` no `build_observation` — Blocos 7 e 8 agora usam valores reais de correlação BTC, beta, D1 bias e market regime
- 🐛 **FIX:** Corrigida lógica de R-multiple no `RewardCalculator` — if/elif invertidos para que bonus de 3R+ funcione corretamente
- 🐛 **FIX:** Corrigido mapeamento de FVG distance features no bloco SMC — índices 13-14 agora calculam distâncias de FVG ao invés de liquidity sweeps
- 🐛 **FIX:** Sincronizado `get_feature_names()` com `build_observation()` — agora retorna exatamente 104 nomes com padding

### Adicionado
- ✨ **FEAT:** Testes unitários para `FeatureEngineer` (10 testes)
- ✨ **FEAT:** Testes unitários para `MultiTimeframeAnalysis` (9 testes)
- ✨ **FEAT:** Testes unitários para `RewardCalculator` (10 testes)

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
