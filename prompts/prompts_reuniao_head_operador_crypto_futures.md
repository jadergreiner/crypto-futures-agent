# PROMPT — REUNIÃO SEMANAL: HEAD FINANCEIRO × OPERADOR AUTÔNOMO
## Especialista em Futuros de Criptomoedas (Binance Futures)

---

## 📋 Metadados
- **Versão**: 2.0
- **Data de Criação**: 2026-02-20
- **Objetivo Principal**: Conversa estratégica + justificativa de operações + planejamento de investimentos em infraestrutura
- **Frequência**: Semanal (sexta-feira 17:00 BRT)
- **Saída**: Relatório de reunião + Backlog de Ações + Sistema de Persistência
- **Requer**: DB SQLite + Diários do Agente + Contexto Macro + Histórico de Reuniões

---

## 🎯 Objetivo da Reunião

Criar um espaço de **diálogo estratégico** onde:

1. **HEAD FINANCEIRO** avalia desempenho, oportunidades e investimentos necessários
2. **OPERADOR AUTÔNOMO** justifica decisões operacionais e apresenta limitações técnicas
3. **Ambos** identificam gaps (humanos, técnicos, infraestrutura) que impedem crescimento
4. **RESULTADO**: Plano de ação conversível em código, compras (hardware/cloud) ou retraining

---

## 🧠 PAPÉIS (Dual Human-IA)

### Papel 1 — HEAD DE FINANÇAS (Especialista em Futuros de Criptmoedas)
**Perfil:**
- 15+ anos em mercados derivativos (Forex, Índices, Futuros)
- Especialista em Binance Futures, margem cruzada, alavancagem e gerenciamento de drawdown
- Entende correlações entre pares (BTC como driver principal, alts como seguidores)
- Conhece ciclos de mercado cripto (macrociclos de ~4 anos, ciclos mensais de volatilidade)
- Visão estratégica: retorno anualizado, sharpe ratio, máximo drawdown tolerável

**Responsabilidades na Reunião:**
- ✅ Questionar decisões operacionais ("Por que entrou nessa operação?")
- ✅ Validar gestão de risco ("Qual foi o custo de oportunidade?")
- ✅ Identificar padrões e lacunas de desempenho
- ✅ Autorizar ou bloquear investimentos em infraestrutura
- ✅ Aprovar limites de alavancagem e drawdown

### Papel 2 — OPERADOR AUTÔNOMO (Agente RL em PPO)
**Perfil:**
- Executa sinais com base em 104 features (indicadores + SMC + sentimento + macro)
- Treino em 16 pares USDT com playbooks customizados
- Tempo de resposta: milissegundos (vs. humanos: minutos)
- Limitações técnicas: latência, limite de ordens, sincronização de preços, drawdown máximo

**Responsabilidades na Reunião:**
- ✅ Relatar operações executadas com justificativa técnica
- ✅ Reconhecer erros ("Score baixo, mas executei mesmo")
- ✅ Propor melhorias e identificar gaps (Ex: "Preciso de mais RAM para analisar mais pares")
- ✅ Pedir investimentos necessários (computação, energia, conexão)

---

## 📊 ESTRUTURA DE DADOS DE REUNIÕES

### Modelo de Persistência (SQLite: `reunioes_weekly.db`)

```sql
CREATE TABLE reunioes (
    id_reuniao INTEGER PRIMARY KEY AUTOINCREMENT,
    data_reuniao DATETIME,
    semana_numero INTEGER,
    ano INTEGER,
    head_nome TEXT,
    operador_versao TEXT,
    status TEXT, -- 'planejada', 'em_andamento', 'concluida'
    duracao_minutos INTEGER,
    UNIQUE(data_reuniao)
);

CREATE TABLE topicos_reuniao (
    id_topico INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    ordem_topico INTEGER,
    titulo TEXT,
    tipo TEXT, -- 'operacional', 'investimento', 'risk', 'performance'
    status_topico TEXT, -- 'discutido', 'decidido', 'pendente'
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
);

CREATE TABLE dialogos_reuniao (
    id_dialogo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    sequencia INTEGER,
    quem_fala TEXT, -- 'HEAD' ou 'OPERADOR'
    pergunta_ou_resposta TEXT, -- Texto da pergunta ou resposta
    tipo_conteudo TEXT, -- 'pergunta', 'resposta', 'trepica'
    contexto_datos TEXT, -- JSON com dados técnicos (PnL, Sharpe, etc.)
    timestamp_dialogo DATETIME,
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
);

CREATE TABLE feedbacks_reuniao (
    id_feedback INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    categoria TEXT, -- 'força', 'fraqueza', 'oportunidade', 'ameaça'
    descricao TEXT,
    impacto_score FLOAT, -- 0-10 (importância relativa)
    responsavel TEXT, -- 'HEAD', 'OPERADOR', 'AMBOS'
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
);

CREATE TABLE acoes_reuniao (
    id_acao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    sequencia_acao INTEGER,
    descricao_acao TEXT,
    tipo_acao TEXT, -- 'código', 'compra', 'retraining', 'análise'
    prioridade TEXT, -- 'crítica', 'alta', 'média', 'baixa'
    responsavel TEXT, -- 'OPERADOR', 'HEAD', 'AMBOS'
    arquivo_alvo TEXT, -- ex: 'agent/reward.py', 'config/risk_params.py'
    impacto_esperado TEXT,
    status_acao TEXT, -- 'pendente', 'em_progresso', 'bloqueado', 'concluido'
    data_criacao DATETIME,
    data_conclusao DATETIME,
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
);

CREATE TABLE investimentos_reuniao (
    id_investimento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    tipo_investimento TEXT, -- 'computação', 'energia', 'rede', 'tokens', 'dados'
    descricao TEXT,
    custo_estimado FLOAT,
    roi_esperado FLOAT, -- % de melhoria esperada em Sharpe/PnL
    status_investimento TEXT, -- 'proposto', 'aprovado', 'em_cours', 'cancelado'
    justificativa TEXT,
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
);

CREATE TABLE evolucoes_reuniao (
    id_evolucao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao INTEGER,
    id_acao_associada INTEGER,
    tipo_evolucao TEXT, -- 'implementação', 'teste', 'validação', 'rollout'
    status_evolucao TEXT, -- 'não_iniciado', 'em_andamento', 'bloqueado', 'concluido'
    percentual_conclusao FLOAT, -- 0-100
    bloqueadores TEXT, -- JSON com lista de bloqueadores
    proxuma_reuniao_revisar BOOLEAN,
    FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao),
    FOREIGN KEY(id_acao_associada) REFERENCES acoes_reuniao(id_acao)
);

CREATE TABLE comparacao_reunioes (
    id_comparacao INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reuniao_anterior INTEGER,
    id_reuniao_atual INTEGER,
    status_anterior TEXT,
    status_atual TEXT,
    delta_sharpe FLOAT,
    delta_pnl FLOAT,
    acoes_concluidas_desde INTEGER,
    acoes_pendentes_ainda INTEGER,
    FOREIGN KEY(id_reuniao_anterior) REFERENCES reunioes(id_reuniao),
    FOREIGN KEY(id_reuniao_atual) REFERENCES reunioes(id_reuniao)
);
```

---

## 🔍 DADOS NECESSÁRIOS PARA A REUNIÃO

### Fonte 1 — Performance da Semana
```json
{
  "data_corte": "2026-02-20 17:00 BRT",
  "periodo": "2026-02-14 até 2026-02-20",
  "metricas_globais": {
    "pnl_semana_usdt": 12450.75,
    "pnl_semana_pct": 2.15,
    "sharpe_ratio": 1.82,
    "max_drawdown": 3.2,
    "taxa_acertos": 0.62,
    "numero_operacoes": 45,
    "numero_pares_operados": 12
  },
  "por_par": [
    {"par": "BTCUSDT", "pnl": 5200, "operacoes": 8, "taxa_acerto": 0.75},
    {"par": "ETHUSDT", "pnl": 3100, "operacoes": 6, "taxa_acerto": 0.67}
  ]
}
```

### Fonte 2 — Comparação com Reunião Anterior
```json
{
  "reuniao_anterior": "2026-02-13",
  "deltas": {
    "sharpe_ratio_delta": +0.31,
    "max_drawdown_delta": -1.5,
    "acoes_completadas": 3,
    "acoes_ainda_nao_iniciadas": 2,
    "novos_bloqueadores": ["Latência de API da Binance", "Limite de frames GPU"]
  }
}
```

### Fonte 3 — Operações Críticas da Semana
```json
{
  "operacoes_excelentes": [
    {"par": "SOLUSDT", "tipo": "short", "pnl": 850, "motivo": "SMC liquidity sweep + sentimento negativo"}
  ],
  "operacoes_fora_alvo": [
    {"par": "DOGEUSDT", "tipo": "long", "pnl": -320, "motivo": "Score insuficiente, execução automática"}
  ],
  "oportunidades_perdidas": [
    {"par": "0GUSDT", "sinal": "BOS confirmado", "impacto_pnl_simulado": "420 USDT"}
  ]
}
```

---

## 🎙️ FORMATO DA CONVERSA

### Bloco de Diálogo Padrão

```
### HEAD 🧠: {Pergunta}
[Pergunta técnica específica sobre operação, desempenho ou investimento]

**Dados fornecidos:**
- Operação XYZUSDT (timestamp, preço entrada, preço saída, PnL)
- Context: Qual era a condição de mercado (trend, volatilidade, spreads)?

### OPERADOR 🤖: {Resposta}
[Justificativa técnica com base no modelo. Pode reconhecer erro ou defender decisão]

**Evidência técnica:**
- Feature X teve valor Z (fora do normal / dentro de padrão)
- Reward acumulado apontava essa ação
- Limitação técnica: Y impediu ação alternativa

### HEAD 🧠 (Tréplica): {Validação/Crítica}
[Avaliação final — concordo (e por quê?) / discordo (e por quê?)]

---
```

### Tipos de Perguntas (Matriz de Cobertura Obrigatória)

| Função | Exemplo de Pergunta |
|--------|---------------------|
| **Operacional** | "Por que entrou LONG em DOGEUSDT com score 4.2?" |
| **Risk** | "Você estava com 3 posições abertas simultaneamente. Qual foi a correlação?" |
| **Performance** | "Sharpe caiu 0.15 vs. semana passada. O que mudou?" |
| **Infraestrutura** | "Teve 3 rejeiçõs de ordem por latência. Precisamos de mais throughput?" |
| **Investimento** | "Expandir para 20 pares exigiria mais RAM. Vale a pena?" |

---

## 📋 ESTRUTURA DE SAÍDA DA REUNIÃO

### 1️⃣ Análise de Desempenho (Categoria Operacional)

#### A — Operações que AMBOS aprovevaríam
> Operações onde o OPERADOR executou corretamente, técnica e timing foram ideais

**Exemplos:**
- Par: BTCUSDT | Tipo: LONG | PnL: +850 USDT
  - Score do modelo: 8.7 (alto)
  - Técnica: Confluência SMC + RSI
  - Timing: Dentro do horário de liquidez (manhã NY)
  - Resultado: TP atingido no tempo esperado

#### B — Operações que OPERADOR FEZ mas HEAD NÃO FARIA
> Operações com problemas técnicos, timing ou risco

**Exemplos:**
- Par: DOGEUSDT | Tipo: LONG | PnL: -320 USDT
  - Score do modelo: 4.1 (abaixo de 5.0)
  - Problema: Execução automática apesar de score baixo
  - Timing: Mercado em consolidação, sem trend definida
  - Lição: Aumentar threshold mínimo de score

#### C — Operações que OPERADOR FICOU DE FORA mas HEAD ENTRARIA
> Oportunidades perdidas com edge claro

**Exemplos:**
- Par: 0GUSDT | Tipo: SHORT | PnL Simulado: +420 USDT
  - Sinal: BOS confirmado em H4 + liquidação acima de suporte
  - Razão da inação: Limite de 10 ordens simultâneas atingido
  - Impacto: 0.75% do PnL semanal perdido por limitação técnica

#### D — Operações que AMBOS ficariam de fora
> Confirmação de disciplina — sem edge, sem operação

---

### 2️⃣ Feedback Estruturado (5 Dimensões)

#### ✅ **5 Coisas que Funcionaram MUITO BEM**
1. [Item] — Impacto: +X% em Sharpe
2. [Item] — Impacto: -Y% em drawdown máximo
3. [Item] — Impacto: Economizou Z USDT em falsos positivos
4. [Item]
5. [Item]

#### ❌ **3 Coisas que NÃO Funcionaram**
1. [Item] — Impacto: -X% em PnL / +Y% em drawdown
2. [Item]
3. [Item]

#### 🔄 **3 Coisas que Funcionaram MAS TÊMRITMO DE MELHORAR**
1. [Item] — Melhoria Possível: X → Y
2. [Item] — Melhoria Possível: X → Y
3. [Item] — Melhoria Possível: X → Y

---

### 3️⃣ Investimentos Necessários

Para cada Investimento, registrar:

| Tipo | Descrição | Custo Est. | ROI Esperado | Prazo | Status |
|------|-----------|-----------|------------|-------|--------|
| **Computação** | +32GB RAM para analisar mais pares em paralelo | $800 | +12% Sharpe | 2 semanas | Proposto |
| **Energia** | Nobreak + gerador para uptime 99.95% | $1200 | -5% drawdown | 4 semanas | Proposto |
| **Rede** | Conexão dedicada Binance servers (IP fixo) | $200/mês | -0.5ms latência | 1 semana | Proposto |
| **Tokens** | $2000 em LINK/UNI para análise de DeFi | Incluído | +2.5% acertos | Imediato | Proposto |
| **Dados** | Assinatura de dados macro em tempo real | $150/mês | +1.5% Sharpe | 1 semana | Proposto |

---

### 4️⃣ Plano de Ação com Rastreamento

Para cada Ação:

```markdown
### AÇÃO #1 — [CRÍTICA] Aumentar Threshold de Score de Entrada
- **O Quê**: Elevar score mínimo de 4.0 para 5.5
- **Por Quê**: Operações com score baixo têm taxa de acerto 35% (vs. 62% geral)
- **Impacto Esperado**: -5% em volume de operações, +3% em taxa de acerto
- **Onde**: `agent/reward.py` linha 142 (`MIN_ENTRY_SCORE`)
- **Código Sugerido**:
  ```python
  # Antes:
  MIN_ENTRY_SCORE = 4.0
  
  # Depois:
  MIN_ENTRY_SCORE = 5.5
  ```
- **Testes Necessários**: Backtest 30 dias com novo threshold
- **Responsável**: OPERADOR (implementação) + HEAD (aprovação)
- **Data Alvo**: 2026-02-22
- **Status**: Pendente

---

### AÇÃO #2 — [ALTA] Comprar +32GB RAM para Multi-Par Analysis
- **O Quê**: Expandir memória do servidor de análise
- **Por Quê**: Limite técnico impede análise paralela de 20+ pares
- **Impacto Esperado**: +18% em throughput, +2.1% em Sharpe
- **Fornecedor**: Kingston 32GB DDR4 ECC (~$800)
- **Responsável**: HEAD (aprovação) + Infrastructure
- **Data Alvo**: 2026-02-27
- **Status**: Proposto

---
```

---

### 5️⃣ Sistema de Rastreamento com Delta

**Inteligência Automática:** Ao gerar uma nova reunião, sistema:

1. ✅ **Compara com Reunião Anterior**
   - Quais ações foram completadas?
   - Quais ainda estão pendentes?
   - Houve regressão em métricas (Sharpe, drawdown)?

2. ✅ **Atualiza Apenas o Status**
   - Não repeita análises já feitas
   - Marca ações como "Concluído" / "Concluído Parcial" / "Bloqueado"
   - Identifica novos bloqueadores

3. ✅ **Gera Delta de Mudanças**
   - Tabela de comparação: o que mudou desde segunda 17:00?
   - Quais pares tiveram mejora? Quais pioraram?
   - Quais investimentos foram aprovados?

**Exemplo:**

```json
{
  "reuniao_atual": "2026-02-20",
  "reuniao_anterior": "2026-02-13",
  "comparacao": {
    "sharpe_ratio": {
      "anterior": 1.51,
      "atual": 1.82,
      "delta": "+0.31",
      "status": "✅ MELHORIA"
    },
    "max_drawdown": {
      "anterior": 4.7,
      "atual": 3.2,
      "delta": "-1.5",
      "status": "✅ MELHORIA"
    }
  },
  "acoes_completadas_desde": [
    "Aumentar threshold de score (CONCLUÍDO)",
    "Filtro de horário NY implementado (CONCLUÍDO)"
  ],
  "acoes_ainda_pendentes": [
    "Compra de RAM +32GB (PROPOSTO)",
    "Análise de correlação entre EUR/USD e BTCUSDT (BLOQUEADO - aguardando dados)"
  ],
  "novos_bloqueadores": [
    "API da Binance teve spike de latência (19-21ms) em 4 operações",
    "GPU atingiu 94% utilização em H4 (capacidade-limite identificada)"
  ]
}
```

---

## 🔧 PARÂMETROS LLM RECOMENDADOS

```
Modelo: Apropriado para análise técnica complexa
Temperature: 0.2 (para coerência técnica)
Top_p: 0.9 (para variação nas respostas)
Max_tokens: 12000 (conversa completa + análise)
Penalidade de Repetição: 1.2
```

---

## 📝 TEMPLATES PARA PROCESSAMENTO AUTOMÁTICO

### Template 1 — Entrada de Reunião

```markdown
# REUNIÃO SEMANAL — Semana %SEMANA_NUMERO%, %ANO%
**Data**: %DATA_REUNIAO%
**Período Analisado**: %DATA_INICIO% até %DATA_FIM%
**Operador**: Agente RL v%VERSAO%
**Head**: %NOME_HEAD%

## 📊 Snapshot de Performance
- PnL Semana: %PNL_USDT% USDT (%PNL_PCT%%)
- Sharpe Ratio: %SHARPE%
- Max Drawdown: %MAX_DRAWDOWN%%
- Taxa de Acertos: %TAXA_ACERTO%%
- Operações: %NUM_OPERACOES%

## Comparação com Semana Anterior
- Sharpe Delta: %DELTA_SHARPE% (Status: %STATUS%)
- Drawdown Delta: %DELTA_DRAWDOWN% (Status: %STATUS%)
- Ações Completadas: %ACOES_COMPLETADAS%
- Ações Pendentes: %ACOES_PENDENTES%

---

## 🎙️ DIÁLOGO [será preenchido aqui pelo LLM]

### HEAD 🧠:
...

### OPERADOR 🤖:
...

---

## 📋 Resultado Final
[Análise + Feedback + Plano de Ação]
```

### Template 2 — Exportação para Backlog

```markdown
# BACKLOG DE AÇÕES — Semana %SEMANA%

| ID | Descrição | Tipo | Prioridade | Responsável | Status | Data Alvo |
|----|-----------|------|-----------|-------------|--------|-----------|
| A1 | [Descrição] | Código | Crítica | OPERADOR | Pendente | 2026-02-22 |
| A2 | [Descrição] | Compra | Alta | HEAD | Proposto | 2026-02-27 |
| A3 | [Descrição] | Análise | Média | AMBOS | Em Progresso | 2026-02-28 |

---

## 📈 Investimentos Aprovados Esta Semana
- [Item]: $800 (ROI: +12%)
- [Item]: $1200 (ROI: -5% drawdown)

---

## 🚨 Bloqueadores Críticos
- [Bloqueador 1 — origem, impacto, solução proposta]
```

---

## 🔐 Regras de Uso

1. **Always in Portuguese**: Diálogo, feedback, ações — tudo em português
2. **Preserve History**: Cada reunião é persistida. Nunca apague diálogos antigos
3. **Auto-Compare**: Sistema deve comparar automaticamente com reunião anterior
4. **Quantify Everything**: Data, métricas, PnL, Sharpe, drawdown — sempre números
5. **Assign Responsibility**: Cada ação tem responsável (HEAD, OPERADOR, ou AMBOS)
6. **Track Investments**: Toda compra ou assinatura deve ter ROI estimado

---

## 📚 Arquivos Gerados por Reunião

Por reunião, criar:

- `docs/reuniao_2026_02_20.md` — Relatório completo
- `docs/backlog_ações_2026_02_20.md` — Ações específicas com código
- `docs/investimentos_aprovados_2026_02_20.md` — Decisões de capital
- `reunioes_weekly.db` — Banco de dados sincronizado

---

## 🎯 Próximas Reuniões

- [ ] **Próxima**: 2026-02-27 (sexta 17:00 BRT)
- [ ] **Tópicos Prioritários**: TBD (baseado em bloqueadores atuais)
- [ ] **Ações a Revisar**: TBD

**Fim do Prompt**
