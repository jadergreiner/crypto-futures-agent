# 🧩 Features — Crypto Futures Agent

## v0.2 — Pipeline Fix

| ID | Feature | Prioridade | Status |
|----|---------|-----------|--------|
| F-01 | Integrar `multi_tf_result` no `build_observation` (Blocos 7 e 8) | 🔴
CRÍTICA | ✅ DONE |
| F-02 | Adicionar FVG distance features (indices 13-14 do SMC estavam mapeados
para sweeps, não FVGs) | 🟡 ALTA | ✅ DONE |
| F-03 | Fix bug no `RewardCalculator` — lógica `r_multiple > 3.0` nunca era
atingida (elif após if > 2.0) | 🟡 ALTA | ✅ DONE |
| F-04 | Validar `get_feature_names()` vs `build_observation()` — contagem dos
nomes não batia 100% | 🟡 ALTA | ✅ DONE |
| F-05 | Testes unitários para cada bloco de features | 🟢 MÉDIA | ✅ DONE |

## v0.2.1 — Administração de Posições (20/02/2026)

| ID | Feature | Prioridade | Status |
|----|---------|-----------|--------|
| F-05a | Configuração de 9 pares USDT em Profit Guardian Mode | 🔴 CRÍTICA | ✅
DONE |
| F-05b | Criação de 4 novos playbooks especializados (TWT, LINK, OGN, IMX) | 🔴
CRÍTICA | ✅ DONE |
| F-05c | Mecanismos de sincronização obrigatória de documentação | 🟡 ALTA | ✅
DONE |
| F-05d | Arquivo de rastreamento SYNCHRONIZATION.md | 🟡 ALTA | ✅ DONE |
| F-05e | Validação completa com test_admin_9pares.py (36/36 OK) | 🟢 MÉDIA | ✅
DONE |

## v0.3 — Training Ready (OPERAÇÃO PARALELA C)

| ID | Feature | Prioridade | Status |
|----|---------|-----------|--------|
| F-06 | Implementar `step()` completo no `CryptoFuturesEnv` | 🔴 CRÍTICA | ✅
DONE (20/02) |
| F-07 | Implementar `_get_observation()` usando `FeatureEngineer` | 🔴 CRÍTICA |
✅ DONE (20/02) |
| F-08 | Pipeline de dados para treinamento (carregar do DB → DataFrames) | 🔴
CRÍTICA | ✅ DONE (20/02) |
| F-09 | Script de treinamento funcional (`python main.py --train`) | 🔴 CRITICA
| 🔄 IN PROGRESS |
| F-10 | Teste E2E de pipeline completo (load → train → save → load) | 🔴 CRÍTICA
| 🔄 IN PROGRESS |
| F-11 | Reward shaping refinado com curriculum learning | 🟡 ALTA | ⏳ Validação
em v0.3 |
| F-13 | Orchestrator paralelo (LIVE + v0.3 isolados) | 🔴 CRÍTICA | ✅ DONE
(20/02 20:15) |
| F-14 | Monitor crítico com health checks (60s) + kill switch (2% loss) | 🔴
CRÍTICA | ✅ DONE (20/02 20:15) |
| F-15 | Autorização formal (AUTHORIZATION_OPÇÃO_C_20FEV.txt) | 🔴 CRÍTICA | ✅
DONE (20/02 20:30) |

## v0.4 — Backtest Engine (21-23/02/2026)

| ID | Feature | Prioridade | Status | Detalhes |
|----|---------|-----------|--------|----------|
| F-12 | Backtester funcional com 6 métricas + Risk Clearance | 🔴 CRÍTICA | ⏳
TODO | Sharpe≥1.0, MaxDD≤15%, WR≥45%, PF≥1.5, CFactor≥2.0, ConsecLosses≤5 |
| F-12a | BacktestEnvironment (subclasse CryptoFuturesEnv) | 🔴 CRÍTICA | ⏳ TODO
| Determinístico, reutiliza 95% de step() |
| F-12b | Data pipeline 3-camadas (cache Parquet) | 🔴 CRÍTICA | ⏳ TODO | 6-10x
mais rápido que SQLite direto |
| F-12c | TradeStateMachine (IDLE/LONG/SHORT) | 🔴 CRÍTICA | ⏳ TODO | Rastreia
posições + calcula PnL com fees |
| F-12d | Reporter (Text + JSON) | 🟡 ALTA | ⏳ TODO | Relatório legível em
terminal + estruturado |
| F-12e | 8 unit tests (determinismo, state machine, metrics) | 🔴 CRÍTICA | ⏳
TODO | Coverage de validação core |
| F-13 | Walk-forward com janelas train/test | 🟡 ALTA | ⏳ Após F-12 | Valida
retreinamento incremental (v0.4.1) |
| F-14 | Métricas extras (Sortino, Calmar) | 🟡 ALTA | ⏳ Após F-12 | Análise mais
profunda |
| F-15 | Equity curve plot com matplotlib | 🟡 ALTA | ⏳ Após F-12 | Visualização
de performance |

## v0.5 — Paper Trading

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-17 | Scheduler operacional com ciclos H4 | 🔴 CRÍTICA |
| F-18 | Execução simulada (paper) com tracking de PnL | 🔴 CRÍTICA |
| F-19 | Logs estruturados de cada decisão | 🟡 ALTA |
| F-20 | Dashboard simples em terminal (posições, PnL, sinais) | 🟢 MÉDIA |

## v1.0 — Live MVP

| ID | Feature | Prioridade |
|----|---------|-----------|
| F-21 | Execução real de ordens via Binance SDK | 🔴 CRÍTICA |
| F-22 | Circuit breaker (pause se drawdown > 10%) | 🔴 CRÍTICA |
| F-23 | Validação dupla antes de cada ordem | 🔴 CRÍTICA |
| F-24 | Alertas (arquivo de log ou webhook simples) | 🟡 ALTA |
| F-25 | Capital inicial limitado (micro-posições) | 🟡 ALTA |
