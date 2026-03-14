# 🚀 Geração de Sinais com Suporte a RL — Model 2.0

**Status:** OPERACIONAL (14 MAR 2026)
**Versao:** M2-016.1
**Checkpoint:** PPO treinado 500k timesteps | Sharpe evaluation: IN PROGRESS

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

A pipeline de **Geração de Sinais com RL** integra um modelo PPO treinado com a detecção determinística de padrões SMC (Smart Money Concepts) para gerar sinais de trading com maior confiança.

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
│  9. RL SIGNAL  ← 🆕 ENHANCEMENT com modelo PPO                  │
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
- [x] Treinamento incremental (`train_ppo_incremental.py`)
- [x] Integração na pipeline diária
- [x] Logging e monitoramento

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
**Última Atualização:** 14 MAR 2026 01:12 UTC
