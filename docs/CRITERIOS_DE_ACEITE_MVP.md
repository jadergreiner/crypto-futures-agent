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

## 📋 Matriz de Critérios — Sprint 1

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

## 🚦 Checklist Go/No-Go — Sprint 1

| Gate                              | Critério                          | Status |
|-----------------------------------|-----------------------------------|--------|
| Conectividade                     | Todos S1-1 ✅                     | 🟡     |
| Risco                             | Todos S1-2 ✅                     | 🟡     |
| Execução                          | Todos S1-3 ✅                     | 🟡     |
| Telemetria                        | Todos S1-4 ✅                     | 🟡     |
| **GO/NO-GO**                      | **Todos os gates ✅**             | 🟡     |

> **Regra:** Se qualquer gate com status 🔴, bloquear go-live. Ver
> [Runbook Operacional](RUNBOOK_OPERACIONAL.md) para procedimento de rollback.

---

*Legenda: ✅ Concluído · 🟡 Em andamento · 🔴 Bloqueado*
