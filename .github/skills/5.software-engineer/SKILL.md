---
name: 5.software-engineer
description: |
  Implementa codigo Python orientado a testes (TDD Green-Refactor),
  modelagem de banco de dados e calibracao de modelos ML.
  Use quando: receber demanda refinada do QA-TDD com suite de testes
  em fase RED. Atualiza backlog para Em Desenvolvimento e gera prompt
  executavel para Tech Lead realizar code review.
metadata:
  workflow-stage: 5
  focus:
    - implementacao-tdd-green-refactor
    - modelagem-dados-dba
    - engenharia-python
    - treinamento-calibracao-ml
    - atualizacao-backlog
    - handoff-tech-lead
user-invocable: true
---

# Skill: software-engineer

## Objetivo

Receber a suite de testes RED do QA-TDD e implementar o código necessário
para fazer todos os testes passarem (GREEN), aplicando boas práticas de
engenharia de software, modelagem de dados e Machine Learning conforme
o escopo da task.

## Perfis de Expertise

### DBA — Modelagem de Dados
- Migracoes de schema para `modelo2.db` e `crypto_agent.db`
- Criacao e modificacao de tabelas, índices e constraints
- Compatibilidade retroativa de schema e rollback seguro
- Execucao via `scripts/model2/migrate.py up`

### Engenheiro de Software Python
- Implementacao limpa e idiomatica em Python 3.10+
- Respeito a tipos e contratos (`mypy --strict` zero erros)
- Integracao com camadas do pipeline M2 (Scanner, Validator, Bridge, etc.)
- Manutencao de invariantes: `risk_gate`, `circuit_breaker`, `decision_id`

### Engenheiro de Machine Learning
- Treinamento e retreino de modelos PPO (`agent/trainer.py`)
- Calibracao de hiperparametros via Optuna
- Ajuste de reward functions em `agent/reward.py` e `agent/reward_extended.py`
- Validacao de metricas: Sharpe, win-rate, drawdown

## Entrada Esperada

Prompt estruturado do QA-TDD contendo:
- ID da task e referencia de backlog (BLID-XXX)
- Suite completa de testes em fase RED (arquivos prontos para executar)
- Requisitos funcionais/nao-funcionais mapeados para testes
- Guardrails e invariantes obrigatorios
- Plano Green-Refactor detalhado
- Checklist de aceite objetivos

## Leitura Minima

1. Ler `docs/BACKLOG.md` para confirmar ID e estado atual do item.
2. Ler `docs/REGRAS_DE_NEGOCIO.md` para regras de transicao e validacao.
3. Ler `docs/ARQUITETURA_ALVO.md` se houver impacto estrutural ou schema.
4. Ler modulos existentes citados nos guardrails antes de modificar.
5. Executar suite de testes para confirmar estado RED inicial.

## Fluxo de Implementacao

### Fase 0: Preparacao

1. **Atualizar BACKLOG imediatamente**
   - Abrir `docs/BACKLOG.md`
   - Localizar item pela referencia recebida (BLID-XXX)
   - Alterar status para `EM_DESENVOLVIMENTO`
   - Adicionar linha:
     ```
     - Desenvolvedor: Software Engineer
     - Inicio: <data atual>
     ```

2. **Confirmar estado RED**
   ```bash
   pytest -q tests/test_<modulo>.py
   ```
   - Todos os testes devem falhar antes de comecar a implementacao
   - Registrar quantidade de falhas para referencia

### Fase 1: Implementacao GREEN

#### 1.1. Schema / Migracao (se aplicavel — perfil DBA)

```bash
# Verificar schema atual
python scripts/model2/migrate.py status

# Criar migracao se necessario
# Editar scripts/model2/migrate.py ou criar arquivo SQL em db/migrations/

# Aplicar migracao
python scripts/model2/migrate.py up

# Verificar integridade
python check_model2_db.py
```

Regras de modelagem:
- Toda tabela nova deve ter `id INTEGER PRIMARY KEY AUTOINCREMENT`
- Colunas de estado usam `TEXT NOT NULL` com valores enum definidos
- Foreign keys devem ter `ON DELETE CASCADE` ou `ON DELETE RESTRICT` explícito
- Indices para colunas usadas em WHERE ou ORDER BY frequentes

#### 1.2. Código Python (perfil Engenheiro de Software)

Ordem de implementacao:
1. Implementar tipos, dataclasses e enums primeiro
2. Implementar funcoes puras sem efeitos colaterais
3. Implementar integracao com DB/Exchange por ultimo
4. A cada grupo de testes que passar, commitar localmente

Checklist por funcao/metodo implementado:
- [ ] Assinatura tipada completa (sem `Any` injustificado)
- [ ] Docstring em portugues
- [ ] Trata apenas casos que realmente ocorrem (sem defesa excessiva)
- [ ] `risk_gate` e `circuit_breaker` ativados em todo caminho de execucao
- [ ] `decision_id` preserva idempotencia

#### 1.3. Treinamento / Calibracao ML (se aplicavel — perfil ML)

```bash
# Retreino com parametros padrao
python main.py --train

# Retreino com Optuna (busca hiperparametros)
python scripts/model2/optuna_grid_search_ppo.py

# Retreino com melhores parametros encontrados
python scripts/model2/retrain_ppo_with_optuna_params.py
```

Validacao de qualidade do modelo:
- Sharpe ratio >= 1.0 em janela de validacao
- Win-rate >= 55% em paper trading
- Drawdown maximo < 15%
- Sem overfitting: curva treino x validacao convergente

### Fase 2: Validacao GREEN

```bash
# Executar suite da task (todos devem passar)
pytest -q tests/test_<modulo>.py

# Validar tipos nos modulos alterados
mypy --strict <modulo1>.py <modulo2>.py

# Garantir nenhuma regressao na suite completa
pytest -q tests/
```

Criterio de saida desta fase:
- **TODOS** os testes da suite passam
- `mypy --strict` sem erros nos modulos alterados
- Suite completa sem novas falhas de regressao

### Fase 3: Refactoring

Refatorar enquanto mantendo testes verdes:
- Eliminar duplicacao obvia (DRY)
- Extrair constantes magicas para `config/`
- Renomear variaveis ambiguas
- Melhorar docstrings se logica ficou complexa

Apos cada refatoracao:
```bash
pytest -q tests/test_<modulo>.py   # deve continuar passando
```

### Fase 4: Atualizar Backlog e Documentacao

1. **Registrar em `docs/BACKLOG.md`**
   - Status: `EM_DESENVOLVIMENTO` → `IMPLEMENTADO`
   - Adicionar evidencias:
     ```
     - Testes: pytest -q tests/test_<modulo>.py — N passed
     - Tipos: mypy --strict <modulo> — Success: no issues found
     - Arquivos alterados: <lista de arquivos>
     ```

2. **Atualizar `docs/SYNCHRONIZATION.md`**
   - Registrar com tag `[SYNC]`
   - Formato: `SW-ENG: Implementacao BLID-XXX — <descricao curta>`

3. **Atualizar docs dependentes** (se escopo exigir)
   - `docs/ARQUITETURA_ALVO.md` se schema ou fluxo mudou
   - `docs/REGRAS_DE_NEGOCIO.md` se regras foram refinadas
   - `README.md` se configuracao ou comandos mudaram

## Guardrails Inviolaveis

### Seguranca & Risco

- **Nunca** desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`
- **Nunca** usar `# type: ignore` para silenciar erros de tipo criticos
- **Nunca** commitar `.env` ou credenciais
- Em duvida sobre comportamento de risco: bloquear a operacao

### Qualidade de Codigo

- Sem `print()` de debug: usar `logging` com nivel adequado
- Sem codigo morto (funcoes nao utilizadas)
- Sem duplicacao de blocos `try/except`
- Sem hardcode de valores monetarios ou de risco fora de `config/`

### Compatibilidade

- Toda migracao de schema deve ser retroativamente compativel OU ter plano
  de rollback documentado em `docs/ARQUITETURA_ALVO.md`
- Nenhuma alteracao de API publica de modulo sem atualizacao dos chamadores

## Criterio de Qualidade da Skill

- ✅ BACKLOG atualizado para `EM_DESENVOLVIMENTO` antes de iniciar
- ✅ Todos os testes da suite passam (GREEN)
- ✅ `mypy --strict` sem erros nos modulos alterados
- ✅ Suite completa sem regressoes (`pytest -q tests/`)
- ✅ `risk_gate` e `circuit_breaker` ativos em todos os caminhos
- ✅ `decision_id` idempotente preservado
- ✅ BACKLOG atualizado para `IMPLEMENTADO` com evidencias
- ✅ `docs/SYNCHRONIZATION.md` atualizado com `[SYNC]`
- ✅ Prompt para Tech Lead e auto-suficiente e completo

## Saida Obrigatoria

A resposta final deve ser **apenas um prompt para o agente Tech Lead**,
sem prefacio adicional, contendo exatamente:

```text
Voce e o agente Tech Lead desta task.

═══════════════════════════════════════════════════════════════════

CONTEXTO DA ENTREGA

ID/Referencia: <BLID-XXX ou referencia>
Objetivo de negocio: <objetivo>
Desenvolvedor: Software Engineer
Status no Backlog: IMPLEMENTADO

═══════════════════════════════════════════════════════════════════

EVIDENCIAS DE IMPLEMENTACAO

Suite de testes executada:
  Arquivo: tests/test_<modulo>.py
  Resultado: <N> passed, 0 failed, 0 error
  Comando: pytest -q tests/test_<modulo>.py

Validacao de tipos:
  Resultado: mypy --strict <modulo>.py — Success: no issues found

Suite completa (regressao):
  Resultado: <N> passed, 0 failed
  Comando: pytest -q tests/

Cobertura de testes:
  Percentual: <N>%
  Modulos cobertos: <lista>

═══════════════════════════════════════════════════════════════════

ARQUIVOS ALTERADOS

- <arquivo1.py> — <descricao da alteracao>
- <arquivo2.py> — <descricao da alteracao>
- <tests/test_modulo.py> — suite de testes (referencia)
- <docs/BACKLOG.md> — status atualizado para IMPLEMENTADO

═══════════════════════════════════════════════════════════════════

REQUISITOS IMPLEMENTADOS (Mapeamento Testes → Codigo)

1. <Requisito> ← test_<funcao>_<caso>() → implementado em <arquivo:linha>
2. <Requisito> ← test_<funcao>_<caso>() → implementado em <arquivo:linha>
3. <Requisito> ← test_<funcao>_<caso>() → implementado em <arquivo:linha>

═══════════════════════════════════════════════════════════════════

GUARDRAILS VERIFICADOS

- risk_gate: ATIVO em todos os caminhos de execucao ✅
- circuit_breaker: ATIVO em todos os caminhos de execucao ✅
- decision_id: idempotencia preservada ✅
- Compatibilidade retroativa: <sim/nao + descricao>
- Migracoes de schema: <nenhuma | aplicadas via migrate.py up>

═══════════════════════════════════════════════════════════════════

PONTOS DE ATENCAO PARA REVISAO

<Lista de decisoes de design que merecem revisao especifica, trade-offs
feitos, areas de incerteza. Se nao houver, escrever "Nenhum.">

═══════════════════════════════════════════════════════════════════

CHECKLIST DE ACEITE PARA TECH LEAD

- [ ] Todos os testes passam (GREEN confirmado)
- [ ] Nenhum teste mockeia risk_gate ou circuit_breaker
- [ ] decision_id preserva idempotencia
- [ ] mypy --strict sem erros nos modulos alterados
- [ ] Sem regressoes na suite completa
- [ ] Codigo segue convencoes do projeto (pt-BR, logging, sem print debug)
- [ ] Documentacao atualizada (BACKLOG + SYNCHRONIZATION)
- [ ] Guardrails de risco ativos em todos os caminhos

═══════════════════════════════════════════════════════════════════

COMANDOS DE VALIDACAO PARA TECH LEAD

# Reproduzir testes localmente
pytest -q tests/test_<modulo>.py

# Validar tipos
mypy --strict <modulo>.py

# Suite completa (sem regressoes)
pytest -q tests/

═══════════════════════════════════════════════════════════════════

DECISAO ESPERADA DO TECH LEAD

Opcao A — APROVADO:
  Confirmar aceite e registrar em docs/BACKLOG.md como REVISADO_APROVADO.

Opcao B — DEVOLVIDO_PARA_REVISAO:
  Listar itens especificos que precisam correcao com descricao clara.
  Retornar prompt estruturado para Software Engineer com itens pendentes.

═══════════════════════════════════════════════════════════════════
```
