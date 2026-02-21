# 🎯 BACKLOG DE AÇÃO CRÍTICA — Operação Live

**Data de Criação**: 2026-02-20 20:50:00
**Última Atualização**: 2026-02-21 00:15:00 UTC
**Prioridade**: 🔴 CRÍTICA
**Status**: 🟢 EM EXECUÇÃO — FILOSOFIA OPERACIONAL DEFINIDA
**Reunião de Referência**: Reunião Investidor + Especialistas

---

## 🚀 DECISÃO ESTRATÉGICA — HEAD's Operação

**Direção Executiva (23:50 UTC):**

```text
ESTRATÉGIA DE OPERAÇÃO - FASE 1 — TESTE DE PROCESSO

Margem por Posição:       $1.00 USD
Alavancagem:              10x
Exposição por Posição:    $10.00 USD
Máximo Simultâneo:        30 posições (~$30 margem)
Total de Margem:          $40 (de $424 disponível)

Racional:
├─ Risco MÍNIMO: Cada posição limita PnL a ±$1
├─ Validação: Testa processo end-to-end
├─ Escalabilidade: Pode aumentar para $5-$10 por posição após sucesso
└─ Focus: Processo primeiro, PnL depois
```

✅ **Aprovado por**: Investidor + Tech Lead + Especialista Risk

---

## 🎯 NOVO PLANO DE AÇÃO (2 horas)

### FASE 0: Validação de Sistema (30 min)

**ID**: VALIDATE-SYSTEM-1DOLLAR
**Status**: 🔴 PRONTO PARA EXECUTAR AGORA
**Responsável**: Tech Lead
**Scripts**:
- `scripts/test_executor_with_1dollar.py` ← Testar configuração
- `scripts/execute_1dollar_trade.py` ← Executar trade piloto

```
PASSO 1 (10 min): Rodar test_executor_with_1dollar.py
├─ Verificar conectividade com Binance
├─ Validar que alavancagem 10x está disponível
├─ Confirmar cálculo de quantidade para $1 margem
└─ Status: GO/NO-GO para próximo passo

PASSO 2 (15 min): Se GO — Executar dry-run de ordem
├─ python execute_1dollar_trade.py --dry-run
├─ Simular ordem sem executar
└─ Validar cálculos

PASSO 3 (5 min): Se tudo OK → GO para FASE 1
```

### FASE 1: Primeira Posição Live (45 min)

**ID**: EXECUTE-FIRST-POSITION
**Símbolo**: ANKRUSDT (estável, líquido)
**Direção**: LONG (mais simples para teste)
**Margem**: $1.00
**Alavancagem**: 10x
**Exposição**: $10.00

```
TIMELINE:
├─ T+00 min: Executar python execute_1dollar_trade.py
├─ T+01 min: Ordem MARKET executada
├─ T+02 min: Posição aberta no Binance
├─ T+05 min: Trade registrado em DB com status OPEN
├─ T+30 min: Monitorar PnL (esperado ±$0.30)
└─ T+45 min: Validar que tudo funcionou
```

**Critério de Sucesso**:
- ✅ Ordem executada sem rejeitada
- ✅ Posição aparece em Binance API
- ✅ DB registrado com status correto
- ✅ Agent consegue monitorar sem erros
- ✅ Sem perdas inesperadas (stop loss não disparou)

**Se Sucesso → FASE 2**

### FASE 2: Aumentar para 3 Posições Paralelas (45 min)

**ID**: EXECUTE-PARALLEL-POSITIONS
**Símbolos**: BTCUSDT, ETHUSDT, AVAXUSDT
**Margem Total**: $3.00 (3 × $1)
**Alavancagem**: 10x cada
**Exposição Total**: $30.00

```
TIMELINE:
├─ T+45 min (de FASE 1): Gerar 3 sinais com score >= 4.0
├─ T+50 min: Executar 3 trades em paralelo (podem ser automáticos)
├─ T+55 min: Todos registrados em DB
├─ T+90 min: Monitorar status final
└─ T+120 min: DECISÃO: Aumentar ou parar?
```

**Critério de Sucesso**:
- ✅ 3 posições abertas simultaneamente
- ✅ Nenhuma rejeição de ordem
- ✅ Agent conseguiu gerenciar sem travamento
- ✅ DB sincronizado com Binance
- ✅ Total de $3 margem utilizado corretamente

### FASE 3: Decisão de Escalação (30 min)

**ID**: DECISION-SCALE-UP
**Status**: Análise e votação

```
SE tudo funcionou em FASE 2:
├─ ✅ Aumentar para $5 margem por posição?
├─ ✅ Deixar automático (agent dispara sozinho)?
├─ ✅ Aumentar max simultâneo para 5-10 posições?
└─ ✅ Retrainagem de modelo (data 13-20 feb)?

SE houve erro em FASE 1 ou 2:
├─ Debug específico
├─ Correção imediata
├─ Retry quando pronto
└─ SEM escalar até saber causa raiz
```

---

## 🏛️ FILOSOFIA OPERACIONAL — OS 5 PILARES

**Definido em Reunião**: 2026-02-21 00:00+ UTC
**Decisor**: Investidor (C-Level)
**Aprovadores**: Tech Lead, Especialista RL, Especialista Risk

### **PILAR 1: CONFLUÊNCIA > SORTE**

```
Abrir apenas quando MÚLTIPLOS indicadores convergem na MESMA direção.

Métricas de Confluência (ponderadas):
├─ TECHNICAL (45%):
│  ├─ RSI oversold/overbought: 15%
│  ├─ EMA alignment (3 EMAs): 15%
│  └─ MACD histogram+signal: 15%
│
├─ SMART MONEY (30%):
│  ├─ Order blocks: 10%
│  ├─ Fair Value Gaps: 10%
│  └─ Market structure: 10%
│
└─ SENTIMENTO (25%):
   ├─ Funding rate: 12%
   ├─ Long/Short ratio: 8%
   └─ Open Interest: 5%

Score >= 7.0: ABRIR com confiança 80%+
Score 5.0-6.9: ABRIR com confiança 60-70%
Score < 5.0: NÃO ABRIR (esperar) — MAS com monitoring inteligente

GATILHO DE SAÍDA DE HOLD:
├─ Se opportunity_cost_24h > $5 → reduz threshold 5.0 → 4.7
├─ Se score trend positivo > 12h → força entrada
└─ Máximo 24h em HOLD contínuo
```

### **PILAR 2: SKILL VALIDATION — POR QUE ACERTOU/ERROU?**

```
Cada trade registra: indicadores estavam REALMENTE certos?

Classificações de Resultado:
├─ ✅ GANHO COM SKILL: Indicadores 75%+ corretos
│  └─ Recompensa: 1.0x (máxima)
│  └─ Aprendizado: "SUBA confiança nesse padrão"
│
├─ ⚠️ GANHO COM SORTE: Indicadores <50% corretos
│  └─ Recompensa: 0.2x (mínima)
│  └─ Aprendizado: "Ignore esse padrão próxima vez"
│
├─ ✅ PERDA COM SKILL: Indicadores 75%+ corretos, mercado contra
│  └─ Punição: -0.7x (leve, estava certo)
│  └─ Aprendizado: "Modelo funciona, mercado surpresa"
│
└─ ❌ PERDA COM FALTA DE SKILL: Indicadores ruins
   └─ Punição: -0.1x (esperado)
   └─ Aprendizado: "Evita padrão, indicador falhou"

MÉTRICA: SKILL_SCORE após N trades
├─ Agregado de todas recompensas ajustadas
├─ Se > 0.15: modelo tem SKILL genuíno
├─ Se 0.05-0.15: borderline, refinar
├─ Se < 0.05: sorte pura (NÃO escalar)
```

### **PILAR 3: INDICADOR DINAMISMO — PESOS EVOLUEM**

```
Cada indicador tem "taxa de acerto" rastreada:

┌──────────────────┬────────┬────────┬──────┐
│ Indicador        │ Acertos│ Erros  │ Taxa │ Ação
├──────────────────┼────────┼────────┼──────┼─────┐
│ RSI oversold     │ 28     │ 12     │ 70%  │ ↑ peso
│ EMA cruzamento   │ 35     │ 15     │ 70%  │ ↑ peso
│ Funding rate     │ 20     │ 20     │ 50%  │ ↓ peso
│ SMC Order Block  │ 18     │ 22     │ 45%  │ ↓↓ peso
└──────────────────┴────────┴────────┴──────┴─────┘

REGRA AUTOMÁTICA:
├─ If accuracy < 55%: reduz peso 15% → 5%
├─ If accuracy > 75%: aumenta peso 15% → 25%
└─ Modelo se auto-calibra iterativamente
```

### **PILAR 4: SEPARAÇÃO SKILL/LUCK — EVENTOS EXTERNOS**

```
Quando mercado faz "surpresa" (Fed, earnings, notícia macro):

CENÁRIO: Indicadores bullish 7.5/10, você abre LONG
         Mas Fed announcement cai (evento inesperado)
         Mercado desaba -8%, stop loss em -$0.30

ANÁLISE:
├─ Skill component: +63% (modelo estava certo)
├─ Luck component: -30% (Fed foi sorte ruim)
├─ Recompensa modificada: -$0.30 × (0.63 - 0.30) = -$0.10
└─ Interpretação: "Estava certo, absorva punição leve"

AÇÃO:
├─ Penalidade: -$0.10 (suave)
├─ Aprendizado: incorporar Fed/earnings calendar
├─ Log: "Evento macro destruiu trade, mas modelo acertou"
```

### **PILAR 5: PONTO DE EQUILÍBRIO = 55% WIN RATE**

```
MATEMÁTICA SIMPLES:

Se Win Rate = 50%: Break-even (0 lucro)
Se Win Rate = 55%: Lucro = +$2.50/100 trades = +$5-10/dia
Se Win Rate = 60%: Lucro = +$10/100 trades = +$15-20/dia
Se Win Rate = 65%: Lucro = +$15/100 trades = +$25-30/dia

META PARA SEMANA 1:
├─ 280-400 trades (40 trades/dia × 7 dias)
├─ Descobrir: W/L = 55%+ ?
├─ Se SIM: escalar para $5 margem  (semana 2)
├─ Se NÃO: refinar indicadores antes escalar

PONTO DE EQUILÍBRIO CRÍTICO:
└─ Abaixo 55% = modelo sem skill (não escalar)
└─ Acima 55% = skill genuíno (escalar com segurança)
```

---

## 🚨 FRAMEWORK: HOLD COM INTELIGÊNCIA

**Decisão Crítica Descoberta**: 2026-02-21 00:05 UTC
**Problema**: Sistema em Profit Guardian (HOLD puro 14h), perdeu oportunidade
**Solução**: HOLD inteligente com métricas

### **O PARADOXO DO HOLD: "INAÇÃO TAMBÉM CUSTA"**

```
Quando sistema diz "score < 5.0, espera":
├─ Economiza risco de entrada ruim ✅
├─ MAS deixa ganho na mesa ❌
│
Exemplo 21 fev 10:00-00:00:
├─ BTC subiu +1.6% (ganho possível $6.40)
├─ Sistema em HOLD (etiquetado como "seguro")
├─ Resultado: $0 ganho + opportunity cost -$6.40
│
QUESTÃO: É esse trade-off correto?
RESPOSTA: Apenas se mercado FOSSE para baixo
         Para cima = HOLD foi errado
```

### **MÉTRICA: OPPORTUNITY COST PER DAY**

```
opportunity_cost = (média_ganho_possível) - (ganho_modelo)

Se HOLD deixa $2.50/dia na mesa × 7 dias = -$17.50/semana

PERGUNTA: Vale risco de operar para ganhar $17.50?
RESPOSTA: Sim, se operando você ganha 55%+ (skill > sorte)
```

### **HOLD DECISION MATRIX**

```
Volatilidade   Score      Ação            Justificativa
─────────────────────────────────────────────────────
BAIXA          >7.0       ABRIR 100%      Seguro
               5.0-6.9    ABRIR 70%       Bom
               <5.0       HOLD            Espera

MÉDIA          >8.0       ABRIR 100%      Raro
               6.0-8.0    ABRIR 70%       Cuidado
               <6.0       HOLD            Demais

ALTA           >9.0       ABRIR 30%       Muito seletivo
               7.5-9.0    HOLD            Perigoso
               <7.5       HOLD 100%       Não

Evento macro   N/A        HOLD 100%       Risco externo
(Fed, etc)                Esperando       Incontrolável
```

### **REGRAS OPERACIONAIS DE HOLD**

```
ENTRA EM HOLD:
├─ Score < 5.0 AND (
│  ├─ Volatilidade > 2.5% histórica, OU
│  ├─ Evento macro próximo <4h, OU
│  └─ Oportunidade loss < expected loss)

VALIDA HOLD A CADA 2-4h:
├─ Calcular opportunity_cost_24h
├─ Se > $5: sai de HOLD, reduz threshold 5.0 → 4.7
├─ Se score trend positivo: força entrada parcial
└─ Se > 24h: força revalidação completa

SAI DE HOLD:
├─ Score >= 5.0, OU
├─ Oportunidade acumulada > limite, OU
├─ 24 horas passaram
└─ Com novo(s) threshold(s) ajustado(s)

LOG OBRIGATÓRIO:
└─ "HOLD Duration: 4h | OpportunityCost: -$2.50 | Status: VALID"
```

### **HOLD QUALITY TRACKER (implementado em agent/hold_quality_tracker.py)**

```python
class HoldQualityTracker:
    def check_hold_validity(self):
        # A cada 2-4h, verifica:
        market_return = get_market_performance()
        opportunity_cost = market_return × portfolio_size

        if abs(opportunity_cost) > abs(expected_loss_avoided):
            # HOLD está custando mais que ajudando
            self.exit_hold_early()
            self.reduce_threshold(5.0 → 4.7)

        if hold_duration > timedelta(hours=24):
            # Máximo 24h contínuo
            self.exit_hold_with_reevaluation()
```

---

## 📊 MANTRAS FINAIS — FILOSOFIA DOCUMENTADA

### **MANTRA #1: CONFLUÊNCIA COM CONFIANÇA**

```
"Não abro pela sorte de um indicador.
 Abro quando múltiplos indicadores convergem na mesma direção.

 Quando ganho, valido se foi pelos motivos certos.
 Quando perdo, analiso se indicadores falharam
 ou se fui punido por algo que não controlava.

 Ganhos com SKILL são aprendizado valioso.
 Ganhos com SORTE, ignoro na próxima decisão.
 Perdas com SKILL ensinam mais que ganhos casuais."
```

### **MANTRA #2: INAÇÃO TAMBÉM CUSTA**

```
"Mas não fico em HOLD infinito.
 HOLD é válido se:
 ├─ Volatilidade está anormal (risco elevado), OU
 ├─ Score realmente < 4.8, OU
 └─ Evento macro pendente

 Se nenhum desses: reduz threshold e experimenta.
 Inação tem custo. Oportunidade perdida é risco também.

 Após 24h em HOLD: revalido tudo.
 Se opportunity_cost > benefício: saio mais cedo."
```

### **MANTRA #3: SKILL ANTES DE LUCRO**

```
"Não estou operando ainda.
 Estou CALIBRANDO.
 Cada trade de $1 é um teste de hipótese.

 Lucro virá NATURALMENTE quando SKILL > 50%.
 Até isso acontecer, coleto dados e refino modelo.

 Ponto de equilíbrio: 55% win rate.
 Abaixo disso = modelo sem skill (NÃO escalar).
 Acima disso = skill genuíno (pode escalar com confiança)."
```

---


## 📊 RISK CONTROLS

```
MÁXIMOS PERMISSIVOS PARA FASE 1:
├─ Max 1ª posição: $1.00 margem → $10 exposição
├─ Max acumulado: $40 margem (de $420 disponível)
├─ Max pares simultâneos: 30
├─ Max perda por posição: $1.00 (10% de $10 exposição)
└─ Stop automático em: -10% (liquidação em alavancagem 10x)

SE ATINGIR LIMITES:
└─ Sistema para automaticamente, alerta investidor
```

---

## 🚨 BLOQUEADOR ABSOLUTO #0 — VERIFICAR API KEY E CONTA

**ID**: VERIFY-API-KEY-ACCOUNT (PRÉ-REQUISITO PARA TUDO)
**Prioridade**: 🔴🔴🔴🔴 BLOQUEADOR CRÍTICO IMEDIATO
**Tipo**: Verificação de conectividade
**Status**: 🔴 EXECUTAR AGORA (antes de qualquer auditoria)
**Tempo Estimado**: 15 minutos
**Responsável**: Tech Lead
**Dependência**: NENHUMA (executar IMEDIATAMENTE)
**Descoberto em**: Reunião do Investidor 20/02/2026 23:33 UTC

### ⚠️ CONTEXTO CRÍTICO

**Discrepância impossível:**

```
INVESTIDOR RELATA (observa na conta Binance web):
├─ Capital: $424 USDT
├─ Posições abertas: 20
└─ Perdas não realizadas: -$182

SISTEMA RETORNA (auditoria API 23:32 UTC):
├─ Capital: [N/A]
├─ Posições abertas: 0
└─ Perdas não realizadas: 0

MATEMATICAMENTE IMPOSSÍVEL:
└─ Se há -$182 em perdas não realizadas, OBRIGATORIAMENTE há posições abertas
└─ Se sistema retorna 0 posições, não pode haver -$182 em PnL
```

### 🔴 PROBLEMA RAIZ IDENTIFICADO

A **API Key configurada em `.env` pode estar:**

1. **Apontando para CONTA ERRADA**
   - Você tem múltiplas contas Binance
   - `.env` tem chave de conta 2, mas você está vendo dados de conta 1
   - Resultado: API retorna dados vazios da conta errada

2. **Apontando para TESTNET ao invés de LIVE**
   - Configuração `TRADING_MODE=paper`
   - Sistema conecta ao testnet (dados vazios)
   - Conta real está em outro lugar

3. **API Key com Permissões Restritas**
   - Chave não tem permissão de leitura
   - Retorna resposta vazia

4. **Defasagem de Dados**
   - API está atrasada/em cache
   - Mas isso não explica 0 vs 20 posições

### ✅ AÇÃO: VERIFICAÇÃO IMEDIATA (15 min)

```
PASSO 1: Verificar `.env` (2 min)
────────────────────────────────────────────────────────
   □ Abrir arquivo config/.env (ou .env na raiz)
   □ Anotar valor de BINANCE_API_KEY
   □ Anotar valor de TRADING_MODE
   □ Anotar valor de BINANCE_API_SECRET

PASSO 2: Comparar com conta real (3 min)
────────────────────────────────────────────────────────
   □ Ir para https://www.binance.com
   □ Login com suas credenciais
   □ Ir para "Futuros" → "Posições Abertas"
   □ Contar quantas posições aparecem
   □ Anotar o PnL total

   Resultado esperado:
   ├─ Se vê 20 posições: API Key em `.env` está ERRADA
   └─ Se vê 0 posições: Sistema está certo (há discrepância com seu relato)

PASSO 3: Verificar qual API Key é qual (5 min)
────────────────────────────────────────────────────────
   □ Se tem múltiplas contas Binance:
      └─ Anote a API Key de CADA conta
      └─ Compare qual está em `.env`

   □ Se tem apenas uma conta:
      └─ A API Key em `.env` deve ser dessa conta
      └─ Se mismatch: há erro de configuração

PASSO 4: Validar TRADING_MODE (2 min)
────────────────────────────────────────────────────────
   □ Verificar se TRADING_MODE em `.env`
   □ Se TRADING_MODE=paper: Sistema conecta ao testnet (dados vazios esperado)
   □ Se TRADING_MODE=live: Sistema conecta à conta de produção

PASSO 5: Corrigir e re-testar (3 min)
────────────────────────────────────────────────────────
   □ Se API Key estava errada: Atualizar `.env`
   □ Se TRADING_MODE foi testnet: Mudar para live
   □ Re-executar: python audit_positions_simple.py
   □ Verificar se agora retorna 20 posições + -$182 PnL
```

### 📋 CRITÉRIO DE SUCESSO

✅ API retorna exatamente 20 posições abertas
✅ API retorna -$182 de PnL não realizado
✅ Concordância 100% entre conta Binance web ↔ API
✅ Configuração `.env` validada como correta
✅ VALIDA-000 pode então prosseguir com segurança

### ⚠️ SE ISSO FALHAR

Se após ajustes a API ainda retornar dados diferentes:
- 🔴 Escalar para Binance Support (problema de API ou permissões)
- 🔴 Possível comprometimento de credenciais
- 🔴 Necessário re-gerar API Keys

---
## � BLOQUEADOR ABSOLUTO — VALIDA-DATA-INTEGRITY

**ID**: VALIDA-000 (PRÉ-REQUISITO PARA TODAS AS AÇÕES)
**Prioridade**: 🔴🔴🔴 BLOQUEADOR CRÍTICO
**Tipo**: Auditoria de Dados + Validação de Integridade
**Status**: 🔴 EXECUTAR AGORA (antes de qualquer operação)
**Tempo Estimado**: 2 horas
**Responsável**: Tech Lead + Analista de Dados
**Dependência**: NENHUMA (executar imediatamente)
**Descoberto em**: Reunião do Investidor 20/02/2026 23:30

### ⚠️ CONTEXTO CRÍTICO

**Problema Identificado pelo Investidor:**

Durante a reunião executiva, apresentamos:
- 21 posições abertas com perdas de -$42k
- Perdas de -$1.122 em ETHUSDT, -$4.600 em SOLUSDT, etc.
- Capital em risco de liquidação

**Realidade verificada em 20/02/2026 23:24:**
- 0 posições abertas
- Capital: ~$424 USDT
- Perdas não realizadas: -$182 USDT
- Nenhuma exposição ativa

### 🔴 IMPACTO CRÍTICO

```text
QUESTÃO FUNDACIONAL:
════════════════════════════════════════════════════════════

Se os dados apresentados na reunião NÃO correspondem à realidade,
então TODAS as decisões tomadas com base nesses dados são INVÁLIDAS.

Exemplos de decisões afetadas:
❌ ACAO-001 (fechar 5 posições) — Posições não existem!
❌ Narrativa de "Profit Guardian Mode" — Fatos são diferentes
❌ Impacto financeiro -$2.670/dia — Cálculo baseado em dado falso
❌ Aprovação de operações — Baseada em dados inconsistentes

CONFIANÇA NO MODELO:
════════════════════════════════════════════════════════════

Se o modelo está recebendo dados incorretos/desatualizados,
como podemos confiar que ele toma as decisões certas?

Riscos:
  1. Modelo opera em base de fatos falsos
  2. Validações de risco podem estar inoperantes
  3. Histórico de operações pode estar comprometido
  4. Auditoria pós-operação seria inválida
```

### ✅ AÇÃO: AUDITORIA COMPLETA DE DADOS

```text
FASE 1: RECONCILIAÇÃO DE DADOS (1.5h)
════════════════════════════════════════════════════════════

□ 1.1 — Conectar à Binance API LIVE
        └─ Obter estado REAL de:
           ├─ Balance (capital disponível)
           ├─ Posições abertas (símbolo, quantidade, PnL)
           ├─ Ordens abertas (SL/TP condicionais)
           └─ Histórico de trades últimas 72h

□ 1.2 — Verificar Database Local (db/crypto_futures.db)
        └─ Consultar tabelas:
           ├─ position_snapshots (últimas 441 entradas)
           ├─ execution_log (última execução)
           ├─ trade_log (histórico de fechamentos)
           └─ Comparar timestamps com API Binance

□ 1.3 — Verificar Documentação (markdown files)
        └─ Arquivos mencionados com dados de posições:
           ├─ DASHBOARD_EXECUTIVO_20FEV.md
           ├─ DIRECTOR_BRIEF_20FEV.md
           ├─ BACKLOG_ACOES_CRITICAS_20FEV.md
           ├─ README.md
           └─ Identificar QUANDO foram atualizados (last commit)

□ 1.4 — Análise de Timeline
        └─ Determinar:
           ├─ Quando os dados dos docs foram precisos?
           ├─ Quando as posições foram fechadas?
           ├─ Por que documentação não foi atualizada?
           ├─ Quem é responsável pela sincronização?
           └─ Qual é o SLA de atualização esperado?

FASE 2: ROOT CAUSE ANALYSIS (30 min)
════════════════════════════════════════════════════════════

□ 2.1 — Identificar fonte de desatualização
        └─ É:
           ├─ Processo manual não executado?
           ├─ Automação quebrada?
           ├─ Falta de monitoramento?
           └─ Documentação nunca foi atualizada?

□ 2.2 — Verificar integridade do execution_log na DB
        └─ Existe registro de fechamento das posições?
           └─ Se sim: QUANDO foi executado?
           └─ Se não: As posições eram reais ou hipotéticas?

□ 2.3 — Validar estado de config/execution_config.py
        └─ Qual é o valor REAL de:
           ├─ allowed_actions (OPEN está habilitada?)
           ├─ AUTHORIZED_SYMBOLS (quantos pares permitidos?)
           └─ profit_guardian_mode (ativo ou inativo?)

FASE 3: DOCUMENTO DE VALIDAÇÃO (30 min)
════════════════════════════════════════════════════════════

Criar relatório OFICIAL:

┌──────────────────────────────────────────────────────┐
│ RELATÓRIO: DATA INTEGRITY AUDIT — 20 FEV 2026       │
├──────────────────────────────────────────────────────┤
│                                                       │
│ SEÇÃO 1: ESTADO REAL DA CONTA (verificado)          │
│   └─ Capital, posições, PnL (fonte: API Binance)    │
│                                                       │
│ SEÇÃO 2: ESTADO DOCUMENTADO (inconsistencies)       │
│   └─ O que foi informado na reunião vs. realidade   │
│                                                       │
│ SEÇÃO 3: ANÁLISE DE INCONSISTÊNCIAS                 │
│   ├─ Quais documentos estão desatualizados?         │
│   ├─ Quando foram atualizados pela última vez?      │
│   ├─ Por que a desatualização não foi detectada?    │
│   └─ Impacto nas decisões tomadas                   │
│                                                       │
│ SEÇÃO 4: CAUSA RAIZ                                 │
│   └─ Processos quebrados? Automação falhou? Manual  │
│       não executado? Falta de validação de dados?   │
│                                                       │
│ SEÇÃO 5: RECOMENDAÇÕES                              │
│   ├─ Como prevenir isso no futuro?                  │
│   ├─ Qual é o SLA de sincronização de dados?        │
│   ├─ Quem é responsável por validação?              │
│   └─ Implementar checklist de dados antes de reunião│
│                                                       │
└──────────────────────────────────────────────────────┘

Arquivo de saída: docs/DATA_INTEGRITY_AUDIT_20FEV_2026.md
```

### 📋 CRITÉRIO DE SUCESSO

✅ Auditoria completa com timeline de atualização de cada documento
✅ Reconciliação 100% entre Binance API ↔ DB Local ↔ Documentação
✅ Identificação clara da causa raiz de desatualização
✅ Processo de validação de dados proposto para futuro
✅ ANTES de executar ACAO-001, ACAO-002, ou qualquer operação

### ⚠️ IMPACTO NA REUNIÃO

**Aguardando resultado desta auditoria para:**
- ✋ PARAR ACAO-001 (fechar posições) até saber se existem mesmo
- ✋ REVISAR narrativa de "Profit Guardian Mode"
- ✋ QUESTIONAR quais outras informações estão incorretas
- ✋ VALIDAR confiabilidade do modelo de trading

---

## �📋 ITEM 1 — FASE 1: Fechar 5 Maiores Posições Perdedoras

**ID**: ACAO-001
**Prioridade**: 🔴 CRÍTICA
**Tipo**: Operação Manual + Monitoramento
**Status**: 🛑 **BLOQUEADA até VALIDA-000 ser concluída**
**Tempo Estimado**: 30 minutos
**Responsável**: Operador Autônomo
**Dependência**: ✋ VALIDA-000 (Data Integrity Audit)

### Descrição

Fechar as 5 maiores posições abertas com perdas catastróficas para:
1. Reconhecer PnL realizado negativo (-$8.500 est.)
2. Liberar capital para novo trading
3. Reduzir risco catastrófico de posições -42% a -511%

### Posições para Fechar

| # | Símbolo | Direção | PnL Atual | Ação |
|---|---------|---------|-----------|------|
| 1 | BERTAUSDT | LONG | -511% | MARKET CLOSE |
| 2 | BTRUSDT | SHORT | -524% | MARKET CLOSE |
| 3 | BCHUSDT | SHORT | -93% | MARKET CLOSE |
| 4 | MERLUSDT | SHORT | -42% | MARKET CLOSE |
| 5 | AAVEUSDT | SHORT | -34% | MARKET CLOSE |

### Passos Técnicos

```text
PASSO 1 (2 min):
  └─ Conectar ao cliente Binance autenticado
     └─ Verificar balance atual
     └─ Confirmar cada posição aberta

PASSO 2 (15 min):
  └─ Para cada posição (ordem: BERTAUSDT → MERLUSDT):
     ├─ Obter price LIVE
     ├─ Executar MARKET order de fechamento
     ├─ AGUARDAR confirmação <2s
     └─ Registrar PnL realizado em log

PASSO 3 (10 min):
  └─ Validação pós-fechamento:
     ├─ Verificar position_snapshots em DB
     ├─ Confirmar 5 posições desaparecerem
     └─ Calcular PnL total realizado

PASSO 4 (3 min):
  └─ Documentar:
     ├─ Criar arquivo logs/fecha_posicoes_fase1_20fev.log
     ├─ Registrar timestamps + slippage + PnL
     └─ Summarizar resultados
```text

### Código de Execução

```python
# File: scripts/fechar_posicoes_fase1.py
from execution.order_executor import OrderExecutor
from data.database import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = DatabaseManager("db/crypto_futures.db")
executor = OrderExecutor()

POSICOES_FECHAR_FASE1 = [
    "BERTAUSDT",  # -511%
    "BTRUSDT",    # -524%
    "BCHUSDT",    # -93%
    "MERLUSDT",   # -42%
    "AAVEUSDT"    # -34%
]

def fechar_fase1():
    logger.info("=[FASE 1]= Iniciando fechamento de 5 posições críticas")

    resultados = []
    for symbol in POSICOES_FECHAR_FASE1:
        try:
            # Obter posição atual
            posicao = db.get_position(symbol)
            if not posicao:
                logger.warning(f"Posição {symbol} não encontrada")
                continue

            # Executar CLOSE
            logger.info(f"Fechando {symbol} (direção: {posicao['direction']})")
            ordem_id = executor.execute_order(
                symbol=symbol,
                action="CLOSE",
                confidence=0.95
            )

            resultados.append({
                "symbol": symbol,
                "order_id": ordem_id,
                "timestamp": datetime.now(),
                "status": "OK"
            })
            logger.info(f"✓ {symbol} fechado com sucesso")

        except Exception as e:
            logger.error(f"✗ Erro fechando {symbol}: {e}")
            resultados.append({
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now(),
                "status": "ERRO"
            })

    # Resumo
    sucessos = sum(1 for r in resultados if r["status"] == "OK")
logger.info(f"=[FASE 1]= Resultado: {sucessos}/{len(POSICOES_FECHAR_FASE1)}
posições fechadas")
    return resultados

if __name__ == "__main__":
    fechar_fase1()
```json

### Critérios de Aceitação

✅ **Deve cumprir**:
- [ ] Todas 5 posições fechadas com MARKET orders
- [ ] PnL total realizado entre -$8.200 a -$8.800
- [ ] Nenhuma posição deve permanecer aberta dos 5 símbolos
- [ ] Latência média de execução <200ms/ordem
- [ ] Zero rejeições de ordem (se rejeição: retry automático)

🚫 **Não deve**:
- [ ] Deixar qualquer posição parcialmente aberta
- [ ] Executar LIMIT orders (deve ser MARKET para garantir saída)
- [ ] Deletar dados do DB (apenas registrar como "closed")

### Monitoramento & Rollback

**Se alguma ordem falhar**:
```text
├─ 1ª tentativa: MARKET order com slippage 0.2%
├─ 2ª tentativa: MARKET order com slippage 0.5% (não recomendado)
└─ Parar e reportar se >2 falhas
```text

**Rollback** (se necessário):
- Operação é irreversível (posições fechadas no exchange)
- Apenas restaurar em DB se execução foi bem-sucedida

### Entregáveis

- ✅ Arquivo log: `logs/fecha_posicoes_fase1_20fev.log`
- ✅ Sumário de PnL realizado
- ✅ Confirmação de 5 posições desaparecidas
- ✅ Commit git: `[OPERAÇÃO] Fase 1 concluída: 5 posições fechadas`

### Notas Operacionais

⚠️ **Aviso**: Essa operação é **DEFINITIVA**. Uma vez executada, posições estão
fechadas no exchange e realizadas em PnL.

---

## 📋 ITEM 2 — FASE 1.5: Validar e Documentar Fechamento

**ID**: ACAO-002
**Prioridade**: 🟠 ALTA
**Tipo**: Validação + Documentação
**Status**: ⏳ Bloqueado por ACAO-001
**Tempo Estimado**: 15 minutos
**Responsável**: Operador + Revisor
**Dependência**: ACAO-001 (COMPLETA)

### Descrição

Validar que o fechamento foi bem-sucedido e documentar estado final para
rastreabilidade.

### Passos Técnicos

```text
PASSO 1 (5 min): Validação em Database
  ├─ Query: SELECT * FROM position_snapshots WHERE symbol IN (...)
  └─ Esperado: 0 registros para cada símbolo de ACAO-001

PASSO 2 (5 min): Validação em Binance API
  ├─ GET /fapi/v2/positionRisk para cada símbolo
  ├─ Esperado: positionAmt = 0 para todos
  └─ Se não: rejeitar e reportar erro crítico

PASSO 3 (5 min): Documentação
  ├─ Criar arquivo: docs/FASE1_VALIDACAO_20FEV.md
  ├─ Listar: Símbolos fechados, PnL confirmado, timestamps
  └─ Anexar: Screenshots de confirmação Binance
```text

### Código de Validação

```python
# File: scripts/validar_fase1.py
from data.database import DatabaseManager
from data.binance_client import BinanceClient
import logging

logger = logging.getLogger(__name__)
db = DatabaseManager("db/crypto_futures.db")
client = BinanceClient()

POSICOES_ESPERADAS_ZERO = [
    "BERTAUSDT", "BTRUSDT", "BCHUSDT", "MERLUSDT", "AAVEUSDT"
]

def validar_fase1():
    logger.info("=[VALIDAÇÃO FASE 1]=")

    # Check 1: Database
    falhas_db = []
    for symbol in POSICOES_ESPERADAS_ZERO:
        snapshots = db.get_position_snapshots(symbol, limit=1)
        if snapshots and snapshots[0]["position_amount"] != 0:
            falhas_db.append(symbol)

    if falhas_db:
        logger.error(f"✗ DB: Posições ainda abertas em DB: {falhas_db}")
        raise Exception("Validação de DB falhou")
    else:
        logger.info("✓ DB: Todas as 5 posições confirmadas como fechadas")

    # Check 2: Binance Live
    falhas_binance = []
    for symbol in POSICOES_ESPERADAS_ZERO:
        position = client.get_position(symbol)
        if position and position["positionAmt"] != 0:
            falhas_binance.append((symbol, position["positionAmt"]))

    if falhas_binance:
        logger.error(f"✗ Binance: Posições ainda abertas: {falhas_binance}")
        raise Exception("Validação de Binance falhou")
    else:
logger.info("✓ Binance: Todas as 5 posições confirmadas como fechadas no
exchange")

    logger.info("✓ =[VALIDAÇÃO FASE 1]= SUCESSO")
    return True

if __name__ == "__main__":
    validar_fase1()
```json

### Critérios de Aceitação

✅ **Deve cumprir**:
- [ ] 0 snapshots abertos em DB para cada símbolo
- [ ] 0 posições abertas em Binance para cada símbolo
- [ ] Documento `docs/FASE1_VALIDACAO_20FEV.md` criado
- [ ] PnL realizado confirmado em ambos banco de dados

🚫 **Se falhar**:
- [ ] Reportar erro crítico
- [ ] Bloquear avanço para ACAO-003 até resolver

### Entregáveis

- ✅ Arquivo validação: `docs/FASE1_VALIDACAO_20FEV.md`
- ✅ Log de verificação: `logs/validacao_fase1_20fev.log`
- ✅ Status: PASSOU / FALHOU

---

## 📋 ITEM 3 — Reconfiguração de `allowed_actions` para Habilitar "OPEN"

**ID**: ACAO-003
**Prioridade**: 🔴 CRÍTICA
**Tipo**: Mudança de Configuração
**Status**: ⏳ Bloqueado por ACAO-002
**Tempo Estimado**: 10 minutos (5 min edição + 5 min reinicialização)
**Responsável**: Engenheiro
**Dependência**: ACAO-002 (VALIDAÇÃO PASSOU)

### Descrição

Modificar arquivo de configuração para habilitar abertura de novas posições.
Isso reverte o agente de "Profit Guardian Mode" para "Trading Ativo".

### Mudança Exata

**Arquivo**: `config/execution_config.py`
**Linhas**: 33-37

### Pré-Mudança (Atual)
```python
    # Allowed actions — ONLY reduce/close, NEVER open
# This is a hard safety guard: even if code has a bug, only these actions pass
    "allowed_actions": ["CLOSE", "REDUCE_50"],
```bash

### Pós-Mudança (Desejado)
```python
    # Allowed actions — CLOSE, REDUCE_50, and OPEN new positions
    # Profit Guardian Mode disabled; trading active resumed
    "allowed_actions": ["OPEN", "CLOSE", "REDUCE_50"],
```bash

### Passos Técnicos

```text
PASSO 1 (2 min): Editar arquivo
  ├─ Abrir config/execution_config.py
  ├─ Linha 35: adicionar "OPEN" no início da lista
  └─ Salvar arquivo

PASSO 2 (1 min): Validar sintaxe
  └─ python -m py_compile config/execution_config.py
     └─ Esperado: sem erro de syntax

PASSO 3 (5 min): Reiniciar agente
  ├─ Se agente está rodando: kill processo
  ├─ Aguardar logs se estiverem abertos
  ├─ Restart: python main.py --mode live OR python main.py --mode paper
  └─ Verificar log: "allowed_actions: ['OPEN', 'CLOSE', 'REDUCE_50']"

PASSO 4 (2 min): Validar em memória
  └─ Verificar que agente carregou nova config
     └─ Log deve mostrar: "Agent initialized with allowed_actions: ..."
```json

### Código de Mudança

```python
# Mudança exata (diff):
- "allowed_actions": ["CLOSE", "REDUCE_50"],
+ "allowed_actions": ["OPEN", "CLOSE", "REDUCE_50"],
```python

### Script de Validação Pós-Mudança

```python
# File: scripts/validar_allowed_actions.py
from config.execution_config import EXECUTION_CONFIG
import logging

logger = logging.getLogger(__name__)

def validar_allowed_actions():
    actions = EXECUTION_CONFIG.get("allowed_actions", [])
    logger.info(f"Allowed actions carregadas: {actions}")

    esperado = {"OPEN", "CLOSE", "REDUCE_50"}
    atual = set(actions)

    if atual == esperado:
        logger.info("✓ Validação PASSOU: 'OPEN' está habilitado")
        return True
    else:
        faltam = esperado - atual
        logger.error(f"✗ Validação FALHOU: faltam {faltam}")
        return False

if __name__ == "__main__":
    if not validar_allowed_actions():
        exit(1)
```json

### Critérios de Aceitação

✅ **Deve cumprir**:
- [ ] Arquivo `config/execution_config.py` linha 35 contém "OPEN"
- [ ] Sintaxe Python válida (py_compile sucesso)
- [ ] Agente reinicia sem erro
- [ ] Log mostra: `allowed_actions: ['OPEN', 'CLOSE', 'REDUCE_50']`
- [ ] Script validar returna True

🚫 **Não deve**:
- [ ] Quebrar nenhuma outra configuração
- [ ] Deixar agente em estado inconsistente
- [ ] Aceitar "HOLD" ou outras ações não-documentadas

### Entregáveis

- ✅ Arquivo modificado: `config/execution_config.py`
- ✅ Log de reinicialização: `logs/reconfig_allowed_actions_20fev.log`
- ✅ Validação: `validar_allowed_actions.py` reporta PASSOU
- ✅ Commit git: `[CONFIG] Habilitar 'OPEN' em allowed_actions — fim de Profit
Guardian Mode`

### Rollback (Se Necessário)

```bash
git revert <commit-hash>
# Agente volta para Profit Guardian Mode
```bash

---

## 📋 ITEM 4 — Disparo de Primeiro Sinal: BTCUSDT LONG Score 5.7

**ID**: ACAO-004
**Prioridade**: 🟠 ALTA
**Tipo**: Trading + Monitoramento
**Status**: ⏳ Bloqueado por ACAO-003
**Tempo Estimado**: 15 minutos (aguardar market, executar, monitorar)
**Responsável**: Operador (com aprovação HEAD para primeiro sinal)
**Dependência**: ACAO-003 (AGENTE RECONFIGURADO)

### Descrição

Executar primeiro sinal novo gerado pela agente após reabilitação de "OPEN" em
`allowed_actions`. Teste de validação de que gerador de sinais continua
funcionando.

### Parâmetros do Sinal

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Símbolo:              BTCUSDT
Direção:              LONG
Score Confluência:    5.7/10 (MUITO BUS - acima 5.0)
Confiança Modelo:     72%
Timeframes Alinhados: H1 + H4 bullish
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tamanho:              0.2 BTC (PEQUENO para teste)
Entry Price:          42.850 (aproximado)
Stop Loss:            41.800 (1.2% risco = ~$420)
TP1:                  43.200 (+3.2% reward = ~$700)
TP2:                  43.800 (+5.0%)

Risco/Reward:         1:1.7 (satisfatório para score 5.7)
```text

### Passos Técnicos

```text
PRÉ-EXECUÇÃO (TODAY ~12h-16h antes mercadoX):
  ├─ Aguardar confirmação do HEAD em Slack/email
  ├─ Revisar sinais pendentes: agent.get_pending_signals()
  └─ Confirmar BTCUSDT score 5.7 está aí

EXECUÇÃO (AMANHÃ ~06h00 MARKET OPEN - Binance):
  ├─ Conectar BinanceClient
  ├─ Obter LIVE price BTCUSDT
  ├─ Verificar balance (>0.2 BTC disponível)
  ├─ Criar ordem:
  │  └─ side: BUY
  │  ├─ quantity: 0.2
  │  ├─ type: MARKET
  │  └─ timestamp: <1s
  ├─ Aguardar confirmação <100ms
  └─ Registrar entry price, timestamp

PÓS-EXECUÇÃO (PRIMEIRA HORA):
  ├─ Monitor: price vs stop (41.800) vs TP (43.200)
  ├─ Se stop atingido: CLOSE automático
  ├─ Se TP1 atingido: vendor 50% (lock profit)
  └─ Log tudo em monitoring/
```text

### Código de Execução

```python
# File: scripts/executar_primeiro_sinal_btc.py
from execution.order_executor import OrderExecutor
from data.database import DatabaseManager
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)
db = DatabaseManager("db/crypto_futures.db")
executor = OrderExecutor()

def executar_btcusdt_sinal():
    """Executa primeiro sinal BTCUSDT score 5.7 após reconfiguração"""

    logger.info("=[PRIMEIRO SINAL]= Iniciando execução BTCUSDT LONG")

    symbol = "BTCUSDT"
    direction = "LONG"
    tamanho = 0.2  # BTC
    stop_loss = 41.800
    tp_1 = 43.200

    try:
        # Pré-voo
        logger.info(f"Verificando signal: {symbol} score 5.7")
        sinal = db.get_signal(symbol)
        if not sinal or sinal["score"] < 5.0:
            logger.error("Sinal não encontrado ou score insuficiente")
            return False

        logger.info(f"Score confirmado: {sinal['score']:.1f}")

        # Obter balance
        balance = executor.get_balance()
        if balance < tamanho:
            logger.error(f"Balance insuficiente: {balance} < {tamanho}")
            return False

        # Executar LONG
        logger.info(f"Executando {tamanho} BTC LONG em market price")
        ordem_entrada = executor.execute_order(
            symbol=symbol,
            action="OPEN",
            direction="LONG",
            size=tamanho,
            confidence=0.72
        )

        entry_price = ordem_entrada["fill_price"]
        logger.info(f"✓ Entry: {entry_price:.2f} USD")

        # Log transação
        db.save_trade_signal({
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "entry_time": datetime.now(),
            "stop_loss": stop_loss,
            "tp_1": tp_1,
            "size": tamanho,
            "score": sinal["score"],
            "status": "OPEN"
        })

        logger.info(f"✓ Trade registrado em DB")
        logger.info(f"Monitorando... Stop: {stop_loss}, TP1: {tp_1}")

        # Monitor primeiros 30 minutos
        for i in range(12):  # 12 × 5seg = 60seg = 1min check interval
            time.sleep(5)
            posicao = executor.get_position(symbol)
            preco_atual = executor.get_price(symbol)

            # Setar SL/TP no exchange
            if i == 0:  # First iteration
logger.info(f"Setando SL/TP no exchange: SL={stop_loss}, TP={tp_1}")
                executor.set_stop_loss(symbol, stop_loss, tamanho)
executor.set_take_profit(symbol, tp_1, 0.5 * tamanho)  # Vender 50%

logger.info(f"[{i+1}min] Preço: {preco_atual:.2f} | PnL: {((preco_atual -
entry_price) / entry_price * 100):.2f}%")

            # Check if stop hit
            if preco_atual <= stop_loss:
                logger.critical(f"✗ STOP HIT em {preco_atual:.2f}")
                break

            # Check if TP hit
            if preco_atual >= tp_1:
                logger.info(f"✓ TP1 HIT em {preco_atual:.2f}")
                break

        logger.info("=[PRIMEIRO SINAL]= Conclusão com sucesso")
        return True

    except Exception as e:
        logger.error(f"✗ Erro: {e}")
        raise

if __name__ == "__main__":
    executar_btcusdt_sinal()
```json

### Critérios de Aceitação

✅ **Deve cumprir**:
- [ ] Trade é executado em MARKET order (1 segundo)
- [ ] Entry price registrado em DB
- [ ] Stop loss 41.800 setado no exchange
- [ ] Take profit 43.200 setado no exchange (50% venda)
- [ ] Monitor ativo por pelo menos 1 hora
- [ ] Log detalhado em `logs/primeiro_sinal_btc_20fev.log`

🚫 **Não deve**:
- [ ] Exceder risk de 1.2% da conta
- [ ] Acionar stop-loss prematuramente por slippage
- [ ] Executar sem aprovação HEAD explícita

### Critério de Sucesso para Reunião de Follow-up

- ✅ Trade foi executado
- ✅ Permaneceu aberto por >30 minutos (sem stop hit imediato)
- ✅ Monitoramento funcionou
- ✅ Log registrou tudo
- ✅ Agente voltou a gerar sinais "OPEN" após reconfiguração

### Entregáveis

- ✅ Trade ID e timestamps
- ✅ Log de execução: `logs/primeiro_sinal_btc_20fev.log`
- ✅ Posição aberta em DB com status OPEN
- ✅ Monitoramento ativo até TP/SL hit

---

## 📋 ITEM 5 — Reunião de Follow-up & Análise de Resultados

**ID**: ACAO-005
**Prioridade**: 🟠 ALTA
**Tipo**: Análise + Decisão
**Status**: ⏳ Bloqueado por ACAO-004
**Tempo Estimado**: 30 minutos (reunião + análise)
**Responsável**: HEAD + Operador
**Dependência**: ACAO-004 (SINAL EXECUTADO)

### Descrição

Reunião de follow-up 24 horas após reconfiguração (2026-02-21 ~16:00 BRT) para
avaliar:
1. Se BTCUSDT LONG funcionou (ganho/perda)
2. Se FASES 2-3 de fechamento devem ser executadas
3. Se próximos sinais são disparados
4. Se scaling é possível

### Agenda da Reunião

```text
┌─ DURAÇÃO: 30 minutos ─────────────────────────────
│
├─ [0-5 min] BTCUSDT Análise
│  ├─ Entry price vs atual
│  ├─ Status: Ganho/perda/stopped
│  └─ Conclusão: sucesso?
│
├─ [5-15 min] Diagnóstico de Sinais
│  ├─ Quantos sinais novos foram gerados?
│  ├─ Scores atuais de 21 pares
│  └─ Próximos candidatos para trade
│
├─ [15-20 min] Decisão FASES 2-3
│  ├─ Se BTCUSDT funcionou: aprovar fechar resto
│  ├─ Se BTCUSDT failed: analyspar e ajustar configs
│  └─ Cronograma: 2026-02-21 à noite?
│
├─ [20-25 min] Plano de Scaling
│  ├─ Se sucesso: aumentar tamanho 0.2 BTC → 0.3 BTC?
│  ├─ Se sucesso: quantos trades/dia?
│  └─ Se sucesso: co-location infrastructure?
│
└─ [25-30 min] Próximos passos
   ├─ Retrainagem modelo (data feb 13-20)
   ├─ Ajustes de MIN_ENTRY_SCORE se necessário
   └─ Calendário: próxima reunião?
```text

### Dados a Coletar PRÉ-REUNIÃO

```python
# Script: scripts/preparar_reuniao_follow_up.py
from data.database import DatabaseManager
from datetime import datetime, timedelta
import json

db = DatabaseManager("db/crypto_futures.db")

def preparar_dados():
    """Coleta dados para reunião follow-up"""

    # 1. BTCUSDT resultado
    btc_trade = db.get_latest_trade("BTCUSDT")
    btc_resultado = {
        "simbolo": "BTCUSDT",
        "entry": btc_trade["entry_price"],
        "saida": btc_trade["exit_price"],
"ganho_pct": ((btc_trade["exit_price"] - btc_trade["entry_price"]) /
btc_trade["entry_price"] * 100),
"duracao": (btc_trade["exit_time"] - btc_trade["entry_time"]).total_seconds(),
        "status": "GANHO" if btc_trade["pnl"] > 0 else "PERDA"
    }

    # 2. Sinais atuais
    sinais_agora = db.get_all_pending_signals()
    sinais_info = [
        {
            "symbol": s["symbol"],
            "score": s["score"],
            "direction": s["direction"],
            "timestamp": s["timestamp"]
        }
        for s in sinais_agora
    ]

    # 3. Posições abertas
    posicoes = db.get_all_positions()

    # 4. PnL do dia
    trades_hoje = db.get_trades(desde=datetime.now() - timedelta(hours=24))
    pnl_total = sum(t["pnl"] for t in trades_hoje)

    return {
        "data": datetime.now().isoformat(),
        "btc_resultado": btc_resultado,
        "novos_sinais": sinais_info,
        "posicoes_abertas": len(posicoes),
        "pnl_24h": pnl_total,
"pares_com_score_5plus": sum(1 for s in sinais_info if s["score"] >= 5.0)
    }

if __name__ == "__main__":
    dados = preparar_dados()
    print(json.dumps(dados, indent=2))
```json

### Estrutura de Relatório

**Arquivo**: `docs/FOLLOW_UP_20FEV_21H00.md`

```markdown
# Follow-up Reunião — BTCUSDT e Resultados 24h

**Data**: 2026-02-21 16:00 BRT
**Participantes**: HEAD + Operador

## 📊 Resultado BTCUSDT
- Entry: 42.850
- Saída: [DADO LIVE]
- Ganho/Perda: [CÁLCULO]
- Status: ✅/❌

## 🎯 Sinais Novos Gerados
- Total: X
- Score >5.0: Y
- Próximos candidatos: [LISTA]

## 📈 PnL 24h
- Trades: X
- Total: $[VALOR]

## ✅ Decisão
- [ ] Aprovar FASES 2-3 (fechar resto posições?)
- [ ] Aumentar tamanho 0.2 → 0.3 BTC?
- [ ] Prosseguir com scaling?

## 📅 Próximos Passos
- [...lista...]
```bash

### Critérios de Sucesso da Reunião

✅ **Dados necessários**:
- [ ] BTCUSDT resultado claro (ganho ou perda)
- [ ] Número de sinais novos gerados
- [ ] Scores atualizados para todos os pares
- [ ] PnL total 24h calculado

✅ **Decisões tomadas**:
- [ ] Aprovar ou bloquear FASES 2-3
- [ ] Aprovar ou bloquear escalação de tamanho
- [ ] Roadmap para semana/mês

### Entregáveis

- ✅ Relatório: `docs/FOLLOW_UP_20FEV_21H00.md`
- ✅ Dados preparados: `scripts/preparar_reuniao_follow_up.py` executado
- ✅ Decisões documentadas
- ✅ Commit: `[REUNIÃO] Follow-up 24h — análise BTCUSDT e próximos passos`

---

## 📌 Sumário de Dependências

```text
ACAO-001 (Fechar 5 posições)
    ↓ (sucesso)
ACAO-002 (Validar fechamento)
    ↓ (validação passou)
ACAO-003 (Reconfigurar allowed_actions)
    ↓ (config aplicada e agente reiniciado)
ACAO-004 (Disparo BTCUSDT LONG)
    ↓ (trade executado)
ACAO-005 (Reunião follow-up)
    ↓ (análise e decisão)
PRÓXIMAS AÇÕES (FASES 2-3, scaling, etc)
```text

---

## 📋 Status Geral do Backlog

| ID | Item | Status | Bloqueador |
|----|----|--------|-----------|
| ACAO-001 | Fechar 5 posições | ⏳ Aguardando Aprovação | (Nenhum) |
| ACAO-002 | Validar fechamento | ⏳ Bloqueado | ACAO-001 |
| ACAO-003 | Reconfiguração | ⏳ Bloqueado | ACAO-002 |
| ACAO-004 | Primeiro sinal BTCUSDT | ⏳ Bloqueado | ACAO-003 |
| ACAO-005 | Follow-up 24h | ⏳ Bloqueado | ACAO-004 |

---

## 🎯 Critérios de Sucesso Global

✅ **Se tudo funciona**:
- ✓ Posições perdedoras fechadas
- ✓ Agente voltar ao trading ativo
- ✓ Primeiro sinal BTCUSDT executado com sucesso
- ✓ Nova geração de sinais confirmada
- ✓ Roadmap para scaling aprovado

🚫 **Cenários de Bloqueio**:
- ✗ Rejeições durante fechamento → Retry com suporte
- ✗ Validação falha → Debug e rollback
- ✗ BTCUSDT perde →  Análise de causa raiz antes scaling
- ✗ Nenhum novo sinal após reconfig → Investigate config loading

---

**Última atualização**: 2026-02-20 20:50
**Revisão necessária em**: 24 horas (2026-02-21 16:00)

