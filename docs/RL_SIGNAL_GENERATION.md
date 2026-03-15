# 🚀 Geração de Sinais com Suporte a RL — Model 2.0

**Status:** OPERACIONAL (15 MAR 2026)
**Versão:** M2-016.4 (LSTM Policy & Training)
**Checkpoint:** LSTM Policy integrated, Treino PPO vs MLP | Sharpe evaluation: IN PROGRESS

## 📊 Resultados de Treinamento (14 MAR 2026)

### Execução M2-016.1 — Treino PPO Incremental

| Métrica | Valor |
|---------|-------|
| Timesteps Treinos | 500,000 ✓ |
| Duração Treinamento | 1118.3s (18.6 min) |
| Dataset Episodes | 7 episódios |
| Symbols Processados | BNBUSDT, SOLUSDT, ETHUSDT, PTBUSDT, BTCUSDT, XRPUSDT |
| Timeframe | H4 |
| Learning Rate | 0.0003 |
| Modelo Final | `checkpoints/ppo_training/ppo_model.zip` |
| Taxa RL Enhancement (Validação) | 100% (2/2 sinais) |
| RL Confidence Médio | 0.75 |

### Métricas de Treinamento

```
Final Training Stats:
- Rollout EP Reward Mean: 0.6
- Entropy Loss: -0.0266
- Explained Variance: 0.00116
- Loss: -0.000398
- N Updates: 39,060
- FPS: 447
```

### Learnings de Hiperparâmetros

1. **Learning Rate:** 0.0003 funcionou bem para dados esparsos (7 episódios)
2. **Batch Size:** 32 foi suficiente para 7 samples
3. **N Epochs:** 10 convergiu sem overfitting
4. **Environment Window:** 100 timesteps por episódio foi adequado

### Próximos Passos

- [ ] **Validação Sharpe:** Executar backtest 72h para medir Sharpe ratio
- [ ] **Scaling de Dados:** Coletar >=50 episódios antes de próximo treino
- [ ] **Feature Engineering:** Adicionar market regime features
- [ ] **RL Enhancement Goal:** Atingir 60%+ de melhoria sobre determinístico

---

## Visão Geral

A pipeline de **Geração de Sinais com RL** integra um modelo PPO treinado com a
detecção determinística de padrões SMC (Smart Money Concepts) para gerar sinais
de trading com maior confiança.

## Enriquecimento de Features com Dados de Mercado (Fases D.2-D.4)

A partir de 14 MAR 2026, a pipeline integra dados de mercado externo para
enriquecer episódios de treinamento:

### Fase D.2: Coleta de Taxas de Financiamento (Operacional)

Daemon coleta taxa de financiamento em tempo real pela API Binance:

```bash
python scripts/model2/daemon_funding_rates.py --symbols BTCUSDT,ETHUSDT
```

Dados coletados:
- `latest_rate`: Taxa atual da posição perpetual
- `avg_rate_24h`: Média móvel 24h (prediz reversão)
- `sentiment`: Classificação (bullish/neutral/bearish)
- `trend`: Dirção da mudança

### Fase D.3: Integração em Episódios (Operacional)

A pipeline enriquece cada episódio com features PR/OI:

```json
{
  "episode_id": "EP-20260314-001",
  "features_json": {
    "fr_latest_rate": 0.000315,
    "fr_sentiment": "bullish",
    "oi_current": 1250000.5,
    "oi_sentiment": "accumulating",
    "...": "mais 15 features escalares"
  }
}
```

Estado esperado: >= 90% de episódios com features enriquecidas.

### Fase D.4: Análise de Correlação (Operacional)

Descoberta: sentimento de FR prediz resultado com r=0.27 (p=0.006, significante).

Implicação operacional:
```
FR Bearish  → 0.00% win rate (SINAL FORTE DE PERDA)
FR Neutral  → 37.14% win rate (baseline)
FR Bullish  → 25.81% win rate (não melhor)
```

Recomendação: Rejeitar sinais quando `fr_sentiment = bearish`.

Executar análise semanal:
```bash
python scripts/model2/phase_d4_correlation_analysis.py \
  --db-path db/modelo2.db \
  --output-dir results/model2/analysis/
```

### Fase E.1 a E.5: Ambiente, Política, Treino e MACD (15 MAR)

[Conteudo anterior sobre E.1-E.5...]

### Fase E.6: Enriquecimento com Indicadores Avancados (15 MAR — EM PROGRESSO)

Nova fase dedica à adição de indicadores avançados para melhorar discriminação de sinais.

**Objetivo:** Expandir de 22 features (E.5) para 26 features com indicadores de momentum.

**Novos Indicadores (4 features):**

1. **Estocastico K (14)** — Oscilador de zona extrema
   - Range: [0, 100]
   - Interprete: >80 = sobrecompra, <20 = sobrevenda
   - Beneficio: Detecta reversoes em picos/fundos

2. **Estocastico D (14)** — Suavizacao de K (sinal)
   - Range: [0, 100]
   - Interprete: Confirmacao de K lines cruzadas
   - Beneficio: Reduz falsos sinais (wait for D confirmation)

3. **Williams %R (14)** — Oscilador relacionado
   - Range: [-100, 0]
   - Interprete: >-20 = sobrecompra, <-80 = sobrevenda
   - Beneficio: Correlacao com Estocastico (redundancia util)

4. **ATR Normalizado (14)** — Volatilidade % do preco
   - Range: [0, ∞)
   - Interprete: % variacao do preco (pos-risk sizing)
   - Beneficio: Normalizado (escala independente)

**Estrutura das 26 Features (E.6):**

```
Categorias de Features por Tipo:
├─ Candles (5): OHLCV
├─ Volatilidade Real (8 → 12):
│  ├─ ATR_20, RSI_14
│  ├─ Bollinger Bands (lower, upper, position)
│  ├─ MACD (line, signal, histogram)
│  ├─ Estocastico (K, D) [🆕 +2]
│  ├─ Williams %R [🆕 +1]
│  └─ ATR Normalizado [🆕 +1]
├─ Multi-Timeframe (3): H1, H4, D1 closes (+ ATR norm cada TF)
├─ Funding Rates (4): latest_rate, sentiment, trend, avg_24h
└─ Open Interest (3): current, sentiment, direction
```

**Status de Implementacao:**

| Componente | Status | Evidencia |
|-----------|--------|-----------|
| Feature Enricher método Stochastic | ✅ OK | `calculate_stochastic()` |
| Feature Enricher método Williams | ✅ OK | `calculate_williams_r()` |
| Feature Enricher método ATR Norm | ✅ OK | `calculate_atr_normalized()` |
| Testes Unitarios | ✅ 9/9 PASS | `test_model2_phase_e6_indicators.py` |
| Modelos MLP retreinados | 🔄 EM PROGRESSO | train_ppo_lstm.py --policy mlp |
| Modelos LSTM retreinados | 🔄 EM PROGRESSO | train_ppo_lstm.py --policy lstm |
| Comparacao Sharpe (22 vs 26) | 🔄 AGENDADO | `phase_e6_sharpe_comparison.py` |

**Testes Unitarios E.6 (9 Passed):**

```
✓ test_stochastic_basic — Calculo basico funciona
✓ test_stochastic_overbot_zone — Detecta sobrecompra
✓ test_stochastic_insufficient_data — Fallback correto
✓ test_williams_r_basic — Range [-100, 0]
✓ test_williams_r_at_high — Proxima de 0 em maxima
✓ test_williams_r_insufficient_data — Fallback -50
✓ test_atr_normalized_basic — % normalizacao OK
✓ test_atr_normalized_high_volatility — Maior em alta vol
✓ test_feature_enricher_integration — Metodos acessiveis
```

**Pipeline de Execucao E.6:**

```
Feature Enricher + novos indicadores
                ↓
    Modelo MLP retreinado (300k timesteps)
                ↓
    Modelo LSTM retreinado (300k timesteps)
                ↓
Comparacao Sharpe: E.5 (22 feat) vs E.6 (26 feat)
                ↓
Selecionar melhor modelo (MLP ou LSTM)
                ↓
Integrar em checkpoints/ para producao
```

**Resultado Esperado:**

- Sharpe ratio melhorado em 5-10% vs E.5
- Reducao de false signals (Williams + Stochastic redundancia)
- Melhor deteccao de reversoes (peaks/valleys)

### Fase E.7: Otimizacao de Hiperparametros com Optuna (15 MAR — AGENDADA)

Nova fase dedica a otimizar hiperparametros do modelo PPO baseado em metricas
de performance.

**Objetivo:** Melhorar Sharpe ratio em 10-15% alem do baseline E.6.

**Hiperparametros a Otimizar:**

| Parametro | Range | Baseline E.6 |
|-----------|-------|--------------|
| Learning Rate | [1e-5, 1e-3] | 3e-4 |
| Batch Size | [32, 64, 128] | 64 |
| Entropy Coef | [0.0, 0.1] | 0.01 |
| Clip Range | [0.1, 0.3] | 0.2 |
| GAE Lambda | [0.9, 0.99] | 0.95 |

**Metricas de Avaliacao:**

1. **Sharpe Ratio** — Objetivo principal (meta: >1.5)
2. **Win Rate** — % trades lucrativos
3. **Max Drawdown** — Risco maximo suportado
4. **Convergence Time** — Timesteps ate convergencia

**Status de Implementacao:**

| Componente | Status | Evidencia |
|-----------|--------|-----------|
| Script Optuna grid search | ✅ OK | `optuna_grid_search_ppo.py` |
| Estrutura de otimizacao | ✅ OK | TPESampler + MedianPruner |
| Objective functions | ✅ OK | MLP e LSTM separadas |
| Testes unitarios | 🔄 AGENDADO | `test_model2_phase_e7_optuna.py` |

**Pipeline E.7:**

```
Baseline E.6 (26 features, default hyperparams)
                ↓
Optuna Grid Search (100 trials: 50 MLP + 50 LSTM)
                ↓
Avaliar Top 5 Hyperparameter Sets
                ↓
Selecionar Best Hyperparams por Modelo
                ↓
Retreinar MLP + LSTM com Best Params
                ↓
Comparacao: Baseline E.6 vs Otimizado E.7
                ↓
Publicar Resultados em results/model2/analysis/
```

**Resultado Esperado:**

- Sharpe ratio E.7 >= Sharpe E.6 + 10%
- Top 5 hyperparameter sets documentados
- Melhor modelo (MLP ou LSTM) identificado
- Versao otimizada pronta para producao

### Fase E.8: Retreinar PPO com Best Hyperparameters (EM PROGRESSO)

**Objetivo:** Usar best hyperparams de E.7 para retreinar modelos MLP + LSTM
com 26 features e validar melhoria teórica em prática.

**Status de Implementacao:**

| Componente | Status | Evidencia |
|-----------|--------|-----------|
| Script retrain | ✅ OK | `retrain_ppo_with_optuna_params.py` |
| Load best params | ✅ OK | Carrega de E.7 results JSON |
| Script comparacao | ✅ OK | `compare_e6_vs_e8_sharpe.py` |
| Treinamento MLP | 🔄 EM PROGRESSO | 500k timesteps com best params |
| Treinamento LSTM | 🔄 EM PROGRESSO | 500k timesteps com best params |
| Metricas (Sharpe, Win Rate) | ⭕ AGENDADO | Calculo pos-treino |

**Pipeline E.8:**

```
Load Best Hyperparams from E.7
       ↓
Retrain MLP (500k timesteps)
       ↓
Retrain LSTM (500k timesteps)
       ↓
Avaliar E.6 baseline vs E.8 otimizado
       ↓
Calcular Sharpe, Win Rate, Max Drawdown
       ↓
Selecao de melhor modelo (MLP vs LSTM)
       ↓
Publicar resultados em results/model2/analysis/
```

**Metricas Esperadas (E.8 vs E.6):**

| Baseline | Meta E.8 | Melhoria |
|----------|----------|----------|
| MLP Sharpe: 1.23 | >=1.35 | +10% |
| LSTM Sharpe: 1.15 | >=1.27 | +10% |
| MLP Win Rate: 54% | >=57% | +5% |
| LSTM Win Rate: 52% | >=55% | +5% |

### Fase E.9: Ensemble Voting (MLP + LSTM) para Robustez (EM PROGRESSO)

**Objetivo:** Combinar predicoes de MLP + LSTM via votacao (soft+hard)
para melhorar robustez, reduzir volatilidade e aumentar consistencia.

**Status de Implementacao:**

| Componente | Status | Evidencia |
|-----------|--------|----------|
| Soft voting | ✅ OK | `ensemble_voting_ppo.py` |
| Hard voting | ✅ OK | `ensemble_voting_ppo.py` |
| Avaliacao | ✅ OK | `evaluate_ensemble_e9.py` |
| Benchmark | ✅ OK | `compare_e5_to_e9_final.py` |

**Pipeline E.9:**

```
Load E.8 (MLP + LSTM Optuna)
       ↓
Soft Voting (0.48·MLP + 0.52·LSTM)
       ↓
Hard Voting (votacao com pesos)
       ↓
Avaliar (Sharpe, Win Rate, Drawdown)
       ↓
Benchmark E.5->E.9
```

**Metricas Esperadas:**

| Baseline | Meta | Beneficio |
|----------|------|----------|
| Ensemble Sharpe | >=1.40 | +5-10% |
| Ensemble Win Rate | >=56% | Consistencia |
| Consenso Votos | >75% | Coesao |

---

## Próximas Fases

### Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE DIÁRIA (daily_pipeline.py)          │
├─────────────────────────────────────────────────────────────────┤
│  1. MIGRATE    → Inicializar bancos                              │
│  2. SCAN       → Detectar padrões SMC                            │
│  3. TRACK      → Monitorar estado das oportunidades              │
│  4. VALIDATE   → Validar integridade                             │
│  5. RESOLVE    → Resolver conflitos                              │
│  6. BRIDGE     → Converter oportunidades → sinais técnicos       │
│  7. ORDER      → Aplicar lógica de risco                         │
│  8. EXPORT     → Exportar sinais para trading                    │
│  9. RL SIGNAL  ← ENHANCEMENT com modelo PPO                      │
│  10. ENRICH    ← 🆕 Enriquecer com FR/OI (D.2-D.3)               │
└─────────────────────────────────────────────────────────────────┘
                           ↓
        ┌───────────────────────────────────────┐
        │  TREINAMENTO INCREMENTAL (weekly)     │
        ├───────────────────────────────────────┤
        │ train_ppo_incremental.py              │
        │  1. Carregar 7+ episódios do banco    │
        │  2. Preparar dataset (obs, rewards)   │
        │  3. Treinar modelo PPO (10k+ steps)   │
        │  4. Salvar checkpoint com metadata    │
        └───────────────────────────────────────┘
```

## Fluxo de Dados

### Fase 1: Coleta de Episódios (Contínuo)

Cada ciclo da pipeline gera **episódios de treinamento** que alimentam o modelo:

```json
{
  "episode": {
    "cycle_run_id": "20260314T040222Z",
    "symbol": "BTCUSDT",
    "timeframe": "H4",
    "label": "context",        // type: context, signal, execution, trade
    "status": "CYCLE_CONTEXT",
    "reward_proxy": null,      // será calculado pós-execução
    "features": {
      "latest_candle": {...},  // OHLCV, variação %
      "technical_signals": {...},  // RSI, SMC patterns
      "opportunities": {...},  // Estado de oportunidades
      "market_context": {...}  // Bias, liquidez, funding rate
    },
    "target": {
      "objective": "support_training_dataset_with_cycle_state"
    }
  }
}
```

**Tabela**: `training_episodes` em `db/modelo2.db`
- 7 episódios atuais (H4, todos simbologia 'context')
- Crescimento esperado: 8 episódios/ciclo × 288 ciclos/dia = 2.3k episódios/dia

### Fase 2: Treinamento Incremental (Semanal)

Script: `scripts/model2/train_ppo_incremental.py`

**Entrada:**
- Episódios persistidos da semana (2k+ amostras)
- Modelo anterior (para fine-tune)

**Pipeline:**
```
Load Episodes (2k+)  →  Prepare Dataset  →  Train PPO  →  Save Checkpoint
  7 episódios          Obs shape (7,5)      10k steps     ppo_model.pkl
  6 símbolos           Rewards shape (7,)   Sharpe > 0.5  + metadata.json
  Labels: context      Mean reward: 0.10    Duration: 5s
```

**Saída:**
```
checkpoints/ppo_training/
  ├── ppo_model.pkl                    (modelo treinado)
  ├── ppo_training_metadata_*.json     (métricas de treinamento)
  └── vecnorm_model.pkl               (normalizador de features)
```

### Fase 3: Geração de Sinais com RL Enhancement (Diário)

Script: `scripts/model2/rl_signal_generation.py`

**Input:**
- 2 oportunidades detectadas (from BRIDGE stage)
- Modelo PPO (se disponível em checkpoints/)

**Pipeline:**

```
Opportunity  →  Extract Features  →  PPO Predict  →  Filter  →  Generate Signal
{
  id: 1,
  symbol: BTCUSDT,
  signal_side: BUY,
  entry_price: 42500,
  SL: 41500,
  TP: 44000
}

              [log(42500), log(1.0),    [action: LONG,]    confidence >=  Technical Signal
               0.5 (RSI),              probs: [0.3,       0.50? YES:
               0.0 (pos),              0.6, 0.1]]         GENERATE
               0.0 (PnL)]

                                                          ↓

                                                    {
                                                      op_id: 1,
                                                      symbol: BTCUSDT,
                                                      side: BUY,
                                                      rl_confidence: 0.85,
                                                      rl_action: LONG,
                                                      rl_enhanced: true
                                                    }
```

**Output:**

```json
{
  "status": "ok",
  "run_id": "20260314T041114Z",
  "ppo_available": false,           // Sem modelo ainda
  "episodes_available": 7,
  "opportunities_processed": 2,
  "signals_generated": 2,           // 2/2 oportunidades convertidas
  "signals_with_rl_enhancement": 0, // 0 com PPO (fallback determinístico)
  "opportunities": [
    {
      "opportunity_id": 1,
      "symbol": "BTCUSDT",
      "status": "IDENTIFICADA",
      "rl_confidence": 0.7,         // Confiança padrão (sem PPO)
      "rl_action": "LONG",
      "signal_generated": true
    }
  ]
}
```

## Modos de Operação

### Modo 1: Fallback Determinístico (Atual)
**Situação:** Sem modelo PPO treinado
**Comportamento:**
- ✅ Gera sinais normalmente
- ✅ Usa confiança padrão (0.7)
- ⚠️ Sem otimização ML

```
rl_confidence = 0.7 (padrão)
rl_action = "LONG"|"SHORT"|"HOLD" (baseado em signal_side)
rl_enhanced = false
```

### Modo 2: PPO Enhancement (Quando modelo disponível)
**Situação:** Checkpoint PPO em `checkpoints/ppo_training/ppo_model.pkl`
**Comportamento:**
- ✅ Carrega modelo
- ✅ Faz predição por oportunidade
- ✅ Ajusta confiança baseado em concordância PPO/determinístico

```
if action_ppo == expected_action:
    rl_confidence = 0.85  (ALTO - concordância)
elif action_ppo == "HOLD":
    rl_confidence = 0.50  (MÉDIO - hesitante)
else:
    rl_confidence = 0.30  (BAIXO - discordância)

Filtro: signal_generated = True if rl_confidence >= 0.50
```

## Features do Modelo RL

**Espaço de Observação:**
```python
[
    close_normalized,     # log(close) — fechamento normalizado
    volume_normalized,    # log(volume) — volume normalizad
    rsi,                  # RSI [0, 1] — RSI relativista
    position,             # [HOLD=0, LONG=1, SHORT=-1] — posição aberta
    pnl_pct               # tanh(pnl %) — P&L normalizado
]
# Shape: (5,) = Box(5,) da Gymnasium
```

**Espaço de Ações:**
```python
{
    0: "HOLD",    # Não fazer nada
    1: "LONG",    # Entrar/Manter long
    2: "SHORT"    # Entrar/Manter short
}
# Shape: Discrete(3)
```

**Rewards:**

| Episódio | Label | Reward |
|----------|-------|--------|
| Vitória | `win` | +1.0 |
| P&L positivo | `profit` | +0.5 a +1.0 (proportional) |
| Breakeven | `breakeven` | ±0.0 |
| P&L negativo | `loss` | -0.5 a -1.0 |
| Contexto | `context` | +0.1 (suporte) |

## Integração com Pipeline Diária

**Arquivo:** `scripts/model2/daily_pipeline.py`

**Stage adicionada:**

```python
(
    "rl_signal_generation",
    run_rl_signal_generation,
    {
        "model2_db_path": resolved_model2_db,
        "timeframe": timeframe,
        "symbols": symbols_to_use,
        "dry_run": bool(dry_run),
        "output_dir": resolved_output_dir,
    },
),
```

**Posição:** Após `export_signals` (stage 8)
**Timing:** ~200ms (fallback) a ~5s (com PPO)
**Fallback:** Se erro, continua com determinístico

## Próximas Fases

### ✅ Implementado
- [x] Persistência de episódios (`persist_training_episodes.py`)
- [x] Geração de sinais com RL (`rl_signal_generation.py`)
- [x] Integração na pipeline diária
- [x] Logging e monitoramento
- [x] Ambiente Temporal LSTM (`LSTMSignalEnvironment`)
- [x] Política LSTM customizada (`LSTMPolicy` + Extractor)
- [x] Script de Treino PPO Dual MLP/LSTM (`train_ppo_lstm.py`)

### 🔄 Próximo
- [ ] Executar primeiro treinamento completo (500k timesteps, 96h)
- [ ] Validar Sharpe ratio gates (0.4 → 0.7 → 1.0)
- [ ] Testar predições em mercado ao vivo
- [ ] Implementar feedback loop (recompensas pós-execução)
- [ ] Fine-tune com dados reais (não simulados)

### 📊 Métricas de Sucesso

| Métrica | Baseline | Target |
|---------|----------|--------|
| Episódios/dia | 8 | 50+ |
| Taxa de RL enhancement | 0% | 60%+ |
| Sharpe ratio médio | - | 0.70+ |
| Win rate de sinais RL | - | 55%+ |
| Tempo de inference | - | <100ms |

## Como Executar

### Manual

**Geração de sinais (uma execução):**
```bash
python scripts/model2/rl_signal_generation.py \
  --model2-db-path db/modelo2.db \
  --timeframe H4
```

**Treinamento incremental (semanal):**
```bash
python scripts/model2/train_ppo_incremental.py \
  --model2-db-path db/modelo2.db \
  --timesteps 50000
```

### Automático (via iniciar.bat)
```batch
REM Option 2: Model 2.0 Pipeline Runner
REM Executa diariamente:
iniciar.bat opção 2
```

## Troubleshooting

### "Nenhum checkpoint PPO disponível"
**Cause:** Nenhum treinamento executado ainda
**Solution:** Rodar `train_ppo_incremental.py` uma vez
**Teste Interim:** Fallback determinístico funciona

### "Reward: mean=0.100 std=0.000"
**Cause:** Episódios são todos "context" label
**Solution:** Aguardar execuções com dados pós-trade
**Status:** Normal em fase inicial

### "stable_baselines3 indisponível"
**Cause:** Dependência não instalada
**Solution:** `pip install stable-baselines3[extra]`
**Teste Interim:** Continua em fallback determinístico

## Referências

- **Training Loop:** `agent/rl/training_loop.py` (96h wall-time PPO)
- **Environment:** `agent/rl/training_env.py` (Gymnasium CryptoTradingEnv)
- **PPO Config:** `agent/rl/ppo_trainer.py` + `config/ml_training_config.json`
- **Episode Storage:** `db/modelo2.db::training_episodes` table
- **Signals Bridge:** `core/model2/signal_bridge.py`
- **Repository:** `core/model2/repository.py`

---

**Status:** ✅ OPERACIONAL (modo fallback determinístico ativo)
**Última Atualização:** 15 MAR 2026
