# ✅ PRODUCT — CHECKLIST PRÉ-GO-LIVE

**Timeline:** 22 FEV 08:00 → 09:50 UTC (110 minutos até go-live)  
**Responsável:** Product Manager (você)  
**Objetivo:** Validar que dashboard & documentação operacional estão 100% prontos  
**Status se TUDO OK:** Go-live pode prosseguir  
**Status se ALGUM ✗:** Escalate para Angel imediatamente  

---

## ⏱️ SEÇÃO 1: DASHBOARD FÍSICO (20 minutos — 08:00 a 08:20)

### Verificação de Renderização

```
[ ] Dashboard carrega em localhost (sem erros de JavaScript)
    Abra: file:///c:/repo/crypto-futures-agent/dashboard_projeto.html
    Espera até ver números (pode levar 10 seg)

[ ] Todos os 60 pares mostrando (ou ≥50 pares)
    Scroll down na seção de pares
    Confirme que não há "Symbol not found"

[ ] Cores aparecem corretamente:
    - 🟢 Sinais verdes (para active)
    - 🔴 Sinais vermelhos (para inactive)
    - 🟡 Amarelo para drawdown <-1%
    - 🟠 Laranja para drawdown <-2%
    - 🔴 Vermelho para circuit breaker

[ ] Números ficam legíveis (fonte, contraste, tamanho)
    Teste em tela 24"+ (qual é a resolução padrão?)
    Pergunte: "Um operador consegue ler de 1m de distância?"
```

### Verificação de Atualização Automática

```
[ ] Dashboard atualiza a cada 30 segundos
    Espere 40 segundos sem fazer nada
    Números devem mudar (mesmo que pequeno) em "Last Updated"

[ ] Dados sincronizam com status real
    Execute: python update_dashboard.py (já fiz: ✅ 01:41)
    Verifique que não há "Arquivo não encontrado"

[ ] JSON file existe e é válido
    Abra: c:\repo\crypto-futures-agent\dashboard_data.json
    Deve ser JSON válido (não está corrompido)
```

---

## 📚 SEÇÃO 2: DOCUMENTAÇÃO OPERACIONAL (30 minutos — 08:20 a 08:50)

### Documento 1: 3 Cenários Críticos

```
[ ] Arquivo existe:
    c:\repo\crypto-futures-agent\docs\OPERACIONAL_3_CENARIOS_CRITICOS.md

[ ] Cenário 1 (Signal Firing) está claro:
    [ ] Explica o que é sinal disparado
    [ ] Dá exemplos REAIS
    [ ] Lista comportamento esperado
    [ ] Lista o que fazer se errado

[ ] Cenário 2 (Drawdown Alert) está claro:
    [ ] Explica o que é drawdown %
    [ ] Mostra níveis de alerta (verde/amarelo/laranja)
    [ ] Faseamento do canary (fase 1/2 têm limites diferentes)
    [ ] O que significa -3% (circuit breaker trigger)

[ ] Cenário 3 (Circuit Breaker) está claro:
    [ ] Explica ativação automática
    [ ] Esclarecade que NÃO é bom nem ruim (é proteção)
    [ ] Desenha passo-a-passo do que fazer
    [ ] Explica que Guardian decide o que fazer depois

[ ] Léxico é simples (não-técnico):
    Ler primeira frase de cada seção
    Se tem jargão técnico = reescrever antes de 09:50
```

### Documento 2: Validação UX & Compreensão

```
[ ] Arquivo existe:
    c:\repo\crypto-futures-agent\docs\VALIDACAO_UX_COMPREENSAO_CAMPOS.md

[ ] Tem 13 campos de teste:
    Count: 4 campos seção 1, 4 seção 2, 3 seção 3, 2 seção 4 = 13 ✓

[ ] Cada teste tem:
    [ ] Pergunta clara (pode ler em voz alta)
    [ ] Resposta esperada (clara)
    [ ] Respostas ERRADAS (e como corrigir)
    [ ] Critério de aprovação (score ≥12/13)

[ ] Checklist final está pronto (template):
    [ ] Template de certificado de aprovação pronto
    [ ] Instruções de como executar test (09:30)
```

### Documento 3: Guia Rápido de Emergência

```
[ ] Arquivo existe:
    c:\repo\crypto-futures-agent\docs\GUIA_RAPIDO_EMERGENCIA_UMA_PAGINA.md

[ ] Pronto para imprimi-lo (one-pager):
    [ ] Cabe em 1 página A4
    [ ] Fonte ≥10pt (legível)
    [ ] Tem contatos de emergência
    [ ] Tem os 3 protocolos (normal, algo estranho, emergência)

[ ] Impresso e plastificado (se possível):
    Print 5 cópias (para operador + backup)
    Deixe à mão durante go-live

[ ] Contatos estão preenchidos:
    [ ] Guardian: email & telefone
    [ ] Executor: email & telefone
    [ ] Trader (Alpha): email & telefone
    [ ] Data: email & telefone
```

---

## 👥 SEÇÃO 3: TESTE OPERADOR (20 minutos — 08:50 a 09:10)

### Seleção de Operador

```
[ ] 1 operador designado para monitorar (nome prenchido):
    Operador: _____________________
    
[ ] Operador tem 0 jargão técnico (se possível)
    Se é DEV: pior, vai entender "muito" e perder detalhe
    Se é completamente novo: mejor, aprende certo
```

### Teste UX

```
[ ] Operador senta à lado de você no computador

[ ] Você lê as 13 perguntas em VOZ ALTA
    Ele responde SEM ler a documentação
    Você marca cada resposta: ✓ ou ✗

[ ] Score final: ___/13

[ ] Se ≥12/13: ✅ APROVADO
    Preench certificado (template em VALIDACAO_UX_COMPREENSAO_CAMPOS.md)
    Ele assina o documento

[ ] Se <12/13: ⚠️ MENTORIA NECESSÁRIA
    Re-treino dos campos falhados (15 min max)
    Re-teste daqueles campos (5 min)
    Novo score: ___/13
    Se ainda <12/13: 🔴 ESCALATE para Angel (não autoriza go-live)
```

### Teste Prático

```
[ ] Mostrar operador o dashboard ao vivo
[ ] Ele aponta cada campo (sem ler doc):
    "O que é isso?"
    "E isso?"
    "Como você sabe quando pausar?"

[ ] Se consegue apontar & responder 80%+: ✓ Pronto
[ ] Se não consegue: ✗ Mais treinamento
```

---

## 🎯 SEÇÃO 4: VALIDAÇÃO FINAL & ASSINATURA (20 minutos — 09:10 a 09:30)

### Documentação de Go-Live

```
[ ] Criar arquivo de GO-LIVE (novo arquivo):
    Nome: PRODUCT_GO_LIVE_READINESS_22FEV.md
    
    Conteúdo:
    ─────────────────────────────────────
    # GO-LIVE READINESS CHECKLIST — PRODUCT
    
    **Data:** 22 FEV 2026 - 09:30 UTC
    **Preparado por:** Product Manager
    **Status:** ✅ PRONTO ou ❌ NÃO PRONTO
    
    ## Dashboard
    - ✅ Renderiza sem erros
    - ✅ 60 pares visíveis
    - ✅ Atualiza a cada 30s
    - ✅ Cores funcionam
    
    ## Documentação Operacional
    - ✅ 3 Cenários críticos documentados
    - ✅ UX Compreensão testada (13/13 campos)
    - ✅ Guia rápido impresso & plastificado
    - ✅ Contatos de emergência preenchidos
    
    ## Operador
    - ✅ Teste UX: 12/13 aprovado
    - ✅ Conhece os 3 cenários
    - ✅ Sabe quando pausar
    - ✅ Contatos salvos no celular
    
    ## Conclusão
    Dashboard e documentação operacional estão 100% prontos para go-live às 10:00 UTC.
    Operador aprovado e treinado.
    
    Assinado: Product Manager
    Data: 22 FEV 2026 - 09:30 UTC
    ─────────────────────────────────────
```

### Sign-Off & Comunicação

```
[ ] Enviar mensagem para Planner (ops):
    "Dashboard e docs prontos. Operador aprovado.
    Referência: PRODUCT_GO_LIVE_READINESS_22FEV.md"

[ ] Copiar Angel & Elo (governance):
    Mandar o go-live readiness como FYI

[ ] Marcar no calendar:
    10:00 UTC = START GO-LIVE
    Você vai estar no slack/zoom para bugs imediatos
```

---

## ⏱️ HORA POR HORA — DIA 22 FEV

```
08:00 — PRODUCT começa checklist
   └─ Dashboard & docs review (30 min)

08:30 — Operador chega
   └─ Teste UX (20 min) + prático (10 min)

09:00 — Resultados
   └─ ≥12/13? SIM → certificado + assinatura
   └─ <12/13? NÃO → mentoria 15 min, re-teste

09:30 — Final prep
   └─ Imprime guia de emergência
   └─ Preenche PRODUCT_GO_LIVE_READINESS_22FEV.md
   └─ Anuncia para Planner que está tudo pronto

09:50 — 10 minutos antes
   └─ Operador sentado, dashboard aberto, guia de emergência à mão
   └─ Angel/Elo/Executor prontos para start

10:00 — GO-LIVE 🚀
   └─ Fase 1 (10% volume, 10 min)
   └─ Product monitora dashboard, operador observa
   └─ Próximo gate: 10:10 (decisão: continuar ou pause)
```

---

## 🚨 RED FLAGS — ESCALATE AGORA

```
Se QUALQUER um destes acontecer, escalate para Angel imediatamente:

❌ Dashboard não carrega
❌ Mais de 10 pares faltando no display
❌ Cores não aparecem (tudo monótono)
❌ Documentação 3 cenários é confusa (operador não entende)
❌ Operador falha em <10/13 teste UX mesmo após retrain
❌ Dashboard congelado em dados velhos (>1 min sem update)
❌ Operador não consegue apontar campos no dashboard
❌ Contatos de emergência não resolvem (emails/telefones errados)
❌ Qualquer coisa que TE FAÇA DUVIDAR: escalate

Mensagem para Angel:
"🚨 PRODUCT BLOCKER: [qual é o problema]
Impacto: Go-live não pode prosseder sem isto.
Recomendação: [adie 1h / adie para amanhã / resolvemos em X min]
Assinado: Product Manager"
```

---

## ✅ FINAL APPROVAL TEMPLATE

Copie isto como arquivo se TUDO OK:

```
═══════════════════════════════════════════════════════════

✅ PRODUCT MANAGER — PRÉ-GO-LIVE APPROVAL

Data: 22 FEV 2026
Hora: 09:45 UTC (15 min antes do go-live)
Responsável: Product Manager

DASHBOARD:
✅ Renderiza sem erros (60/60 pares)
✅ Atualiza a cada 30 segundos
✅ Cores, legibilidade, UX aprovados

DOCUMENTAÇÃO OPERACIONAL:
✅ 3 Cenários críticos (Signal/Drawdown/Circuit Breaker)
✅ Validação UX com 13 campos de teste
✅ Guia rápido de emergência (1 página, pronto para imprimir)

OPERADOR:
✅ Teste UX Score: 13/13 (100% aprovado)
✅ Conhece protocolo de emergência
✅ Contatos de emergência no celular
✅ Pronto para monitorar 4 horas

CONCLUSÃO:
✅ UX/Documentação operacional 100% PRONTO
✅ Operador 100% AUTORIZADO
✅ Go-live pode prosseder como planejado às 10:00 UTC

Assinado digitalmente por:
Product Manager
22 FEV 2026 - 09:45 UTC

═══════════════════════════════════════════════════════════
```

---

**Nota Final:** Você é responsável por garantir que o operador esteja confiante e bem informado. Se ele não tem confiança, o sistema fica vulnerável a decisões erradas em crise. Leve a sério este checklist.

**Good luck! 🚀**

