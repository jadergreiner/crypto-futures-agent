---
name: performance-review
description: |
  Analise de metricas de reward e Sharpe por janela temporal.
  Cobre treinamento RL, backtest walk-forward e execucao live/shadow.
  Emite diagnostico com severidade e acao recomendada.
metadata:
  tags:
    - performance
    - reward
    - sharpe
    - metricas
    - rl
    - backtest
  focus:
    - evidencias-objetivas
    - janela-temporal
    - diagnostico-direto
user-invocable: true
---

# Skill: performance-review

## Objetivo

Analisar metricas de reward e Sharpe do sistema por janela temporal e
emitir diagnostico objetivo com severidade e acao recomendada.

Use esta skill para:

- verificar se o reward medio esta em plateau ou degradando
- calcular e avaliar Sharpe de backtest por janela walk-forward
- comparar performance live/shadow com baseline treinado
- identificar degradacao de modelo antes que afete operacao
- subsidiar decisoes de retreino ou ajuste de hiperparametros

## Modo Economico

Regra principal: ler apenas o necessario para a janela solicitada.

Ordem de leitura:

1. Dados de episodios/treino no banco (`rl_episodes`, `rl_training_log`)
   — sempre primeiro para reward RL.
2. `agent/convergence_monitor.py` e `logs/training_metrics/metrics.csv`
   — para historico de convergencia e plateau.
3. `backtest/backtest_metrics.py` e `backtest/walk_forward.py`
   — apenas se a analise envolver Sharpe de backtest.
4. `monitoring/performance.py` — para metricas de execucao live/shadow.
5. `core/model2/cycle_report.py` e tabela `signal_executions`
   — apenas se a janela incluir PnL de posicoes reais.
6. `config/ppo_config.py`, `config/risk_params.py`
   — apenas para comparar com thresholds configurados.

Evitar:

- recalcular metricas quando os scripts de diagnostico ja as fornecem
- abrir arquivos de treinamento sem definir a janela primeiro
- propor retreino sem evidencia de plateau ou degradacao confirmada

## Janelas Temporais Padrao

| Janela | Uso tipico | Fonte |
|---|---|---|
| Ultimos 100 episodios | Monitoramento de plateau | `rl_episodes` |
| Ultimas 500 epocas | Tendencia de reward | `rl_training_log` |
| 14 dias corridos | Degradacao operacional | `signal_executions` |
| 30 dias (walk-forward) | Sharpe por janela | `backtest/walk_forward.py` |
| 365 dias (treino) | Baseline de referencia | `WalkForward` config |
| Desde ultimo retreino | Drift pos-deploy | `rl_episodes + rl_training_log` |

Se o usuario nao especificar janela, usar "ultimos 100 episodios" para
reward RL e "ultimos 30 dias" para metricas live/shadow.

## Areas de Analise

### 1. Reward por Episodio (RL)

**Tabelas:** `rl_episodes`, `rl_training_log` em `db/modelo2.db`.

**Metricas extraidas:**

- `avg_reward` — media da janela
- `reward_trend` — inclinacao por regressao linear simples
- `plateau_score` — quantos episodios sem melhora relevante
- `best_reward` e `worst_reward` da janela

**Thresholds de severidade:**

| Condicao | Severidade |
|---|---|
| `avg_reward` caiu > 20% vs baseline | `CRITICO` |
| Plateau > 100 episodios sem melhora | `MODERADO` |
| `avg_reward` estaticamente plano (trend ~0) | `INFORMATIVO` |
| `avg_reward` crescente | `OK` |

**Diagnostico rapido (SQL):**

```sql
-- Reward medio por bloco de 100 episodios
SELECT
    (id / 100) AS bloco,
    COUNT(*) AS episodios,
    ROUND(AVG(reward), 4) AS avg_reward,
    ROUND(MIN(reward), 4) AS min_reward,
    ROUND(MAX(reward), 4) AS max_reward
FROM rl_episodes
ORDER BY bloco DESC
LIMIT 10;

-- Ultimos 5 registros de treino
SELECT id, episodes_used, avg_reward, model_version, completed_at
FROM rl_training_log
ORDER BY completed_at DESC
LIMIT 5;

-- Episodios desde o ultimo retreino (drift pos-deploy)
SELECT COUNT(*) AS episodios_novos,
       ROUND(AVG(reward), 4) AS avg_reward_novo,
       MIN(created_at) AS inicio, MAX(created_at) AS fim
FROM rl_episodes
WHERE created_at > (
    SELECT MAX(completed_at) FROM rl_training_log
);
```

**Script de diagnostico:**

```bash
python check_episodes_live.py   # contagem por tabela e status PPO
```

---

### 2. Sharpe Ratio (Backtest)

**Formula usada no projeto:**

$$\text{Sharpe} = \frac{\bar{r} - r_f}{\sigma_r} \times \sqrt{252}$$

Onde:
- $\bar{r}$ = retorno diario medio
- $r_f$ = 0.0000792 (equivalente diario de 2% a.a.)
- $\sigma_r$ = desvio padrao dos retornos diarios
- $\sqrt{252}$ = fator de anualização

**Arquivo:** `backtest/backtest_metrics.py` →
`BacktestMetrics.calculate_from_equity_curve()`

**Walk-forward:** `backtest/walk_forward.py`
— janelas de 365d treino + 30d teste, agrega Sharpe medio.

**Thresholds (de `backtest_metrics.py` `risk_clearance_status`):**

| Metrica | Threshold minimo | Gate |
|---|---|---|
| Sharpe Ratio | ≥ 1.0 | Obrigatorio |
| Max Drawdown | ≤ 15% | Obrigatorio |
| Win Rate | ≥ 45% | Obrigatorio |
| Profit Factor | ≥ 1.5 | Obrigatorio |
| Calmar Ratio | ≥ 2.0 | Recomendado |
| Consecutive Losses | ≤ 5 | Obrigatorio |

**Severidade por Sharpe:**

| Valor | Severidade |
|---|---|
| < 0.5 | `CRITICO` — abaixo do aceitavel |
| 0.5 – 0.99 | `MODERADO` — abaixo do gate minimo |
| 1.0 – 1.49 | `OK` — acima do gate, mas margem estreita |
| ≥ 1.5 | `BOM` — solido |
| ≥ 2.0 | `EXCELENTE` |

**Como rodar walk-forward:**

```python
from backtest.walk_forward import WalkForward
from backtest.backtester import Backtester

wf = WalkForward(backtester=Backtester(), train_days=365, test_days=30)
results = wf.run(symbol="BTCUSDT", timeframe="H4")
# results["avg_sharpe"], results["windows"]
```

---

### 3. Metricas de Execucao Live/Shadow

**Tabela:** `signal_executions` em `db/modelo2.db`.

**Calculo de PnL realizado (posicoes EXITED):**

```
gross_pnl = (exit_price - filled_price) × filled_qty  [LONG]
gross_pnl = (filled_price - exit_price) × filled_qty  [SHORT]
entry_fee  = (filled_price × filled_qty) × 0.00075
exit_fee   = (exit_price  × filled_qty) × 0.001
net_pnl    = gross_pnl - entry_fee - exit_fee
```

**Diagnostico rapido (SQL):**

```sql
-- Resumo de performance por janela (ultimos 14 dias)
SELECT
    symbol,
    COUNT(*) AS trades,
    SUM(CASE WHEN exit_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN exit_reason = 'STOP_LOSS'   THEN 1 ELSE 0 END) AS losses,
    ROUND(100.0 * SUM(CASE WHEN exit_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1) AS win_rate_pct,
    ROUND(AVG(
        CASE signal_side
            WHEN 'LONG'  THEN (exit_price - filled_price)
            WHEN 'SHORT' THEN (filled_price - exit_price)
        END * filled_qty
    ), 4) AS avg_gross_pnl
FROM signal_executions
WHERE status = 'EXITED'
  AND exited_at > (strftime('%s','now') - 14 * 86400) * 1000
GROUP BY symbol
ORDER BY trades DESC;

-- R-multiple medio por janela
SELECT
    ROUND(
        AVG(ABS((exit_price - filled_price) / NULLIF(ABS(filled_price - stop_loss_price), 0)))
    , 2) AS avg_r_multiple
FROM signal_executions
WHERE status = 'EXITED'
  AND exited_at > (strftime('%s','now') - 30 * 86400) * 1000;

-- Sequencia maxima de perdas consecutivas
-- (requer analise em Python — ver monitoring/performance.py)
```

**Scripts de diagnostico:**

```bash
python resumo_ciclo.py          # win_rate, signals, posicoes ativas
python monitoring/performance.py  # sharpe_ratio, profit_factor, max_drawdown
```

**Thresholds de alerta operacional:**

| Metrica | Alerta | Bloqueio |
|---|---|---|
| Win Rate | < 45% | — |
| Drawdown diario | > 3% | > 5% (bloqueia 24h) |
| Drawdown total | > 10% | > 15% (pausa agente) |
| R-multiple medio | < 1.5 (alerta) | < 1.0 (retreino urgente) |
| Perdas consecutivas | > 3 | > 5 |

---

### 4. Dados de Convergencia do Treino

**Arquivo:** `logs/training_metrics/metrics.csv`

Formato: `step, reward_mean, ep_len_mean, kl_divergence, ...`

**Verificar:**

- `reward_mean` por bloco de 1000 steps — tendencia crescente?
- `kl_divergence` — threshold critico: > 0.05 indica instabilidade
- Plateau: sem melhora em `reward_mean` por > 100 episodios
  (`convergence_monitor.no_improve_episodes = 100`)

**Diagnostico rapido:**

```python
import pandas as pd
df = pd.read_csv("logs/training_metrics/metrics.csv")
print(df.tail(20)[["step", "reward_mean", "kl_divergence"]])
# Verificar tendencia das ultimas 20 linhas
trend = df["reward_mean"].tail(100).diff().mean()
print(f"Tendencia (delta medio): {trend:.5f}")
```

---

## Fluxo Operacional

1. Definir **janela temporal** e **area de analise**:
   - reward RL | Sharpe backtest | execucao live | convergencia
2. Executar as queries/scripts mais diretos para a janela.
3. Calcular ou extrair as metricas criticas.
4. Classificar severidade por area (tabelas acima).
5. Identificar causa raiz se houver degradacao:
   - Plateau: dados novos insuficientes ou hiperparametros saturados?
   - Sharpe caindo: regime de mercado mudou ou overfitting?
   - Win rate baixo: sinal fraco ou execucao com slippage?
6. Emitir diagnostico no formato padrao (ver abaixo).
7. Se severidade `CRITICO`: sugerir acao imediata antes de prosseguir.

## Decisao de Retreino

Acionar retreino quando **qualquer** condicao `CRITICO` for confirmada
**ou** quando duas ou mais condicoes `MODERADO` coexistirem:

| Condicao | Nivel |
|---|---|
| `avg_reward` caiu > 20% vs baseline | `CRITICO` |
| Plateau > 100 episodios confirmado | `MODERADO` |
| Sharpe < 0.5 em backtest recente | `CRITICO` |
| Win rate < 40% por 14 dias | `MODERADO` |
| R-multiple medio < 1.0 | `CRITICO` |
| KL divergence > 0.05 persistente | `MODERADO` |
| Drawdown total > 10% sem recuperacao | `MODERADO` |

**Comando de retreino:**

```bash
python main.py --train           # retreino geral
python main.py --train --symbols "BTCUSDT,ETHUSDT"  # por simbolo
```

Antes do retreino verificar:
- Has pelo menos 500 episodios novos em `rl_episodes`?
- Dados OHLCV atualizados ate hoje?

## Guardrails

- Nao propor retreino com menos de 200 episodios novos — resultado sera
  estatisticamente irrelevante.
- Sharpe calculado sem anualização (sem √252) nao e comparavel com os
  thresholds do sistema — sempre confirmar fator usado.
- Nao usar win_rate isolado: profit_factor e R-multiple sao mais
  informativos para este sistema.
- Em modo live, degradacao de Sharpe abaixo de 1.0 deve ser escalada
  antes de qualquer alteracao de parametro.
- Nunca desabilitar `risk_gate.py` ou `circuit_breaker.py` para
  "melhorar" metricas de execucao.

## Formato de Resposta

```
AREA: <reward_rl | sharpe_backtest | execucao_live | convergencia>
JANELA: <ex: ultimos 100 episodios | 14 dias | walk-forward 30d>
SIMBOLO: <BTCUSDT | todos | N/A>
SEVERIDADE: <OK | INFORMATIVO | MODERADO | CRITICO>

METRICAS:
  avg_reward:      <valor>  (baseline: <valor>)
  sharpe_ratio:    <valor>  (gate: >= 1.0)
  win_rate:        <valor>% (gate: >= 45%)
  max_drawdown:    <valor>% (gate: <= 15%)
  profit_factor:   <valor>  (gate: >= 1.5)
  avg_r_multiple:  <valor>  (alvo: >= 2.0)
  episodes_drift:  <N> episodios desde ultimo retreino

DIAGNOSTICO:
  - <achado objetivo 1>
  - <achado objetivo 2>

ACAO RECOMENDADA:
  T+0: <acao imediata se CRITICO>
  T+1: <acao de seguimento>
  RETREINO: <SIM | NAO | AVALIAR> — <justificativa>
```

Para analises `OK` ou `INFORMATIVO`, saida pode ser mais curta,
omitindo secoes sem dados relevantes.
