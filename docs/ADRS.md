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
