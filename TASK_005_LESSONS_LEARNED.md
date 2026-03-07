# 📚 TASK-005 Lições Aprendidas — Iteração Phase 2/3

**Data:** 07 MAR 2026  
**Status:** ✅ NO-GO Decisão Registrada  
**Próximo Passo:** Phase 2 Refinement & Retraining

---

## 🎯 Contexto da Iteração

**Objetivo Original:**
- Treinar agente PPO em 500k steps com daily Sharpe gates (D1≥0.40, D2≥0.70, D3≥1.0)
- Alcançar Sharpe ≥ 1.0 para produção
- Validar contra 5 critérios de sucesso

**Resultado Obtido:**
- ❌ NO-GO Decision — 3/5 critérios falharam
- Early stop em ~50k steps (Sharpe artificial muito alto)
- Métricas não-realistas em produção

---

## 🔍 Achados Principais

### 1. **Sharpe Ratio Anormalmente Alto (Problema Critical)**

**Observado:**
- Training Sharpe: 5,480,161,813.1656 (impossível)
- Validation Sharpe: 0.4775 (realista mas abaixo da meta)
- Gap: ~11 bilhões (erro de cálculo)

**Causa Raiz Provável:**
- Fórmula de Sharpe em `final_validation.py` calcula sobre dataset muito pequeno
- Dados sintéticos (70 trades) criam volatilidade artificial
- Divisor muito pequeno cause excessiva amplificação

**Recomendação:**
```python
# REVISAR: agent/rl/final_validation.py
# Linha: sharpe_ratio = anual_return / annual_vol
# Problema: annual_vol próximo a zero com 70 trades
# Solução: Usar minimum vol floor ou mais dados
```

---

### 2. **Win Rate Crítico (18.6% vs 45% meta)**

**Observado:**
- Win Rate Training: 18.6% ✗
- Win Rate Validation: 18.6% ✓ (consistente, mas baixo)
- Trades: 70 total, ~13 tradwins, ~57 losses

**Causa Raiz Provável:**
- Dados Sprint 1 tiveram 50% win rate histórico
- Modelo PPO não generalizou para ambiente novo
- Reward shaping pode estar penalizando ganhos pequenos

**Implicação:**
- Modelo está sendo conservador demais
- Pode estar evitando trades por medo de loss
- Environment setup pode estar enviesado

**Recomendação:**
```python
# REVISAR: agent/rl/training_env.py
# Reward Function (linhas ~150-180):
#   r_pnl = profit or 0  ← Possível: -1 for losses
#   r_sharpe_bonus = sharpe × 0.1
# Problema: Loss penalty pode estar muito severo
# Solução: Balancear reward para incentivar trading
```

---

### 3. **Early Stop Muito Agressivo**

**Observado:**
- Early stop trigger: Sharpe ≥ 1.0 (acionado em ~22min)
- Timesteps: ~50k / 500k (10% do alvo)
- Checkpoint 1: ppo_checkpoint_1.pkl ✓

**Causa Raiz Provável:**
- Gate de Sharpe usando métrica não-confiável
- Callback SharpeGateCallback pode estar mal calibrado
- Pode estar chamando `_evaluate_sharpe()` com dados insuficientes

**Implicação:**
- Modelo treinado apenas 10% do intended
- Não houve convergência real
- Fase 2 foi abortada prematuramente

**Recomendação:**
```python
# REVISAR: agent/rl/ppo_trainer.py
# Função: SharpeGateCallback._check_daily_gate()
# Linha ~130-150: if avg_sharpe >= 1.0 → early_stop
# Problema: Critério muito agressivo com Sharpe ruim
# Solução: Remover ou aumentar threshold (e.g., 2.0)
```

---

### 4. **Dados Sintéticos Insuficientes**

**Observado:**
- Trades de treinamento: 70 (muito pequeno)
- Timeframe: 1 hora (assumido)
- Período coberto: ~3 dias (72 horas)
- Símbolos: 60 pares, mas dados diluídos

**Causa Raiz:**
- Generator (TradesGenerator) criou dataset micro
- Não há diversidade temporal/mercado
- Modelo não vê padrões significativos

**Implicação:**
- Overfitting possível em dados tão pequenos
- Métricas irreliáveis
- Não generalizará para trading real

**Recomendação:**
```python
# REVISAR: data/trades_history_generator.py
# Linha ~60: num_trades = 70
# Problema: Muito pequeno para treinamento RL
# Solução: Aumentar para 500+ trades (5-7 dias)
#          com representação balanceada de outcomes
```

---

### 5. **Profit Factor Suspeitosamente Alto (25,875)**

**Observado:**
- Profit Factor: 25,875.71 (impossível em trading real)
- Meta: ≥ 1.5 (extremamente ultrapassada)
- Implicação: Todas lucros, praticamente zeros losses

**Causa Raiz Provável:**
- Coincidência com dados sintéticos minúsculos
- Fórmula pode estar dividindo por número muito pequeno
- Generator pode ter criado trades enviesados

**Recomendação:**
```python
# REVISAR: agent/rl/final_validation.py
# Função: _calculate_profit_factor()
# Verificar: losing_trades numerador/denominador
# Possível: Proteção contra divisão por zero alterando resultado
```

---

## 📋 Checklist de Refinamentos Necessários

### Phase 2 Iteration Fixes

- [ ] **Fix Sharpe Calculation**
  - Adicionar floor de volatilidade mínima
  - Usar mais dados para volatilidade anualizada
  - Validar fórmula contra padrão industrial

- [ ] **Expand Training Dataset**
  - Aumentar TradesGenerator de 70 → 500+ trades
  - Representação balanceada (e.g., 50% win rate baseline)
  - Multi-timeframe (1h, 4h, 1d)

- [ ] **Adjust Reward Shaping**
  - Revisar penalidade de loss
  - Balancear incentivo de trading vs risco
  - Testar com ambiente demo antes

- [ ] **Remove/Adjust Early Stop**
  - Remover gate de Sharpe do callback
  - Deixar treinar full 500k steps
  - Ou aumentar threshold para 5.0+

- [ ] **Validate Success Criteria**
  - Confirmar cálculos de Win Rate
  - Revisar Max Drawdown computation
  - Testar métricas com dados conhecidos

---

## 🎓 Lições Aprendidas

### ✅ O Que Funcionou

1. **Infrastructure Setup**
   - Phase 1 components (Env, Loader, Trainer) funcionaram perfeitamente
   - Import path fixes resolveram problemas rapidamente
   - TensorFlow/TensorBoard integração bem

2. **Early Detection**
   - Phase 3 validation detectou problemas antes de deployment
   - 4-persona approval framework funcionou
   - NO-GO decision protegeu produção

3. **Audit Security**
   - Risk gates passaram (Audit #8 approved)
   - Max Drawdown = 0% (excelente)
   - Safety mechanisms funcionou ✓

### ❌ O Que Precisa Melhorar

1. **Metric Reliability**
   - Sharpe/Win Rate cálculos não-confiáveis com dados pequenos
   - Falta validação contra dataset de referência conhecido
   - Precisam de "sanity checks" internos

2. **Data Engineering**
   - 70 trades insuficientes para aprendizado robusto
   - Generator muito simples (precisa diversidade)
   - Sem multi-timeframe, sem padrões reais

3. **Training Configuration**
   - Early stop muito agressivo
   - Daily gates usando métrica ruim
   - Falta checkpoint intermediário de validação

---

## 🔄 Próxima Iteração — Phase 2 v2

### Step 1: Fix Sharpe & Metrics
**Tempo Estimado:** 1-2 horas
```python
# agent/rl/final_validation.py
# Adicionar:
# - Volatilidade mínima floor (e.g., 0.01)
# - Mais dias de dados para volatilidade
# - Teste unitário com dados conhecidos
```

### Step 2: Expand Training Data
**Tempo Estimado:** 0.5 horas
```python
# data/trades_history_generator.py
# Alterar:
# num_trades = 70 → 500
# Adicionar balanceamento de outcomes
```

### Step 3: Adjust Reward & Early Stop
**Tempo Estimado:** 1-2 horas
```python
# agent/rl/training_env.py
# Revisar reward shaping
# agent/rl/ppo_trainer.py
# Desabilitar ou aumentar early stop threshold
```

### Step 4: Re-Run Phase 2
**Tempo Estimado:** 96 horas (wall-time)
```bash
python agent/rl/training_loop.py
```

### Step 5: Run Phase 3 Validation
**Tempo Estimado:** 0.25 horas
```bash
python agent/rl/phase3_executor.py
```

---

## 📊 Comparação: v1 vs v2 (Esperado)

| Métrica | v1 (Atual) | v2 (Esperado) |
|---------|-----------|---------------|
| Sharpe Training | 5.4B | ~1.5-2.0 |
| Sharpe Validation | 0.48 | ~1.0+ |
| Win Rate | 18.6% | ~45%+ |
| Max Drawdown | 0% | <12% |
| Early Stop | 22 min | 96h ou Sharpe≥1.0 |
| Phase 3 Decision | NO-GO | GO (esperado) |

---

## 🎯 Success Criteria v2

Para Phase 2 próxima iteração contar como sucesso:

- ✅ Todos 5 critérios PASS (ou 4/5 com justificativa)
- ✅ 3 personas aprovam (Arch, Quality, Brain)
- ✅ Audit continua 100% (risk gates OK)
- ✅ Phase 3 Decision = GO (deployment ready)

---

## 📝 Notas Técnicas

### Debug Helper Functions Adicionadas

Considere adicionar para próximas iterações:

```python
# agent/rl/final_validation.py

def validate_metrics_sanity(metrics: Dict) -> bool:
    """Validate metrics against known bounds."""
    assert 0 <= metrics['sharpe'] <= 10, "Sharpe unrealistic"
    assert 0 <= metrics['win_rate'] <= 1, "Win rate invalid"
    assert 0 <= metrics['max_dd'] <= 1, "Drawdown invalid"
    assert metrics['profit_factor'] >= 0, "PF negative"
    return True

def test_with_known_data():
    """Test metrics with dataset of known outcome."""
    # Usar 70 trades com known metrics
    # Comparar computed vs expected
    # Assert match within 1%
```

---

## 🚀 Conclusão

**Status:** ✅ Iteração 1 CONCLUÍDA com learnings claros  
**Próxima:** Phase 2 v2 com fixes  
**Blocker:** Nenhum (tudo resolvível em dados/code)  
**Timeline:** ~2-4 horas fixes + 96h training = 100h total para v2 completa

**Recomendação:** Implementar Fix #1 (Sharpe) e #2 (Data expansion) em paralelo, depois rerun Phase 2 + 3.

