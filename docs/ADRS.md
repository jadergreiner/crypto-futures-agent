# ADRs - Modelo 2.0 (Estado Atual)

Este arquivo lista as decisoes arquiteturais vigentes.

## ADR-001 - Arquitetura model-driven

**Status:** ACEITO

A decisao de trade nasce no modelo.
Acoes permitidas: OPEN_LONG, OPEN_SHORT, HOLD, REDUCE, CLOSE.

## ADR-002 - Safety envelope inviolavel

**Status:** ACEITO

`risk_gate` e `circuit_breaker` permanecem ativos em todos os caminhos.
Em duvida operacional, bloquear operacao.

## ADR-003 - Reconciliacao obrigatoria

**Status:** ACEITO

Estado de banco e exchange deve ser reconciliado continuamente.
Divergencia critica bloqueia continuidade e gera evento auditavel.

## ADR-004 - Idempotencia de execucao

**Status:** ACEITO

Uma decisao efetiva nao pode gerar ordens duplicadas.
Retries devem preservar correlacao de decisao.

## ADR-005 - Persistencia de aprendizado completo

**Status:** ACEITO

Persistir episodios com estado, acao, reward e proximo estado.
Incluir episodios da acao HOLD.

## ADR-006 - Retreino automatico governado

**Status:** ACEITO

Retreino e automatico, mas com controles:

1. treino fora do runtime live;
2. validacao obrigatoria;
3. gate GO/NO-GO;
4. rollback de versao.

## ADR-007 - Promocao para live por evidencia

**Status:** ACEITO

Promocao depende de criterios objetivos de risco, estabilidade e consistencia.
Sem evidencia suficiente, resultado obrigatorio: NO_GO.

## ADR-008 - Banco canonico M2

**Status:** ACEITO

`db/modelo2.db` e o banco canonico de operacao do Modelo 2.0.
Schema e evoluido por migracoes versionadas.

## ADR-009 - Auditabilidade ponta a ponta

**Status:** ACEITO

Toda decisao, transicao e mitigacao relevante deve gerar trilha com:

1. timestamp UTC;
2. status;
3. motivo;
4. metadados operacionais.

## ADR-025 - RL Decision per Symbol (M2-019)

**Status:** ACEITO

Decisao de entrada nascera em modelos RL individuais por simbolo
(M2-019), ao inves de dependencia exclusiva no scanner SMC.

Arquitetura:

1. Gym.Env customizado para cada simbolo (`EntryDecisionEnv`)
2. Action space: NEUTRAL(0), LONG(1), SHORT(2)
3. Observation: 36 features consolidadas (OHLCV + indicators + funding)
4. Reward: retroativo de outcome real em signal_executions
5. Environment fallback: episodio dummy com reward=0 quando sem dados

Beneficios:

1. Decisao de entrada totalmente data-driven
2. Aprendizado continuo com dados de operacao real
3. Fallback seguro quando modelo indisponivel
4. Auditoria completa via logging de episodios

Restrições:

1. Model nao ativa: fallback gracioso sem entrada
2. Confidence baixa: passagem adiante (conservador)
3. Contradic ao com direcao SMC: cancelamento auditavel

Componentes:

1. `agent/entry_decision_env.py` — Environment Gym
2. `agent/episode_loader.py` — Carregamento de episodios (futura)
3. `scripts/model2/train_entry_agents.py` — Treino diario (futura)
4. `scripts/model2/entry_rl_filter.py` — Filter stage (futura)
