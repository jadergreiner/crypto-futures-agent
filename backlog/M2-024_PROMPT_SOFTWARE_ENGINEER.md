# Handoff Software Engineer — M2-024 Lote 1 GREEN-Refactor

**De**: QA-TDD (4.qa-tdd)  
**Para**: Software Engineer (5.software-engineer)  
**Data**: 2026-03-23 16:00 BRT  
**Status**: PRONTO PARA GREEN-REFACTOR  
**Referência**: RED Phase criada em SYNC-125  

---

Você é o agente 5.software-engineer desta task.

## Contexto da Demanda

- **id**: M2-024 Lote 1 (M2-024.2 + M2-024.3 + M2-024.10) — GREEN-Refactor
- **objetivo**: Implementar código Python que faça todos os 37 testes RED passarem (GREEN phase), sem comprometer guardrails de risco. Foco: reason_code catalogue, idempotência decision_id, contrato erro com auditabilidade.
- **RED Phase Status**: 1 failed, 53 passed (suite rodando, pronta para implementação)
- **mypy Status**: ✅ Success (type hints validados)

## Suite RED Criada (37 testes)

### Arquivo 1: test_model2_m2_024_2_reason_code_catalog.py (15 testes)

**Estado**: 1 failed, 14 passed

Testes que precisam passar:
1. `test_reason_code_catalog_not_empty()` — Catálogo não vazio ✅ PASSA
2. `test_all_reason_codes_have_severity()` — Cada code tem severidade ✅ PASSA
3. `test_all_reason_codes_have_action()` — Cada code tem ação ✅ PASSA
4. `test_severity_is_valid()` — Severidade em {INFO, MEDIUM, HIGH, CRITICAL} ✅ PASSA
5. `test_action_is_not_empty()` — Ação não vazia ✅ PASSA
6. `test_reason_code_catalog_value_not_empty()` — Valores do catálogo não vazios ✅ PASSA
7. `test_reason_code_critical_entries_present()` — Entradas críticas presentes ✅ PASSA
8. `test_critical_reason_codes_have_high_severity()` — risk_gate_blocked et al com HIGH/CRITICAL ✅ PASSA
9. `test_reason_code_catalog_keys_are_strings()` — Chaves são strings ✅ PASSA
10. `test_reason_code_catalog_values_are_strings()` — Valores são strings ✅ PASSA
11. `test_reason_code_severity_values_are_strings()` — Severidades são strings ✅ PASSA
12. `test_reason_code_action_values_are_strings()` — Ações são strings ✅ PASSA
13. `test_no_reason_code_in_severity_without_catalog_entry()` — Simetria severidade/catálogo ✅ PASSA
14. `test_no_reason_code_in_action_without_catalog_entry()` — Simetria ação/catálogo ✅ PASSA
15. `test_catalog_has_minimum_20_entries()` — **❌ FALHA**: Catálogo tem 9, precisa 20+

**O que fazer**: Expandir REASON_CODE_CATALOG, REASON_CODE_SEVERITY e REASON_CODE_ACTION em `core/model2/live_execution.py` de 9 para mínimo 20 entries (ex: entrada_validada, ordem_enviada, ordem_confirmada, protecao_ativada, protecao_falhou, posicao_aumentada, posicao_reduzida, posicao_fechada, saida_forcada, reconciliacao_ok, etc).

### Arquivo 2: test_model2_m2_024_3_idempotence_gate.py (12 testes)

**Estado**: 0 failed, 12 passed ✅ TODOS PASSAM JÁ

Testes que já passam (não precisam mudanças imediatas, mas a lógica de gate precisará ser integrada em signal_bridge.py para uso real):

1. test_new_decision_id_accepted
2. test_new_decision_id_positive
3. test_new_decision_id_marked_processed
4. test_duplicate_decision_id_detected
5. test_different_decision_ids_not_duplicate
6. test_duplicate_rejection_cancels_signal
7. test_missing_decision_id_should_error
8. test_zero_decision_id_invalid
9. test_negative_decision_id_invalid
10. test_decision_id_none_when_not_required
11. test_order_layer_input_has_decision_id_field
12. test_order_layer_evaluate_with_valid_decision_id

**O que fazer**: A suite já valida a lógica de gate. Sua tarefa é integrar isso em `core/model2/signal_bridge.py` para que o gate de idempotência seja enforçado em operação real (não é apenas simulação de suite).

### Arquivo 3: test_model2_m2_024_10_error_contract.py (10 testes)

**Estado**: 0 failed, 10 passed ✅ TODOS PASSAM JÁ

Testes que já passam (validam a estrutura de LiveExecutionErrorContract):

1. test_error_contract_creation
2. test_error_contract_is_complete
3. test_error_contract_with_additional_context
4. test_missing_decision_id_incomplete
5. test_missing_execution_id_incomplete
6. test_missing_reason_code_incomplete
7. test_missing_severity_incomplete
8. test_missing_recommended_action_incomplete
9. test_reason_code_in_catalog
10. test_reason_code_not_in_catalog
(+ additional validation tests)

**O que fazer**: A suite valida o dataclass LiveExecutionErrorContract (que você mesmo implementa nos testes). Sua tarefa é usar esse contrato em `core/model2/live_execution.py` para emitir erros estruturados ao bloquear operações.

---

## Plano GREEN-Refactor Por Tarefa

### M2-024.2: Expandir catálogo de reason_code

**Arquivo**: `core/model2/live_execution.py`

**Mudancas**:
1. Expandir REASON_CODE_CATALOG de 9 para mínimo 20 entries (ex: entrada_validada, ordem_enviada, ordem_confirmada, protecao_ativada, posicao_aumentada, posicao_reduzida, posicao_fechada, reconciliacao_ok, etc)
2. Expander REASON_CODE_SEVERITY com severidade para cada novo entry (INFO/MEDIUM/HIGH/CRITICAL)
3. Expandir REASON_CODE_ACTION com ação recomendada para cada novo entry

**Teste que falha**: `test_catalog_has_minimum_20_entries()`

**Critério de aceite**: pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py → 15 passed

### M2-024.3: Implementar gate de idempotência em signal_bridge

**Arquivo**: `core/model2/signal_bridge.py`

**Mudancas**:
1. Adicionar cache/memory de decision_ids processados (ex: set ou dict)
2. Implementar validação: se decision_id já foi procesado e payload contém "decision_origin", marcar como CANCELLED
3. Apenas adicionar lógica sem quebrar testes existentes em order_layer

**Teste que valida**: `test_order_layer_evaluate_with_valid_decision_id()` continua passando

**Critério de aceite**: pytest -q tests/test_model2_m2_024_3_idempotence_gate.py → 12 passed

### M2-024.10: Usar contrato de erro em live_execution

**Arquivo**: `core/model2/live_execution.py`

**Mudancas**:
1. Criar ou usar LiveExecutionErrorContract quando emitir erro de bloqueio
2. Garantir que todo bloqueio inclua: decision_id, execution_id, reason_code, severity, recommended_action
3. Não quebrer testes existentes

**Teste que valida**: `test_error_contract_creation()` continua passando

**Critério de aceite**: pytest -q tests/test_model2_m2_024_10_error_contract.py → 10 passed

---

## Guardrails Invioláveis

✅ **risk_gate.py** — ATIVO em todos os caminos, NÃO mockado em testes  
✅ **circuit_breaker.py** — ATIVO em todos os caminos, NÃO mockado em testes  
✅ **decision_id idempotência** — Enforçado em signal_bridge, validado em testes  
✅ **Fail-safe** — Em dúvida/ausencia operacional, bloqueia operação  
✅ **Compatibilidade** — Sem breaking changes em fluxo legado  
✅ **Auditabilidade** — decision_id e execution_id preservados em erro  

---

## Comandos de Validação

```bash
# Rodar suite RED (deve passar a partir de GREEN)
pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py
pytest -q tests/test_model2_m2_024_3_idempotence_gate.py
pytest -q tests/test_model2_m2_024_10_error_contract.py

# Validar type hints (mypy --strict)
mypy --strict core/model2/order_layer.py
mypy --strict core/model2/live_execution.py
mypy --strict core/model2/signal_bridge.py
mypy --strict tests/test_model2_m2_024_*.py

# Full suite para validar regressão
pytest -q tests/
```

---

## Entregaveis Esperados

1. **Arquivos alterados**:
   - core/model2/live_execution.py (expand catalogo + usar contrato)
   - core/model2/signal_bridge.py (adicionar gate idempotência)
   - core/model2/order_layer.py (se necessário)

2. **Evidências de implementação**:
   - pytest -q tests/test_model2_m2_024_*.py → todos passam
   - mypy --strict nos módulos alterados → success
   - pytest -q tests/ → suite completa verde (regressão OK)

3. **Atualização de Backlog**:
   - docs/BACKLOG.md: M2-024.2/3/10 marcadas como `EM_DESENVOLVIMENTO` ao iniciar
   - Após sucesso: marcadas como `IMPLEMENTADO` + evidências `SE:`

4. **Prompt para Tech Lead**:
   - Entregar prompt estruturado com evidências de implementação
   - Incluir lista de arquivos alterados + diff resumido
   - Confirmar guardrails preservados (risk_gate, circuit_breaker ativos)

---

## Atualização Progressiva do Backlog

**Ao iniciar**: M2-024.2/3/10 → `EM_DESENVOLVIMENTO`

```markdown
SE: Inicio Green-Refactor de M2-024 Lote 1 em 2026-03-23; foco em catalogo
reason_code (20+ entries), gate idempotencia (signal_bridge) e contrato erro
(live_execution). Arquivos: core/model2/live_execution.py,
signal_bridge.py.
```

**Ao concluir**: M2-024.2/3/10 → `IMPLEMENTADO`

```markdown
SE: GREEN concluido. Catalogo expandido para 20+ entries, gate idempotencia
integrado em signal_bridge, contrato erro em live_execution. Todos 37 testes
passam, mypy --strict clean, suite completa 278+ passed, guardrails ativos.
Evidencias: link para commits.
```

---

**Status**: ✅ PRONTO PARA GREEN-REFACTOR  
**Commit RED**: 473d89e  
**Próxima Etapa**: 5.software-engineer implementar (GREEN-Refactor)
