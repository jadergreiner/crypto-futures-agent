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

1. `from_status = NULL` so e permitido no evento inicial com `to_status = IDENTIFICADA`.

## Regra inicial do padrao de Fase 1

### Padrao: Falha em regiao de oferta para venda

Implementacao de referencia: `core/model2/scanner.py`.

Contrato:

1. Lado fixo da tese inicial: `SHORT`.
2. Tipo da tese: `FALHA_REGIAO_VENDA`.
3. Regra canonicamente auditada por `rule_id = M2-002.1-RULE-FAIL-SELL-REGION`.

### Identificacao

1. Selecionar a zona bearish mais recente e valida (`order_block` ou `fvg`).
2. Preco deve tocar/intersectar a zona (`high >= zone_low` e `low <= zone_high`).
3. Contexto tecnico nao pode estar em estrutura bullish.

### Validacao

1. Rejeicao visivel: candle que toca a zona e fecha abaixo de `zone_low`.
2. A rejeicao deve ter wick superior dominante.
3. Gatilho da tese: minima da vela de rejeicao (`trigger_price`).
4. Confirmacao do padrao inicial: candle posterior rompe a minima da rejeicao.

### Invalidacao

1. Nivel inicial de invalidacao: topo da zona (`invalidation_price = zone_high`).
2. Estrutura muda para leitura altista clara no periodo de decisao.

### Registro inicial da tese (M2-002.2)

1. Detectado o padrao, criar oportunidade em `IDENTIFICADA` com tese completa.
2. Registrar evento inicial auditavel `NULL -> IDENTIFICADA` em `opportunity_events`.
3. Aplicar idempotencia por (`symbol`, `timeframe`, `thesis_type`, `rejection_candle.timestamp`).

## Regra de monitoramento inicial por vela (M2-003.1)

Implementacao de referencia: `core/model2/repository.py` e `scripts/model2/track.py`.

1. O rastreador deve consumir oportunidades em `IDENTIFICADA`.
2. Cada oportunidade consumida deve transicionar para `MONITORANDO`.
3. A transicao deve respeitar a matriz oficial de estados (`IDENTIFICADA -> MONITORANDO`).
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
   - `rule_id = M2-003.3-RULE-THESIS-INVALIDATION|M2-003.3-RULE-THESIS-EXPIRATION`
5. Idempotencia operacional:
   - Se ja estiver no estado alvo, nao criar novo evento.
   - Se o estado atual nao permitir a transicao, nao transicionar.

## Resultado esperado para o negocio

1. Menos sinais impulsivos.
2. Mais clareza no motivo da operacao.
3. Melhor governanca para evolucao do modelo.
