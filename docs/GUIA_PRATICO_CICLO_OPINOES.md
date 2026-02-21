# 🎯 GUIA PRÁTICO: USAR CICLO DE OPINIÕES NA PRÓXIMA REUNIÃO

**Data de implementação:** 23 FEV 2026
**Facilitador:** Elo (Gestor de Alinhamento)
**Público:** Todos os 16 membros da equipe

---

## ⚡ ANTES DA REUNIÃO (15 min antes)

### 1. Facilitador (Elo) prepara a reunião

```bash
cd /path/to/crypto-futures-agent

# Opção A: Decision #2 (ML Training Strategy)
python scripts/condutor_board_meeting.py --decisao ML_TRAINING_STRATEGY

# Opção B: Decision #3 (Posições Underwater)
python scripts/condutor_board_meeting.py --decisao POSIOES_UNDERWATER

# Opção C: Decision #4 (Escalabilidade)
python scripts/condutor_board_meeting.py --decisao ESCALABILIDADE
```

### 2. Verificar que foi criado

```bash
# Banco de dados criado
ls -la db/board_meetings.db

# Pauta estruturada gerada
ls -la reports/board_meeting_*.md
```

---

## 📊 DURANTE A REUNIÃO (70 min)

### Fase 1: ABERTURA (5 min)

**Elo (Facilitador):**
> "Bom dia a todos. Hoje temos uma decisão importante para votar. Vou apresentar a decisão e as opções. Então cada um de vocês vai opinar de sua especialidade. Total: 70 minutos."

### Fase 2: APRESENTAÇÃO (5 min)

**Apresenta:**
- Título da decisão
- Contexto (por que precisamos decidir agora)
- Opções em votação (ex: A, B, C)
- Critério de sucesso

**Arquivo de referência:** Salvo em `reports/board_meeting_N.md`

### Fase 3: PAUTA ESTRUTURADA (5 min)

**Elo exibe perguntas por especialidade:**

```
Cada membro receberá perguntas estruturadas para sua especialidade:

👑 Executiva (Angel)
   "Qual opção melhor equilibra ROI, timeline e risco?"

🤖 Machine Learning (The Brain)
   "Qual opção garante melhor generalização?"

💰 Financeira (Dr. Risk)
   "Qual opção tem melhor trade-off custo/benefício?"

... e assim por diante (16 especialidades)
```

### Fase 4: CICLO DE OPINIÕES (40 min — 2:30 por membro)

**Sequência de apresentação (4 min cada):**

1. **Angel** (Investidor) — 0:00-4:00
   - Sua perspectiva executiva
   - Custo de oportunidade
   - Apetite de risco

2. **Elo** (Facilitador) — 4:00-8:00
   - Alinhamento de stakeholders
   - Riscos de processo
   - Reversibilidade

3. **Audit (Docs)** — 8:00-12:00
   - Documentação [SYNC]
   - Auditoria
   - Compliance

4. **Planner** (PM Ops) — 12:00-16:00
   - Timeline e milestone
   - Riscos de operação
   - Escalação

5. **Dr. Risk** (Head Finanças) — 16:00-20:00
   - Análise financeira
   - ROI e capital
   - Hedge strategy

6. **Flux** (Arquiteto Dados) — 20:00-24:00
   - Integridade de dados
   - Performance
   - Escalabilidade de pipeline

7. **The Brain** (Engenheiro ML) — 24:00-28:00
   - Validação científica
   - Generalização do modelo
   - Walk-Forward confidence

8. **Guardian** (Risk Manager) — 28:00-32:00
   - Proteção de capital
   - Drawdown máximo
   - Liquidação risk

9. **Audit (QA)** (QA Manager) — 32:00-36:00
   - Testabilidade
   - Edge cases
   - Regression risk

10. **The Blueprint** (Tech Lead) — 36:00-40:00
    - Arquitetura
    - Escalabilidade técnica
    - Tech debt

11. **Dev** (The Implementer) — 40:00-44:00
    - Implementação
    - Esforço de desenvolvimento
    - Code quality

12. **Vision** (PM) — 44:00-48:00
    - Posicionamento no mercado
    - Roadmap alignment
    - Diferencial competitivo

13. **Arch** (AI Architect) — 48:00-52:00
    - Infraestrutura de cluster
    - Training feasibility
    - Cost operacional

14. **Alpha** (Crypto Trader) — 52:00-56:00
    - Price action validation
    - Execution quality
    - Market microstructure

15. **Board Member** (Estratégia) — 56:00-60:00
    - Long-term vision
    - Strategic optionality
    - Exit scenarios

16. **Compliance** (Auditor) — 60:00-64:00
    - Regulação
    - Audit trail
    - Risk compliance

### Fase 5: SÍNTESE (5 min)

**Elo resume:**
- Quantas pessoas FAVORÁVEL
- Quantas CONDICIONAL
- Quantas CONTRÁRIO
- Qual foi o consenso

**Exemplo:**
```
RESUMO DE VOTOS:
- FAVORÁVEL:    11/16 (69%)
- CONDICIONAL:   4/16 (25%)
- CONTRÁRIO:     1/16 (6%)
- NEUTRO:        0/16 (0%)

CONSENSO: Opção C (Hybrid) com apoio superlativo
```

### Fase 6: VOTAÇÃO FINAL (10 min)

**Angel (Decision Maker) declara:**
> "Baseado nas opiniões dos 16 especialistas, APROVO: Opção C (Hybrid ML Training Strategy)
> Timeline: 3-4 dias. Owner: The Brain + Arch.
> KPI de sucesso: Sharpe >0.3, Max DD <15%."

**Elo registra:**
```
✅ Decision #2 — APROVADA
   Opção: C (Hybrid Adaptive)
   Votação: 11 FAVORÁVEL, 4 CONDICIONAL, 1 CONTRÁRIO
   Decision Maker: Angel
   Data da Decisão: 23 FEV 2026 15:00 UTC
   Author Implementação: The Brain + Arch
   Data Alvo: 26/27 FEV 2026
```

---

## 📋 TEMPLATE: O QUE CADA MEMBRO DEVE FALAR

### Para Angel (Investidor) — 4 min

```
"Minha perspectiva:
1. Custo de oportunidade: cada dia custa -$2.670
2. Opção C oferece 60% ROI de B em 3 dias (vs 7)
3. Risk ajustado: Max DD <15%, aceitável
4. Aprovaria Opção C ou B, dependo de ciência (ouço The Brain)
5. Meu voto: FAVORÁVEL C"
```

### Para Elo (Facilitador) — 4 min

```
"Minha perspectiva processual:
1. Consensus: Tech quer B, Finance quer A, convergem C
2. Documentação: protocolo [SYNC] suporta mudanças rápidas
3. Reversibilidade: se C falha, fácil pivotar B
4. Stakeholder alignment: todos podem com C
5. Meu voto: FAVORÁVEL C"
```

### Para The Brain (ML) — 4 min

```
"Minha perspectiva científica:
1. Rigor: B > C > A, mas B leva 7 dias
2. Walk-Forward: B garante OOT >80%, C ~60%
3. Confiança produção: B=> Sharpe >0.5; C=> Sharpe ~0.2
4. Timeline: C é compromisso aceitável
5. Meu voto: CONDICIONAL (prefiro B, tolero C)"
```

### Para Dr. Risk (Head Finanças) — 4 min

```
"Minha perspectiva financeira:
1. TCO: A=-$13.3k, B=-$26.7k, C=-$13.3k
2. Break-even: C chega profitabilidade dia 20
3. Capital: preservação garantida com circuit breakers
4. ROI: C espero ~30% aa
5. Meu voto: FAVORÁVEL C"
```

...e assim para cada um dos 16 membros.

---

## 💾 PÓS-REUNIÃO (Relatório Exportado)

### Arquivo gerado automaticamente

```
reports/board_meeting_1_ML_TRAINING_STRATEGY.md
```

**Conteúdo:**
- ✅ Decisão apresentada (completa)
- ✅ Opiniões de TODOS 16 membros
- ✅ Argumentos detalhados
- ✅ Riscos apontados
- ✅ Posição final (FAVORÁVEL/CONTRÁRIO/etc)
- ✅ Resultado de votação
- ✅ Próximos passos

### Como usar o relatório

1. **Auditoria [SYNC]:** Garantir rastreabilidade de decisão
2. **Comunicação:** Compartilhar com investidor/stakeholders
3. **Implementação:** Owner tem checklist de ações
4. **Histórico:** Arquivo permanente da decisão

---

## 🎯 CHECKLIST FACILITADOR

Antes da reunião:
- [ ] Preparar cenário (executar script)
- [ ] Banco de dados criado
- [ ] Pauta estruturada impressa/disponível
- [ ] Pautas por especialidade distribuídos

Durante a reunião:
- [ ] Apresentação (5 min)
- [ ] Pauta estruturada (5 min)
- [ ] Ciclo de opiniões (40 min) — guardar tempo
- [ ] Síntese (5 min)
- [ ] Votação final (10 min)

Depois da reunião:
- [ ] Relatório exportado
- [ ] Relatório compartilhado com equipe
- [ ] Decision registrada em docs/DECISIONS.md
- [ ] Próximos passos comunicados

---

## 📞 SUPORTE

**Durante a reunião, se houver dúvidas:**

> "Consultem a pauta estruturada. Se não está claro, Elo pode clarificar."

**Repositório de referência:**
- `docs/EQUIPE_FIXA.md` — Profiles de cada membro (2.642 linhas!)
- `docs/SYNC_BOARD_MEETING_16_MEMBERS.md` — Infra técnica
- `scripts/README_BOARD_MEETINGS.md` — Como rodar os scripts

**Owner:** Elo (Facilitador)
**Contato:** Em reunião de board ou via Slack

---

## 📈 PRÓXIMA REUNIÃO

**Hoje (23 FEV):**
- ✅ Decision #2 — ML Training Strategy
- ✅ Decision #3 — Posições Underwater
- ✅ Decision #4 — Escalabilidade

**Amanhã/próxima:**
- [ ] Revisão de implementação (Arch + The Brain)
- [ ] Ajustes pós-implementação
- [ ] Validação de KPIs

---

**🎯 Pronto para reunião?** Let's go!

**Executor:**
```bash
python scripts/condutor_board_meeting.py --decisao ML_TRAINING_STRATEGY
```

**Tempo:** ~70 minutos
**Participantes:** 16 membros
**Owner:** Elo (Facilitador) + Angel (Decision Maker)
**Saída:** Relatório markdown com rastreabilidade [SYNC]
