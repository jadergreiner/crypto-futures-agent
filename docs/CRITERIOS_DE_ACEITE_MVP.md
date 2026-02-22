# ✅ Critérios de Aceite — MVP (Now)

**Versão:** 1.0.0
**Última atualização:** 2026-02-22

---

## 🔗 Links Rápidos

- [ROADMAP](ROADMAP.md)
- [Status de Entregas](STATUS_ENTREGAS.md)
- [Plano de Sprints](PLANO_DE_SPRINTS_MVP_NOW.md)
- [Runbook Operacional](RUNBOOK_OPERACIONAL.md)

---

## 📋 Matriz de Critérios — Sprint 1 + Sprint 2-3

### S1-1 — Integração de Conectividade {#s1-1}

| Critério                                | Como validar                          | Evidência       | Automatizado? | Status |
|-----------------------------------------|---------------------------------------|-----------------|---------------|--------|
| REST API conecta sem erro               | `pytest tests/test_api_key.py`        | Log de saída    | ✅ Sim        | 🟡     |
| WebSocket recebe dados em tempo real    | Executar `main.py` por 60s            | Log streams     | ❌ Manual     | 🟡     |
| Rate limits respeitados (<1200 req/min) | Monitorar logs por 5min               | Log contadores  | ❌ Manual     | 🟡     |

### S1-2 — Risk Gate 1.0 {#s1-2}

| Critério                                    | Como validar                              | Evidência        | Automatizado? | Status |
|---------------------------------------------|-------------------------------------------|------------------|---------------|--------|
| Stop Loss hardcoded ativa em -3% de drawdown | `pytest tests/test_protections.py`        | Resultado pytest | ✅ Sim        | 🟡     |
| Circuit Breaker fecha posição em -3%         | Simular queda de -3.1% em paper mode     | Log close order  | ❌ Manual     | 🟡     |
| Risk Gate não pode ser desabilitado          | Revisar código `risk/`                    | Code review      | ❌ Manual     | 🟡     |

### S1-3 — Módulo de Execução {#s1-3}

| Critério                                      | Como validar                          | Evidência           | Automatizado? | Status |
|-----------------------------------------------|---------------------------------------|---------------------|---------------|--------|
| Ordens market executam sem erro               | Executar em paper mode por 30min      | Log ordens          | ❌ Manual     | 🟡     |
| Tratamento de erros de API (retry e fallback) | Desconectar API e observar retry      | Log retry events    | ❌ Manual     | 🟡     |
| Rate limits de ordem respeitados              | Monitorar via dashboard               | Dashboard metrics   | ❌ Manual     | 🟡     |

### S1-4 — Telemetria Básica {#s1-4}

| Critério                                   | Como validar                            | Evidência          | Automatizado? | Status |
|--------------------------------------------|-----------------------------------------|--------------------|---------------|--------|
| Logs estruturados gerados por trade        | Executar um trade em paper mode         | Arquivo de log     | ❌ Manual     | 🟡     |
| Logs contêm: símbolo, preço, PnL, motivo  | Inspecionar arquivo de log              | Log entry example  | ❌ Manual     | 🟡     |
| Auditoria permite reconstruir histórico    | Consultar `db/crypto_agent.db`          | Query SQL resultado | ❌ Manual    | 🟡     |

---

## � Matriz de Critérios — Sprint 2-3 (Backtesting)

### S2-3 — Backtesting Engine {#s2-3}

#### Gate 1: Dados Históricos

| Critério                                | Como validar                          | Evidência       | Automatizado? | Status |
|-----------------------------------------|---------------------------------------|-----------------|---------------|--------|
| Dados OHLCV carregados para 60 símbolos | `pytest tests/test_backtest_data.py`  | Log PASS        | ✅ Sim        | 🟡     |
| Sem gaps, duplicatas, preços válidos    | Validar `backtest/cache/*.parquet`    | Relatório valid | ✅ Sim        | 🟡     |
| Parquet cache funciona (< 100ms)        | Executar engine com cache hit         | Tempo read      | ✅ Sim        | 🟡     |
| Mínimo 6 meses de dados por símbolo     | Query `data_cache.py`                 | Query result    | ✅ Sim        | 🟡     |

#### Gate 2: Engine de Backtesting

| Critério                                  | Como validar                          | Evidência       | Automatizado? | Status |
|-------------------------------------------|---------------------------------------|-----------------|---------------|--------|
| Engine executa trade sem erro             | `pytest tests/test_backtest_core.py`  | 8/8 PASS        | ✅ Sim        | 🟡     |
| PnL realized + unrealized correto         | Validar `backtest_metrics.py`         | Cálculos verif  | ✅ Sim        | 🟡     |
| Max Drawdown calculado corretamente       | Relatório após backtest               | Valor vs manual | ✅ Sim        | 🟡     |
| Risk Gate 1.0 aplicado (-3% hard stop)    | Simular posição com loss -3.1%        | Ordem close     | ✅ Sim        | 🟡     |
| Walk-Forward testing suportado            | Executar `walk_forward.py`            | Resultados sep  | ✅ Sim        | 🟡     |

#### Gate 3: Validação & Testes

| Critério                                  | Como validar                          | Evidência       | Automatizado? | Status |
|-------------------------------------------|---------------------------------------|-----------------|---------------|--------|
| 8 testes PASS (backtest + metrics)        | `pytest backtest/test_*.py -v`        | 8/8 PASS        | ✅ Sim        | 🟡     |
| Cobertura ≥ 80% em `backtest/`            | `pytest --cov=backtest --cov-report` | Relatório HTML  | ✅ Sim        | 🟡     |
| Nenhuma regressão em Sprint 1 (70 testes) | `pytest tests/ -v`                    | 70 PASS         | ✅ Sim        | 🟡     |
| Performance: 6 meses × 60 símbolos < 30s  | Executar backtest completo            | Log timestamp   | ✅ Sim        | 🟡     |

#### Gate 4: Documentação

| Critério                                  | Como validar                          | Evidência       | Automatizado? | Status |
|-------------------------------------------|---------------------------------------|-----------------|---------------|--------|
| Docstrings em classes/funções (PT)        | Code review `backtest/*.py`           | ✓ Revisado      | ❌ Manual     | 🟡     |
| `backtest/README.md` com guia uso         | Arquivo exists, mín. 500 palavras     | Arquivo OK      | ❌ Manual     | 🟡     |
| CRITERIOS atualizado com S2-3             | Verificar seção S2-3 (este arquivo)   | ✓ Completo      | ❌ Manual     | 🟡     |
| Trade-offs críticos em DECISIONS.md       | Verificar nova seção S2-3              | Entry criado    | ❌ Manual     | 🟡     |
| Código comentado (trade_state, walk_fwd)  | Code review inline comments (PT)      | ✓ Revisado      | ❌ Manual     | 🟡     |

---

## �🚦 Checklist Go/No-Go — Sprint 1 ✅ COMPLETA

| Gate                              | Critério                          | Status |
|-----------------------------------|-----------------------------------|--------|
| Conectividade                     | S1-1: WebSocket + Rate Limits ✅   | 🟢     |
| Risco                             | S1-2: Stop Loss + CB ✅            | 🟢     |
| Execução                          | S1-3: Paper Mode + Telemetry ✅    | 🟢     |
| Telemetria                        | S1-4: StructuredLogger + DB ✅     | 🟢     |
| **GO/NO-GO**                      | **TODOS os gates 🟢 GREEN**        | 🟢 GO  |

> **Decisao:** Todos os gates ✅ GREEN. **GO-LIVE LIBERADO PARA SPRINT 2**.
> Evidencia: [Connectivity Results](../logs/connectivity_validation_results.md),
> [RiskGate Results](../logs/riskgate_validation_results.md),
> [Execution Results](../logs/execution_validation_results.md).
> 
> Ver [Runbook Operacional](RUNBOOK_OPERACIONAL.md) para procedimento de go-live.

---

*Legenda: ✅ Concluído · 🟡 Em andamento · 🔴 Bloqueado*
