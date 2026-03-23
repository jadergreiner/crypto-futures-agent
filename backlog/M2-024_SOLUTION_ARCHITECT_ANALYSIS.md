# Análise Técnica — Pacote M2-024: Hardening

**De**: Solution Architect (3.solution-architect)
**Data**: 2026-03-23 14:00 BRT
**Status**: EM_ANALISE → PROPOSTA TECNICA
**Referência**: Handoff PO M2-024_PRODUCT_OWNER_HANDOFF.md

---

## 1. Validação de Aderência Arquitetural

### 1.1 Alinhamento com Arquitetura Vigente

O Pacote M2-024 **alinha-se com princípios de arquitetura**:

| Princípio | Aderência | Evidência |
|-----------|-----------|-----------|
| Decisão direta do modelo | ✅ SIM | M2-024.1-3: idempotência de decision_id |
| Guard-rails invioláveis | ✅ SIM | M2-024.2,7: reason_code + circuit_breaker |
| Fail-safe em dúvida | ✅ SIM | M2-024.4,13,14: timeout, preflight, rollback |
| Auditabilidade ponta-a-ponta | ✅ SIM | M2-024.6,8,9: telemetria, reconciliação, snapshot |

### 1.2 Conformidade com Regras de Negócio

| Regra | Tarefa | Conformidade |
|-------|--------|--------------|
| RN-001 (Decisão única) | M2-024.3 | ✅ Gate de idempotência |
| RN-003 (Envelope seguro) | M2-024.2,7 | ✅ Reason_code + circuit_breaker contextualizado |
| RN-004 (Fail-safe) | M2-024.5,14 | ✅ Timeout + rollback |
| RN-006 (Idempotência) | M2-024.3 | ✅ Deduplik por decision_id |
| RN-007 (Reconciliação) | M2-024.8 | ✅ Determinística |

---

## 2. Análise de Dependências Refinada

### 2.1 Grafo de Dependências (Ordem de Execução)

```
FASE I - Fundação (Tarefas 1-3):
  M2-024.1 (✅ CONCLUÍDO)
    ├─→ M2-024.2 (reason_code catalogue)
    │    ├─→ M2-024.3 (idempotência gate)
    │    ├─→ M2-024.4 (retry + backoff)
    │    └─→ M2-024.7 (circuit breaker)

FASE II - Observabilidade (Tarefas 4-6):
  M2-024.4 + M2-024.5
    ├─→ M2-024.6 (telemetria latência)

FASE III - Guardrails Avançados (Tarefas 7-9):
  M2-024.7 + M2-024.8
    └─→ M2-024.9 (snapshot único)

FASE IV - Testes & Validação (Tarefas 10-14):
  M2-024.10 (suite RED)
  M2-024.11 (regressão stress) [paralelo com 12-14]
  M2-024.12 (testnet integração)
  M2-024.13 (gate preflight)
  M2-024.14 (rollback policy)

FASE V - Governança (Tarefa 15):
  M2-024.15 (docs + SYNC)
```

### 2.2 Sequenciamento Recomendado (8 sprints)

| Sprint | Tarefas | Duração Estimada | Bloqueadores |
|--------|---------|------------------|-------------|
| 1 | M2-024.2, M2-024.10 | 3-4 dias | Nenhum |
| 2 | M2-024.3, M2-024.4, M2-024.5 | 4-5 dias | Sprint 1 |
| 3 | M2-024.6, M2-024.7, M2-024.8 | 5-6 dias | Sprint 2 |
| 4 | M2-024.9 | 2-3 dias | Sprint 3 |
| 5 | M2-024.11, M2-024.12 (paralelo) | 5-7 dias | Sprint 4 |
| 6 | M2-024.13 | 3-4 dias | Sprint 2 |
| 7 | M2-024.14 | 2-3 dias | Sprint 3 |
| 8 | M2-024.15 (governança final) | 1-2 dias | Sprints 1-7 |

**Esforço total estimado**: 28-37 dias de desenvolvimento

---

## 3. Modelagem de Dados

### 3.1 Análise de Schema

**Não é necessário criar tabelas novas em `modelo2.db`**.

Rationale:
- M2-024 é sobre determinismo, auditabilidade e failSafe
- Technical_signals, signal_executions já existem
- Dados novos (telemetria, reason_code) podem ser persistidos como JSONx ou computed

### 3.2 Extensões Necessárias (Compatíveis)

| Tabela | Coluna | Tipo | Função | Compatibilidade |
|--------|--------|------|--------|-----------------|
| signal_executions | reason_code_key | TEXT | Chave do catálogo | ✅ NOVA COLUNA (nullable) |
| signal_executions | severity_level | TEXT | Severidade do bloqueio | ✅ NOVA COLUNA (nullable) |
| signal_executions | execution_metadata | JSON | Telemetria de latência | ✅ EXTENSÃO JSON |
| signal_execution_events | latency_ms | INTEGER | Latência por etapa | ✅ NOVA TABELA (opcional) |

**Migração**: Compatível retroativa (colunas nullable, sem ALTER COLUMN)

---

## 4. Componentes Afetados

### 4.1 Mapa de Implementação

| Componente | Tarefa(s) | Tipo Mudança | Risco |
|------------|-----------|--------------|-------|
| `core/model2/order_layer.py` | M2-024.1/2/3 | Validação contrato | 🟢 Baixo |
| `core/model2/live_execution.py` | M2-024.2/4/5/8 | Retry, timeout, reason_code | 🟡 Médio |
| `core/model2/live_service.py` | M2-024.6/8/9 | Telemetria, reconciliação, snapshot | 🟡 Médio |
| `core/model2/signal_bridge.py` | M2-024.3 | Gate de idempotência | 🟡 Médio |
| `risk/circuit_breaker.py` | M2-024.7 | Contextualização por classe | 🟡 Médio |
| `scripts/model2/go_live_preflight.py` | M2-024.13 | Validação schema + contrato | 🟢 Baixo |
| `tests/test_model2*.py` | M2-024.10/11 | Suite RED → GREEN | 🟢 Baixo |
| Banco `modelo2.db` | M2-024.2/5/6 | Colunas nullable + JSON | 🟢 Baixo |

---

## 5. Análise de Risco Técnico

### 5.1 Riscos Identificados e Mitigações

| Risco | Severidade | Probabilidade | Mitigação |
|-------|-----------|-----------------|----------|
| Duplicação de decision_id em M2-024.3 | CRITICAL | BAIXA | Suite RED em M2-024.10 (testes de idempotência) |
| Race condition em reconciliação M2-024.8 | HIGH | MÉDIA | Determinismo testado em stress (M2-024.11) |
| Regression em circuit_breaker M2-024.7 | HIGH | MÉDIA | Testnet full flow (M2-024.12) validando proteção |
| Timeout agressivo em M2-024.5 bloqueando legítimo | MEDIUM | BAIXA | Parametrização testável, preflight (M2-024.13) |
| Incompatibilidade schema em live com shadow (M2-024.13) | HIGH | BAIXA | Migração nullable em M2-024.2/5 |

**Score geral de risco**: 🟢 **Controlável** (mitigações claras, testes em cada etapa)

---

## 6. Guardrails & Invariantes Confirmados

✅ **risk_gate.py** — ativo em M2-024.4/5/7, testado em M2-024.11/12
✅ **circuit_breaker.py** — evolução contextualizada (M2-024.7), sem remoção
✅ **decision_id idempotência** — enforçado em M2-024.3, testado em M2-024.10
✅ **Fail-safe** — timeout (M2-024.5), rollback (M2-024.14), preflight (M2-024.13)
✅ **Compatibilidade retroativa** — schema nullable, supply fluxo legado
✅ **Auditabilidade** — decision_id, reason_code, telemetria (M2-024.6/9)

---

## 7. Plano Técnico de Handoff para QA-TDD

**Prioridade para QA-TDD**: 3 tarefas iniciais para desbloquear pipeline

### Lote 1 (RED - Testes Iniciais, Prioridade ALTA):
- **M2-024.2** — Suite RED para reason_code catalogue + severidade
- **M2-024.10** — Suite RED para contrato de decisão + idempotência
- **M2-024.3** — Suite RED para gate de idempotência

### Lote 2 (GREEN, após Lote 1):
- Implementação das 3 tarefas em Green-Refactor

### Lote 3 (Red para tarefas 4-9, paralelo com Lote 2):
- M2-024.4, M2-024.5, M2-024.6, M2-024.7, M2-024.8

---

## 8. Estimativas de Esforço Refinadas

| Tarefa | Esforço (PO) | Esforço Real (SA) | Delta | Rationale |
|--------|--------------|------------------|-------|-----------|
| M2-024.1 | Baixo | ✅ Baixo | — | Concluído, validado |
| M2-024.2 | Baixo | Médio | ↑ | Requer 20+ cases no catálogo |
| M2-024.3 | Médio | Médio | — | Validação com tabela e mutex clareza |
| M2-024.4 | Médio | Médio-Alto | ↑ | Budget + exponential backoff complexo |
| M2-024.5 | Médio | Médio | — | Configurável, testável |
| M2-024.6 | Baixo | Baixo | — | JSON extension simples |
| M2-024.7 | Alto | Alto | — | Estateful, janela deslizante |
| M2-024.8 | Alto | Alto | — | Reconciliação determinística complexa |
| M2-024.9 | Médio | Médio-Baixo | ↓ | Agregação de dados existentes |
| M2-024.10 | Médio | Médio | — | Suite RED estruturada |
| M2-024.11 | Alto | Alto | — | Cenários stress + chaos |
| M2-024.12 | Alto | Alto | — | Integração testnet real |
| M2-024.13 | Médio | Médio-Baixo | ↓ | Extensão do preflight existente |
| M2-024.14 | Médio | Médio | — | Politica claro, casos definidos |
| M2-024.15 | Baixo | Baixo | — | Sincronização final |

**Revisão de Esforço Total**: 28-37 dias → **32-40 dias** (margem de segurança +15%)

---

## 9. Referências Técnicas

- **M2-024.1**: Contrato único (já implementado, APROVADO)
- **ARQUITETURA_ALVO.md**: Camadas do M2
- **REGRAS_DE_NEGOCIO.md**: RN-001 a RN-015
- **REASON_CODE_CATALOG**: Padrão em live_execution.py
- **M2-018.2**: Testnet baseline (referência para M2-024.12)
- **BLID-076**: Reconciliação determinística (dependência reversa)

---

## 10. Recomendações Finais

1. ✅ **Executar Lote 1 (M2-024.2/3/10) em paralelo com outras sprints**
2. ✅ **Usar M2-024.1 como template de contratos** (já validado)
3. ✅ **Testnet (M2-024.12) é gatekeeper** antes de qualquer ramp-up novo
4. ✅ **Circuit breaker (M2-024.7) é pre-requisito** para M2-024.11/12
5. ✅ **Não comprometer guardrails de risco** em nenhuma tarefa

---

**Status**: ✅ ANÁLISE CONCLUÍDA
**Pronto Para**: QA-TDD (Prompt acionável em seção seguinte)
