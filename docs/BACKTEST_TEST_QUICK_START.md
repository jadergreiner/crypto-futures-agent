# 🚀 Quick Start — Testes Backtest Engine (S2-3)

**Versão:** 1.0.0  
**QA Lead:** Member #12  
**Data:** 2026-02-22  
**Executar em:** ~1 minuto

---

## ⚡ TL;DR

10 testes prontos para executar. Coverage: ~82%. Runtime: 45-60s.

```bash
# Rodar todos os testes
cd c:\repo\crypto-futures-agent
pytest tests/test_backtest_engine.py -v

# Rodar com coverage report
pytest tests/test_backtest_engine.py --cov=backtest --cov-report=html

# Rodar em paralelo (rápido)
pytest tests/test_backtest_engine.py -n auto
```

---

## 📋 10 Testes Implementados

### Unit Tests (5) — ~8s

```bash
pytest tests/test_backtest_engine.py::TestBacktesterInit -v
pytest tests/test_backtest_engine.py::TestBacktesterValidation -v
pytest tests/test_backtest_engine.py::TestMetricsEmpty -v
pytest tests/test_backtest_engine.py::TestRiskGateDrawdown -v
pytest tests/test_backtest_engine.py::TestPnLCalculation -v
```

| Teste | Descrição | Esperado |
|-------|-----------|----------|
| UT-1 | Backtester init com 10k | ✅ PASS |
| UT-2 | Rejeita capital ≤ 0 | ✅ PASS |
| UT-3 | Métricas com zero trades | ✅ PASS |
| UT-4 | Risk gate @ -3% DD | ✅ PASS |
| UT-5 | PnL com fees | ✅ PASS |

### Integration Tests (3) — ~18s

```bash
pytest tests/test_backtest_engine.py::TestFullPipeline -v
pytest tests/test_backtest_engine.py::TestRateLimits -v
pytest tests/test_backtest_engine.py::TestMultipleSymbols -v
```

| Teste | Descrição | Esperado |
|-------|-----------|----------|
| IT-1 | Fluxo E2E: data → sim → report | ✅ PASS |
| IT-2 | Rate limits (1300+ barras) | ✅ PASS |
| IT-3 | BTC + ETH independentes | ✅ PASS |

### Regression Test (1) — ~2s

```bash
pytest tests/test_backtest_engine.py::TestRiskGateRegression -v
```

| Teste | Descrição | Esperado |
|-------|-----------|----------|
| RT-1 | Risk gate bloqueia stress trades | ✅ PASS |

### E2E Test (1) — ~12s

```bash
pytest tests/test_backtest_engine.py::TestRealisticScenario -v
```

| Teste | Descrição | Esperado |
|-------|-----------|----------|
| E2E-1 | Trending + consolidação + volatilidade | ✅ PASS |

---

## 📊 Validação de Coverage

```bash
# Gerar HTML report
pytest tests/test_backtest_engine.py \
  --cov=backtest \
  --cov-report=html:htmlcov

# Abrir report no navegador
start htmlcov/index.html
```

**Target:** 80%+ | **Plano:** ~82%

| Componente | Coverage |
|-----------|----------|
| `Backtester.__init__()` | 90% |
| `Backtester._calculate_metrics()` | 85% |
| `BacktestEnvironment.step()` | 90% |
| **Risk Gate** | **95%** |
| **Global** | **~82%** |

---

## 🔍 Rodar Teste Específico

```bash
# Apenas UT-1
pytest tests/test_backtest_engine.py::TestBacktesterInit::test_backtester_initializes_with_valid_data -v

# Com output detalhado
pytest tests/test_backtest_engine.py::TestBacktesterInit -vv --tb=long

# Com debug prints
pytest tests/test_backtest_engine.py::TestBacktesterInit -v -s
```

---

## 📁 Arquivos Entregues

| Arquivo | Linhas | Propósito |
|---------|--------|-----------|
| `docs/BACKTEST_ENGINE_TEST_PLAN.md` | 450+ | Plano detalhado completo |
| `docs/BACKTEST_TEST_PLAN_EXECUTIVE.md` | 250+ | Resumo executivo rápido |
| `tests/test_backtest_engine.py` | 650+ | Testes implementados (10) |
| `docs/STATUS_ENTREGAS.md` | SYNC | Status atualizado |
| `docs/SYNCHRONIZATION.md` | SYNC | Auditoria documentada |

---

## ✅ Checklist de Validação

Antes de submeter PR:

- [ ] Todos os 10 testes rodam com sucesso
- [ ] Coverage ≥ 80% (target 82%)
- [ ] Sem warnings ou erros
- [ ] Risk Gate testado (UT-4, RT-1, E2E-1)
- [ ] Fixtures carregam corretamente
- [ ] Tempo < 1 minuto (solo) ou < 20s (paralelo)

---

## 📞 Troubleshooting

### Erro: ModuleNotFoundError: No module named 'backtest'

```bash
# Assume você está em c:\repo\crypto-futures-agent
# Se não, mude para lá
cd c:\repo\crypto-futures-agent

# Volte a rodar
pytest tests/test_backtest_engine.py -v
```

### Erro: ModuleNotFoundError: No module named 'pytest'

```bash
pip install pytest pytest-cov
```

### Fixtures não carregando

Confirme que `conftest.py` está em `tests/`:

```bash
ls tests/conftest.py  # Deve existir
```

Se não existir, você pode copiar as fixtures de `test_backtest_engine.py` para um novo `tests/fixtures_backtest.py` e importar lá.

---

## 🎓 Documentação Relacionada

- 📄 [Full Test Plan](BACKTEST_ENGINE_TEST_PLAN.md) — Detalh completo
- 📄 [Executive Summary](BACKTEST_TEST_PLAN_EXECUTIVE.md) — Resumo 2 páginas
- 📄 [Critérios de Aceite](CRITERIOS_DE_ACEITE_MVP.md) — Requisitos MVP
- 📄 [ROADMAP](ROADMAP.md) — Timeline
- 📄 [Status de Entregas](STATUS_ENTREGAS.md) — Progress

---

**Pronto para rodar!** Execute `pytest tests/test_backtest_engine.py -v` e valide que todos passam ✅

