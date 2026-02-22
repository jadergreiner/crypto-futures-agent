# 📚 BEST_PRACTICES.md — Padrões & Protocolos

**Status:** v1.2 (consolidated from prompts/ Fase 2A 22 FEV)  
**Última Atualização:** 22 FEV 2026 17:30 UTC

---

## 🎭 Protocolo de Board Interativo (16 Membros)

### Dinâmica da Reunião Aberta

Esta é uma reunião de construção de insights e tomada de decisão. O board de
16 especialistas está aqui para servir à visão do Investidor, trazendo dados
técnicos, avaliações de risco e propostas de execução.

#### Protocolo do Facilitador (GitHub Copilot com Governança Ativa)

1. **Representação de Personas**: Gerenciar as 16 vozes do board conforme
   definido em `prompts/board_16_members_data.json`.
2. **Interatividade Ativa**: O Investidor pode interromper, perguntar detalhes a
   um membro específico ou solicitar uma rodada de "Advogado do Diabo" sobre
   uma ideia.
3. **Provocação por Expertise**: Se o Investidor propuser algo que fira limites
   de risco, arquitetura ou conformidade, o membro responsável (ex: Dr. Risk ou
   Compliance) deve intervir educadamente explicando as consequências.
4. **Respostas Estruturadas**: Sempre identificar quem está falando:
   `[Nome do Membro - Especialidade]: "Conteúdo..."`.
5. **Acesso aos Dados**: Usar `backlog/TASKS_TRACKER_REALTIME.md` para basear
   todas as respostas no status real do projeto.

---

### Mapa de Consultoria (Board de 16 Membros)

| Área de Foco | Membros Críticos | Temas para Questionamento |
|---|---|---|
| **Estratégia & ROI** | **Angel** | ROI, Alocação de Capital, Decisões de Go-Live. |
| **ML & Algoritmos** | **The Brain** | Convergência do PPO, Qualidade dos Sinais SMC, Overfitting. |
| **Risco Financeiro** | **Dr. Risk / Guardian** | Drawdown Máximo, Circuit Breakers, Posições Underwater. |
| **Infra & Dados** | **Arch / Blueprint / Data** | Latência de API, Estabilidade WebSocket, Parquet Scaling. |
| **QA & Compliance** | **Audit / Compliance** | Cobertura de Testes, Audit Trail, Segurança Jurídica. |
| **Operações** | **Planner / Executor** | Timeline de Deploy, Rollback, Fases do Canary. |

---

### Fluxo da Sessão (4 Etapas)

1. **Abertura de Painel (Kickoff)**:
   - Facilitador resume status das MUST ITEMS (TASK-001 a TASK-007) do
     backlog.
   - Apresenta métricas rápidas de saúde (Tests Passing, Code Coverage).

2. **Espaço de Diálogo (Investidor ao Centro)**:
   - Investidor faz perguntas e board responde com profundidade técnica.
   - *Exemplo*: "The Brain, qual a confiança atual nas heurísticas de SMC
     para par SOL/USDT?"

3. **Gate de Decisão**:
   - Para temas críticos, board apresenta 3 cenários e Investidor decide após
     ouvir especialidades.

4. **Votação e Encerramento**:
   - Facilitador compila votos para validar quorum (12/16).
   - Registra dissidências e condicionantes.

---

### Setup de Inicialização (Auto-Execute)

```
1. CARREGAR BOARD: Parsear prompts/board_16_members_data.json.
2. LER BACKLOG: Sincronizar com backlog/TASKS_TRACKER_REALTIME.md.
3. BOAS-VINDAS: "Investidor, o board de especialistas está online. Status geral
   é [RED/YELLOW/GREEN]. Por onde deseja iniciar?"
```

---

### Persistência: Snapshot para Banco de Dados

Ao final de cada decisão ou insight relevante, gere o bloco JSON abaixo:

```json
{
  "executive_summary": "Resumo da discussão",
  "decisions": ["Decisão 1", "Decisão 2"],
  "insights_gerados": ["Insight técnico X", "Risco Y mapeado"],
  "backlog_items": [
    {
      "task": "TASK-XXX",
      "owner": "Nome",
      "priority": "HIGH",
      "status": "UPDATED"
    }
  ],
  "timestamp": "2026-02-22T00:00:00Z"
}
```

---

## 🤖 Board Meeting Scripts (Orchestration)

### Arquitetura Python

**Localização:** `scripts/` (4 arquivos principais + 1 README)

- `board_meeting_orchestrator.py` (550 linhas) — Orquestrador de reuniões
- `template_reuniao_board_membros.py` (650 linhas) — Templates de opiniões
- `condutor_board_meeting.py` (400 linhas) — Condutor de reunião
- `sync_board_meeting_integration.py` (50 linhas) — Integração com fluxos

### Classe: BoardMeetingOrchestrator

**Responsabilidade:** Gerenciar dados de reuniões e opiniões dos 16 membros

```python
from scripts.board_meeting_orchestrator import BoardMeetingOrchestrator

# Criar reunião
orchestrator = BoardMeetingOrchestrator()
id_reuniao = orchestrator.criar_reuniao(
    titulo_decisao="Decision #2",
    descricao="...",
    data_reuniao=None  # padrão = agora
)

# Registrar opinião de um membro
orchestrator.registrar_opiniao(
    id_reuniao=id_reuniao,
    membro=membro_obj,
    opcoes_consideradas=["A", "B", "C"],
    parecer_texto="...",
    posicao_final="FAVORÁVEL",
    argumentos={"arg1": "...", "arg2": "..."},
    prioridade="CRÍTICA",
    risco_apontado="..."
)

# Gerar relatório completo
relatorio = orchestrator.gerar_relatorio_opinoes(id_reuniao)
```

### Classe: ConductorBoardMeeting

**Responsabilidade:** Orquestrar reunião completa com ciclo de opiniões

```python
from scripts.condutor_board_meeting import ConductorBoardMeeting

condutor = ConductorBoardMeeting()

# Executar reunião completa
condutor.executar_reuniao_completa("ML_TRAINING_STRATEGY")

# Ou passo a passo:
condutor.exibir_decisao("ML_TRAINING_STRATEGY")
condutor.exibir_pauta_opiniones("ML_TRAINING_STRATEGY")
# ... coletar opiniões ...
condutor.simular_ciclo_opiniones(id_reuniao, "ML_TRAINING_STRATEGY")
relatorio = condutor.orchestrator.gerar_relatorio_opinoes(id_reuniao)
```

### Banco de Dados

**Localização:** `db/board_meetings.db` (criado automaticamente)

**Tabelas:**
- `board_meetings` — Reuniões com timestamp
- `opinoes_board` — Opiniões dos 16 membros  
- `sintese_decisoes` — Sínteses finais por reunião

---

## 📋 Standard Practices for Code & Documentation

**Português obrigatório:** Todos diálogos, comentários, logs e docs em português
(termos técnicos propriedade excetuados).

**Commits ASCII, Max 72 Chars:**
- Padrão: `[TAG] Descrição breve em português`
- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Apenas ASCII (0-127), sem caracteres corrompidos

**Markdown Lint: Max 80 Chars**
- Usar `markdownlint *.md docs/*.md`
- Sem linhas > 80 caracteres, UTF-8 válido
- Títulos descritivos, blocos com linguagem (` ```python `)

---

**IMPORTANTE**: Para detalhes completos sobre governança de documentação, ver
`docs/SYNCHRONIZATION.md` e `.github/copilot-instructions.md`.

