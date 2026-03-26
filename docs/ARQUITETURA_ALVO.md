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
  `classify_exchange_exception` (transient|permanent), `exchange_retry_with_budget`
  (max 3 tentativas, backoff exponencial) e `ExchangeRetryBudgetError`.
  `live_service.py` expoe `_place_market_entry_with_retry` que aplica o retry
  e retorna None (fail-safe) apos budget esgotado. Guardrails intactos.
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

Resiliencia e fail-safe de pipeline (M2-027):

- `core/model2/cycle_watchdog.py` — modulo transversal de resiliencia com:
  - `CycleWatchdog`: detecta travamento por ausencia de progressao em janela
    configuravel (padrao 300s); aciona fail-safe preservando estado sem
    desabilitar risk_gate ou circuit_breaker.
  - `validate_schema_pre_exec`: valida tabelas obrigatorias no modelo2.db antes
    de cada ciclo; bloqueia com `reason_code='schema_divergence'` em divergencia.
  - `detect_orphan_positions`: compara posicoes abertas na exchange vs
    signal_executions IN_PROGRESS; identifica posicoes sem monitoramento.
  - `build_orphan_exit_order`: constroi ordem de saida orfa com STOP_MARKET
    obrigatorio e audit_event com decision_id sintetico.
  - `execute_atomic_state_transition`: garante transicao CONSUMED->IN_PROGRESS
    atomica com revert logico em falha da segunda escrita.
- `REASON_CODE_CATALOG` expandido com `orphan_position` (M2-027.3).
- `core/model2/resilience_controls.py` (PKG-PO10-0326) — funcoes puras para
  contrato de resiliencia operacional:
  - drift gate pre-admissao (`evaluate_position_drift_gate`)
  - degradacao por latencia (`evaluate_latency_degradation`)
  - restart idempotente (`plan_restart_from_snapshot`)
  - fila priorizada (`prioritize_events`)
  - trilha filtrada por decision_id (`query_risk_gate_audit_by_decision_id`)
  - validacao cruzada fail-safe (`cross_validate_signal_context_position`)
  - retry por categoria (`execute_with_category_retry`)
  - indicadores de reconciliacao (`compute_reconciliation_health_indicators`)
  - validacao de runbook (`validate_contingency_runbook`)
  - validacao de schema por conjunto de tabelas (`validate_schema_tables`)

## Camada 5 - Persistencia e Aprendizado Continuo

Responsavel por:

1. Persistir decisoes e resultados.
2. Persistir episodios completos para treino.
3. Persistir rewards para operar e nao operar.
4. Habilitar retreino automatico governado.

Persistencia de decisao no estado atual:

1. Tabela `model_decisions` para trilha da inferencia.
2. Vinculo opcional `signal_executions.decision_id` para correlacao.

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

**M2-026 (Observabilidade + Auditoria + Conformidade)**:

1. `core/model2/risk_gate_telemetry.py` — Telemetria de bloqueios do risk_gate (M2-026.1)
   - `RiskGateBlockEvent` (frozen dataclass): reason_code, condition, limit_value,
     actual_value, decision_id, timestamp_ms — imutavel e auditavel
   - `RiskGateTelemetryRecorder`: append-only; metodos record(), total_events(),
     all_events(), query_by_reason() com count e percentual por reason_code
   - Hook em `live_service._enforce_guardrails_before_order`: registra bloqueio
     com decision_id quando risk_gate_allows_order=False
   - Telemetria in-memory por ciclo; sem schema DB novo; guardrails intactos

2. `core/model2/circuit_breaker_events.py` — CircuitBreakerEventRecorder (append-only)
   - Registra transições de estado do circuit_breaker: CLOSED→OPEN→HALF_OPEN→CLOSED
   - Query rápida: get_history_24h(), get_current_state(), get_reactivation_time()
   - Singleton pattern com reset para testes

3. `management/logging_retention.py` — LogRotationManager + RetentionPolicy
   - Rotação automática por tamanho (100MB) e tempo
   - Retenção por severidade: CRITICAL 365d, ERROR 90d, WARN 14d, INFO 7d
   - Config centralizado em config/logging_retention_policy.yaml
   - Compressão .gz de arquivos antigos

**M2-028.1 (Gate de Promocao GO/NO-GO shadow→paper)**:

1. `core/model2/promotion_gate.py` — contrato de avaliacao de promocao
   - `PromotionConfig`: thresholds configuráveis (min_win_rate, min_episodes, max_drawdown_pct)
   - `PromotionResult` (frozen dataclass): decisao GO/NO-GO, reasons,
     evaluated_at ISO UTC
   - `PromotionEvaluator`: avalia criterios de forma fail-safe (nunca lanca excecao)
   - Defaults conservadores: win_rate >= 55%, episodes >= 30, drawdown <= 5%

Dados coletados por simbolo:

1. Candles capturados (count, timestamp do ultimo)
2. Decisao do modelo (acao, confianca, dados frescos?)
3. Episodio persistido (ID, reward, status)
4. Treino (ultima data, episodios pendentes, progresso)
5. Posicao aberta (side, qty, entry, mark, PnL%, PnL USD)
6. Modo de execucao (shadow/live)

## Fluxo operacional atual

1. Construir estado de mercado.
2. Inferir decisao do modelo.
3. Validar com safety envelope.
4. Executar (ou aguardar) e reconciliar.
5. Persistir episodio e reward.

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
