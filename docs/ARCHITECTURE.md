# Arquitetura do Projeto

## Resumo

Este documento consolida a arquitetura operacional do Crypto Futures Agent e
complementa o [C4_MODEL.md](C4_MODEL.md) com foco em execução real e status
atual de componentes.

- Runtime principal: Python
- Execução: CLI (`iniciar.bat`, `menu.py`) e rotinas automatizadas
- Persistência: SQLite (`db/crypto_futures.db`) + Parquet (`data/`, snapshots)
- Integrações: Binance Futures API + Telegram Alerts

---

## Camadas Arquiteturais

1. Strategy Layer (`agent/`, `indicators/`)
- SMC analysis (Order Blocks + BoS)
- Heurísticas multi-timeframe
- Inference/treinamento PPO (TASK-005)

2. Execution Layer (`execution/`, `monitoring/`)
- Execução de ordens
- Gestão de posição, SL/TP e trailing stop
- Auditoria operacional de decisões e fills

3. Risk Layer (`risk/`, `management/`)
- Gates de capital, drawdown, alavancagem e limite de posições
- Circuit breaker e bloqueios preventivos

4. Data & Persistence Layer (`data/`, `db/`, `backtest/`)
- Cache quente em SQLite
- Snapshot/analytics em Parquet
- Pipeline de backtest e métricas

---

## Estado Atual (07 MAR 2026)

- TASK-005 v2 (engenharia): concluída
- Treino longo PPO (500k steps): pendente
- Phase 3 final GO/NO-GO: pendente após treino longo

### Mudança arquitetural relevante (TASK-005 v2)

Foi introduzida separação explícita entre métrica financeira e reward de treino:

- `raw_pnl`: valor financeiro real por fechamento de trade
- `shaped_reward`: sinal de aprendizado para PPO

Foi criada fonte única para métricas em `agent/rl/metrics_utils.py`, usada por:

- `agent/rl/training_loop.py`
- `agent/rl/final_validation.py`
- `agent/rl/ppo_trainer.py` (callback de avaliação)

Essa padronização elimina divergência de Sharpe/PF entre treino e validação.

---

## Componentes Críticos RL (TASK-005)

- `agent/rl/training_env.py`
  - Responsável por step/reset, reward shaping e eventos de fechamento
  - Expõe `raw_pnl`, `shaped_reward` e `closed_trade` no `info`

- `agent/rl/training_loop.py`
  - Orquestra checkpoints, gates e artefatos de treino
  - Registra `vol_floor`, `num_trades_evaluated`, `metric_sanity_passed`, `stop_reason`

- `agent/rl/final_validation.py`
  - Executa avaliação final com mesmas fórmulas do treino
  - Define GO/NO-GO somente com critérios formais + sanity checks

- `agent/rl/phase3_executor.py`
  - Consolida aprovação por personas e decisão final

---

## Referências Cruzadas

- [BACKLOG.md](BACKLOG.md)
- [C4_MODEL.md](C4_MODEL.md)
- [DATA_FLOW_DIAGRAM.md](DATA_FLOW_DIAGRAM.md)
- [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md)
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md)
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md)
