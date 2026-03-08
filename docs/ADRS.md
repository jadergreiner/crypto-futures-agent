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
