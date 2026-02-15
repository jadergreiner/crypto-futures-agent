# 📊 Sprint Tracker — Crypto Futures Agent

## Sprint Atual: v0.2 — Pipeline Fix

**Duração:** 2 semanas
**Esforço total estimado:** ~10h

| Task | Story | Status | Esforço |
|------|-------|--------|---------|
| Atualizar `build_observation` para receber `multi_tf_result` | US-01 | ⬜ TODO | 2h |
| Preencher Bloco 7 com `correlation_btc`, `beta_btc` | US-01 | ⬜ TODO | 1h |
| Preencher Bloco 8 com `d1_bias` e `market_regime` scores | US-01 | ⬜ TODO | 1h |
| Fix R-multiple ordering no `RewardCalculator` | US-02 | ⬜ TODO | 30min |
| Sincronizar `get_feature_names()` | US-03 | ⬜ TODO | 1h |
| Teste unitário `FeatureEngineer.build_observation` | US-01 | ⬜ TODO | 2h |
| Teste unitário `MultiTimeframeAnalysis.aggregate` | US-01 | ⬜ TODO | 1h |
| Teste unitário `RewardCalculator.calculate` | US-02 | ⬜ TODO | 1h |
| Validar dry-run com valores reais nos blocos 7/8 | US-01 | ⬜ TODO | 30min |

## Backlog Priorizado

| Sprint | Release | Foco | Esforço Est. |
|--------|---------|------|-------------|
| Sprint 2 | v0.3 | `env.step()` completo + pipeline de dados para treino | ~20h |
| Sprint 3 | v0.3 | Treinamento funcional (100k+ steps) | ~15h |
| Sprint 4 | v0.4 | Backtester real com métricas | ~15h |
| Sprint 5 | v0.4 | Walk-forward + relatório | ~10h |
| Sprint 6 | v0.5 | Paper trading E2E | ~15h |
| Sprint 7 | v1.0 | Execução real + circuit breakers | ~20h |
