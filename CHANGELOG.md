# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Unreleased] — v0.3 (Training Ready)

### Adicionado
- **Diagnóstico de Disponibilidade de Dados**: Novo método `diagnose_data_readiness()` no `DataLoader` que verifica se há dados suficientes ANTES de iniciar o treinamento
  - Analisa quantidade de candles disponíveis por timeframe (H1, H4, D1)
  - Calcula requisitos considerando split treino/validação e min_length
  - Verifica requisitos de indicadores (ex: EMA_610 precisa de 610+ candles D1)
  - Verifica atualização dos dados (detecta dados desatualizados >24h)
  - Retorna diagnóstico detalhado com recomendações acionáveis
- Integração do diagnóstico no `train_model()` - agora para com mensagem clara se dados insuficientes (sem fallback silencioso)
- Script de demonstração `test_diagnosis_demo.py` para visualizar o diagnóstico
- Testes abrangentes em `tests/test_data_diagnostics.py` (6 testes, 100% cobertura)

### Modificado
- `HISTORICAL_PERIODS` em `config/settings.py`:
  - H4: 180 → 250 dias (para suportar min_length=1000 com split 80/20)
  - D1: 365 → 730 dias (para suportar EMA_610 com margem)
  - H1: 90 → 120 dias (ajuste para consistência)
- `_validate_data()` em `agent/data_loader.py` agora exibe mensagens mais informativas com cálculo de dias necessários e recomendações
- `collect_historical_data()` em `main.py` agora usa valores de `HISTORICAL_PERIODS` do settings.py
- `RL_TRAINING_GUIDE.md` atualizado com seção sobre diagnóstico de dados e requisitos mínimos

### Corrigido
- 🐛 **FIX:** Problema do fallback silencioso para dados sintéticos quando usuário esperava treinar com dados reais
- 🐛 **FIX:** Mensagens de erro genéricas substituídas por diagnósticos detalhados e acionáveis
- 🐛 **FIX:** Falta de visibilidade sobre requisitos de dados antes de iniciar treinamento demorado

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
