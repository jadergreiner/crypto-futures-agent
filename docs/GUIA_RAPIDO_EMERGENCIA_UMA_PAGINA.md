# 🚨 GUIA RÁPIDO — EMERGÊNCIA LIVE

**Imprima isso. Leve com você. Consulte durante o go-live.**

---

## 🎯 3 COISAS QUE PRECISAS SABER

### 1️⃣ TUDO ESTÁ NORMAL?

**Checklist cada 10 minutos:**

```
☑️ Drawdown: VERDE (entre 0% e -1%)
☑️ Circuit Breaker: MOSTRA "ARMED" (não vermelho)
☑️ Sinais: aparecem a cada 5-30 min (18/60 é normal)
☑️ Dashboard: números mudam a cada 30s (não congelado)

Se TODOS ✅: Tudo ótimo. Continue observando.
Se ALGUM ✗: Vá para seção 2
```

---

### 2️⃣ ALGO ESTRANHO?

**O que fazer:**

```
1️⃣  Tire SCREENSHOT (preserve evidência)

2️⃣  Identifique qual é o problema:
    a) Drawdown virou 🟡 AMARELO (-1% to -2%)
       → OBSERVAR por 5 min. Se melhora, ok.
       → Se continua caindo, vá para seção 3

    b) Drawdown virou 🟠 LARANJA (-2% to -5%)
       → ALERTA ALTO. Prepare para seção 3

    c) Circuit Breaker virou 🔴 VERMELHO
       → EMERGÊNCIA. Vá para seção 3 AGORA

    d) Algo TOTALMENTE diferente (dashboard congelado, números impossíveis)
       → Pause o sistema. Vá para seção 3

3️⃣  Se SIM a qualquer acima → VAI PARA SEÇÃO 3
```

---

### 3️⃣ EMERGÊNCIA — PROTOCOLO

```
🚨 Se chegou aqui, EXECUTE ISTO:

PASSO 1 (Imediato — 10 segundos):
  □ Clique botão PAUSE (ou Ctrl+Shift+P)
  □ Screenshot do dashboard: salve como "EMERGENCY_[hora].png"
  □ Anote a hora exata no relógio UTC

PASSO 2 (CHAMAR AGORA — 30 segundos):
  Envie mensagem EXATA para Guardian:

  "🚨 EMERGÊNCIA GO-LIVE
  Horário: [HH:MM UTC]
  Problema: [drawdown -5%, circuit vermelho, congelado, etc]
  Drawdown final: [X%]
  Screenshot anexada"

  CONTATOS:
  📧 Email: guardian@crypto-futures-agent.local
  💬 Slack: #go-live-emergency
  📱 Telefone: [NÚMERO AQUI]

PASSO 3 (Próximos 5 minutos):
  □ NÃO reinicie nada
  □ NÃO cancele ordens manualmente
  □ NÃO feche o dashboard
  □ AGUARDE resposta de Guardian

PASSO 4 (Guardian decide):
  Ele vai dizer:
  A) "Volta para fase 1" → espere instruções
  B) "Reinicia fase 2" → obedece
  C) "Pausa tudo" → pausa
  D) "Código de erro X, já sabemos, ignora" → volta normal

  FAÇA O QUE ELE DISSER. FIM.
```

---

## 📊 DASHBOARD CAMPOS PRINCIPAIS

```
Topo em GRANDE:
┌────────────────────────────────┐
│🟢 LIVE ou 🟠 CANARY PHASE     │ ← Qual modo estou
│Drawdown: -2.1% (cor importa)   │ ← Principal métrica
│Sinais Ativos: 18/60            │ ← Pares com trades
│Latência: 245ms                 │ ← Velocidade (OK se <500ms)
└────────────────────────────────┘

Meio (tabela):
┌─────────────┬────────┬────────────┬──────┐
│ PAR         │ SINAL  │ P&L        │ Pos  │
├─────────────┼────────┼────────────┼──────┤
│ BTCUSDT     │ 🟢     │ +$125      │ 0.42 │ ← Ganho
│ ETHUSDT     │ 🔴     │ -$45       │ 0    │ ← Perda
│ BNBUSDT     │ 🟢     │ +$89       │ 0.81 │ ← Ganho
└─────────────┴────────┴────────────┴──────┘

Cores importantes:
🟢 Verde = Normal, tudo bem         → Apenas observe
🟡 Amarelo = Cuidado, atenção       → Observe mais
🟠 Laranja = Aviso grave            → Prepare alerta
🔴 Vermelho = CRÍTICO               → PAUSE AGORA
```

---

## ⚡ SÍNTESE — E SE NADA DISSO FAZ SENTIDO?

**Regra de Ouro:**

Se algo parece:
- ❌ Errado
- ❌ Estranho
- ❌ Você não entende
- ❌ Dashboard congelado
- ❌ Números impossíveis

**PAUSE o sistema. CHAME Guardian. FIM.**

Melhor pausar sem motivo do que deixar queimar.

---

## 📞 CONTATOS (Copie esses nomes no seu celular!)

```
🔨 EMERGÊNCIA GERAL:
   Guardian (Dr. Risk)
   guardian@...
   Slack: @Guardian
   TEL: [NÚMERO]

🛠️ SE NÃO RESPONDE:
   Executor (Tech Lead)
   Arch (Arquiteto)

💰 QUESTÕES DE P&L:
   Trader (Alpha)
   trader@...

📡 DADOS/API:
   Data (Engenheiro)
   data@...
```

---

## ✅ PRÉ-GO-LIVE CONFIRMAÇÃO

Antes de 10:00 UTC:

```
☑️ Entendo os 3 cenários (sinal, drawdown, circuit breaker)
☑️ Entendo quando pausar o sistema
☑️ Tenho screenshot do dashboard NORMAL (baseline)
☑️ Contatos salvos no celular
☑️ Li este documento 2x
☑️ Fiz teste de compreensão (≥12/13 campos)
☑️ Pronto para 4 horas de monitoramento
```

Se faltou algum ☑️: **NÃO INICIA GO-LIVE.**

---

## 🎯 DURANTE AS 4 HORAS

**Cada 10 min:**
1. Observe drawdown (cor)
2. Confirme sinais aparecem
3. Cheque latência (<500ms)
4. Veja se nenhum erro visual

**Se tudo verde:** Continue

**Se qualquer amarelo/laranja:** Vá para seção 2 deste guia

**Se qualquer vermelho ou congelado:** Vá para seção 3 AGORA

---

**Boa sorte! Você consegue! 🚀**

