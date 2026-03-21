---
name: backlog-development
description: |
  Use quando: Gerenciar tarefas do Backlog (criar, atualizar status, definir
  prioridade), evoluir o backlog com base em resultados de treinamento RL,
  feedback de convergencia e operacoes em mercado, manter docs/BACKLOG.md
  sincronizado com arquitetura do projeto.
  Workflow multi-step: validacao > transformacao > sincronizacao > auditoria.
  Saida: Atualizacoes em docs/, commits audataveis com tag [SYNC]/[FEAT].
applyTo:
  - docs/BACKLOG.md
  - docs/PRD.md
  - docs/*.md
  - .github/**
keywords:
  - backlog
  - tarefas
  - sprint
  - prioridade
  - status
  - docs
  - sincronizacao
  - resultados-rl
  - feedback-treinamento
  - operacoes-mercado
---

# Skill: Agente de Desenvolvimento do Backlog em Português

## Visão Geral

Este skill implementa um workflow multi-step para gerenciar o backlog do
projeto `crypto-futures-agent` mantendo integridade com:

- **docs/BACKLOG.md** (fonte única de verdade)
- **docs/PRD.md** (escopo e direcionamento do produto)
- **docs/SYNCHRONIZATION.md** (auditoria de mudanças)
- **iniciar.bat** (integração com automação)

**Princípios:** Português obrigatório, commits <= 72 chars ASCII, markdown
<= 80 chars, rastreabilidade 100%, segurança operacional preservada.

---

## Multi-Step Workflow

```
┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  ENTRADA    │→│  VALIDAÇÃO   │→│ TRANSFORMAÇÃO│→│  SINCRONIZAÇÃO
├─────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│ Comando     │ │ Estrutura    │ │ Gerar relat. │ │ Atualizar DB │
│ Azione      │ │ Dependências │ │ Propostas    │ │ Gerar commit │
│ Dados       │ │ Validar prts │ │ Mergear árvore│ │ Auditoria    │
└─────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
       ↓               ↓               ↓               ↓
  Parar se    Avisar efeitos    Confirmar output  Registrar em
  invalido    Sugerir corr.     Permitir editar   SYNC.md
  ou bloqueado laterais         Pedir aprovação
```

### PASSO 1 — Analisar Entrada

**O que fazer:**
1. Ler comando/ação do usuário (criar task, atualizar status, etc.)
2. Determinar tipo: CRUD, VALIDATE, REPORT, SYNC
3. Extrair parâmetros (nome task, sprint, prioridade, etc.)

**Checklist:**
- [ ] Comando está claro e bem formado?
- [ ] Parâmetros estão válidos (não vazios, sem chars inválidos)?
- [ ] Ação está documentada em copilot-instructions.md?

**Se BLOQUEADO:**
```
⚠️ Ação bloqueada: [RAZÃO]
   Sugestão: [ALTERNATIVA]
```

---

### PASSO 2 — Validar contra docs Arquiteturais + BACKLOG.md

**O que fazer:**
1. Carregar docs/BACKLOG.md como fonte única de verdade
2. Validar estrutura (seções, campos obrigatórios)
3. Validar alinhamento com docs arquiteturais (ADRS, ARQUITETURA_ALVO, etc)
4. Checar regras de negócio (prioridade, sprint, dependências)
5. Identificar efeitos colaterais (tasks impactadas, docs impactadas)

**Checklist - Estrutura (BACKLOG.md):**
- [ ] BACKLOG.md usa seções: Sprint, Status, Prioridade, Dependências?
- [ ] Cada task tem: ID, título, descrição, aceite, prioridade?
- [ ] Sprints estão em ordem cronológica?
- [ ] Não há IDs duplicadas?

**Checklist - Arquitetura (docs/ARQUITETURA_ALVO.md):**
- [ ] Implementação proposta segue ARQUITETURA_ALVO.md?
- [ ] Há violação de design patterns estabelecidos?
- [ ] Se há mudança arquitetural, evolução está documentada?
- [ ] Módulos/componentes estão alinhados com camadas esperadas?

**Checklist - Decisões Arquiteturais (docs/ADRS.md):**
- [ ] Task impacta algum ADR existente?
- [ ] Há conflito entre decisão proposta e ADR ativo?
- [ ] Se novo ADR necessário, foi criado (ou está em backlog)?
- [ ] ADRs relacionados foram revisados?

**Checklist - Dados (docs/MODELAGEM_DE_DADOS.md):**
- [ ] Implementação usa modelo de dados aprovado?
- [ ] Novas tabelas/schemas estão mapeadas?
- [ ] Se mudança no modelo, MODELAGEM atualizada?
- [ ] Migrações de banco estão documentadas?

**Checklist - Diagramas (docs/DIAGRAMAS.md):**
- [ ] Diagrama C4 será impactado?
- [ ] Fluxo de dados mudará?
- [ ] SLA/Performance diagrama será afetada?
- [ ] Se sim, diagrama será atualizado junto na task?

**Checklist - Regras de Negócio (docs/REGRAS_DE_NEGOCIO.md):**
- [ ] Task implementa ou muda alguma regra de negócio?
- [ ] Linguagem não-técnica (acessível) foi reavaliada?
- [ ] Validações de risco (sizing, stop, liquidação) preservadas?
- [ ] Se novo comportamento, regra foi criada/documentada?

**Checklist - PRD (docs/PRD.md):**
- [ ] Prioridade alinhada com PRD?
- [ ] Task alinhada aos demais DOCs?

**Checklist - Regras de Negócio (Geral):**
- [ ] Prioridade alinhada com PRD.md?
- [ ] Dependências existem e estão resolvidas?
- [ ] Status transitions valid? (Backlog→Planned→In Progress→Done)
- [ ] Task não viola regra de risco (security-first)?

**Se EFEITOS COLATERAIS detectados:**
```
⚠️ Impacto em outras tasks:
   - Task-X (sprint Y): [dependência]
   - Task-Z (sprint W): [integração]

Recomendação: Atualizar dependências em BACKLOG.md antes de prosseguir.
```

---

### PASSO 3 — Transformar: Ler → Sugerir → Gerar Propostas

**O que fazer:**
1. Gerar relatório visual (ASCII table ou Markdown)
2. Propor mudanças (upsert task, atualizar status, mover sprint)
3. Sugerir sincronizações com docs arquiteturais (ADRS, ARQUITETURA_ALVO, etc)
4. Listar docs que serão impactados e precisam atualização
5. Verificar que implementação será "percebida" por iniciar.bat

**Outputs Possíveis:**

#### 3a. CREATE task (nova tarefa)

```markdown
## Proposta: Criar Task

**ID:** BLID-XXX (gerado automaticamente)
**Título:** [Seu título]
**Sprint:** S-2 (Sprint Atual)
**Prioridade:** M (Média) | verify se OK
**Status:** Backlog
**Descrição:**
[Seu texto]

**Critérios de Aceite:**
- [ ] Criterion 1
- [ ] Criterion 2

**Dependências:**
- Nenhuma | ou listas aqui

### Efeitos Colaterais:
- TRACKER.md: atualizar contador "Total Tasks"
- docs/SYNCHRONIZATION.md: registrar novo BLID-XXX
- Docs Arquiteturais a Atualizar?
  - docs/ARQUITETURA_ALVO.md? [SIM/NÃO]
  - docs/ADRS.md? [SIM/NÃO, criar ADR-XXX?]
  - docs/BACKLOG.md? [SIM/NÃO]
  - docs/CHANGELOG.md? [SIM/NÃO]
  - docs/DIAGRAMAS.md? [SIM/NÃO]
  - docs/PRD.md? [SIM/NÃO]
  - docs/MODELAGEM_DE_DADOS.md? [SIM/NÃO]
  - docs/REGRAS_DE_NEGOCIO.md? [SIM/NÃO]

### CheckSum:
- ✓ Não viola prioridades existentes
- ✓ Não quebra dependências
- ✓ Alinhado com ARQUITETURA_ALVO.md
- ✓ Não conflita com ADRS ativo (ou novo ADR será criado)
- ✓ Implementação em Python/config será visível por iniciar.bat? SIM
- ✓ Docs arquiteturais serão sincronizados? [listar]

**Próximo passo:** Confirmar [Y/N]?
```

#### 3b. UPDATE task (mudar status/prioridade)

```markdown
## Proposta: Atualizar Task

**ID:** BLID-XXX
**Campo:** Status: Backlog → In Progress

**Antes:**
| Status | Sprint | Prioridade |
|--------|--------|-----------|
| Backlog | S-1 | M |

**Depois:**
| Status | Sprint | Prioridade |
|--------|--------|-----------|
| In Progress | S-1 | M |

### Impacto:
- Dependências: 2 tasks bloqueadas (BLID-YYY, BLID-ZZZ) podem desbloquear
- TRACKER.md: "In Progress" +1, "Backlog" -1

### Validação:
- ✓ Sprint válida
- ✓ Prioridade alinhada
- ✓ Sem ciclos de dependência

**Próximo passo:** Confirmar [Y/N]?
```

#### 3c. REPORT (relatório de progresso)

```markdown
## Relatório: Status do Backlog (Hoje)

**Resumo Executivo:**
- Total Tasks: 47
- Backlog: 15 | Planned: 12 | In Progress: 8 | Done: 12
- Progress NOW: 12/12 = 100% ✓ (sprint atual)
- Health: 🟢 On Track

**Por Sprint:**
| Sprint | Total | Backlog | Planned | In Progress | Done | Health |
|--------|-------|---------|---------|-------------|------|--------|
| S-1    | 12    | 0       | 0       | 0           | 12   | 🟢 Done |
| S-2    | 12    | 2       | 4       | 6           | 0    | 🟡 80% |
| S-3    | 15    | 13      | 2       | 0           | 0    | 🔴 13% |

**Top 3 Bloqueadores:**
1. BLID-AAA: [Task] — bloqueada por infra
2. BLID-BBB: [Task] — aguarda decisão
3. BLID-CCC: [Task] — dependência em BLID-0

**Sincronização com ROADMAP.md:**
| Milestone | Sprint | Status | Evidence |
|-----------|--------|--------|----------|
| MVP-1     | S-1    | 🟢 Done | v0.1 released 28FEV |
| v0.2      | S-2    | 🟡 80% | 10/12 features ready |
| v0.3      | S-3    | 🔴 13% | Planejamento em progresso |

**Insight:** Sprint S-2 está no caminho certo. S-3 precisa de ramp-up.
Recomendação: Iniciar planejamento S-3 detalhado na reunião de sprint.
```

#### 3d. SYNC (sincronizar docs)

```markdown
## Proposta: Sincronizar Documentação

**Arquivos Impactados:**
- docs/BACKLOG.md: [RAZÃO]
- docs/PRD.md: [RAZÃO]
- docs/SYNCHRONIZATION.md: [REGISTRO]
- docs/ARQUITETURA_ALVO.md: [SIM/NÃO, RAZÃO]
- docs/ADRS.md: [SIM/NÃO, RAZÃO]
- docs/DIAGRAMAS.md: [SIM/NÃO, RAZÃO]
- docs/MODELAGEM_DE_DADOS.md: [SIM/NÃO, RAZÃO]
- docs/REGRAS_DE_NEGOCIO.md: [SIM/NÃO, RAZÃO]

**Mudanças Propostas:**
1. Atualizar BACKLOG.md com status novo
2. Atualizar PRD.md quando houver impacto de escopo/produto
4. Atualizar DIAGRAMAS.md se flow/componentes mudaram
5. Atualizar ARQUITETURA_ALVO.md se evolução arquitetural ocorreu
6. Criar/atualizar ADRs se decisões novas (docs/ADRS.md)
7. Atualizar MODELAGEM_DE_DADOS.md se modelo mudou
8. Atualizar REGRAS_DE_NEGOCIO.md em linguagem acessível
9. Registrar em SYNCHRONIZATION.md com tag [SYNC] + timestamp

### Validação:
- ✓ Markdown lint passa (<80 chars per linha)
- ✓ Português correto
- ✓ Rastreabilidade: todas as mudanças com source/motivo
- ✓ Commit message ASCII puro (<= 72 chars): "[SYNC] Atualizado BACKLOG S-2 status"

**Próximo passo:** Confirmar e gerar commit [Y/N]?
```

---

### PASSO 4 — Sincronizar & Auditoria (com Lint Automático)

**O que fazer:**
1. Atualizar arquivo(s) em disk (BACKLOG.md, PRD.md, etc.)
2. **Validar markdown lint** — docs nascem com lint correto
3. Gerar commit com tag adequada ([SYNC], [FEAT], [DOCS])
4. Registrar em docs/SYNCHRONIZATION.md para auditoria
5. Verificar que iniciar.bat enxergará a mudança

**Checklist de Sincronização (com Lint):**
- [ ] Arquivo atualizado com proposta aprovada?
- [ ] UTF-8 válido, sem chars corrompidos?
- [ ] **Markdown Lint: PASSOU** (ver detalhes abaixo)
- [ ] Commit message: 72 chars ASCII puro (sem acentos), tag [SYNC]/[FEAT]/[DOCS]?
- [ ] docs/SYNCHRONIZATION.md foi registrado?
- [ ] Docs Arquiteturais sincronizados (se necessário)?
  - [ ] docs/ARQUITETURA_ALVO.md
  - [ ] docs/ADRS.md (novo ADR criado ou existente atualizado?)
  - [ ] docs/DIAGRAMAS.md (100% atualizado?)
  - [ ] docs/MODELAGEM_DE_DADOS.md (100% atualizado?)
  - [ ] docs/REGRAS_DE_NEGOCIO.md (linguagem acessível, 100% atualizado?)

---

### Validação Automática: Markdown Lint

**Regras obrigatórias (verificadas automaticamente):**

```
✓ Linhas <= 80 caracteres (exceto URLs/code blocks)
✓ Sem espaços em branco no final de linhas
✓ Títulos com # (não usar underlines)
✓ Listas com indentação consistente (2 espaços)
✓ Blocos de código com linguagem declarada (```python, ```markdown, etc)
✓ Sem múltiplos espaços em branco
✓ UTF-8 válido (sem caracteres corrompidos)
✓ Sem CRLF (Linux/Mac line endings)
```

**Quando o skill cria/atualiza doc:**

```
1. Gera mudança proposta
2. Formata com lint automático:
   - Garante linhas <= 80 chars
   - Remove espaços extras
   - Normaliza indentação
   - Valida encoding UTF-8
3. Valida com markdownlint
4. Se passou: ✓ Pronto para commit
5. Se falhou: ⚠️ Para e avisa problema
```

**Output esperado (após PASSO 4):**

```
✓ docs/BACKLOG.md — lint OK
✓ docs/TRACKER.md — lint OK
✓ docs/DIAGRAMAS.md — lint OK (se impactado)
✓ docs/SYNCHRONIZATION.md — lint OK

Commit: [SYNC] Atualizado BACKLOG S-2 status
```

**Se lint FALHAR:**

```
⚠️ ERRO: docs/REGRAS_DE_NEGOCIO.md linha 45
  Problema: Linha com 95 caracteres (max 80)

Ação do skill:
1. Reformata linha 45 (quebra em múltiplas linhas)
2. Tenta validar novamente
3. Se passou: continua
4. Se falhou ainda: PARA e mostra erro específico
```

**Teste manual (você pode rodar):**

```bash
# Validar arquivos específicos
markdownlint docs/BACKLOG.md docs/DIAGRAMAS.md

# Validar tudo
markdownlint *.md docs/*.md

# Corrigir automaticamente (alguns problemas)
markdownlint --fix docs/*.md
```

**Registr

o em SYNCHRONIZATION.md:**

```markdown
## [SYNC] 15-MAR-2026 14:30 — Agente Backlog

**Acao:** Criar BLID-062 (ML3: Early Exit Mecanismo)
**Arquivos:** docs/BACKLOG.md, docs/TRACKER.md, docs/SYNCHRONIZATION.md
**Commit:** [SYNC] Adicionado BLID-062 ML3 Early Exit Mecanismo
**Source:** Agente Backlog Development (SKILL)
**Motivo:** Melhorar seguranca do modelo em mercados extremos
**Impacto:** +1 task em S-3, ROADMAP.md atualizado

---
```

**Verificação iniciar.bat:**
- [ ] Se houver mudanças em `config/symbols.py` → lido por iniciar.bat?
- [ ] Se BACKLOG.md → visível por logging/monitoring?
- [ ] Se ROADMAP.md → propagado para README.md?

---

## Integração com Docs Arquiteturais (Essencial)

Toda task do backlog **DEVE** considerar os seguintes documentos antes de
implementação e sincronizá-los após conclusão. Isto **NÃO é opcional**.

### 1. docs/ARQUITETURA_ALVO.md

**Quando:** ANTES de qualquer implementação
**Ação:** Avaliar se task segue a arquitetura alvo

```
Checklist:
✓ Implementação proposta segue ARQUITETURA_ALVO.md?
✓ Não viola design patterns estabelecidos?
✓ Módulos/componentes alinhados com camadas esperadas?
✓ Se há mudança arquitetural, evolução está documentada?
```

**Saída esperada:**
- Aprovar (segue arquitetura)
- Requerer ajuste (antes de continuar)
- Registrar mudança em ARQUITETURA_ALVO.md (se evolução)

---

### 2. docs/ADRS.md (Architecture Decision Records)

**Quando:** ANTES de decisões, DURANTE implementação
**Ação:** Observar decisões ativas, respeitar, atualizar ou criar novas

```
Checklist:
✓ Task impacta algum ADR existente?
✓ Há conflito entre decisão proposta e ADR ativo?
✓ Decision é nova? Criar ADR-XXX com Status: Pending/Active
✓ ADRs relacionados revisados?
```

**Saída esperada:**
- **Se impacta ADR ativo**: Avisar. Considerar reconsiliar decisão.
- **Se nova decisão**: Criar ADR-XXX com Contexto, Opções, Decisão,
  Consequências
- **Se ADR já existe**: Referenciar em BLID (comentário "Related ADR: ADR-XXX")

---

### 3. docs/DIAGRAMAS.md

**Quando:** DURANTE desenvolvimento (continuar checando), APÓS conclusão
**Ação:** Manter 100% atualizado com decisões/fluxos do agente

```
Checklist:
✓ Diagrama C4 (Context/Containers/Components/Code)?
✓ Fluxo de dados será impactado? mudará?
✓ SLA/Performance diagrama será afetado?
✓ Se sim, diagrama será atualizado junto na SYNC?
```

**Saída esperada:**
- Atualizar diagramas C4 se componentes/fluxo mudar
- Atualizar diagrama de sequência se integração nova
- Atualizar diagrama de estado (se máquina de estado mudar)
- Commitar junto com código ([FEAT] atualiza DIAGRAMAS.md)

---

### 4. docs/MODELAGEM_DE_DADOS.md

**Quando:** ANTES se novo schema, APÓS mudanças de dados
**Ação:** Manter 100% atualizado com novo modelo de dados

```
Checklist:
✓ Task implementa nova estrutura de dados?
✓ Novas tabelas/schemas/fields mapeados?
✓ Se mudança no modelo, MODELAGEM atualizada?
✓ Migrações de banco documentadas?
```

**Saída esperada:**
- Adicionar novo schema em MODELAGEM_DE_DADOS.md (ERD, campos, tipos)
- Documentar migration script (como foram migrados dados antigos?)
- Atualizar índices/constraints
- Versionar schema (v1.0 → v1.1 → v2.0)

---

### 5. docs/REGRAS_DE_NEGOCIO.md

**Quando:** ANTES se nova regra, APÓS implementação
**Ação:** Manter 100% atualizado com regras, decisões, linguagem acessível

```
Checklist:
✓ Task implementa ou muda regra de negócio?
✓ Linguagem é não-técnica (acessível, sem jargão)?
✓ Validações de risco (sizing, stop, liquidação) preservadas?
✓ Se novo comportamento, regra foi criada/documentada?
```

**Saída esperada:**
- Adicionar regra em formato legível: "SE [condição], ENTÃO [ação]"
- Incluir exemplos (caso concreto)
- Não usar siglas técnicas (ex: "PPO" explicar como "algoritmo de
  otimização")
- Incluir "Por quê" (justificativa de négocio)
- Listar trade-offs se houver

**Exemplo ruim (❌ técnico):**
```
PPO updates leverage window w/ reward shaping via KL divergence.
```

**Exemplo bom (✓ acessível):**
```
O agente aprende a ajustar quantidades de operação levando em conta:
- Risco atual (não ultrapassar alavancagem máxima de 5x)
- Histórico de ganhos/perdas (aprender com erros)
- Segurança (sempre manter margem de 10% para cobrir variações)
```

---

## Fluxo Integrado (4 Passos + Docs Arquiteturais)

```
┌─────────────────────────────┐
│ ENTRADA: Task a fazer       │
└────────────┬────────────────┘
             ↓
┌─────────────────────────────────────────────────────────┐
│ PASSO 2: VALIDAÇÃO                                      │
│ ├─ Estrutura BACKLOG.md? ✓                              │
│ ├─ ARQUITETURA_ALVO.md? ✓ (aprova antes de começar)   │
│ ├─ ADRS.md? ✓ (respeita decisões, cria nova se preciso) │
│ ├─ DIAGRAMAS? ✓ (será afetado?)                        │
│ ├─ MODELAGEM? ✓ (novo schema?)                         │
│ └─ REGRAS_DE_NEGOCIO? ✓ (nova regra?)                  │
└────────────┬────────────────────────────────────────────┘
             ↓
┌──────────────────────────────┐
│ PASSO 3: PROPOSTAS           │
│ Listar todos os docs a sync. │
│ Pedir aprovação              │
└────────────┬─────────────────┘
             ↓
┌────────────────────────────────────────────────────────┐
│ PASSO 4: SINCRONIZAÇÃO (Arquiteturais + Outros)        │
│ ├─ BACKLOG.md                                          │
│ ├─ TRACKER.md                                          │
│ ├─ SYNCHRONIZATION.md                                  │
│ ├─ ARQUITETURA_ALVO.md (se evoluiu)                    │
│ ├─ ADRS.md (novo ADR criado? existente atualizado?)    │
│ ├─ DIAGRAMAS.md (100% atualizado)                      │
│ ├─ MODELAGEM_DE_DADOS.md (100% atualizado)             │
│ └─ REGRAS_DE_NEGOCIO.md (100% atualizado, acessível)   │
│                                                         │
│ Commit: [FEAT]/[SYNC] com referência a docs            │
│ Verificar: iniciar.bat enxergará?                      │
└────────────┬──────────────────────────────────────────┘
             ↓
      ✓ PRONTO
```

---

## Evolucao do Backlog Baseada em Resultados

O agente **toma decisoes de evolucao do backlog** com base em 3 pilares:

### 1. Resultados de Treinamento (RL Agent)

**Metricas monitoradas:**
- Convergencia do modelo (loss diminuindo?)
- Estabilidade do reward (variance aceitavel?)
- Melhoria de Sharpe ratio (estavel acima de 2.0?)
- Drawdown maximo (dentro de controles de risco?)

**Decisoes acionadas:**
```
IF reward em plateau por N episodios:
  → Criar BLID: "Investigar convergencia + melhorar reward shaping"

IF loss aumenta (overfitting):
  → Criar BLID: "Adicionar regularizacao ou reduzir complexity"

IF Sharpe < 1.5:
  → Criar BLID: "Revisar validacoes de risco + rebalancear alavancagem"
```

### 2. Feedback de Operacao em Mercado (Live/Backtest)

**Metricas monitoradas:**
- P&L realizado (positivo/negativo/volatilidade?)
- Numero de trades errados (slippage, delay?)
- Violacoes de controle de risco (stop, liquidacao?)
- Taxa de execucao (ordens aceitas?)

**Decisoes acionadas:**
```
IF P&L < -2% em D:
  → Criar BLID: "Revisar decisoes de entrada/saida + validar stops"

IF muitos trades fecham ao contrario:
  → Criar BLID: "Debug ordem de execucao + melhorar latencia"

IF risco realizado > risco permitido:
  → Criar BLID urgente: "Ajuste emergencial de alavancagem"
```

### 3. Qualidade do Processamento (Dados + Sinais)

**Metricas monitoradas:**
- Latencia de dados (Binance delay?)
- Qualidade de precos (gaps, spikes?)
- Sinais com ruidol (taxa de sinais falsos?)
- Cobertura de pares (quantos pares ativos?)

**Decisoes acionadas:**
```
IF dados chegam com delay > 100ms:
  → Criar BLID: "Otimizar collector.py para reducao de latencia"

IF muitos sinais falsos (high slippage em execucao):
  → Criar BLID: "Mel ho rar sinal reward + adicionar filtros"

IF novo par tradeable encontrado:
  → Criar BLID: "Adicionar par novo em symbols.py + testar"
```

### Workflow de Evolucao Automatizada

```
┌──────────────────────────────────────────────┐
│ Agente RL roda + coleta metricas             │
│ - loss, reward, Sharpe, P&L, delay, etc      │
└───────────┬──────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────┐
│ Analisar limites / thresholds                │
│ - Convergiou? OK                             │
│ - Piora? Problematico                        │
│ - Estavel? Manter ou melhorar?               │
└───────────┬──────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────┐
│ Tomar decisao                                │
│ - Nenhuma acao: continuar                    │
│ - Criar BLID: investigar/melhorar            │
│ - Criar BLID urgent: parar/ajustar           │
└───────────┬──────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────┐
│ Se criar BLID: usar skill backlog-development│
│ 1. Propor task com motivo claro (metrica)    │
│ 2. Sprint: hoje ou sprint proxima?           │
│ 3. Prioridade: baseada em impacto no risco   │
│ 4. Commit: mensagem explica resultado RL     │
└───────────┬──────────────────────────────────┘
            ↓
      ✓ BACKLOG EVOLUI
```

### Exemplo: Mensagem de Commit com Resultado RL

**Cenario:** Sharpe ratio caiu abaixo de 1.5, precisa investigacao.

**Commit esperado (sem acentos/emojis):**
```
[FEAT] Investigar queda Sharpe 1.5 - reward shaping

Resultado RL: Sharpe caiu de 2.1 para 1.45 em ultimas 500 epocas.
Hipotese: reward shaping nao captura volatilidade adequadamente.

Task BLID-XYZ criada para:
- Analisar distribuicao de rewards
- Ajustar KL penalty se necessario
- Testar novas combinacoes de weight

Metrica objetivo: Sharpe > 2.0 em proximas 1000 epocas.
```

---

## Padrões e Templates

### Template: Task Básica (Markdown)

```markdown
### BLID-XXX: [Título Descritivo da Task]

**Sprint:** S-N
**Prioridade:** M (Alta | Média | Baixa)
**Status:** Backlog | Planned | In Progress | Done | WontDo
**Assignee:** [nome] ou [indefinido]

**Descrição:**
Uma descrição clara com:
- Contexto do problema
- Por que isso importa para o projeto
- Alinhamento com ARQUITETURA_ALVO.md?

**Critérios de Aceite (DoD):**
- [ ] Código implementado e testado (pytest >= 95%)
- [ ] Documentação atualizada (comentários + docstrings)
- [ ] Validado contra ARQUITETURA_ALVO.md
- [ ] ADRS revisados (ou novo ADR criado se decisão)
- [ ] Commit message com tag [FEAT]/[FIX]/[DOCS]
- [ ] Sincronizado em docs/SYNCHRONIZATION.md
- [ ] Docs Arquiteturais atualizados:
  - [ ] DIAGRAMAS.md (se flow/componentes mudaram)
  - [ ] MODELAGEM_DE_DADOS.md (se dados mudaram)
  - [ ] REGRAS_DE_NEGOCIO.md (se regra nova/mudou)
  - [ ] ADRS.md (se decisão arquitetural nova)

**Dependências:**
- BLID-YYY (task anterior, mesma feature)
- BLID-ZZZ (validação de risco)

**Impacto Arquitetural:**
- ARQUITETURA_ALVO.md: [SIM/NÃO]
- ADRS: [SIM/NÃO, listar]
- DIAGRAMAS: [SIM/NÃO]
- MODELAGEM: [SIM/NÃO]
- REGRAS: [SIM/NÃO]

**Notas Adicionais:**
[Se houver]
```

### Template: Pull Request (Git)

```
Título (72 chars ASCII max):
[TAG] Descricao breve

Descrição:
Resolve #123 (GitHub Issue)
Relacionado a BLID-XXX

## O que muda:
- [Item 1]
- [Item 2]

## Testing:
- pytest -q [passou]
- Backtest com dados 28FEV-14MAR OK

## Docs:
- [X] docs/BACKLOG.md atualizado
- [X] docs/SYNCHRONIZATION.md registrado
- [X] Commit message com tag

## Checklist Segurança:
- [X] Validações de risco preservadas
- [X] Fallback conservador se falhar
```

---

## Validações Obrigatórias (100% Automatizadas)

### Markdown Lint (Obrigatório)

Toda doc criada/atualizada **nasce com lint correto**:

```
✓ Linhas <= 80 caracteres
✓ Sem espaços no final de linhas
✓ Indentação consistente (2 espaços)
✓ Code blocks com linguagem declarada
✓ UTF-8 válido (nenhum char corrompido)
✓ Títulos com # (consistente)
✓ Sem múltiplos espaços em branco
```

**Antes de confirmar a proposta,** skill **sempre:**
1. Antecipa problemas de lint
2. Sugere formatação correta
3. Valida com `markdownlint`
4. **Bloqueia se lint falhar** (avisa erro específico)

---

**Nunca faça:**

```
❌ Remover controles de risco (sizing, alavancagem, stop, liquidação)
❌ Deixar docs desatualizadas vs código
❌ Docs nascerem com lint errado (❌ > 80 chars, espaços extras, etc)
❌ Implementar sem revisar ARQUITETURA_ALVO.md primeiro
❌ Ignorar ADRS existentes ou criar conflitos com decisões ativas
❌ Deixar DIAGRAMAS desatualizado com novas decisões
❌ Deixar MODELAGEM_DE_DADOS desatualizado com mudanças de schema
❌ Deixar REGRAS_DE_NEGOCIO ambíguo ou em linguagem técnica
❌ Usar non-ASCII ou chars corrompidos em commits
❌ Task sem Critérios de Aceite
❌ Sprint sem dependências documentadas
❌ Criar feature "nice-to-have" sem solicitação
❌ Alterar arquitetura para resolver problema local
```

**Sempre faça:**

```
✓ Ler docs/BACKLOG.md primeiro (fonte unica de verdade)
✓ Revisar ARQUITETURA_ALVO.md antes de implementar
✓ Consultar ADRS.md para decisoes ja tomadas
✓ Verificar DIAGRAMAS.md (sera impactado?)
✓ Verificar MODELAGEM_DE_DADOS.md (mudancas de schema?)
✓ Verificar REGRAS_DE_NEGOCIO.md (regra nova/mudanca?)
✓ Garantir docs nascem com markdown lint 100% OK
✓ Rodar markdownlint antes de commit (validacao local)
✓ Mensagens em Portugues ASCII puro (sem acentos/emojis)
✓ Atualizar docs/SYNCHRONIZATION.md (auditoria)
✓ Incluir tag em commit message ([SYNC], [FEAT], [DOCS], [FIX], [TEST])
✓ Validar dependências (não criar ciclos)
✓ Testar impacto em iniciar.bat (implementação será visível?)
✓ Manter Português em diálogos, comentários, logs
✓ Descrever "por quê" além do "o quê"
✓ Manter linguagem não-técnica em REGRAS_DE_NEGOCIO.md (acessível)
```

---

## Integração com iniciar.bat

`iniciar.bat` é o automático que percebe mudanças do projeto. Para que
tarefas do backlog criem efeito observável:

**Coordenação:**

1. **Mudanças em `config/symbols.py`** → lidas por iniciar.bat na próxima
   execução (symbols de trading)
2. **Mudanças em `agent/`, `execution/`, `risk/`** → visíveis por pytest +
   logging do boot
3. **Mudanças em `docs/`** → registradas em SYNCHRONIZATION.md (auditoria)

**Auto-discovery:**

- Task com tag `[FEAT]` em `agent/` ou `risk/` → será compilada + testada
- Task com tag `[DOCS]` → sincronizada no README.md + PRD.md
- Task com tag `[SYNC]` → registrada em SYNCHRONIZATION.md automaticamente

---

## Fluxo Recomendado (Resumido)

1. **Usuário inicia:** "Preciso criar task de feature X"
2. **Skill responde:**
   - ✓ Validação vs BACKLOG.md
   - ✓ Proposta visual (table + efeitos colaterais)
   - ✓ Convite para confirmar
3. **Usuário confirma:** "Sim, criar"
4. **Skill executa:**
   - Atualiza BACKLOG.md
  - Atualiza PRD.md (quando houver impacto)
   - Registra em SYNCHRONIZATION.md
   - Gera commit [FEAT] + mensagem ASCII
5. **Resultado:** Task criada, auditável, sincronizada com iniciar.bat

---

## Exemplos de Prompt

Abra VS Code chat (`Ctrl+Shift+I`), digite `/` e procure por
`backlog-development`:

```
/backlog-development Criar task para implementar Early Exit em ML3

/backlog-development Qual é o status atual de S-2? Gerar relatório

/backlog-development Sincronizar docs — BACKLOG.md foi atualizado

/backlog-development BLID-042 está bloqueada? Verificar dependências

/backlog-development Mover BLID-055 de S-3 para S-2 (reprioritizar)
```

---

## Relacionado

Considere estes skills/customizações quando terminar:

1. **Skill: Code Review Checklist** — Validar PRs com critérios de aceite
2. **Skill: Test Coverage Dashboard** — Monitorar cobertura pytest
3. **.instructions.md** — Padrões Python específicos para `agent/`, `risk/`
4. **Hooks** — Auto-format commits com tag [SYNC] ao salvar BACKLOG.md

---

## Troubleshooting

### "Task não aparece em iniciar.bat"

- Verificar: task está em `config/` ou `agent/` ou `risk/`?
- Checklist: arquivo Python foi atualizado com tag [FEAT]?
- Solução: Executar `pytest -q` para compilar novos módulos

### "docs/BACKLOG.md está desincronizado"

- Verificar: existe uncommitted edits?
- Solução: rodar SYNC (PASSO 4) para registrar em SYNCHRONIZATION.md
- Fallback: git diff docs/BACKLOG.md para ver o que mudou

### "Muitas dependências circulares"

- Parar. É um sinal de design ruim.
- Ação: Quebrar task em sub-tasks menores, ou reconsiderar prioridades
- Validação: Usar grafo de dependências (ASCII) para visualizar

---

Ver também: [copilot-instructions.md](../../copilot-instructions.md),
[docs/BACKLOG.md](../../docs/BACKLOG.md),
[docs/SYNCHRONIZATION.md](../../docs/SYNCHRONIZATION.md)
