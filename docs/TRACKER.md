# 📊 Sprint Tracker — Crypto Futures Agent

## Sprint Concluído: v0.2 — Pipeline Fix ✅

**Duração:** 2 semanas
**Esforço total estimado:** ~10h

| Task | Story | Status | Esforço |
|------|-------|--------|---------|
| Atualizar `build_observation` para receber `multi_tf_result` | US-01 | ✅ DONE | 2h |
| Preencher Bloco 7 com `correlation_btc`, `beta_btc` | US-01 | ✅ DONE | 1h |
| Preencher Bloco 8 com `d1_bias` e `market_regime` scores | US-01 | ✅ DONE | 1h |
| Fix R-multiple ordering no `RewardCalculator` | US-02 | ✅ DONE | 30min |
| Sincronizar `get_feature_names()` | US-03 | ✅ DONE | 1h |
| Teste unitário `FeatureEngineer.build_observation` | US-01 | ✅ DONE | 2h |
| Teste unitário `MultiTimeframeAnalysis.aggregate` | US-01 | ✅ DONE | 1h |
| Teste unitário `RewardCalculator.calculate` | US-02 | ✅ DONE | 1h |
| Validar dry-run com valores reais nos blocos 7/8 | US-01 | ✅ DONE | 30min |

## Sprint Atual: v0.3 — Training Ready � OPERAÇÃO PARALELA C (20/02/2026)

**Duração:** 20/02 (1 dia - Sprint expedito)
**Esforço total estimado:** ~8h
**Status:** ✅ AUTORIZADO — Operação Paralela C (LIVE + v0.3) desde 20:30 BRT

| Task | Story | Status | Esforço | Prioridade |
|------|-------|--------|---------|----------|
| ✅ Implementar `step()` completo no `CryptoFuturesEnv` | US-04 | ✅ DONE | - | |
| ✅ Implementar `_get_observation()` usando `FeatureEngineer` | US-04 | ✅ DONE | - | |
| ✅ Pipeline de dados para treinamento | US-04 | ✅ DONE | - | |
| ✅ Script de treinamento funcional (`python main.py --train`) | US-04 | ✅ DONE | - | |
| ✅ Criar orchestrator paralelo (LIVE + v0.3) | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| ✅ Criar monitor crítico com safeagues | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| ✅ Obter autorização formal (Operação C) | US-04 | ✅ DONE | - | 🔴 CRÍTICA |
| 🔄 Criar teste E2E completo (3 símbolos, 10k steps) | US-04 | 🔄 IN PROGRESS | 2h | 🔴 CRÍTICA |
| 🔄 Validar treinamento (CV < 1.5 + WinRate > 45%) | US-04 | 🔄 IN PROGRESS | 1.5h | 🔴 CRÍTICA |
| 🔄 Debug signal generation (0 sinais) | US-04 | 🔄 IN PROGRESS | 1h | 🔴 CRÍTICA |
| 🔄 Sincronização de documentação | US-04 | 🔄 IN PROGRESS | 1h | 🔴 CRÍTICA |
| ⏳ Salvar/carregar modelo treinado (nice-to-have) | US-05 | ⏳ DEFER v0.4 | - | 🟢 MÉDIA |

## Sprint Planejado: v0.4 — Backtest Engine (21-23/02/2026)

**Duração:** 3 dias (21, 22, 23 fev)
**Esforço total estimado:** ~4.5h (core F-12) + ~2h (documentação + testes)
**Status:** ⏳ PLANEJADO — Aguarda validação v0.3 (até 23:59 BRT hoje)

| Task | Feature | Status | Esforço | Prioridade |
|------|---------|--------|---------|----------|
| Refinar história F-12 com 3 personas (PO + Finance + Tech) | F-12 | ✅ DONE | 0h | 🔴 CRÍTICA |
| Implementar BacktestEnvironment (subclasse CryptoFuturesEnv) | F-12a | ⏳ TODO | 1h | 🔴 CRÍTICA |
| Implementar BacktestDataLoader (3-camadas Parquet) | F-12b | ⏳ TODO | 1.5h | 🔴 CRÍTICA |
| Implementar TradeStateMachine (IDLE/LONG/SHORT) | F-12c | ⏳ TODO | 1.5h | 🔴 CRÍTICA |
| Implementar BacktestReporter (Text + JSON) | F-12d | ⏳ TODO | 0.5h | 🟡 ALTA |
| Escrever 8 unit tests (determinismo, SM, métricas) | F-12e | ⏳ TODO | 1h | 🔴 CRÍTICA |
| Integração `--train-and-backtest` em main.py | F-12 | ⏳ TODO | 0.5h | 🟡 ALTA |
| Sincronizar documentação (FEATURES, ROADMAP, SYNC) | F-12 | ⏳ TODO | 0.5h | 🔴 CRÍTICA |
| Teste manual end-to-end (BTCUSDT, 90 dias) | F-12 | ⏳ TODO | 0.5h | 🟡 ALTA |

**Risk Clearance Checklist** (antes expansão v0.5):

- [ ] Sharpe ≥ 1.0
- [ ] MaxDD ≤ 15%
- [ ] Win Rate ≥ 45%
- [ ] Profit Factor ≥ 1.5
- [ ] Recovery Factor ≥ 2.0
- [ ] Consecutive Losses ≤ 5

## Backlog Priorizado

| Sprint | Release | Foco | Esforço Est. |
|--------|---------|------|-------------|
| Sprint 3 | v0.4 | Backtester real com métricas | ~15h |
| Sprint 4 | v0.4 | Walk-forward + relatório | ~10h |
| Sprint 5 | v0.5 | Paper trading E2E | ~15h |
| Sprint 6 | v1.0 | Execução real + circuit breakers | ~20h |
