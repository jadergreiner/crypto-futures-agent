# Regras de Negocio - Modelo 2.0

## Objetivo

Definir regras claras e simples para o Modelo 2.0,
reduzindo complexidade na tomada de decisao:

1. Primeiro identificar oportunidade tecnica.
2. Depois acompanhar a tese.
3. So entao validar ou invalidar.

## Escopo da Fase 1

Esta fase NAO executa ordem automaticamente.

Ela deve:

1. Detectar oportunidades.
2. Registrar tese com niveis claros.
3. Monitorar a tese ate um desfecho.

## Escopo da Fase 2

Esta fase adiciona execucao real nativa ao M2.

Ela deve:

1. Consumir apenas `technical_signals` ja admitidos em `CONSUMED`.
2. Criar ciclo de vida dedicado em `signal_executions`.
3. Enviar apenas entrada `MARKET` na V1 live.
4. Proteger toda posicao com `STOP_MARKET` e `TAKE_PROFIT_MARKET`.
5. Reconciliar continuamente ordens, protecoes e saidas.
6. Manter o adaptador legado fora do caminho critico do live.

## Conceitos de negocio

## Oportunidade

Situacao tecnica onde existe chance real de movimento direcional.

## Tese

Hipotese operacional escrita em linguagem de mercado:

1. Direcao esperada (compra ou venda; internamente LONG ou SHORT).
2. Regiao de interesse.
3. Condicao de validacao.
4. Condicao de invalidacao.

## Validada

Quando o mercado confirma a tese conforme regras objetivas.

## Invalidada

Quando o mercado quebra a premissa da tese.

## Expirada

Quando o tempo limite acaba sem validacao nem invalidacao.

## Regras obrigatorias

### RN-001 - Toda oportunidade precisa de tese explicita

Nao pode existir oportunidade sem:

1. Direcao.
2. Zona tecnica.
3. Gatilho de confirmacao.
4. Nivel de invalidacao.

### RN-002 - Nao existe "entrada por ansiedade"

A tese so pode virar sinal se houver confirmacao.

### RN-003 - Toda tese precisa de prazo de validade

Se o mercado ficar lateral sem confirmacao, a tese expira.

### RN-004 - Uma tese deve terminar em um estado final

Estados finais permitidos:

1. VALIDADA
2. INVALIDADA
3. EXPIRADA

### RN-005 - Auditoria obrigatoria

Toda mudanca de estado deve deixar trilha:

1. Quando ocorreu.
2. O que mudou.
3. Qual regra foi usada.

### RN-006 - RL enhancement com fallback deterministica

Quando um modelo PPO treinado estiver disponivel:

1. Aplicar `rl_signal_generation.py` como etapa 9 do pipeline.
2. Atribuir confidence score de RL ao sinal (range [0.0, 1.0]).
3. So gerar sinal se RL confidence >= 0.50 (threshold minimo configurable).
4. Regressar para confidence deterministica 0.70 se PPO indisponivel
   ou quando convergencia < 0.5.
5. Registrar em auditoria qual modelo foi usado (deterministica vs RL) e versao.

### RN-007 - Coleta obrigatoria de taxas de financiamento (Fase D.2)

Toda operacao deve enriquecer episodios com dados de taxa de financiamento:

1. Daemon `daemon_funding_rates.py` deve estar ativo durante pipeline.
2. Minimo 30 segundos de intervalo de coleta por par.
3. Rejeitar episodios sem features de FR quando >= 90% de cobertura atingida.
4. Registrar em auditoria razao de falha de coleta (API down, timeout, etc).
5. Fallback: permitir episodio vazio se coleta falhar < 10% de tempo.

Metricas de sucesso:
>
- >= 1000 registros/dia por par em `funding_rates_api`
- >= 90% of episodios enriquecidos com `fr_sentiment` e `fr_trend`

### RN-008 - Validacao de correlacao com sentimento de FR (Fase D.4)

Sinais devem considerar correlacao empirica entre FR sentiment e resultado:

1. **FR Bearish**: REJEITAR sinal. Taxa de ganho = 0% (alto risco).
2. **FR Neutral**: Usar baseline (37% taxa de ganho, safe).
3. **FR Bullish**: Usar com cautela (25% taxa de ganho, abaixo de neutral).

Regra pratica:

- Se `fr_sentiment == "bearish"`, **bloquear entrada** (RN-008.1).
- Se `fr_sentiment != "bearish"`, prosseguir com RN-006.

Revisao semanal:

- Executar `phase_d4_correlation_analysis.py`
- Comparar Pearson r vs threshold 0.20 para sinalizar drift
- Alertar se `bearish_win_rate > 10%` (mudanca de regra)

### RN-009 - Preparacao de features temporais para LSTM (Fase E.1)

Quando modelo LSTM estiver em desenvolvimento, validar features:

1. **22 scalares obrigatorios** em `training_episodes.features_json`:
   - 5 candle (OHLCV)
   - 7 volatilidade (ATR, Bollinger, MACD)
   - 3 multi-TF (H1, H4, D1)
   - 4 funding rates (rate, avg, sentiment, trend)
   - 3 open interest (OI, sentimento, direcao)

2. **Normalizacao obrigatoria** em [-1, 1] para cada scalar.
3. **Sequencia obrigatoria** de 10 timesteps (rolling window).
4. **Rejeicao**: episodios com NaN ou fora de [-1, 1].
5. **Audit trail**: registrar qual subconjunto de features usado por modelo.

Metricas de sucesso:

- 100% dos episodios tem 20 features normalizadas
- Shape (10, 20) para LSTM, (200,) para fallback MLP
- Zero NaN apos normalizacao

## Estados oficiais e matriz de transicao (M2-001.3)

Fonte canonica de codigo: `core/model2/thesis_state.py`.

Estados oficiais:

1. IDENTIFICADA
2. MONITORANDO
3. VALIDADA
4. INVALIDADA
5. EXPIRADA

Matriz oficial de transicao:

1. `NULL -> IDENTIFICADA` (criacao auditavel da tese)
2. `IDENTIFICADA -> MONITORANDO`
3. `MONITORANDO -> VALIDADA`
4. `MONITORANDO -> INVALIDADA`
5. `MONITORANDO -> EXPIRADA`
6. `VALIDADA` sem saidas
7. `INVALIDADA` sem saidas
8. `EXPIRADA` sem saidas

Regra adicional de auditoria:

1. `from_status = NULL` so e permitido no evento inicial com
   `to_status = IDENTIFICADA`.

## Regra inicial do padrao de Fase 1

### Padrao: Falha em regiao de oferta para venda

Implementacao de referencia: `core/model2/scanner.py`.

Contrato:

1. Lado fixo da tese inicial: `SHORT`.
2. Tipo da tese: `FALHA_REGIAO_VENDA`.
3. Regra canonicamente auditada por `rule_id = M2-002.1-RULE-FAIL-SELL-REGION`.

### Identificacao

1. Selecionar a zona bearish mais recente e valida (`order_block` ou `fvg`).
2. Preco deve tocar/intersectar a zona
   (`high >= zone_low` e `low <= zone_high`).
3. Contexto tecnico nao pode estar em estrutura bullish.

### Validacao

1. Rejeicao visivel: candle que toca a zona e fecha abaixo de `zone_low`.
2. A rejeicao deve ter wick superior dominante.
3. Gatilho da tese: minima da vela de rejeicao (`trigger_price`).
4. Confirmacao do padrao inicial: candle posterior rompe a minima da rejeicao.

### Invalidacao

1. Nivel inicial de invalidacao: topo da zona
   (`invalidation_price = zone_high`).
2. Estrutura muda para leitura altista clara no periodo de decisao.

### Registro inicial da tese (M2-002.2)

1. Detectado o padrao, criar oportunidade em `IDENTIFICADA` com tese completa.
2. Registrar evento inicial auditavel `NULL -> IDENTIFICADA`
   em `opportunity_events`.
3. Aplicar idempotencia por (`symbol`, `timeframe`, `thesis_type`,
   `rejection_candle.timestamp`).

## Regra de monitoramento inicial por vela (M2-003.1)

Implementacao de referencia: `core/model2/repository.py`
e `scripts/model2/track.py`.

1. O rastreador deve consumir oportunidades em `IDENTIFICADA`.
2. Cada oportunidade consumida deve transicionar para `MONITORANDO`.
3. A transicao deve respeitar a matriz oficial de estados
   (`IDENTIFICADA -> MONITORANDO`).
4. A transicao deve gerar evento auditavel em `opportunity_events` com:
   - `event_type = STATUS_TRANSITION`
   - `from_status = IDENTIFICADA`
   - `to_status = MONITORANDO`
   - `rule_id = M2-003.1-RULE-CANDLE-MONITORING`
5. Idempotencia operacional:
   - Se a oportunidade ja estiver `MONITORANDO`, nao criar novo evento.
   - Se a oportunidade estiver em estado final, nao transicionar.

## Regra de validacao da tese (M2-003.2)

Implementacao de referencia: `core/model2/validator.py`,
`core/model2/repository.py` e `scripts/model2/validate.py`.

1. O validador deve consumir oportunidades em `MONITORANDO`.
2. Criterios obrigatorios para validar tese SHORT:
   - Confirmar rejeicao registrada em `metadata_json.rejection_candle`.
   - Confirmar rompimento do gatilho (`low < trigger_price`) em vela posterior
     ao inicio de monitoramento.
3. Se os criterios forem atendidos, transicionar para `VALIDADA`.
4. A transicao deve gerar evento auditavel em `opportunity_events` com:
   - `event_type = STATUS_TRANSITION`
   - `from_status = MONITORANDO`
   - `to_status = VALIDADA`
   - `rule_id = M2-003.2-RULE-THESIS-VALIDATION`
5. Idempotencia operacional:
   - Se ja estiver `VALIDADA`, nao criar novo evento.
   - Se o estado atual nao permitir transicao para `VALIDADA`, nao transicionar.

## Regra de invalidacao e expiracao da tese (M2-003.3)

Implementacao de referencia: `core/model2/resolver.py`,
`core/model2/repository.py` e `scripts/model2/resolve.py`.

1. O resolvedor deve consumir oportunidades em `MONITORANDO`.
2. Criterio de invalidacao (tese SHORT):
   - Identificar vela posterior ao inicio de monitoramento com
     `close > invalidation_price`.
   - Se ocorrer antes (ou sem prazo definido), transicionar para `INVALIDADA`.
3. Criterio de expiracao:
   - Se `now_ms > expires_at` sem invalidacao valida anterior, transicionar para
     `EXPIRADA`.
4. As transicoes devem gerar evento auditavel em `opportunity_events` com:
   - `event_type = STATUS_TRANSITION`
   - `from_status = MONITORANDO`
   - `to_status = INVALIDADA|EXPIRADA`
   - `rule_id =
     M2-003.3-RULE-THESIS-INVALIDATION|M2-003.3-RULE-THESIS-EXPIRATION`
5. Idempotencia operacional:
   - Se ja estiver no estado alvo, nao criar novo evento.
   - Se o estado atual nao permitir a transicao, nao transicionar.

## Regra de painel de oportunidades (M2-004.1)

Implementacao de referencia: `core/model2/observability.py` e
`scripts/model2/dashboard.py`.

1. O painel deve materializar snapshot por execucao com `run_id` e
   `snapshot_timestamp`.
2. O painel deve publicar contagem por todos os estados oficiais:
   `IDENTIFICADA`, `MONITORANDO`, `VALIDADA`, `INVALIDADA`, `EXPIRADA`.
3. O painel deve publicar tempo medio ate resolucao:
   - Geral: `AVG(resolved_at - created_at)` para estados finais.
   - Por estado final: `VALIDADA`, `INVALIDADA`, `EXPIRADA`.
4. Retencao obrigatoria de snapshots: 30 dias.

## Regra de auditoria materializada (M2-004.2)

Implementacao de referencia: `core/model2/observability.py` e
`scripts/model2/audit.py`.

1. Cada snapshot deve registrar transicoes com correlacao por
   `opportunity_id`.
2. O snapshot deve carregar contexto minimo:
   `symbol`, `timeframe`, `from_status`, `to_status`, `rule_id`,
   `event_timestamp` e `payload_json`.
3. O runner deve aceitar filtros operacionais:
   `opportunity_id`, `symbol`, `timeframe`, `start_ts`, `end_ts`, `limit`.
4. Retencao obrigatoria de snapshots: 30 dias.

## Regra de replay historico (M2-005.2)

Implementacao de referencia: `scripts/model2/reprocess.py`.

1. Replay deve rodar por timestamp com pipeline deterministico:
   `scan -> track -> validate -> resolve`.
2. O replay deve usar apenas velas com `timestamp <= replay_timestamp`.
3. O replay deve usar banco isolado (`db/modelo2_replay.db`) por padrao.
4. O uso de `db/modelo2.db` no replay deve ser bloqueado por padrao, com
   override explicito.
5. O resumo deve publicar duas familias oficiais de taxa:
   - Direcional:
     `VALIDADA/(VALIDADA+INVALIDADA)` e
     `INVALIDADA/(VALIDADA+INVALIDADA)`.
   - Sobre resolvidas:
     `VALIDADA/(VALIDADA+INVALIDADA+EXPIRADA)` e
     `INVALIDADA/(VALIDADA+INVALIDADA+EXPIRADA)`.

## Resultado esperado para o negocio

1. Menos sinais impulsivos.
2. Mais clareza no motivo da operacao.
3. Melhor governanca para evolucao do modelo.

## Regra da ponte de sinal (M2-006.1)

Implementacao de referencia: `core/model2/signal_bridge.py`,
`core/model2/repository.py` e `scripts/model2/bridge.py`.

RN-M2-006.1:

1. Toda tese em `VALIDADA` pode gerar no maximo um sinal padrao idempotente.
2. Estados nao elegiveis devem ser rejeitados sem persistencia de sinal.
3. O sinal deve ser persistido em `technical_signals` no banco canonico M2.
4. Campos minimos obrigatorios do sinal:
   - `opportunity_id`, `symbol`, `timeframe`, `signal_side`
   - `entry_type`, `entry_price`, `stop_loss`, `take_profit`
   - `signal_timestamp`, `status`, `rule_id`, `payload_json`
5. Regra canonica auditada: `rule_id = M2-006.1-RULE-STANDARD-SIGNAL`.
6. Status inicial do sinal gerado: `CREATED`.

## Regra de consumo na camada de ordem (M2-007.1)

Implementacao de referencia: `core/model2/order_layer.py`,
`core/model2/repository.py` e `scripts/model2/order_layer.py`.

1. A camada de ordem deve consumir apenas sinais em
   `technical_signals.status = CREATED`.
2. A camada de ordem deve registrar decisao deterministica sem enviar
   ordem real na Fase 1.
3. Decisoes validas devem transicionar o sinal para `CONSUMED`.
4. Decisoes bloqueadas devem transicionar o sinal para `CANCELLED`.
5. Reprocessamento do mesmo sinal deve ser idempotente:
   - `CONSUMED` permanece `CONSUMED`.
   - `CANCELLED` permanece `CANCELLED`.
6. Regra canonica auditada: `rule_id = M2-007.1-RULE-ORDER-LAYER-CONSUMER`.

## Regra do adaptador para legado (M2-007.2)

Implementacao de referencia: `core/model2/signal_adapter.py`,
`core/model2/repository.py` e `scripts/model2/export_signals.py`.

1. O adaptador deve consumir apenas sinais em
   `technical_signals.status = CONSUMED`.
2. O adaptador deve gerar payload legado em `trade_signals` com
   `execution_mode = PENDING`.
3. O adaptador nao deve enviar ordem real na Fase 1.
4. O adaptador deve registrar idempotencia por origem (`m2_technical_signal_id`)
   no `confluence_details` do legado.
5. O adaptador deve marcar exportacao no `payload_json` de `technical_signals`
   para evitar duplicidade.
6. Regra canonica auditada: `rule_id = M2-007.2-RULE-TECHNICAL-TO-TRADE-SIGNAL`.

## Regra de observabilidade do fluxo de sinais (M2-007.3)

Implementacao de referencia: `core/model2/observability.py` e
`scripts/model2/export_dashboard.py`.

1. O snapshot deve publicar contagens por etapa:
   - `created_count`
   - `consumed_count`
   - `cancelled_count`
   - `exported_count`
2. O snapshot deve publicar taxa de exportacao:
   - `export_rate = exported_count / consumed_count`
     (quando `consumed_count > 0`).
3. O snapshot deve publicar erro de exportacao:
   - `export_error_count` a partir da trilha
     `payload_json.adapter_export_trade_signals.last_error`.
4. O snapshot deve publicar latencias medias:
   - `avg_created_to_consumed_ms`
   - `avg_consumed_to_exported_ms`
   - `avg_created_to_exported_ms`
5. Retencao obrigatoria dos snapshots: 30 dias.

## Regra do ciclo de vida de execucao real (M2-009.1)

Implementacao de referencia: `core/model2/live_execution.py`,
`core/model2/repository.py` e
`scripts/model2/migrations/0006_create_signal_executions.sql`.

1. `technical_signals.status` continua sendo apenas trilha de admissao:
   - `CREATED -> CONSUMED`
   - `CREATED -> CANCELLED`
2. O ciclo real da ordem deve existir em entidade separada `signal_executions`.
3. Estados oficiais de `signal_executions`:
   - `READY`
   - `BLOCKED`
   - `ENTRY_SENT`
   - `ENTRY_FILLED`
   - `PROTECTED`
   - `EXITED`
   - `FAILED`
   - `CANCELLED`
4. Matriz oficial de transicao:
   - `NULL -> READY|BLOCKED`
   - `READY -> ENTRY_SENT|FAILED|CANCELLED`
   - `ENTRY_SENT -> ENTRY_FILLED|FAILED|CANCELLED`
   - `ENTRY_FILLED -> PROTECTED|EXITED|FAILED`
   - `PROTECTED -> EXITED|FAILED`
5. Cada transicao do ciclo live deve gerar evento em `signal_execution_events`.
6. Um `technical_signal_id` pode existir no maximo uma vez
   em `signal_executions`.

## Regra do gate live (M2-009.2)

Implementacao de referencia: `core/model2/live_execution.py`,
`core/model2/live_service.py` e `scripts/model2/live_execute.py`.

1. O gate deve avaliar apenas sinais em `technical_signals.status = CONSUMED`.
2. O gate deve bloquear quando qualquer condicao ocorrer:
   - simbolo fora da whitelist live
   - simbolo fora da whitelist autorizada
   - saldo indisponivel/insuficiente
   - limite diario atingido
   - cooldown ativo por simbolo
   - execucao ativa ja existente para o simbolo
   - posicao aberta ja existente na exchange
   - sinal expirado
3. O resultado do gate deve ser persistido como:
   - `READY` quando elegivel
   - `BLOCKED` quando inelegivel
4. O motivo do gate deve ser persistido em `signal_executions.gate_reason`
   e na trilha `payload_json.gate`.

## Regra do executor de entrada MARKET (M2-009.3)

Implementacao de referencia: `core/model2/live_service.py` e
`scripts/model2/live_execute.py`.

1. A V1 live suporta apenas `entry_order_type = MARKET`.
2. Ao enviar a entrada, o sistema deve registrar:
   - `exchange_order_id`
   - `client_order_id`
   - `requested_qty`
3. Quando houver fill confirmado, o sistema deve registrar:
   - `filled_qty`
   - `filled_price`
   - `entry_filled_at`
4. Reprocessar o mesmo `technical_signal` nao pode abrir ordem duplicada.

## Regra de fail-safe de protecao (M2-009.4)

Implementacao de referencia: `core/model2/live_service.py`.

1. Toda execucao `ENTRY_FILLED` deve tentar armar:
   - `STOP_MARKET`
   - `TAKE_PROFIT_MARKET`
2. A posicao so e considerada saudavel quando
   `signal_executions.status = PROTECTED`.
3. Se a protecao nao ficar armada, o agente deve:
   - fechar a posicao a mercado
   - registrar incidente
   - terminar em `FAILED`

## Regra de reconciliacao live (M2-010.1)

Implementacao de referencia: `core/model2/live_service.py` e
`scripts/model2/live_reconcile.py`.

1. O reconciliador deve operar sobre execucoes em:
   - `READY`
   - `ENTRY_SENT`
   - `ENTRY_FILLED`
   - `PROTECTED`
2. Se existir posicao aberta para uma execucao `READY|ENTRY_SENT`,
   o sistema deve recuperar o fill e seguir para protecao.
3. Se uma execucao `PROTECTED` perder a posicao na exchange, ela deve
   terminar em `EXITED`.
4. Se uma execucao `PROTECTED` perder SL/TP, o reconciliador deve tentar
   rearmar a protecao.
5. A reconciliacao deve ser restart-safe e idempotente.

## Regra de observabilidade live (M2-010.2)

Implementacao de referencia: `core/model2/observability.py` e
`scripts/model2/live_dashboard.py`.

1. O dashboard live deve materializar snapshot em `signal_execution_snapshots`.
2. O snapshot deve publicar backlog por status:
   - `ready_count`
   - `blocked_count`
   - `entry_sent_count`
   - `entry_filled_count`
   - `protected_count`
   - `exited_count`
   - `failed_count`
   - `cancelled_count`
3. O snapshot deve publicar riscos operacionais:
   - `unprotected_filled_count`
   - `stale_entry_sent_count`
   - `open_position_mismatches_count`
4. O snapshot deve publicar latencias medias:
   - `avg_signal_to_entry_sent_ms`
   - `avg_entry_sent_to_filled_ms`
   - `avg_filled_to_protected_ms`
5. Retencao obrigatoria dos snapshots: 30 dias.

## Regra de healthcheck live (M2-010.3)

Implementacao de referencia: `scripts/model2/healthcheck_live_execution.py`.

1. O healthcheck deve validar a recencia do ultimo
   `model2_live_dashboard_*.json`.
2. O healthcheck deve alertar quando exceder thresholds de:
   - `unprotected_filled_count`
   - `stale_entry_sent_count`
   - `open_position_mismatches_count`
3. O healthcheck deve retornar exit code operacional:
   - `0` para `status=ok`
   - `1` para `status=alert`

## Regra de hardening de risco (M2-012)

Implementacao de referencia: `config/settings.py`,
`core/model2/repository.py` e `core/model2/live_service.py`.

1. Configuracoes obrigatorias da Fase 2:
   - `M2_EXECUTION_MODE=shadow|live`
   - `M2_LIVE_SYMBOLS`
   - `M2_MAX_DAILY_ENTRIES`
   - `M2_MAX_MARGIN_PER_POSITION_USD`
   - `M2_MAX_SIGNAL_AGE_MINUTES`
   - `M2_SYMBOL_COOLDOWN_MINUTES`
2. O limite diario e o cooldown devem ser apurados no banco canonico M2.
3. Deve existir no maximo uma execucao live ativa por simbolo.
4. O rollout operacional deve seguir a sequencia:
   - `shadow`
   - `live` com subset de simbolos
   - ampliacao progressiva da whitelist

## Fonte unica de verdade de simbolos (M2-012.1)

Implementacao de referencia: `config/settings.py`,
`scripts/model2/daily_pipeline.py`,
`scripts/model2/sync_market_context.py` e `iniciar.bat`.

1. A fonte canonica de simbolos operacionais do M2 e `M2_SYMBOLS`
   (em `config/settings.py`).
2. `M2_SYMBOLS` e derivado de `M2_LIVE_SYMBOLS` no `.env` (prioridade maxima).
3. Se `M2_LIVE_SYMBOLS` estiver vazio, o fallback e
   `config.symbols.ALL_SYMBOLS`.
4. Todos os runners M2 devem usar o mesmo conjunto padrao quando `--symbol`
   nao for informado.
5. Alteracoes em `M2_LIVE_SYMBOLS` devem refletir igualmente em coleta
   (`sync_market_context`), pipeline (`daily_pipeline`) e ciclo live
   (`live_cycle`).

## Estado operacional atual (2026-03-14)

Implementacao operacional vigente no entrypoint Windows:
`iniciar.bat`.

1. O agente possui dois modos no menu:
   - `1` legado (`menu.py`)
   - `2` nova versao M2 (loop continuo)
2. O modo `2` executa em cada ciclo:
   - `daily_pipeline` para gerar/atualizar oportunidades e sinais
   - `live_cycle` para execucao/reconciliacao/dashboard live
   - `healthcheck_live_execution` para gate de saude operacional
3. O loop fica ativo ate interrupcao manual (`Ctrl+C`).
4. Parametros operacionais do loop:
   - `M2_LOOP_SECONDS` (padrao: `300`)
   - `M2_RUN_ONCE=1` para executar apenas um ciclo
5. No estado atual de producao, `M2_EXECUTION_MODE=live`
   com whitelist progressiva configurada por `M2_LIVE_SYMBOLS`.
6. Nao existir `processed_ready` em um ciclo live nao e erro operacional:
   significa ausencia de sinais elegiveis (`technical_signals` em `CONSUMED`).

## Regra de coleta por ciclo (M2-015.2)

Implementacao de referencia: `scripts/model2/sync_market_context.py`
e `iniciar.bat`.

1. No modo `2` do `iniciar.bat`, cada ciclo deve executar coleta de contexto em:
   - `H4`
   - `M5`
2. A coleta deve cobrir o universo canonico `M2_SYMBOLS`.
3. A coleta deve persistir candles em tabelas OHLCV correspondentes.
4. A coleta deve registrar resumo por ciclo em
   `results/model2/runtime/model2_market_context_*.json`.

## Regra de deduplicacao de candles (M2-015.2)

1. E proibido persistir o mesmo candle duas vezes para o mesmo ativo/timeframe.
2. A chave natural de deduplicacao e (`symbol`, `timestamp`).
3. O sync deve descartar candles ja existentes antes da insercao.
4. Resultado esperado no resumo do ciclo:
   - `candles_persisted`
   - `candles_duplicated_skipped`

## Regra de escopo de simbolos (coleta x execucao)

1. `M2_SYMBOLS` governa todo o escopo operacional do M2
   (coleta, pipeline e live).
2. `M2_LIVE_SYMBOLS` no `.env` e a forma de declarar/atualizar `M2_SYMBOLS`.
3. `--symbol` nos scripts atua apenas como filtro ad-hoc do ciclo;
   sem `--symbol`, prevalece `M2_SYMBOLS`.

## Regra de persistencia de episodios por ciclo

Implementacao de referencia: `scripts/model2/persist_training_episodes.py`.

1. Cada ciclo deve materializar episodios em JSONL para treino incremental.
2. Cada ciclo deve persistir episodios em `training_episodes` no banco M2.
3. A extracao incremental deve usar cursor de `updated_at` para evitar
   reprocessamento total.
