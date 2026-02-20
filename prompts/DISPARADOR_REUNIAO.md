# Disparador de Reunião — Chamar a Reunião Com Contexto

## O que é?

Documento executável que chama o motor de reunião ad-hoc com **contexto opcional de mercado ou operacional**.

Sempre que você vir um movimento importante ou tiver questionamentos sobre a operação, dispara uma reunião instantânea entre o **Head Financeiro** e o **Operador Autônomo**.

---

## Como Usar

### 1. Reunião Simples (Sem Contexto)

Despara reunião imediatamente com status operacional:

```bash
python scripts/disparador_reuniao.py
```

**Resultado:**
- Cria registro em `db/reunioes.db`
- Executa 7-step workflow
- Exporta markdown em `docs/reuniao_[timestamp].md`

---

### 2. Reunião Com Contexto de Mercado

Passa observação de mercado para discussão:

```bash
python scripts/disparador_reuniao.py \
  --contexto "BTC caiu 15%, FVG aberto em H4, sinal bearish em Daily"
```

**O que acontece:**
1. Sistema registra o contexto observado
2. Head analisa: "Seria entrada em que timeframe?"
3. Operador explica: "Rejeitei 3 setup, aguardando pull-back"
4. Tréplica: Ajustes necessários

---

### 3. Reunião Com Problemas Técnicos

Quando há latência, rejeições ou falhas:

```bash
python scripts/disparador_reuniao.py \
  --contexto "3 rejeições de ordem hoje, latência 45-60ms em Binance"
```

**Output:**
- Debate sobre cause root (API, network, posição?)
- Plano de ação para mitigação
- Possível investimento (upgrade server, redundância)

---

### 4. Reunião Para Aprovar Investimento

Propõe novo hardware ou integração:

```bash
python scripts/disparador_reuniao.py \
  --contexto "Proposta: RAM 32GB para cache ML, custo R$4.2k, ROI +12%"
```

**Resultado:**
- Head avalia ROI vs. risco
- Operador justifica necessidade
- Registra decisão + timeline implementação

---

### 5. Reunião Com Nome Customizado

Se o Head mudou ou há transição:

```bash
python scripts/disparador_reuniao.py \
  --head "Carlos Rafael" \
  --operador "v0.4beta" \
  --contexto "Teste de nova versão do RL agent"
```

---

## Exemplos Práticos

### Exemplo A: Movimento de Mercado

```bash
python scripts/disparador_reuniao.py \
  --contexto "ETH pump 8% em 4h, volatilidade acima histórica, 3 liquidações de shorts"
```

**Diálogo gerado:**
```
HEAD: "Você entrou nessas 3 velas?"
OP: "Sim, 0.5 BNB LONG + 1 ETH SHORT hedge"
HEAD: "Razão para short ETH com pump?"
OP: "Divergência Stoch em H1, expectativa pullback"
AÇÃO: Monitorar suportes 2400, 2350 para stop loss
```

### Exemplo B: Erro de Máquina

```bash
python scripts/disparador_reuniao.py \
  --contexto "Websocket desconectou 2x em 30min, perdemos sinal ao vivo"
```

**Resultado:**
```
HEAD: "Impacto?"
OP: "Parei operação em BTC/USDT por 8 minutos"
HEAD: "Plano?"
OP: "Implementar fallback + heartbeat custom (3 dias)"
INVESTIMENTO: Servidor secundário + health check (R$ 2k)
```

### Exemplo C: Performance Questionável

```bash
python scripts/disparador_reuniao.py \
  --contexto "Sharpe caiu de 1.8 para 1.2 em 1 semana, Win rate 42%"
```

**Output:**
```
FEEDBACK:
- Fraqueza: Parâmetros defasados pro mercado volatilidade atual
- Oportunidade: Retreinar com últimos 30 dias dados
- Ação: Backteste novo modelo vs. live (2 dias)
```

---

## Estrutura Técnica

### Script Disparador
- **Arquivo:** `scripts/disparador_reuniao.py`
- **Classe:** Envolve `ExecutorReuniao` do motor
- **Parâmetros:** Contexto, Head, Operador versão, data/hora
- **Output:** Reunião registrada + Markdown exportado

### Motor Base
- **Arquivo:** `scripts/executar_reuniao_semanal.py` → classe `ExecutorReuniao`
- **7-Step Workflow:**
  1. Carregar métricas performance
  2. Buscar reunião anterior para comparação
  3. Montar contexto de prompt
  4. Criar registro reunião em DB
  5. Adicionar diálogos + feedbacks + ações + investimentos
  6. Exportar relatório markdown
  7. Imprimir resumo executivo

### Banco de Dados
- **Arquivo:** `db/reunioes.db` (SQLite3)
- **Tabelas:** 8 tabelas (reunioes, dialogos, feedbacks, acoes, investimentos, comparacao, evolucoes, topicos)
- **Query:** Busca automática de reunião anterior para delta Sharpe/PnL

---

## Integração Com Contexto

### Usando Contexto em Python

Se quiser disparar reunião programaticamente com contexto:

```python
from scripts.executar_reuniao_semanal import ExecutorReuniao
from datetime import datetime

executor = ExecutorReuniao(
    data_reuniao=datetime.now().isoformat(sep=" ")
)

# Carregar contexto customizado
contexto = "BTC +12%, Volume 2x media, FVG acima"

# ✅ Disparar reunião
executor.executar_fluxo_completo()

# Contexto será registrado automaticamente nos dados da reunião
```

### Salvando Contexto Explicitamente

Dentro do `ExecutorReuniao`, o contexto é passado para a tabela `topicos_reuniao`:

```python
db.criar_topico_reuniao(
    id_reuniao=1,
    topico=contexto,
    tipo_topico="mercado"  # ou "tecnico", "investimento", "performance"
)
```

---

## Timeline Esperada

| Ação | Duração |
|------|---------|
| Disparar reunião | < 1 seg |
| Carregar métricas | 3-5 seg |
| Gerar diálogos (LLM) | 15-30 seg (manual: < 5 seg) |
| Salvar no BD | < 1 seg |
| Exportar markdown | 2-3 seg |
| **Total** | **~20-40 seg** |

---

## Checklist Para Disparar Reunião

Antes de disparar, considere:

- [ ] Contexto é específico? (ex: "BTC +15% em 4h" vs. "mercado subiu")
- [ ] Data/hora está correta?
- [ ] Head/Operador identificados?
- [ ] Tipo de reunião claro? (performance / mercado / técnico / investimento)
- [ ] Informações confidenciais? (não incluir API keys, senhas)

---

## Outputs Gerados

### 1. Registro em Banco
```
db/reunioes.db
├── reunioes (ID, data, head, operador)
├── dialogos_reuniao (pergunta, resposta, tréplica)
├── feedbacks_reuniao (força, fraqueza, oportunidade, ameaça, ritmo)
├── acoes_reuniao (descrição, prioridade, responsável, arquivo_alvo)
├── investimentos_reuniao (tipo, custo, roi, justificativa)
├── topicos_reuniao (contexto passado)
├── comparacao_reunioes (delta vs. anterior)
└── evolucoes_reuniao (histórico estado do agente)
```

### 2. Relatório Markdown
```
docs/reuniao_2026_02_20_20_15_31.md
├── # Reunião Head × Operador [timestamp]
├── ## Contexto Observado
├── ## Diálogos
├── ## Feedbacks
├── ## Ações Planejadas
├── ## Investimentos Propostos
├── ## Comparação Com Reunião Anterior
└── ## Próximos Passos
```

### 3. Log Executivo
```
✅ Reunião disparada com sucesso!
   ID: 1
   Head: Roberto Silva
   Operador: v0.3
   Contexto: "BTC caiu 15%..."
   Arquivo: docs/reuniao_2026_02_20_20_15_31.md
```

---

## Troubleshooting

### "Script não encontrado"
```bash
# Garantir que você está no diretório correto
cd c:\repo\crypto-futures-agent

# Depois rodar
python scripts/disparador_reuniao.py
```

### "Erro ao conectar BD"
```bash
# Verificar se db/ existe
dir db/

# Se não existir, criar
mkdir db

# Rodar script novamente (vai inicializar BD)
python scripts/disparador_reuniao.py
```

### "Contexto muito longo"
- Máximo de caracteres é ~1000 (recomendado: 100-200)
- Ser específico ajuda (data hora movimento observado, não longa história)

---

## Referência Rápida

```bash
# Sem contexto
python scripts/disparador_reuniao.py

# Com contexto simples
python scripts/disparador_reuniao.py --contexto "BTC caiu 10%"

# Com múltiplos parâmetros
python scripts/disparador_reuniao.py \
  --head "Carlos" \
  --operador "v0.4" \
  --contexto "Teste novo modelo RL com reward customizado"

# Ver help
python scripts/disparador_reuniao.py --help
```

**Próximo Destino:** Veja [GUIA_REUNIOES_SEMANAIS.md](../docs/GUIA_REUNIOES_SEMANAIS.md) para análise profunda de cada etapa de reunião.
