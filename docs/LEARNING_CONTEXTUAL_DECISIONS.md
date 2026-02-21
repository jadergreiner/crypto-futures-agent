# Aprendizado Contextual: Quando Ficar Fora É Sábio vs Desperdiçador

**Data**: 21 de fevereiro de 2026
**Objetivo**: Diferenciar entre prudência (ficar fora certo) e ganância (ficar fora errado)

---

## O Problema Anterior

Com o componente `r_out_of_market` (Round 5), o agente aprendia:

- ✅ Ficar fora em drawdown = +0.15 (sempre positivo)
- ✅ Ficar fora após atividade = +0.10 (sempre positivo)
- ❌ Mas NÃO diferenciava entre:
  - **Prudência**: Ficar fora quando DEVERIA (mercado perigoso)
  - **Ganância**: Ficar fora quando NÃO DEVERIA (oportunidade desperdiçada)

**Exemplo de Falta**:

```
Candle 10: Drawdown 2.2%, Signal gerado (confluence 8.5), agente fica fora
Reward: +0.15 (proteção reconhecida)
Mas a oportunidade depois ganha +2.5%!
Agente aprendeu: ficar fora é sempre bom (ERRADO)
```

---

## A Solução: Opportunity Learning (Meta-Learning)

Novo módulo `agent/opportunity_learning.py` implementa **aprendizado retrospectivo contextual**.

### Fluxo

```
TEMPO T (Signal gerado):
  │
  ├─ Signal BTCUSDT LONG, confluence 8.5
  ├─ Entry price: 45000
  ├─ Agente decide: fica fora (DD 2.2%, ou múltiplos trades)
  ├─ Registra: MissedOpportunity com contexto
  │
  │ ... X candles passam ...
  │
TEMPO T+X (Lookback completo):
  │
  ├─ Preço atingiu: 45900 (seria +2% de lucro)
  ├─ Calcula: "Se tivesse entrado, como seria?"
  ├─ Simula: Entry 45000, TP 52500, SL 43500
  ├─ Resultado: Ganharia +2%, não teria batido stop
  ├─ Análise: Oportunidade BOA foi desperdiçada
  └─ Aprendizado: -0.10 (penalidade por ganância)
         Reasoning: "Em condições normais,
                    desperdiçou oportunidade BOA.
                    Deveria ter entrado."
```

---

## Lógica de Aprendizado Contextual

### Matriz de Decisões

```
┌─────────────────────────────────────────────────────────────┐
│ SE: Oportunidade teria GANHADO bem (+3% ou mais)            │
├─────────────────────────────────────────────────────────────┤
│ CENÁRIO 1: Drawdown alto (≥3%) & Confluence normal         │
│   Decisão: MISTO                                            │
│   Reward: -0.15 (penalidade moderada)                       │
│   Reasoning: "Deveria ter entrado com menor size"            │
│   Status: APRENDIZADO - Ser menos aversivo                  │
│                                                              │
│ CENÁRIO 2: Múltiplas trades recentes & Oportunidade boa     │
│   Decisão: ERRADA                                           │
│   Reward: -0.10 (penalidade média)                          │
│   Reasoning: "Descanso foi longo demais"                     │
│   Status: APRENDIZADO - Reiniciar treinamento mais rápido   │
│                                                              │
│ CENÁRIO 3: Condições normais & Oportunidade boa             │
│   Decisão: MUITO ERRADA                                     │
│   Reward: -0.20 (penalidade forte)                          │
│   Reasoning: "Sem justificativa válida, desperdiçou"        │
│   Status: APRENDIZADO - Entrar quando há oportunidade       │
├─────────────────────────────────────────────────────────────┤
│ SE: Oportunidade teria PERDIDO bem (-2% ou mais)            │
├─────────────────────────────────────────────────────────────┤
│ CENÁRIO 4: Qualquer contexto                                │
│   Decisão: CORRETA                                          │
│   Reward: +0.30 (recompensa forte)                          │
│   Reasoning: "Evitou perda, decisão clara sábia"           │
│   Status: APRENDIZADO - Confie na decisão de ficar fora    │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementação Técnica

### Arquivo: `agent/opportunity_learning.py`

```python
class OpportunityLearner:
    """Aprende quando ficar fora é sábio vs desperdiçador."""

    def register_missed_opportunity(self, symbol, step, direction,
                                   entry_price, confluence, atr,
                                   drawdown_pct, recent_trades_24h):
        """
        Registra oportunidade não tomada.
        Salva contexto: por que não entrou?
        """

    def evaluate_opportunity(self, opportunity_id, current_price,
                            max_price_reached, min_price_reached):
        """
        Depois de X candles, avalia se 'ficar fora' foi sábio.
        Computar contextual_reward baseado em lógica acima.
        """
```

### Integração ao Environment

```python
# agent/environment.py - no step()

# Se não abriu posição mas tínhamos signal
signal_had_opportunity = (action == 0 and had_signal)
if signal_had_opportunity:
    opp_id = self.opportunity_learner.register_missed_opportunity(
        symbol=self.symbol,
        step=self.current_step,
        direction=signal_direction,
        entry_price=signal_entry_price,
        confluence=signal_confidence,
        atr=current_atr,
        drawdown_pct=portfolio_dd,
        recent_trades_24h=len(recent_trades)
    )

# Depois de LOOKBACK_CANDLES, avaliar
if self.current_step - opportunity_step >= OPPORTUNIT_LOOKBACK_CANDLES:
    opp = self.opportunity_learner.evaluate_opportunity(
        opportunity_id=opp_id,
        current_price=current_price,
        max_price_reached=highest_price_in_window,
        min_price_reached=lowest_price_in_window
    )

    # Adicionar contextual_reward ao agente
    if opp:
        reward += opp.contextual_reward
        logger.info(f"Contextual learning: {opp.reasoning}")
```

---

## Cenários de Aprendizado

### Cenário 1: Prudência Correta

```
T=10:  Signal ETHUSDT LONG, confluence 8.5, entry 3500
       Drawdown: 3.2% (proteção ativada)
       Ação: Ficar fora
       Reward: +0.15 (proteção em drawdown)

T=30:  Preço desceu para 3400 (10 candles depois)
       Análise: "Se tivesse entrado, teria perdido -2.8%"
       Contextual Learning: +0.30 (recompensa forte)
       Reasoning: "Decisão sábia evitou perda"

RESULTADO: Agente aprendeu corretamente que ficar fora foi bom.
```

### Cenário 2: Ganância Errada

```
T=15:  Signal BTCUSDT LONG, confluence 9.0, entry 45000
       Drawdown: 0.5% (normal)
       Múltiplos trades: 0 (já descansou)
       Ação: Ficar fora (conservador demais?)
       Reward: 0 (sem penalidade, normal)

T=35:  Preço subiu para 45900 (+2%)
       Análise: "Se tivesse entrado, teria ganhado bom"
       Contextual Learning: -0.20 (penalidade forte)
       Reasoning: "Sem justificativa válida, desperdiçou"

RESULTADO: Agente aprendeu que ser muito conservador é prejudicial.
```

### Cenário 3: Decisão Equilibrada

```
T=20:  Signal SOLUSDT SHORT, confluence 8.2, entry 150
       Drawdown: 2.5% (proteção em drawdown)
       Oportunidade teria ganhado +1.8%
       Ação: Ficar fora
       Reward: +0.15 (proteção em drawdown)

T=40:  Preço = 148 (seria +1.3%)
       Análise: "Oportunidade boa, mas drawdown alto"
       Contextual Learning: -0.08 (penalidade leve)
       Reasoning: "Deveria ter entrado com menor size"

RESULTADO: Agente aprende balanço entre prudência e ganância.
```

---

## Impacto no Policy

### Antes (Round 5)

```
Estado: Drawdown 2.5%, signal confluence 8.5, sem trades recentes
Ação anterior: HOLD (ficar fora)
Aprendizado: +0.15 (sempre positivo, sem contexto)
Policy: "Ficar fora em drawdown é SEMPRE bom"
Resultado: Muita perda de oportunidades
```

### Depois (Round 5 + Opportunity Learning)

```
Estado: Drawdown 2.5%, signal confluence 8.5, oportunidade excelente
Ação: HOLD (ficar fora)
Aprendizado: +0.15 (proteção) - 0.08 (oportunidade desperdiçada) = +0.07
Policy: "Ficar fora é bom QUANDO oportunidade é ruim"
Resultado: Menos perda de oportunidades, mantém proteção em crises
```

---

## Métricas de Sucesso

Ao final do training, esperar:

| Métrica | Esperado | Significado |
|---------|----------|-------------|
| `wise_decisions_pct` | 70%+ | 70% das decisões de ficar fora foram corretas |
| `avg_contextual_reward` | > 0 | Aprendizado positivo em média |
| `desperate_decisions` | < 30% | Menos de 30% de decisões ruins (ganância) |
| `opportunity_quality` | GOOD+ | Oportunidades descartadas são de qualidade ruim |

---

## Tuning e Ajustes

### Aumentar Conservadorismo

```python
OPPORTUNITY_LOOKBACK_CANDLES = 30      # Observar mais tempo
DRAWDOWN_THRESHOLD_FOR_WISDOM = 2.0    # Proteção ativada mais cedo
OPPORTUNITY_PENALTY_GOOD_MOVE = -0.20  # Penalidade maior por desperdiçar
```

### Aumentar Agressividade

```python
OPPORTUNITY_MIN_CONFLUENCE = 8.0       # Só rastrear boas oportunidades
DRAWDOWN_THRESHOLD_FOR_WISDOM = 4.0    # Proteção só em drawdown extremo
OPPORTUNITY_PENALTY_GOOD_MOVE = -0.05  # Penalidade menor por desperdiçar
```

---

## Filosofia

**O agente aprende não a regra "ficar fora é bom"**
**Mas a regra mais sofisticada:**

> "Ficar fora é bom QUANDO as oportunidades desperdidas seriam ruins.
> Ficar fora é ruim QUANDO as oportunidades desperdidas seriam excelentes."

Isso é **verdadeira inteligência adaptativa**.

---

## Próximos Passos

1. ✅ Módulo `opportunity_learning.py` criado
2. ⏳ Integrar ao `environment.py` para rastrear oportunidades
3. ⏳ Conectar ao `reward.py` para adicionar contextual reward
4. ⏳ Criar testes de validação
5. ⏳ Documentar integração completa

---

## Referência

**Arquivo**: `agent/opportunity_learning.py` (290+ linhas)
**Classe Principal**: `OpportunityLearner`
**Conceito**: Meta-Learning de decisões (aprendizado sobre aprendizado)
