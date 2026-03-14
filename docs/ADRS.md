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

## ADR-021 - Coleta por ciclo com deduplicacao de candles

**Status:** ACEITO

**Decisao:**
No fluxo operacional Windows (`iniciar.bat`, opcao `2`), executar `sync_market_context`
antes do pipeline de decisao em dois timeframes por ciclo:

1. `H4` (janela curta de atualizacao)
2. `M5` (granularidade intraday para contexto operacional)

Regras associadas:

1. A coleta de contexto roda para todo o universo canonico `M2_SYMBOLS`.
2. `M2_SYMBOLS` e derivado de `M2_LIVE_SYMBOLS` no `.env` (fallback: `config.symbols.ALL_SYMBOLS`).
3. O sync deve deduplicar candles por chave natural (`symbol`, `timestamp`) antes de persistir.

**Consequencia:**

1. Cada ciclo parte de dados de mercado atualizados, reduzindo sinal sobre base defasada.
2. A persistencia permanece idempotente, sem duplicar o mesmo candle.
3. Unifica coleta, pipeline e live no mesmo escopo operacional (`M2_SYMBOLS`).

## ADR-022 - Pipeline de RL com coleta de episodios por ciclo

**Status:** ACEITO

**Decisao:**
Integrar modelo PPO treinado via episodios coletados automaticamente a cada ciclo do pipeline:

1. Cada ciclo coleta eventos de contexto, oportunidade e resultado em `training_episodes`.
2. Episodios sao agregados por ciclo (`cycle_run_id`) e persistidos em Sqlite.
3. Treinamento incremental roda off-pipeline (semanal) via `train_ppo_incremental.py`.
4. Modelo PPO e consumido on-demand por `rl_signal_generation.py` como etapa 9 do pipeline.
5. Fallback deterministica com confidence 0.70 quando modelo indisponivel.

**Consequencia:**

1. Cada ciclo contribui dados para melhorar o modelo ML progressivamente.
2. Pipeline nao e bloqueada por convergencia de treinamento (offline).
3. RL enhancement e aplicativo apenas quando modelo passar limiares de qualidade (Sharpe > 0.5).
4. Auditoria completa de episodios permite replay e diagnostico de producao.

## ADR-023 - Enriquecimento de episodios com dados de mercado externo

**Status:** ACEITO

**Decisao:**
Enriquecer episodios de treinamento com dados de taxa de financiamento (FR)
e interesse aberto (OI) coletados via API Binance (Fases D.2-D.4):

1. Daemon `daemon_funding_rates.py` coleta FR continuamente (interval: 30s).
2. Features de FR (`latest_rate`, `avg_rate_24h`, `sentiment`, `trend`)
   sao integradas em cada episodio durante coleta do pipeline.
3. Features de OI (`open_interest`, `oi_sentiment`, `change_direction`)
   sao calculadas e persistidas em `training_episodes.features_json`.
4. Analise de correlacao (Fase D.4) roda semanal via
   `phase_d4_correlation_analysis.py` para validar poder preditivo.
5. Descoberta: FR bearish prediz 0% win rate (sinal forte de perda).

**Alternativas consideradas:**

- Sincronização pull-on-demand (rejeitada): aumentaria latencia do pipeline.
- Apenas histórico Binance (rejeitada): não captura dados em tempo real necessários.
- Mock data (rejeitada): não valida integracao real com API.

**Consequencia:**

1. Episodios agora contem contexto de mercado externo (20 features).
2. Modelos PPO treinam com sinal mais rico, potencialmente melhorando performance.
3. Correlacao descoberta (r=0.27, p=0.006) pode gerar regra RN-008 de rejeicao.
4. Requer monitoramento continuo do daemon (operacao day-to-day).
5. Fallback: permitir episodio com NaN se coleta falhar < 10%.

## ADR-024 - Ambiente LSTM with rolling window state buffer

**Status:** ACEITO

**Decisao:**
Preparar suporte para politicas LSTM na pipeline RL via novo
`LSTMSignalEnvironment` wrapper (Fase E.1):

1. `LSTMSignalEnvironment` envolve `SignalReplayEnv` com buffer temporal
   (`deque`, `maxlen=10` timesteps).
2. Feature extraction normaliza 20 escalares (candle, volatility,
   multi-TF, FR, OI) para shape (seq_len=10, n_features=20).
3. Modo dual suporta LSTM output (10, 20) e fallback MLP flat (200,).
4. Runtime switchable via `set_model_type()` para compatibilidade backward.
5. Proximas fases (E.2-E.4): Treinar LSTM policy e comparar vs MLP baseline.

**Alternativas consideradas:**

- Stacking candles em (n_candles, n_features) sem buffer (rejeitada):
  pierde ordem temporal importante.
- Frame stacking legado (rejeitada): sem normalizacao, features heterogeneas.
- Apenas LSTM sem fallback (rejeitada): quebra compatibilidade com agents MLP existentes.

**Consequencia:**

1. Novo `agent/lstm_environment.py` (260 linhas) requerido com manutencao.
2. LSTM politicas agora viavel (roadmap E.2-E.4).
3. Backward compatibility preservada com flat mode.
4. Sharpe ratio LSTM >= baseline MLP meta para go-live (idealm. +5%).
5. Requer validacao de normalizacao ([-1, 1]) em todos 20 features.
