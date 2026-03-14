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
2. Persistencia inicial + evento `NULL -> IDENTIFICADA`: `core/model2/repository.py`.
3. Cobertura de idempotencia e atomicidade: `tests/test_model2_thesis_repository.py`.

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

1. Migracao de materializacao: `scripts/model2/migrations/0003_create_observability_snapshots.sql`.
2. Servico canonico de observabilidade: `core/model2/observability.py`.
3. Runner operacional do painel: `scripts/model2/dashboard.py`.
4. Cobertura de metricas e persistencia: `tests/test_model2_observability.py`.

### TAREFA M2-004.2 - Registros de auditoria

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Registro por transicao. [OK]
2. Correlacao por `opportunity_id`. [OK]

Evidencias:

1. Tabela materializada de auditoria: `scripts/model2/migrations/0003_create_observability_snapshots.sql`.
2. Servico de refresh e filtros de auditoria: `core/model2/observability.py`.
3. Runner operacional de auditoria: `scripts/model2/audit.py`.
4. Cobertura de filtros e retencao: `tests/test_model2_observability.py`.

## INICIATIVA M2-005 - Qualidade

### TAREFA M2-005.1 - Testes unitarios de transicao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Casos validos e invalidos de mudanca de estado. [OK]

Evidencias:

1. Suite unitaria dedicada de transicoes: `tests/test_model2_transition_suite.py`.
2. Cobertura de caminhos validos/invalidos/idempotencia/not_found e auditoria por evento:
   `tests/test_model2_transition_suite.py`.
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
3. Migracao de schema M2: `scripts/model2/migrations/0004_create_technical_signals.sql`.
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

1. Migracao de snapshot: `scripts/model2/migrations/0005_create_signal_flow_snapshots.sql`.
2. Servico canonico de observabilidade estendido: `core/model2/observability.py`.
3. Runner operacional: `scripts/model2/export_dashboard.py`.
4. Cobertura de metricas e runner: `tests/test_model2_signal_flow_observability.py`.

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
2. Criar trilha de eventos `signal_execution_events` com auditoria por transicao. [OK]
3. Manter `technical_signals.status` apenas como trilha de admissao (`CREATED -> CONSUMED|CANCELLED`). [OK]

Evidencias:

1. Contrato canonico de estados live: `core/model2/live_execution.py`.
2. Persistencia transacional do ciclo live: `core/model2/repository.py`.
3. Migracao de schema: `scripts/model2/migrations/0006_create_signal_executions.sql`.
4. Cobertura de migracao: `tests/test_model2_migrate.py`.

### TAREFA M2-009.2 - Gate live do M2

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Admitir apenas `technical_signals` em `CONSUMED`. [OK]
2. Bloquear por simbolo, saldo, cooldown, limite diario, posicao aberta e sinal vencido. [OK]
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
2. Persistir `exchange_order_id`, `client_order_id`, `filled_qty` e `filled_price`. [OK]
3. Garantir idempotencia por `technical_signal_id` sem ordem duplicada. [OK]

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
3. Testes de falha de protecao e fechamento emergencial: `tests/test_model2_live_execution.py`.

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

1. Snapshot materializado live: `scripts/model2/migrations/0007_create_signal_execution_snapshots.sql`.
2. Servico de observabilidade live: `core/model2/observability.py`.
3. Runner operacional do dashboard: `scripts/model2/live_dashboard.py`.
4. Testes de metricas e runner: `tests/test_model2_live_observability.py`.

### TAREFA M2-010.3 - Healthcheck e runbook

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Alertar quando houver dashboard stale, posicao sem protecao ou divergencia acima do limite. [OK]
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
2. Separar o caminho critico live do `export_signals -> trade_signals` legado. [OK]
3. Publicar resumo unico do ciclo live. [OK]

Evidencias:

1. Orquestrador do ciclo live: `scripts/model2/live_cycle.py`.
2. Runners independentes do ciclo live: `scripts/model2/live_execute.py` e `scripts/model2/live_reconcile.py`.
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
3. Testes de aceite do gate e idempotencia: `tests/test_model2_live_execution.py`.

### TAREFA M2-012.2 - Configuracao explicita de ativacao

Status: CONCLUIDA (2026-03-09)
Entrega:

1. Expor `M2_EXECUTION_MODE=shadow|live`. [OK]
2. Expor `M2_LIVE_SYMBOLS`, `M2_MAX_DAILY_ENTRIES` e `M2_MAX_MARGIN_PER_POSITION_USD`. [OK]
3. Expor idade maxima de sinal e cooldown por simbolo para operacao progressiva. [OK]

Evidencias:

1. Configuracoes do ambiente: `config/settings.py`.
2. Exemplo de ambiente: `.env.example`.
3. Runners consumindo configuracao: `scripts/model2/live_execute.py` e `scripts/model2/live_reconcile.py`.

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

1. Atualizar backlog, arquitetura alvo, modelagem de dados e regras de negocio. [OK]
2. Atualizar ADRs, diagramas e runbook operacional. [OK]
3. Atualizar README operacional dos scripts do M2. [OK]

Evidencias:

1. Backlog canonico: `docs/BACKLOG.md`.
2. Arquitetura alvo: `docs/ARQUITETURA_ALVO.md`.
3. Regras de negocio: `docs/REGRAS_DE_NEGOCIO.md`.
4. Modelagem de dados: `docs/MODELAGEM_DE_DADOS.md`.
5. ADRs e diagramas: `docs/ADRS.md` e `docs/DIAGRAMAS.md`.
6. Runbook e comandos: `docs/RUNBOOK_M2_OPERACAO.md` e `scripts/model2/README.md`.
7. Suite de sincronismo documental: `tests/test_docs_model2_sync.py`.

## INICIATIVA M2-014 - Automacao de go-live da Fase 2

### TAREFA M2-014.1 - Runner unico de preflight para go-live

Status: CONCLUIDA (2026-03-13)
Entrega:

1. Publicar runner unico `go_live_preflight.py` cobrindo os 10 itens do checklist. [OK]
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
3. Executar ciclo operacional M2 em loop continuo com healthcheck por ciclo. [OK]
4. Permitir modo de diagnostico `M2_RUN_ONCE=1` e intervalo configuravel via `M2_LOOP_SECONDS`. [OK]

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
2. Coleta aplicada para todo `M2_SYMBOLS` (derivado de `M2_LIVE_SYMBOLS`, com fallback para `ALL_SYMBOLS`). [OK]
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

1. `technical_signal` em `CONSUMED` pode virar no maximo uma execucao em `signal_executions`.
2. O fluxo live oficial suporta `READY -> ENTRY_SENT -> ENTRY_FILLED -> PROTECTED -> EXITED`.
3. Falha ao armar protecao fecha a posicao e termina em `FAILED`.
4. Reconciliacao recupera fills pendentes e detecta fechamento manual/externo.
5. Dashboard live publica backlog, falhas, latencias e posicoes sem protecao.
6. Healthcheck live alerta quando existir dashboard stale ou risco acima do threshold.
7. O caminho critico live nao depende de `export_signals -> trade_signals`.

## Go-live checklist da Fase 2

1. Confirmar o banco operacional configurado (`MODEL2_DB_PATH`) e validar permissao de escrita no path resolvido.
2. Se necessario, corrigir permissao de escrita da pasta `db/` antes do go-live (ex.: ACL no Windows).
3. Executar python scripts/model2/migrate.py up no banco operacional.
4. Validar M2_EXECUTION_MODE=shadow com `M2_SYMBOLS` restrito.
5. Definir `M2_LIVE_SYMBOLS` explicitamente para estabelecer `M2_SYMBOLS` inicial.
6. Revisar M2_MAX_DAILY_ENTRIES, M2_MAX_MARGIN_PER_POSITION_USD, M2_MAX_SIGNAL_AGE_MINUTES e M2_SYMBOL_COOLDOWN_MINUTES.
7. Validar python scripts/model2/live_execute.py em shadow.
8. Validar python scripts/model2/live_reconcile.py sem divergencias.
9. Confirmar python scripts/model2/live_dashboard.py e python scripts/model2/healthcheck_live_execution.py publicando status=ok.
10. Revisar o runbook de incidente antes de ativar M2_EXECUTION_MODE=live.

---

## INICIATIVA M2-016 - Continuidade e Melhorias Pós-Backlog

### TAREFA M2-016.1 - Treino e convergencia progressiva do modelo PPO

Status: CONCLUIDA (2026-03-14)

Entrega esperada:

1. Executar `train_ppo_incremental.py --timesteps 500000` para modelo inicial. [OK]
2. Atingir convergencia com Sharpe > 1.0 no dia 3. [PENDENTE - validacao shadow]
3. Validar taxa de sinais com RL enhancement >= 60%. [OK - 100% enhancement em validacao]
4. Documenter learnings de hiperparametros e features. [OK]

Evidencias:

1. Checkpoint PPO treino: `checkpoints/ppo_training/ppo_model.zip`.
2. Metricas de treinamento: `results/model2/training_metrics_*.json` + log `logs/ppo_training_real.log`.
3. Comparacao deterministica vs RL: `results/model2/signal_enhancement_report_20260314.json`.
4. Atualizacao: `docs/RL_SIGNAL_GENERATION.md` com dados empíricos.
5. Validacao de geracao de sinais: 2/2 sinais com RL enhancement (100%), confidence 0.75.
6. Training stats: 500k timesteps, 1118.3s, rollout reward mean 0.6, entropy -0.0266.

### TAREFA M2-016.2 - Validacao shadow/live com RL enhancement

Status: EM_PROGRESSO (iniciada 2026-03-14 11:51 UTC)

Entrega esperada:

1. 72h em shadow com RL ativo (deterministica fallback desativada).
2. Comparacao de desempenho vs baseline deterministico.
3. Documentacao de incidentes, edge cases e respostas operacionais.

Evidencias:

1. Dashboard live com metricas: `results/model2/signal_execution_snapshots_*.json`.
2. Analise de divergencia entre RL prediction vs resultado real.
3. Atualizacao do runbook com playbooks de RL-specific incidents.

### TAREFA M2-016.3 - Melhorias de features e reward engineering

Status: EM_PROGRESSO (iniciada 2026-03-14, Fases A-C concluídas)

Entrega atual (Fases A-C):

1. Validador de acurácia de labels vs outcomes reais. [OK]
2. Enriquecimento de features com volatilidade (ATR, RSI, Bandas de Bollinger). [OK]
3. Enriquecimento com multi-timeframe context (H1, H4, D1). [OK]
4. Especificação técnica completa de roadmap (5 fases). [OK]
5. Reward function estendida com Sharpe, drawdown, recovery time. [OK]
6. Teste de cenários de reward: Winning (+0.76), No Trade (+0.06), Slow Recovery (-0.47), Losing (-0.85). [OK]
7. Grid search PPO 64 combinações (learning_rate, batch_size, entropy_coef). [OK]
8. Best hyperparams validados: lr=3e-4, bs=64, ent=0.01 (Sharpe=1.176). [OK]

Evidencias (Fases A-C concluídas):

1. Validador acurácia: `scripts/model2/validate_training_episodes.py`
2. Enriquecedor features: `scripts/model2/feature_enricher.py`
3. Integração pipeline: `scripts/model2/persist_training_episodes.py`
4. Reward estendida: `agent/reward_extended.py`
5. Teste cenários: `scripts/test_reward_extended.py` (output: `results/model2/extended_reward_test.json`)
6. Grid search PPO: `scripts/model2/ppo_grid_search.py`
7. Análise grid search: `designs/M2_016_3_PPO_GRID_SEARCH_ANALYSIS.md` (grid 64 combos, best=baseline)
8. Resultados grid: `results/model2/ppo_grid_search_20260314T121210Z.json`
9. Spec técnica: `designs/M2_016_3_FEATURE_REWARD_IMPROVEMENTS.md`

Próximas Fases:

1. **Fase D (Dias 22-28)**: Enriquecimento Fase 2 - Funding rates, open interest, onchain data
2. **Fase E (Dias 29-42)**: Experimentar LSTM para capturar state dependence temporal



