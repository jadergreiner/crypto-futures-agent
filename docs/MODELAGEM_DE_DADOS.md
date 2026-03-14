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

## Atualizacao operacional 2026-03-14

A operacao da opcao `2` do `iniciar.bat` foi expandida para coleta por ciclo,
persistencia `M5` e materializacao de episodios de treino.

Mudancas de dados:

1. Banco de mercado (`db/crypto_agent.db`) inclui `ohlcv_m5`.
2. Chave primaria de OHLCV segue `PRIMARY KEY (timestamp, symbol)`.
3. `sync_market_context` aplica filtro de duplicidade por (`symbol`, `timestamp`) antes de inserir.
4. Banco M2 (`db/modelo2.db`) passa a materializar `training_episodes` para dataset incremental.

Novos artefatos operacionais:

1. `model2_market_context_*.json`
2. `model2_training_episodes_*.json`
3. `model2_training_episodes_*.jsonl`
4. `model2_training_episodes_cursor.json`



## Tabela: OHLCV M5 (`ohlcv_m5`)

Persistencia intraday para coleta por ciclo na operacao M2.

Campos:

1. `timestamp` (INTEGER UTC ms)
2. `symbol` (TEXT)
3. `open` (REAL)
4. `high` (REAL)
5. `low` (REAL)
6. `close` (REAL)
7. `volume` (REAL)
8. `quote_volume` (REAL)
9. `trades_count` (INTEGER)

Integridade:

1. `PRIMARY KEY (timestamp, symbol)`
2. Index: `idx_ohlcv_m5_symbol`



## Tabela: episodios de treino (`training_episodes`)

Materializacao incremental de episodios por ciclo operacional.

Campos principais:

1. `episode_key` (TEXT UNIQUE)
2. `cycle_run_id` (TEXT)
3. `execution_id` (INTEGER)
4. `symbol` (TEXT)
5. `timeframe` (TEXT)
6. `status` (TEXT)
7. `event_timestamp` (INTEGER UTC ms)
8. `label` (TEXT)
9. `reward_proxy` (REAL, nulo permitido)
10. `features_json` (TEXT)
11. `target_json` (TEXT)
12. `created_at` (INTEGER UTC ms)

## Tabela: taxas de financiamento da API (`funding_rates_api`)

Coleta continua de taxa de financiamento (FR) pela API Binance (Fase D.2).

Campos:

1. `id` (PK INTEGER)
2. `symbol` (TEXT, ex.: BTCUSDT)
3. `timestamp` (INTEGER UTC ms, indice)
4. `funding_rate` (REAL, valor bruto da taxa)
5. `mark_price` (REAL, preco de marca)
6. `index_price` (REAL, preco de indice)
7. `sentiment` (TEXT: bullish|neutral|bearish)
   - bullish: funding_rate > 0.0001
   - neutral: -0.0001 <= funding_rate <= 0.0001
   - bearish: funding_rate < -0.0001
8. `trend` (TEXT: increasing|stable|decreasing)
   - Comparacao: valor atual vs media movel 24h
9. `created_at` (INTEGER UTC ms, quando registrado)

Indices:

1. `idx_funding_rates_symbol_timestamp` (`symbol`, `timestamp` DESC)
2. `idx_funding_rates_sentiment` (`sentiment`)
3. `idx_funding_rates_created_at` (`created_at`)

Schema minimo esperado:
```sql
CREATE TABLE funding_rates_api (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  funding_rate REAL,
  mark_price REAL,
  index_price REAL,
  sentiment TEXT,
  trend TEXT,
  created_at INTEGER
);
```

Target: >= 1000 registros/dia por par.

## Tabela: interesse aberto da API (`open_interest_api`)

Coleta de interesse aberto (OI) para analise de sentimento (Fase D.3).

Campos:

1. `id` (PK INTEGER)
2. `symbol` (TEXT, ex.: BTCUSDT)
3. `timestamp` (INTEGER UTC ms, indice)
4. `open_interest` (REAL, OI total normalizado /100k)
5. `oi_sentiment` (TEXT: accumulating|neutral|liquidating)
   - accumulating: OI aumentando + FR bullish
   - neutral: OI estavel
   - liquidating: OI reduzindo + FR bearish
6. `change_direction` (TEXT: up|down|stable)
   - Derivada: (OI_atual - OI_24h_atras) / OI_24h_atras
7. `created_at` (INTEGER UTC ms)

Indices:

1. `idx_oi_symbol_timestamp` (`symbol`, `timestamp` DESC)
2. `idx_oi_sentiment` (`oi_sentiment`)

Schema minimo:
```sql
CREATE TABLE open_interest_api (
  id INTEGER PRIMARY KEY,
  symbol TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  open_interest REAL,
  oi_sentiment TEXT,
  change_direction TEXT,
  created_at INTEGER
);
```

## Enriquecimento de Features em training_episodes (Fases D.3, E.1)

Campo `features_json` em `training_episodes` contem 20 features escalares normalizadas para LSTM:

```json
{
  "episode_id": "EP-20260314-001",
  "timestamp": 1710417600000,
  "features_json": {
    "candle_open": 0.125,
    "candle_high": 0.342,
    "candle_low": -0.089,
    "candle_close": 0.205,
    "candle_volume": 0.567,
    "volatility_atr_14": 0.043,
    "volatility_bb_upper": 0.234,
    "volatility_bb_sma": 0.089,
    "volatility_bb_lower": -0.056,
    "multitf_h1_close": 0.101,
    "multitf_h4_close": 0.215,
    "multitf_d1_close": 0.312,
    "fr_latest_rate": 0.00031,
    "fr_avg_rate_24h": 0.00015,
    "fr_sentiment": 0.67,
    "fr_trend": 0.45,
    "oi_current": 0.789,
    "oi_sentiment": 0.56,
    "oi_change_direction": 0.32,
    "padding": 0.0
  },
  "timestamp_utc_ms": 1710417600000
}
```

Normalizacao obrigatoria:
- Todos valores em [-1.0, 1.0]
- NaN nao permitido (rejeitar episodio se falhar)
- Ordem fixa (LSTM exige consistencia)

Frequencia de atualizacao:
- A cada ciclo de pipeline (every H4 candle)
- Fallback: permitir NaN se coleta de API falhar < 10%
- Retry: tentar coleta de dados historicos via Binance REST API
