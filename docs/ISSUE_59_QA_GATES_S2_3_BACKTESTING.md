# 🎯 QA Gates & Checklist — Issue #59 (S2-3: Backtesting)

**Versão:** 1.0  
**Data:** 2026-02-22  
**Role:** Audit (#8) — QA Lead | Documentation Officer | Audit Authority  
**Status:** 🟡 EM DEFINIÇÃO  

---

## 📋 Contexto

**Sprint 1:** 4 gates ✅ GREEN (conectividade, risco, execução, telemetria)  
**S2-3:** Backtesting requer gates similares, adaptados para:
- Carregamento e validação de dados históricos
- Engine de backtesting (simulação de trades)
- Testes e validação de regressão
- Documentação técnica completa

---

## 🚦 Os 4 Gates para S2-3

### **Gate 1: Dados Históricos** ✅

**Objetivo:** Validar que dados históricos estão disponíveis, íntegros e cachê funciona.

| Aspecto | Critério de Aceite | Como Validar | Evidência | Automatizado |
|---------|-------------------|--------------|-----------|:---:|
| **Carregamento** | Dados OHLCV carregados para 60 símbolos | `pytest tests/test_backtest_data.py` | Log PASS | ✅ |
| **Integridade** | Sem gaps, sem duplicatas, preços válidos | Verificar `backtest/cache/*.parquet` | Relatório validação | ✅ |
| **Cache** | Parquet em `backtest/cache/` funciona | Executar engine com cache hit | Tempo < 100ms | ✅ |
| **Período** | Mínimo 6 meses de dados históricos | Query `data_cache.py` | SQL query result | ✅ |

**Responsável:** Data Engineer  
**Timeout sign-off:** 48h após PRsubmissão

---

### **Gate 2: Engine de Backtesting** ✅

**Objetivo:** Engine simula trades, calcula PnL/Drawdown e respeita Risk Gate 1.0 (inviolável).

| Aspecto | Critério de Aceite | Como Validar | Evidência | Automatizado |
|---------|-------------------|--------------|-----------|:---:|
| **Simulação** | Engine executa trade sem erro | `pytest tests/test_backtest_core.py` | Log PASS | ✅ |
| **Cálculo PnL** | PnL realized + unrealized correto | Validar `backtest_metrics.py` | Resultados vs manual | ✅ |
| **Drawdown** | Max Drawdown calculado (≤ histórico) | Relatório após backtest | Gráfico equity curve | ✅ |
| **Risk Gate** | Stop Loss aplicado em -3% | Simular posição com loss -3.1% | Ordem close registrada | ✅ |
| **Walk-Forward** | Engine suporta walk-forward testing | Executar `walk_forward.py` | Resultados separados por janela | ✅ |

**Responsável:** Backend/RL Engineer  
**Timeout sign-off:** 48h após PR submission

---

### **Gate 3: Validação & Testes** ✅

**Objetivo:** 8 testes PASS, coverage ≥ 80%, sem regressão em Sprint 1.

| Aspecto | Critério de Aceite | Como Validar | Evidência | Automatizado |
|---------|-------------------|--------------|-----------|:---:|
| **Testes Core** | 8 testes passam (backtest + metrics + trade_state) | `pytest backtest/test_*.py -v` | 8/8 PASS | ✅ |
| **Coverage** | Cobertura ≥ 80% em `backtest/` | `pytest --cov=backtest --cov-report=html` | Relatório HTML | ✅ |
| **Regressão S1** | Nenhuma quebra em connectivity/risk/execution | `pytest tests/ -v` | 70 testes PASS | ✅ |
| **Performance** | Backtest 6 meses × 60 símbolos < 30s | Time exec completo | Log timestamp | ✅ |

**Responsável:** QA Lead + Backend Engineer  
**Timeout sign-off:** 24h pós-evidência

---

### **Gate 4: Documentação** ✅

**Objetivo:** Código comentado, README de backtesting, critérios atualizados.

| Aspecto | Critério de Aceite | Como Validar | Evidência | Automatizado |
|---------|-------------------|--------------|-----------|:---:|
| **Docstrings** | Classes/funções principais têm docstrings (PT) | Revisar `backtest/*.py` | Code review ✓ | ❌ Manual |
| **README** | `backtest/README.md` com guia de uso | Arquivo existe, mínimo 500 palavras | Arquivo completo | ❌ Manual |
| **Critérios** | `docs/CRITERIOS_DE_ACEITE_MVP.md` atualizado com S2-3 | Verificar seção S2-3 | Commit com [SYNC] | ❌ Manual |
| **Decisões** | Trade-offs críticos logados em `docs/DECISIONS.md` | Verificar seção S2-3 backtest | Novo entry criado | ❌ Manual |
| **Comentários** | Lógica complexa em `trade_state_machine.py`, `walk_forward.py` comentada | Code review | Inline comments PT | ❌ Manual |

**Responsável:** Documentation Officer + Backend Engineer  
**Timeout sign-off:** 24h pós-evidência

---

## 📝 Checklist de Documentação (5-6 Itens)

- [ ] **Docstrings PT** — Todas as classes e funções principais têm docstrings em português  
  - `backtester.py`: `Backtester`, `run_backtest()`
  - `backtest_environment.py`: `BacktestEnvironment`, `step()`, `reset()`
  - `backtest_metrics.py`: `BacktestMetrics`, `calculate_pnl()`, `calculate_drawdown()`
  - `trade_state_machine.py`: `TradeStateMachine`, `transition()`
  - `walk_forward.py`: `WalkForwardBacktest`, `run()`

- [ ] **README Backtesting** — `backtest/README.md` criado com:
  - Descrição geral do engine
  - Exemplo de uso básico (5+ linhas código)
  - Como interpretar resultados (PnL, Drawdown, Sharpe, Calmar)
  - Como rodar backtest com parâmetros customizados
  - Troubleshooting (cache, dados, performance)

- [ ] **Atualizar CRITERIOS_DE_ACEITE_MVP.md** — Adicionar seção S2-3:
  - 4 tópicos de critério (Dados, Engine, Testes, Documentação)
  - Tabela com validações (como Sprint 1)
  - Checklist go/no-go final

- [ ] **LOG em DECISIONS.md** — Nova seção "DECISÃO #X — BACKTESTING S2-3":
  - Trade-offs arquiteturais (e.g., Parquet vs CSV, Walk-Forward vs Historical)
  - Justificativa de métricas (Sharpe, Calmar, Profit Factor)
  - Decisões sobre Risk Gate em backtest (sempre -3% hard stop)
  - Opções rejeitadas e por quê

- [ ] **Comentários Inline** — Código comentado em português:
  - Lógica de cálculo de drawdown (máximo running)
  - State machine transitions (abrir → fechar → aguardar)
  - Walk-forward train/test split logic

- [ ] **SYNCHRONIZATION.md** — Adicionar entrada [SYNC]:
  ```
  [SYNC] 2026-02-22 S2-3 Gates + Docs criados (CRITERIOS + DECISIONS + README)
  ```

---

## 👤 Matriz de Responsabilidades

| Gate | Descrição | Responsável | Sign-off | Timeline |
|------|-----------|---|:-:|---|
| **Gate 1: Dados** | Dados históricos carregados, validados, cache funciona | Data Engineer | 1️⃣ Audit | 48h |
| **Gate 2: Engine** | Engine simula, calcula PnL/Drawdown, respeita Risk Gate | Backend/RL Eng | 2️⃣ Audit | 48h |
| **Gate 3: Testes** | 8 testes PASS, 80%+ coverage, sem regressão | QA Lead | 3️⃣ QA/Audit | 24h |
| **Gate 4: Docs** | Docstrings, README, critérios, decisões, sync | Doc Officer | 4️⃣ Audit | 24h |

**Fluxo de Sign-off:**
1. Backend Engineer → Gate 1 + 2 completo
2. QA Lead → Gate 3 (testes)
3. Documentation Officer → Gate 4 (docs)
4. **Audit (#8)** → Validação final dos 4 gates + checklist
5. **Product Lead** → Aprovação para merge

---

## 🎯 Checklist Go/No-Go — S2-3

| Gate | Status | Evidência |
|------|:------:|:---------:|
| ✅ Gate 1: Dados | 🟡 | Aguardando PR |
| ✅ Gate 2: Engine | 🟡 | Aguardando PR |
| ✅ Gate 3: Testes | 🟡 | Aguardando PR |
| ✅ Gate 4: Docs | 🟡 | Aguardando PR |
| **GO/NO-GO** | 🟡 | **AGUARDANDO GATES** |

---

## 📌 Referência Rápida — Código de Saída

Quando todos os gates ✅ GREEN, commit final deve ser:

```bash
git commit -am "[SYNC] S2-3 QA Gates completo + Documentação atualizada

- Gate 1 (Dados): ✅ 60 símbolos, 6+ meses, cache OK
- Gate 2 (Engine): ✅ Simulação, PnL, Drawdown, Risk Gate 1.0 inviolável
- Gate 3 (Testes): ✅ 8/8 PASS, 80%+ coverage, 0 regressões
- Gate 4 (Docs): ✅ Docstrings PT, README, CRITERIOS + DECISIONS sync

Issue #59 ready for merge."
```

---

## 🔒 Invioláveis (Risk Gate 1.0 em Backtest)

- ❌ **Nunca desabilitar** stop loss hardcoded em -3%
- ❌ **Nunca permitir** backtest sem validação de Risk Gate
- ❌ **Nunca ignorar** dados corrompidos (gap, duplicata)
- ❌ **Nunca aceitar** coverage < 80%

---

**Audit Sign-off:** 🟡 Pendente  
**Data esperada de conclusão:** 2026-02-24  
**Último update:** 2026-02-22 22:50 UTC

