# Regras de Negocio - Modelo 2.0

## Objetivo

Definir as regras de negocio vigentes para a arquitetura model-driven.

## Regra mestra

A decisao de trading e do modelo.
Nao existe regra estrategica externa para definir direcao de trade.

## Acoes de negocio permitidas

1. OPEN_LONG
2. OPEN_SHORT
3. HOLD
4. REDUCE
5. CLOSE

## Regras obrigatorias

### RN-001 - Decisao unica do modelo

Toda intencao de entrada, reducao, saida ou espera deve vir da inferencia do
modelo.

### RN-002 - HOLD e decisao valida

Ficar fora do mercado (`HOLD`) e acao de negocio legitima e deve ser tratada
como decisao completa.

### RN-003 - Envelope de seguranca inviolavel

As validacoes abaixo sao obrigatorias em todos os caminhos de live:

1. `risk/risk_gate.py`
2. `risk/circuit_breaker.py`

### RN-004 - Fail-safe

Em qualquer incerteza operacional relevante, a operacao deve ser bloqueada.
Mecanismos de resiliencia operacional (ex: retries) devem abortar imediatamente
(fail-fast) sempre que o `circuit_breaker` ou `risk_gate` estiverem armados.

### RN-005 - Protecao obrigatoria

Toda posicao aberta deve ter protecao ativa apos fill.
Sem protecao, o estado deve ser tratado como risco critico.

### RN-006 - Idempotencia

O sistema nao pode gerar ordem duplicada para a mesma decisao efetiva.

### RN-007 - Reconciliacao obrigatoria

Estados de banco e exchange devem ser reconciliados continuamente.
Divergencias criticas devem gerar falha segura (`FAILED`) e evento
auditavel.
Mismatch entre `signal_side` esperado e lado real da posicao na exchange,
assim como quantidade de posicao nao positiva, sao divergencias criticas
bloqueantes e nao podem seguir para transicao final.

### RN-008 - Auditoria obrigatoria

Toda decisao e toda mudanca de estado relevante devem registrar:

1. timestamp UTC
2. motivo
3. status
4. metadados operacionais

### RN-015 - Contrato unico de erros de execucao (M2-023.1)

Todo evento de bloqueio ou falha em execucao live deve carregar:

1. `reason_code`: codigo canonico do catalogo (`REASON_CODE_CATALOG`)
2. `severity`: nivel de impacto (INFO/MEDIUM/HIGH/CRITICAL)
3. `recommended_action`: acao operacional recomendada
4. `decision_id`: correlacao auditavel com a decisao original
5. `execution_id`: correlacao com a execucao de sinal

Implementacao de referencia: `core/model2/live_execution.py`
(REASON_CODE_SEVERITY, REASON_CODE_ACTION, campos em LiveExecutionGateInput)
e `core/model2/live_service.py`
(emit_execution_error_contract_event, classify_unknown_execution_error).

### RN-016 - Contrato de decisao no order_layer (M2-024.1)

Sinais que carregam `decision_id` ou `decision_origin` no payload sao
sujeitos a validacao estrita antes de avançar para execucao live:

1. `decision_id` presente e maior que zero (correlacao auditavel)
2. `signal_timestamp` valido (nao zero)
3. `payload.decision_origin` preenchido (origem da decisao)

Sinais legados sem esses campos passam pela validacao anterior sem
block (retrocompat). Modo `strict_contract` e opt-in por deteccao.

Implementacao de referencia: `core/model2/order_layer.py`
(bloco strict_contract em `evaluate_signal_for_order_layer`).

### RN-009 - Aprendizado continuo

Toda decisao deve gerar episodio de aprendizado, inclusive `HOLD`.

Implementacao de referencia (M2-020.6):

1. `scripts/model2/persist_training_episodes.py::persist_learning_episode`
   persiste contrato completo de episodio e aplica idempotencia por
   `decision_id`.
2. Em falha de persistencia, retorna bloqueio fail-safe com
   `reason_code='learning_episode_persist_failed'`.

### RN-010 - Reward para operar e nao operar

O reward deve considerar:

1. resultado liquido de execucao
2. custo operacional
3. risco assumido
4. qualidade da decisao de aguardar

Contrato vigente (M2-020.7):

1. `EXECUTED/EXITED`: base em PnL percentual realizado; custo operacional
   aplicado em modo opt-in de `_reward_label(..., apply_operational_cost=True)`.
2. Compatibilidade legado preservada por default em `_reward_label`:
   reward bruto e classificacao `breakeven` nao regressiva.
3. `HOLD_DECISION/BLOCKED`: reward counterfactual deterministico para
   `hold_correct` vs `hold_opportunity_missed`, incluindo branch `NEUTRAL`.
4. Treino PPO (`incremental` e `lstm`): penalidades deterministicas para
   `overtrading`, `risk_gate` adverso, `circuit_breaker` aberto e contexto
   duplicado de `decision_id`.
5. Fail-safe obrigatorio: ausencia de metadata nao quebra dataset nem runtime;
   em ambiguidade, manter comportamento deterministico conservador.

### RN-011 - Retreino automatico governado

Retreino pode ser automatico, mas com governanca:

1. treino fora do runtime live
2. gate de promocao
3. rollback de versao

### RN-012 - Promocao para live

Promocao de modelo exige decisao GO/NO-GO baseada em evidencia.
Sem criterio atendido, resultado obrigatorio: NO_GO.

### RN-013 - Prontidao de alertas operacionais

Quando alertas operacionais estiverem habilitados, o preflight deve validar
credenciais minimas de notificacao antes de liberar live.

Sem credenciais validas, resultado obrigatorio: NO_GO.

### RN-014 - RL Decision per Symbol (M2-019)

Modelos RL individuais por simbolo fornecem decisao de entrada em paralelo
ao scanner SMC.

Regras de integracao:

1. Se modelo nao existe: fallback para decisao deterministico
2. Se confianca < threshold (0.55): passa adiante (conservador)
3. Se acao NEUTRAL com confianca >= threshold: cancela entrada com motivo
4. Se acao alinhada com direcao SMC: enriquece signal_execution
5. Se acao contradiz direcao SMC: cancela com motivo auditavel
6. Todos os casos registram episodio para retreino continuo

Implementacao de referencia:

1. `scripts/model2/train_entry_agents.py` (treino diario por simbolo)
2. `scripts/model2/entry_rl_filter.py`
   (threshold, fallback e cancelamento)
3. `scripts/model2/daily_pipeline.py`
   (ordem: persist -> train -> filter -> order)

### RN-017 - Observabilidade de Circuit Breaker (M2-026.2)

Transições de estado do circuit_breaker
(`CLOSED→OPEN→HALF_OPEN→CLOSED`) devem ser registradas com auditoria
imutável:

1. Cada transição registra: `timestamp_utc`, `from_state`, `to_state`,
   `reason` e `reactivation_time_utc`.
2. Estrutura e append-only: nenhuma alteração retroativa permitida
   (frozen dataclass).
3. Query rápida: estado atual e histórico 24h (DESC por timestamp).
4. Comportamento de decisão do circuit_breaker permanece inviolável.
5. Falha em logging de evento não bloqueia decisão
   (fail-safe com try/except).

### RN-024 - Maquina de estados do Circuit Breaker (BLID-092)

O circuit_breaker opera com tres estados canonicos expostos em `risk/states.py`:

- `CLOSED` (alias `NORMAL`): trading permitido; drawdown dentro do limiar
- `OPEN` (alias `TRANCADO`): trading bloqueado; drawdown excedeu o limiar
- `HALF_OPEN`: tentativa de recuperacao ativa

Transicoes e responsaveis:

1. `CLOSED -> OPEN`: automatica via `trip(reason)` quando
   `drawdown <= threshold`.
2. `OPEN -> HALF_OPEN`: via `attempt_recovery()` ou
   `reset_manual(operator=...)`.
3. `HALF_OPEN -> CLOSED`: automatica via `attempt_recovery()` se o
   drawdown recuperar.
4. `HALF_OPEN -> OPEN`: automatica via `attempt_recovery()` se o
   drawdown continuar critico.

Regras de reset manual com operador:

1. `reset_manual(operator=<nome>)` exige identificacao auditavel do
   operador humano
2. Forca transicao OPEN->HALF_OPEN->CLOSED independente do drawdown atual
3. Registro obrigatorio: `reason=reset_manual:operador=<nome>`,
   `from_state`, `to_state`, `timestamp_utc`
4. Acao irreversivel por codigo — responsabilidade operacional do operador
5. Apenas operador humano autorizado deve invocar reset_manual em ambiente live

### RN-019 - Watchdog de Ciclo M2 (M2-027.1)

O pipeline M2 deve ser monitorado por um watchdog que detecta ausencia de
progressao dentro de janela configuravel (padrao 300s):

1. Ausencia de progressao acima da janela emite `reason_code='cycle_stalled'`
   com timestamp_utc e elapsed_seconds.
2. Fail-safe de interrupcao preserva estado do ciclo sem corromper execucao
   em andamento.
3. risk_gate e circuit_breaker NUNCA sao desabilitados pelo watchdog.
4. Todo acionamento de fail-safe gera `audit_event` com `decision_id`
   e `timestamp_utc`.

### RN-020 - Validacao de Schema Pre-Execucao (M2-027.2)

O schema do modelo2.db deve ser validado antes de cada ciclo live:

1. Tabelas obrigatorias: `schema_migrations`, `technical_signals`,
   `signal_executions`, `signal_execution_events`,
   `signal_execution_snapshots` e `audit_decision_execution`.
2. Divergencia bloqueia ciclo com `reason_code='schema_divergence'` e lista
   de tabelas ausentes.
3. Banco inexistente bloqueia com `reason_code='db_not_found'`.
4. Validacao registrada com timestamp_utc; overhead maximo tolerado: 50ms.
5. No preflight de go-live (M2-024.13), o check 3 tambem valida colunas
   obrigatorias das tabelas criticas e bloqueia em divergencia.
6. O preflight deve validar migracao alvo (ultima versao em
   `scripts/model2/migrations`) presente em `schema_migrations`.
7. No warm-up endurecido de `M2-022.1`, o check 3 deve classificar
   severidade por violacao: `db_not_found` e `missing_tables` => `CRITICAL`;
   `missing_columns`, `missing_migrations` e `foreign_key_violations` =>
   `HIGH`.
8. O check 3 deve expor relatorio auditavel de coverage (`required_tables`,
   `tables_present`, `required_columns_total`, `required_columns_present`,
   `coverage_pct`, `severity_counts`) e evidencia estruturada de
   `foreign_key_check`.
9. Se o `max_severity` do check 3 for `CRITICAL` ou `HIGH`, o warm-up deve
   bloquear o go-live com `summary.reason_code='schema_divergence'`.
10. `candle_freshness`, `train_checkpoint` e `train_episodes` nao pertencem
    ao check 3; esses controles continuam na trilha de consistencia operacional
    `M2-025.14` e usam `reason_code='DATA_CONSISTENCY_FAIL'` quando aplicavel.

### RN-021 - Posicoes Orfas e Saida Segura (M2-027.3)

Posicoes abertas na exchange sem signal_execution IN_PROGRESS correspondente
sao consideradas orfas e devem ser tratadas como risco critico:

1. Deteccao por comparacao symbol entre exchange e signal_executions.
2. Saida de posicao orfa usa SOMENTE `STOP_MARKET` — nunca `MARKET`.
3. Ordem de saida carrega `reason_code='orphan_position'` do catalogo canonico.
4. Audit_event gerado com decision_id sintetico (formato `ORPHAN-<UUID>`) e
   timestamp_utc antes de qualquer ordem ser enviada.
5. risk_gate validado antes de toda ordem de saida orfa.

### RN-022 - Consistencia Transacional CONSUMED->IN_PROGRESS (M2-027.4)

A transicao de estado CONSUMED (order_layer) para IN_PROGRESS (live_execution)
deve ser atomica e reversivel:

1. Se a segunda escrita (IN_PROGRESS) falhar, a primeira (CONSUMED) e revertida.
2. Estado parcial nunca persiste apos revert (`partial_state_persisted=False`).
3. Toda transicao gera audit_event com signal_id, execution_id, decision_id e
   timestamp_utc independente do resultado (committed ou reverted).
4. Compatibilidade obrigatoria com gate de idempotencia M2-024.3.

### RN-023 - Contrato de Promocao GO/NO-GO shadow→paper (M2-028.1)

A promocao do pipeline de shadow para paper trading requer avaliacao objetiva
de criterios via `PromotionEvaluator` em `core/model2/promotion_gate.py`:

1. `win_rate` observado >= `min_win_rate` (padrao: 55%).
2. `episode_count` >= `min_episodes` (padrao: 30 episodios).
3. `max_drawdown_pct` observado <= `max_drawdown_pct` configurado (padrao: 5%).
4. Todos os motivos de bloqueio sao acumulados e reportados
   (nao apenas o primeiro).
5. `PromotionResult` e imutavel (frozen dataclass) com
   `evaluated_at` ISO UTC.
6. `evaluate()` nunca lanca excecao; entrada invalida resulta em
   NO-GO com `reason`.

### RN-024 - Gate de Evidencia Minima para Promocao (M2-020.11)

Toda decisao de promocao deve bloquear quando faltar evidencia operacional
minima de risco, estabilidade ou consistencia:

1. `PromotionEvaluator.evaluate_evidence_gate(...)` em
   `core/model2/promotion_gate.py` e o contrato canonico.
2. `decision_id` valido e obrigatorio para rastreabilidade;
   ausencia retorna `NO_GO`.
3. `risk_evidence_ok`, `stability_evidence_ok` e
   `consistency_evidence_ok` devem estar todos verdadeiros para GO.
4. `evidence_ref` obrigatorio para trilha auditavel; ausencia retorna NO_GO.
5. Resultado imutavel em `PromotionEvidenceResult` inclui `decision`,
   `reasons`, `evidence_sufficient` e `evaluated_at` ISO UTC.
6. `scripts/model2/healthcheck_live_execution.py` deve publicar bloco
   `promotion_gate` no summary para consumo operacional via `iniciar.bat`.

### RN-025 - Timeout por Etapa de Execucao (M2-024.5)

Cada etapa do ciclo de execucao live possui timeout configuravel definido em
`StageTimeoutPolicy` (`core/model2/execution_timeout.py`):

1. Admissao (`order_layer`): padrao 5 000 ms — expirado retorna CANCELLED com
   `reason_code='TIMEOUT_ADMISSION'`.
2. Envio de ordem (`live_service`): padrao 10 000 ms — expirado retorna
   `reason_code='TIMEOUT_SEND'`.
3. Reconciliacao (`live_service`): padrao 30 000 ms — expirado retorna
   `reason_code='TIMEOUT_RECONCILIATION'`.
4. Todos os codes `TIMEOUT_*` possuem `severity=HIGH` e
   `action=bloquear_operacao` no `REASON_CODE_CATALOG`.
5. Expiracao de qualquer etapa emite telemetria via
   `emit_stage_slo_violation_event` com `latency_ms` e `slo_ms`.
6. `StageTimeoutPolicy` e frozen dataclass — imutavel apos instancia.
7. `execution_timeout.py` nao importa `risk_gate` nem `circuit_breaker`;
   guardrails permanecem inviolaveis em todos os caminhos.

### RN-026 - Timezone Canonico de Exibicao (M2-025.2)

Toda exibicao de timestamp ao operador no pipeline M2 deve usar o utilitario
canonico `core/model2/time_utils.py`:

1. Exibicao ao operador: sempre em BRT via `now_brt_str()` ou
   `ts_ms_to_brt_str()` — sufixo obrigatorio `BRT`.
2. Persistencia interna: sempre UTC como `int` (Unix milliseconds).
3. Proibido usar `strftime('%Z')` diretamente — pode renderizar `LMT` ou
   offset numerico em vez de `BRT`.
4. `time_utils.py` e o unico ponto de conversao BRT; nao duplicar logica.

Implementacao de referencia: `core/model2/time_utils.py`
(`now_brt_str`, `ts_ms_to_brt_str`, `posix_to_brt_str`).

### RN-027 - Evidencia Testnet e Contrato Canonico em Shadow (M2-024.12)

No fluxo paper/testnet, a trilha de evidencias operacionais deve permanecer
auditavel e consistente entre preflight e execucao:

1. `go_live_preflight.py` deve persistir `testnet_evidence` no summary final.
2. `testnet_evidence` deve incluir `testnet_credentials` e
   `decision_execution_correlation`.
3. `decision_execution_correlation.required_fields` inclui:
   `decision_id`, `execution_id`, `reason_code`, `severity`,
   `recommended_action`.
4. Em modo `shadow`, `_execute_ready_signal` deve retornar os mesmos campos
   canonicos de correlacao e razao operacional.
5. Guardrails de risco permanecem obrigatorios e inalterados.

### RN-028 - Controles de Resiliencia Contratuais (PKG-PO10-0326)

O pacote de resiliencia operacional deve manter contratos deterministas e
fail-safe para validacao de runtime:

1. Drift pre-admissao bloqueia com `reason_code='position_drift_blocked'`.
2. Degradacao por latencia entra em `mode='degraded'` ao romper SLO.
3. Restart usa replay idempotente sem reenvio de ordem.
4. Priorizacao de eventos respeita ordem CRITICAL > HIGH > WARN.
5. Consulta de auditoria por `decision_id` retorna trilha filtrada.
6. Validacao cruzada contraditoria bloqueia com fail-safe.
7. Retry por categoria nao repete falha permanente.
8. Indicadores de reconciliacao expõem drift medio, p95 confirmacao e taxa.
9. Runbook ausente/invalido retorna `runbook_missing_or_invalid`.
10. Schema incompleto bloqueia com `reason_code='schema_divergence'`.

#### Consolidacao M2-028.10 (RN-023 a RN-028)

Para fechamento do pacote M2-028, as RN-023..RN-028 devem permanecer
coerentes e sem contradicao com backlog, arquitetura e runbook:

1. Promocao GO/NO-GO sempre exige evidencia minima e trilha auditavel
   com `decision_id` (RN-023 e RN-024).
2. Timeout por etapa e timezone canonico continuam obrigatorios para
   rastreabilidade operacional (RN-025 e RN-026).
3. Evidencia testnet e contrato canonico em shadow devem manter os
   mesmos campos de correlacao exigidos no preflight (RN-027).
4. Controles de resiliencia de runtime permanecem fail-safe e
   deterministas em todas as etapas do ciclo (RN-028).
5. Na promocao paper->live, alem das regras acima, validar
   reconciliacao, ausencia de erro critico e aprovacao manual
   registrada.
6. Risco dinamico do pacote exige combinacao de sizing por
   volatilidade e bloqueio por correlacao, sem bypass de guardrails.
7. Qualidade minima do pacote exige benchmark por etapa com alerta
   p95>2x baseline e gate de cobertura critica por modulo.

### RN-018 - Retenção Determinística de Logs (M2-026.5)

Logs devem ser rotacionados e retidos conforme politica centralizada
por severidade:

1. CRITICAL: retido por 365 dias (1 ano) para compliance
2. ERROR: retido por 90 dias
3. WARN: retido por 14 dias
4. INFO: retido por 7 dias
5. Rotação automática por tamanho (100MB) + compressão .gz
6. Config centralizado em config/logging_retention_policy.yaml
7. Scheduler determinístico sem intervenção manual

### RN-029 - Governanca Documental do Pacote M2-024 (M2-024.15)

A conclusao do pacote M2-024 exige sincronizacao documental auditavel
entre backlog, arquitetura e regras de negocio:

1. O runbook unico do pacote M2-024 deve consolidar resposta a incidente,
   criterios de bloqueio e retomada segura.
2. A matriz de guardrails deve explicitar `risk_gate`, `circuit_breaker`
   e idempotencia por `decision_id` como invariantes inviolaveis.
3. Toda alteracao de governanca deve gerar trilha em `docs/SYNCHRONIZATION.md`
   com tag `[SYNC]` e referencia da task.
4. Divergencia entre docs oficiais e implementacao deve resultar em
   tratamento conservador (no-go para expansao operacional).

### RN-030 - Validacao de Carga Shadow e Isolamento de Contexto (M2-022.5)

A validacao de carga para preparo de expansao operacional deve ocorrer em modo
`shadow` com guardrails preservados e criterios objetivos de desempenho:

1. Escopo minimo de carga: 40 simbolos em janela de 5 minutos, sem envio de
   ordens reais.
2. SLO de latencia: razao `P95/P50 <= 1.5` por simbolo na janela avaliada.
3. SLO de episodios: taxa de sucesso de persistencia `>= 99.5%`.
4. SLO de reconciliacao: drift maximo `<= 0.01%`.
5. Classificacao de erro operacional deve manter correlacao por
   `decision_id` e `execution_id`.
6. Isolamento de contexto e obrigatorio: modo `shadow` nao pode operar com
   credencial live; em ambiguidade, bloquear em fail-safe.
7. Relatorio consolidado deve explicitar guardrails ativos:
   `risk_gate=ATIVO`, `circuit_breaker=ATIVO`, `decision_id=IDEMPOTENTE`.

### RN-031 - Correlacao de Ciclo entre Deteccao, Episodio e Treino (M2-025.6)

Para trilha auditavel fim-a-fim no ciclo M2:

1. `cycle_id` deve ser aceito como campo opcional nos contratos de deteccao
   (`DetectorInput` e `DetectionResult`).
2. Quando informado, `cycle_id` deve ser propagado para metadados de deteccao
   e persistido em `opportunities.metadata_json`.
3. A implementacao deve manter compatibilidade com payload legado sem
   `cycle_id`, sem exigencia de migracao de schema.
4. A ausencia de `cycle_id` nao pode quebrar fluxos existentes nem alterar os
   guardrails obrigatorios (`risk_gate`, `circuit_breaker`, idempotencia por
   `decision_id`).

### RN-032 - Retry Seguro de Leitura de Mercado (M2-025.7)

No caminho de leitura de mercado do ciclo live:

1. A leitura deve usar politica imutavel de retry (`RetryPolicy`) com budget
   maximo e backoff deterministico.
2. Falha classificada como permanente deve abortar sem retentativas extras,
   com `reason_code='MARKET_READ_PERMANENT_FAILURE'`.
3. Exaustao de budget/tentativas deve retornar fallback conservador com
   `reason_code='MARKET_READ_RETRY_EXHAUSTED'`.
4. O hook de retry deve estar integrado ao fluxo operacional do
   `live_service` (nao apenas declarado).
5. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-033 - Timeout por Etapa Critica de Dados (M2-025.8)

No pipeline de dados do ciclo M2:

1. Timeout por etapa deve ser configurado via contrato imutavel
   `TimeoutPolicy` em `core/model2/pipeline_timeout.py` com budgets para
   `collect`, `validate` e `consolidate`.
2. Expiracao de etapa deve produzir reason_code canonico da propria etapa:
   `TIMEOUT_COLLECT`, `TIMEOUT_VALIDATE` ou `TIMEOUT_CONSOLIDATE`.
3. Scanner e validator devem usar wrappers de short-circuit por timeout,
   bloqueando processamento tardio e preservando comportamento fail-safe.
4. Toda expiracao deve emitir telemetria auditavel por
   `emit_stage_timeout_telemetry` em `core/model2/observability.py`, com
   `event_type='stage_timeout_expired'`, `elapsed_ms`, `budget_ms`,
   `reason_code` e `cycle_id` quando disponivel.
5. Latencia de timeout deve ser registrada com
   `resultado='timeout_expired'` e mapeamento de etapa operacional
   (`collect->scan`, `validate->validate`, `consolidate->signal`).
6. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-034 - Snapshot Unico por Ciclo (M2-025.10)

Para suporte operacional rapido e investigacao auditavel por ciclo:

1. O sistema deve manter snapshot consolidado por `cycle_id` contendo, no
   minimo, `candle`, `decisao`, `episodio` e `treino`.
2. A persistencia consolidada deve ocorrer em estrutura dedicada
   `cycle_snapshots` com um unico registro por `cycle_id` (upsert).
3. A atualizacao deve integrar o fluxo observability (`record_cycle_snapshot`)
   sem quebrar compatibilidade com ciclos sem `cycle_id`.
4. O consolidado deve preservar trilha de correlacao com execucao/treino
   quando dados estiverem disponiveis no banco.
5. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-035 - Regressao de Treino Incremental em Carga Moderada (M2-025.12)

Para reduzir risco de corrida silenciosa no trigger de treino incremental:

1. Toda decisao de trigger de treino deve ser auditavel com:
   `trigger_reason`, `status`, `decision_id` e `concurrency_key`.
2. O contrato de avaliacao de trigger deve gerar `idempotency_key`
   deterministica por `decision_id` e `timeframe` quando `decision_id`
   estiver disponivel.
3. O trigger de treino em `live_service` deve aceitar `decision_id` e
   `concurrency_label`, mantendo compatibilidade com chamadas legadas.
4. Deve existir regressao automatizavel em CI para carga moderada com
   metrica objetiva `concurrency_violations`; aceite somente com valor `0`.
5. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.
6. O status operacional exibido no `iniciar.bat` deve publicar resumo
   objetivo de auditoria de treino da janela de 24h na linha `Treino`:
   `started`, `running_block` e `conclusivo`.
7. Quando metadata da decisao nao trouxer `decision_id`, o trigger de treino
   deve gerar fallback deterministico
   `{symbol}:{timeframe}:{decision_timestamp}` para manter rastreabilidade.

### RN-036 - Gate Preflight de Consistencia de Dados (M2-025.14)

Antes de qualquer ativacao live, o preflight deve validar consistencia minima
de dados e treino com bloqueio fail-safe em falha:

1. O preflight deve validar frescor de candle via `ohlcv_cache` com limite
   de idade configuravel (`candle_max_age_minutes`).
2. O preflight deve validar existencia de checkpoint de treino no diretorio
   configurado (`checkpoints_dir`).
3. O preflight deve validar baseline minima de passos/episodios de treino
   (`min_train_steps`) a partir dos checkpoints detectados.
4. Falha em qualquer check de consistencia acima deve forcar
   `reason_code='DATA_CONSISTENCY_FAIL'` no summary de preflight.
5. Compatibilidade legada deve ser preservada no contrato do runner:
   aceita `model2_db_path` e alias `db_path`.
6. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-037 - Diagnostico Imediato por Artefatos Persistidos (M2-016.2)

Quando a operacao em producao ja tiver acumulado evidencia suficiente:

1. O fechamento da M2-016.2 pode usar `persisted_artifacts` sem aguardar nova
   janela operacional.
2. O diagnostico imediato deve localizar obrigatoriamente os artefatos
   `window`, `checkpoint` e `report` persistidos.
3. O `report.window_id` deve coincidir com o `window.window_id`; divergencia
   implica bloqueio fail-safe com `NO_GO`.
4. O `report.kpis` deve conter, no minimo:
   `enhancement_rate_percent`, `win_rate_percent`, `incident_count`,
   `divergence_proxy`, `avg_pipeline_latency_ms` e
   `p95_pipeline_latency_ms`.
5. Ausencia de qualquer KPI minimo obrigatorio implica bloqueio fail-safe com
   `NO_GO`.
6. O fechamento imediato deve expor `wait_for_new_window=False` e manter
   rastreabilidade por `decision_id`.
7. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-038 - Contrato Verificavel do Status M2 por Simbolo (BLID-101)

Para eliminar ambiguidade operacional no `iniciar.bat` sem consulta
manual ao DB:

1. O bloco por simbolo deve publicar versao de contrato textual:
   `contract=BLID-101-v1`.
2. Quando houver decisao correlacionada, a linha `Decisao` deve expor:
   `decision_id`, `model_version`, `reason`, `source` e `confianca`.
3. A linha `Frescor` deve expor, no minimo:
   `signal_ts`, `signal_age_ms`, `max_signal_age_ms`,
   `M5_last`, `H1_last`, `H4_last`, `D1_last`.
4. A linha `Features` deve explicitar features-chave de inferencia e
   `snapshot_at` rastreavel.
5. A linha `Persist.` deve correlacionar
   `model_decisions`, `signal_executions` e `training_episodes`
   por simbolo, com ids auditaveis.
6. Em legado sem vinculo por `decision_id`, a saida deve exibir
   `LEGACY_NO_DECISION_LINK` de forma explicita (sem mascarar lacuna).
7. A linha `Candles` deve manter a semantica multi-timeframe vigente e
   explicitar `window_ms` da janela de classificacao fresh/stale.
8. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-039 - Camada Humana no Status Operacional (BLID-102)

Para reduzir ambiguidade no `iniciar.bat` sem perder auditabilidade tecnica:

1. A linha `Episodio` deve publicar `episode_type` e
   `eligibility_for_training`.
2. A linha `Persist.` deve manter trilha tecnica por ids e incluir
   `human_reason` quando houver lacuna de correlacao.
3. Quando ocorrer `LEGACY_NO_DECISION_LINK`, a saida deve traduzir em
   linguagem de operador: registro existente sem vinculo completo
   `decisao -> execucao -> episodio`.
4. A linha `Treino` deve explicitar `eligibility_rule`, `cutoff_ms` e
   `timeframe` aplicado na contagem de pendencias.
5. A linha `Aud24h` deve manter `started`, `running_block`, `conclusivo`
   e adicionar `aud24h_human` para leitura operacional imediata.
6. Em erro de consulta/DB, o status deve permanecer renderizavel
   (fail-safe) com lacuna explicita e sem mascarar causa.
7. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-040 - Governanca Documental do Pacote M2-025 (M2-025.15)

Para o fechamento do pacote M2-025 com auditoria documental:

1. O item M2-025.15 deve sincronizar `ARQUITETURA_ALVO`, `ADRS`,
   `DIAGRAMAS`, `MODELAGEM_DE_DADOS`, `PRD`, `REGRAS_DE_NEGOCIO` e
   `RUNBOOK_M2_OPERACAO`.
2. Toda sincronizacao da M2-025.15 deve registrar trilha em
   `docs/SYNCHRONIZATION.md` com tag `[SYNC]` e referencia explicita do item.
3. O runbook deve incluir checklist de troubleshooting com evidencias
   observaveis em `iniciar.bat`, `logs/startup_log.txt` e `logs/m2_cycle.log`.
4. A governanca documental da M2-025.15 nao pode introduzir promessa de
   comportamento ainda nao implementado no runtime.
5. Guardrails obrigatorios permanecem inviolaveis:
   `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`.

### RN-041 - Alerta de Degradacao do Modelo RL por Simbolo (M2-028.7)

Quando o desempenho do RL degradar por simbolo:

1. O runtime deve combinar media de confianca recente (`model_decisions`)
   com hit rate e regressao entre janelas (`training_episodes`).
2. O threshold deve ser resolvido por simbolo em `config/risk_params.py`,
   com fallback para defaults conservadores.
3. Ao detectar degradacao, o sistema deve emitir alerta com
   `reason_code='MODEL_DEGRADATION'` e incluir simbolo, janela e metricas.
4. O alerta nao pode bloquear a admissao nem bypassar `risk_gate` ou
   `circuit_breaker`; ele apenas registra e notifica.
5. A prioridade de retreino deve ser persistida em `rl_training_audit` com
   rastreabilidade por simbolo/timeframe e, quando houver, `decision_id`.

### RN-042 - Isolamento de Contexto por Modo Operacional (M2-022.6)

Os modos `live`, `shadow` e `paper` devem operar em contexto isolado,
com comportamento fail-safe e sem compartilhamento ambiguo de credenciais,
ordens ou decisoes em execucao.

1. `live` usa somente credencial e telemetria do ambiente real, com
   `risk_gate` e `circuit_breaker` ativos em todo o ciclo.
2. `shadow` replica decisao e reconciliacao sem enviar ordem real; em
   ambiguidade de contexto, deve bloquear e registrar evidencias.
3. `paper` opera em simulacao controlada, sem reutilizar credencial live
   e sem mascarar lacunas de auditoria.
4. Qualquer mistura entre `live`, `shadow` e `paper` viola o isolamento
   operacional e exige bloqueio fail-safe imediato.
5. Toda triagem ou escalada deve preservar rastreabilidade por
   `decision_id`, `reason_code` e modo operacional.

### RN-043 - Isolamento do Fallback Heuristico Nominal (M2-020.13)

A decisao oficial exibida ao operador deve permanecer model-driven e sem
contaminacao do legado heuristico no fluxo nominal.

1. `origin=RL_MODEL` so pode aparecer quando `action_source='rl_action'`
   e `rl_fallback=False`.
2. `signal_side` e `fallback_action` podem existir somente em auditoria ou
   em `baseline_comparative`, nunca como decisao oficial do ciclo.
3. `execution.heuristic_signals` so pode ser ativado por rollback
   explicito, auditavel e fail-safe.
4. Toda divergencia deve registrar `contaminated`, `decision_id` e
   `rl_fallback_reason` no `payload_json` existente, sem schema novo.
5. `risk_gate`, `circuit_breaker` e idempotencia por `decision_id`
   permanecem obrigatorios em qualquer fallback.
