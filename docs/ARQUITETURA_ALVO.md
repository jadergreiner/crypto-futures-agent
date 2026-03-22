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
4. `format_cycle_summary()` — Resumo do ciclo com N simbolos

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
