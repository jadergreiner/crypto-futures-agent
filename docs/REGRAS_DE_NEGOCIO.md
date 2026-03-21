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

### RN-005 - Protecao obrigatoria

Toda posicao aberta deve ter protecao ativa apos fill.
Sem protecao, o estado deve ser tratado como risco critico.

### RN-006 - Idempotencia

O sistema nao pode gerar ordem duplicada para a mesma decisao efetiva.

### RN-007 - Reconciliacao obrigatoria

Estados de banco e exchange devem ser reconciliados continuamente.
Divergencias criticas devem gerar bloqueio e evento auditavel.

### RN-008 - Auditoria obrigatoria

Toda decisao e toda mudanca de estado relevante devem registrar:

1. timestamp UTC
2. motivo
3. status
4. metadados operacionais

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
