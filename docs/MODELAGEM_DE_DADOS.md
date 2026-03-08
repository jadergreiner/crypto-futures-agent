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

## Tabela: sinais tecnicos (`technical_signals`) - fase posterior

Gerada pela Ponte de Sinal apos tese validada.

Campos sugeridos:

1. `id` (PK)
2. `opportunity_id` (FK)
3. `symbol` (TEXT)
4. `side` (TEXT)
5. `entry_type` (TEXT)
6. `entry_price` (REAL)
7. `stop_loss` (REAL)
8. `take_profit` (REAL)
9. `signal_timestamp` (INTEGER UTC ms)
10. `status` (TEXT)

## Regras de integridade

1. `zone_low < zone_high`
2. `trigger_price` deve estar coerente com `side`
3. `invalidation_price` obrigatorio para toda oportunidade
4. Estado final nao pode voltar para estado anterior
5. Toda mudanca de status deve gerar evento em `opportunity_events`
