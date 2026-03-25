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

### RN-010 - Reward para operar e nao operar

O reward deve considerar:

1. resultado liquido de execucao
2. custo operacional
3. risco assumido
4. qualidade da decisao de aguardar

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

### RN-017 - Observabilidade de Circuit Breaker (M2-026.2)

Transições de estado do circuit_breaker (CLOSED→OPEN→HALF_OPEN→CLOSED) devem
ser registradas com auditoria imutável:

1. Cada transição registra: timestamp_utc, from_state, to_state, reason, reactivation_time_utc
2. Estrutura é append-only: nenhuma alteração retroativa permitida (frozen dataclass)
3. Query rápida: estado atual, histórico 24h (DESC por timestamp)
4. Comportamento de decisão do circuit_breaker permanece inviolável
5. Falha em logging de evento não bloqueia decisão (fail-safe com try/except)

### RN-024 - Maquina de estados do Circuit Breaker (BLID-092)

O circuit_breaker opera com tres estados canonicos expostos em `risk/states.py`:

- `CLOSED` (alias `NORMAL`): trading permitido; drawdown dentro do limiar
- `OPEN` (alias `TRANCADO`): trading bloqueado; drawdown excedeu o limiar
- `HALF_OPEN`: tentativa de recuperacao ativa

Transicoes e responsaveis:

1. `CLOSED -> OPEN`: automatica via `trip(reason)` quando drawdown <= threshold
2. `OPEN -> HALF_OPEN`: via `attempt_recovery()` ou `reset_manual(operator=...)`
3. `HALF_OPEN -> CLOSED`: automatica via `attempt_recovery()` se drawdown recuperado
4. `HALF_OPEN -> OPEN`: automatica via `attempt_recovery()` se drawdown ainda critico

Regras de reset manual com operador:

1. `reset_manual(operator=<nome>)` exige identificacao auditavel do operador humano
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
4. Todo acionamento de fail-safe gera audit_event com decision_id e timestamp_utc.

### RN-020 - Validacao de Schema Pre-Execucao (M2-027.2)

O schema do modelo2.db deve ser validado antes de cada ciclo live:

1. Tabelas obrigatorias: schema_migrations, technical_signals, signal_executions,
   signal_execution_events, signal_execution_snapshots, audit_decision_execution.
2. Divergencia bloqueia ciclo com `reason_code='schema_divergence'` e lista
   de tabelas ausentes.
3. Banco inexistente bloqueia com `reason_code='db_not_found'`.
4. Validacao registrada com timestamp_utc; overhead maximo tolerado: 50ms.

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
4. Todos os motivos de bloqueio sao acumulados e reportados (nao apenas o primeiro).
5. `PromotionResult` e imutavel (frozen dataclass) com `evaluated_at` ISO UTC.
6. `evaluate()` nunca lanca excecao; entrada invalida resulta em NO-GO com reason.

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

### RN-018 - Retenção Determinística de Logs (M2-026.5)

Logs devem ser rotacionados e retidos conforme política centralizada por severidade:

1. CRITICAL: retido por 365 dias (1 ano) para compliance
2. ERROR: retido por 90 dias
3. WARN: retido por 14 dias
4. INFO: retido por 7 dias
5. Rotação automática por tamanho (100MB) + compressão .gz
6. Config centralizado em config/logging_retention_policy.yaml
7. Scheduler determinístico sem intervenção manual
