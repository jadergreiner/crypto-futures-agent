# 📊 DASHBOARD — GUIA RÁPIDO DE ALERTAS

**Documento:** Interpretação de Alertas do Dashboard  
**Audiência:** Operador/Executivo  
**Status:** ✅ OPERACIONAL  
**Data:** 22 FEV 2026 | **Versão:** 1.0

---

## 🎯 O DASHBOARD MOSTRA 4 CARDS CRÍTICOS

Abra: `dashboard_projeto.html`

---

## CARD 1️⃣: Status Crítico

```
┌─────────────────────────────────────┐
│  Status Crítico                     │
│  ──────────────────────────────────  │
│  🔴 DRAWDOWN -46.61%               │
│                                     │
│  Interpretação:                     │
│  - Conta perdeu 46.61% de valor     │
│  - Very bad (limite seguro: -5%)    │
│  - Circuit breaker deve estar ON    │
│                                     │
│  Ação: Verificar Card 2 (CB status) │
└─────────────────────────────────────┘
```

**O que significa:**
- Seu saldo diminuiu 46% desde que Phase 2 começou
- Esta é UMA PERDA CRÍTICA
- Sistema deve estar bloqueado para proteger mais

**Próximo passo:** Ver Card 2

---

## CARD 2️⃣: Circuit Breaker

```
┌─────────────────────────────────────┐
│  Circuit Breaker                    │
│  ──────────────────────────────────  │
│  🔴 DISPARADO                       │
│                                     │
│  Interpretação:                     │
│  - Sistema BLOQUEOU novas ordens    │
│  - Drawdown ≤ -3% (proteção ativa) │
│  - Posições abertas NÃO podem      │
│    ser aumentadas                   │
│                                     │
│  Ação: Ver Card 3 (posições)        │
└─────────────────────────────────────┘
```

**O que significa:**
- Sistema ativou proteção automática
- Novas posições NÃO serão abertas
- Proteções (stop loss) PERMANECEM ativas
- Isso é BOM (evita piorar)

**Estados possíveis:**
- 🔴 DISPARADO = -3% threshold cruzado (bloqueado)
- 🟢 ATIVO = Sistema operando normalmente
- ⚠️ PRESTES A DISPARAR = -2.8% (perto do limite)

---

## CARD 3️⃣: Posições Abertas

```
┌─────────────────────────────────────┐
│  Posições Abertas                   │
│  ──────────────────────────────────  │
│  20 (Risco Alto)                    │
│                                     │
│  Interpretação:                     │
│  - Sistema mantém 20 trades abertos │
│  - Cada um tem P&L (lucro/perda)    │
│  - Risco: Liquidação se pior        │
│                                     │
│  Ação: Abrir dashboard JSON para    │
│  detalhes de cada posição           │
└─────────────────────────────────────┘
```

**O que significa:**
- Há 20 trades ativos em Binance Futures
- Cada posição tem exposição (risco)
- Se mercado continua caindo, algumas podem liquidar
- 20 posições É MUITA exposição em situação de crise

**Risco de Liquidação:**
- Se qualquer posição cai 100%, é liquidada
- Efeito cascata possível
- Circuit breaker tenta evitar isso

---

## CARD 4️⃣: Modo Operacional

```
┌─────────────────────────────────────┐
│  Modo Operacional                   │
│  ──────────────────────────────────  │
│  LIVE + Integrated                  │
│                                     │
│  Interpretação:                     │
│  - LIVE = Capital real (não paper)  │
│  - Integrated = Trading + Training  │
│    acontecem SIMULTANEAMENTE        │
│                                     │
│  Ação: Saiba que PPO model está    │
│  aprendendo enquanto opera          │
└─────────────────────────────────────┘
```

**O que significa:**
- Sistema está com capital REAL em operação
- Está ao mesmo tempo TREINANDO modelos
- Training acontece a cada 2 horas (background)
- PPO deve convergir até 25 FEV

---

## 🚨 CENÁRIOS COM ALERTAS

### Cenário A: 🟢 Tudo Verde (Normal)

```
Dashboard mostra:
  Status Crítico: 🟢 (+2.43%)
  Circuit Breaker: 🟢 ATIVO
  Posições: 10 (Risco Médio)
  Modo: LIVE + Integrated

Interpretação:
  ✅ Operação normal
  ✅ Ganhando dinheiro
  ✅ Sistema operando bem
  ✅ Sem ação necessária

Sua ação:
  - MONITORAR a cada 30 minutos
  - Deixar rodar
```

### Cenário B: 🟡 Aviso (Amarelo)

```
Dashboard mostra:
  Status Crítico: 🟡 (-2.87%)
  Circuit Breaker: 🟡 PRESTES A DISPARAR
  Posições: 15 (Risco Alto)
  Modo: LIVE + Integrated

Interpretação:
  ⚠️ Próximo ao threshold
  ⚠️ Drawdown deteriorando
  ⚠️ Circuit breaker pode disparar em minutos
  
Sua ação:
  1. MONITORAR a cada 5 minutos
  2. Prepare ação de redução de risco
  3. NÃO durma (acompanhe)
  4. Prepare report para Risk Manager
```

### Cenário C: 🔴 CRÍTICO (Vermelho)

```
Dashboard mostra:
  Status Crítico: 🔴 (-46.61%)
  Circuit Breaker: 🔴 DISPARADO
  Posições: 20 (Risco Alto)
  Modo: LIVE + Integrated

Interpretação:
  🔴 SITUAÇÃO CRÍTICA
  🔴 Sistema BLOQUEADO
  🔴 Proteção ativa mas em limite
  🔴 Ação imediata necessária

Sua ação:
  1. Execute: python posicoes.py (salvar estado)
  2. Contate Angel AGORA
  3. Prepare: Parada emergencial ou Redução 50%
  4. Faça: Relatório de diagnostics
     → envie para Risk Manager
  5. Decida: Com Angel qual próximo passo
  
[Veja: EMERGENCY_STOP_PROCEDURE.md]
[Veja: CIRCUIT_BREAKER_RESPONSE.md]
```

---

## 🔍 COMO INTERPRETAR O NÚMERO DEBAIXO DE CADA CARD

```
Exemplo:
  ┌──────────────────────┐
  │ Status Crítico       │
  │ 🔴 DRAWDOWN -46.61%  │  ← Card título + status
  │                      │
  │ vs. safe -5% limit   │  ← Comparação (referência)
  └──────────────────────┘
  
Significado de "-46.61%":
  - Negativo = Perda
  - 46.61 = Magnitude (quase 50% de perda!)
  - MUITO pior que limite seguro (-5%)
```

---

## 🎯 LEITURA RÁPIDA (30 SEGUNDOS)

Abra dashboard. Olhe para 4 cards:

1. **Card 1 (Status Crítico)**
   - 🟢 Verde = Positivo ou pequena perda OK
   - 🟡 Amarelo = Perto do limite
   - 🔴 Vermelho = CRÍTICO

2. **Card 2 (Circuit Breaker)**
   - 🟢 ATIVO = Operando normalmente
   - 🟡 PRESTES = Próximo ao limite
   - 🔴 DISPARADO = BLOQUEADO (proteção)

3. **Card 3 (Posições)**
   - < 5 = Risco Baixo
   - 5-15 = Risco Médio
   - \> 15 = Risco Alto

4. **Card 4 (Modo)**
   - LIVE = Capital real (cuidado!)
   - Paper = Simulação (é só treino)

---

## 📋 CHECKLIST RÁPIDO

Checklist de 2 minutos, 4x por dia:

- [ ] Dashboard carrega? (Sim/Não)
- [ ] Status Crítico = Verde/Amarelo/Vermelho?
- [ ] Circuit Breaker = DISPARADO? (Sim/Não)
- [ ] Quantas posições abertas?
- [ ] Modo = LIVE? (traço real, não papel?)

**Se Vermelho ou Disparado:** Contate Risk Manager

---

## 🔗 DOCUMENTAÇÃO RELACIONADA

- [CIRCUIT_BREAKER_RESPONSE.md](CIRCUIT_BREAKER_RESPONSE.md)
  — O que fazer quando CB dispara
- [EMERGENCY_STOP_PROCEDURE.md](EMERGENCY_STOP_PROCEDURE.md)
  — Como parar sistema
- [OPERADOR_GUIA_SIMPLES.md](OPERADOR_GUIA_SIMPLES.md)
  — Guia de início

---

## 💡 DICAS

**Dica 1:** Dashboard atualiza a cada 30 segundos automaticamente

**Dica 2:** Em crise, abra duas janelas:
- Dashboard (monitorar)
- Terminal (para executar python posicoes.py)

**Dica 3:** Guarde snapshots:
- 08:00 BR (manhã)
- 14:00 BR (tarde)
- 20:00 BR (noite)

**Dica 4:** Se duvidoso, é vermelho. Contate Risk Manager.

---

**Doc Advocate Note:**  
Dashboard está sincronizado com dados reais.  
Atualizado em: 22 FEV 02:05 Brasil  
Próxima atualização: Automática a cada 30s

