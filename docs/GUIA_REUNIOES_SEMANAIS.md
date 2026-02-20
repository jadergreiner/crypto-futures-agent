# GUIA DE USO — Sistema de Reuniões Semanais
## Head Financeiro × Operador Autônomo (Crypto Futures)

---

## 📋 Visão Geral

Este sistema mantém histórico completo de reuniões semanais entre o **Head Financeiro** (especialista em derivativos cripto) e o **Operador Autônomo** (agente RL em PPO).

Cada reunião registra:
- ✅ Diálogos técnicos com dados contextuais
- ✅ Feedbacks estruturados (5D: força, fraqueza, oportunidade, ameaça)
- ✅ Ações (código, compras, retraining, análise)
- ✅ Investimentos (com ROI estimado)
- ✅ Rastreamento de evolução entre reuniões

---

## 🔧 Instalação e Uso

### Pré-requisitos
```bash
# Python 3.8+
python --version

# Pacote sqlite3 (incluído no Python)
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

### Inicializar o Sistema

```bash
# Teste básico (criar banco + registrar reunião exemplo)
python scripts/reuniao_manager.py

# Saída esperada:
# ✅ Reunião criada com sucesso!
# ID: 1
# Relatório exportado para: docs/reuniao_YYYY_MM_DD_HHMMSS.md
```

### Usar em Seu Código Python

```python
from scripts.reuniao_manager import ReuniaoWeeklyDB

# Criar/conectar ao banco
db = ReuniaoWeeklyDB(db_path="db/reunioes_weekly.db")

# Criar nova reunião
id_reuniao = db.criar_reuniao(
    data_reuniao="2026-02-20 17:00:00",
    semana_numero=8,
    ano=2026,
    head_nome="Roberto Silva",
    operador_versao="v0.3"
)

# Adicionar diálogo
db.adicionar_dialogo(
    id_reuniao=id_reuniao,
    sequencia=1,
    quem_fala="HEAD",
    pergunta_ou_resposta="Por que você entrou LONG em DOGEUSDT com score baixo?",
    tipo_conteudo="pergunta",
    contexto_dados={
        "par": "DOGEUSDT",
        "score": 4.2,
        "pnl": -320
    }
)

# Criar ação
db.criar_acao(
    id_reuniao=id_reuniao,
    descricao_acao="Aumentar threshold de score mínimo",
    tipo_acao="código",
    prioridade="crítica",
    responsavel="OPERADOR",
    arquivo_alvo="agent/reward.py"
)

# Exportar relatório em Markdown
db.exportar_relatorio_markdown(
    id_reuniao=id_reuniao,
    arquivo_saida="docs/reuniao_2026_02_20.md"
)
```

---

## 📊 Fluxo de Reunião (Passo a Passo)

### Passo 1: Preparar Contexto
Antes da reunião (qualquer horário), coletar dados:

```python
# Dados de performance
performance_semanal = {
    "pnl_usdt": 12450.75,
    "pnl_pct": 2.15,
    "sharpe": 1.82,
    "max_drawdown": 3.2,
    "taxa_acertos": 0.62,
    "num_operacoes": 45
}

# Comparação com semana anterior
comparacao = {
    "delta_sharpe": +0.31,
    "delta_drawdown": -1.5,
    "acoes_completadas": 3,
    "acoes_pendentes": 2
}
```

### Passo 2: Criar Reunião
```python
id_reuniao = db.criar_reuniao(
    data_reuniao="2026-02-20 15:30:00",  # Qualquer horário, qualquer dia
    semana_numero=8,  # Opcional (informativo)
    ano=2026,
    head_nome="Roberto Silva",
    operador_versao="v0.3"
)
```

### Passo 3: Adicionar Diálogos
Estrutura: HEAD faz pergunta → OPERADOR responde → HEAD faz tréplica

```python
# Pergunta 1
db.adicionar_dialogo(
    id_reuniao=id_reuniao,
    sequencia=1,
    quem_fala="HEAD",
    pergunta_ou_resposta="Qual foi seu maior acerto esta semana?",
    tipo_conteudo="pergunta",
    contexto_dados={
        "periodo": "2026-02-14 a 2026-02-20",
        "metrica": "sharpe_ratio"
    }
)

# Resposta 1
db.adicionar_dialogo(
    id_reuniao=id_reuniao,
    sequencia=2,
    quem_fala="OPERADOR",
    pergunta_ou_resposta=(
        "BTCUSDT LONG com entry em 42.850, TP em 44.200. "
        "Score do modelo: 8.7 (confluência SMC + RSI confirmado). "
        "PnL: +850 USDT em 4 horas."
    ),
    tipo_conteudo="resposta",
    contexto_dados={
        "par": "BTCUSDT",
        "tipo": "LONG",
        "score": 8.7,
        "pnl": 850
    }
)

# Tréplica (avaliação)
db.adicionar_dialogo(
    id_reuniao=id_reuniao,
    sequencia=3,
    quem_fala="HEAD",
    pergunta_ou_resposta=(
        "Excelente. Score alto, confluência justificada, TP atingido no tempo. "
        "Isso é operação de qualidade. Manter padrão."
    ),
    tipo_conteudo="trepica"
)
```

### Passo 4: Adicionar Feedbacks
```python
# Força
db.adicionar_feedback(
    id_reuniao=id_reuniao,
    categoria="força",
    descricao="Taxa de acerto subiu de 59% para 62%",
    impacto_score=9.0,
    responsavel="OPERADOR"
)

# Fraqueza
db.adicionar_feedback(
    id_reuniao=id_reuniao,
    categoria="fraqueza",
    descricao="Executou 3 operações com score <5.0. Taxa de acerto em low scores: 35%",
    impacto_score=7.5,
    responsavel="OPERADOR"
)

# Oportunidade
db.adicionar_feedback(
    id_reuniao=id_reuniao,
    categoria="oportunidade",
    descricao="0GUSDT teve sinal de BOS claro. Limite de ordens (10) impediu execução.",
    impacto_score=8.0,
    responsavel="OPERADOR"
)
```

### Passo 5: Criar Ações
```python
# Ação 1: Código
id_acao1 = db.criar_acao(
    id_reuniao=id_reuniao,
    descricao_acao="Aumentar threshold mínimo de score de 4.0 para 5.5",
    tipo_acao="código",
    prioridade="crítica",
    responsavel="OPERADOR",
    arquivo_alvo="agent/reward.py",
    impacto_esperado="+3% em taxa de acerto, -5% em volume",
    sequencia_acao=1
)

# Ação 2: Compra/Investimento
id_acao2 = db.criar_acao(
    id_reuniao=id_reuniao,
    descricao_acao="Comprar +32GB RAM para expansão de 20+ pares",
    tipo_acao="compra",
    prioridade="alta",
    responsavel="HEAD",
    impacto_esperado="+18% throughput, +2.1% Sharpe",
    sequencia_acao=2
)
```

### Passo 6: Registrar Investimentos
```python
db.criar_investimento(
    id_reuniao=id_reuniao,
    tipo_investimento="computação",
    descricao="Kingston 32GB DDR4 ECC + instalação",
    custo_estimado=800.0,
    roi_esperado=12.0,
    justificativa=(
        "Limite técnico atual: 12 pares em paralelo. "
        "Com mais RAM: 20+ pares. Impacto: correlações complexas "
        "permitirão hedging mais eficiente."
    )
)

db.criar_investimento(
    id_reuniao=id_reuniao,
    tipo_investimento="infraestrutura",
    descricao="Nobreak 1500W + gerador 5kW",
    custo_estimado=1200.0,
    roi_esperado=-5.0,  # Defensive (reduz drawdown)
    justificativa=(
        "Uptime crítico de 99.95% exige redundância de energia. "
        "Queda de energia = stop loss automático em TODAS as posições. "
        "Investimento preventivo."
    )
)

db.criar_investimento(
    id_reuniao=id_reuniao,
    tipo_investimento="rede",
    descricao="Conexão dedicada co-location Binance (IP fixo, latência <0.5ms)",
    custo_estimado=200.0,
    roi_esperado=1.5,
    justificativa=(
        "Latência atual: 19-21ms em picos. "
        "Co-location: 0.5ms > pega ordens 40x mais rápido > "
        "less slippage em futuros voláteis."
    )
)
```

### Passo 7: Exportar Relatório
```python
# Exportar em Markdown
relatorio_md = db.exportar_relatorio_markdown(
    id_reuniao=id_reuniao,
    arquivo_saida="docs/reuniao_2026_02_20.md"
)

print(f"✅ Relatório exportado: docs/reuniao_2026_02_20.md")
```

---

## 📈 Rastreamento de Ações Entre Reuniões

### Atualizar Status de Ação

```python
# Inicialmente: Pendente
# Semana seguinte: Implementado

db.atualizar_status_acao(
    id_acao=1,
    novo_status="concluido",
    percentual_conclusao=100.0
)

print("✅ Ação #1 concluída!")
```

### Gerar Comparação Automática

```python
# Criar comparação entre reunião anterior e atual
id_comparacao = db.gerar_comparacao_reunioes(
    id_reuniao_anterior=1,  # Semana anterior
    id_reuniao_atual=2,     # Semana atual
    delta_sharpe=+0.31,
    delta_pnl=+1850.40
)

# Gera automaticamente:
# - Quantas ações foram concluídas desde a reunião anterior?
# - Quantas ainda estão pendentes?
# - Status evoluiu (ex: 'pendente' → 'em_andamento' → 'concluido')?
```

---

## 🗂️ Estrutura de Arquivos Gerados

Por cada reunião, o sistema cria:

```
docs/
├── reuniao_2026_02_20.md          # Relatório markdown completo
├── backlog_acoes_2026_02_20.md    # Ações específicas com snippets
├── investimentos_2026_02_20.md    # Decisões de capital + ROI
└── tracker_evolucoes.md            # Rastreamento de progresso

db/
└── reunioes_weekly.db
    ├── reunioes (metadata)
    ├── dialogos_reuniao
    ├── feedbacks_reuniao
    ├── acoes_reuniao
    ├── investimentos_reuniao
    ├── evolucoes_reuniao
    └── comparacao_reunioes
```

---

## 🔍 Consultas Úteis

### Ver Todas as Reuniões

```python
import sqlite3

conn = sqlite3.connect("db/reunioes_weekly.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT id_reuniao, data_reuniao, semana_numero, status,
           head_nome, operador_versao
    FROM reunioes
    ORDER BY data_reuniao DESC
""")

for row in cursor.fetchall():
    print(f"[{row[0]}] {row[1]} — {row[4]} vs {row[5]} — Status: {row[3]}")

conn.close()
```

### Ver Ações Pendentes

```python
cursor.execute("""
    SELECT a.id_acao, a.descricao_acao, a.prioridade, 
           r.data_reuniao, a.arquivo_alvo
    FROM acoes_reuniao a
    JOIN reunioes r ON a.id_reuniao = r.id_reuniao
    WHERE a.status_acao = 'pendente'
    ORDER BY a.prioridade DESC, r.data_reuniao DESC
""")

for row in cursor.fetchall():
    print(f"[{row[2].upper()}] {row[1]}")
    print(f"     Reunião: {row[3]} | Alvo: {row[4]}\n")
```

### Investimentos em Análise

```python
cursor.execute("""
    SELECT tipo_investimento, descricao, custo_estimado, 
           roi_esperado, status_investimento
    FROM investimentos_reuniao
    WHERE status_investimento IN ('proposto', 'aprovado')
    ORDER BY custo_estimado DESC
""")

total = 0
for row in cursor.fetchall():
    print(f"[{row[4]}] {row[0]}")
    print(f"   {row[1]} — ${row[2]:.2f} (ROI: {row[3]}%)")
    total += row[2]

print(f"\nTotal Investimento: ${total:.2f}")
```

---

## 📋 Template de Reunião (Ad-hoc)

Use este template sempre que uma reunião for necessária:

```markdown
# REUNIÃO SEMANAL — Semana [X], 2026

**Data**: 2026-02-20 17:00 BRT
**Semana**: 8 | **Operador**: v0.3
**Head Financeiro**: [Nome]

## 📊 Métricas Resumidas
- PnL Semana: [X] USDT ([X]%)
- Sharpe: [X] (Δ: [+/-X] vs. semana anterior)
- Max Drawdown: [X]%
- Taxa de Acertos: [X]%
- Operações Executadas: [X]

## 🎙️ Diálogos

### HEAD 🧠:
[Pergunta 1]

### OPERADOR 🤖:
[Resposta 1]

### HEAD 🧠 (Tréplica):
[Validação 1]

---

## 📋 Feedbacks

### ✅ Força (#1)
[Descrição] — Impacto: [X]/10

### ❌ Fraqueza (#1)
[Descrição] — Impacto: [X]/10

---

## 🚀 Ações [n= ]

### AÇÃO #1 [CRÍTICA] 
O Quê: [...]
Por Quê: [...]
Impacto: [...]
Arquivo: [...]
Data Alvo: 2026-02-22

---

## 💰 Investimentos Propostos

| Tipo | Descrição | Custo | ROI | Status |
|------|-----------|-------|-----|--------|
```

---

## ✅ Boas Práticas

1. **Sempre registrar contexto**: Cada diálogo leva dados técnicos
2. **Feedbacks específicos**: Não genéricos. Anexar métricas
3. **Ações mensuráveis**: "Aumentar de X para Y" (não "melhorar")
4. **Investimentos com ROI claro**: Cada $ tem justificativa quantitativa
5. **Atualizar status regularmente**: Não deixar ações "ghost" por dias ou semanas
6. **Exportar sempre**: Manter arquivo markdown para auditoria

---

## 🐛 Troubleshooting

### "Reunião para 2026-02-20 já existe"
Você está criando uma segunda reunião para mesma data. Use:
```python
cursor.execute(
    "DELETE FROM reunioes WHERE data_reuniao = '2026-02-20 17:00:00'"
)
# Antes de criar nova
```

### "Foreign Key Constraint"
Ação referencia ação_id que não existe. Verifique:
```python
cursor.execute("SELECT id_acao FROM acoes_reuniao WHERE id_acao = ?", (id,))
print(cursor.fetchone())
```

### Banco corrompido
```bash
# Backup
cp db/reunioes_weekly.db db/reunioes_weekly_backup.db

# Resetar
rm db/reunioes_weekly.db
python scripts/reuniao_manager.py  # Recreia vazio
```

---

**Documentação Completa** — Ver `.github/copilot-instructions.md` para protocolo formal de sincronização.

