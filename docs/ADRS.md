# ADRs - Modelo 2.0

Este arquivo centraliza as decisoes tecnicas do Modelo 2.0.

## ADR-001 - Arquitetura em camadas

**Status:** ACEITO

**Decisao:**
Separar o processo em camadas independentes:

1. Scanner de Oportunidades.
2. Rastreador de Tese.
3. Ponte de Sinal.
4. Motor de Execucao (futuro).

**Consequencia:**
Menor acoplamento e menor carga cognitiva.

## ADR-002 - Fase 1 sem execucao automatica

**Status:** ACEITO

**Decisao:**
No Modelo 2.0 Fase 1, o sistema apenas identifica e valida tese.

**Consequencia:**
Reduz risco operacional durante a migracao.

## ADR-003 - Maquina de estados obrigatoria para tese

**Status:** ACEITO

**Decisao:**
Toda oportunidade passa por estados controlados:

1. IDENTIFICADA
2. MONITORANDO
3. VALIDADA
4. INVALIDADA
5. EXPIRADA

**Consequencia:**
Fluxo auditavel e sem ambiguidade.

**Implementacao de referencia:**
Contrato canonico em `core/model2/thesis_state.py`, com `ThesisStatus`,
`ALLOWED_TRANSITIONS` e validacao utilitaria de transicao.

## ADR-004 - Persistencia orientada a eventos

**Status:** ACEITO

**Decisao:**
Guardar:

1. Entidade principal da oportunidade.
2. Historico de eventos de transicao.

**Consequencia:**
Permite reprocessamento, auditoria e metricas de qualidade da tese.

## ADR-005 - Regras deterministicas antes de ML

**Status:** ACEITO

**Decisao:**
Primeiro construir motor de tese deterministico.
Modelos estatisticos e ML entram como camada adicional depois.

**Consequencia:**
Maior previsibilidade no inicio da implantacao.

## ADR-006 - Modelo 2.0 isolado da documentacao legada

**Status:** ACEITO

**Decisao:**
Manter uma pasta `docs` nova e focada somente no Modelo 2.0.

**Consequencia:**
Evita mistura de contexto e acelera integracao de novos membros.

## ADR-007 - Banco canonico e migracoes versionadas do Modelo 2.0

**Status:** ACEITO

**Decisao:**
Adotar `db/modelo2.db` como banco canonico do Modelo 2.0, com migracoes SQL
versionadas executadas por `scripts/model2/migrate.py`.

**Consequencia:**
Evita mistura com schema legado (`db/crypto_agent.db`), melhora rastreabilidade
de evolucao de schema e padroniza operacao do M2.

## ADR-008 - Governanca de scripts e outputs do Modelo 2.0

**Status:** ACEITO

**Decisao:**
Centralizar scripts do M2 em `scripts/model2/` e outputs operacionais em
`results/model2/runtime/`, sem criar artefatos na raiz nem em `docs/`.

**Consequencia:**
Repositorio mais organizado, menor poluicao de arvore e auditoria operacional
mais simples.

## ADR-009 - Observabilidade materializada por snapshots com retencao

**Status:** ACEITO

**Decisao:**
Materializar snapshots operacionais do M2 no proprio banco:

1. Painel (`opportunity_dashboard_snapshots`).
2. Auditoria (`opportunity_audit_snapshots`).
3. Retencao hibrida de 30 dias por `snapshot_timestamp`.

**Consequencia:**
Permite consulta historica, comparacao entre execucoes e governanca de volume
com limpeza automatica.

## ADR-010 - Reprocessamento historico em banco isolado de replay

**Status:** ACEITO

**Decisao:**
Executar replay historico em `db/modelo2_replay.db` por padrao, com bloqueio
do banco operacional `db/modelo2.db` salvo override explicito.

**Consequencia:**
Evita contaminacao do ambiente operacional e garante reproducibilidade de
metricas historicas.

## ADR-011 - Taxas oficiais de qualidade em duas familias

**Status:** ACEITO

**Decisao:**
Publicar simultaneamente:

1. Taxa direcional: `VALIDADA/(VALIDADA+INVALIDADA)` e
   `INVALIDADA/(VALIDADA+INVALIDADA)`.
2. Taxa sobre resolvidas: `VALIDADA/(VALIDADA+INVALIDADA+EXPIRADA)` e
   `INVALIDADA/(VALIDADA+INVALIDADA+EXPIRADA)`.

**Consequencia:**
Leitura mais completa da qualidade da tese sem perder contexto de expiracao.

## ADR-012 - Persistencia dedicada da Ponte de Sinal no banco canonico M2

**Status:** ACEITO

**Decisao:**
Persistir os sinais da Camada 3 em tabela dedicada `technical_signals` no
`db/modelo2.db`, sem acoplamento direto ao `trade_signals` legado.

**Consequencia:**
Mantem isolamento arquitetural do Modelo 2.0, simplifica auditoria por
`opportunity_id` e prepara integracao controlada com a camada de execucao
futura (M2-007).

## ADR-013 - Consumo da camada de ordem em modo decisao-only na Fase 1

**Status:** ACEITO

**Decisao:**
A camada de ordem do M2 deve consumir `technical_signals` em status `CREATED`
e registrar decisao em banco (`CONSUMED` ou `CANCELLED`) sem enviar ordem real.

**Consequencia:**
Permite validar integracao fim-a-fim da arquitetura sem risco operacional de
execucao real durante a Fase 1.

## ADR-014 - Dual-write controlado para compatibilidade com trade_signals legado

**Status:** ACEITO

**Decisao:**
Adicionar adaptador dedicado para exportar `technical_signals` consumidos para
`trade_signals` legado com idempotencia por origem (`m2_technical_signal_id`)
e sem envio de ordem real.

**Consequencia:**
Mantem compatibilidade com componentes legados de treinamento/monitoramento,
sem violar o principio de seguranca da Fase 1 (zero execucao real de ordem).

## ADR-015 - Snapshot dedicado para observabilidade do fluxo de sinais

**Status:** ACEITO

**Decisao:**
Materializar metricas do fluxo `CREATED -> CONSUMED -> exportado` em tabela
dedicada `signal_flow_snapshots` no banco canonico M2.

**Consequencia:**
Permite operacao orientada por dados da integracao com execucao, com leitura de
taxa de exportacao, backlog, erros e latencias sem consultar tabelas brutas.

## ADR-016 - Ciclo de execucao real separado de technical_signals

**Status:** ACEITO

**Decisao:**
Manter `technical_signals` apenas como trilha de admissao (`CREATED -> CONSUMED|CANCELLED`)
e modelar o ciclo real da ordem em `signal_executions` e `signal_execution_events`.

**Consequencia:**
Evita misturar decisao de admissao com estado real da execucao, melhora a
auditoria do live e permite reconciliacao restart-safe sem inflar o contrato da
tabela de sinais tecnicos.

## ADR-017 - Caminho critico live nativo e legado fora da rota principal

**Status:** ACEITO

**Decisao:**
Executar o live do M2 por runners dedicados (`live_execute`, `live_reconcile`,
`live_dashboard`, `live_cycle`) sem depender do `export_signals -> trade_signals`
no caminho critico.

**Consequencia:**
O legado continua disponivel por compatibilidade, mas deixa de ser requisito
para operar o agente em mercado real.

## ADR-018 - Protecao obrigatoria com fail-safe de fechamento emergencial

**Status:** ACEITO

**Decisao:**
Toda execucao `ENTRY_FILLED` deve armar `STOP_MARKET` e `TAKE_PROFIT_MARKET`.
Se a protecao nao ficar ativa, a posicao deve ser fechada imediatamente e a
execucao deve terminar em `FAILED`.

**Consequencia:**
Reduz o risco de deixar posicoes abertas sem protecao e formaliza uma regra de
seguranca operacional minima para o go-live.

## ADR-019 - Governanca de risco e observabilidade nativas do M2

**Status:** ACEITO

**Decisao:**
Calcular limite diario, cooldown e exclusividade por simbolo dentro do banco
canonico M2 e publicar dashboard/healthcheck dedicados do live.

**Consequencia:**
O M2 deixa de depender dos contadores em memoria do executor legado e ganha
capacidade propria de rollout progressivo (`shadow -> live subset -> whitelist ampla`).

## ADR-020 - Entry point unico em Windows para operacao legacy + M2

**Status:** ACEITO

**Decisao:**
Consolidar a operacao local Windows em um unico entry point (`iniciar.bat`),
com duas opcoes:

1. Fluxo legado (`menu.py`).
2. Fluxo M2 em loop continuo (`daily_pipeline -> live_cycle -> healthcheck`).

**Consequencia:**
Padroniza a operacao, reduz erro humano de comando manual e garante que o
fluxo live receba sinais atualizados antes de cada tentativa de execucao.
