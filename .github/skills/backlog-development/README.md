---
name: backlog-development-readme
description: |
  Guia de inicio rapido para o skill backlog-development.
  Gerencia tarefas com evolucao automatizada baseada em resultados RL,
  feedback de treinamento e operacoes em mercado.
---

# Skill: Agente de Desenvolvimento do Backlog em Português 🚀

## O Que E?

Um **skill interativo** para gerenciar tarefas, sprints e evolucao do
projeto `crypto-futures-agent` mantendo tudo sincronizado, auditavel e em
portugues.

O skill e acionado por:
- Comando manual do usuario (criar task, atualizar status)
- **Agente RL** (com base em metricas de convergencia, Sharpe, P&L, delay)
- **Feedback de treinamento** (loss, reward, estabilidade)
- **Operacoes em mercado** (resultado real, violacoes, qualidade de sinal)

Pense nele como um assistente experiente que:
- Entende a estrutura de BACKLOG.md
- Valida dependencias e prioridades
- Gera propostas antes de mudar nada
- Evolui o backlog com base em resultados RL/treinamento/mercado
- Sincroniza docs/ automaticamente
- Registra tudo em SYNCHRONIZATION.md (auditoria)
- Usa mensagens em Portugues ASCII puro (sem acentos/emojis)

---

## Como Usar (Quick Start)

### 1. Abrir VS Code Chat
```
Windows/Linux: Ctrl+Shift+I
Mac: Cmd+Shift+I
```

### 2. Procurar o Skill
```
Tipo "/" no input
Procure por "backlog-development"
Clique quando aparecer
```

### 3. Digitar o Comando
```
/backlog-development Criar task para implementar Early Exit

/backlog-development Qual é o status atual de S-2?

/backlog-development Sincronizar docs — BLID-050 foi concluída
```

### 4. Confirmar Proposta
O skill vai:
1. **Validar** sua entrada vs docs/BACKLOG.md
2. **Propor** mudanças em Markdown visual
3. **Pedir aprovação** [Y/N]
4. **Executar** e registrar commit

---

## Casos de Uso Comum

| Preciso fazer... | Comando | Resultado |
|------------------|---------|-----------|
| Criar nova task | `Criar task: [descrição]` | BLID-XXX criado em BACKLOG.md |
| Mover task para In Progress | `Mover BLID-062 para "In Progress"` | Status atualizado + TRACKER.md |
| Ver status do backlog | `Status do backlog hoje` | Relatório completo com gráfico |
| Task está bloqueada? | `BLID-042 está bloqueada?` | Análise de dependências |
| Sincronizar docs | `Sincronizar BACKLOG.md` | Atualizar TRACKER + ROADMAP |
| Encontrar problemas | `Validar integridade BACKLOG.md` | Ciclos, orphaned refs, etc |
| Reprioritizar | `Mover BLID-055 de S-3 para S-2` | Sprint mudado + impacto analisado |

---

## Arquivos do Skill

```
.github/skills/backlog-development/
├── SKILL.md               ← Principal: Workflow + templates + validações
├── examples.md            ← 5 exemplos práticos com inputs/outputs
├── templates.md           ← Templates prontos copy/paste
└── README.md              ← Este arquivo
```

**Dica:** Abra [SKILL.md](./SKILL.md) para entender o workflow multi-step
completo (Entrada → Validação → Transformação → Sincronização).

**Dica 2:** Veja [examples.md](./examples.md) para casos reais: criar task,
atualizar status, gerar relatório, sincronizar.

**Dica 3:** Use [templates.md](./templates.md) quando criar uma task nova.
Copy/paste e customize.

---

## Workflow em 4 Passos

```
┌──────────────────────────────────────────────────────────────┐
│           ENTRADA: O que você quer fazer?                    │
│  Criar task / Atualizar status / Gerar relatório / etc       │
└──────────────┬───────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────────────┐
│      VALIDAÇÃO: Checkar vs docs/BACKLOG.md                   │
│  Estrutura? Dependências? Ciclos? Regras de negócio? OK?    │
└──────────────┬───────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────────────┐
│    TRANSFORMAÇÃO: Gerar proposta visual                       │
│  Antes/Depois | Impacto | Validações | Checklist             │
│          ⟨ Pedir aprovação ao usuário ⟩                    │
└──────────────┬───────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────────────┐
│  SINCRONIZAÇÃO: Executar + Auditoria                         │
│  1. Atualizar arquivo                                         │
│  2. Gerar commit message [TAG] ...                           │
│  3. Registrar em docs/SYNCHRONIZATION.md                      │
│  4. Verificar iniciar.bat vai enxergar                       │
└──────────────────────────────────────────────────────────────┘
```

Veja [SKILL.md § Multi-Step Workflow](./SKILL.md#multi-step-workflow) para
detalhes.

---

## ✨ Markdown Lint Automático

**Toda doc criada/atualizada nasce com lint 100% OK:**

```
✓ Linhas <= 80 caracteres
✓ Sem espaços extras no final
✓ Indentação consistente (2 espaços)
✓ Code blocks com linguagem declarada (```python, ```markdown, etc)
✓ UTF-8 válido (nenhum char corrompido)
✓ Títulos com # (nunca underlines)

Validação acontece AUTOMATICAMENTE:
→ Você propõe
→ Skill formata + valida lint
→ Você confirma
→ Commit saiu com lint OK ✓
```

Você **nunca** recebe proposta com lint errado. Se houver problema, skill
avisa exatamente qual é e corrige automaticamente.

---

## Principios (Leia isto!)

Estes principios do projeto **NUNCA sao contornaveis**:

```
\u2713 Portugues obrigatorio (codigo, docs, logs, comentarios)
\u2713 Mensagens: 100% ASCII puro (SEM acentos, emojis ou chars corrompidos)
\u2713 Seguranca operacional: Nunca remover validacoes de risco
\u2713 Sincronizacao: Toda mudanca em codigo > docs ATUALIZADA
\u2713 Arquitetura: Antes de implementar > revisar ARQUITETURA_ALVO.md
\u2713 Decisoes: Observar, respeitar, atualizar ou criar ADRS.md
\u2713 Diagramas: Manter 100% sincronizado (DIAGRAMAS.md)
\u2713 Dados: Manter 100% sincronizado (MODELAGEM_DE_DADOS.md)
\u2713 Regras: Manter 100% sincronizado, linguagem acessivel
           (REGRAS_DE_NEGOCIO.md)
\u2713 Evolucao: Backlog evolui com base em resultados RL/treinamento/mercado
\u2713 Auditoria: Toda mudanca > registrada em docs/SYNCHRONIZATION.md
\u2713 Estrutura: Commits <= 72 chars ASCII, markdown <= 80 chars
\u2713 Rastreabilidade: Decisoes criticas sao audataveis
```

Se violado, o skill vai **blocar** a acao e sugerir correcao.

---

## Integração com iniciar.bat

O arquivo **iniciar.bat** é o automático que percebe mudanças.

Quando você cria uma task:
- ✓ Em `config/` → será lida por iniciar.bat na próxima execução
- ✓ Em `agent/`, `risk/`, `execution/` → compilada + testada por pytest
- ✓ Em `docs/` → registrada em SYNCHRONIZATION.md

O skill **sempre verifica** que sua implementação será visível.

---

## Validações Automáticas

O skill **valida automaticamente**:

```
Estrutura
├─ Cada task tem ID (BLID-XXX)?
├─ Todos os campos obrigatórios presentes?
├─ Sprints em ordem cronológica?
├─ IDs não duplicadas?
└─ Markdown válido (<80 chars/linha)?

Dependências
├─ Task listada existe?
├─ Há ciclos? (A→B→C→A) ⚠️ BLOQUEADO
├─ Ordem de execução é viável?
└─ Sprint sem dependências futuras?

Regras de Negócio
├─ Prioridade alinhada com ROADMAP?
├─ Status transition válida?
├─ Não viola validações de risco?
└─ Implementação será visível por iniciar.bat? ✓

Português
├─ Sem ASCII corrompido?
├─ Docs em português?
├─ Commits com tag [FEAT]/[FIX]/[SYNC]/[DOCS]/[TEST]?
└─ Max 72 chars (commits), 80 chars (markdown)?
```

Se algo falhar, o skill **para**, avisa o problema, e sugere correção.

---

## Exemplos Rápidos

### Exemplo 1: Criar Task (3 linhas)
```
/backlog-development Criar task para EMA dinâmico em ML2
Sprint: S-2, Prioridade: Alta
Deps: BLID-047 (aprendizado período)
```

**Output:** Proposta → Você confirma [Y] → BLID-063 criado ✓

---

### Exemplo 2: Status (1 linha)
```
/backlog-development Qual é o status do backlog hoje?
```

**Output:** Relatório com gráfico ASCII + recomendações ✓

---

### Exemplo 3: Sincronizar (1 linha)
```
/backlog-development BLID-050 foi concluída, sincronizar
```

**Output:** Confirma → Atualiza BACKLOG + TRACKER + ROADMAP ✓

Veja [examples.md](./examples.md) para casos mais complexos.

---

## Troubleshooting

### "Skill não aparece no chat"

1. Abra comando palette: `Ctrl+Shift+P`
2. Search: `Developer: Reload Window`
3. Aguarde carregar
4. Tente `/backlog-development` novamente

### "Erro: Dependencies circulares encontradas"

É um sinal de design ruim. **Parar aqui.**

Ação:
1. Visualizar grafo (ASCII) que o skill gera
2. Redefinir escopos das tasks ou quebrar em sub-tasks
3. Consultar [SKILL.md § Troubleshooting](./SKILL.md#troubleshooting)

### "Arquivo não sincroniza com iniciar.bat"

Verificar:
- [ ] Arquivo está em `config/`, `agent/`, ou `risk/`?
- [ ] Foi feito commit com tag [FEAT]?
- [ ] `pytest -q` passa?

Se sim, é ok — iniciar.bat lerá na próxima execução.

---

## 🏗️ Docs Arquiteturais (Essenciais)

O skill valida e sincroniza continuamente com **5 documentos arquiteturais**:

| Doc | Propósito | Quando | Ação |
|-----|-----------|--------|------|
| [ARQUITETURA_ALVO.md](../../docs/ARQUITETURA_ALVO.md) | Alvo de design | **Antes** de implementar | Revisar se segue |
| [ADRS.md](../../docs/ADRS.md) | Decisões arquiteturais | **Antes** e **durante** | Observar, respeitar, criar novos |
| [DIAGRAMAS.md](../../docs/DIAGRAMAS.md) | C4, fluxos, SLA | **Durante** | Manter 100% atualizado |
| [MODELAGEM_DE_DADOS.md](../../docs/MODELAGEM_DE_DADOS.md) | Schema, ERD, migrações | **Antes** (novo schema) | Manter 100% atualizado |
| [REGRAS_DE_NEGOCIO.md](../../docs/REGRAS_DE_NEGOCIO.md) | Regras, linguagem acessível | **Antes** (nova regra) | Manter 100% atualizado |

**Workflow Integrado:**
```
Task    →  [Revisar ARQUITETURA_ALVO + ADRS]  →  [Implementar]
         →  [Atualizar DIAGRAMAS + MODELAGEM + REGRAS]  →  [SYNC]
```

Ver [SKILL.md § Integração com Docs Arquiteturais](./SKILL.md#integração-com-docs-arquiteturais-essencial) para detalhes.

---

1. **Este arquivo (README)** — Overview (você está aqui)
2. **[SKILL.md](./SKILL.md)** — Workflow completo + validações + templates
3. **[examples.md](./examples.md)** — 5 cases práticos com input/output
4. **[templates.md](./templates.md)** — Copy/paste para criar tasks
5. **[docs/BACKLOG.md](../../docs/BACKLOG.md)** — Fonte única de verdade

---

## FAQ

**P: O skill modifica BACKLOG.md diretamente?**
R: Não. Ele propõe mudanças, você confirma, ele executa.
Sempre reversível se der problema (git revert).

---

**P: Preciso de GitHub Issues?**
R: Não. BACKLOG.md é (suficiente) a fonte única de verdade.
Mas se usá-las, o skill pode sincronizar (BLID ↔ #issue).

---

**P: Quando devo usar [FEAT] vs [SYNC] vs [DOCS]?**
R:
- `[FEAT]` — Nova implementacao (code + testes)
- `[FIX]` — Bug fix
- `[SYNC]` — Atualizar status/prioridade (sem code)
- `[DOCS]` — So documentacao
- `[TEST]` — Testes, sem codigo novo

---

**P: Por que mensagens sao ASCII puro (sem acentos)?**
R: Git e systems antigos podem corromper acentos/emojis:
   Exemplo ruim (EVITAR):
   `[SYNC] Markdown Lint obrigatorio — docs nascem com lint OK`
   Fica corrompido:
   `[SYNC] Markdown Lint obrigatorio ÔÇö docs nascem com lint OK`

   Solucao: usar ASCII puro:
   `[SYNC] Markdown Lint obrigatorio - docs nascem com lint OK`

---

**P: Como o agente RL evolui o backlog automaticamente?**
R: Com base em 3 metricas contantes:
   1. **Convergencia RL**: Sharpe < 1.5? Cria BL ID investigacao
   2. **Operacoes mercado**: P&L ruim? Cria BLID debug
   3. **Sinais/dados**: Latencia > 100ms? Cria BLID otimizacao

   Ver secao "Evolucao do Backlog" em SKILL.md para detalhes.

---

**P: Posso ter BLIDs não cronológicas (ex: BLID-062, pular 5)?**
R: Sim! IDs não precisam ser contíguas. Ex: BLID-050, BLID-062, BLID-055.

---

**P: O que é docs/SYNCHRONIZATION.md?**
R: Auditoria de TODAS as mudanças em docs/.
Registro com timestamp, motivo, impacto.
Essencial para rastreabilidade.

---

## Precisa de Ajuda?

- Dúvida sobre workflow? → Ler [SKILL.md](./SKILL.md)
- Exemplos práticos? → Ler [examples.md](./examples.md)
- Template para minha task? → Copiar em [templates.md](./templates.md)
- Estrutura do projeto? → Ver [copilot-instructions.md](../../.github/copilot-instructions.md)

---

**Última atualização:** 15-MAR-2026
**Versão skill:** 1.0 (Initial Release)
**Compatibilidade:** Python 3.9+, VS Code Insiders+
