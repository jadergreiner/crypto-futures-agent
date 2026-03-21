# Backlog - Modelo 2.0

Somente funcionalidades e tarefas do Modelo 2.0.

## Prioridade P0 (iniciar agora)

## INICIATIVA M2-001 - Fundacao da tese

### TAREFA M2-001.1 - Criar esquema de oportunidades

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Criar tabela `opportunities`. [OK]
2. Criar indices basicos. [OK]
3. Criar migracao versionada. [OK]

Evidencias:

1. Migracao SQL: `scripts/model2/migrations/0001_create_opportunities.sql`.
2. Runner de migracao: `scripts/model2/migrate.py`.
3. Banco canonico M2: `db/modelo2.db`.
4. Output operacional: `results/model2/runtime/model2_migrate_*.json`.

### TAREFA M2-001.2 - Criar esquema de eventos

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Criar tabela `opportunity_events`. [OK]
2. Garantir chave estrangeira e indices. [OK]

Evidencias:

1. Migracao SQL: `scripts/model2/migrations/0002_create_opportunity_events.sql`.
2. Cobertura de testes: `tests/test_model2_migrate.py`.
3. Execucao de migracoes M2: `scripts/model2/migrate.py`.

### TAREFA M2-001.3 - Definir enumeracoes de estado

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Estados oficiais. [OK]
2. Matriz de transicao valida. [OK]

Evidencias:

1. Contrato canonico: `core/model2/thesis_state.py`.
2. Pacote de dominio M2: `core/model2/__init__.py`.
3. Testes do contrato: `tests/test_model2_state_contract.py`.
4. Migracoes alinhadas ao contrato: `tests/test_model2_migrate.py`.
5. Documentacao sincronizada: `docs/REGRAS_DE_NEGOCIO.md`,
   `docs/MODELAGEM_DE_DADOS.md` e `docs/ADRS.md`.

## INICIATIVA M2-002 - Scanner de Oportunidades

### TAREFA M2-002.1 - Implementar detector do padrao inicial

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Padrao "falha em regiao para venda". [OK]
2. Registro `IDENTIFICADA`. [OK]

Evidencias:

1. Detector canonico: `core/model2/scanner.py`.
2. Runner operacional do scanner: `scripts/model2/scan.py`.
3. Testes unitarios do detector: `tests/test_model2_scanner_detector.py`.

### TAREFA M2-002.2 - Persistir tese inicial

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Gravar niveis de zona. [OK]
2. Gravar gatilho e invalidacao. [OK]
3. Gravar metadados da analise tecnica. [OK]

Evidencias:

1. Repositorio transacional M2: `core/model2/repository.py`.
2. Persistencia inicial + evento `NULL -> IDENTIFICADA`:
   `core/model2/repository.py`.
3. Cobertura de idempotencia e atomicidade:
   `tests/test_model2_thesis_repository.py`.

## INICIATIVA M2-003 - Rastreador de Tese

### TAREFA M2-003.1 - Monitoramento por vela

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Consumir oportunidades abertas. [OK]
2. Atualizar para `MONITORANDO`. [OK]

Evidencias:

1. Transicao de estado no repositorio M2: `core/model2/repository.py`.
2. Runner do rastreador por vela: `scripts/model2/track.py`.
3. Testes de transicao e idempotencia: `tests/test_model2_tracker.py`.

### TAREFA M2-003.2 - Regras de validacao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Confirmar rejeicao. [OK]
2. Confirmar rompimento do gatilho. [OK]
3. Transicionar para `VALIDADA`. [OK]

Evidencias:

1. Validador deterministico: `core/model2/validator.py`.
2. Transicao `MONITORANDO -> VALIDADA`: `core/model2/repository.py`.
3. Runner operacional de validacao: `scripts/model2/validate.py`.
4. Testes de regra e fluxo: `tests/test_model2_validator.py` e
   `tests/test_model2_validation_flow.py`.

### TAREFA M2-003.3 - Regras de invalidacao/expiracao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Invalidar por quebra da premissa. [OK]
2. Expirar por tempo limite. [OK]

Evidencias:

1. Resolvedor deterministico: `core/model2/resolver.py`.
2. Transicoes `MONITORANDO -> INVALIDADA|EXPIRADA`: `core/model2/repository.py`.
3. Runner operacional de resolucao: `scripts/model2/resolve.py`.
4. Testes de regra e fluxo: `tests/test_model2_resolver.py` e
   `tests/test_model2_resolution_flow.py`.

## Prioridade P1 (apos P0)

## INICIATIVA M2-004 - Observabilidade

### TAREFA M2-004.1 - Painel de oportunidades

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Contagem por estado. [OK]
2. Tempo medio ate resolucao. [OK]

Evidencias:

1. Migracao de materializacao:
   `scripts/model2/migrations/0003_create_observability_snapshots.sql`.
2. Servico canonico de observabilidade: `core/model2/observability.py`.
3. Runner operacional do painel: `scripts/model2/dashboard.py`.
4. Cobertura de metricas e persistencia: `tests/test_model2_observability.py`.

### TAREFA M2-004.2 - Registros de auditoria

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Registro por transicao. [OK]
2. Correlacao por `opportunity_id`. [OK]

Evidencias:

1. Tabela materializada de auditoria:
   `scripts/model2/migrations/0003_create_observability_snapshots.sql`.
2. Servico de refresh e filtros de auditoria: `core/model2/observability.py`.
3. Runner operacional de auditoria: `scripts/model2/audit.py`.
4. Cobertura de filtros e retencao: `tests/test_model2_observability.py`.

## INICIATIVA M2-005 - Qualidade

### TAREFA M2-005.1 - Testes unitarios de transicao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Casos validos e invalidos de mudanca de estado. [OK]

Evidencias:

1. Suite unitaria dedicada de transicoes:
   `tests/test_model2_transition_suite.py`.
2. Cobertura de caminhos validos/invalidos/idempotencia/not_found e auditoria
   por evento: `tests/test_model2_transition_suite.py`.
3. Checagem automatizada de sincronismo documental:
   `tests/test_docs_model2_sync.py` e `.github/workflows/docs-validate.yml`.

### TAREFA M2-005.2 - Reprocessamento historico

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Reprocessar velas passadas. [OK]
2. Medir taxa de validacao vs invalidacao. [OK]

Evidencias:

1. Runner de replay historico em DB isolado: `scripts/model2/reprocess.py`.
2. Bloqueio por padrao do DB operacional e suporte a janela temporal:
   `scripts/model2/reprocess.py`.
3. Taxas direcionais e sobre resolvidas no resumo operacional:
   `scripts/model2/reprocess.py`.
4. Cobertura de replay VALIDADA/INVALIDADA/EXPIRADA e taxas:
   `tests/test_model2_reprocess.py`.

## Prioridade P2 (fase posterior)

## INICIATIVA M2-006 - Ponte de Sinal

### TAREFA M2-006.1 - Gerar sinal padrao apos validacao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Contrato canonico de sinal padrao e regra M2-006.1. [OK]
2. Persistencia dedicada em `technical_signals` com migracao versionada. [OK]
3. Runner operacional da ponte de sinal com dry-run e resumo de execucao. [OK]
4. Testes unitarios, de repositorio e fluxo integrado da ponte. [OK]

Subtarefas rastreaveis:

1. M2-006.1.1 - Contrato de sinal padrao. [OK]
2. M2-006.1.2 - Persistencia e migracao. [OK]
3. M2-006.1.3 - Runner operacional. [OK]
4. M2-006.1.4 - Testes e evidencias. [OK]

Evidencias:

1. Dominio da ponte: `core/model2/signal_bridge.py`.
2. Persistencia no repositorio M2: `core/model2/repository.py`.
3. Migracao de schema M2:
   `scripts/model2/migrations/0004_create_technical_signals.sql`.
4. Runner operacional da ponte: `scripts/model2/bridge.py`.
5. Documentacao de script: `scripts/model2/README.md`.
6. Testes de dominio: `tests/test_model2_signal_bridge.py`.
7. Testes de fluxo integrado: `tests/test_model2_bridge_flow.py`.
8. Cobertura de migracao/repositorio: `tests/test_model2_migrate.py` e
   `tests/test_model2_thesis_repository.py`.

## INICIATIVA M2-007 - Integracao com execucao

### TAREFA M2-007.1 - Consumir sinal validado na camada de ordem

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Consumir sinais `CREATED` de `technical_signals` na camada de ordem M2. [OK]
2. Registrar decisao sem envio de ordem real na Fase 1. [OK]
3. Atualizar status para `CONSUMED` ou `CANCELLED` com idempotencia. [OK]

Evidencias:

1. Contrato de decisao da camada de ordem: `core/model2/order_layer.py`.
2. Persistencia de consumo idempotente: `core/model2/repository.py`.
3. Runner operacional da camada de ordem: `scripts/model2/order_layer.py`.
4. Documentacao operacional: `scripts/model2/README.md`.
5. Testes unitarios: `tests/test_model2_order_layer.py`.
6. Testes de fluxo integrado: `tests/test_model2_order_layer_flow.py`.
7. Cobertura de repositorio: `tests/test_model2_thesis_repository.py`.

### TAREFA M2-007.2 - Adaptar technical_signals para trade_signals legado

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Adaptador deterministico `technical_signals -> trade_signals`. [OK]
2. Dual-write controlado com idempotencia por `technical_signal_id`. [OK]
3. Sem envio de ordem real (apenas persistencia no legado). [OK]

Evidencias:

1. Contrato do adaptador: `core/model2/signal_adapter.py`.
2. Marcacao de export no repositorio M2: `core/model2/repository.py`.
3. Runner operacional de exportacao: `scripts/model2/export_signals.py`.
4. Documentacao operacional: `scripts/model2/README.md`.
5. Testes de unidade do adaptador: `tests/test_model2_signal_adapter.py`.
6. Testes de fluxo E2E do adaptador: `tests/test_model2_export_signals_flow.py`.

### TAREFA M2-007.3 - Observabilidade do fluxo de sinais

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Snapshot materializado do fluxo `CREATED -> CONSUMED -> exportado`. [OK]
2. Metricas de contagem, taxa de exportacao, erros e latencia por etapa. [OK]
3. Runner operacional dedicado para dashboard do fluxo. [OK]

Evidencias:

1. Migracao de snapshot:
   `scripts/model2/migrations/0005_create_signal_flow_snapshots.sql`.
2. Servico canonico de observabilidade estendido:
   `core/model2/observability.py`.
3. Runner operacional: `scripts/model2/export_dashboard.py`.
4. Cobertura de metricas e runner:
   `tests/test_model2_signal_flow_observability.py`.

## INICIATIVA M2-008 - Orquestracao operacional

### TAREFA M2-008.1 - Orquestrar pipeline diario ponta a ponta

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Runner unico para encadear etapas operacionais M2 em sequencia fixa. [OK]
2. Controle de dry-run, fail-fast e continue-on-error por execucao. [OK]
3. Resumo operacional unico com rastreio de erros por etapa. [OK]

Evidencias:

1. Orquestrador diario: `scripts/model2/daily_pipeline.py`.
2. Documentacao operacional: `scripts/model2/README.md`.
3. Cobertura unitaria do orquestrador: `tests/test_model2_daily_pipeline.py`.

### TAREFA M2-008.2 - Operacionalizar execucao agendada

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Runner de agendamento diario com horario fixo e timezone configuravel. [OK]
2. Controle de concorrencia por lock de arquivo (single-run). [OK]
3. Politica de retry controlada para falhas de execucao do pipeline. [OK]

Evidencias:

1. Scheduler operacional M2: `scripts/model2/schedule_daily_pipeline.py`.
2. Documentacao de uso operacional: `scripts/model2/README.md`.
3. Cobertura unitaria de lock/retry: `tests/test_model2_daily_scheduler.py`.

### TAREFA M2-008.3 - Hardening operacional (monitoramento e alertas)

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Healthcheck automatizado da execucao agendada com alerta por exit code. [OK]
2. Validacao de recencia e status (`status=ok`) do ultimo schedule. [OK]
3. Smoke test de operacao `--once --dry-run` em CI. [OK]
4. Runbook operacional com resposta a incidentes. [OK]

Evidencias:

1. Healthcheck operacional: `scripts/model2/healthcheck_daily_schedule.py`.
2. Workflow CI de smoke operacional: `.github/workflows/model2-smoke.yml`.
3. Testes de healthcheck: `tests/test_model2_daily_healthcheck.py`.
4. Runbook de operacao/incidentes: `docs/RUNBOOK_M2_OPERACAO.md`.
5. Documentacao de comandos: `scripts/model2/README.md`.

## Prioridade P0 (Fase 2 - execucao real nativa)

## INICIATIVA M2-009 - Execucao real nativa

### TAREFA M2-009.1 - Modelar ciclo de vida de execucao

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Criar entidade dedicada `signal_executions` para o ciclo real do M2. [OK]
2. Criar trilha de eventos `signal_execution_events` com auditoria
   por transicao. [OK]
3. Manter `technical_signals.status` apenas como trilha de admissao
   (`CREATED -> CONSUMED|CANCELLED`). [OK]

Evidencias:

1. Contrato canonico de estados live: `core/model2/live_execution.py`.
2. Persistencia transacional do ciclo live: `core/model2/repository.py`.
3. Migracao de schema:
   `scripts/model2/migrations/0006_create_signal_executions.sql`.
4. Cobertura de migracao: `tests/test_model2_migrate.py`.

### TAREFA M2-009.2 - Gate live do M2

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Admitir apenas `technical_signals` em `CONSUMED`. [OK]
2. Bloquear por simbolo, saldo, cooldown, limite diario, posicao aberta
   e sinal vencido. [OK]
3. Materializar execucao como `READY` ou `BLOCKED` com motivo auditavel. [OK]

Evidencias:

1. Regra deterministica do gate live: `core/model2/live_execution.py`.
2. Orquestracao de staging live: `core/model2/live_service.py`.
3. Runner operacional de entrada: `scripts/model2/live_execute.py`.
4. Testes de aceite do gate e staging: `tests/test_model2_live_execution.py`.

### TAREFA M2-009.3 - Executor de entrada MARKET

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Enviar ordem de entrada `MARKET` para o mercado real. [OK]
2. Persistir `exchange_order_id`, `client_order_id`, `filled_qty`
   e `filled_price`. [OK]
3. Garantir idempotencia por `technical_signal_id` sem ordem duplicada. [OK]

#### INCIDENTE - Discrepância margem/exposição (2026-03-21)

Resumo: durante execução live para `execution_id=15` foi enviada ordem com
`margin_usd=10` e `leverage=10`, resultando em exposição de **100 USD**.
O comportamento do cálculo está correto segundo a fórmula atual
(`exposure = margin_usd * leverage`), porém o esperado era **1 USD** de
margin (exposição alvo 10 USD). A discrepância pode ter origem em: (a) valor
de `max_margin_per_position_usd` configurado em `EXECUTION_CONFIG`; (b) entrada
manual incorreta de parâmetro; (c) falha de interface do operador.

Evidências:

- Log de evidência salvo: `logs/order_event_15_1774066144.json`
- Evento de reconciliação inserido em `signal_execution_events` para
   `execution_id=15` com tipo `RECONCILIATION` e payload relevante.
- Evento adicional `DISCREPANCY` inserido em `signal_execution_events` com
   detalhes (`expected_margin_usd=1.0`, `used_margin_usd=10.0`,
   `used_exposure_usd=100.0`).

Ações recomendadas:

1. Revisar `config/execution_config.py` e variável `max_margin_per_position_usd`.
2. Validar a origem do parâmetro que iniciou a execução (manual vs gate).
3. Se necessário, fechar/reduzir a posição (opção manual).
4. Registrar lição em `docs/LESSONS_LEARNED.md` se for problema de processo.

Evidencias:

1. Abstracao de exchange live: `core/model2/live_exchange.py`.
2. Servico de execucao real/shadow: `core/model2/live_service.py`.
3. Runner operacional live: `scripts/model2/live_execute.py`.
4. Testes de happy path e idempotencia: `tests/test_model2_live_execution.py`.

### TAREFA M2-009.4 - Fail-safe de protecao

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Criar protecoes `STOP_MARKET` e `TAKE_PROFIT_MARKET` apos fill. [OK]
2. Fechar a posicao imediatamente quando a protecao nao fica armada. [OK]
3. Encerrar a execucao em `FAILED` com incidente auditavel. [OK]

Evidencias:

1. Fail-safe de protecao no servico live: `core/model2/live_service.py`.
2. Runner operacional que dispara a protecao: `scripts/model2/live_execute.py`.
3. Testes de falha de protecao e fechamento emergencial:
   `tests/test_model2_live_execution.py`.

## INICIATIVA M2-010 - Reconciliacao e observabilidade live

### TAREFA M2-010.1 - Reconciliador de ordens e posicoes

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Recuperar fills apos restart a partir de ordem enviada/posicao aberta. [OK]
2. Detectar fechamento manual/externo da posicao e encerrar em `EXITED`. [OK]
3. Recriar protecao ausente quando a posicao ainda existir. [OK]

Evidencias:

1. Servico de reconciliacao restart-safe: `core/model2/live_service.py`.
2. Runner operacional dedicado: `scripts/model2/live_reconcile.py`.
3. Testes de reconciliacao e manual exit: `tests/test_model2_live_execution.py`.

### TAREFA M2-010.2 - Dashboard live

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Publicar backlog por status do ciclo live. [OK]
2. Publicar latencias ate `ENTRY_SENT`, `ENTRY_FILLED` e `PROTECTED`. [OK]
3. Sinalizar posicoes sem protecao, `ENTRY_SENT` stale e falhas. [OK]

Evidencias:

1. Snapshot materializado live:
   `scripts/model2/migrations/0007_create_signal_execution_snapshots.sql`.
2. Servico de observabilidade live: `core/model2/observability.py`.
3. Runner operacional do dashboard: `scripts/model2/live_dashboard.py`.
4. Testes de metricas e runner: `tests/test_model2_live_observability.py`.

### TAREFA M2-010.3 - Healthcheck e runbook

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Alertar quando houver dashboard stale, posicao sem protecao ou divergencia
   acima do limite. [OK]
2. Padronizar resposta a incidentes do live M2. [OK]
3. Produzir artefato operacional versionado por execucao. [OK]

Evidencias:

1. Healthcheck do live: `scripts/model2/healthcheck_live_execution.py`.
2. Runbook operacional do M2: `docs/RUNBOOK_M2_OPERACAO.md`.
3. Testes do healthcheck live: `tests/test_model2_live_healthcheck.py`.

## INICIATIVA M2-011 - Orquestracao operacional live

### TAREFA M2-011.1 - Runner live_execute

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Publicar runner de staging e entrada live/shadow. [OK]
2. Validar schema antes da execucao. [OK]
3. Emitir resumo operacional em `results/model2/runtime/`. [OK]

Evidencias:

1. Runner operacional: `scripts/model2/live_execute.py`.
2. Documentacao de uso: `scripts/model2/README.md`.
3. Testes de runner e persistencia: `tests/test_model2_live_execution.py`.

### TAREFA M2-011.2 - Runner live_reconcile

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Publicar runner de reconciliacao continua. [OK]
2. Cobrir `READY`, `ENTRY_SENT`, `ENTRY_FILLED` e `PROTECTED`. [OK]
3. Emitir resumo operacional em `results/model2/runtime/`. [OK]

Evidencias:

1. Runner operacional: `scripts/model2/live_reconcile.py`.
2. Documentacao de uso: `scripts/model2/README.md`.
3. Testes de runner e reconciliacao: `tests/test_model2_live_execution.py`.

### TAREFA M2-011.3 - Runner live_cycle

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Encadear `live_execute -> live_reconcile -> live_dashboard`. [OK]
2. Separar o caminho critico live do `export_signals -> trade_signals`
   legado. [OK]
3. Publicar resumo unico do ciclo live. [OK]

Evidencias:

1. Orquestrador do ciclo live: `scripts/model2/live_cycle.py`.
2. Runners independentes do ciclo live: `scripts/model2/live_execute.py`
   e `scripts/model2/live_reconcile.py`.
3. Documentacao operacional: `scripts/model2/README.md`.

## INICIATIVA M2-012 - Hardening de risco

### TAREFA M2-012.1 - Contadores persistidos no M2

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Calcular limite diario e cooldown a partir do banco canonico M2. [OK]
2. Nao depender do contador em memoria do executor legado. [OK]
3. Rastrear contagem por `execution_mode` e simbolo. [OK]

Evidencias:

1. Consultas persistidas de risco: `core/model2/repository.py`.
2. Gate live consumindo contadores M2: `core/model2/live_service.py`.
3. Testes de aceite do gate e idempotencia:
   `tests/test_model2_live_execution.py`.

### TAREFA M2-012.2 - Configuracao explicita de ativacao

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Expor `M2_EXECUTION_MODE=shadow|live`. [OK]
2. Expor `M2_LIVE_SYMBOLS`, `M2_MAX_DAILY_ENTRIES`
   e `M2_MAX_MARGIN_PER_POSITION_USD`. [OK]
3. Expor idade maxima de sinal e cooldown por simbolo para operacao
   progressiva. [OK]

Evidencias:

1. Configuracoes do ambiente: `config/settings.py`.
2. Exemplo de ambiente: `.env.example`.
3. Runners consumindo configuracao: `scripts/model2/live_execute.py`
   e `scripts/model2/live_reconcile.py`.

### TAREFA M2-012.3 - Exclusividade por simbolo

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Garantir no maximo uma execucao ativa live por simbolo. [OK]
2. Bloquear quando existir posicao aberta no ativo. [OK]
3. Persistir motivo do bloqueio em `signal_executions.gate_reason`. [OK]

Evidencias:

1. Regra de bloqueio por simbolo: `core/model2/live_execution.py`.
2. Consultas de exclusividade no repositorio: `core/model2/repository.py`.
3. Testes de gate/blocking: `tests/test_model2_live_execution.py`.

## INICIATIVA M2-013 - Documentacao canonica da Fase 2

### TAREFA M2-013.1 - Sincronizar arquitetura, modelagem e regras de negocio

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Atualizar backlog, arquitetura alvo, modelagem de dados e regras
   de negocio. [OK]
2. Atualizar ADRs, diagramas e runbook operacional. [OK]
3. Atualizar README operacional dos scripts do M2. [OK]

Evidencias:

1. Backlog canonico: `docs/BACKLOG.md`.
2. Arquitetura alvo: `docs/ARQUITETURA_ALVO.md`.
3. Regras de negocio: `docs/REGRAS_DE_NEGOCIO.md`.
4. Modelagem de dados: `docs/MODELAGEM_DE_DADOS.md`.
5. ADRs e diagramas: `docs/ADRS.md` e `docs/DIAGRAMAS.md`.
6. Runbook e comandos: `docs/RUNBOOK_M2_OPERACAO.md`
   e `scripts/model2/README.md`.
7. Suite de sincronismo documental: `tests/test_docs_model2_sync.py`.

## INICIATIVA M2-014 - Automacao de go-live da Fase 2

### TAREFA M2-014.1 - Runner unico de preflight para go-live

Status: CONCLUIDA (2026-03-13)
Entrega:

1. Publicar runner unico `go_live_preflight.py` cobrindo os 10 itens
   do checklist. [OK]
2. Aplicar auto-fix por padrao no Windows com opcao `--no-apply`. [OK]
3. Emitir resumo operacional versionado em `results/model2/runtime/`. [OK]
4. Cobrir cenarios de sucesso/falha/continue-on-error em testes. [OK]
5. Atualizar README e runbook para o fluxo oficial de preflight. [OK]

Evidencias:

1. Runner operacional de preflight: `scripts/model2/go_live_preflight.py`.
2. Cobertura unitaria dedicada: `tests/test_model2_go_live_preflight.py`.
3. Validacao de sincronismo documental: `tests/test_docs_model2_sync.py`.
4. Documentacao de comandos: `scripts/model2/README.md`.
5. Runbook operacional atualizado: `docs/RUNBOOK_M2_OPERACAO.md`.

## INICIATIVA M2-015 - Unificacao operacional do agente

### TAREFA M2-015.1 - Consolidar entrada operacional em `iniciar.bat`

Status: CONCLUIDA (2026-03-14)
Entrega:

1. Manter um unico agente de inicializacao no Windows (`iniciar.bat`). [OK]
2. Preservar acesso ao fluxo legado e ao fluxo M2 no mesmo entrypoint. [OK]
3. Executar ciclo operacional M2 em loop continuo com healthcheck
   por ciclo. [OK]
4. Permitir modo de diagnostico `M2_RUN_ONCE=1` e intervalo configuravel
   via `M2_LOOP_SECONDS`. [OK]

Evidencias:

1. Entry point unificado: `iniciar.bat`.
2. Orquestrador do pipeline de sinais: `scripts/model2/daily_pipeline.py`.
3. Orquestrador do ciclo live: `scripts/model2/live_cycle.py`.
4. Healthcheck live: `scripts/model2/healthcheck_live_execution.py`.
5. Regras operacionais atualizadas: `docs/REGRAS_DE_NEGOCIO.md`.

### TAREFA M2-015.2 - Coleta por ciclo e deduplicacao de candles

Status: CONCLUIDA (2026-03-14)
Entrega:

1. Coleta `H4` e `M5` por ciclo no fluxo `iniciar.bat` opcao `2`. [OK]
2. Coleta aplicada para todo `M2_SYMBOLS` (derivado de `M2_LIVE_SYMBOLS`,
   com fallback para `ALL_SYMBOLS`). [OK]
3. Deduplicacao de candles por (`symbol`, `timestamp`) no sync de contexto. [OK]
4. Persistencia de episodios por ciclo para treino em JSONL e banco M2. [OK]

Evidencias:

1. Runner de coleta: `scripts/model2/sync_market_context.py`.
2. Runner de episodios: `scripts/model2/persist_training_episodes.py`.
3. Entry point atualizado: `iniciar.bat`.
4. Persistencia M5 no banco de mercado: `data/database.py` (`ohlcv_m5`).

## Criterios de pronto para a Fase 1

1. Oportunidade nasce sempre com tese completa.
2. Toda tese termina em estado final.
3. Toda transicao gera evento auditavel.
4. Nenhuma ordem real e enviada na Fase 1.

## Criterios de pronto para a Fase 2

1. `technical_signal` em `CONSUMED` pode virar no maximo uma execucao
   em `signal_executions`.
2. O fluxo live oficial suporta
   `READY -> ENTRY_SENT -> ENTRY_FILLED -> PROTECTED -> EXITED`.
3. Falha ao armar protecao fecha a posicao e termina em `FAILED`.
4. Reconciliacao recupera fills pendentes e detecta fechamento manual/externo.
5. Dashboard live publica backlog, falhas, latencias e posicoes sem protecao.
6. Healthcheck live alerta quando existir dashboard stale ou risco
   acima do threshold.
7. O caminho critico live nao depende de `export_signals -> trade_signals`.

## Go-live checklist da Fase 2

1. Confirmar o banco operacional configurado (`MODEL2_DB_PATH`) e validar
   permissao de escrita no path resolvido.
2. Se necessario, corrigir permissao de escrita da pasta `db/` antes
   do go-live (ex.: ACL no Windows).
3. Executar python scripts/model2/migrate.py up no banco operacional.
4. Validar M2_EXECUTION_MODE=shadow com `M2_SYMBOLS` restrito.
5. Definir `M2_LIVE_SYMBOLS` explicitamente para estabelecer
   `M2_SYMBOLS` inicial.
6. Revisar M2_MAX_DAILY_ENTRIES, M2_MAX_MARGIN_PER_POSITION_USD,
   M2_MAX_SIGNAL_AGE_MINUTES e M2_SYMBOL_COOLDOWN_MINUTES.
7. Validar python scripts/model2/live_execute.py em shadow.
8. Validar python scripts/model2/live_reconcile.py sem divergencias.
9. Confirmar python scripts/model2/live_dashboard.py e python
   scripts/model2/healthcheck_live_execution.py publicando status=ok.
10. Revisar o runbook de incidente antes de ativar M2_EXECUTION_MODE=live.

---

## INICIATIVA M2-016 - Continuidade e Melhorias Pós-Backlog

### TAREFA M2-016.1 - Treino e convergencia progressiva do modelo PPO

Status: CONCLUIDA (2026-03-14)

Entrega esperada:

1. Executar `train_ppo_incremental.py --timesteps 500000` para modelo
   inicial. [OK]
2. Atingir convergencia com Sharpe > 1.0 no dia 3. [PENDENTE - validacao shadow]
3. Validar taxa de sinais com RL enhancement >= 60%.
   [OK - 100% enhancement em validacao]
4. Documenter learnings de hiperparametros e features. [OK]

Evidencias:

1. Checkpoint PPO treino: `checkpoints/ppo_training/ppo_model.zip`.
2. Metricas de treinamento: `results/model2/training_metrics_*.json`
   - log `logs/ppo_training_real.log`.
3. Comparacao deterministica vs RL:
   `results/model2/signal_enhancement_report_*.json`.
4. Atualizacao: `docs/RL_SIGNAL_GENERATION.md` com dados empíricos.
5. Validacao de geracao de sinais: 2/2 sinais com RL enhancement (100%),
   confidence 0.75.
6. Training stats: 500k timesteps, 1118.3s, rollout reward mean 0.6,
   entropy -0.0266.

### TAREFA M2-016.2 - Validacao shadow/live com RL enhancement

Status: EM_PROGRESSO (iniciada 2026-03-14 11:51 UTC)

Entrega esperada:

1. 72h em shadow com RL ativo (deterministica fallback desativada).
2. Comparacao de desempenho vs baseline deterministico.
3. Documentacao de incidentes, edge cases e respostas operacionais.

Evidencias:

1. Dashboard live com metricas:
   `results/model2/signal_execution_snapshots_*.json`.
2. Runner de automacao da janela 72h:
   `scripts/model2/m2_016_2_validation_window.py`.
3. Checkpoints e consolidacao operacional:
   `results/model2/runtime/model2_m2_016_2_checkpoint_*.json`.
4. Estado da janela de validacao:
   `results/model2/runtime/model2_m2_016_2_window_*.json`.
5. Relatorio final RL vs baseline:
   `results/model2/analysis/model2_m2_016_2_report_*.json`.
6. Cobertura unitaria da automacao:
   `tests/test_model2_m2_016_2_validation_window.py`.
7. Atualizacao do runbook com playbooks de RL-specific incidents.

### TAREFA M2-016.3 - Melhorias de features e reward engineering

Status: EM_PROGRESSO (iniciada 2026-03-14, Fases A-D.4 concluídas,
Fase E iniciada)

Entrega atual (Fases A-D.4):

1. Validador de acurácia de labels vs outcomes reais. [OK]
2. Enriquecimento de features com volatilidade (ATR, RSI,
   Bandas de Bollinger). [OK]
3. Enriquecimento com multi-timeframe context (H1, H4, D1). [OK]
4. Especificação técnica completa de roadmap (5 fases). [OK]
5. Reward function estendida com Sharpe, drawdown, recovery time. [OK]
6. Teste de cenários de reward: Winning (+0.76), No Trade (+0.06),
   Slow Recovery (-0.47), Losing (-0.85). [OK]
7. Grid search PPO 64 combinações (learning_rate, batch_size,
   entropy_coef). [OK]
8. Best hyperparams validados: lr=3e-4, bs=64, ent=0.01 (Sharpe=1.176). [OK]
9. Coletor de funding rates com análise de sentiment e leverage. [OK]
10. Integração de open interest com análise de acumulação/distribuição. [OK]
11. Integração feature enricher com dados Binance Futures (simulator). [OK]
12. Teste end-to-end Phase D (simulator). [OK]
13. API client Binance real (mode hybrid mock/real). [OK]
14. Daemon background para coleta contínua (8h FR, 1h OI). [OK]
15. Integration test Phase D.2 (Daemon + API + Enrichment). [OK]
16. Integração API client com persist_training_episodes.py. [OK]
17. Enriquecimento composto (volatility + multi-TF + funding rates + OI)
    em episodes. [OK]
18. API client com métodos de sentiment analysis (funding + OI). [OK]
19. Teste end-to-end Phase D.3 (episodes contêm funding data enriched). [OK]
20. Análise de correlação FR sentiment vs label (Pearson r). [OK]
21. Análise de correlação FR trend vs reward (Pearson r). [OK]
22. Análise de correlação OI sentiment vs label (Pearson r). [OK]
23. Gerador de dados sintéticos para validação. [OK]
24. Script phase_d4_correlation_analysis.py. [OK]
25. Relatório JSON com estatísticas e interpretações. [OK]

Evidencias (Fases A-D.4 concluídas):

1. Validador acurácia: `scripts/model2/validate_training_episodes.py`
2. Enriquecedor features: `scripts/model2/feature_enricher.py`
3. Integração pipeline: `scripts/model2/persist_training_episodes.py`
   (com API client Phase D.3)
4. Reward estendida: `agent/reward_extended.py`
5. Teste cenários: `scripts/test_reward_extended.py`
   (output: `results/model2/extended_reward_test.json`)
6. Grid search PPO: `scripts/model2/ppo_grid_search.py`
7. Análise grid search: `designs/M2_016_3_PPO_GRID_SEARCH_ANALYSIS.md`
8. Spec técnica Phase D: `designs/M2_016_3_PHASE_D_FUNDING_ENRICHMENT.md`
9. Coletor funding/OI simulator: `scripts/model2/binance_funding_collector.py`
10. Teste Phase D: `scripts/model2/test_phase_d_funding_enrichment.py`
11. API client Binance: `scripts/model2/binance_funding_api_client.py`
    (mock + real modes, sentiment methods)
12. Daemon collector: `scripts/model2/binance_funding_daemon.py`
    (8h/1h schedule)
13. Teste Phase D.2: `scripts/model2/test_phase_d2_api_integration.py`
14. Spec Phase D.2: `designs/M2_016_3_PHASE_D2_API_DAEMON.md`
15. Teste Phase D.3 integration: `scripts/model2/test_phase_d3_integration.py`
16. Teste Phase D.3 direct: `scripts/model2/test_phase_d3_direct.py` (PASSED)
17. Gerador dados sintéticos D.4:
    `scripts/model2/test_phase_d4_synthetic_data.py`
18. Análise correlação D.4: `scripts/model2/phase_d4_correlation_analysis.py`
19. Spec Phase D.4: `designs/M2_016_3_PHASE_D4_CORRELATION_ANALYSIS.md`
20. Relatório correlação: `results/model2/analysis/phase_d4_correlation_*.json`

Entrega atual (Fases E.1 + Documentação):

1. LSTM Environment wrapper com rolling buffer (10 timesteps, 20 features). [OK]
2. Feature extraction (5 candle + 4 volatility + 3 multi-TF + 4 FR + 3 OI). [OK]
3. Modo dual LSTM/MLP (output shapes: (10,20) vs (200,)). [OK]
4. Ambiente LSTM ready para integração com training pipeline. [OK]
5. Sincronização de 8 docs governança (CRITICAL/HIGH/MEDIUM/LOW). [OK]
6. ARQUITETURA_ALVO.md atualizado (M2-016.3, camada de features). [OK]
7. RUNBOOK_M2_OPERACAO.md atualizado (daemon, D.4 monitoring, E.1 setup). [OK]
8. RL_SIGNAL_GENERATION.md atualizado (M2-016.3, feature enrichment
   - LSTM). [OK]
9. REGRAS_DE_NEGOCIO.md atualizado (RN-007, RN-008, RN-009). [OK]
10. MODELAGEM_DE_DADOS.md atualizado (funding_rates_api,
    open_interest_api). [OK]
11. ADRS.md atualizado (ADR-023: Feature enrichment, ADR-024: LSTM design). [OK]
12. DIAGRAMAS.md atualizado (diagrama 1c D.2-D.4, diagrama 1d E.1). [OK]
13. CHANGELOG.md criado (M2-016.x release history). [OK]
14. SYNCHRONIZATION.md criado (audit trail de sincronização completo). [OK]

Evidencias (Fase E.1 + Documentação concluídas):

1. LSTM environment wrapper: `agent/lstm_environment.py`
2. Spec Phase E.1: `designs/M2_016_3_PHASE_E_LSTM_POLICY.md`
3. Docs sincronizados: `docs/ARQUITETURA_ALVO.md`,
   `docs/RUNBOOK_M2_OPERACAO.md`, `docs/RL_SIGNAL_GENERATION.md`,
   `docs/REGRAS_DE_NEGOCIO.md`, `docs/MODELAGEM_DE_DADOS.md`,
   `docs/ADRS.md`, `docs/DIAGRAMAS.md`
4. Novo CHANGELOG: `docs/CHANGELOG.md`
5. Audit trail sincronização: `docs/SYNCHRONIZATION.md`
6. Commits sync:
   - eae8d20: 4 docs (CRITICAL+HIGH)
   - 7064e13: 2 docs (MEDIUM)
   - 3dc6f79: 2 docs (LOW) + CHANGELOG
   - 367aa73: SYNCHRONIZATION.md

Entrega atual (Fase D.5):

1. Análise de correlação com dados reais (`shadow` e `live`). [OK]
2. Runner com filtro por `execution_mode` e `min_episodes`. [OK]
3. Cobertura de testes para o novo runner. [OK]

Evidencias (Fase D.5 concluída):

1. Runner de análise: `scripts/model2/phase_d5_real_data_correlation.py`
2. Testes de unidade: `tests/test_model2_phase_d5_correlation.py`
3. Relatório de exemplo: `results/model2/analysis/phase_d5_correlation_*.json`

Entrega atual (Fase E.2):

1. LSTM Policy usando CustomLSTMFeaturesExtractor (64U LSTM + 128D dense). [OK]
2. SubclassedPolicy LSTMPolicy integrada com ActorCriticPolicy para suporte
   default em SB3. [OK]
3. Unit tests executados com sucesso em ambiente simulado DummyLSTMEnv. [OK]

Evidencias (Fase E.2 concluída):

1. LSTM Policy implementation: `agent/lstm_policy.py`
2. Testes de unidade da LSTM Policy: `tests/test_lstm_policy.py`
3. Backlog e docs sincronizados com o encerramento da E.2.

Entrega atual (Fase E.3):

1. Script interativo de treinamento local: `scripts/model2/train_ppo_lstm.py`
   parametrizado. [OK]
2. Refatoração do ambiente para suporte ao Gym.Wrapper via
   `LSTMSignalEnvironment`. [OK]
3. Run comparativo executado tanto para `mlp` e `lstm` e métricas geradas
   separadamente. [OK]

Evidencias (Fase E.3 concluída):

1. Script de Treinamento Duplo: `scripts/model2/train_ppo_lstm.py`
2. Resoluções do ambiente LSTM: `agent/lstm_environment.py`
3. Checkpoints e modelos localizados em: `checkpoints/ppo_training/mlp`
   e `checkpoints/ppo_training/lstm`

Entrega atual (Fase E.4):

1. Script avaliador para simular e calcular histórico real:
   `scripts/model2/phase_e4_sharpe_analysis.py` [OK]
2. Implementação de Testes mockando banco SQLite:
   `tests/test_model2_phase_e4_sharpe.py` [OK]
3. Comparativo PPO MLP vs PPO LSTM exportados para a pasta analysis [OK]

Evidencias (Fase E.4 concluída):

1. Script de Análise Comparativa: `scripts/model2/phase_e4_sharpe_analysis.py`
2. Relatório exportado em:
   `results/model2/analysis/phase_e4_sharpe_analysis.json`

Entrega atual (Fase E.5):

1. Adição de features MACD (linha, sinal, histograma) ao
   `feature_enricher`. [OK]
2. Modelos MLP e LSTM retreinados com 22 features. [OK]
3. Nova avaliação comparativa executada. [OK]

Evidencias (Fase E.5 concluída):

1. Feature Enricher atualizado: `scripts/model2/feature_enricher.py`
2. Modelos retreinados em: `checkpoints/ppo_training/`
3. Relatório de análise atualizado:
   `results/model2/analysis/phase_e4_sharpe_analysis.json`

Entrega atual (Fase E.6 - BLID-064):

1. Adicionar indicador Estocastico (K e D, periodo 14). [OK]
2. Adicionar indicador Williams %R (periodo 14). [OK]
3. Adicionar ATR normalizado multitimeframe (H1, H4, D1). [OK]
4. Total de features expandidas de 22 para 26. [OK]
5. Retreinar modelos MLP e LSTM com 26 features. [OK (background)]
6. Gerar relatorio comparativo Sharpe (22 vs 26 features). [AGENDADO]

Evidencias (Fase E.6 CONCLUIDA — 2026-03-15):

1. Feature Enricher estendido: `scripts/model2/feature_enricher.py`
   (Estocastico, Williams, ATR)
2. Modelos em treinamento background: `checkpoints/ppo_training/mlp/e6`
   e `checkpoints/ppo_training/lstm/e6`
3. Unit tests: `tests/test_model2_phase_e6_indicators.py` — 9/9 PASSED
4. Commit: 4dc1956 [FEAT] BLID-064 Indicadores avancados
5. Backlog e docs sincronizados com E.6

Entrega atual (Fase E.7 - BLID-065):

1. Otimizar hiperparametros PPO com Optuna grid search. [OK]
2. Grid search: learning_rate, batch_size, entropy_coef, clip_range,
   gae_lambda. [OK]
3. Avaliar top 5 hyperparameter sets em ambos os modelos (MLP + LSTM). [OK]
4. Comparacao de performance: baseline E.6 vs otimizado E.7. [OK]
5. Resultados: MLP score 0.8761, LSTM score 0.8690 (E.7 grid completou)

Evidencias (Fase E.7 CONCLUIDA — 2026-03-15):

1. Script Optuna (100 trials): `scripts/model2/optuna_grid_search_ppo.py`
2. Resultados grid search:
   `results/model2/analysis/optuna_grid_search_results.json`
3. Execução: 2026-03-15 16:40 UTC — ✅ COMPLETED
4. Commit: 71b8038 [FEAT] BLID-065 Grid search Optuna (100 trials)
5. Docs sincronizados com E.7

Entrega atual (Fase E.8 - BLID-066):

1. Retreinar modelos MLP com best hyperparameters de E.7.
   [EM_PROGRESSO (background)]
2. Retreinar modelos LSTM com best hyperparameters de E.7.
   [EM_PROGRESSO (background)]
3. Executar comparacao E.6 vs E.8 (baseline vs otimizado).
   [AGENDADO (pos-treino)]
4. Validar melhoria de Sharpe ratio (meta: +10% vs E.6). [AGENDADO (pos-treino)]

Evidencias (Fase E.8 EM PROGRESSO — 2026-03-15):

1. Script retrain com Optuna params:
   `scripts/model2/retrain_ppo_with_optuna_params.py` ✅ OK
2. Script comparacao E.6 vs E.8: `scripts/model2/compare_e6_vs_e8_sharpe.py`
   ✅ OK
3. Treinamento background: MLP (Terminal fe6d7c38...),
   LSTM (Terminal 5c5b7fa1...)
4. Checkpoints esperados:
   `checkpoints/ppo_training/{mlp,lstm}/optuna/ppo_{type}_e8_optuna.zip`
5. Commit: 20fc4ca + 1f8b0c8 [FEAT] BLID-066 com [FIX] glob pattern

## INICIATIVA M2-020 - Arquitetura Model-Driven de Decisao

Objetivo: migrar do fluxo de tese/oportunidade/sinal para decisao direta do
modelo sobre abrir ordem ou aguardar, mantendo somente guard-rails de
seguranca operacional.

### TAREFA M2-020.1 - Definir contrato unico de decisao do modelo

Status: CONCLUIDA (2026-03-21)
Entrega:

1. Especificar entrada e saida da decisao do modelo.
2. Definir acoes: OPEN_LONG, OPEN_SHORT, HOLD, REDUCE, CLOSE.
3. Definir campos obrigatorios: confidence, size_fraction, sl, tp, reason.

Critérios de aceite:

1. Contrato documentado e validado por testes.
2. Payload invalido gera erro explicito e bloqueio seguro.

Evidencias:

1. Contrato canonico de decisao: `core/model2/model_decision.py`.
2. Exposicao no pacote M2: `core/model2/__init__.py`.
3. Testes do contrato e fail-safe:
   `tests/test_model2_model_decision.py`.

### TAREFA M2-020.2 - Criar camada de inferencia desacoplada

Status: CONCLUIDA (2026-03-21)
Entrega:

1. Implementar servico de inferencia independente da tese.
2. Isolar versao de modelo, latencia e metadados de decisao.

Critérios de aceite:

1. Decisao operacional nasce da inferencia do modelo.
2. Logs incluem model_version e tempo de inferencia.

Evidencias:

1. Servico desacoplado de inferencia:
   `core/model2/model_inference_service.py`.
2. Integracao no ponto de decisao (staging live/shadow):
   `core/model2/live_service.py`.
3. Persistencia de `model_decisions` e vinculo por `decision_id`:
   `core/model2/repository.py`.
4. Migracao de schema M2:
   `scripts/model2/migrations/0008_create_model_decisions.sql`.
5. Runner exigindo tabela `model_decisions`:
   `scripts/model2/live_execute.py`.
6. Testes de inferencia desacoplada:
   `tests/test_model2_model_inference_service.py`.
7. Testes de migracao e fluxo live atualizados:
   `tests/test_model2_migrate.py` e `tests/test_model2_live_execution.py`.

### TAREFA M2-020.3 - Consolidar state builder de mercado

Status: CONCLUIDA (2026-03-21)
Entrega:

1. Consolidar estado unico para inferencia em tempo real. [OK]
2. Incluir contexto de posicao e risco no estado. [OK]

Critérios de aceite:

1. Estado completo e serializavel. [OK]
2. Falta de campo critico bloqueia fluxo com fail-safe. [OK]

Evidencias:

1. Builder consolidado com `market_state`, `position_state` e `risk_state`:
   `core/model2/model_state_builder.py`.
2. Persistencia auditavel do estado completo em `model_decisions.input_json`:
   `core/model2/live_service.py`.
3. Cobertura unitaria do builder: `tests/test_model2_model_state_builder.py`.
4. Cobertura integrada no fluxo live/shadow:
   `tests/test_model2_live_execution.py`.

### TAREFA M2-020.4 - Integrar decisao ao orquestrador de execucao

Status: CONCLUIDA (2026-03-21)
Entrega:

1. Substituir origem de decisao atual pelo contrato do modelo. [OK]
2. Permitir acao HOLD sem erro e sem ordem. [OK]

Critérios de aceite:

1. Ordem nasce apenas de decisao do modelo. [OK]
2. Fluxo nao depende de tese/oportunidade para abrir ordem. [OK]

Evidencias:

1. Orquestrador passa a derivar a direcao efetiva da execucao da acao
   do modelo: `core/model2/live_service.py`.
2. Persistencia da execucao reflete o lado decidido pelo modelo e
   preserva a trilha do lado legado de origem:
   `core/model2/repository.py`.
3. Cobertura do fluxo com `OPEN_LONG` sobre candidato `SHORT` e `HOLD`
   sem ordem: `tests/test_model2_live_execution.py`.

### TAREFA M2-020.5 - Manter guard-rails sem estrategia externa

Status: CONCLUIDA (2026-03-21)
Entrega:

1. Preservar `risk/risk_gate.py` e `risk/circuit_breaker.py` no caminho
   critico entre `ModelDecision.action` e envio de ordem. [OK]
2. Manter `scripts/model2/go_live_preflight.py` como gate obrigatorio
   para promocao e operacao `live`. [OK]
3. Remover qualquer estrategia externa como fonte de direcao, entrada ou
   desbloqueio operacional. [OK]

Criterios de aceite:

1. Toda tentativa de entrada `live` passa pelo safety envelope antes de
   qualquer ordem real. [OK]
2. `risk_gate` e `circuit_breaker` permanecem ativos mesmo quando a
   direcao nasce exclusivamente do modelo. [OK]
3. `OPEN_LONG` e `OPEN_SHORT` representam apenas intencao do modelo; a
   liberacao final continua subordinada aos guard-rails. [OK]
4. `HOLD`, `REDUCE` e `CLOSE` nao reativam estrategia externa como
   fallback de direcao. [OK]
5. Falha, ausencia ou inconsistencia em guard-rails bloqueia a execucao
   em fail-safe. [OK]

Evidencias:

1. Importacao e handling explicito de `ACTION_REDUCE` e `ACTION_CLOSE`
   com reason codes auditaveis: `core/model2/live_service.py`.
2. Constante `M2_020_5_RULE_ID` rastreavel em todos os bloqueios de
   acao nao suportada: `core/model2/live_service.py`.
3. Funcao `_check_guardrails_functional` verificando instanciacao e
   operacionalidade de `RiskGate` e `CircuitBreaker` no preflight:
   `scripts/model2/go_live_preflight.py`.
4. Check 6 do preflight expandido com evidencias dos guard-rails:
   `scripts/model2/go_live_preflight.py`.
5. Testes de bloqueio auditavel para `ACTION_REDUCE` e `ACTION_CLOSE`:
   `tests/test_model2_live_execution.py`.
6. Testes do novo check de guard-rails no preflight:
   `tests/test_model2_go_live_preflight.py`.

### TAREFA M2-020.6 - Persistir episodios completos de aprendizado

Status: BACKLOG
Entrega:

1. Persistir estado, acao, reward e proximo estado.
2. Persistir decisoes HOLD e eventos de nao entrada.

Critérios de aceite:

1. Episodios salvos com idempotencia.
2. Auditoria inclui execution_id/symbol quando aplicavel.

### TAREFA M2-020.7 - Definir reward para operar e nao operar

Status: BACKLOG
Entrega:

1. Modelar reward de PnL liquido e custo operacional.
2. Modelar reward para HOLD (evitou perda x perdeu oportunidade).

Critérios de aceite:

1. Reward reproduzivel em replay.
2. Penalidade para overtrading e risco excessivo definida.

### TAREFA M2-020.8 - Reforcar reconciliacao model-driven

Status: BACKLOG
Entrega:

1. Reconciliar decisao do modelo com estado real da exchange.
2. Registrar divergencias criticas como bloqueantes.

Critérios de aceite:

1. Divergencias banco vs exchange detectadas e auditadas.
2. Nao existe transicao final sem reconciliacao minima.

### TAREFA M2-020.9 - Rodar shadow como decisor unico

Status: BACKLOG
Entrega:

1. Operar em shadow com modelo decidindo sozinho.
2. Registrar comparativo de decisoes e resultados.

Critérios de aceite:

1. Shadow gera decisoes completas para todos os sinais.
2. Sem fallback estrategico antigo na decisao.

### TAREFA M2-020.10 - Habilitar retreino automatico governado

Status: BACKLOG
Entrega:

1. Coleta continua de episodios para treino.
2. Treino em ambiente separado do runtime live.
3. Promocao com gate e rollback.

Critérios de aceite:

1. Nova versao so promove com criterio de qualidade.
2. Rollback automatico funcional.

### TAREFA M2-020.11 - Definir gate de promocao GO/NO-GO

Status: BACKLOG
Entrega:

1. Definir criterios minimos de risco, estabilidade e consistencia.
2. Bloquear promocao com evidencia insuficiente.

Critérios de aceite:

1. Decisao GO/NO-GO rastreavel.
2. Falha em criterio retorna NO_GO automaticamente.

### TAREFA M2-020.12 - Migrar live para decisao unica do modelo

Status: BACKLOG
Entrega:

1. Tornar modelo a fonte unica de decisao em live.
2. Preservar envelope de seguranca e reconciliacao.

Critérios de aceite:

1. Fluxo live nao depende de tese/oportunidade para decidir entrada.
2. Protecao pos-fill e fail-safe permanecem ativos.

### TAREFA M2-020.13 - Desativar estrategia legada

Status: BACKLOG
Entrega:

1. Remover acoplamentos legados de estrategia deterministica.
2. Manter compatibilidade operacional de observabilidade.

Critérios de aceite:

1. Nao ha caminho estrategico antigo interferindo na decisao live.
2. Regressao funcional ausente em testes relevantes.

### TAREFA M2-020.14 - Consolidar documentacao da nova arquitetura

Status: BACKLOG
Entrega:

1. Atualizar docs tecnicos e runbook para fluxo model-driven.
2. Atualizar trilha de sincronizacao documental.

Critérios de aceite:

1. Arquitetura, regras e operacao estao consistentes entre docs.
2. Fontes de verdade do M2 refletem decisao direta do modelo.
3. Timeline: ~20-30 min para completar treinos (em andamento)

Proximas Fases:

- Ensemble voting entre MLP e LSTM para robustez.
- Status: EM PROGRESSO (2026-03-15)

### Fase E.9 - BLID-067: Ensemble Voting (MLP + LSTM)

**Status: SCRIPTS CONCLUIDOS — AGENDADO EXECUCAO (2026-03-15 17:00 UTC)**

1. Implementar votador ensemble (soft + hard voting). [OK]
2. Avaliar ensemble vs modelos individuais. [AGENDADO (apos E.8)]
3. Executar benchmark E.5->E.9 (todas as fases). [AGENDADO (apos E.8)]
4. Selecionar melhor metodo de voting para producao. [AGENDADO]

Evidencias (Fase E.9 — Scripts Criados):

1. Votador ensemble: `scripts/model2/ensemble_voting_ppo.py`
   (370+ linhas, soft+hard)
2. Script avaliacao: `scripts/model2/evaluate_ensemble_e9.py`
   (320+ linhas, 4-vias)
3. Script benchmark E.5->E.9: `scripts/model2/compare_e5_to_e9_final.py`
   (280+ linhas)
4. Commit: 21ef5b4 [FEAT] BLID-067 Votador ensemble para robustez
5. Docs sincronizados: BACKLOG, RL_SIGNAL_GENERATION, SYNCHRONIZATION

### Proxima Fase - BLID-068: Geração de Sinais Ensemble em Operação

#### E.10 - Sinais ao vivo com votacao ensemble + paper trading (2026-03-15+)

Status: EM PROGRESSO (scripts criados, integração daily_pipeline)

#### BLID-068 (E.10): Integrar Ensemble em Daily Pipeline

1. Criar wrapper ensemble compatible com daily_pipeline. [OK]
2. Integrar votador em loop operacional (soft + hard). [OK]
3. Implementar confidence scoring baseado em consenso. [OK]
4. Fallback automático para determinístico. [OK]
5. Logging de votação + observabilidade. [OK]
6. Testes em mock environment. [AGENDADO]

Evidencias (Fase E.10 — BLID-068 EM PROGRESSO):

1. Wrapper ensemble: `scripts/model2/ensemble_signal_generation_wrapper.py` ✅
   - EnsembleSignalGenerator class (soft+hard voting)
   - Confidence scoring (consenso + pesos)
   - Fallback gracioso
   - Stats + logging
2. Integração daily_pipeline: `scripts/model2/daily_pipeline.py` ✅
   - Import run_ensemble_signal_generation
   - Etapa "ensemble_signal_generation" adicionada após RL signals
   - Configuracao: voting_method='soft', min_confidence=0.6
3. Commit: [FEAT] BLID-068 Integrar votador ensemble no pipeline

Dependências: BLID-067 (E.9 scripts prontos)

---

## INICIATIVA M2-017 - Adicao de novos simbolos ao pipeline RL

### TAREFA M2-017.1 - Habilitar FLUXUSDT no pipeline RL

Status: CONCLUIDA (2026-03-17)

Entrega:

1. Adicionar FLUXUSDT a config/symbols.py com metadados completos. [OK]
2. Criar playbook FLUXPlaybook (playbooks/flux_playbook.py). [OK]
3. Registrar FLUXPlaybook em playbooks/**init**.py. [OK]
4. Corrigir bug SYMBOLS_ENABLED -> ALL_SYMBOLS no daemon de funding. [OK]
5. Criar testes de integracao tests/test_fluxusdt_integration.py
   (41 testes). [OK]
6. Treinar sub-agente FLUXUSDT apos coleta de >= 20 sinais validados. [PENDENTE]
7. Verificar pipeline completo (5 camadas) com FLUXUSDT em dry-run. [PENDENTE]

Evidencias:

1. Config: `config/symbols.py` — FLUXUSDT (mid_cap_cross_chain, beta 2.9)
2. Playbook: `playbooks/flux_playbook.py` — FLUXPlaybook (4 metodos)
3. Registro: `playbooks/__init__.py` — import + **all** atualizados
4. Bug fix: `scripts/model2/binance_funding_daemon.py`
   - SYMBOLS_ENABLED -> ALL_SYMBOLS (correcao de fallback silencioso)
5. Testes: `tests/test_fluxusdt_integration.py` — 41/41 passando
6. Commits: [FEAT] + [TEST] + [SYNC] aprovados pelo pre-commit hook

---

## INICIATIVA M2-018 - Ativacao do modo live na Binance

Objetivo: ativar `M2_EXECUTION_MODE=live` com confianca, aproveitando
a integracao ja existente entre `scripts/model2/live_execute.py`, `Model2LiveExchange`
e `BinanceClientFactory`. A Camada 5 esta implementada; o que falta e
validar o ciclo ponta-a-ponta no testnet e promover para producao.

Contexto:

- `core/model2/live_exchange.py` — adapter completo (394 linhas):
  `place_market_entry`, `place_protective_order`, `get_available_balance`,
  `list_open_positions`, `get_protection_state`, `close_position_market`,
  precisao automatica via `exchange_information()`.
- `data/binance_client.py` — factory com HMAC + Ed25519, testnet/prod.
- `scripts/model2/live_execute.py` — instancia `Model2LiveExchange` com
  `create_binance_client(mode="live")` quando `execution_mode == "live"`.
- O pipeline roda em shadow por padrao; trocar para live so requer
  `M2_EXECUTION_MODE=live` no `.env`.

### TAREFA M2-018.1 - Validacao do ciclo shadow ponta-a-ponta

Status: PENDENTE

Entrega:

1. Executar `go_live_preflight.py` e confirmar todos os 10 checks. [ ]
2. Rodar 3 ciclos completos (`daily_pipeline + live_cycle`) em shadow
   e confirmar `status=ok` no healthcheck em cada ciclo. [ ]
3. Confirmar que `signal_executions` acumula registros READY/BLOCKED
   com `execution_mode=shadow`. [ ]
4. Confirmar que nenhuma ordem e enviada a Binance em shadow. [ ]

Evidencias:

1. Preflight: `results/model2/runtime/model2_go_live_preflight_*.json`.
2. Healthcheck: `results/model2/runtime/model2_healthcheck_*.json`.
3. Snapshot execucoes: banco `db/modelo2.db` tabela `signal_executions`.

### TAREFA M2-018.2 - Testes de integracao com Binance Testnet

Status: PENDENTE

Entrega:

1. Configurar chaves de testnet em `.env`
   (`BINANCE_API_KEY`, `BINANCE_API_SECRET`, `TRADING_MODE=paper`). [ ]
2. Setar `M2_LIVE_SYMBOLS` com 1 simbolo de baixa liquidez (ex.: BNBUSDT)
   e `M2_MAX_MARGIN_PER_POSITION_USD=1.0`. [ ]
3. Executar 1 ciclo live no testnet e confirmar fill real em
   `signal_executions` (`status=PROTECTED`). [ ]
4. Simular fechamento externo e confirmar que reconciliacao detecta
   `EXITED`. [ ]
5. Confirmar healthcheck sem divergencias apos o ciclo. [ ]

Evidencias:

1. Log do ciclo: `results/model2/runtime/model2_live_execute_*.json`.
2. Snapshot: `signal_executions` com `status=PROTECTED` + `status=EXITED`.
3. Healthcheck: `results/model2/runtime/model2_healthcheck_*.json`.

### TAREFA M2-018.3 - Ativacao em producao com limites conservadores

Status: PENDENTE

Entrega:

1. Definir `M2_EXECUTION_MODE=live` + `TRADING_MODE=live` no `.env`. [ ]
2. Definir `M2_LIVE_SYMBOLS` com no maximo 3 simbolos de alta liquidez
   (BTCUSDT, ETHUSDT, SOLUSDT). [ ]
3. Manter `M2_MAX_MARGIN_PER_POSITION_USD=1.0` e
   `M2_MAX_DAILY_ENTRIES=3` para estreia. [ ]
4. Monitorar os primeiros 5 ciclos live manualmente via healthcheck. [ ]
5. Documentar no runbook os thresholds de escalonamento progressivo. [ ]

Evidencias:

1. `.env` configurado (nao comitar segredos).
2. Log primeiros ciclos: `results/model2/runtime/model2_live_execute_*.json`.
3. Runbook atualizado: `docs/RUNBOOK_M2_OPERACAO.md`.

---

## INICIATIVA M2-019 - RL por Simbolo como Decisor de Entrada

Objetivo: Substituir o scanner SMC deterministico como unico decisor por
modelos RL individuais por simbolo (BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT,
XRPUSDT, FLUXUSDT). Cada simbolo tem seu proprio modelo PPO que decide
LONG/SHORT/NEUTRAL com base em features reais de mercado, integrado ao
pipeline diario como filtro entre o bridge e a order layer.

Arquitetura resultante:

Scanner SMC -> Bridge -> persist_episodes -> train_entry_agents
-> entry_rl_filter -> Order Layer -> Execucao

Regras inviolaveis:

- Fallback conservador quando modelo nao existe ou confianca baixa
- risk_gate.py e circuit_breaker.py permanecem ativos na execucao
- Novos stages com continue_on_error=True

### TAREFA M2-019.1 - EntryDecisionEnv: environment de decisao de entrada

Status: PENDENTE

Entrega:

1. Criar `agent/entry_decision_env.py` com `EntryDecisionEnv(gym.Env)`. [ ]
2. Action space: Discrete(3) — 0=NEUTRAL, 1=LONG, 2=SHORT. [ ]
3. Observation space: Box(36,) normalizado em [-1, 1] com OHLCV
   multi-TF H1/H4/D1 (24), indicadores RSI/MACD/BB/ATR/Stoch/Williams
   (6), funding/LS-ratio/OI (3), contexto SMC (3). [ ]
4. Reward retroativo: outcome real da signal_execution. [ ]
5. Reset seleciona episodio aleatorio da lista de training_episodes. [ ]
6. Fallback gracioso para lista vazia (episodio dummy, reward=0). [ ]
7. Passar gym.utils.check_env sem erro. [ ]
8. Criar `tests/test_entry_decision_env.py` com mock de episodios. [ ]

Dependencias: Nenhuma

---

### TAREFA M2-019.2 - EpisodeLoader: carregamento e normalizacao de episodios

Status: PENDENTE

Entrega:

1. Criar `agent/episode_loader.py` com load_episodes(db_path, symbol,
   timeframe, min_episodes=20). [ ]
2. Conectar ao banco `modelo2.db`, filtrar por symbol e timeframe. [ ]
3. Descartar episodios com label=pending (sem outcome real). [ ]
4. Parsear features_json e mapear para vetor de 36 features. [ ]
5. Normalizar cada feature para [-1, 1] com limites empiricos. [ ]
6. Campos ausentes tornam-se 0.0 (np.nan_to_num). [ ]
7. Retornar List[Dict] ou [] quando insuficiente. [ ]
8. Testar com banco in-memory e episodios sinteticos. [ ]

Dependencias: M2-019.1

---

### TAREFA M2-019.3 - Adaptar SubAgentManager para EntryDecisionEnv

Status: PENDENTE

Entrega:

1. Modificar `agent/sub_agent_manager.py`. [ ]
2. Adicionar train_entry_agent(symbol, episodes, total_timesteps)
   usando EntryDecisionEnv. [ ]
3. Adicionar predict_entry(symbol, observation) retornando
   Tuple[int, float] (acao, confianca). [ ]
4. Fallback: retornar (0, 0.0) — NEUTRAL — quando modelo nao existe. [ ]
5. Salvar modelos como {symbol}_entry_ppo.zip (separado dos de
   gestao). [ ]
6. load_all() carrega modelos de entrada e gestao separadamente. [ ]
7. Ampliar `tests/test_sub_agent_manager.py` com casos de entrada. [ ]

Dependencias: M2-019.1, M2-019.2

---

### TAREFA M2-019.4 - Runner de treinamento diario por simbolo

Status: PENDENTE

Entrega:

1. Criar `scripts/model2/train_entry_agents.py` compativel com
   daily_pipeline. [ ]
2. Para cada simbolo, carregar episodios via EpisodeLoader. [ ]
3. Se episodios >= 20: treinar (5000 steps por ciclo). [ ]
4. Se episodios < 20: retornar status=skipped para o simbolo. [ ]
5. Dry_run nao salva modelos. [ ]
6. Output JSON em `results/model2/runtime/`. [ ]
7. Teste de integracao: banco in-memory, 30 episodios, 1000 steps. [ ]

Dependencias: M2-019.2, M2-019.3

---

### TAREFA M2-019.5 - EntryRLFilter: stage de filtragem por RL no pipeline

Status: PENDENTE

Entrega:

1. Criar `scripts/model2/entry_rl_filter.py` compativel com
   daily_pipeline. [ ]
2. Ler technical_signals com status=CREATED. [ ]
3. Para cada sinal, extrair features (OHLCV + indicadores + funding). [ ]
4. Chamar SubAgentManager.predict_entry(symbol, obs). [ ]
5. Modelo nao existe: passa adiante (fallback conservador). [ ]
6. Confianca < M2_RL_MIN_CONFIDENCE (0.55): passa adiante. [ ]
7. Acao NEUTRAL com confianca >= threshold: cancela com
   reason=rl_entry_neutral. [ ]
8. Acao coincide com direcao: enriquece payload_json e passa. [ ]
9. Acao contradiz direcao: cancela com reason=rl_entry_contradiction. [ ]
10. Output JSON com contagens por categoria de decisao. [ ]
11. Criar `tests/test_entry_rl_filter.py` com todos os caminhos. [ ]

Dependencias: M2-019.3, M2-019.4

---

### TAREFA M2-019.6 - Integrar novos stages ao daily_pipeline

Status: PENDENTE

Entrega:

1. Modificar `scripts/model2/daily_pipeline.py`. [ ]
2. Inserir stage train_entry_agents apos bridge. [ ]
3. Inserir stage entry_rl_filter antes de order_layer. [ ]
4. Ambos os stages com continue_on_error=True. [ ]
5. Manter stages rl_signal_generation e ensemble_signal_generation. [ ]
6. pytest -q tests/ passa apos modificacao. [ ]

Dependencias: M2-019.4, M2-019.5

---

### TAREFA M2-019.7 - Mover persist_training_episodes no pipeline

Status: PENDENTE

Entrega:

1. Modificar `scripts/model2/daily_pipeline.py`. [ ]
2. Reposicionar persist_training_episodes antes de
   train_entry_agents. [ ]
3. Ordem: bridge -> persist_training_episodes ->
   train_entry_agents -> entry_rl_filter -> order_layer. [ ]
4. Episodios do ciclo atual disponiveis para treino no mesmo
   ciclo. [ ]

Dependencias: M2-019.6

---

### TAREFA M2-019.8 - Migracao: auditoria de decisao RL em technical_signals

Status: PENDENTE

Entrega:

1. Criar `scripts/model2/migrations/0008_add_rl_decision.sql`
   ou usar payload_json existente sem ALTER TABLE. [ ]
2. Executar via `python scripts/model2/migrate.py up` sem erro em
   banco novo e existente. [ ]
3. Ampliar `tests/test_model2_migrate.py`. [ ]

Dependencias: Paralelo a M2-019.5

---

### TAREFA M2-019.9 - Testes de integracao ponta-a-ponta

Status: PENDENTE

Entrega:

1. Criar `tests/test_entry_decision_env.py`. [ ]
2. Criar `tests/test_entry_rl_filter.py`. [ ]
3. Criar `tests/test_train_entry_agents.py`. [ ]
4. Todos usando banco in-memory. [ ]
5. Cobrir os 3 caminhos de fallback do entry_rl_filter. [ ]
6. pytest -q tests/ passa sem falhas. [ ]

Dependencias: M2-019.1 a M2-019.7

---

### TAREFA M2-019.10 - Atualizacao documental

Status: PENDENTE

Entrega:

1. Atualizar `docs/ARQUITETURA_ALVO.md` com nova camada RL. [ ]
2. Atualizar `docs/REGRAS_DE_NEGOCIO.md` com regras do
   entry_rl_filter (threshold, fallback, cancelamento). [ ]
3. Atualizar `README.md` mencionando novo stage. [ ]
4. markdownlint docs/*.md passa sem erro. [ ]
5. pytest -q tests/test_docs_model2_sync.py passa. [ ]

Dependencias: M2-019.9

---

## Evidências Finais de Deploy (Model 2.0)

1. **Instalador NSSM:** Arquivo `deploy/install_windows_service.bat` criado.
2. **Payload Daemon:** Input stream mockado em `deploy/daemon_input.txt`.
3. **Runbook Go-Live:** Atualizadas as mecânicas de setup 24/7 de Background
   Process no `RUNBOOK_M2_OPERACAO.md`.
