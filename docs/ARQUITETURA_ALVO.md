# Arquitetura Alvo - Modelo 2.0

**Status:** ATIVA
**Versao:** M2-020 (model-driven)

## Visao geral

A arquitetura atual e model-driven.
O modelo decide a acao de trade diretamente e o sistema executa com
seguranca, reconciliacao e trilha auditavel.

Decisao do modelo (acoes permitidas):

1. OPEN_LONG
2. OPEN_SHORT
3. HOLD
4. REDUCE
5. CLOSE

## Principios de arquitetura

1. Decisao de trade nasce no modelo, nao em regra estrategica externa.
2. Guard-rails de risco permanecem inviolaveis.
3. Em duvida operacional, bloquear operacao (fail-safe).
4. Toda decisao e evento relevante devem ser auditaveis.

## M2-020.14 - Consolidacao documental da nova arquitetura

A M2-020.14 consolida a leitura oficial do fluxo nominal sem alterar
schema, contratos de seguranca ou logica de runtime:

1. a decisao direta do modelo continua sendo a unica fonte da acao
   oficial exibida ao operador;
2. a origem nominal puramente model-driven so vale quando
   `origin=RL_MODEL`, `action_source='rl_action'` e
   `rl_fallback=False`;
3. `legado heuristico`, `signal_side` e `fallback_action` ficam
   restritos a rollback explicito, diagnostico e auditoria;
4. `risk_gate`, `circuit_breaker` e `decision_id` seguem como
   invariantes de fail-safe e rastreabilidade.

## Fluxo Live Ponta-a-Ponta

O ciclo live segue um fluxo unico, auditavel e ponta-a-ponta entre as
camadas principais do Modelo 2.0:

1. warm-up e construcao do estado de mercado multi-timeframe;
2. inferencia da policy com `model_inference_service.py`;
3. validacao do safety envelope via `risk_gate` e `circuit_breaker`;
4. execucao de ordem permitida pela camada live;
5. reconciliacao de fills, protecoes e saidas externas.

Metricas operacionais por etapa critica:

1. latencia de inferencia para detectar degradacao de resposta;
2. taxa de bloqueio por risco para monitorar pressao do safety envelope;
3. divergencia de reconciliacao entre banco e exchange;
4. posicoes sem protecao como alerta critico de operacao;
5. falhas de idempotencia por `decision_id` para auditoria.

A referencia cruzada operacional destas metricas fica em
`docs/RUNBOOK_M2_OPERACAO.md`, onde a triagem de incidente detalha a
acao fail-safe por etapa.

## Healthcheck e Componentes Monitorados

Os componentes abaixo devem permanecer monitorados antes e durante a
operacao live:

1. `scripts/model2/go_live_preflight.py` — valida pre-condicoes, risco,
   schema e evidencia minima antes do go-live;
2. `scripts/model2/healthcheck_live_execution.py` — verifica a saude da
   execucao, reconciliacao e promocao GO/NO-GO no runtime;
3. `core/model2/live_service.py` — aplica guardrails antes do envio de
   ordens e publica trilha auditavel da execucao;
4. `core/model2/live_execution.py` — consolida `reason_code`, severidade
   e `recommended_action` para falhas e bloqueios.

## Componentes principais

## Camada 1 - Coleta de Estado de Mercado

Responsavel por consolidar estado para inferencia:

1. OHLCV multi-timeframe.
2. Features tecnicas e contexto de mercado.
3. Estado de posicao e restricoes operacionais.

Saida:

1. Objeto de estado unico para inferencia.

## Camada 2 - Policy Model (Decisor)

Responsavel por inferencia da acao de trading.

Implementacao vigente do ponto de inferencia desacoplado:

1. `core/model2/model_inference_service.py`
2. Contrato de decisao: `core/model2/model_decision.py`

Implementacao de RL por simbolo (Iniciativa M2-019):

1. `agent/entry_decision_env.py` — Gym.Env para decisao de entrada
2. Environment action space: NEUTRAL(0), LONG(1), SHORT(2)
3. Environment observation space: 36 features normalizadas
4. Reward retroativo: outcome real de execucao de sinal
5. Runtime no pipeline diario: `persist_training_episodes` ->
   `train_entry_agents` -> `entry_rl_filter` -> `order_layer`
6. `entry_rl_filter` aplica threshold, fallback e cancelamento auditavel
   antes de liberar sinal para execucao
7. No fluxo nominal, `origin=RL_MODEL` so e valido quando
   `action_source='rl_action'` e `rl_fallback=False`.
8. `signal_side`, `fallback_action` e `execution.heuristic_signals`
   ficam restritos a auditoria ou rollback fail-safe explicito.

Entradas:

1. Estado de mercado consolidado.
2. Estado operacional (posicao, risco, limites).

Saida:

1. Acao + confianca + parametros de execucao.
2. Metadados de inferencia: `model_version`, `inference_latency_ms`.

## Camada 3 - Safety Envelope

Responsavel por seguranca operacional obrigatoria:

1. `risk/risk_gate.py`
2. `risk/circuit_breaker.py`
3. Validacoes de preflight do live, incluindo prontidao de alertas.

Comportamento:

1. Permitir execucao quando seguro.
2. Bloquear quando houver risco ou incerteza relevante.

## Camada 4 - Execucao e Reconciliacao

Responsavel por:

1. Traduzir acao do modelo em ordem.
2. Confirmar fill e armar protecao obrigatoria.
3. Reconciliar banco com exchange.
4. Marcar divergencia critica como `FAILED` com alerta e auditoria.

Componentes referencia:

1. `core/model2/live_service.py`
2. `core/model2/live_exchange.py`
3. `core/model2/live_execution.py`
4. `scripts/model2/go_live_preflight.py`

Contrato unificado de erros (M2-023.1, estendido em M2-024.1):

- Todo bloqueio ou falha emite `reason_code`, `severity`,
  `recommended_action`, `decision_id` e `execution_id`.
- Catalogo canonico: `REASON_CODE_CATALOG` em `live_execution.py`
  (36 entries com `REASON_CODE_SEVERITY` e `REASON_CODE_ACTION` simetricos).
- Unificacao M2-024.2: `order_layer.py` importa `REASON_CODE_CATALOG` de
  `live_execution.py` — fonte unica, sem copia local.
- Erros desconhecidos: fallback fail-safe via
  `classify_unknown_execution_error()` com severidade CRITICAL.
- Validacao de contrato no `order_layer` (M2-024.1): sinais com
  `decision_id` ou `decision_origin` passam por strict_contract
  opt-in antes de avançar para execucao live.
- Gate de idempotencia (M2-024.3): `order_layer` chama
  `is_decision_id_duplicate` de `signal_bridge` antes de processar.
  Se duplicado, retorna CANCELLED com reason `duplicate_decision_id`.
  Apos CONSUMED, `mark_decision_id_processed` registra o decision_id.
  Fluxo legado (decision_id=None) nao e afetado.
- Retry controlado de exchange (M2-024.4): `io_retry.py` fornece
  `classify_exchange_exception` (transient|permanent),
  `exchange_retry_with_budget` (max 3 tentativas, backoff exponencial)
  e `ExchangeRetryBudgetError`.
  `live_service.py` expoe `_place_market_entry_with_retry` que aplica o
  retry e retorna None (fail-safe) apos budget esgotado.
  Guardrails intactos.
- Timeout por etapa (M2-024.5): `core/model2/execution_timeout.py` fornece
  `StageTimeoutPolicy` (frozen dataclass, defaults: admissao=5s, envio=10s,
  reconciliacao=30s), `check_admission_timeout`, `check_send_timeout`,
  `check_reconciliation_timeout` e `emit_timeout_telemetria`. Gate de admissao
  integrado em `order_layer.py` via parametro opcional `timeout_policy`.
  Reason codes `TIMEOUT_ADMISSION`, `TIMEOUT_SEND`, `TIMEOUT_RECONCILIATION`
  adicionados ao `REASON_CODE_CATALOG` com severity=HIGH e
  action=bloquear_operacao. Modulo nao importa risk_gate nem circuit_breaker.
- Integracao Testnet ponta a ponta (M2-024.12): `go_live_preflight.py`
  publica `testnet_evidence` no summary (inclui `testnet_credentials` e
  contrato de correlacao `decision_id/execution_id/reason_code/severity/
  recommended_action`). No modo shadow, `_execute_ready_signal` retorna esses
  campos canonicos para manter auditabilidade consistente entre preflight e
  execucao.
- Gate de contrato de schema no preflight (M2-024.13): check 3 valida
  tabelas/colunas obrigatorias e presenca da migracao alvo (ultima versao em
  `schema_migrations`). Em divergencia, bloqueia com evidencia estruturada
  (`missing_tables`, `missing_columns`, `missing_migrations`,
  `applied_migrations`, `expected_latest_migration`).
- Endurecimento do check 3 no warm-up (M2-022.1): o contrato de schema agora
  tambem expõe `severity_counts`, `max_severity`, `coverage_pct`,
  `foreign_key_check` e `scope_boundary`. Violacoes `CRITICAL` ou `HIGH`
  propagam `summary.reason_code='schema_divergence'` antes do live, enquanto
  `candle_freshness`, `train_checkpoint` e `train_episodes` permanecem fora do
  check 3 e seguem na trilha `M2-025.14` (`DATA_CONSISTENCY_FAIL`).
- Contrato de erro de execucao auditavel (M2-024.10):
  `LiveExecutionErrorContract` frozen dataclass em
  `live_execution.py` com campos obrigatorios `decision_id`,
  `execution_id`, `reason_code`, `severity`, `recommended_action`
  e campo opcional `additional_context`.
  Imutabilidade garantida por frozen=True.
  Toda falha ou bloqueio deve ser representada por esta estrutura para
  rastreabilidade ponta a ponta.

Politica de rollback por severidade (M2-024.14):

- `core/model2/rollback_policy.py` com:
  - `ROLLBACK_ACTION_INTERRUPT` = "INTERRUPT_AND_HALT"
  - `ROLLBACK_ACTION_OBSERVE` = "OBSERVE_AND_ALERT"
  - `ROLLBACK_ACTION_LOG` = "LOG_ONLY"
  - `get_rollback_action(severity)`: CRITICAL/HIGH -> INTERRUPT;
    MEDIUM -> OBSERVE; LOW/INFO -> LOG; desconhecido -> INTERRUPT (fail-safe)
  - `evaluate_rollback(severity, reason_code)`: retorna action, safe_to_resume
    e alert_message. Nunca levanta excecao.

Governanca de docs e runbook do pacote M2-024 (M2-024.15):

- Consolidar runbook unico do pacote M2-024 como trilha de operacao segura
  para incidentes, degradacao e retomada controlada.
- Manter matriz de guardrails (`risk_gate`, `circuit_breaker`, `decision_id`)
  explicitando invariantes que nao podem ser bypassados em nenhum stage.
- Centralizar evidencias do pacote no backlog e no audit trail `[SYNC]`,
  garantindo rastreabilidade entre arquitetura, regras e execucao.

Resiliencia e fail-safe de pipeline (M2-027):

- `core/model2/cycle_watchdog.py` — modulo transversal de resiliencia com:
  - `CycleWatchdog`: detecta travamento por ausencia de progressao em janela
    configuravel (padrao 300s); aciona fail-safe preservando estado sem
    desabilitar risk_gate ou circuit_breaker.
  - `validate_schema_pre_exec`: valida tabelas obrigatorias no
    modelo2.db antes de cada ciclo; bloqueia com
    `reason_code='schema_divergence'` em divergencia.
  - `detect_orphan_positions`: compara posicoes abertas na exchange vs
    signal_executions IN_PROGRESS; identifica posicoes sem monitoramento.
  - `build_orphan_exit_order`: constroi ordem de saida orfa com STOP_MARKET
    obrigatorio e audit_event com decision_id sintetico.
  - `execute_atomic_state_transition`: garante transicao CONSUMED->IN_PROGRESS
    atomica com revert logico em falha da segunda escrita.
- `REASON_CODE_CATALOG` expandido com `orphan_position` (M2-027.3).
- `core/model2/resilience_controls.py` (PKG-PO10-0326) — funcoes puras para
  contrato de resiliencia operacional:
  - drift gate pre-admissao (`evaluate_position_drift_gate`) — bloqueia
    nova admissao quando drift entre `position_qty` local e observado
    supera `threshold_pct`; retorna `allow`, `reason_code`
    ('position_drift_blocked' ou None), `decision_id` e `drift_pct`;
    baseline protege contra divisao por zero (M2-023.2, ADR-002/007)
  - degradacao por latencia (`evaluate_latency_degradation`) — avalia
    entrada no modo degradado (p95_ms > p95_limit_ms ou p99_ms >
    p99_limit_ms) e saida do modo: `exit_ready=True` somente quando
    `stable_window_count` medicoes consecutivas ficam abaixo do SLO;
    janela vazia ou insuficiente retorna `exit_ready=False`; retrocompat
    com chamadas sem janela (M2-023.3, ADR-002/007)
  - restart idempotente (`plan_restart_from_snapshot`) — valida snapshot
    obrigatorio com `decision_id`, `phase` e `heartbeat_ms`; retorna
    `valid_snapshot` (bool), campos auditaveis e `send_new_order`
    conservador (False quando `has_open_order=True`, snapshot invalido
    ou fase ja executada: ENTRY_FILLED | PROTECTION_ARMED | MONITORING |
    CLOSING); fail-safe: campos ausentes nao geram excecao; funcao pura
    sem side-effects (M2-023.4, ADR-002/ADR-004/ADR-009)
  - fila priorizada (`prioritize_events`, `record_event_processing_time`,
    `get_event_processing_metrics`, `reset_event_processing_times`) —
    `prioritize_events` ordena eventos por classe (CRITICAL=0, HIGH=1,
    WARN=2; classe desconhecida ao final), garantindo que eventos criticos
    sejam processados primeiro (M2-023.5, criterios 1+2); metricas de
    tempo de processamento acumuladas em `_event_processing_times`
    (module-level); `record_event_processing_time(priority, elapsed_ms)`
    registra elapsed_ms por classe; `get_event_processing_metrics()`
    retorna dict com `mean_ms` e `count` por classe presente; `reset_
    event_processing_times()` zera estado para testes e reinicio de
    sessao; fail-safe: excecoes nao propagam para o caller; funcoes
    puras, sem schema DB (M2-023.5, ADR-002/ADR-009)
  - trilha filtrada por decision_id (`query_risk_gate_audit_by_decision_id`)
  - trilha ponta-a-ponta do DB por decision_id
    (`build_risk_gate_audit_trail`) — consulta `signal_executions JOIN
    signal_execution_events` retornando lista com execution_id,
    reason_code, symbol, timestamp_ms e metadata; fail-safe sem excecao
    (M2-023.6, ADR-002/007)
  - validacao cruzada antes da admissao
    (`cross_validate_signal_context_position`) — bloqueia quando sinal
    contradiz tendencia de mercado (LONG+DOWN ou SHORT+UP) ou quando
    posicao ja esta aberta na mesma direcao (double-exposure); retorna
    `allow`, `reason_code` (`cross_validation_conflict` |
    `position_already_open` | None) e `decision_id` auditavel; funcao
    pura, fail-safe com campos ausentes, retrocompat via `decision_id=0`
    (M2-023.7, ADR-002/ADR-004/ADR-009)
  - retry orientado a categoria (`execute_with_category_retry`) —
    separa categorias retentaveis (transient/timeout) de permanentes;
    retorna `actual_attempts` (tentativas reais), `max_attempts`,
    `reason_code` auditavel e `should_retry`; backoff configuravel via
    `backoff_seconds` entre tentativas transientes; acumula contadores
    por categoria; fail-safe: excecao nunca propaga para o caller;
    `build_retry_category_report()` retorna dict de contagens acumuladas;
    `reset_retry_counters()` zera estado para testes e reinicio de sessao
    (M2-023.8, ADR-002/ADR-004/ADR-009)
  - indicadores de reconciliacao (`compute_reconciliation_health_indicators`
    e `check_reconciliation_health_alerts`) — `compute_reconciliation_
    health_indicators` agrega drift_mean, confirmation_p95_ms e
    adjustment_rate a partir de amostras; `check_reconciliation_health_
    alerts(metrics, thresholds)` compara cada metrica com o limite
    correspondente (drift_mean_limit, p95_limit_ms,
    adjustment_rate_limit) e retorna lista de dicts com severity,
    indicator_name, value e threshold_exceeded para cada metrica que
    ultrapassar o limite; limites sao configurados externamente (nao
    hardcoded); fail-safe: metricas ou limites ausentes retornam lista
    vazia sem excecao; funcao pura e deterministica
    (M2-023.9, ADR-002/ADR-009)
  - validacao de runbook (`validate_contingency_runbook`)
  - validacao de schema por conjunto de tabelas (`validate_schema_tables`)
  - reconciliacao fail-safe de lado/quantidade da posicao em
    `core/model2/live_service.py`, com `FAILED` auditavel quando a
    exchange diverge do `signal_side` esperado

## Camada 5 - Persistencia e Aprendizado Continuo

Responsavel por:

1. Persistir decisoes e resultados.
2. Persistir episodios completos para treino.
3. Persistir rewards para operar e nao operar.
4. Habilitar retreino automatico governado.

Persistencia de decisao no estado atual:

1. Tabela `model_decisions` para trilha da inferencia.
2. Vinculo opcional `signal_executions.decision_id` para correlacao.

**M2-028.7 (Alerta de degradacao RL por simbolo)**:

1. `core/model2/model_degradation_monitor.py` combina duas fontes:
  `model_decisions` para media de confianca recente e
  `training_episodes` para hit rate e regressao entre janelas.
2. `core/model2/live_service.py` resolve thresholds por simbolo via
  `config/risk_params.py`, publica alerta `MODEL_DEGRADATION` e registra
  flag `model_degradation_priority` em `rl_training_audit`.
3. O alerta e nao bloqueante: a admissao segue o fluxo normal, enquanto o
  backlog operacional de treino ganha prioridade auditavel por simbolo.

**M2-020.7 (Reward deterministico operar vs HOLD)**:

1. `scripts/model2/persist_training_episodes.py`:
   - `_reward_label` preserva contrato legado por default (reward bruto +
     `breakeven`) e permite custo operacional em opt-in
     (`apply_operational_cost=True`);
   - `_reward_counterfactual` mantem regra deterministica para HOLD/BLOCKED.
2. `scripts/model2/train_ppo_incremental.py` e
   `scripts/model2/train_ppo_lstm.py`:
   - `_compute_reward` aplica penalidades deterministicas por episodio
     (`overtrading`, `risk_gate`, `circuit_breaker`, duplicidade de
     `decision_id`) no consumo de dataset de treino.
3. `scripts/model2/operator_cycle_status.py`:
   - `_query_episode_info` prioriza reward nao-neutro mais recente quando o
     ultimo episodio tiver reward neutro cronico.
4. `core/model2/cycle_report.py`:
   - compatibilidade com legado de `created_at` numerico preservada para
     manter contagem de pendentes reproduzivel no ciclo operacional.

## Camada 6 - Observabilidade e Reporting

Responsavel por:

1. Consolidar e formatar status do ciclo de forma clara e auditavel.
2. Comunicar decisao + reward + treino + posicao aberta ao operador.
3. Coletar metricas de execucao (latencia, precisao, P&L).

Componentes:

1. `core/model2/cycle_report.py` — Modulo de formatacao de relatorios
2. `SymbolReport` — Dataclass com metricas do ciclo por simbolo
3. `format_symbol_report()` — Bloco ASCII legivel
4. `format_cycle_summary()` — Resumo do ciclo com N simbolos;
   timestamp do header via `now_brt_str()` de `time_utils` (M2-025.2)
5. `core/model2/time_utils.py` — Utilitario canonico obrigatorio de exibicao
   de timestamps; toda conversao BRT passa por `now_brt_str()`,
   `ts_ms_to_brt_str()` ou `posix_to_brt_str()`; persistencia permanece
   como `int` UTC ms

**M2-025.1/025.3 (Frescor e lacuna de candles)**:

- `resolve_candle_freshness_contract(ts_ms, symbol, mode)` em
  `core/model2/cycle_report.py`: retorna `CandleFreshnessContract` com
  `candle_state` (fresh|stale|absent) e `freshness_reason`.
  Janela: live=120s, shadow=300s. Fail-safe: absent se ts_ms=None.
  Propagado em `live_service` e `operator_cycle_status`.
- `detect_candle_gap(symbol, timeframe, last_candle_ts_ms, gap_window_ms)`
  (M2-025.3): detecta lacuna por janela configuravel (padrao 300s).
  Retorna `has_gap`, `gap_ms`, `gap_reason` (absent|stale|'') e
  `alert_message`. Nunca levanta excecao (fail-safe conservador).
  `DEFAULT_GAP_WINDOW_MS=300_000` exportado do modulo.

**BLID-082 reabertura (Contrato Candles auditavel no iniciar.bat)**:

- `scripts/model2/operator_cycle_status.py` aplica contrato multi-timeframe por
  simbolo para `D1/H4/H1/M5` na linha `Candles`.
- A exibicao separa explicitamente origem de contagem:
  - `scan=<n>`: janela operacional do scanner/runtime
  - `db=<n>`: total persistido em `db/crypto_agent.db` (`ohlcv_*`)
- Estados operacionais explicitos por timeframe:
  `fresh`, `stale`, `absent`, `nao_executado`, `sem_persistencia`,
  `degradado` (fail-safe em indisponibilidade de fonte).
- Regra de auditabilidade: `M5: N/A` nao pode aparecer quando houver
  persistencia em `ohlcv_m5` para o simbolo.

**BLID-101 (Contrato verificavel de decisao no iniciar.bat)**:

- `scripts/model2/operator_cycle_status.py` publica `contract=BLID-101-v1`
  no bloco por simbolo para versionar o contrato textual de auditoria.
- Linha `Decisao` (quando correlacionada) deve incluir:
  `decision_id`, `model_version`, `reason`, `source` e `confianca`.
- Linha `Frescor` deve incluir:
  `signal_ts`, `signal_age_ms`, `max_signal_age_ms`,
  `M5_last`, `H1_last`, `H4_last`, `D1_last`.
- Linha `Features` deve explicitar vetor usado na inferencia e
  `snapshot_at` da decisao.
- Linha `Persist.` deve correlacionar ponta a ponta:
  `model_decisions -> signal_executions -> training_episodes` por simbolo.
- Fallback legado obrigatorio:
  quando nao houver vinculo por `decision_id`, expor
  `LEGACY_NO_DECISION_LINK` sem mascarar lacuna.
- Linha `Candles` preserva contrato anterior e inclui `window_ms` explicito.

**BLID-102 (Clareza operacional de episodio e treino)**:

- O `operator_cycle_status` adota camada dupla no status por simbolo:
  tecnica (ids/campos auditaveis) e humana (explicacao operacional curta).
- Linha `Episodio` passa a explicitar:
  `episode_type` (`TRADE_EPISODE` ou `CYCLE_CONTEXT`) e
  `eligibility_for_training` (`ELIGIBLE`/`NOT_ELIGIBLE`).
- Linha `Persist.` em legado preserva trilha tecnica
  (`model_decisions`, `signal_execution`, `episode`) e adiciona
  `human_reason` para traduzir `LEGACY_NO_DECISION_LINK`.
- Linha `Treino` passa a explicitar regra de elegibilidade
  (`eligibility_rule`), ponto de corte (`cutoff_ms`) e `timeframe`
  aplicado na contagem de pendencias.
- Linha `Aud24h` mantem contrato tecnico
  (`started`, `running_block`, `conclusivo`) e adiciona
  `aud24h_human` para leitura imediata do operador.
- Em indisponibilidade de DB/consulta, o contrato mantem fail-safe:
  bloco renderizavel com lacuna explicita e sem mascaramento.

**BLID-104 (Prontidao de promocao por simbolo)**:

- Linha `Promocao` adicionada ao bloco por simbolo em
  `operator_cycle_status.py` via helper
  `_build_promotion_readiness_line(symbol, risk_state, tf_statuses)`.
- Deriva tres pilares de evidencia dos dados ja disponiveis no ciclo:
  `risk_evidence_ok` (CB=normal e RG=ok), `stability_evidence_ok`
  (todos os timeframes frescos), `consistency_evidence_ok` (ao menos
  1 timeframe fresco).
- Chama `PromotionEvaluator().evaluate_evidence_gate()` (ADR-007).
- GO exibe `[PRONTO PARA PROMOCAO]`; NO_GO exibe razao principal
  (max 60 chars).
- `decision_id` estavel por janela de 5 minutos (idempotente).
- Fail-safe: qualquer excecao retorna "N/A" sem propagar (ADR-002).



- `detect_candle_gap(symbol, timeframe, last_candle_ts_ms, gap_window_ms)`
  em `core/model2/cycle_report.py` (M2-025.3): detecta lacuna por janela
  configuravel (DEFAULT_GAP_WINDOW_MS=300_000). Retorna has_gap, gap_ms,
  gap_reason (absent|stale|'') e alert_message. Fail-safe: sem excecao.
- `check_stale_circuit_breaker(stale_count, max_stale)` (M2-025.9):
  acionado quando stale_count >= max_stale. Retorna tripped, reason e
  alert_message. Fail-safe: TRIPPED em excecao.

**M2-025.4/025.5 (Guardrail de treino + Idempotencia de episodios)**:

- `check_training_data_minimum(db_path, min_episodes)` em
  `scripts/model2/persist_training_episodes.py`:
  retorna `(ok, reason_code, count)`. Bloqueia treino com
  `reason_code=insufficient_training_data` quando count < min_episodes.
  Fail-safe: retorna `(False, "insufficient_training_data", 0)` em erro.
- `is_episode_duplicate(db_path, decision_id)` no mesmo modulo:
  verifica por coluna `decision_id` (se existir) ou fallback por
  `episode_key LIKE %:decision_id:%`. Retorna False para decision_id=None
  (legado) e em caso de excecao (fail-safe).
- `persist_learning_episode(...)` no mesmo modulo (M2-020.6):
  persiste episodio completo em `learning_episodes` com deteccao dinamica
  de schema, idempotencia por `decision_id` e retorno fail-safe auditavel
  (`learning_episode_persist_failed`) em erro de persistencia.

**M2-025.6 (Correlacao auditavel por ciclo)**:

- `DetectorInput` e `DetectionResult` em `core/model2/scanner.py` passam a
  aceitar `cycle_id` opcional (`str | None`) sem quebrar chamadas legadas.
- `detect_initial_short_failure(...)` propaga `cycle_id` para
  `DetectionResult.cycle_id` e para `metadata["cycle_id"]` quando presente.
- `Model2ThesisRepository.create_initial_thesis(...)` em
  `core/model2/repository.py` persiste `cycle_id` no `metadata_json` da
  `opportunities` sem alteracao de schema.
- Compatibilidade retroativa: ausencia de `cycle_id` preserva comportamento
  anterior e idempotencia vigente por chave natural/`decision_id`.

**M2-025.7 (Retry seguro para leitura de mercado)**:

- `core/model2/market_reader.py` introduz contrato dedicado de leitura com:
  - `RetryPolicy` (frozen dataclass: `max_retries`, `backoff_base_ms`,
    `max_budget_ms`)
  - `classify_market_read_exception` (transient|permanent)
  - `read_market_with_retry` com fallback conservador em falha
- Integracao operacional em `core/model2/live_service.py`:
  `_build_gate_input` chama `_read_market_state_with_retry` no caminho
  produtivo antes da montagem de `LiveExecutionGateInput`.
- Semantica canonica de erros em `REASON_CODE_CATALOG`:
  - `MARKET_READ_RETRY_EXHAUSTED`: budget/tentativas esgotados
  - `MARKET_READ_PERMANENT_FAILURE`: erro permanente sem retry adicional
- Guardrails preservados: `risk_gate`, `circuit_breaker` e idempotencia por
  `decision_id` permanecem ativos; em ambiguidade, fallback fail-safe.

**M2-025.8 (Timeout por etapa critica de dados)**:

- `core/model2/pipeline_timeout.py` define contrato dedicado para pipeline de
  dados com:
  - `TimeoutPolicy` (frozen dataclass: `collect_timeout_ms`,
    `validate_timeout_ms`, `consolidate_timeout_ms`)
  - checks deterministicas por etapa:
    `check_collect_timeout`, `check_validate_timeout`,
    `check_consolidate_timeout`
  - wrappers de short-circuit:
    `wrap_scanner_with_timeout` e `wrap_validator_with_timeout`
- Integracao de telemetria em `core/model2/observability.py`:
  `emit_stage_timeout_telemetry` gera payload auditavel
  (`event_type='stage_timeout_expired'`) e registra latencia com
  `resultado='timeout_expired'`.
- Mapeamento de etapa para latencia operacional:
  `collect -> scan`, `validate -> validate`, `consolidate -> signal`.
- Guardrails preservados: nao ha bypass de `risk_gate` ou
  `circuit_breaker`; `decision_id` permanece preservado no wrapper de
  validacao.

**M2-025.10 (Snapshot unico de dados por ciclo)**:

- `core/model2/cycle_snapshot.py` introduz:
  - `CycleSnapshot` (frozen dataclass) com consolidado de `candle`,
    `decisao`, `episodio` e `treino` por `cycle_id`;
  - `CycleSnapshotRepository` com agregacao por `cycle_id`, merge
    conservador e upsert unico em `cycle_snapshots`.
- Persistencia dedicada:
  - migration `scripts/model2/migrations/0014_create_cycle_snapshots.sql`
    cria tabela `cycle_snapshots` com colunas JSON (`candle_json`,
    `decisao_json`, `episodio_json`, `treino_json`) e `updated_at`.
- Integracao operacional:
  - `Model2ObservabilityService.record_cycle_snapshot(...)` passa a
    atualizar automaticamente o consolidado de ciclo quando `cycle_id`
    estiver presente.
- Guardrails preservados:
  - sem bypass de `risk_gate`/`circuit_breaker`;
  - idempotencia por `decision_id` mantida;
  - ausência de `cycle_id` nao quebra compatibilidade legada.

**M2-026 (Observabilidade + Auditoria + Conformidade)**:

1. `core/model2/risk_gate_telemetry.py` — Telemetria de bloqueios do
   `risk_gate` (M2-026.1)
   - `RiskGateBlockEvent` (frozen dataclass): `reason_code`,
     `condition`, `limit_value`, `actual_value`, `decision_id`,
     `timestamp_ms` — imutavel e auditavel
   - `RiskGateTelemetryRecorder`: append-only; metodos record(), total_events(),
     all_events(), query_by_reason() com count e percentual por reason_code
   - Hook em `live_service._enforce_guardrails_before_order`: registra bloqueio
     com decision_id quando risk_gate_allows_order=False
   - Telemetria in-memory por ciclo; sem schema DB novo; guardrails intactos

2. `core/model2/audit_decision_execution.py` — Auditoria imutavel (M2-026.3)
   - `AuditDecisionExecution` (frozen dataclass): decision_id, execution_id,
     signal_id, timestamp_utc, decision_status, execution_status,
     error_reason, additional_context
   - `AuditDecisionExecutionRepository`: INSERT-only; UPDATE/DELETE levantam
     NotImplementedError
   - Migration 0013: tabela `audit_decision_execution` com indices em
     decision_id/execution_id/signal_id
   - Integrado no preflight check3: tabela obrigatoria verificada

3. `core/model2/circuit_breaker_events.py` — CircuitBreakerEventRecorder
   - Registra transicoes: CLOSED->OPEN->HALF_OPEN->CLOSED
   - Query rapida: get_history_24h(), get_current_state()
   - Singleton pattern com reset para testes

4. `management/logging_retention.py` — LogRotationManager + RetentionPolicy
   - Rotacao automatica por tamanho (100MB) e tempo
   - Retencao: CRITICAL 365d, ERROR 90d, WARN 14d, INFO 7d
   - Config centralizado em config/logging_retention_policy.yaml

5. `core/model2/dashboard_operational.py` — Dashboard operacional (M2-026.4)
   - `query_operational_status(db_path, symbol)`: sumario consolidado
   - `query_by_symbol(db_path, symbol, limit)`: oportunidades ativas (max 100)
   - `query_by_period(db_path, start, end, symbol, limit)`: eventos por janela
   - `sort_alerts_by_severity(alerts)`: CRITICAL > ERROR > WARN > INFO
   - MAX_ROWS_PER_QUERY=100 enforca limite em todas queries

**M2-028.1 (Gate de Promocao GO/NO-GO shadow→paper)**:

1. `core/model2/promotion_gate.py` — contrato de avaliacao de promocao
   - `PromotionConfig`: thresholds configuraveis (`min_win_rate`,
     `min_episodes`, `max_drawdown_pct`)
   - `PromotionResult` (frozen dataclass): decisao GO/NO-GO,
     `reasons` e `evaluated_at` ISO UTC
   - `PromotionEvaluator`: avalia criterios de forma fail-safe
     (nunca lanca excecao)
   - Defaults conservadores: `win_rate >= 55%`, `episodes >= 30`,
     `drawdown <= 5%`

**M2-020.11 (Gate de evidencia minima GO/NO-GO)**:

1. `core/model2/promotion_gate.py` expandido com:
   - `PromotionEvidenceResult` (frozen dataclass): `decision`, `reasons`,
     `decision_id`, flags de evidencia e `evaluated_at`
   - `PromotionEvaluator.evaluate_evidence_gate(...)`: fail-safe conservador
     para risco/estabilidade/consistencia com bloqueio automatico (NO_GO)
     quando qualquer evidencia estiver ausente
2. `scripts/model2/healthcheck_live_execution.py` passa a gerar bloco
   `promotion_gate` no summary de runtime com decisao GO/NO_GO e motivos,
   tornando a trilha observavel no ciclo operacional iniciado por `iniciar.bat`.

**M2-020.10 (Retreino automatico governado — ciclo continuo)**:

1. `scripts/model2/continuous_learning_controller.py` — controlador
   de gatilho de retreino automatico:
   - `should_run_continuous_cycle(min_new_episodes, symbols)`: avalia
     threshold de episodios novos por simbolo e intervalo minimo;
     retorna `(bool, reason_str)` fail-safe sem lancar excecao
   - `mark_run_executed(symbol, state_file)`: persiste timestamp de
     ultima execucao para controle de janela temporal
   - Estado por simbolo em JSON (STATE_FILE); idempotente por janela
   - Threshold padrao via `RETRAIN_EPISODE_THRESHOLD` de `cycle_report`
2. `scripts/model2/continuous_learning_cycle.py` — ciclo continuo com
   gate de promocao:
   - `run_continuous_learning_cycle_once(db_path, symbol, timeframe)`:
     pipeline completo (probe de decisao, drift, treino, gate)
   - Fases auditaveis via `_run_stage` (nome, funcao, kwargs);
     falha de fase nao interrompe trilha de execucao
   - `PromotionEvaluator.evaluate()` pos-treino: so promove quando
     `win_rate >= 55%`, `episodes >= 30`, `drawdown <= 5%`
   - Resultado persistido em `training_runs` (go_no_go, metrics_json)
3. `core/model2/continuous_cycle.py` — integracao PromotionGate:
   - Liga resultado de treino ao gate antes de qualquer promocao
   - Fail-safe: excecao em gate retorna NO_GO conservador
4. Guardrails: `risk_gate=ATIVO`, `circuit_breaker=ATIVO`,
   `decision_id=IDEMPOTENTE` (M2-020.10, ADR-006/ADR-007)

**M2-028.10 (Governanca e runbook do pacote M2-028)**:

1. Consolidacao de promocao GO/NO-GO em dois gates auditaveis:
   - shadow->paper: `PromotionEvaluator.evaluate()` com thresholds de
     win_rate, episodios e drawdown (RN-023).
   - paper->live: `PromotionEvaluator.evaluate_paper_to_live()` com
     aprovacao manual, reconciliacao e erros criticos (M2-028.2).
2. Risco dinamico padronizado no ciclo:
   - sizing por volatilidade via `core/model2/volatility_sizing.py`
     integrado no `live_service` (M2-028.3).
   - bloqueio por concentracao de correlacao via config e
     `reason_code=PORTFOLIO_CORRELATION_LIMIT` (M2-028.5).
3. Automacao de qualidade no fluxo operacional:
   - benchmark por etapa com baseline e alerta de regressao p95>
     2x em `core/model2/latency_metrics.py` e
     `scripts/model2/daily_pipeline.py` (M2-028.8).
   - gate de cobertura critica por modulo com minimo 80% linha e
     70% branch via
     `scripts/model2/check_critical_module_coverage.py` (M2-028.9).
4. Invariantes preservados no pacote:
   `risk_gate=ATIVO`, `circuit_breaker=ATIVO` e
   `decision_id=IDEMPOTENTE`.

**M2-022.5 (Validacao de carga shadow multi-simbolo)**:

1. `core/model2/shadow_load_validation.py` consolida validacao de carga em
   `shadow` para 40 simbolos por janela de 5 minutos, sem envio de ordem real.
2. SLOs avaliados no relatorio consolidado:
   - latencia por razao P95/P50 (`<= 1.5`)
   - sucesso de episodios (`>= 99.5%`)
   - drift de reconciliacao (`<= 0.01%`)
3. Classificacao de erro operacional com correlacao por `decision_id` e
   `execution_id` para rastreabilidade.
4. Isolamento de contexto operacional por modo (`shadow`/`paper`/`live`) em
   fail-safe quando credencial nao aderente ao contexto.
5. Relatorio final publica snapshot de guardrails:
   `risk_gate=ATIVO`, `circuit_breaker=ATIVO`, `decision_id=IDEMPOTENTE`.

Dados coletados por simbolo:

1. Candles capturados (count, timestamp do ultimo)
2. Decisao do modelo (acao, confianca, dados frescos?)
3. Episodio persistido (ID, reward, status)
4. Treino (ultima data, episodios pendentes, progresso)
5. Posicao aberta (side, qty, entry, mark, PnL%, PnL USD)
6. Modo de execucao (shadow/live)
7. Ensemble (metodo, confianca) — (M2-026.10)

## M2-026 (Ensemble Signal Generation — Fase E.10 e E.11)

A geracao de sinais em `daily_pipeline.py` utiliza o `EnsembleSignalGenerator`
para consolidar decisões entre modelos MLP e LSTM:

1. Votação Ponderada: MLP (weight: 0.48) e LSTM (weight: 0.52) por padrão.
2. **Recalibragem Adaptativa (BLID-110 - E.11)**: O `EnsembleRecalibrator`
   ajusta os pesos dinamicamente com base no Win Rate das últimas 48h.
   - Momentum: 0.7 (default) / 0.3 (performance recente).
   - Fallback: Pesos default (0.48, 0.52) se dados < 5 trades.
3. Gate de Confianca: Decisão via ensemble exige `confidence >= 0.6`.
4. Fallback Determinístico (SMC): Ativado automaticamente se a confiança
   for insuficiente ou em erro de carregamento dos modelos.
5. **Trilha Auditável**: Dados de votação, incluindo `applied_weights`,
   são persistidos no `payload_json` do sinal para rastreabilidade
   operacional.

## Fluxo operacional atual

1. Construir estado de mercado.
2. Inferir decisao do modelo.
3. Validar com safety envelope.
4. Executar (ou aguardar) e reconciliar.
5. Persistir episodio e reward.

**M2-022.2 (Auditoria de trigger de treino incremental)**:

1. `core/model2/training_audit.py` centraliza:
   - `ensure_rl_training_audit_schema(conn)`
   - `record_training_audit_event(...)`
   - `evaluate_training_trigger_audit(...)`
   - `detect_training_stale(...)`
2. `core/model2/live_service.py` integra auditoria no caminho de trigger:
   - registra decisao auditavel (`started|blocked`) em `rl_training_audit`
   - bloqueia duplicidade quando treino ja esta em andamento
   - detecta stale de treino > 6h em operacao ativa (fail-safe)
3. Guardrails preservados:
   - `risk_gate` e `circuit_breaker` permanecem ativos
   - idempotencia por `decision_id` inalterada

**M2-025.12 (Regressao de treino incremental em carga moderada)**:

1. `core/model2/training_audit.py` passa a suportar trilha estendida:
   - schema `rl_training_audit` com colunas `decision_id` e
     `concurrency_key` (retrocompativel por `ALTER TABLE` condicional);
   - `record_training_audit_event(...)` persiste os novos campos sem
     quebrar chamadas legadas;
   - `evaluate_training_trigger_audit(...)` aceita `decision_id/timeframe`
     e retorna `idempotency_key` deterministica.
2. `core/model2/live_service.py` estende o trigger de treino incremental:
   - `_trigger_incremental_training_if_needed(..., decision_id,
     concurrency_label)` com fallback seguro para chamadas antigas;
   - propagacao de `decision_id` e `concurrency_key` para auditoria de
     trigger `started|blocked`, mantendo semantica fail-safe.
3. `core/model2/training_load_regression.py` adiciona harness deterministico
   para carga moderada em CI:
   - `run_incremental_training_load_regression(...)` mede tentativas,
     bloqueios e `concurrency_violations`;
   - criterio de estabilidade: `concurrency_violations=0`.
4. Guardrails preservados:
   - sem bypass de `risk_gate`/`circuit_breaker`;
   - idempotencia por `decision_id` mantida no caminho de trigger/auditoria.
5. Fechamento da devolucao PM (valor operacional em `iniciar.bat`):
   - `core/model2/training_audit.py` expoe
     `summarize_training_audit_window(...)` para consolidar janela 24h
     (`started`, `training_already_running`,
     `threshold_not_reached`, `conclusive`);
   - `core/model2/live_service.py` injeta no `SymbolReport` os campos
     `training_audit_started_24h`, `training_audit_running_blocks_24h` e
     `training_audit_conclusive_24h`, refletidos na linha `Treino`;
   - fallback deterministico de `decision_id` no trigger:
     `{symbol}:{timeframe}:{decision_timestamp}` quando metadata nao informar
     `decision_id`.

**M2-016.2 (Diagnostico imediato com artefatos persistidos)**:

1. `scripts/model2/m2_016_2_validation_window.py` suporta fechamento imediato
   por `persisted_artifacts`, sem iniciar nova janela operacional:
   - `collect_persisted_validation_artifacts(...)` localiza `window`,
     `checkpoint` e `report` persistidos;
   - `validate_persisted_artifact_completeness(...)` exige campos de topo e
     KPIs minimos obrigatorios nos artefatos persistidos;
   - `validate_persisted_window_consistency(...)` valida duracao >= 72h e
     consistencia temporal entre `window` e `checkpoint`;
   - `run_finalize_from_persisted_artifacts(...)` finaliza com
     `wait_for_new_window=False`.
2. O fluxo opera em fail-safe e retorna `NO_GO` quando:
   - faltar artefato obrigatorio;
   - `report.window_id` divergir de `window.window_id`;
   - qualquer KPI minimo obrigatorio estiver ausente.
3. KPIs minimos obrigatorios no `report.kpis`:
   - `enhancement_rate_percent`
   - `win_rate_percent`
   - `incident_count`
   - `divergence_proxy`
   - `avg_pipeline_latency_ms`
   - `p95_pipeline_latency_ms`
4. `scripts/model2/phase_d5_real_data_correlation.py` expõe
   `build_persisted_phase_e_metrics_bundle(...)` para consolidar o bundle
   minimo a partir do relatorio persistido.
5. `scripts/model2/train_ppo_lstm.py` expõe
   `validate_m2_016_2_production_gate(...)` para aceitar somente evidencias
   oriundas de `persisted_artifacts` com status `GO|GO_COM_RESTRICOES`.
6. Guardrails preservados:
   - sem bypass de `risk_gate`/`circuit_breaker`;
   - idempotencia por `decision_id` mantida;
   - em ambiguidade operacional, diagnostico bloqueado.

**M2-025.15 (Governanca e auditoria documental do pacote)**:

1. Fechamento documental do pacote M2-025 exige sincronizacao cruzada entre:
   `docs/ARQUITETURA_ALVO.md`, `docs/ADRS.md`, `docs/DIAGRAMAS.md`,
   `docs/MODELAGEM_DE_DADOS.md`, `docs/PRD.md`, `docs/REGRAS_DE_NEGOCIO.md`,
   `docs/RUNBOOK_M2_OPERACAO.md` e trilha em `docs/SYNCHRONIZATION.md`.
2. Objetivo arquitetural: reduzir divergencia entre contrato tecnico e operacao
   observada no `iniciar.bat` por meio de checklist auditavel.
3. Guardrails inviolaveis no fechamento documental:
   `risk_gate=ATIVO`, `circuit_breaker=ATIVO`, `decision_id=IDEMPOTENTE`.
4. Escopo sem impacto de runtime ou schema; mudanca restrita a governanca de
   documentacao e rastreabilidade.
5. Esta secao formaliza a governanca documental do pacote com criterio
   verificavel para auditoria.

## Modos de operacao

1. `backtest`: validacao offline da politica.
2. `shadow`: decisao do modelo sem ordem real.
3. `live`: decisao do modelo com ordem real e guard-rails ativos.

## Banco de dados

1. Banco canonico: `db/modelo2.db`.
2. Schema aplicado por migracoes em `scripts/model2/migrations/`.

## Requisitos nao funcionais

1. Idempotencia em decisao e execucao.
2. Reconciliacao obrigatoria pos-execucao.
3. Protecao obrigatoria para posicao aberta.
4. Auditabilidade ponta a ponta.
5. Fallback seguro para bloqueio, sem estrategia externa.
