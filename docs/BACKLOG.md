# Backlog - Modelo 2.0

Somente funcionalidades e tarefas do Modelo 2.0.

## Prioridade P0 (iniciar agora)

## INICIATIVA M2-001 - Fundacao da tese

### TAREFA M2-001.1 - Criar esquema de oportunidades

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Criar tabela `opportunities`. [OK]
2. Criar indices basicos. [OK]
3. Criar migracao versionada. [OK]

Evidencias:

1. Migracao SQL: `scripts/model2/migrations/0001_create_opportunities.sql`.
2. Runner de migracao: `scripts/model2/migrate.py`.
3. Banco canonico M2: `db/modelo2.db`.
4. Output operacional: `results/model2/runtime/model2_migrate_*.json`.

### TAREFA M2-001.2 - Criar esquema de eventos

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Criar tabela `opportunity_events`. [OK]
2. Garantir chave estrangeira e indices. [OK]

Evidencias:

1. Migracao SQL: `scripts/model2/migrations/0002_create_opportunity_events.sql`.
2. Cobertura de testes: `tests/test_model2_migrate.py`.
3. Execucao de migracoes M2: `scripts/model2/migrate.py`.

### TAREFA M2-001.3 - Definir enumeracoes de estado

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Estados oficiais. [OK]
2. Matriz de transicao valida. [OK]

Evidencias:

1. Contrato canonico: `core/model2/thesis_state.py`.
2. Pacote de dominio M2: `core/model2/__init__.py`.
3. Testes do contrato: `tests/test_model2_state_contract.py`.
4. Migracoes alinhadas ao contrato: `tests/test_model2_migrate.py`.
5. Documentacao sincronizada: `docs/REGRAS_DE_NEGOCIO.md`,
   `docs/MODELAGEM_DE_DADOS.md` e `docs/ADRS.md`.

## INICIATIVA M2-002 - Scanner de Oportunidades

### TAREFA M2-002.1 - Implementar detector do padrao inicial

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Padrao "falha em regiao para venda". [OK]
2. Registro `IDENTIFICADA`. [OK]

Evidencias:

1. Detector canonico: `core/model2/scanner.py`.
2. Runner operacional do scanner: `scripts/model2/scan.py`.
3. Testes unitarios do detector: `tests/test_model2_scanner_detector.py`.

### TAREFA M2-002.2 - Persistir tese inicial

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Gravar niveis de zona. [OK]
2. Gravar gatilho e invalidacao. [OK]
3. Gravar metadados da analise tecnica. [OK]

Evidencias:

1. Repositorio transacional M2: `core/model2/repository.py`.
2. Persistencia inicial + evento `NULL -> IDENTIFICADA`: `core/model2/repository.py`.
3. Cobertura de idempotencia e atomicidade: `tests/test_model2_thesis_repository.py`.

## INICIATIVA M2-003 - Rastreador de Tese

### TAREFA M2-003.1 - Monitoramento por vela

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Consumir oportunidades abertas. [OK]
2. Atualizar para `MONITORANDO`. [OK]

Evidencias:

1. Transicao de estado no repositorio M2: `core/model2/repository.py`.
2. Runner do rastreador por vela: `scripts/model2/track.py`.
3. Testes de transicao e idempotencia: `tests/test_model2_tracker.py`.

### TAREFA M2-003.2 - Regras de validacao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Confirmar rejeicao. [OK]
2. Confirmar rompimento do gatilho. [OK]
3. Transicionar para `VALIDADA`. [OK]

Evidencias:

1. Validador deterministico: `core/model2/validator.py`.
2. Transicao `MONITORANDO -> VALIDADA`: `core/model2/repository.py`.
3. Runner operacional de validacao: `scripts/model2/validate.py`.
4. Testes de regra e fluxo: `tests/test_model2_validator.py` e
   `tests/test_model2_validation_flow.py`.

### TAREFA M2-003.3 - Regras de invalidacao/expiracao

Status: CONCLUIDA (2026-03-08)
Entrega:

1. Invalidar por quebra da premissa. [OK]
2. Expirar por tempo limite. [OK]

Evidencias:

1. Resolvedor deterministico: `core/model2/resolver.py`.
2. Transicoes `MONITORANDO -> INVALIDADA|EXPIRADA`: `core/model2/repository.py`.
3. Runner operacional de resolucao: `scripts/model2/resolve.py`.
4. Testes de regra e fluxo: `tests/test_model2_resolver.py` e
   `tests/test_model2_resolution_flow.py`.

## Prioridade P1 (apos P0)

## INICIATIVA M2-004 - Observabilidade

### TAREFA M2-004.1 - Painel de oportunidades

Status: A FAZER
Entrega:

1. Contagem por estado.
2. Tempo medio ate resolucao.

### TAREFA M2-004.2 - Registros de auditoria

Status: A FAZER
Entrega:

1. Registro por transicao.
2. Correlacao por `opportunity_id`.

## INICIATIVA M2-005 - Qualidade

### TAREFA M2-005.1 - Testes unitarios de transicao

Status: A FAZER
Entrega:

1. Casos validos e invalidos de mudanca de estado.

### TAREFA M2-005.2 - Reprocessamento historico

Status: A FAZER
Entrega:

1. Reprocessar velas passadas.
2. Medir taxa de validacao vs invalidacao.

## Prioridade P2 (fase posterior)

## INICIATIVA M2-006 - Ponte de Sinal

### TAREFA M2-006.1 - Gerar sinal padrao apos validacao

Status: A FAZER

## INICIATIVA M2-007 - Integracao com execucao

### TAREFA M2-007.1 - Consumir sinal validado na camada de ordem

Status: A FAZER

## Criterios de pronto para a Fase 1

1. Oportunidade nasce sempre com tese completa.
2. Toda tese termina em estado final.
3. Toda transicao gera evento auditavel.
4. Nenhuma ordem real e enviada na Fase 1.
