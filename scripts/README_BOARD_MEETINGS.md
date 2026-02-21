#!/usr/bin/env bash
# [SYNC] Scripts de Reunião de Board com 16 Membros
# Facilitador: Elo (Gestor de Alinhamento)

## 📊 ESTRUTURA

```
scripts/
├── board_meeting_orchestrator.py          # Orquestrador principal (550 linhas)
├── template_reuniao_board_membros.py      # Templates de opiniões (650 linhas)
├── condutor_board_meeting.py              # Condutor de reunião (400 linhas)
├── sync_board_meeting_integration.py      # Integração con existentes (50 linhas)
└── README_BOARD_MEETINGS.md               # Este arquivo
```

---

## 🎯 USO RÁPIDO

### 1. Executar reunião de decisão

```bash
# Decision #2: ML Training Strategy
python scripts/condutor_board_meeting.py --decisao ML_TRAINING_STRATEGY

# Decision #3: Posições Underwater
python scripts/condutor_board_meeting.py --decisao POSIOES_UNDERWATER

# Decision #4: Escalabilidade
python scripts/condutor_board_meeting.py --decisao ESCALABILIDADE
```

### 2. Saída esperada

```
🎯 INICIANDO REUNIÃO DE BOARD COM 16 MEMBROS
================================================================================
...processo completo...
✅ REUNIÃO CONCLUÍDA
📊 Relatório completo: reports/board_meeting_1_ML_TRAINING_STRATEGY.md
```

### 3. Relatório gerado

Arquivo `reports/board_meeting_1_ML_TRAINING_STRATEGY.md`:
- Decisão apresentada
- Opiniões de cada um dos 16 membros
- Posição final (FAVORÁVEL, CONTRÁRIO, NEUTRO, CONDICIONAL)
- Argumentos por membro
- Riscos identificados

---

## 🔧 COMPONENTES

### 1. `board_meeting_orchestrator.py`

**Responsabilidade:** Gerenciar dados de reuniões e opiniões

**Classe principal:** `BoardMeetingOrchestrator`

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

# Gerar relatório
relatorio = orchestrator.gerar_relatorio_opinoes(id_reuniao)
```

**Equipe fixa definida:** 16 membros

```python
orchestrator.EQUIPE_FIXA  # Lista completa com 16 membros
```

### 2. `template_reuniao_board_membros.py`

**Responsabilidade:** Estruturar perguntas por especialidade

**Classe principal:** `TemplateReuniaoBoardMembros`

```python
from scripts.template_reuniao_board_membros import TemplateReuniaoBoardMembros

# Renderizar pauta estruturada
pauta = TemplateReuniaoBoardMembros.renderizar_pauta_reuniao("ML_TRAINING_STRATEGY")
print(pauta)

# Obter template de formulário para membro
template = TemplateReuniaoBoardMembros.template_formulario_opiniao(
    especialidade="machine_learning",
    tipo_decisao="ML_TRAINING_STRATEGY"
)
```

**Tipos de decisão suportados:**
- `ML_TRAINING_STRATEGY` — Decision #2
- `POSIOES_UNDERWATER` — Decision #3
- `ESCALABILIDADE` — Decision #4

### 3. `condutor_board_meeting.py`

**Responsabilidade:** Orquestrar reunião completa

**Classe principal:** `ConductorBoardMeeting`

```python
from scripts.condutor_board_meeting import ConductorBoardMeeting

condutor = ConductorBoardMeeting()

# Executar reunião com ciclo de opiniões
condutor.executar_reuniao_completa("ML_TRAINING_STRATEGY")

# Ou passo a passo:
condutor.exibir_decisao("ML_TRAINING_STRATEGY")
condutor.exibir_pauta_opiniones("ML_TRAINING_STRATEGY")
# ... coletar opiniões ...
condutor.simular_ciclo_opiniones(id_reuniao, "ML_TRAINING_STRATEGY")
relatorio = condutor.orchestrator.gerar_relatorio_opinoes(id_reuniao)
```

---

## 📋 FLUXO DE REUNIÃO

```
┌─────────────────────────────────────────┐
│ 1. APRESENTAR DECISÃO (5 min)          │
│    - Título, contexto, opções          │
│    - Critério de sucesso               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. EXIBIR PAUTA ESTRUTURADA (5 min)    │
│    - Perguntas por especialidade       │
│    - 16 grupos de especialidades       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. CICLO DE OPINIÕES (40 min)          │
│    - 4 minutos por membro              │
│    - 16 membros × 4 min = 64 min      │
│    - Coleta estruturada via template   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. SÍNTESE DE POSIÇÕES (5 min)         │
│    - Contagem: FAVORÁVEL vs CONTRÁRIO  │
│    - Identificar consenso/dissenso     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 5. VOTAÇÃO FINAL (5 min)               │
│    - Angel toma decisão final          │
│    - Registra em banco de dados        │
│    - Exporta markdown com [SYNC]       │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 6. RELATÓRIO EXPORTADO                 │
│    - reports/board_meeting_N_*.md      │
│    - Todas 16 opiniões documentadas    │
│    - Pronto para auditoria [SYNC]      │
└─────────────────────────────────────────┘
```

---

## 💾 BANCO DE DADOS

Localização: `db/board_meetings.db`

**Tabelas:**
- `board_meetings` — Reuniões
- `opinoes_board` — Opiniões dos membros
- `sintese_decisoes` — Sínteses finais

**Exemplo de query:**

```sql
-- Obter todas opiniões de uma reunião
SELECT nome_membro, posicao_final, prioridade
FROM opinoes_board
WHERE id_reuniao = 1
ORDER BY tipo_opiniao;

-- Contar posições
SELECT posicao_final, COUNT(*) as total
FROM opinoes_board
WHERE id_reuniao = 1
GROUP BY posicao_final;
```

---

## 📊 EXEMPLO: Decision #2 (ML Training)

### Executar

```bash
python scripts/condutor_board_meeting.py --decisao ML_TRAINING_STRATEGY
```

### Output esperado

```
🎯 INICIANDO REUNIÃO DE BOARD COM 16 MEMBROS
================================================================================
Decisão: Decision #2 — ML Training Strategy
Hora: 2026-02-23T14:30:00
================================================================================

1️⃣ Criando reunião...
   ✅ Reunião criada (ID=1)

2️⃣ Apresentando decisão...
   [Decisão apresentada]

3️⃣ Exibindo pauta estruturada...
   [Perguntas para cada especialidade]

4️⃣ Executando ciclo de opiniões (16 membros)...
   ✅ Ciclo completo

5️⃣ Gerando relatório de opiniões...
   ✅ Relatório salvo: reports/board_meeting_1_ML_TRAINING_STRATEGY.md

6️⃣ RESUMO DE OPINIÕES
================================================================================

FAVORÁVEL: 10/16 (62.5%)
  ✓ Angel (Investidor)
  ✓ Elo (Facilitador)
  ✓ Dr. Risk (Head Finanças)
  ... (7 mais)

CONDICIONAL: 4/16 (25%)
  ✓ The Brain (ML)
  ✓ Arch (AI Architect)
  ... (2 mais)

NEUTRO: 2/16 (12.5%)
  ✓ Flux (Dados)
  ... (1 mais)

================================================================================
✅ REUNIÃO CONCLUÍDA
📊 Relatório completo: reports/board_meeting_1_ML_TRAINING_STRATEGY.md
```

### Relatório Markdown

Arquivo `reports/board_meeting_1_ML_TRAINING_STRATEGY.md`:

```markdown
# 🎯 BOARD MEETING — Decision #2 — ML Training Strategy

[Decisão apresentada]

## 📋 CICLO DE OPINIÕES (16 MEMBROS)

### 👑 EXECUTIVA

#### Angel (Investidor)
**Posição:** FAVORÁVEL | **Prioridade:** CRÍTICA
**Parecer:** "Opção C oferece melhor trade-off..."
**Argumentos:** [3 argumentos principais]
**Risco:** [Riscos identificados]

### 🤖 MACHINE LEARNING

#### The Brain (Engenheiro ML)
[...]

[15 membros mais...]
```

---

## 🔧 CUSTOMIZAÇÃO

### Adicionar nova decisão

Editar `scripts/condutor_board_meeting.py`:

```python
DECISOES_TEMPLATE = {
    "NOVA_DECISAO": {
        "titulo": "Decision #5 — Nova Decisão",
        "descricao": "...",
        "opcoes": ["A", "B", "C"],
        "owner_final_decision": "Angel"
    }
}
```

### Adicionar novas perguntas por especialidade

Editar `scripts/template_reuniao_board_membros.py`:

```python
PERGUNTAS_POR_ESPECIALIDADE = {
    "NOVA_DECISAO": {
        "nova_especialidade": PerguntaPorEspecialidade(
            especialidade="Nome",
            pergunta_principal="...",
            sub_perguntas=[...],
            criterios_avaliacao=[...],
            impactos_esperados=[...]
        )
    }
}
```

---

## 🔐 [SYNC] — PROTOCOLO DE SINCRONIZAÇÃO

Todos os scripts seguem protocolo [SYNC]:
- ✅ Docstrings completos em português
- ✅ Type hints em todas funções
- ✅ Logging estruturado
- ✅ Banco de dados persistente
- ✅ Relatórios markdown exportáveis
- ✅ Rastreamento de decisões auditável

**Documento oficial:** `docs/SYNC_BOARD_MEETING_16_MEMBERS.md`

---

## 📞 TROUBLESHOOTING

### "Banco de dados não existe"

```python
# Automático! BoardMeetingOrchestrator cria em:
# db/board_meetings.db
```

### "ImportError: No module named 'scripts.board_meeting_orchestrator'"

```bash
# Adicione à raiz do projeto em sys.path
cd /path/to/crypto-futures-agent
python -c "import sys; sys.path.insert(0, '.'); from scripts.board_meeting_orchestrator import BoardMeetingOrchestrator"
```

### "Relatório não gerado"

```bash
# Verificar permissões
mkdir -p reports
chmod 755 reports/
```

---

## 📈 PRÓXIMOS PASSOS

1. ✅ Implementação básica (ciclo de opiniões)
2. ⏳ Interface web para coleta de opiniões (opcional)
3. ⏳ Integração com GitHub Issues
4. ⏳ Dashboard de histórico de decisões
5. ⏳ Votação weighted por especialidade

---

**Owner:** Elo (Facilitador)
**Última atualização:** 23 FEV 2026
**Próxima review:** Após primeiro ciclo ao vivo
