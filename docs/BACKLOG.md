# Backlog - Modelo 2.0

Somente funcionalidades e tarefas do Modelo 2.0.

## Prioridade P0 (iniciar agora)

## INICIATIVA M2-001 - Fundacao da tese

### TAREFA M2-001.1 - Criar esquema de oportunidades

Status: A FAZER
Entrega:

1. Criar tabela `opportunities`.
2. Criar indices basicos.
3. Criar migracao versionada.

### TAREFA M2-001.2 - Criar esquema de eventos

Status: A FAZER
Entrega:

1. Criar tabela `opportunity_events`.
2. Garantir chave estrangeira e indices.

### TAREFA M2-001.3 - Definir enumeracoes de estado

Status: A FAZER
Entrega:

1. Estados oficiais.
2. Matriz de transicao valida.

## INICIATIVA M2-002 - Scanner de Oportunidades

### TAREFA M2-002.1 - Implementar detector do padrao inicial

Status: A FAZER
Entrega:

1. Padrao "falha em regiao para venda".
2. Registro `IDENTIFICADA`.

### TAREFA M2-002.2 - Persistir tese inicial

Status: A FAZER
Entrega:

1. Gravar niveis de zona.
2. Gravar gatilho e invalidacao.
3. Gravar metadados da analise tecnica.

## INICIATIVA M2-003 - Rastreador de Tese

### TAREFA M2-003.1 - Monitoramento por vela

Status: A FAZER
Entrega:

1. Consumir oportunidades abertas.
2. Atualizar para `MONITORANDO`.

### TAREFA M2-003.2 - Regras de validacao

Status: A FAZER
Entrega:

1. Confirmar rejeicao.
2. Confirmar rompimento do gatilho.
3. Transicionar para `VALIDADA`.

### TAREFA M2-003.3 - Regras de invalidacao/expiracao

Status: A FAZER
Entrega:

1. Invalidar por quebra da premissa.
2. Expirar por tempo limite.

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
