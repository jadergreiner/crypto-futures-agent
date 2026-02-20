# Round 4: Bloqueio de CLOSE Prematuro + Simplificação de Reward

## Resumo Executivo

Implementação de mudanças estruturais para resolver o problema de fechamento prematuro de posições lucrativas pelo agente PPO.

**Status**: ✅ Completo - 22/22 testes passaram, 0 alertas de segurança

## Problema Identificado

Após 3 rounds de ajustes na reward function, os resultados do Round 3 mostraram:

- Win Rate: 48.48%, Profit Factor: 0.66, Sharpe: -0.14
- **Agente fecha posições lucrativas cedo demais** (R=0.36, R=0.08 quando TP seria R≈2-3)
- Direção estava correta (DD caiu, PF subiu), mas comportamento persistia

### Causa Raiz

1. **Ação CLOSE sempre disponível**: Agente aprende que fechar é "seguro" para evitar drawdown futuro
2. **Observação sem informação de momentum**: Agente não "vê" se preço está acelerando a seu favor
3. **Conflito de sinais**: 8 componentes de reward com pesos diferentes gerando sinais conflitantes

## Solução Implementada

### 1. Bloqueio de CLOSE Prematuro (agent/environment.py)

#### Constante

```python
MIN_R_MULTIPLE_TO_CLOSE = 1.0  # R-multiple mínimo para permitir CLOSE manual
```

#### Lógica no step()

- Quando `action == 3` (CLOSE) e há posição aberta:
  - Calcula R-multiple atual: `pnl / initial_risk`
  - **BLOQUEIA** se: `PnL > 0` E `R < 1.0`
    - Marca `action_valid = False`
    - NÃO executa o fechamento
    - Log: "CLOSE bloqueado: R=X.XX < 1.0, PnL=$XXX (lucro)"
  - **PERMITE** se: `PnL <= 0` (cortar perdas é sempre permitido)
  - **PERMITE** se: `R >= 1.0` (fechamento com lucro adequado)

#### Histórico de PnL

- Adicionado `self.pnl_history = []` em `__init__` e `reset()`
- Populado a cada step em `_get_position_state()`
- Usado para calcular momentum

### 2. Momentum e R-Multiple no position_state (agent/environment.py)

#### Novos Campos Retornados

```python
{
    'pnl_momentum': float,      # Taxa de variação do PnL
    'current_r_multiple': float # R-multiple atual da posição
}
```

#### Cálculo de Momentum

```python
if len(self.pnl_history) >= 6:
    recent_avg = np.mean(self.pnl_history[-3:])
    previous_avg = np.mean(self.pnl_history[-6:-3])
    pnl_momentum = recent_avg - previous_avg
else:
    pnl_momentum = 0.0
```

**Interpretação**:

- Momentum > 0: PnL acelerando positivamente (incentiva segurar)
- Momentum < 0: PnL perdendo força (alerta para sair)
- Momentum = 0: PnL estável ou histórico insuficiente

### 3. Simplificação da Reward (agent/reward.py)

#### ANTES (Round 3): 8 Componentes

```
r_pnl, r_risk, r_consistency, r_overtrading, 
r_hold_bonus, r_invalid_action, r_unrealized, r_inactivity
```

#### DEPOIS (Round 4): 3 Componentes

**1. r_pnl** (peso 1.0) - PnL realizado amplificado

```python
r_pnl = pnl_pct × 10.0 (PNL_SCALE)

Bonus adicional:
- R > 3.0: +1.0 (R_BONUS_HIGH)
- R > 2.0: +0.5 (R_BONUS_LOW)
```

**2. r_hold_bonus** (peso 1.0) - Incentivo assimétrico

```python
Se pnl_pct > 0 (lucro):
    r_hold_bonus = 0.05 + pnl_pct × 0.1 + (momentum × 0.05 se momentum > 0)
    
Se pnl_pct < -2.0 (prejuízo alto):
    r_hold_bonus = -0.02 (penalidade leve)
```

**3. r_invalid_action** (peso 1.0) - Penalidade forte

```python
Se action_valid == False:
    r_invalid_action = -0.5
```

#### Justificativa

- **r_pnl**: Sinal primário - amplifica PnL realizado e recompensa R-multiples altos
- **r_hold_bonus**: Incentiva segurar lucros (assimétrico: bonus cresce com lucro, penalidade leve para perda)
- **r_invalid_action**: Penaliza tentativas de CLOSE prematuro (-0.5 é significativo)

### 4. Testes Completos

#### tests/test_reward.py (12 testes)

- ✅ `test_calculate_basic`: Valida 3 componentes, ausência de componentes antigos
- ✅ `test_r_multiple_greater_than_3`: R=3.5 → r_pnl = 36.0 (35 + 1.0 bonus)
- ✅ `test_r_multiple_between_2_and_3`: R=2.5 → r_pnl = 25.5 (25 + 0.5 bonus)
- ✅ `test_r_multiple_exactly_2`: R=2.0 → r_pnl = 20.0 (sem bonus)
- ✅ `test_r_multiple_less_than_2`: R=1.5 → r_pnl = 15.0 (sem bonus)
- ✅ `test_r_multiple_exactly_3`: R=3.0 → r_pnl = 30.5 (30 + 0.5 bonus LOW)
- ✅ `test_r_multiple_negative`: R=-1.0 → r_pnl = -10.0 (sem bonus)
- ✅ `test_r_multiple_zero`: R=0.0 → r_pnl = 0.0
- ✅ `test_r_multiple_5_receives_high_bonus`: R=5.0 → r_pnl = 51.0 (50 + 1.0 bonus)
- ✅ `test_invalid_action_penalty`: r_invalid_action = -0.5
- ✅ `test_close_blocked_is_invalid`: CLOSE bloqueado gera penalidade + hold_bonus
- ✅ `test_hold_bonus_with_momentum`: Valida cálculo com momentum positivo/zero/negativo

#### tests/test_rl_environment.py (4 novos + 6 existentes)

- ✅ `test_close_blocked_when_r_below_minimum`: R=0.5, lucro → CLOSE bloqueado
- ✅ `test_close_allowed_when_losing`: Prejuízo → CLOSE permitido
- ✅ `test_close_allowed_when_r_above_minimum`: R=1.5 → CLOSE permitido
- ✅ `test_position_state_has_momentum`: Valida campos momentum e current_r_multiple

## Impacto Esperado

### Comportamento do Agente

1. **Não pode mais fechar cedo com lucro pequeno**
   - CLOSE bloqueado se R < 1.0 e posição lucrativa
   - Forçado a deixar stop/TP gerenciar a saída
   - Aprende que tentar fechar cedo gera penalidade (-0.5)

2. **Incentivado a segurar lucros**
   - Hold bonus cresce proporcionalmente ao PnL
   - Bonus extra se momentum é positivo (acelerando a favor)
   - Sinal claro: "segurar posição lucrativa é bom"

3. **Pode cortar perdas rapidamente**
   - CLOSE sempre permitido quando PnL <= 0
   - Penalidade leve (-0.02) se segura perda grande
   - Gestão de risco preservada

### Métricas Esperadas (Round 4)

- **Win Rate**: Deve cair inicialmente (menos trades, mais seletivo)
- **R-Multiple Médio**: Deve AUMENTAR significativamente (de -0.10 para ~0.5+)
- **Profit Factor**: Deve AUMENTAR (de 0.66 para ~0.9+)
- **Max Drawdown**: Pode subir levemente (menos exits prematuros)
- **Sharpe Ratio**: Deve MELHORAR (de -0.14 para ~0.0+)

## Compatibilidade

### Interface Pública Mantida

✅ `CryptoFuturesEnv.__init__()` - mesma assinatura
✅ `step()` retorna mesmo formato (obs, reward, terminated, truncated, info)
✅ `reset()` retorna mesmo formato (obs, info)
✅ `RewardCalculator.calculate()` - mesma assinatura

### Novos Campos (backwards compatible)

- `info['action_valid']` - novo campo, código antigo ignora
- `position_state['pnl_momentum']` - novo campo, código antigo ignora
- `position_state['current_r_multiple']` - novo campo, código antigo ignora

## Próximos Passos

1. **Treinar modelo Round 4**
   - Usar mesmo protocolo: Fase 1 (exploração) + Fase 2 (refinamento)
   - Monitorar se agente aprende a esperar por R > 1.0

2. **Analisar resultados**
   - Verificar distribuição de R-multiples dos trades fechados
   - Verificar se manual_close diminuiu drasticamente
   - Verificar se take_profit e stop_loss aumentaram

3. **Ajuste fino** (se necessário)
   - Se R-multiple ainda baixo: aumentar MIN_R_MULTIPLE_TO_CLOSE para 1.5
   - Se Win Rate muito baixo: ajustar bonus de hold
   - Se DD muito alto: adicionar penalidade para segurar posições com momentum negativo

## Resumo Técnico

### Arquivos Modificados

- `agent/environment.py`: +52 linhas (bloqueio CLOSE, momentum, pnl_history)
- `agent/reward.py`: -78 linhas, +60 linhas (simplificação 8→3 componentes)
- `tests/test_reward.py`: reescrito completo (12 testes)
- `tests/test_rl_environment.py`: +171 linhas (4 novos testes)

### Validação

- ✅ 22/22 testes unitários passaram
- ✅ 0 alertas de segurança (CodeQL)
- ✅ 0 comentários críticos (code review)
- ✅ Interface pública mantida (backward compatibility)

### Segurança

- Nenhuma vulnerabilidade introduzida
- Validação de índices mantida
- Tratamento de divisão por zero preservado
- Clipping de reward mantido (-10, +10)
