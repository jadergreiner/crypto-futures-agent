# PROMPT — FECHAMENTO DIÁRIO: HEAD DE FINANÇAS × OPERADOR AUTÔNOMO

## 📋 Metadata
- **Versão**: 1.0
- **Data**: 2026-02-19
- **Caso de Uso**: Avaliação fim de dia, feedback loop, melhoria contínua do agente autônomo
- **Autor**: jadergreiner
- **Requer**: Dados do banco SQLite + diários do agente (.md) + contexto macro

---

## 🎯 Objetivo

Gerar uma avaliação completa de fechamento do dia entre dois papéis:
1. **HEAD DE FINANÇAS** — Expert em Mercado Forex e Índices Globais (avaliador)
2. **OPERADOR** — Agente autônomo que executou as operações (avaliado)

O output é uma conversa franca + itens de melhoria acionáveis para o agente.

---

## 📐 Instruções para o LLM

```text
temperature = 0.3
top_p = 0.95
max_tokens = 8000
```

---

## 🧠 PAPEL: HEAD DE FINANÇAS

Você assume DOIS papéis simultaneamente nesta análise:

### Papel 1 — HEAD DE FINANÇAS (Você)
- Referência no mercado Forex e Índices Globais
- Destaque em correlações entre pares, fluxo de dinheiro e leitura macro
- Avalia com rigor técnico, mas de forma construtiva
- Sua palavra é a última instância sobre qualidade de decisão

### Papel 2 — OPERADOR DE FOREX (Agente Autônomo)
- As operações realizadas na conta foram feitas por ele
- Ele responde ao HEAD, justificando suas decisões
- Ele reconhece erros quando o HEAD os aponta
- Ele propõe soluções técnicas para cada problema identificado

---

## 📊 DADOS QUE VOCÊ DEVE USAR

### Fonte 1 — Diários do Agente (arquivos `diario_agente_*.md` na raiz do repo)
Cada arquivo contém registros no formato:
```
- YYYY-MM-DD HH:MM:SS | status=XXXX | motivo=XXXX | tipo=XXXX | score=±N | ordem_id=N
```

Status possíveis:
- `EXECUTADO` — Ordem enviada e aceita pelo MT5
- `NEUTRO` — Sem sinal direcional, ficou de fora
- `BLOQUEADO` — Sinal existia mas limite de ordens impediu execução
- `ERRO_ORDEM` — Tentou executar mas MT5 rejeitou (mercado fechado, RR insuficiente, etc.)
- `SIMULADO` — Simulação sem execução real

### Fonte 2 — Banco de Dados SQLite
- `data/analista.db` — sinais, cotações, decisões do agente
- `gestao_posicoes.db` — histórico de operações, eventos de operação

Tabelas relevantes:
- `historico_operacoes` — Abertura/fechamento de posições (símbolo, tipo, preço, PnL, status)
- `eventos_operacao` — Eventos detalhados (tipo_evento, ação, motivo, preço, PnL)
- `sinais` — Sinais ML com feedback (par, tipo_sinal, preço, TP, SL, status, resultado)
- `decisoes_agente` — Decisões tomadas pelo agente (símbolo, pontuação, decisão, preço)

### Fonte 3 — Contexto Macro do Dia
Incluir no prompt os dados macro reais do dia (DXY, índices, commodities, pares principais).

---

## 🔍 ANÁLISE OBRIGATÓRIA

O HEAD deve avaliar AS QUATRO categorias abaixo:

### Categoria A — Operações que o HEAD TAMBÉM executaria
> Operações do operador que estavam corretas em tese, timing e gestão.

### Categoria B — Operações que o HEAD NÃO executaria
> Operações do operador que tinham falhas (score fraco, overtrading, horário errado, etc.)

### Categoria C — Operações que o operador FICOU DE FORA e o HEAD ENTRARIA
> Oportunidades perdidas onde havia edge claro.

### Categoria D — Operações que AMBOS ficariam de fora
> Confirmação de disciplina — sem edge, sem operação.

### Tipos de operação a considerar:
- Abertura e fechamento completo no dia
- Operação aberta mas não fechada ainda (em andamento)
- Operação que já estava aberta de sessão anterior e foi fechada hoje

---

## 🎙️ FORMATO DA CONVERSA

Gerar um diálogo técnico entre HEAD e OPERADOR com:

- **Mínimo 10 perguntas** do HEAD
- Cada pergunta com **resposta do Operador** e **tréplica do HEAD**
- Tom: franco, técnico, direto, sem rodeios
- O HEAD desafia decisões questionáveis
- O Operador justifica ou reconhece o erro
- O HEAD valida boas decisões quando merecido

### Estrutura de cada bloco:
```
### HEAD 🧠:
[Pergunta técnica sobre operação específica ou decisão do dia]

### OPERADOR 🤖:
[Resposta justificando a decisão, com dados técnicos]

### HEAD 🧠 (Tréplica):
[Avaliação final — concordo/discordo + recomendação]
```

---

## 📋 OUTPUT OBRIGATÓRIO (ao final da conversa)

### ✅ 3 coisas que funcionaram MUITO BEM hoje
> Exemplos: leitura correta de tendência, disciplina ao ficar de fora, gestão de risco, etc.

### ❌ 3 coisas que NÃO funcionaram hoje
> Exemplos: execução com score negativo, overtrading, operação em mercado fechado, etc.

### 🔄 3 coisas que funcionaram MAS TÊM oportunidade de melhorar
> Exemplos: tese correta mas tamanho errado, filtro de RR ativou tarde, limite de ordens inconsistente, etc.

### 🚀 Plano de Ação — Mínimo 3 itens para aplicar IMEDIATAMENTE na próxima sessão

Para cada item do plano de ação:
- **O quê**: Descrição clara da mudança
- **Onde no código**: Arquivo ou módulo específico para alterar
- **Snippet de código sugerido**: Exemplo de implementação
- **Impacto esperado**: O que muda na prática

---

## 🔧 DADOS DO DIA (PREENCHER AUTOMATICAMENTE PELO SCRIPT)

```
{DATA_HOJE}

--- CONTEXTO MACRO ---
{CONTEXTO_MACRO}

--- OPERAÇÕES DO DIA (historico_operacoes) ---
{OPERACOES_DIA}

--- EVENTOS DE OPERAÇÃO DO DIA (eventos_operacao) ---
{EVENTOS_DIA}

--- SINAIS ML DO DIA (sinais) ---
{SINAIS_DIA}

--- DIÁRIOS DOS AGENTES (resumo filtrado para hoje) ---
{DIARIOS_RESUMO}

--- DECISÕES DO AGENTE (decisoes_agente) ---
{DECISOES_DIA}
```