# Modelagem de Dados - Modelo 2.0

## Objetivo

Definir estrutura minima para suportar:

1. Identificacao de oportunidade.
2. Acompanhamento de tese.
3. Auditoria de transicao de estado.

## Tabela: oportunidades (`opportunities`)

Representa a tese em nivel de negocio.

Campos sugeridos:

1. `id` (PK)
2. `symbol` (TEXT, simbolo)
3. `timeframe` (TEXT, periodo)
4. `side` (TEXT: COMPRA|VENDA; internamente LONG|SHORT)
5. `thesis_type` (TEXT, tipo de tese)
6. `status` (TEXT: IDENTIFICADA|MONITORANDO|VALIDADA|INVALIDADA|EXPIRADA)
7. `zone_low` (REAL)
8. `zone_high` (REAL)
9. `trigger_price` (REAL)
10. `invalidation_price` (REAL)
11. `created_at` (INTEGER UTC ms)
12. `updated_at` (INTEGER UTC ms)
13. `expires_at` (INTEGER UTC ms)
14. `resolved_at` (INTEGER UTC ms, nulo permitido)
15. `resolution_reason` (TEXT, nulo permitido)
16. `metadata_json` (TEXT, metadados)

Contrato minimo de `metadata_json` para M2-002:

1. `rule_id` (ex.: `M2-002.1-RULE-FAIL-SELL-REGION`)
2. `rule_version` (versao do detector deterministico)
3. `technical_zone`:
   - `source` (`order_block` ou `fvg`)
   - `zone_id` (quando disponivel)
   - `timestamp`
   - `zone_low`
   - `zone_high`
   - `status`
4. `rejection_candle`:
   - `timestamp`
   - `open`
   - `high`
   - `low`
   - `close`
5. `context` (estrutura de mercado usada na decisao)
6. `parameters` (parametros deterministas aplicados)
7. `scan_timestamp`

Indices sugeridos:

1. `idx_opportunities_status` (`status`)
2. `idx_opportunities_symbol_status` (`symbol`, `status`)
3. `idx_opportunities_created_at` (`created_at`)

## Tabela: eventos de oportunidade (`opportunity_events`)

Historico completo da tese.

Campos implementados:

1. `id` (PK)
2. `opportunity_id` (FK -> opportunities.id, referencia da oportunidade)
3. `event_type` (TEXT, obrigatorio)
4. `from_status` (TEXT, nulo permitido)
5. `to_status` (TEXT, obrigatorio)
6. `event_timestamp` (INTEGER UTC ms, obrigatorio)
7. `rule_id` (TEXT, obrigatorio)
8. `payload_json` (TEXT, obrigatorio, default `'{}'`)

Indices sugeridos:

1. `idx_events_opportunity_ts` (`opportunity_id`, `event_timestamp`)
2. `idx_events_event_type` (`event_type`)

Regras de integridade implementadas:

1. FK: `opportunity_events.opportunity_id -> opportunities.id`
2. Politica FK: `ON DELETE RESTRICT` e `ON UPDATE RESTRICT`
3. `from_status` deve ser nulo ou um estado valido
4. `to_status` deve ser um estado valido
5. `event_timestamp > 0`
6. Evento inicial da tese deve respeitar `from_status = NULL` e `to_status = IDENTIFICADA`
7. Evento de monitoramento inicial deve respeitar
   `from_status = IDENTIFICADA` e `to_status = MONITORANDO`
8. Evento de validacao deve respeitar
   `from_status = MONITORANDO` e `to_status = VALIDADA`
9. Evento de invalidacao deve respeitar
   `from_status = MONITORANDO` e `to_status = INVALIDADA`
10. Evento de expiracao deve respeitar
    `from_status = MONITORANDO` e `to_status = EXPIRADA`

## Contrato canonico de estados e transicoes

Fonte canonica de aplicacao: `core/model2/thesis_state.py`.

Estados oficiais:

1. IDENTIFICADA
2. MONITORANDO
3. VALIDADA
4. INVALIDADA
5. EXPIRADA

Matriz oficial de transicao na aplicacao:

1. `NULL -> IDENTIFICADA`
2. `IDENTIFICADA -> MONITORANDO`
3. `MONITORANDO -> VALIDADA|INVALIDADA|EXPIRADA`
4. Estados finais sem transicoes de saida

Observacao:

1. `from_status = NULL` e reservado ao evento inicial de criacao da tese.

## Tabela: sinais tecnicos (`technical_signals`)

Gerada pela Ponte de Sinal apos tese validada.

Campos implementados:

1. `id` (PK)
2. `opportunity_id` (FK -> opportunities.id)
3. `symbol` (TEXT)
4. `timeframe` (TEXT)
5. `signal_side` (TEXT: LONG|SHORT)
6. `entry_type` (TEXT)
7. `entry_price` (REAL)
8. `stop_loss` (REAL)
9. `take_profit` (REAL)
10. `signal_timestamp` (INTEGER UTC ms)
11. `status` (TEXT: CREATED|CONSUMED|CANCELLED)
12. `rule_id` (TEXT)
13. `payload_json` (TEXT, default `'{}'`)
14. `created_at` (INTEGER UTC ms)
15. `updated_at` (INTEGER UTC ms)

Indices implementados:

1. `idx_technical_signals_status` (`status`)
2. `idx_technical_signals_symbol_timeframe` (`symbol`, `timeframe`)
3. `idx_technical_signals_timestamp` (`signal_timestamp`)

Regras de integridade implementadas:

1. FK: `technical_signals.opportunity_id -> opportunities.id`
2. Politica FK: `ON DELETE RESTRICT` e `ON UPDATE RESTRICT`
3. Idempotencia por oportunidade: `UNIQUE(opportunity_id)`
4. Fluxo de status de consumo na Fase 1:
   - `CREATED -> CONSUMED` (decisao registrada, sem ordem real)
   - `CREATED -> CANCELLED` (decisao bloqueada)
5. Na Fase 2, `technical_signals` NAO representa o ciclo real da ordem.
   O ciclo live passa a existir em `signal_executions`.
5. `payload_json` pode carregar trilha da camada de ordem em
   `payload_json.order_layer`.
6. `payload_json` pode carregar trilha do adaptador legado em
   `payload_json.adapter_export_trade_signals`.

## Tabela: execucoes live (`signal_executions`)

Materializacao do ciclo real/shadow do M2 apos admissao do sinal.

Campos implementados:

1. `id` (PK)
2. `technical_signal_id` (FK -> technical_signals.id, UNIQUE)
3. `opportunity_id` (FK -> opportunities.id)
4. `symbol` (TEXT)
5. `timeframe` (TEXT)
6. `signal_side` (TEXT: LONG|SHORT)
7. `execution_mode` (TEXT: shadow|live)
8. `status` (TEXT: READY|BLOCKED|ENTRY_SENT|ENTRY_FILLED|PROTECTED|EXITED|FAILED|CANCELLED)
9. `entry_order_type` (TEXT: MARKET)
10. `gate_reason` (TEXT, nulo permitido)
11. `exchange_order_id` (TEXT, nulo permitido)
12. `client_order_id` (TEXT, nulo permitido)
13. `requested_qty` (REAL, nulo permitido)
14. `filled_qty` (REAL, nulo permitido)
15. `filled_price` (REAL, nulo permitido)
16. `stop_order_id` (TEXT, nulo permitido)
17. `take_profit_order_id` (TEXT, nulo permitido)
18. `entry_sent_at` (INTEGER UTC ms, nulo permitido)
19. `entry_filled_at` (INTEGER UTC ms, nulo permitido)
20. `protected_at` (INTEGER UTC ms, nulo permitido)
21. `exited_at` (INTEGER UTC ms, nulo permitido)
22. `exit_reason` (TEXT, nulo permitido)
23. `exit_price` (REAL, nulo permitido)
24. `failure_reason` (TEXT, nulo permitido)
25. `payload_json` (TEXT, default `'{}'`)
26. `created_at` (INTEGER UTC ms)
27. `updated_at` (INTEGER UTC ms)

Indices implementados:

1. `sqlite_autoindex_signal_executions_1` (`technical_signal_id`)
2. `idx_signal_executions_status` (`status`)
3. `idx_signal_executions_symbol_status` (`symbol`, `status`)
4. `idx_signal_executions_updated_at` (`updated_at`)
5. `idx_signal_executions_mode_status` (`execution_mode`, `status`)

Regras de integridade implementadas:

1. FK: `signal_executions.technical_signal_id -> technical_signals.id`
2. FK: `signal_executions.opportunity_id -> opportunities.id`
3. Um `technical_signal` pode ter no maximo uma execucao live.
4. `signal_side` aceita apenas `LONG|SHORT`.
5. `execution_mode` aceita apenas `shadow|live`.
6. `entry_order_type` aceita apenas `MARKET` na V1 live.
7. `payload_json` carrega no minimo:
   - `signal_snapshot`
   - `gate`
   - `live_execution`

## Tabela: eventos de execucao live (`signal_execution_events`)

Historico auditavel do ciclo live.

Campos implementados:

1. `id` (PK)
2. `signal_execution_id` (FK -> signal_executions.id)
3. `event_type` (TEXT)
4. `from_status` (TEXT, nulo permitido)
5. `to_status` (TEXT, nulo permitido)
6. `event_timestamp` (INTEGER UTC ms)
7. `rule_id` (TEXT)
8. `payload_json` (TEXT, default `'{}'`)

Indices implementados:

1. `idx_signal_execution_events_execution_ts` (`signal_execution_id`, `event_timestamp`)
2. `idx_signal_execution_events_type` (`event_type`)

Regras de integridade implementadas:

1. FK: `signal_execution_events.signal_execution_id -> signal_executions.id`
2. `from_status` e `to_status` devem ser nulos ou um estado valido do live.
3. `event_timestamp > 0`.

## Tabela: snapshots do live (`signal_execution_snapshots`)

Materializacao operacional do M2-010.2.

Campos implementados:

1. `id` (PK)
2. `run_id` (TEXT)
3. `snapshot_timestamp` (INTEGER UTC ms)
4. `ready_count` (INTEGER)
5. `blocked_count` (INTEGER)
6. `entry_sent_count` (INTEGER)
7. `entry_filled_count` (INTEGER)
8. `protected_count` (INTEGER)
9. `exited_count` (INTEGER)
10. `failed_count` (INTEGER)
11. `cancelled_count` (INTEGER)
12. `unprotected_filled_count` (INTEGER)
13. `stale_entry_sent_count` (INTEGER)
14. `open_position_mismatches_count` (INTEGER)
15. `avg_signal_to_entry_sent_ms` (REAL, nulo permitido)
16. `avg_entry_sent_to_filled_ms` (REAL, nulo permitido)
17. `avg_filled_to_protected_ms` (REAL, nulo permitido)
18. `created_at` (INTEGER UTC ms)

Indices implementados:

1. `idx_signal_execution_snapshots_run` (`run_id`, `snapshot_timestamp`)
2. `idx_signal_execution_snapshots_ts` (`snapshot_timestamp`)

## Tabela: snapshots do fluxo de sinais (`signal_flow_snapshots`)

Materializacao operacional do M2-007.3.

Campos implementados:

1. `id` (PK)
2. `run_id` (TEXT)
3. `snapshot_timestamp` (INTEGER UTC ms)
4. `created_count` (INTEGER)
5. `consumed_count` (INTEGER)
6. `cancelled_count` (INTEGER)
7. `exported_count` (INTEGER)
8. `consumed_not_exported_count` (INTEGER)
9. `export_error_count` (INTEGER)
10. `export_rate` (REAL)
11. `avg_created_to_consumed_ms` (REAL)
12. `avg_consumed_to_exported_ms` (REAL)
13. `avg_created_to_exported_ms` (REAL)
14. `created_at` (INTEGER UTC ms)

Indices implementados:

1. `idx_signal_flow_snapshots_run` (`run_id`, `snapshot_timestamp`)
2. `idx_signal_flow_snapshots_ts` (`snapshot_timestamp`)

## Tabela: snapshots de painel (`opportunity_dashboard_snapshots`)

Materializacao operacional do M2-004.1.

Campos implementados:

1. `id` (PK)
2. `run_id` (TEXT, identificador da execucao)
3. `snapshot_timestamp` (INTEGER UTC ms)
4. `status` (TEXT, estado oficial)
5. `opportunity_count` (INTEGER)
6. `avg_resolution_ms` (REAL, media para o estado final quando aplicavel)
7. `avg_resolution_ms_overall` (REAL, media global de resolucao)
8. `created_at` (INTEGER UTC ms)

Indices implementados:

1. `idx_dashboard_run_status` (`run_id`, `status`)
2. `idx_dashboard_snapshot_ts` (`snapshot_timestamp`)

## Tabela: snapshots de auditoria (`opportunity_audit_snapshots`)

Materializacao operacional do M2-004.2.

Campos implementados:

1. `id` (PK)
2. `run_id` (TEXT)
3. `snapshot_timestamp` (INTEGER UTC ms)
4. `event_id` (INTEGER, referencia logica ao evento original)
5. `opportunity_id` (INTEGER)
6. `symbol` (TEXT)
7. `timeframe` (TEXT)
8. `event_type` (TEXT)
9. `from_status` (TEXT, nulo permitido)
10. `to_status` (TEXT)
11. `event_timestamp` (INTEGER UTC ms)
12. `rule_id` (TEXT)
13. `payload_json` (TEXT)
14. `created_at` (INTEGER UTC ms)

Indices implementados:

1. `idx_audit_snapshot_run` (`run_id`, `event_timestamp`, `event_id`)
2. `idx_audit_snapshot_ts` (`snapshot_timestamp`)
3. `idx_audit_snapshot_opportunity` (`opportunity_id`, `event_timestamp`)

## Regras de integridade

1. `zone_low < zone_high`
2. `trigger_price` deve estar coerente com `side`
3. `invalidation_price` obrigatorio para toda oportunidade
4. Estado final nao pode voltar para estado anterior
5. Toda mudanca de status deve gerar evento em `opportunity_events`
6. Idempotencia de criacao inicial por chave natural:
   (`symbol`, `timeframe`, `thesis_type`, `metadata_json.rejection_candle.timestamp`)
7. Snapshots materializados de observabilidade devem respeitar retencao de 30 dias
