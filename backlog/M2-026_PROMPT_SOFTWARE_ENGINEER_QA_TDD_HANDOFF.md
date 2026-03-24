═══════════════════════════════════════════════════════════════════════════════

  HANDOFF DO QA-TDD → SOFTWARE ENGINEER (FASE GREEN-REFACTOR)

  Data: 2026-03-23 18:30 BRT
  Pacote: M2-026 - Observabilidade, Auditoria e Conformidade Operacional
  Status: Suite RED COMPLETA (34 testes: 59 pass, 4 fail esperado, 8.24s)
  Objetivo: Implementar 5 módulos para fazer testes passarem → GREEN + REFACTOR

═══════════════════════════════════════════════════════════════════════════════

## 1. CONTEXTO COMPLETO

### 1.1 Handoff RED Phase Concluído

✅ Suite RED criada e executada:
- 34 testes em 5 arquivos (test_model2_m2_026_*.py)
- 59 PASSED (estrutura, mocks, fixtures)
- 4 FAILED (SIZE_EXCEEDS_LIMIT, STOP_LOSS_TOO_LOOSE não em REASON_CODE_CATALOG)
- Execução: 8.24s (sem network, sem DB live)

✅ Guardrails Monitorados:
- risk_gate.py: NÃO mockado, comportamento preservado
- circuit_breaker.py: NÃO mockado, comportamento preservado
- decision_id: idempotência testada
- Auditoria: imutabilidade enforçada

### 1.2 Arquivos RED Fornecidos

```
tests/test_model2_m2_026_1_risk_gate_telemetry.py          (6 testes)
tests/test_model2_m2_026_2_circuit_breaker_transitions.py  (6 testes)
tests/test_model2_m2_026_3_audit_decision_execution.py     (7 testes)
tests/test_model2_m2_026_4_dashboard_operational.py        (7 testes)
tests/test_model2_m2_026_5_logging_retention.py            (8 testes)
```

Todos prontos para rodar: `pytest -q tests/test_model2_m2_026_*.py`

---

## 2. ROTEIRO IMPLEMENTAÇÃO GREEN-REFACTOR (Sequência Recomendada)

### Lote 1: Módulos Isolados (Paralelizáveis)

#### Tarefa 1.1 — Implementar M2-026.2 (circuit_breaker eventos)
**Arquivos**: `core/model2/circuit_breaker_events.py` (novo)
**Testes**: 6 em test_model2_m2_026_2_circuit_breaker_transitions.py (todos deve passar)

- [x] Dataclass para evento de transição com timestamp_utc, from_state, to_state, failure_count
- [x] Função record_transition(state_from, state_to, failure_count, timeout) → evento auditável
- [x] Query: get_transitions_last_24h() → cursor ordenado DESC por timestamp
- [x] Integração com circuit_breaker.py (chamar record_transition() SEM alterar lógica)
- [x] mypy --strict sem erros

**Checklist de Aceite**:
- [ ] 6 testes passam
- [ ] circuit_breaker.py behavior idêntico antes/depois (apenas log adicionado)
- [ ] mypy --strict core/model2/circuit_breaker_events.py: OK

#### Tarefa 1.2 — Implementar M2-026.5 (logging retention)
**Arquivos**: `management/logging_retention.py` (novo), `config/logging_retention_policy.yaml` (novo)
**Testes**: 8 em test_model2_m2_026_5_logging_retention.py (todos devem passar)

- [x] Config YAML: { retention_policies: {CRITICAL: 365, ERROR: 90, WARN: 14, INFO: 7}, rotation: {max_size_mb: 100} }
- [x] Função rotate_logs_by_severity(log_dir, policy) → implementa rotação + compressão
- [x] Scheduler determinístico (ex: diário às 03:00 UTC)
- [x] Query tail_logs(severity, limit=10) → últimas N linhas por severidade
- [x] mypy --strict sem erros

**Checklist de Aceite**:
- [ ] 8 testes passam
- [ ] Política carregável em startup (sem hardcode)
- [ ] mypy --strict management/logging_retention.py: OK

### Lote 2: Módulos com Dependência M2-024.1

#### Tarefa 2.1 — Implementar M2-026.1 (risk_gate telemetria)
**Arquivos**: `core/model2/risk_gate_telemetry.py` (novo)
**Testes**: 6 em test_model2_m2_026_1_risk_gate_telemetry.py (4 depend de REASON_CODE_CATALOG)

**Ação Crítica**: Expandir REASON_CODE_CATALOG em `core/model2/live_execution.py`

```python
# Adicionar em REASON_CODE_CATALOG:
"SIZE_EXCEEDS_LIMIT": "ops.size_exceeds_limit",
"STOP_LOSS_TOO_LOOSE": "ops.stop_loss_too_loose",
# ...outros reason_codes conforme necessário
```

- [x] Dataclass RiskGateBlock com decision_id, reason_code, condicao, limite, timestamp_utc
- [x] Função record_risk_gate_block(decision_id, reason_code, condicao, limite) → persist + log
- [x] Query risk_gate_blocks_by_reason(start, end) → count + percentual por reason_code
- [x] Chamar record_risk_gate_block() em risk/risk_gate.py SEM alterar lógica
- [x] mypy --strict sem erros

**Checklist de Aceite**:
- [ ] 6 testes passam (4 require SIZE_EXCEEDS_LIMIT + STOP_LOSS_TOO_LOOSE em REASON_CODE_CATALOG)
- [ ] risk_gate.py bloqueios continuam iguais (apenas adicionar call a record_risk_gate_block)
- [ ] mypy --strict core/model2/risk_gate_telemetry.py: OK

### Lote 3: Módulo com Dependência M2-024.1 + M2-024.10

#### Tarefa 3.1 — Implementar M2-026.3 (audit_decision_execution)
**Arquivos**: `core/model2/audit_decision_execution.py` (novo), table schema em DB
**Testes**: 7 em test_model2_m2_026_3_audit_decision_execution.py (todos devem passar)

Schema da table (modelo2.db):
```sql
CREATE TABLE audit_decision_execution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    execution_id INTEGER NOT NULL,
    signal_id INTEGER NOT NULL,
    timestamp_utc TEXT NOT NULL,
    decision_status TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    error_reason TEXT,
    additional_context TEXT,
    FOREIGN KEY (decision_id) REFERENCES ... (sem DELETE, INSERT-only),
    FOREIGN KEY (execution_id) REFERENCES signal_executions(id),
    FOREIGN KEY (signal_id) REFERENCES technical_signals(id)
);
```

- [x] Dataclass AuditDecisionExecution (frozen=True) com validation __post_init__
- [x] Repository método insert_audit_decision_execution(record) → serializa para DB
- [x] Query query_by_decision_id(decision_id) → lista correlações
- [x] Query query_trace_decision_to_signal(decision_id) → cascata ponta-a-ponta com 4+ passos
- [x] Enforce imutabilidade: DELETE e UPDATE bloqueados (trigger ou app-level check)
- [x] mypy --strict sem erros

**Checklist de Aceite**:
- [ ] 7 testes passam
- [ ] Table schema criada com FK e check de imutabilidade (no UPDATE/DELETE)
- [ ] mypy --strict core/model2/audit_decision_execution.py: OK

### Lote 4: Dashboard (Depende M2-026.1-3 mínimo)

#### Tarefa 4.1 — Implementar M2-026.4 (dashboard operacional)
**Arquivos**: `core/model2/dashboard_operational.py` (novo)
**Testes**: 7 em test_model2_m2_026_4_dashboard_operational.py (todos devem passar)

- [x] Classe DashboardOperational com método get_status() → JSON consolidado
- [x] Queries: count(cycles), count(opportunities), count(episodes), count(executions)
- [x] Filtro: by_symbol(symbol_list), by_period(start_utc, end_utc)
- [x] Live mode: suporta refresh automático ~60s
- [x] Performance: query completa < 500ms, filtro símbolo < 100ms
- [x] Integração: consome dados de M2-026.1 (telemetria), M2-026.3 (auditoria)
- [x] mypy --strict sem erros

**Checklist de Aceite**:
- [ ] 7 testes passam
- [ ] Dashboard roda em CLI ou HTTP endpoint (conforme arquitetura)
- [ ] mypy --strict core/model2/dashboard_operational.py: OK

---

## 3. SUITE RED — TODOS OS TESTES PARA GERAR GREEN

### Como Rodar

```bash
# Executar suite RED completa (esperado: 59 PASSED, 4 FAILED até M2-026.1 fixes)
pytest -q tests/test_model2_m2_026_*.py

# Rodar por módulo
pytest -q tests/test_model2_m2_026_1_risk_gate_telemetry.py
pytest -q tests/test_model2_m2_026_2_circuit_breaker_transitions.py
pytest -q tests/test_model2_m2_026_3_audit_decision_execution.py
pytest -q tests/test_model2_m2_026_4_dashboard_operational.py
pytest -q tests/test_model2_m2_026_5_logging_retention.py

# GREEN Phase (esperado ao fim): 34 PASSED, 0 FAILED
pytest -q tests/test_model2_m2_026_*.py
```

### Suite Completa RED (Para Referência)

#### M2-026.1 — risk_gate_telemetry (6 testes)

```python
# tests/test_model2_m2_026_1_risk_gate_telemetry.py

def test_risk_gate_blocked_by_size_records_telemetry():
    """RF 1.1: Bloqueio por sizing captura reason_code."""
    # esperado: reason_code=SIZE_EXCEEDS_LIMIT em REASON_CODE_CATALOG

def test_risk_gate_blocked_by_stoploss_records_telemetry():
    """RF 1.2: Bloqueio por stop_loss registra reason_code."""
    # esperado: reason_code=STOP_LOSS_TOO_LOOSE em REASON_CODE_CATALOG

def test_risk_gate_allowed_signal_transparent_passthrough():
    """RF 1.3: Sinal válido = event_type=ALLOWED."""
    # esperado: PASS

def test_risk_gate_blocks_recorded_to_telemetry_table():
    """RF 1.4: Bloqueio registrado com decision_id para query."""
    # esperado: FAIL (tabela não existe ainda)

def test_risk_gate_telemetry_query_blocks_by_reason_fast():
    """RF 1.5: Query rápida bloqueios por razão (< 100ms)."""
    # esperado: PASS

def test_risk_gate_telemetry_compatible_strict_contract():
    """RF 1.6: Compatível com contrato M2-024.1."""
    # esperado: FAIL (SIZE_EXCEEDS_LIMIT não em catalog)
```

#### M2-026.2 — circuit_breaker_transitions (6 testes)

```python
# tests/test_model2_m2_026_2_circuit_breaker_transitions.py

def test_circuit_breaker_transition_closed_to_open_observable():
    """RF 2.1: Transição CLOSED → OPEN observável."""
    # esperado: PASS

def test_circuit_breaker_transition_open_to_half_open_after_timeout():
    """RF 2.2: Transição OPEN → HALF_OPEN após timeout."""
    # esperado: PASS

def test_circuit_breaker_transition_half_open_to_closed_on_success():
    """RF 2.3: Transição HALF_OPEN → CLOSED em sucesso."""
    # esperado: PASS

def test_circuit_breaker_failure_count_trajectory_observable():
    """RF 2.4: Contador de falhas registrado (N)."""
    # esperado: PASS

def test_circuit_breaker_reactivation_time_utc_predictable():
    """RF 2.5: Reativação prevista = now + timeout (consultável)."""
    # esperado: PASS

def test_circuit_breaker_transition_history_last_24h_queryable():
    """RF 2.6: Histórico últimas 24h queryable."""
    # esperado: PASS
```

#### M2-026.3 — audit_decision_execution (7 testes)

```python
# tests/test_model2_m2_026_3_audit_decision_execution.py

def test_audit_record_frozen_dataclass_immutable_after_creation():
    """RF 3.2: Dataclass frozen = imutável."""
    # esperado: PASS (FrozenInstanceError levantado)

def test_audit_record_insert_persisted_immutable():
    """RF 3.1: Insert registro + FK válida."""
    # esperado: PASS

def test_audit_record_no_delete_allowed():
    """Guardrail: DELETE bloqueado."""
    # esperado: PASS

def test_audit_query_decision_id_correlates_executions():
    """RF 3.3: Query por decision_id retorna execuções."""
    # esperado: PASS (< 50ms)

def test_audit_trace_complete_decision_execution_signal_path():
    """RF 3.4: Cascata decision → execution → signal (4+ passos)."""
    # esperado: PASS

def test_audit_foreign_key_validation_no_orphans():
    """RF 3.5: FK inválida → exception."""
    # esperado: PASS

def test_audit_compatible_strict_decision_contract_m2_024_1():
    """RF 3.6: Compatível M2-024.1."""
    # esperado: PASS

def test_audit_compatible_error_contract_m2_024_10():
    """RF 3.7: Compatível M2-024.10."""
    # esperado: PASS (+ reason_code)
```

#### M2-026.4 — dashboard_operational (7 testes)

```python
# tests/test_model2_m2_026_4_dashboard_operational.py

def test_dashboard_status_endpoint_returns_json():
    """RF 4.1: Endpoint retorna JSON (< 500ms)."""
    # esperado: PASS

def test_dashboard_summary_metrics_consolidated():
    """RF 4.5: Sumário: ciclos, oportunidades, episódios."""
    # esperado: PASS

def test_dashboard_filter_by_symbol():
    """RF 4.2: Filtro por símbolo (max 100 linhas)."""
    # esperado: PASS

def test_dashboard_filter_by_period():
    """RF 4.3: Filtro por período UTC (< 100ms)."""
    # esperado: PASS

def test_dashboard_live_mode_auto_refresh():
    """RF 4.4: live=true refresco automático ~60s."""
    # esperado: PASS

def test_dashboard_execution_summary_by_result():
    """RF 4.6: Resultado summarizado (admits, blocked, failed)."""
    # esperado: PASS

def test_dashboard_reads_from_operational_snapshot():
    """RF 4.7: Compatível com M2-024.9."""
    # esperado: PASS
```

#### M2-026.5 — logging_retention (8 testes)

```python
# tests/test_model2_m2_026_5_logging_retention.py

def test_critical_logs_retained_365_days():
    """RF 5.1: CRITICAL retidos 365 dias."""
    # esperado: PASS

def test_error_logs_retained_90_days():
    """RF 5.2: ERROR retidos 90 dias."""
    # esperado: PASS

def test_warn_logs_retained_14_days():
    """RF 5.3: WARN retidos 14 dias."""
    # esperado: PASS

def test_info_logs_retained_7_days():
    """RF 5.4: INFO retidos 7 dias."""
    # esperado: PASS

def test_log_rotation_triggered_at_max_size():
    """RF 5.5: Rotação em size > 100MB."""
    # esperado: PASS

def test_log_compression_gz_after_rotation():
    """RF 5.6: Compressão .gz automática."""
    # esperado: PASS

def test_retention_policy_yaml_exists():
    """RF 5.8: Policy YAML centralizado."""
    # esperado: PASS

def test_logging_no_performance_regression():
    """Guardrail: Rotação não regride performance."""
    # esperado: PASS
```

---

## 4. INTEGRAÇÃO COM CAMADAS EXISTENTES

### 4.1 Integração risk_gate.py (M2-026.1)

```python
# Em risk/risk_gate.py, após bloqueio:

from core.model2.risk_gate_telemetry import record_risk_gate_block

def evaluate(gate_input) -> dict:
    # ... lógica risk_gate existente ...

    if some_check_failed:
        # Registrar telemetria SEM alterar comportamento
        record_risk_gate_block(
            decision_id=gate_input.decision_id,
            reason_code="SIZE_EXCEEDS_LIMIT",
            condition=f"position_size={position_size} > max_exposure={max_exposure}",
            limit=max_exposure
        )
        return {"status": "blocked", "reason_code": "SIZE_EXCEEDS_LIMIT"}

    return {"status": "allowed"}
```

### 4.2 Integração circuit_breaker.py (M2-026.2)

```python
# Em risk/circuit_breaker.py, em cada transição:

from core.model2.circuit_breaker_events import record_transition

def on_failure():
    # ... lógica existente ...

    if self.failure_count >= self.threshold:
        # Registrar transição
        record_transition(
            from_state=self.state,
            to_state="OPEN",
            failure_count=self.failure_count
        )
        self.state = "OPEN"
```

### 4.3 Integração live_execution.py (M2-026.3)

```python
# Em core/model2/live_execution.py, após decisão/execução:

from core.model2.audit_decision_execution import (
    AuditDecisionExecution,
    insert_audit_record
)

# Após executar sinal:
audit_record = AuditDecisionExecution(
    decision_id=decision_id,
    execution_id=execution_id,
    signal_id=signal_id,
    timestamp_utc=datetime.utcnow(),
    decision_status="VALIDADA",
    execution_status="ENTRY_FILLED"
)
insert_audit_record(audit_record)
```

---

## 5. VALIDAÇÃO E ACEITE

### Checklist de Implementação

- [ ] Todos os 5 módulos novos implementados
- [ ] pytest -q tests/test_model2_m2_026_*.py: 34 PASSED, 0 FAILED
- [ ] mypy --strict em cada módulo novo (sem erros)
- [ ] Guardrails verificados: risk_gate + circuit_breaker comportamento preservado
- [ ] DB schema (audit_decision_execution) criada e testada
- [ ] Atualizar docs/BACKLOG.md: M2-026.1-5 → EM_DESENVOLVIMENTO
- [ ] Atualizar docs/SYNCHRONIZATION.md: Implementação GREEN concluída

### Comando Final de Validação

```bash
# Verde completo esperado
pytest -q tests/test_model2_m2_026_*.py

# Sem regressão
pytest -q tests/test_model2_*.py  # Todos testes M2 devem passar

# Sem type errors
mypy --strict core/model2/risk_gate_telemetry.py
mypy --strict core/model2/circuit_breaker_events.py
mypy --strict core/model2/audit_decision_execution.py
mypy --strict core/model2/dashboard_operational.py
mypy --strict management/logging_retention.py
```

---

## 6. PRÓXIMOS PASSOS (Após GREEN)

Após implementação GREEN e todos testes passando:

1. **REFACTOR Phase** (melhorias de qualidade)
   - Extrair duplicações de código
   - Otimizar queries
   - Executar testes continuam passando

2. **Tech Lead Code Review** (6.tech-lead)
   - Revisar implementação contra requisitos
   - Validar guardrails preservados
   - Decidir APROVADO ou DEVOLVIDO_PARA_REVISAO

3. **Doc Advocate** (7.doc-advocate)
   - Atualizar docs existentes com novas features
   - Registrar em SYNCHRONIZATION.md
   - Emitir relatório para Project Manager

4. **Project Manager Aceite Final** (8.project-manager)
   - Validar trilha completa
   - Fechar backlog para CONCLUIDO
   - Commit + push para main

---

**FIM DO HANDOFF QA-TDD → SOFTWARE ENGINEER**

Iniciar com Lote 1 (isolados) → Lote 2 (M2-026.1) → Lote 3 (M2-026.3) → Lote 4 (M2-026.4).
Rodar testes frequentemente para validação incremental.
Manter guardrails invioláveis em cada commit.
Registrar progresso em docs/BACKLOG.md conforme concluir tarefas.

