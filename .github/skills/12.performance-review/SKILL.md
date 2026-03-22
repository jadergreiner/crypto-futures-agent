---
name: 12.performance-review
description: |
  Revisa reward, Sharpe e degradacao por janela temporal.
  Emite diagnostico curto com severidade e acao recomendada.
metadata:
  workflow-track: apoio
  workflow-order: 2
  workflow-stage: 12
  focus:
    - janela-temporal
    - thresholds-objetivos
    - saida-curta
user-invocable: true
---

# Skill: performance-review

## Objetivo

Avaliar reward, Sharpe e performance live ou shadow sem abrir analise ampla.

## Janelas Padrao

- reward RL: ultimos 100 episodios
- tendencia de treino: ultimas 500 epocas
- live ou shadow: ultimos 14 dias
- walk-forward: ultimos 30 dias

Se o usuario nao definir janela, usar as janelas acima.

## Leitura Minima

1. Banco de treino: `rl_episodes`, `rl_training_log`.
2. Convergencia: `agent/convergence_monitor.py`,
   `logs/training_metrics/metrics.csv`.
3. Backtest: `backtest/backtest_metrics.py`, `backtest/walk_forward.py`.
4. Live ou shadow: `monitoring/performance.py`, `signal_executions`.
5. Configs so para comparar thresholds: `config/ppo_config.py`,
   `config/risk_params.py`.

## Thresholds Minimos

- Reward: queda > 20% vs baseline = `CRITICO`.
- Plateau > 100 episodios = `MODERADO`.
- Sharpe < 0.5 = `CRITICO`.
- Sharpe entre 0.5 e 0.99 = `MODERADO`.
- Sharpe >= 1.0 = `OK`.
- Drawdown total > 15% = bloqueio.
- Win rate < 45% = alerta.

## Guardrails

- Nao propor retreino sem degradacao confirmada.
- Nao usar win rate isolado para decidir mudanca de modelo.
- Em modo live, Sharpe < 1.0 exige escalacao antes de ajuste.
- Nunca desabilitar `risk_gate.py` ou `circuit_breaker.py`.

## Saida

- janela analisada
- metricas principais
- severidade
- causa provavel
- acao recomendada

Limite alvo: 8-12 linhas.