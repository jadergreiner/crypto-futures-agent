---
name: backlog-examples
description: |
  Exemplos práticos de uso do skill backlog-development.
  Mostre casos de uso comuns: criar task, atualizar status, gerar relatório,
  sincronizar docs.
---

# Exemplos: Agente Backlog Development

## Exemplo 1 — Criar Task Nova

**Prompt do Usuário:**
```
/backlog-development Criar task: Implementar EMA com Período Dinâmico (ML2)
Sprint: S-2, Prioridade: Alta
Descrição: Explorar se período do EMA pode ser ajustado dinamicamente via
aprendizado de recompensa. Impacto em signal_reward.py.
```

**Resposta Esperada:** [ver PASSO 3a do SKILL.md]

```markdown
## Proposta: Criar Task

**ID:** BLID-063
**Título:** Implementar EMA com Período Dinâmico
**Sprint:** S-2
**Prioridade:** Alta
**Status:** Backlog
**Descrição:**
Explorar se período do EMA pode ser ajustado dinamicamente via aprendizado
de recompensa. Impacto em `signal_reward.py`.

**Critérios de Aceite:**
- [ ] Algoritmo de ajuste de período implementado em agent/signal_reward.py
- [ ] Testes unit com cobertura >= 95% (pytest)
- [ ] Backtest com dados 28FEV-14MAR mostra melhoria de Sharpe >= 2%
- [ ] Docs atualizada em docs/SYNCHRONIZATION.md

**Dependências:**
- BLID-047: Mecanismo de Aprendizado de Período (concluído em S-1)

### Efeitos Colaterais:
- TRACKER.md: +1 task em S-2 Backlog
- ROADMAP.md: v0.2 progresso muda de 10/12 para 11/12
- docs/SYNCHRONIZATION.md: registrar novo BLID-063

### CheckSum:
- ✓ Não viola prioridades: S-2 tem espaço
- ✓ Dependências resolvidas: BLID-047 já concluído
- ✓ Implementação visível por iniciar.bat: SIM (agent/signal_reward.py)

**Próximo passo:** Confirmar [Y/N]?
```

**Usuário:** `Y`

**Skill executa:** [PASSO 4]
```
✓ Atualizado docs/BACKLOG.md
✓ Atualizado docs/TRACKER.md
✓ Registrado em docs/SYNCHRONIZATION.md

Commit gerado:
  [FEAT] Adicionado BLID-063 EMA Dinâmico

  Relacionado a: ML2 Improvement Signal
  Sprint: S-2
  Prioridade: Alta

  Deps: BLID-047 (concluído)

  Issue: NÃO linkada (criar issue separada se precisar)
```

---

## Exemplo 2 — Atualizar Status (Mover para In Progress)

**Prompt do Usuário:**
```
/backlog-development Mover BLID-062 para "In Progress"
```

**Resposta Esperada:** [ver PASSO 3b do SKILL.md]

```markdown
## Proposta: Atualizar Task

**ID:** BLID-062
**Campo:** Status: Planned → In Progress

**Antes:**
| ID | Título | Status | Sprint | Prioridade |
|----|--------|--------|--------|-----------|
| BLID-062 | Early Exit Mecanismo | Planned | S-2 | Alta |

**Depois:**
| ID | Título | Status | Sprint | Prioridade |
|----|--------|--------|--------|-----------|
| BLID-062 | Early Exit Mecanismo | In Progress | S-2 | Alta |

### Impacto:
- Tasks dependentes:
  - BLID-065 (integração com executor) pode desbloquear
  - BLID-066 (testes E2E) aguarda conclusão de BLID-062
- TRACKER.md: "In Progress" +1, "Planned" -1
- Estimativa: 3-5 dias (conforme design original)

### Validação:
- ✓ Sprint válida (S-2 ativo)
- ✓ Prioridade preservada (Alta)
- ✓ Dependências: BLID-047, BLID-051 já concluídas
- ✓ Sem ciclos

**Próximo passo:** Confirmar [Y/N]?
```

**Usuário:** `Y`

**Skill executa:**
```
✓ Atualizado docs/BACKLOG.md (BLID-062 status change)
✓ Atualizado docs/TRACKER.md (contadores)
✓ Registrado em docs/SYNCHRONIZATION.md

Commit gerado:
  [SYNC] BLID-062 In Progress — Early Exit

  Sprint: S-2
  Deps OK: BLID-047 ✓, BLID-051 ✓
  Unblock: BLID-065 liberada para iniciar
```

---

## Exemplo 3 — Gerar Relatório de Status

**Prompt do Usuário:**
```
/backlog-development Status do backlog hoje. Incluir recomendações.
```

**Resposta Esperada:** [ver PASSO 3c do SKILL.md]

```markdown
## Relatório: Status do Backlog (15-MAR-2026)

**Resumo Executivo:**
- Total Tasks: 66
- Backlog: 22 | Planned: 14 | In Progress: 10 | Done: 20
- Progress NOW (S-2): 10/12 = 83% ✓
- Health: 🟡 On Track (1 dia atrás do schedule)

**Por Sprint:**
| Sprint | Total | Backlog | Planned | In Progress | Done | % Health |
|--------|-------|---------|---------|-------------|------|----------|
| S-1    | 20    | 0       | 0       | 0           | 20   | 🟢 100% DONE |
| S-2    | 12    | 2       | 2       | 8           | 0    | 🟡 83% |
| S-3    | 15    | 13      | 1       | 1           | 0    | 🔴 13% |
| S-4    | 19    | 7       | 11      | 1           | 0    | 🟡 42% (NEW) |

**Bloqueadores Críticos:**
1. **BLID-062** (Early Exit Mecanismo) — 1 dia atrasada
   - Impacto: BLID-065, BLID-066 aguardando
   - ETA: 17-MAR (prox terça)

2. **Infra Decision** (Early Access Binance Testnet) — externa
   - Impacto: BLID-048 (Advanced Signals) bloqueada
   - Ação: Aguardando resposta Binance
   - Fallback: Usar ambiente sandbox público

3. **BLID-051** (PPO V2 Checkpoint Stability) — revisão de design
   - Status: Bloqueada, aguarda feedback arquitetura
   - Ação: Reunião de design agendada 16-MAR

**Alinhamento com ROADMAP.md:**
| Milestone | Sprint | Status | Evidence | Gap |
|-----------|--------|--------|----------|-----|
| MVP-1 (v0.1) | S-1 | 🟢 Done | Released 28FEV | — |
| v0.2 ML2 | S-2 | 🟡 83% | 10/12 features | ETA +1 dia |
| v0.3 ML3 | S-3 | 🔴 13% | Planned<br>Ainda não iniciado | Planejamento OK, ramp-up em 18-MAR |

**Metricas de Velocidade:**
- S-1: 20 tasks (baseline)
- S-2: 10/12 em 5 dias (166% velocity em on-time, 1 dia atrasado)
- Tendência: Sustentável. S-3 precisa de início rápido.

**Recomendações:**
1. ✓ **MANTER pressão em BLID-062** — Reunião daily amanhã
2. ✓ **Iniciar BLID-048 workaround** — Usar sandbox enquanto aguarda Binance
3. ✓ **Design review BLID-051** — Agendar 16-MAR, aprovar/rejeitar até 17-MAR
4. ✓ **Ramp-up S-3** — Kick-off planejamento 18-MAR (3 dias)
5. 💡 **Considerar pausa S-1** — Recursos de QA? Documentação?

**Syncronização com README.md:**
- [ ] Atualizar versão: v0.2-beta (10/12) em desenvolvimento
- [ ] Atualizar status: "On Track with 1-day delay in S-2"

**Próximo passo:**
- Gerar commit com este relatório em docs/STATUS_ATUAL.md? [Y/N]
- Criar GitHub Issues para bloqueadores? [Y/N]
```

---

## Exemplo 4 — Sincronizar Docs (Após Mudanças Externas)

**Prompt do Usuário:**
```
/backlog-development Sincronizar. BLID-050 foi concluída ontem,
esqueci de atualizar backlog.
```

**Resposta Esperada:**

```markdown
## Proposta: Sincronizar Documentação

**Situação:** BLID-050 (Risk Manager Consolidation) concluída offline

**Arquivos a Atualizar:**
1. docs/BACKLOG.md: BLID-050 status Planned → Done
2. docs/TRACKER.md: contadores (Planned -1, Done +1)
3. docs/ROADMAP.md: v0.2 progresso 9/12 → 10/12 (83%)
4. docs/SYNCHRONIZATION.md: registrar sync com motivo

**Validações:**
- ✓ BLID-050 existe em BACKLOG.md (linha 242)
- ✓ Dependências: BLID-049 concluída ✓
- ✓ Nenhuma task aguardava BLID-050
- ✓ Status transition válida: Planned → Done

**Mudanças Propostas:**
```
docs/BACKLOG.md (linha 242):
- Status: Planned
+ Status: Done
+ Completed: 14-MAR-2026

docs/TRACKER.md:
- Planned: 15
+ Planned: 14
- Done: 19
+ Done: 20

docs/ROADMAP.md (v0.2 section):
- Progress: 9/12 = 75%
+ Progress: 10/12 = 83%
```

**CheckSum:**
- ✓ Markdown lint: sem erros
- ✓ Português: OK
- ✓ UTF-8: válido
- ✓ Commit message: "[SYNC] BLID-050 concluído — Risk Manager"

**Próximo passo:** Confirmar e gerar commit [Y/N]?
```

**Usuário:** `Y`

**Skill executa:**
```
✓ Atualizado docs/BACKLOG.md (BLID-050)
✓ Atualizado docs/TRACKER.md (contadores)
✓ Atualizado docs/ROADMAP.md (v0.2 progress)
✓ Registrado em docs/SYNCHRONIZATION.md

Commit gerado:
  [SYNC] BLID-050 concluído — Risk Manager v2

  Status: Planned → Done
  Completed: 14-MAR-2026

  Impacto:
  - v0.2 progress: 9/12 → 10/12 (83%)
  - Planned: 15 → 14
  - Done: 19 → 20

  Nenhuma tasks bloqueadas.
  Sincronizado com ROADMAP.md e TRACKER.md.
```

---

## Exemplo 5 — Validar Integridade (Encontrar Problemas)

**Prompt do Usuário:**
```
/backlog-development Validar integridade do BACKLOG.md. Há problemas?
```

**Resposta Esperada:**

```markdown
## Validação: Integridade do BACKLOG.md

### Erros Encontrados: 2
```

**🔴 ERRO 1: Ciclo de Dependência**
```
BLID-056 → BLID-057 → BLID-060 → BLID-056
```
- Problema: Impossível resolver ordem de execução
- Ação Recomendada: Quebrar dependência BLID-060 → BLID-056
  ou redefinir escopos

---

**🔴 ERRO 2: Task Órfã**
```
BLID-064 depende de BLID-099 (não encontrada em BACKLOG.md)
```
- Problema: Referência morta
- Ação Recomendada:
  - [ ] Criar BLID-099? (se real)
  - [ ] Remover dependência de BLID-064? (se obsoleta)

---

### Avisos: 3

**🟡 AVISO 1: Sprint S-4 Sobrecarregada**
- Total: 19 tasks
- Histórico S-1/S-2: ~12 tasks por sprint
- Risco: Velocity não sustentável
- Recomendação: Mover 5-7 tasks para S-5

---

**🟡 AVISO 2: BLID-062 Atrasada**
- Planned para: 12-MAR
- Hoje: 15-MAR (3 dias atrasada)
- Impacto: BLID-065, BLID-066 bloqueadas
- Ação: Verificar se ainda é viável? Reestimar?

---

**🟡 AVISO 3: Tasks sem Critérios de Aceite**
- BLID-010, BLID-012, BLID-019 (3 tasks)
- Risco: Critério de "Done" ambíguo
- Ação: Adicionar critérios antes de mover para Planned

---

### OK: 1 Insight

**🟢 INSIGHT: S-2 está no caminho certo**
- 10/12 concluídas ou em progress
- 1 dia de atraso recoverable
- Health: 🟡 On Track

---

## Recomendações Urgentes:
1. Resolver ERRO 1 (ciclo)
2. Resolver ERRO 2 (orphaned ref)
3. Adicionar aceite criteria a BLID-010, BLID-012, BLID-019
4. Rebalancear S-4 (descarregar)

Deseja gerar relatório de correção [Y/N]?
```

---

## Resumo de Padrões

| Caso | Prompt | Esperado | Tag Commit |
|------|--------|----------|-----------|
| Criar task | "Criar task X" | Proposta (PASSO 3a) | [FEAT] |
| Mudar status | "Mover task X para Y" | Update (PASSO 3b) | [SYNC] |
| Gerar relatório | "Status do backlog" | Report (PASSO 3c) | [DOCS] |
| Sincronizar | "Sync BACKLOG.md" | Sync (PASSO 3d) | [SYNC] |
| Validar | "Validar BACKLOG.md" | Validação + erros | [TEST] |

---

Ver também: [SKILL.md](./SKILL.md), [docs/BACKLOG.md](../../docs/BACKLOG.md)
