# 📋 OPERAÇÕES LIVE — 3 CENÁRIOS CRÍTICOS

**Versão:** 1.0  
**Data:** 22 FEV 2026 - 08:00 UTC  
**Público:** Operadores de Trading (sem conhecimento técnico)  
**Go-Live:** 22 FEV 10:00 UTC  

---

## 📍 Contexto

Você vai monitorar o **Crypto Futures Agent** durante as primeiras 4 horas ao vivo (canary deploy). Três situações CRÍTICAS podem acontecer. Este guia explica EXATAMENTE o que cada uma significa e o que fazer.

**Regra de Ouro:** Se algo estranho acontecer, **PAUSE o sistema** e chame Guardian imediatamente.

---

## 🎯 CENÁRIO #1: SIGNAL FIRING (Sinal é Disparado)

### O Que Significa
Um **sinal é gerado** quando o sistema detecta uma oportunidade de trading aparecendo nos dados. Isso acontece continuamente durante o dia (30-50 sinais esperados por hora em 60 pares).

### ✅ COMPORTAMENTO ESPERADO

| Evento | Como Aparece no Dashboard | Status | Ação |
|--------|--------------------------|--------|------|
| **Sinal ativado** | Card azul com 🟢 "SIGNAL ACTIVE" | ✅ NORMAL | Observar |
| **Confiança >70%** | Número verde em "Signal Confidence" | ✅ NORMAL | Observar |
| **Ordem gerada** | P&L começa mostrar movimento | ✅ NORMAL | Monitorar |
| **Ordem executada** | Trade em "Open Positions" | ✅ NORMAL | Registrar horário |

### 🎯 EXEMPLOS REAIS

**Exemplo 1: Sinal Normal**
```
⏰ 22 FEV 10:15 UTC
📊 Par: ETHUSDT
🎯 Sinal: LONG (com base em SMC confirmado)
📈 Confiança: 82%
💰 Posição: +0.5 ETH (microlote)
✅ Status: IDEAL — continuar monitorando
```

**Exemplo 2: Sinal com Baixa Confiança**
```
⏰ 22 FEV 10:30 UTC
📊 Par: BTCUSDT
🎯 Sinal: SHORT (fraco, EMA desalinhada)
📉 Confiança: 58%
💰 Posição: NÃO ABERTA (confiança <70%, rejeitado)
⚠️ Status: EXPECTED — sistema funcionando corretamente
```

### 🚨 SE ALGO ESTÁ ERRADO

| Sintoma | Problema | Ação |
|---------|----------|------|
| Sinais disparando a cada 1-2 segundos | **Overfitting** nas heurísticas | ❌ PAUSE sistema, chame Dev |
| P&L caindo dramaticamente depois do sinal | **Ordem executada com slippage extremo** | ❌ PAUSE sistema, chame Guardian |
| Confiança = 0% em TODOS os sinais | **Modelo quebrado** | ❌ PAUSE sistema, chame Brain |
| Nenhum sinal em 30 min | **Dados não chegando** ou **algo freezou** | ❌ PAUSE sistema, chame Data |

### ✅ CHECKLIST — SIGNAL FIRING

- [ ] Sinais aparecem a cada 5-15 minutos por par (normal)
- [ ] Confiança varia entre 40-90% (saudável)
- [ ] Ordens são executadas com latência <500ms
- [ ] P&L reflete movimentos reais de preço
- [ ] Nenhuma ordem pendurada (stuck orders)

---

## 📉 CENÁRIO #2: DRAWDOWN ALERT (Alerta de Queda de Capital)

### O Que Significa
**Drawdown** = perda acumulada desde o pico. Se começamos com $10k e perdemos $300, drawdown = -3%.

**⚠️ Alerta dispara quando:** Drawdown atinge **-2%** (fase 1) ou **-5%** (limite máximo).

### 📊 NÍVEIS DE DRAWDOWN

```
Faseamento Canary:

Fase 1 (10min, 10% volume):   Alerta em -1%  → P A U S E & investigar
Fase 2 (2h, 50% volume):      Alerta em -2%  → P A U S E & investigar
Fase 3 (100% volume):         Alerta em -5%  → CIRCUIT BREAKER ATIVA
```

### ✅ COMPORTAMENTO ESPERADO

| Nível | Indicador Visual | Significado | Ação |
|-------|-----------------|-------------|------|
| **0% a -1%** | 🟢 Verde | Normal, mercado fluctuando | Observar apenas |
| **-1% a -2%** | 🟡 Amarelo | Atenção crescente | Observar mais de perto |
| **-2% a -5%** | 🟠 Laranja | **AVISO**, phase gate ativa | ⚠️ UE PAUSE se persiste |
| **< -5%** | 🔴 Vermelho | **CIRCUIT BREAKER ATIVA** | 🚨 PAUSE IMEDIATO |

### 🎯 EXEMPLOS REAIS

**Exemplo 1: Drawdown Normal (Fase 1)**
```
⏰ 22 FEV 10:05 UTC (5 min após go-live)
📊 Capital Inicial: $10,000
💰 Capital Atual: $9,950
📉 Drawdown: -0.5% (NORMAL)
✅ Status: Esperado no começo, pequenas perdas enquanto calibra
```

**Exemplo 2: Drawdown em Limite Fase 1**
```
⏰ 22 FEV 10:08 UTC
📊 Capital Inicial: $10,000
💰 Capital Atual: $9,900
📉 Drawdown: -1.0% (ALERTA)
🟡 Ação: OBSERVE — se continuar caindo, PAUSE
```

**Exemplo 3: Drawdown Ativa Circuit Breaker**
```
⏰ 22 FEV 11:45 UTC (fase 2, 50% volume)
📊 Capital Inicial: $10,000
💰 Capital Atual: $9,470
📉 Drawdown: -5.3%
🔴 Circuit Breaker: ATIVADO AUTOMATICAMENTE
🚨 Ação: ORDNAS CANCELADAS, POSIÇÕES LIQUIDADAS, sistema em PAUSA
→ Chamar Guardian URGENTE
```

### 🚨 SE ALGO ESTÁ ERRADO

| Sintoma | Diagnóstico | Ação |
|---------|------------|------|
| Drawdown cresce continuamente (não para) | **Risco não controlado** ou **bug no circuit breaker** | ❌ PAUSE, chame Guardian |
| Drawdown salta de -0.5% para -3% de repente | **Flash crash ou slippage extremo** | ❌ PAUSE, chame Executor |
| Indicador de drawdown não atualiza | **Dashboard congelado** ou **dados atrasados** | ❌ PAUSE, chame Data |
| Drawdown mostra valores negativos muito altos (< -20%) | **Bug crítico** no cálculo | ❌ PAUSE, chame Arch |

### ✅ CHECKLIST — DRAWDOWN ALERT

- [ ] Drawdown atualiza a cada 30 segundos no dashboard
- [ ] Fase 1: Desendown permanece > -1% após 10 min
- [ ] Fase 2: Drawdown permanece > -2% após 2h
- [ ] Alertas visuais mudam de cor (verde → amarelo → laranja)
- [ ] Se cai abaixo de -5%, circuit breaker para TUDO automaticamente

---

## 🛑 CENÁRIO #3: CIRCUIT BREAKER (Proteção de Emergência)

### O Que Significa
**Circuit Breaker** = pára-choque automático. Se drawdown cai abaixo de **-3%**, o sistema **pausa TUDO** em < 100ms:
- ✋ Para de gerar novos sinais
- 🔐 Cancela ordens pendentes
- 💾 Salva estado do sistema
- 📞 Envia alertas críticos

### 🎯 ATIVAÇÃO

```
DRAWDOWN < -3% → Circuit Breaker ATIVA AUTOMATICAMENTE

⏹️  FASE 1: Stop generation (100ms)
    └─ Novos sinais = NÃO
    └─ Ordens = CANCELADAS

🔐 FASE 2: Liquidate positions (se necessário, 500ms)
    └─ Posições abertas = FECHADAS via Market Orders
    └─ Slippage = aceitável até -1% por ordem

📊 FASE 3: Safeguard cash (1s)
    └─ Capital = PRESERVADO
    └─ Dashboard = CONGELADO em último estado

🚨 FASE 4: Alert (imediato)
    └─ Guardian notificado (SMS + email)
    └─ Log de emergência = criado automaticamente
```

### ✅ COMPORTAMENTO ESPERADO

**Normal: Circuit Breaker NÃO deve ativar**

```
⏰ 22 FEV 10:00 - 14:00 (4 horas de operação)
📊 Drawdown Máximo: -2.8% (próximo, mas não ativa)
🟢 Circuit Breaker: NUNCA foi acionado (IDEAL)
✅ Posições: Todas fechadas com lucro ou pequena perda
```

### 🚨 SE CIRCUIT BREAKER ATIVA

**Esse é o caso CRÍTICO. Segue passo-a-passo:**

#### **PASSO 1: Reconhecer a Ativação** (Imediato)

Você verá **UMA ou MAIS** destes sinais:

| Indicador | Como Aparece | O Que Significa |
|-----------|-------------|-----------------|
| 🔴 Badge Vermelho | "CIRCUIT BREAKER ACTIVE" em vermelho piscando | Sistema em PROTEÇÃO |
| 📊 Dashboard Congelado | Nenhum número muda (intentável) | Parou de processar trades |
| 🔐 Posições = 0 | "Open Positions" vazio | Tudo foi liquidado |
| 📉 Drawdown Final | Mostra -3% a -3.5% | Pior loss atingido |

#### **PASSO 2: Registrar Informações** (10 segundos)

Captura de tela de:
1. Dashboard mostrando drawdown final
2. Horário exato (22 FEV 12:34 UTC)
3. Última posição (se congelada no display)
4. Log de eventos (se acessível)

#### **PASSO 3: Chamar Guardian AGORA** (30 segundos)

```
🔴 EMERGÊNCIA 🔴
━━━━━━━━━━━━━━━━━━━━━━━━━

Chamar Guardian IMEDIATAMENTE:
Email: guardian@crypto-futures-agent.local
Slack: @Guardian — "#go-live-emergency"
Telefone: [NÚMERO]

Mensagem:
"CIRCUIT BREAKER ATIVADO
⏰ 22 FEV 12:34 UTC
📉 Drawdown: -3.2%
🔐 Posições: LIQUIDADAS
Status: Sistema em PAUSA"
```

#### **PASSO 4: NÃO TOQUE EM NADA** (Próximos 5 minutos)

```
❌ NÃO feche o dashboard
❌ NÃO tente manualmente desativar proteção
❌ NÃO reinicie servidor
❌ NÃO cancele suas ordens

✅ ESPERE Guardian investigar
✅ RECOLHA informações (screenshots)
✅ DESCREVA o que via momentos antes
```

#### **PASSO 5: Decisão** (Guardian decide)

Guardian vai investigar e escolher:

| Opção | Significado | Próximo Passo |
|-------|------------|--------------|
| **Rollback S1** | Volta para antes do go-live | Volta a backtest, aguarde 2h |
| **Restart S2** | Reinicia canary fase 2 | Vai pegar volume 50% de novo |
| **Extende S1** | Continua testando mais (fase 1) | Volta a 10% volume |
| **Abort & Debug** | Pausa completa, vai debugar | Aguarde maiores instruções |

### ✅ CHECKLIST — CIRCUIT BREAKER

- [ ] Confirmou que Circuit Breaker ativou (não imaginou)
- [ ] Tomou screenshot do dashboard no momento
- [ ] Registrou horário exato (relógio UTC)
- [ ] Chamou Guardian DENTRO de 30 segundos
- [ ] NÃO tentou reiniciar nada
- [ ] Aguardou instruções antes de qualquer ação

---

## 🎯 DASHBOARD — CAMPOS QUE VOCÊ VAI VER

### Seção 1: Status Geral (Topo)

```
┌──────────────────────────────────────┐
│ 🟢 LIVE (ou 🟠 CANARY PHASE 1)      │  ← Qual fase está
│ Drawdown: -2.1% (cor muda com nível)│  ← Principal métrica
│ Sinais Ativos: 18/60                 │  ← Quantos pares têm sinais
│ Latência: 245ms (deve ser <500ms)    │  ← Performance
└──────────────────────────────────────┘
```

### Seção 2: Por Símbolo (Principal)

```
┌─────────────────────────────────────────────────┐
│ BTCUSDT | ETHUSDT | BNBUSDT | ... (60 pares)    │
├─────────────────────────────────────────────────┤
│ 🟢 SIGNAL | -0.2% | 0.45 ETH | ✅ OK            │
│ ↑ Status  │ P&L  │ Posição  │ Saúde             │
└─────────────────────────────────────────────────┘
```

**O que cada coluna significa:**

| Coluna | O Que É | Esperado | Problema Se |
|--------|--------|----------|------------|
| 🟢🔴 SIGNAL | Status current | Alternando entre 🟢/🔴 | Piscando muito rápido |
| P&L | Lucro/Perda deste par | Varia -5% a +3% | Salta para -10%+ |
| Posição | Quanto possui | 0.1-0.5 unidades | Maior que 1 unidade |
| ✅ Saúde | System status | ✅ OK ou 🟡 Atenção | ❌ ERRO frequente |

### Seção 3: Gráficos (Histórico)

```
📈 P&L ao Longo do Tempo (esperado: linha um pouco subindo)
📉 Drawdown Ao Longo do Tempo (esperado: picos pequenos, baseline zero)
📊 Distribuição de Sinais (esperado: distribuído, não concentrado)
```

---

## 🚨 ATALHO — E SE EU NÃO ENTENDO NADA?

**Simples: Monitore APENAS estes 3 números:**

```
1️⃣  DRAWDOWN (deve ser > -2%)
2️⃣  CIRCUIT BREAKER (NÃO deve estar vermelho)
3️⃣  SINAIS ATIVOS (deve variar entre 5-25)

Se QUALQUER UM estiver estranho:
→ PAUSE o sistema
→ Tire screenshot
→ Chame Guardian
FIM.
```

---

## 📞 CONTATOS EMERGÊNCIA

| Situação | Chamar | Tempo Resposta |
|----------|--------|----------------|
| Drawdown caindo | **Guardian** (Dr. Risk) | Imediato |
| Nenhum sinal | **Data** (Engenheiro APIs) | 2-5 min |
| P&L fora da realidade | **Trader** ou **Executor** | 5 min |
| Sistema congelado | **Executor** ou **Tech Lead** | Imediato |
| Dashboard não atualiza | **Data** ou **Arch** | 5 min |

---

## ✅ PRÉ-GO-LIVE CHECKLIST

Antes de 10:00 UTC, confirme:

- [ ] Dashboard carregando em localhost
- [ ] Todos os 60 pares mostrando (ou ao menos 50+)
- [ ] Drawdown começando em 0%
- [ ] Circuit Breaker indicador mostrando "ARMED" (não vermelho)
- [ ] Latência <500ms na maioria das leituras
- [ ] Você entende os 3 cenários acima
- [ ] Você sabe quando pausar o sistema
- [ ] Contatos de emergência testados (SMS/email OK)

---

**🎯 Resumo:** Você vai monitorar o dashboard por 4 horas. Se vê sinal disparando, drawdown caindo, ou proteção vermelha — você saberá EXATAMENTE o que fazer.

**Próxima Etapa:** Tire screenshots do dashboard quando estiver stável. Isso será seu baseline para comparar depois.

---

