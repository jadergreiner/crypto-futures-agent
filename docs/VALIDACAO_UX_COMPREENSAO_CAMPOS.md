# ☑️ VALIDAÇÃO UX — OPERADOR ENTENDE CADA CAMPO?

**Versão:** 1.0  
**Data:** 22 FEV 2026 - 08:30 UTC  
**Objetivo:** Confirmar que operadores conseguem **interpretar corretamente** cada métrica no dashboard  
**Passagem:** Antes de 10:00 UTC (30 min antes go-live)  

---

## 🎯 Metodologia

Apresente cada campo abaixo para o operador. Ele deve conseguir responder à pergunta **SEM ajuda**. 

**Critério de Aprovação:** ≥90% acertos (máx 1 erro)

---

## 📊 CAMPOS DO DASHBOARD — TESTE DE COMPREENSÃO

### SEÇÃO 1: STATUS GERAL (Topo em Grandes Números)

#### **Campo 1.1: MODO OPERACIONAL**

```
Você vê: 🟠 CANARY PHASE 1 (ou 🟢 LIVE)

Pergunta para operador:
"O que significa CANARY PHASE 1?"

Resposta esperada (em essência):
"É o teste inicial com volume reduzido (10%), antes de ir para 100%"

❌ Respostas ERRADAS a corrigir:
"Não sei" → TREINAR
"É um tipo de moeda" → ERRADO, re-explicar
"É um bug" → ERRADO, re-explicar
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:** 
- Explique: "CANARY é teste gradual: 10% → 50% → 100% volume"
- Re-teste em 2 min
- Se ainda errado: ⚠️ FLAG para retraining

---

#### **Campo 1.2: DRAWDOWN**

```
Você vê: 📉 Drawdown: -2.1%

Pergunta para operador:
"Se começamos com $10k e agora mostra -2.1%, quanto temos no total?"

Resposta esperada:
"$10,000 - 2.1% = $9,790 aproximadamente"
(aceitar: qualquer resposta entre $9,750 e $9,850)

❌ Respostas ERRADAS a corrigir:
"Significa que perdemos $2.1" → ERRADO (perdemos $210)
"-2.1% é negativo, então sistema quebrou" → ERRADO (é normal variação)
"Não entendo %" → TREINAR matemática básica
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Drawdown = % de perda do pico. -2.1% = perdemos 2.1% do capital"
- Dê exemplo: "-1% de $10k = $100 perdidos"
- Re-teste em 2 min

---

#### **Campo 1.3: CIRCUIT BREAKER STATUS**

```
Você vê: 🟢 ARMED (ou 🔴 TRIGGERED)

Pergunta para operador:
"O que significa CIRCUIT BREAKER ARMED?"

Resposta esperada:
"Significa que a proteção de emergência está pronta. Se drawdown cai muito, para automaticamente"

❌ Respostas ERRADAS a corrigir:
"Significa que o sistema vai quebrar" → ERRADO (é proteção, não problema)
"ARMED significa que tem bomba?" → ERRADO (é proteção, não explosivo)
"Não sei, só ignoro?" → NÃO, isso é crítico
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Quando Circuit Breaker está ARMED (pronto), o sistema pode se auto-proteger se necessário"
- Parar se vir "TRIGGERED" (vermelho)
- Re-teste em 2 min

---

#### **Campo 1.4: LATÊNCIA**

```
Você vê: ⚡ Latência: 245ms (deve estar entre 50-800ms)

Pergunta para operador:
"Se latência mostra 820ms, isso é bom ou ruim?"

Resposta esperada:
"Isso é ruim. Significa que há atraso na execução de ordens. Acima de 500ms é problema"

❌ Respostas ERRADAS a corrigir:
"Latência é velocidade, então 820 bonitão?" → ERRADO (820ms é lento)
"Não entendo unidades" → TREINAR ms vs s
"Qualquer número é ok" → ERRADO, há limites
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Latência <500ms é bom. >800ms significa atraso, pode perder trades"
- Show exemplo: "Latência longa = ordem chega tarde, paga slippage ruim"
- Re-teste em 2 min

---

### SEÇÃO 2: SIGNALS & POSITIONS (Por Símbolo)

#### **Campo 2.1: STATUS SIGNAL (🟢🔴)**

```
Você vê (exemplo): 
┌────────────────────────────┐
│ BTCUSDT  │ 🟢 SIGNAL ACTIVE │
│          │ Confiança: 78%   │
└────────────────────────────┘

Pergunta para operador:
"Se vê 🟢 SIGNAL ACTIVE, o que significa? Deve fazer algo?"

Resposta esperada:
"Significa um novo sinal foi gerado. Sistema já vai processar. Eu só observo"

❌ Respostas ERRADAS a corrigir:
"Significa vender agora" → ERRADO (não fique nervoso; sistema automático)
"É uma alerta para eu intervir" → ERRADO (é informativo)
"Devo clicar em algo?" → NÃO, dashboard é read-only
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "🟢 SIGNAL = informação apenas. Sistema executa automaticamente"
- Re-teste em 2 min

---

#### **Campo 2.2: CONFIANÇA DO SINAL**

```
Você vê:
│ ETHUSDT  │ 🟢 SIGNAL │ Confiança: 45% │ ❌ REJECTED

Pergunta para operador:
"Por que chegou 'REJECTED' com confiança 45%?"

Resposta esperada:
"Porque confiança < 70%. O sistema só executa sinais com >70% de segurança"

❌ Respostas ERRADAS a corrigir:
"Significa que vai falhar" → ERRADO (significa que será ignorado, proteção)
"O sistema está com problemas?" → NÃO, está funcionando corretamente
"Devo forçar execução?" → NÃO NUNCA
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Confiança <70% = rejeitado (proteção). Evita trades fracas"
- Mostre exemplo: "78% = executa. 58% = ignora"
- Re-teste em 2 min

---

#### **Campo 2.3: P&L (Profit & Loss) POR SÍMBOLO**

```
Você vê:
│ BNBUSDT │ P&L: +$125 │
│ LTCUSDT │ P&L: -$45  │

Pergunta para operador:
"BNBUSDT está com P&L +$125. O que significa?"

Resposta esperada:
"Aquele par ganhou $125 (lucro). LTCUSDT perdeu $45 (perda), mas total ainda pode ser positivo"

❌ Respostas ERRADAS a corrigir:
"+$125 significa que devo vender para garantir?" → NÃO (sistema gerencia automaticamente)
"-$45 é desastre?" → NÃO (é normal, parte de trading)
"Devo fechar posição?" → NÃO (deixa sistema gerenciar até take-profit)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "P&L são lucros/perdas individuais. Não aja; deixa sistema gerenciar"
- Mostre: "Total P&L = soma de todos: (+125) + (-45) = +$80 hoje"
- Re-teste em 2 min

---

#### **Campo 2.4: POSIÇÃO (Tamanho da Ordem Aberta)**

```
Você vê:
│ BTCUSDT  │ Posição: 0.42 BTC │
│ ETHUSDT  │ Posição: 0 ETH    │

Pergunta para operador:
"Qual par tem ordem aberta?"

Resposta esperada:
"BTCUSDT (0.42 BTC). ETHUSDT não tem (0 ETH = fechada ou sem sinal)"

❌ Respostas ERRADAS a corrigir:
"0 ETH significa que perdeu tudo?" → NÃO (0 = sem posição, normal)
"Posição alta = vai bom?" → NÃO (tamanho é predefinido, não muda por performance)
"Devo aumentar 0.42 para 1 BTC?" → NÃO NUNCA (só o sistema dimensiona risco)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Posição = quanto temos alocado. 0 = sem ordem. Não mude manually"
- Re-teste em 2 min

---

### SEÇÃO 3: ALERTAS & PROTEÇÃO

#### **Campo 3.1: DRAWDOWN VISUAL (Cor Muda)**

```
Você vê que a cor de "Drawdown" muda:
- 🟢 Verde (0% to -1%)
- 🟡 Amarelo (-1% to -2%)
- 🟠 Laranja (-2% to -5%)
- 🔴 Vermelho (< -5% = Circuit Breaker ativa)

Pergunta para operador:
"Se drawdown ficar 🟠 laranja em -2.3%, o que fazer?"

Resposta esperada:
"Monitorar de perto. Se continuar caindo, pode ativar proteção. Tenho <5 min para alertar o guardian"

❌ Respostas ERRADAS a corrigir:
"Laranja = é time para vender?" → NÃO (observe, não aja manualmente)
"Pause o sistema quando ficar amarelo?" → NÃO (não até que fique vermelho)
"Laranja = sistema vai cair?" → NÃO (é só aviso, proteção ativa em vermelho)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Cores = níveis de alerta. Observe com atenção em laranja. Pause se ficar vermelho"
- Re-teste em 2 min

---

#### **Campo 3.2: SINAIS ATIVOS (Quantos Pares Têm Ordens)")**

```
Você vê: 📊 Sinais Ativos: 18/60

Pergunta para operador:
"O que significa '18/60 sinais ativos'?"

Resposta esperada:
"De 60 pares monitorizados, 18 têm sinais/ordens abertos neste momento. Os outros 42 estão em espera"

❌ Respostas ERRADAS a corrigir:
"42 pares estão quebrados?" → NÃO (apenas esperando sinal, normal)
"Deveria ser 60/60?" → NÃO (é impossível, não há sinal em todos ao mesmo tempo)
"18 é bom ou ruim?" → NORMAL (esperado 5-30 pares)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Nem todos os pares têm sinal ao mesmo tempo. 18/60 = 30% = saudável"
- Isso é NORMAL, não problema
- Re-teste em 2 min

---

#### **Campo 3.3: ORDENS PENDENTES (Stuck Orders)**

```
Você vê (se houver bug): ⚠️ Pending Orders: 3

Pergunta para operador:
"Se aparece '3 Pending Orders', o que significa?"

Resposta esperada:
"Significa que há 3 ordens que não foram executadas ainda. Se aumentar para 5+, pode ser problema"

❌ Respostas ERRADAS a corrigir:
"Pending = quebradas?" → NÃO (às vezes é ok; isso se elas não executam em 10 seg)
"Devo cancelar?" → NÃO (deixa sistema gerenciar por 30 seg. Se ainda pendente, então alerta)
"Isso é normal?" → PARCIALMENTE (1-2 ok; 5+ é problema)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Pending é normal por até 10 segundos. Se > 30 seg = problema, chame Data"
- Re-teste em 2 min

---

### SEÇÃO 4: ENTENDER QUANDO PAUSAR (Crítico!)

#### **Campo 4.1: PROTEÇÃO AUTOMÁTICA**

```
Pergunta para operador:
"O Circuit Breaker vai parar o sistema sozinho ou você precisa clicar?"

Resposta esperada:
"Sozinho! É automático. Drawdown < -3% = para tudo em <100ms, sem minha ação"

❌ Respostas ERRADAS a corrigir:
"Eu preciso clicar em 'STOP'" → NÃO (funciona automaticamente)
"Não funciona se eu não vir?" → NÃO (funciona em background, sempre)
"Devo rebootar o servidor?" → NÃO (deixa sistema lidar)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Circuit Breaker é automático. Você vê quando acontece, mas não precisa ativar"
- Re-teste em 2 min

---

#### **Campo 4.2: QUANDO PAUSAR MANUALMENTE**

```
Pergunta para operador:
"Em que caso VOCÊ MESMO deve pausar o sistema (clique no botão PAUSE)?"

Resposta esperada:
"Se algo estranho acontecer que não entendo OU que não encaixe com os 3 cenários conhecidos.
Aí eu pauso e chamo Guardian para investigar"

✅ Exemplos de quando pausar:
- "Latência pulou para 2000ms de repente"
- "Drawdown caindo mas Circuit Breaker não responde"
- "Dashboard congelado (números não mudam há 2 min)"
- "Sinais disparando 100x por segundo"
- "P&L mostra valor impossível (tipo $1 milhão ganho em 1 min)"

❌ NUNCA pausar apenas porque:
- "Estava em medo" (se vê sinal disparando)
- "P&L está negativo" (normal, deixa sistema)
- "Sinal disparou em muito par ao mesmo tempo" (normal)
```

**Se operador respondeu CORRETO:** ✅ PASSAR

**Se respondeu ERRADO:**
- Explique: "Pause APENAS se estranho/desconhecido. Sinais, perda pequena = normal"
- Re-teste em 2 min

---

## ☑️ CHECKLIST FINAL — OPERADOR PASSOU?

Após testar todos os 13 campos acima, score:

```
TESTE UX — RESULTADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operador: ________________
Data: 22 FEV 2026 - __:__ UTC

[ ] 1.1 Modo Operacional (CANARY PHASE)      ✓ PASSOU / ✗ FALHOU
[ ] 1.2 Drawdown %                           ✓ PASSOU / ✗ FALHOU
[ ] 1.3 Circuit Breaker Status               ✓ PASSOU / ✗ FALHOU
[ ] 1.4 Latência                             ✓ PASSOU / ✗ FALHOU
[ ] 2.1 Status Signal (🟢/🔴)                ✓ PASSOU / ✗ FALHOU
[ ] 2.2 Confiança do Sinal                   ✓ PASSOU / ✗ FALHOU
[ ] 2.3 P&L (Profit/Loss)                    ✓ PASSOU / ✗ FALHOU
[ ] 2.4 Posição (Tamanho Ordem)              ✓ PASSOU / ✗ FALHOU
[ ] 3.1 Drawdown Visual (Core Muda)          ✓ PASSOU / ✗ FALHOU
[ ] 3.2 Sinais Ativos (18/60)                ✓ PASSOU / ✗ FALHOU
[ ] 3.3 Ordens Pendentes                     ✓ PASSOU / ✗ FALHOU
[ ] 4.1 Proteção Automática                  ✓ PASSOU / ✗ FALHOU
[ ] 4.2 Quando Pausar Manualmente            ✓ PASSOU / ✗ FALHOU

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOTAL: ___/13 campos entendidos

RESULTADO FINAL:
🟢 ≥12/13 = APROVADO, autorizado para monitorar
🟡 10-11/13 = AUTORIZADO COM MENTORIA (retraining 2 campos)
🔴 <10/13 = REJEITADO, retraining necessário antes do go-live
```

---

## 🎯 PRÉ-GO-LIVE PASSOS

**09:30 UTC (30 min antes do go-live):**

1. [ ] Operador senta ao lado de você
2. [ ] Você lê cada pergunta em voz alta
3. [ ] Operador responde (sem ler documentação)
4. [ ] Você marca ✓/✗
5. [ ] Se ✗, explica AGORA
6. [ ] Re-testa aquele campo em 2 min
7. [ ] Se passou segunda vez, marque verde
8. [ ] Ao final: score ≥12/13?

**Se SIM:** Operador APROVADO  
**Se NÃO:** Mais 15 min de treinamento, re-teste

---

## 📞 TEMPLATE — CERTIFICADO DE COMPREENSÃO

Após aprovação, preencha:

```
CERTIFICADO — UX COMPREENSÃO
═══════════════════════════════════

Data/Hora: 22 FEV 2026 - 09:47 UTC
Operador: _________________ (assinatura)
Treiner: Product Manager
Resultado: ✅ APROVADO (13/13)

Operador está autorizado a monitorar 
dashboard do go-live de heurísticas.

Conhece:
 ✅ Os 3 cenários críticos
 ✅ 13 campos do dashboard
 ✅ Quando pausar o sistema
 ✅ Como chamar emergência

Assinado por:
Product Manager _____________
Data ________________
```

---

**Nota Final:** Este test é ESSENCIAL. Operador não entende = risco de decisões erradas em crise. Leve isso a sério.

