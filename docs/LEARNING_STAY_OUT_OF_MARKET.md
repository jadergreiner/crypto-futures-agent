# Aprendizado: Ficar Fora do Mercado com Inteligência

**Data**: 21/02/2026
**Versão**: Reward Round 5
**Objetivo**: Ensinar ao agente RL que ficar fora do mercado é uma decisão válida e frequentemente melhor

---

## 1. O Problema

No treinamento anterior (Round 4), o agente apenas aprendia quando estava:
- **Operando** (abrindo, fechando, reduzindo posições)
- **Segurando** posições lucrativas
- **Cometendo erros** (penalidade por ações inválidas)

**Falta crítica**: O agente NÃO tinha sinal de aprendizado para a ação de **ficar FORA** (posição zero).

Resultado: O agente tinha incentivo implícito de "algo é melhor que nada", levando a overfitting em operações.

---

## 2. A Solução: 4º Componente de Reward

**Nova arquitetura de reward funciona com 4 componentes**:

```
Reward Total = [r_pnl] + [r_hold_bonus] + [r_invalid_action] + [r_out_of_market]
               (Lucros) + (Segurar)      + (Erros)           + (FICAR FORA) ← NOVO
```

### Componente 4: `r_out_of_market` (Novo)

Este componente recompensa **prudentemente** quando o agente fica sem posição aberta.

#### 4.1 Recompensa por Proteção em Drawdown

```python
IF (drawdown >= 2.0%) AND (sem posição aberta):
    reward += 0.15  # Mantém capital seguro em período ruim
    Log: "Out-of-market bonus (drawdown protection)"
```

**Lógica**: Durante drawdown, operações são perigosas. Melhor descansar.

**Calibração**:
- Threshold: 2% de drawdown
- Bonus: +0.15 pontos por candle

#### 4.2 Recompensa por Descanso Após Operações Ruins

```python
IF (três ou mais trades nas últimas 24h) AND (sem posição aberta):
    reward += 0.10 * (trades_24h / 10)  # Descanso após atividade
    Log: "Out-of-market bonus (rest after losses)"
```

**Lógica**: Se o agente fez 3+ operações recentemente (muitas perdas?), é inteligente descansar.

**Calibração**:
- Trigger: ≥3 trades em 24h (6 H4 candles)
- Bonus: +0.01 a +0.03 por trade recente

#### 4.3 Penalidade Leve por Inatividade Excessiva

```python
IF (flat_steps > 96):  # ~16 dias sem posição
    reward -= 0.03 * (flat_steps / 100)
    Log: "Excess inactivity penalty"
```

**Lógica**: Ficar totalmente inativo por semanas é prejudicial. Há sempre oportunidades.

**Calibração**:
- Trigger: >96 H4 candles (~16 dias)
- Penalidade: -0.03 base, escalada com inatividade excessiva

---

## 3. Casos de Uso: Quando Aprender a Ficar Fora

### Cenário 1: Market Drawdown

```
Dia 1: Portfolio -2.5% em drawdown
  → Agente LE = Posição zero (HOLD)
  → Ação: Não abrir trade
  → Reward: +0.15 (proteção)
  ✅ Aprendizado: "Drawdown = stay out"
```

### Cenário 2: Após Múltiplas Perdas

```
Últimas 6 horas: 4 trades, -0.8% total
  → Agente LE = Posição zero (HOLD)
  → Ação: Não abrir novo trade
  → Reward: +0.12 (descanso inteligente)
  ✅ Aprendimento: "Múltiplos trades = rest"
```

### Cenário 3: Mercado Ruim Persistente

```
Últimos 10 dias: Sem confluence adequada
  → Agente aprende a não forçar operações
  → Ação: HOLD repetidamente (10+ dias)
  → Reward: Pequeno mas consistente (+0.10 dia)
  ✅ Aprendizado: "Mercado ruim = paciência, não revenge trading"
```

---

## 4. Implementação Técnica

### 4.1 Modificações em `agent/reward.py`

```python
# Constantes adicionadas
OUT_OF_MARKET_THRESHOLD_DD = 2.0      # Drawdown trigger
OUT_OF_MARKET_BONUS = 0.10              # Bonus por descanso
OUT_OF_MARKET_LOSS_AVOIDANCE = 0.15     # Bonus por proteção
EXCESS_INACTIVITY_PENALTY = -0.03       # Penalidade inatividade > 16d

# Novo componente no dicionário de weights
self.weights = {
    'r_pnl': 1.0,
    'r_hold_bonus': 1.0,
    'r_invalid_action': 1.0,
    'r_out_of_market': 1.0  # ← NOVO
}
```

### 4.2 Novo Parâmetro Passado pelo Environment

```python
# agent/environment.py, função step()

reward_dict = self.reward_calculator.calculate(
    trade_result=trade_result,
    position_state=self._get_position_state(),
    portfolio_state=self._get_portfolio_state(),
    action_valid=action_valid,
    trades_recent=self.episode_trades,
    flat_steps=self.flat_steps  # ← NOVO
)
```

### 4.3 Lógica de Cálculo

```python
# Somente quando FORA do mercado (sem posição)
if portfolio_state and not has_position:

    # Se drawdown > 2%, recompensar por ficar fora
    if drawdown >= 2.0%:
        r_out_of_market = 0.15

    # Se múltiplos trades recentes, recompensar descanso
    if trades_24h >= 3:
        r_out_of_market += 0.10 * (trades_24h / 10)

    # Se muito tempo sem posição, penalidade leve
    if flat_steps > 96:
        r_out_of_market -= 0.03 * (flat_steps / 100)
```

---

## 5. Impacto Esperado no Aprendizado

### 5.1 Curto Prazo (1-5 episódios)

- PPO aprende que action=0 (HOLD) tem rewards positivos
- Reduz incentivo de abrir posições forçadas
- Começa seleção de entrada mais rigorosa

### 5.2 Médio Prazo (10-50 episódios)

- Agente passará mais tempo fora em drawdowns
- Wins tornam-se mais altos (menos operações ruins)
- Capital preservado em períodos adversos

### 5.3 Longo Prazo (100+ episódios)

- Policy converge para "selecionar com cuidado"
- Aceita ficar fora sem guilt/urgência
- Win rate e R-multiples aumentam significativamente

### Métricas Esperadas

| Métrica | Antes (Round 4) | Depois (Round 5) | Mudança |
|---------|----------|---------|---------|
| Trades/Episódio | 6-8 | 3-4 | -50% |
| Win Rate | 45% | 60%+ | +15% |
| Avg R-Multiple | 1.2 | 1.8+ | +50% |
| Dias sem posição | 2% | 15-20% | +10x |

---

## 6. Tuning e Ajustes

### Aumentar Seletividade (Mais Conservador)

```python
OUT_OF_MARKET_LOSS_AVOIDANCE = 0.25  # Aumentar de 0.15
OUT_OF_MARKET_THRESHOLD_DD = 1.5     # Baixar de 2.0% (mais sensível)
```

**Efeito**: Agente fica fora mais frequentemente, menos operações, maiores wins

### Aumentar Atividade (Mais Agressivo)

```python
EXCESS_INACTIVITY_PENALTY = -0.10    # Aumentar de -0.03
```

**Efeito**: Agente busca mais oportunidades, risco maior mas mais trades

### Balancear Componentes

```python
self.weights['r_out_of_market'] = 0.8  # Reduzir se muito conservador
```

---

## 7. Validação

### Checklist de Funcionamento

- [ ] Agent/reward.py compilado sem erros
- [ ] Novo parâmetro `flat_steps` passado corretamente
- [ ] Log mostra "Out-of-market bonus" durante testes
- [ ] Reward total em reward_components inclui `r_out_of_market`
- [ ] Training loss decresce normalmente (não explode)

### Teste Manual

```bash
# Após alterações, verificar se training funciona
python main.py --mode paper --train --train-epochs 10

# Observar logs para "r_out_of_market" em reward_components
```

---

## 8. Referência

**Arquivos modificados**:
- `agent/reward.py` - Novo componente + constantes
- `agent/environment.py` - Passagem de `flat_steps`

**Nenhuma quebra de compatibilidade**: Componente é aditivo, backward-compatible com dados antigos.

---

## Conclusão

O agente agora **aprende que ficar fora do mercado é uma decisão tática válida**, não uma "falha" ou "perda de oportunidade".

Isso vai resultar em:
1. ✅ Menos operações ruins
2. ✅ Maior seletividade
3. ✅ Capital melhor preservado
4. ✅ Wins maiores e mais consistentes

**A prudência é aprendida, não codificada.**
