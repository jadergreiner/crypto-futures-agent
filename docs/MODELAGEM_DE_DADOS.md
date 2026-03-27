# Modelagem de Dados - Modelo 2.0

## Objetivo

Definir o modelo de dados atual da arquitetura model-driven.

## Banco canonico

1. Banco principal: `db/modelo2.db`.
2. Migracoes versionadas em `scripts/model2/migrations/*.sql`.

## Entidades principais

## 1) model_decisions

Registra a decisao emitida pelo modelo.

Campos minimos sugeridos:

1. `id` (PK)
2. `decision_timestamp` (UTC ms)
3. `symbol` (TEXT)
4. `action` (TEXT: OPEN_LONG|OPEN_SHORT|HOLD|REDUCE|CLOSE)
5. `confidence` (REAL)
6. `size_fraction` (REAL)
7. `sl_target` (REAL, nulo permitido)
8. `tp_target` (REAL, nulo permitido)
9. `model_version` (TEXT)
10. `reason_code` (TEXT)
11. `inference_latency_ms` (INTEGER)
12. `input_json` (TEXT)
13. `output_json` (TEXT)
14. `created_at` (UTC ms)

Indices recomendados:

1. `(symbol, decision_timestamp)`
2. `(model_version)`

## 2) signal_executions

Registra o ciclo operacional da execucao.

Campos minimos esperados:

1. `id` (PK)
2. `decision_id` (FK -> model_decisions.id)
3. `execution_mode` (TEXT: shadow|live)
4. `status` (TEXT)
5. `exchange_order_id` (TEXT, nulo permitido)
6. `filled_qty` (REAL, nulo permitido)
7. `filled_price` (REAL, nulo permitido)
8. `stop_order_id` (TEXT, nulo permitido)
9. `take_profit_order_id` (TEXT, nulo permitido)
10. `payload_json` (TEXT)
11. `created_at` (UTC ms)
12. `updated_at` (UTC ms)

Regras:

1. Uma decisao efetiva nao pode gerar execucao duplicada.
2. Execucao em `live` exige reconciliacao e trilha de eventos.
3. `decision_id` pode ser nulo em registros anteriores a migracao 0008.

## 3) signal_execution_events

Historico de transicoes e reconciliacao.

Campos minimos:

1. `id` (PK)
2. `signal_execution_id` (FK)
3. `event_type` (TEXT)
4. `from_status` (TEXT, nulo permitido)
5. `to_status` (TEXT, nulo permitido)
6. `event_timestamp` (UTC ms)
7. `rule_id` (TEXT)
8. `payload_json` (TEXT)

## 4) learning_episodes

Transicoes de aprendizado para retreino.

Campos minimos:

1. `id` (PK)
2. `decision_id` (FK -> model_decisions.id)
3. `state_t_json` (TEXT)
4. `action_t` (TEXT)
5. `reward_t` (REAL)
6. `state_t1_json` (TEXT)
7. `done` (INTEGER 0/1)
8. `outcome_json` (TEXT)
9. `created_at` (UTC ms)

Regra:

1. Deve incluir episodios da acao `HOLD`.

### 4.1) Contrato de persistencia M2-020.6 (`persist_learning_episode`)

Persistencia do episodio completo com foco em rastreabilidade e fail-safe.

Campos esperados quando presentes no schema:

1. `decision_id` (chave de idempotencia)
2. `execution_id` (correlacao com execucao, quando aplicavel)
3. `symbol` (correlacao por ativo)
4. `action_t`, `state_t_json`, `reward_t`, `state_t1_json`, `done`, `outcome_json`
5. `created_at` (UTC ms)

Regras:

1. `decision_id` duplicado deve bloquear nova escrita (idempotencia).
2. Erro de persistencia deve retornar fail-safe com reason code auditavel.
3. Serializacao de estado/outcome deve manter JSON valido.

## 5) training_runs

Audita retreino e promocao de versoes.

Campos minimos:

1. `id` (PK)
2. `model_version_candidate` (TEXT)
3. `dataset_window` (TEXT)
4. `metrics_json` (TEXT)
5. `go_no_go` (TEXT: GO|GO_COM_RESTRICOES|NO_GO)
6. `rollback_version` (TEXT, nulo permitido)
7. `created_at` (UTC ms)

## 6) rl_training_log

Registro de treino RL para coleta de metricas operacionais.

Campos:

1. `id` (PK)
2. `episodes_used` (INTEGER)
3. `avg_reward` (REAL, nulo permitido)
4. `completed_at` (TEXT ISO 8601 ou UTC ms)
5. `model_version` (TEXT, nulo permitido)

Uso:

1. Consultado por `cycle_report.collect_training_info()` para descobrir
   ultimo treino e episodios pendentes.

Indice:

1. `(completed_at DESC)` para busca rápida do último treino.

## 6.1) rl_training_audit (M2-022.2)

Trilha de auditoria do trigger de treino incremental.

Campos:

1. `id` (PK)
2. `triggered_at_ms` (INTEGER UTC ms)
3. `trigger_reason` (TEXT)
4. `episodes_count` (INTEGER)
5. `model_id_before` (TEXT, nulo permitido)
6. `model_id_after` (TEXT, nulo permitido)
7. `avg_reward_delta` (REAL, nulo permitido)
8. `status` (TEXT: started|blocked)
9. `created_at` (TEXT DEFAULT CURRENT_TIMESTAMP)

Uso:

1. Auditar contexto de trigger (threshold, treino em andamento, stale).
2. Suportar analise de anti-duplicidade e explicacao de bloqueio.

Indice:

1. `(triggered_at_ms DESC, id DESC)` para consulta operacional recente.

## 7) rl_episodes

Episódios de aprendizado RL capturados durante execução.

Campos:

1. `id` (PK)
2. `symbol` (TEXT)
3. `decision` (TEXT: OPEN_LONG|OPEN_SHORT|HOLD|REDUCE|CLOSE)
4. `reward` (REAL)
5. `state_json` (TEXT, nulo permitido)
6. `outcome_json` (TEXT, nulo permitido)
7. `created_at` (TEXT ISO 8601 ou UTC ms)

Uso:

1. Consultado por `cycle_report.collect_training_info()` para contar
   episódios pendentes desde o último treino.

Indice:

1. `(symbol, created_at DESC)` para busca por símbolo e tempo.
2. `(created_at)` para query de episódios pendentes pós-treino.

## Integridade obrigatoria

1. UTC ms em todos os timestamps.
2. Chaves de correlacao entre decisao, execucao e episodio.
3. Idempotencia em escrita de execucao e episodio.
4. JSON valido em todos os campos `*_json`.
5. Nenhum segredo em payload persistido.

## PKG-PO10-0326 - Impacto de dados

1. Sem criacao de novas tabelas ou colunas.
2. Contratos de resiliencia operam sobre payloads em memoria e artefatos
   existentes.
3. Validacao de schema reutiliza conjunto de tabelas obrigatorias ja definido
   em RN-020.
