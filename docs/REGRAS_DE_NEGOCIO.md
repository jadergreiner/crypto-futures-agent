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

### Identificacao

1. Preco entra em regiao de oferta relevante.
2. Contexto tecnico nao esta altista claro.

### Validacao

1. Rejeicao visivel na regiao.
2. Rompimento da minima da vela de rejeicao.

### Invalidacao

1. Fechamento acima do topo da regiao.
2. Estrutura muda para leitura altista clara no periodo de decisao.

## Resultado esperado para o negocio

1. Menos sinais impulsivos.
2. Mais clareza no motivo da operacao.
3. Melhor governanca para evolucao do modelo.
