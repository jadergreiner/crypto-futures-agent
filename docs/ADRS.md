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
