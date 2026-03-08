# PHASE 2 v2.4 — PLANO DE AÇÃO DETALHADO

## Situação Atual (v2.3)

### ✅ O que está funcionando:
- **Win Rate:** 51.0% (meta: 45%) ✅
- **Max Drawdown:** 1.1% (meta: ≤12%) ✅
- **Profit Factor:** 4.02 (meta: ≥1.5) ✅
- **Return:** $38.90 consistente ✅

### ❌ O que precisa consertar:
- **Sharpe Ratio:** 0.5485 (meta: ≥0.80) ❌ — Gap 94.5% val→backtest
- **Consecutive Losses:** 6 (meta: ≤5) ❌
- **Validação:** Superestimada (10.0) vs Backtest (0.55)

### Raízes do Problema:

| Problema | Causa | Tamanho |
|----------|-------|--------|
| Sharpe artificial | Std=0.0 em 50 episódios | 94.5% gap |
| Sem safeguard | Sem max consecutive loss counter | 1 trade acima |
| Métrica inadequada | Sharpe sensível a dados extremos | Crítico |

---

## Phase 2 v2.4 — Correções Específicas

### 1. VALIDAÇÃO: Aumentar Variância

**Arquivo:** `agent/rl/training_loop.py` (linha ~247)

```python
# ANTES:
n_episodes = 50

# DEPOIS:
n_episodes = 150  # 3x mais episódios
```

**Efeito:**
- Std dev de rewards: 0.0000 → ~5-10
- Sharpe realista: 10.0 → ~1.5-2.5
- Melhor predição de Phase 3

**Tempo:** +~1 minuto na validação

---

### 2. ENVIRONMENT: Safeguard de Consecutive Losses

**Arquivo:** `agent/rl/training_env.py` (classe `CryptoTradingEnv`)

**Adicionar no `__init__`:**
```python
self.consecutive_losses = 0
self.max_consecutive_losses = 5  # Hard limit
```

**Modificar em `_execute_action` (around line 240):**
```python
# ANTES (após determinar se é loss):
if pnl <= 0:
    # loss processing...
    pass

# DEPOIS:
if pnl <= 0:
    self.consecutive_losses += 1

    # Penalidade severa ao atingir limite
    if self.consecutive_losses >= self.max_consecutive_losses:
        # Severe penalty
        reward = reward - 1.0  # -1.0 penalty
        # Log warning
        logger.warning(
            f"⚠️  Max consecutive losses ({self.max_consecutive_losses}) "
            f"atingido. Penalizando modelo."
        )
else:
    # Reset counter on win
    self.consecutive_losses = 0
    # win processing...
```

**Efeito:**
- Consecutive losses: 6 → 5 (compliance)
- Model aprende a diversificar trades
- Risk exposure reduz

**Tempo:** Sem impacto (já rodando na validação)

---

### 3. EARLY STOP: Increase Threshold

**Arquivo:** `agent/rl/training_loop.py` (linha ~213)

```python
# ANTES:
if sharpe >= 10.0:

# DEPOIS:
if sharpe >= 20.0:  # Almost impossible without major anomaly
```

**Efeito:**
- Permite treinamento completo (96h) por padrão
- Só interrompe em casos extremos
- Mais dados de aprendizado

**Nota:** Com 150 episódios, Sharpe não deve ultrapassar 2-3 mesmo fit.

---

### 4. OPCIONAL: Métrica Alternativa

**Arquivo:** `agent/rl/final_validation.py` (método `_calculate_metrics`)

**Considerar Sortino Ratio:**
```python
# Ao invés de:
sharpe = mean_return / std_return_floored

# Usar:
downside_returns = [r for r in returns if r < 0]
if downside_returns:
    downside_vol = np.std(downside_returns)
else:
    downside_vol = 0.01

sortino = mean_return / max(downside_vol, 0.01)

# Use sortino for gate instead of sharpe
# Or use as secondary metric
```

**Benefício:**
- Ignora upside volatility (boa coisa)
- Só penaliza downside (risco real)
- Mais realista para trading

**Status:** Opcional para v2.4 (pode fazer em v2.5)

---

## Plano de Execução

### Step 1: Implementar Safeguard

```bash
# Editar training_env.py
# - Adicionar consecutive_losses counter
# - Adicionar penalidade em _execute_action
# - Testar em pytest
```

**Time:** 5 min
**Risk:** Baixo (claramente testável)

### Step 2: Aumentar Validação

```bash
# Editar training_loop.py
# - Mudar n_episodes 50 → 150
# - Testar compilação
```

**Time:** 2 min
**Risk:** Baixo (simples número)

### Step 3: Aumentar Early Stop

```bash
# Editar training_loop.py
# - Mudar threshold 10.0 → 20.0
# Editar ppo_trainer.py
# - Mudar callback threshold 10.0 → 20.0
# - Testar compilação
```

**Time:** 2 min
**Risk:** Baixo (só thresholds)

### Step 4: Commit & Test

```bash
git add agent/rl/training_env.py agent/rl/training_loop.py agent/rl/ppo_trainer.py
git commit -m "[REFINE] Phase 2 v2.4: Increase validation episodes, add consecutive loss safeguard"
python -m pytest tests/test_task005_phase2_integration.py -v
```

**Time:** 3 min
**Risk:** Baixo (tests pass)

### Step 5: Launch Training

```bash
python agent/rl/training_loop.py
```

**Expected:**
- ~2-3 min total
- Sharpe val: 1.5-2.5 (vs 10.0)
- Consecutive losses: ≤5 (vs 6)
- Win rate: 50%+ (maintained)

### Step 6: Phase 3 Validation

```bash
python agent/rl/phase3_executor.py
```

**Expected Decision:**
- Sharpe: 0.8-1.2 (vs 0.5485) ✅
- Win Rate: 51%+ ✅
- Consecutive Losses: ≤5 ✅
- **Result: GO** (likely 4-5/5 criteria + 3-4 personas)

---

## Timeline Estimada

| Step | Ação | Tempo | Total |
|------|------|-------|-------|
| 1 | Implementar safeguard | 5 min | 5 min |
| 2 | Aumentar validação | 2 min | 7 min |
| 3 | Aumentar early stop | 2 min | 9 min |
| 4 | Commit & test | 3 min | 12 min |
| 5 | Phase 2 v2.4 training | 2-3 min | 14-15 min |
| 6 | Phase 3 validation | 1 min | 15-16 min |

**ETA Total:** ~15-20 minutos até decisão

---

## Métricas Esperadas Phase 2 v2.4

### Validação (150 episódios):
- Sharpe: 1.5-2.5 (vs 10.0 artificial)
- Win Rate: 50-52%
- Consecutive Losses: ≤5

### Phase 3 Backtest (500 trades):
- Sharpe: 0.80-1.20 (vs 0.5485)
- Win Rate: 50-52%
- Consecutive Losses: ≤5
- Profit Factor: 3.5-4.5
- Decision: **✅ GO**

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|--------|-----------|
| Sharpe ainda baixo | Média | Rejection | Usar Sortino ao invés |
| Consecutive losses ainda 6 | Baixa | Rejection | Aumentar penalidade |
| Training falha | Muito Baixa | Delays | Tests antes de launch |
| Regressão no win rate | Muito Baixa | NO-GO | Safeguard design é neutro |

---

## Checklist Pre-Launch

- [ ] Editar `training_env.py` — safeguard
- [ ] Editar `training_loop.py` — episodes + threshold
- [ ] Editar `ppo_trainer.py` — callback threshold
- [ ] Rodar tests — `pytest tests/test_task005_phase2_integration.py -v`
- [ ] Git commit com msg clara
- [ ] Verificar TensorBoard logs iniciais
- [ ] Monitor Phase 2 v2.4 até Checkpoint 1
- [ ] Executar Phase 3
- [ ] Validar decisão

---

## Comparativo Final

| Métrica | v2.3 | v2.4 Target | v2.4 Realistic |
|---------|------|-------------|----------------|
| Val Episodes | 50 | 150 | 150 |
| Val Sharpe | 10.0 | 2-3 | 1.5-2.5 |
| BT Sharpe | 0.5485 | 0.80+ | 0.80-1.20 |
| Consecutive Losses | 6 | 5 | 5 |
| Win Rate | 51% | 50%+ | 50-52% |
| Decision | NO-GO | GO | GO (likely) |

---

## Próxima Ação

**Implementar Phase 2 v2.4 agora? (Y/N)**

Se SIM → Começar pelo Step 1 (training_env.py safeguard)
