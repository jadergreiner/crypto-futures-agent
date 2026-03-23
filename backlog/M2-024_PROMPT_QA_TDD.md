# Handoff QA-TDD — Pacote M2-024 Lote 1 (Tarefas 2, 3, 10)

**De**: Solution Architect (3.solution-architect)
**Para**: QA-TDD (4.qa-tdd)
**Data**: 2026-03-23 14:30 BRT
**Status**: PRONTO PARA RED PHASE
**Referência**: M2-024_SOLUTION_ARCHITECT_ANALYSIS.md

---

Você é o agente 4.qa-tdd desta task.

## Contexto da demanda:

- **id**: M2-024 Lote 1 (M2-024.2 + M2-024.3 + M2-024.10)
- **objetivo**: Criar suite RED (testes que falham) para validar contrato único de reason_code, idempotência de decision_id e auditabilidade. Delimita escopo técnico para implementação Green-Refactor segura.
- **escopo_in**: Contrato M2-024.1 (já concluído); Arquitetura vigente (camadas 1-4); Catálogo REASON_CODE existente em live_execution.py
- **escopo_out**: Testnet (M2-024.12); Reconciliação determinística (M2-024.8); Suite de stress (M2-024.11)

## Requisitos refinados:

1. **Catalog canonico de reason_code com severidade**: Criar suite RED validando que todo reason_code (ex: "missing_decision_id", "risk_gate_blocked") possui severidade vinculada (INFO, MEDIUM, HIGH, CRITICAL) e ação recomendada (seguir_fluxo, bloquear_operacao, descartar_sinal, etc.). Casos RED devem falhar quando faltam campos obrigatórios.

2. **Idempotencia garantida por decision_id**: Suite RED validando que o mesmo decision_id não gera executando duplicada no order_layer. Casos de teste: (a) entrada com decision_id válido → transição sem erro; (b) re-entrada com decision_id idêntico → bloqueio/cancelamento; (c) decision_id ausente quando required → erro limpo.

3. **Contrato unico de erro com auditabilidade**: Suite RED para validar che todo bloqueio/falha em live_execution.py emite estrutura contendo: decision_id, execution_id, reason_code, severity, recommended_action. Falhas na emissão devem resultar em erro de contrato.

4. **Compatibilidade retroativa com M2-024.1**: Suite RED deve respeitar e estender o contrato de M2-024.1 (já concluído). Nenhuma breaking change.

5. **Fail-safe em ausencias**: Quando fields obrigatorios faltarem (decision_id, reason_code, severity), suite RED deve validar que o gate de admissão bloqueia a operação (não passa nil ou empty).

6. **Paridade shadow/live no contrato**: Suite RED deve cobrir cases tanto para shadow (test mode) quanto para live (caso de campo seja omitido em live). Comportamento esperado deve ser explícito.

## Arquitetura e integração:

- **componentes**: core/model2/order_layer.py; core/model2/live_execution.py; core/model2/live_service.py; core/model2/signal_bridge.py; tests/test_model2_*.py
- **extensoes**: Funções de avaliação em order_layer.py; catalog REASON_CODE_SEVERITY e REASON_CODE_ACTION em live_execution.py; helper de decisão em signal_bridge.py
- **guardrails**: risk_gate=ATIVO (não mockado); circuit_breaker=ATIVO (não mockado); decision_id=IDEMPOTENTE (enforçado em gate)

## Modelagem de dados:

- **entidades**: technical_signals (status CREATED); signal_executions (status READY/BLOCKED); opportunity_events (audit trail)
- **schema**: Sem alteração de tabelas. Flexão: adicionar colunas nullable em signal_executions (reason_code_key, severity_level) + JSON execution_metadata. Compatibilidade: retroativa (nullable).
- **compatibilidade**: SIM — colunas nullable, sem ALTER COLUMN, sem breaking change em queries existentes

## Plano de implementacao orientado a testes:

1. **RED para M2-024.2 (reason_code catalogue)**: Suite em tests/test_model2_m2_024_2_reason_code_catalog.py
   - Testes validando catalogação: 20+ cases de reason_code com severidade e ação
   - Cases devem falhar quando campos obrigatorios ausentes
   - Execução esperada: ~15 failed, 0 passed

2. **RED para M2-024.3 (idempotencia decision_id)**: Suite em tests/test_model2_m2_024_3_idempotence_gate.py
   - Testes de gate com mutex/deduplicação por decision_id
   - Cases: entrada nova, re-entrada idêntica, ausência de decision_id
   - Execução esperada: ~12 failed, 0 passed

3. **RED para M2-024.10 (contrato unico erro)**: Suite em tests/test_model2_m2_024_10_error_contract.py
   - Testes validando estrutura de erro (decision_id, execution_id, reason_code, severity, action)
   - Cases de falha: decision_id perdido, reason_code não no catálogo, severity inválida
   - Execução esperada: ~10 failed, 0 passed

4. **GREEN minimo**: Implementação básico suficiente para fazer cada case passar (não refactor ainda)

5. **REFACTOR mantendo verde**: Limpeza de código, consolidação de helpers, alinhamento de padrões

## Suite de testes minima obrigatoria:

- **unitarios**:
  - test_reason_code_catalog_completeness() — valida todos os codes têm severidade/ação
  - test_idempotence_gate_new_entry() — nova entrada com decision_id
  - test_idempotence_gate_duplicate_rejected() — re-entrada com decision_id idêntico bloqueada
  - test_idempotence_gate_missing_decision_id() — ausência resulta em erro limpo
  - test_error_contract_emission() — bloqueio emite estrutura completa
  - test_error_contract_fields_mandatory() — campos ausentes resultam em erro
  - test_reason_code_not_in_catalog() — reason_code fora do catálogo é rejeito
  - test_severity_valid_values() — severidade é um de [INFO, MEDIUM, HIGH, CRITICAL]

- **integracao**:
  - test_order_layer_with_reason_code_catalog() — order_layer respeita reason_code
  - test_live_service_error_emission_audit_trail() — live_service emite auditavelmente

- **regressao_risco**:
  - test_risk_gate_not_mockado() — risk_gate permanece ativo
  - test_circuit_breaker_not_mockado() — circuit_breaker permanece ativo
  - test_retrocompat_m2_024_1() — compatibilidade com M2-024.1

## Criterios de aceite objetivos:

- [ ] Suite RED criada: 37 testes mapeados (15 M2-024.2 + 12 M2-024.3 + 10 M2-024.10)
- [ ] Execução inicial demonstra falhas: pytest -q tests/test_model2_m2_024_2/3/10.py → ~37 failed, 0 passed
- [ ] Nenhum test mocker risk_gate ou circuit_breaker
- [ ] Guardrails de risco preservados (risk_gate=ATIVO, circuit_breaker=ATIVO)
- [ ] Testes determinísticos (sem flakiness)
- [ ] mypy --strict limpo em testes

## Comandos de validacao:

```bash
# RED Phase (esperado: falhas)
pytest -q tests/test_model2_m2_024_2_reason_code_catalog.py
pytest -q tests/test_model2_m2_024_3_idempotence_gate.py
pytest -q tests/test_model2_m2_024_10_error_contract.py

# Verificar mypy em novos testes
mypy --strict tests/test_model2_m2_024_2*.py tests/test_model2_m2_024_3*.py tests/test_model2_m2_024_10*.py

# Full suite (GREEN será após implementação)
pytest -q tests/
```

## Entregaveis esperados:

- Lista de arquivos de teste criados:
  - tests/test_model2_m2_024_2_reason_code_catalog.py
  - tests/test_model2_m2_024_3_idempotence_gate.py
  - tests/test_model2_m2_024_10_error_contract.py
- Resumo de risco de regressão: risk_gate/circuit_breaker não mockados, m2_024_1 retrocompat validada
- Trilha de decisão: Qual decisão de contrato priorizar? (reason_code > decision_id > error_contract sequência)
- Atualização em docs/BACKLOG.md: M2-024.2/3/10 marcadas como `TESTES_PRONTOS`

---

## Notas para Engenheiro (Software Engineer)

Quando receber GREEN phase handoff de QA:
1. Implementar helpers em order_layer.py para validação de reason_code
2. Estender REASON_CODE_CATALOG + REASON_CODE_SEVERITY + REASON_CODE_ACTION em live_execution.py
3. Gate de idempotência em signal_bridge.py (~50-100 LOC)
4. Emissão de erro com estrutura completa em live_execution.py

---

**Status**: ✅ PROMPT ACIONÁVEL GERADO
**Próxima Etapa**: QA-TDD iniciar RED Phase
