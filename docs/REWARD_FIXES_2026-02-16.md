# Correções do Agente RL - Profit Factor e R-Multiple

## Data: 2026-02-16

## Problema Identificado

Após o Round 2 de treinamento, a validação (Fase 3) mostrou:

```
Win Rate: 52.50%        ← Bom (acima de 50%)
Profit Factor: 0.57     ← Ruim (perde mais $ que ganha)
Sharpe Ratio: -0.20     ← Ruim (retornos negativos)
Max Drawdown: 11.52%    ← Aceitável
Avg R-Multiple: -0.15   ← Ruim (trades perdedores > vencedores)
```

### Causa Raiz

O agente aprendeu a operar (Win Rate 52.50%), mas está fazendo o oposto do desejado: **corta os lucros cedo e deixa as perdas correrem**. Quando ganha, ganha pouco; quando perde, perde muito → Profit Factor 0.57.

Evidências dos logs:
```
Position closed: manual_close, PnL=$-136.66 (-1.51%), R=-0.76
Position closed: manual_close, PnL=$-41.92 (-0.47%), R=-0.24
```

## Mudanças Implementadas

### 1. agent/reward.py

#### Hold Bonus Assimétrico (Componente 5)
**Antes:**
```python
if pnl_pct > 0:
    components['r_hold_bonus'] = 0.02 + pnl_pct * 0.05
elif pnl_pct < -2.0:
    components['r_hold_bonus'] = -0.01
```
- Peso: 0.5

**Depois:**
```python
if pnl_pct > 0:
    # Bonus forte e crescente para posições lucrativas
    components['r_hold_bonus'] = 0.05 + pnl_pct * 0.1
elif pnl_pct < -0.5:
    # Penalidade crescente para posições perdedoras
    components['r_hold_bonus'] = -0.02 * abs(pnl_pct)
```
- Peso: **0.8** (aumentado)
- Incentivo muito mais forte para segurar lucros
- Penalidade mais agressiva para perdas (threshold -0.5% ao invés de -2%)

#### Novo Componente: r_exit_quality
```python
if r_multiple >= 1.0:
    # Bonus proporcional por fechar trade com bom R-multiple
    components['r_exit_quality'] = min(r_multiple * 0.5, 3.0)
elif r_multiple < -0.5:
    # Penalidade por fechar trade com R-multiple muito negativo
    # (mas não penalizar stop loss — é gestão de risco correta)
    exit_reason = trade_result.get('exit_reason', '')
    if exit_reason == 'manual_close':
        components['r_exit_quality'] = r_multiple * 0.3
```
- Peso: **1.0**
- Recompensa explícita por qualidade da saída
- Não penaliza stop loss (gestão de risco correta)
- Penaliza fechamento manual no prejuízo

#### Penalidade de Inatividade Reduzida
**Antes:**
```python
INACTIVITY_THRESHOLD = 10      # ~40h em H4
INACTIVITY_PENALTY_RATE = 0.02
# Peso: 0.5
```

**Depois:**
```python
INACTIVITY_THRESHOLD = 15      # ~60h em H4
INACTIVITY_PENALTY_RATE = 0.015
# Peso: 0.3
```
- Dá mais tempo ao agente para encontrar setups
- Penalidade mais branda
- Reduz pressão para "operar por operar"

### 2. agent/trainer.py

#### TrainingCallback Corrigido
**Antes:**
```python
def _on_rollout_end(self) -> None:
    if len(self.model.ep_info_buffer) > 0:
        ep_info = self.model.ep_info_buffer[-1]  # Apenas o último!
        self.episode_rewards.append(ep_info.get('r', 0))
        self.episode_lengths.append(ep_info.get('l', 0))
```
- Problema: Capturava apenas o último episódio
- Resultado: reward_mean=0.00 sempre nos logs

**Depois:**
```python
def __init__(self, verbose=0, log_interval=1000):
    super().__init__(verbose)
    self.log_interval = log_interval
    self.episode_rewards = []
    self.episode_lengths = []
    self._last_ep_info_len = 0  # Rastrear quantos episódios já processamos

def _on_step(self) -> bool:
    # Capturar TODOS os novos episódios do buffer
    current_len = len(self.model.ep_info_buffer)
    if current_len > self._last_ep_info_len:
        for i in range(self._last_ep_info_len, current_len):
            ep_info = self.model.ep_info_buffer[i]
            self.episode_rewards.append(ep_info.get('r', 0))
            self.episode_lengths.append(ep_info.get('l', 0))
        self._last_ep_info_len = current_len
    
    # Log melhorado
    if self.n_calls % self.log_interval == 0:
        if self.episode_rewards:
            recent_rewards = self.episode_rewards[-100:]
            logger.info(f"Training step {self.n_calls}: "
                       f"reward_mean={np.mean(recent_rewards):.4f}, "
                       f"episodes={len(self.episode_rewards)}, "
                       f"ep_len_mean={np.mean(self.episode_lengths[-100:]):.0f}")
```
- Captura TODOS os episódios novos
- Log com mais informações (reward_mean correto, contagem de episódios, tamanho médio)

## Testes

### Cobertura de Testes
- ✅ `test_reward_fixes.py`: 14 testes novos
  - Hold bonus assimétrico
  - r_exit_quality
  - Constantes ajustadas
  - Pesos atualizados
- ✅ `test_training_callback.py`: 6 testes novos
  - Captura de todos os episódios
  - Rastreamento correto de buffer
  - Logs melhorados
- ✅ `test_reward.py`: 10 testes existentes (mantidos)
- ✅ `test_reward_amplification.py`: 13 testes existentes (mantidos)

**Total: 43/43 testes passaram** ✓

### Demonstração
Script `examples/demonstrate_reward_fixes.py` mostra:
- Hold bonus assimétrico em ação
- r_exit_quality funcionando
- Penalidade de inatividade reduzida
- Cenário completo com múltiplos componentes

## Resultados Esperados

### Antes (Round 2)
- Win Rate: 52.50%
- **Profit Factor: 0.57** ← Ruim
- **Avg R-Multiple: -0.15** ← Negativo
- Sharpe Ratio: -0.20

### Depois (Esperado no Round 3)
- Win Rate: ~50-55% (mantido)
- **Profit Factor: > 1.0** ← Melhoria esperada
- **Avg R-Multiple: > 0** ← Positivo
- Sharpe Ratio: > 0.5

## Arquivos Modificados

1. `agent/reward.py`
   - Hold bonus assimétrico forte
   - Novo componente r_exit_quality
   - Constantes de inatividade ajustadas
   - Pesos atualizados

2. `agent/trainer.py`
   - TrainingCallback corrigido
   - Captura de todos os episódios
   - Logs melhorados

3. Novos arquivos:
   - `tests/test_reward_fixes.py`
   - `tests/test_training_callback.py`
   - `examples/demonstrate_reward_fixes.py`

## Compatibilidade

- ✓ Interface pública preservada
- ✓ Assinatura do método `calculate()` mantida
- ✓ Clipping de reward em [-10, +10] mantido
- ✓ Todos os testes existentes continuam passando
- ✓ Documentação em Português mantida

## Segurança

- ✅ Code review: Nenhum problema encontrado
- ✅ CodeQL: 0 alertas
- ✅ Nenhuma vulnerabilidade introduzida

## Como Usar

### Treinar com as novas configurações
```bash
python main.py --mode train
```

### Ver demonstração das mudanças
```bash
python examples/demonstrate_reward_fixes.py
```

### Rodar testes
```bash
pytest tests/test_reward*.py tests/test_training_callback.py -v
```

## Observações

1. As mudanças são **retrocompatíveis** - código existente continua funcionando
2. O agente precisará ser **retreinado do zero** para aprender o novo comportamento
3. As constantes podem ser ajustadas via `RewardCalculator.update_weights()` se necessário
4. O TrainingCallback agora fornece logs mais informativos durante o treinamento

## Conclusão

As mudanças implementam um sistema de incentivos assimétrico que:
- **Recompensa fortemente** segurar posições lucrativas
- **Penaliza** segurar posições perdedoras
- **Recompensa** fechar com bons R-multiples
- **Penaliza** fechar manualmente no prejuízo (mas não stop loss)
- **Reduz pressão** para operar demais

Isso deve resolver o problema de Profit Factor baixo e R-Multiple negativo, mantendo o Win Rate.
