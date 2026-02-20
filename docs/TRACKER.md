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

## Sprint Atual: v0.3 — Training Ready 🔄 IN PROGRESS (20/02/2026)

**Duração:** 20/02 (1 dia - Sprint expedito)
**Esforço total estimado:** ~8h
**Status:** 🔴 CRÍTICO PATH — Decisão Head Finanças

| Task | Story | Status | Esforço | Prioridade |
|------|-------|--------|---------|----------|
| ✅ Implementar `step()` completo no `CryptoFuturesEnv` | US-04 | ✅ DONE | - | |
| ✅ Implementar `_get_observation()` usando `FeatureEngineer` | US-04 | ✅ DONE | - | |
| ✅ Pipeline de dados para treinamento | US-04 | ✅ DONE | - | |
| ✅ Script de treinamento funcional (`python main.py --train`) | US-04 | ✅ DONE | - | |
| 🔄 Criar teste E2E completo (3 símbolos, 10k steps) | US-04 | 🔄 IN PROGRESS | 2h | 🔴 CRÍTICA |
| 🔄 Validar treinamento (CV < 1.5 + WinRate > 45%) | US-04 | 🔄 IN PROGRESS | 1.5h | 🔴 CRÍTICA |
| 🔄 Sincronização de documentação | US-04 | 🔄 IN PROGRESS | 1h | 🔴 CRÍTICA |
| ⏳ Salvar/carregar modelo treinado (nice-to-have) | US-05 | ⏳ DEFER v0.4 | - | 🟢 MÉDIA |

## Backlog Priorizado

| Sprint | Release | Foco | Esforço Est. |
|--------|---------|------|-------------|
| Sprint 3 | v0.4 | Backtester real com métricas | ~15h |
| Sprint 4 | v0.4 | Walk-forward + relatório | ~10h |
| Sprint 5 | v0.5 | Paper trading E2E | ~15h |
| Sprint 6 | v1.0 | Execução real + circuit breakers | ~20h |
