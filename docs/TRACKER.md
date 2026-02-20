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

## Sprint Atual: v0.3 — Training Ready

**Duração:** 3 semanas
**Esforço total estimado:** ~20h

| Task | Story | Status | Esforço |
|------|-------|--------|---------|
| Implementar `step()` completo no `CryptoFuturesEnv` | US-04 | ✅ DONE | 3h |
| Implementar `_get_observation()` usando `FeatureEngineer` | US-04 | ✅ DONE | 2h |
| Pipeline de dados para treinamento (carregar do DB → DataFrames) | US-04 | ✅ DONE | 4h |
| Script de treinamento funcional (`python main.py --train`) | US-04 | ✅ DONE | 3h |
| Reward shaping refinado com curriculum learning | US-04 | ⬜ TODO | 3h |
| Salvar/carregar modelo treinado | US-05 | ⬜ TODO | 2h |
| Teste E2E de treinamento | US-04 | ⬜ TODO | 3h |

## Backlog Priorizado

| Sprint | Release | Foco | Esforço Est. |
|--------|---------|------|-------------|
| Sprint 3 | v0.4 | Backtester real com métricas | ~15h |
| Sprint 4 | v0.4 | Walk-forward + relatório | ~10h |
| Sprint 5 | v0.5 | Paper trading E2E | ~15h |
| Sprint 6 | v1.0 | Execução real + circuit breakers | ~20h |
