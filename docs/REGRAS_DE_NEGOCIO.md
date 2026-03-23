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
