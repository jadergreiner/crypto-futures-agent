# Handoff — Pacote M2-024: Hardening de Decisão e Execução Live

**Do**: Product Owner (2.product-owner)
**Para**: Solution Architect (3.solution-architect)
**Data**: 2026-03-23 11:00 BRT
**Status**: EM_ANALISE
**Prioridade**: 1 (Bloqueador de Ramp-up)

---

## 1. Contexto de Negócio

O sistema Model 2.0 está **operacional desde 2026-03-21** em modo conservador,
mas apresenta lacunas críticas que bloqueiam **expansão de ramp-up**:

| Lacuna | Impacto | Severidade |
|--------|---------|-----------|
| Duplicação silenciosa de ordens | Múltiplas entradas por decisão | **CRITICAL** |
| Auditabilidade fragmentada | Impossível rastrear bloqueio/motivo | **HIGH** |
| Reconciliação não-determinística | Falso EXITED, divergência de estado | **HIGH** |
| Falhas transitorias sem retry | Perda de oportunidade ou bloqueia slot | **HIGH** |
| Observabilidade operacional | Leitura manual de logs, sem telemetria | **MEDIUM** |
| Testnet não integrado | Impossível validar fluxo antes de live | **HIGH** |

**Decisão**: Priorizar **Pacote M2-024** com 15 tarefas estruturadas
para eliminar estas lacunas e tornar o sistema seguro para escala.

---

## 2. Objetivo Técnico

Preparar a arquitetura model-driven para **escala segura com determinismo**:

1. **Contrato único** de decisão, execução e erro
2. **Idempotência garantida** por `decision_id`
3. **Reconciliação determinística** (sem race conditions)
4. **Circuit breaker contextualizado** por classe de falha
5. **Telemetria de latência** para diagnóstico operacional
6. **Suite testnet completa** antes de qualquer ramp-up

---

## 3. As 15 Tarefas — Escopo Completo

### Fase 1: Contatos & Catalogo (Tarefas 1-3)

| # | Tarefa | Escopo | Esforço | Status |
|---|--------|--------|---------|--------|
| 1 | M2-024.1 | Contrato único de decisão operacional | Baixo | ✅ CONCLUÍDO |
| 2 | M2-024.2 | Catálogo `reason_code` com severidade | Baixo | BACKLOG |
| 3 | M2-024.3 | Gate de idempotência por `decision_id` | Médio | BACKLOG |

**Dependências**: M2-024.1 concluído (APROVADO pelo Tech Lead).

### Fase 2: Retry, Timeout & Telemetria (Tarefas 4-6)

| # | Tarefa | Escopo | Esforço | Status |
|---|--------|--------|---------|--------|
| 4 | M2-024.4 | Retry controlado + backoff | Médio | BACKLOG |
| 5 | M2-024.5 | Timeout padrão por etapa | Médio | BACKLOG |
| 6 | M2-024.6 | Telemetria de latência | Baixo | BACKLOG |

**Dependências**: M2-024.2 (reason_code catalogue).

### Fase 3: Guardrails Avançados (Tarefas 7-9)

| # | Tarefa | Escopo | Esforço | Status |
|---|--------|--------|---------|--------|
| 7 | M2-024.7 | Circuit breaker por classe de falha | Alto | BACKLOG |
| 8 | M2-024.8 | Reconciliação determinística de saída | Alto | BACKLOG |
| 9 | M2-024.9 | Snapshot operacional único/ciclo | Médio | BACKLOG |

**Dependências**: M2-024.5 para timeout; M2-024.2 para reason_code.

### Fase 4: Testes & Validação (Tarefas 10-14)

| # | Tarefa | Escopo | Esforço | Status |
|---|--------|--------|---------|--------|
| 10 | M2-024.10 | Suite RED para contratos | Médio | BACKLOG |
| 11 | M2-024.11 | Regressão de risco com stress | Alto | BACKLOG |
| 12 | M2-024.12 | Integração testnet (fluxo completo) | Alto | BACKLOG |
| 13 | M2-024.13 | Gate preflight com schema M2 | Médio | BACKLOG |
| 14 | M2-024.14 | Política de rollback por severidade | Médio | BACKLOG |

**Dependências**: M2-024.7 (circuit breaker); M2-024.1 (contrato único).

### Fase 5: Governança Final (Tarefa 15)

| # | Tarefa | Escopo | Esforço | Status |
|---|--------|--------|---------|--------|
| 15 | M2-024.15 | Governança de docs + SYNCHRONIZATION | Baixo | BACKLOG |

**Dependências**: Todas as tarefas 1-14 concluídas.

---

## 4. Guardrails Invioláveis

**Nunca violar em nenhuma tarefa**:

1. ✅ `risk/risk_gate.py` ativo em **todos** os caminhos
2. ✅ `risk/circuit_breaker.py` ativo em **todos** os caminhos
3. ✅ Idempotência mantida por `decision_id` em decisão e execução
4. ✅ Fail-safe: em dúvida → bloqueia, nunca assume risco
5. ✅ Compatibilidade retroativa com fluxo legado (sem ruptura)
6. ✅ Determinismo em reconciliação (sem race conditions)
7. ✅ Auditabilidade ponta-a-ponta (timestamp, motivo, status, metadados)

---

## 5. Critérios de Aceite do Pacote

Pacote está **PRONTO para Solution Architect** quando:

- ✅ M2-024.1 concluído com evidências (8 testes + mypy clean)
  - Evidência: `pytest -q tests/test_model2_m2_024_1_decision_contract.py → 8 passed`
  - Evidência: `mypy --strict core/model2/order_layer.py → Success`
  - Status: ✅ APROVADO pelo Tech Lead
- ⏳ M2-024.2-14: análise técnica + plano detalhado + estimativas
- ⏳ M2-024.15: trilha SYNC atualizada ao final
- ⏳ Testnet funcional (M2-024.12)

---

## 6. Entrega Esperada do Solution Architect

Quando receber este handoff, o Solution Architect deve fornecer:

1. **Análise de dependências e sequenciamento**: ordem ideal de execução
2. **Modelagem de dados**: schema novo em `modelo2.db` (se necessário)
3. **Contrato de API/interface**: entre signal_bridge, order_layer, live_execution
4. **Plano de migração**: retrocompat garantida com fluxo legado
5. **Estimativas ajustadas** por tarefa (esforço real vs. indicativo PO)
6. **Prompt acionável para QA-TDD** com suite RED inicial
   - Foco em M2-024.1, M2-024.2, M2-024.10 (prioritárias)
   - Validar reason_code, decision_id, reconciliação

---

## 7. Histórico de Decisão

| Data | Ator | Evento | Decisão |
|------|------|--------|---------|
| 2026-03-21 | Operations | M2 vai live (modo conservador) | Operação iniciada |
| 2026-03-23 | Tech Lead | M2-024.1 aprovado | APROVADO + evidências verdes |
| 2026-03-23 | Product Owner | Pacote M2-024 priorizado | EM_ANALISE + handoff gerado |

---

## 8. Referências

- **Backlog**: `docs/BACKLOG.md` (seção "PACOTE M2-024")
- **Regras**: `docs/REGRAS_DE_NEGOCIO.md` (RN-001 a RN-015)
- **Arquitetura**: `docs/ARQUITETURA_ALVO.md` (Camadas M2, schema modelo2.db)
- **Prioridades**: `docs/PRD.md` (Objetivos OBJ-01 a OBJ-05)
- **Audit**: `docs/SYNCHRONIZATION.md` (SYNC-123 desta priorização)

---

## 9. Próximas Etapas

1. ✅ **Product Owner** — Pacote priorizado (CONCLUÍDO)
2. ⏳ **Solution Architect** — Análise e refinamento técnico (AWAITING)
3. ⏳ **QA-TDD** — Suite RED com cases de contrato (BLOCKED on SA)
4. ⏳ **Software Engineer** — Implementação Green-Refactor (BLOCKED on QA)
5. ⏳ **Tech Lead** — Code review + APROVADO/DEVOLVIDO (BLOCKED on SE)
6. ⏳ **Doc Advocate** — Governança final de docs (BLOCKED on TL)
7. ⏳ **Project Manager** — Aceite + merge para main (BLOCKED on DA)

---

**Status**: EM_ANALISE
**Proprietário**: Product Owner (2.product-owner)
**Última Atualização**: 2026-03-23 11:00 BRT
**Commit**: b2fd33b ([SYNC] PO prioriza M2-024)
