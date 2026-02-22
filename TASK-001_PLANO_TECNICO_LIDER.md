# 🎯 TAREFA-001: PLANO TÉCNICO LÍDER

**Status:** ✅ Planejamento Pronto para Execução
**Data:** 22 FEV 2026 | **Versão:** 1.0
**Líder Técnico:** The Architect
**Cronograma:** 21 FEV 23:00 → 22 FEV 06:00 UTC (6h limite)
**Equipes:** Dev + Brain (ML) + Audit (QA)

---

## 📋 RESUMO EXECUTIVO

Implementar heurísticas conservadoras de trading (TAREFA-001) para
operações ao vivo antes do modelo PPO convergir. Estratégia:
paralelizar desenvolvimento em 3 eixos simultâneos.

**Entregáveis por Eixo:**

| Eixo | Responsável | Duração | Artefatos |
|------|-------------|---------|-----------|
| **Motor Core** | Dev | 4.5h | `execution/heuristic_signals.py` (250 LOC) |
| **Indicadores** | Brain | 4.5h | Enhancements em `indicators/` (190 LOC) |
| **Testes QA** | Audit | 6h | `tests/test_heuristic_signals.py` (19+ testes) |

**Caminho Crítico:** Dev core (0-2h) → Brain (0-3h) → QA testes
(paralelo 0-6h)

**Ponto de Merge:** 22 FEV 06:00 UTC

---

## 🏗️ DECISÃO ARQUITETURAL

### Estrutura de Código

```
execution/
├── heuristic_signals.py          (TAREFA-001 Core ~250 LOC)
│   ├── HeuristicSignalGenerator  (orquestrador principal)
│   ├── RiskGate                  (proteção risco inline)
│   └── SignalComponent           (estrutura componente)
│
indicators/
├── smc.py                        (aprimorado: detecção SMC)
├── technical.py                  (aprimorado: indicadores)
├── multi_timeframe.py            (aprimorado: regime)
└── features.py                   (aprimorado: features)

tests/
├── test_heuristic_signals.py     (19+ testes unitários)
│   ├── TestRiskGate
│   ├── TestSignalComponent
│   ├── TestHeuristicSignalGenerator
│   ├── TestEdgeCases
│   └── TestPerformance
└── test_indicators.py            (testes indicadores)
```

### Componentes a Implementar

```python
# execution/heuristic_signals.py

HeuristicSignalGenerator
├── __init__(configs_indicadores)
├── gerar_sinal(simbolo, dados_ohlcv, regime, dados_d1,
│                dados_h4, dados_h1)
│   ├── Step 1: Validar entradas
│   ├── Step 2: Computar componentes
│   ├── Step 3: Agregar confiança
│   ├── Step 4: Risk gates
│   ├── Step 5: Construir sinal
│   └── Step 6: Log auditoria
├── avaliar_componentes(dados_preco) → List[SignalComponent]
├── computar_score_confluencia(componentes) → int
├── avaliar_risco(saldo_atual, pico_sessao) → str
└── logar_auditoria(sinal, decisao) → None

RiskGate
├── avaliar(saldo_atual, pico_sessao) → (status, mensagem)
├── obter_nivel_risco() → "CLEARED" | "RISKY" | "BLOCKED"
└── checar_circuit_breaker() → bool

SignalComponent
├── nome: str (smc|ema_alignment|rsi|adx)
├── valor: float
├── limiar: float
├── valido: bool
└── confianca: float (0-1)

HeuristicSignal (dataclass)
├── simbolo, timestamp, tipo_sinal
├── componentes: List[SignalComponent]
├── confianca: float (0-100)
├── score_confluencia: int (0-14)
├── regime_mercado: str (RISK_ON|RISK_OFF|NEUTRO)
├── viés_d1: str (BULLISH|BEARISH|NEUTRO)
├── avaliacao_risco: str (CLEARED|RISKY|BLOCKED)
├── preco_entrada, stop_loss, take_profit
├── razao_risco_retorno: Optional[float]
└── auditoria: Dict
```

---

## 🚀 PLANO DE IMPLEMENTAÇÃO PARALELO

### FASE 1: PREPARAÇÃO (21 FEV 23:00 - 23:30 UTC) — 30min

**Ações Simultâneas:**

```
TODOS OS TIMES:
  ✓ Clonar main mais recente
  ✓ Criar branch: feature/TAREFA-001-heuristics
  ✓ Obter especificações (este documento)
  ✓ Setup ambiente local

DEV:
  ✓ Revisar execution/heuristic_signals.py (estado atual)
  ✓ Validar RiskGate + SignalComponent existentes
  ✓ Identificar gaps HeuristicSignalGenerator
  ✓ Preparar templates de código

BRAIN:
  ✓ Revisar módulos indicators/ (SMC, Technical, MultiTimeframe)
  ✓ Identificar cálculos faltando
  ✓ Preparar estratégia cálculo confiança
  ✓ Preparar lógica detecção regime

AUDIT:
  ✓ Revisar test_heuristic_signals.py (versão atual)
  ✓ Preparar matriz plano teste (9+ testes)
  ✓ Setup ambiente pytest
  ✓ Preparar cenários edge case
```

**Checkpoint:** 23:30 → Confirmar todas branches + specs revisadas
(Slack: #tarefa-001-dev)

---

### FASE 2A: DESENVOLVIMENTO MOTOR CORE (23:30 - 02:00) — 2.5h

**Responsável:** Dev
**Entregáveis:**

1. ✅ Classe `HeuristicSignalGenerator` completa (150 LOC)
2. ✅ Integração com `RiskGate` + `SignalComponent`
3. ✅ Implementação orquestrador `gerar_sinal()`
4. ✅ Log auditoria (conformidade)
5. ✅ Tratamento erros + edge cases

**Especificação Técnica:**

Fluxo completo:

1. Componentes: SMC, EMA alignment, RSI, ADX →
   List[SignalComponent]
2. Agregação: confiança & score_confluencia
3. Risk gates: Verificar drawdown, circuit breaker
4. Razão R:R: Validação entrada/stop/take profit
5. Auditoria: Todas decisões logged

**Tratamento Erros:**
- Log + retorna None (não raise)
- Sem exceções propagam acima
- Mensagens em português

**Checkpoint:** 02:00 UTC → Dev code review pass, pronto para
integração Brain/Audit

---

### FASE 2B: APRIMORADOR INDICADORES (23:30 - 02:00) — 2.5h

**Responsável:** Brain (Engenheiro ML)

**Entregáveis:**

1. ✅ Aprimorado `indicators/smc.py` (~100 LOC)
2. ✅ Aprimorado `indicators/technical.py` (~50 LOC)
3. ✅ Aprimorado `indicators/multi_timeframe.py` (~40 LOC)
4. ✅ Fórmula cálculo confiança documentada
5. ✅ Testes integração indicadores (5+ testes)

**Métodos a Implementar:**

SMC:
- `detect_order_blocks(dados)` → List[Dict] com zonas frescas
- `detect_fair_value_gaps(dados)` → List[Dict] FVGs abertos
- `detect_break_of_structure(dados)` → "BULLISH_BOS" |
  "BEARISH_BOS" | "NO_BOS"

Technical:
- `calculate_ema_alignment(dados)` → +1.0 | 0.0 | -1.0
- `calculate_di_plus(dados)` → pd.Series (0-100)
- `calculate_di_minus(dados)` → pd.Series (0-100)

Multi-Timeframe:
- `detect_regime(d1, h4, h1)` → "RISK_ON" | "RISK_OFF" |
  "NEUTRAL"

**Otimizações:**
- Usar numpy/pandas (vetorizado, sem loops)
- Type hints obrigatórios
- Docstrings Google-style
- Sem quebra compatibilidade APIs existentes

**Checkpoint:** 02:00 UTC → Brain enhancements QA pass, pronto para
integração Dev

---

### FASE 2C: SUITE TESTES QA (23:30 - 06:00) — 6h PARALELO

**Responsável:** Audit (Gerente QA)

**Entregáveis:**

1. ✅ Suite testes unitários (9+ testes base)
2. ✅ Testes integração (10+ testes adicionais)
3. ✅ Cenários edge case (5 críticos)
4. ✅ Baseline performance
5. ✅ Validação risk gates
6. ✅ Relatório QA sign-off

**Matriz Plano Testes:**

```
GRUPO 1: RiskGate (4 testes)
├─ test_risk_gate_avaliacao_cleared()
├─ test_risk_gate_avaliacao_risky()
├─ test_risk_gate_circuit_breaker()
└─ test_risk_gate_sem_historico()

GRUPO 2: SignalComponent (2 testes)
├─ test_signal_component_criacao()
└─ test_signal_component_serializacao()

GRUPO 3: HeuristicSignalGenerator (6+ testes)
├─ test_gerar_sinal_basico()
├─ test_gerar_sinal_todos_componentes_validos()
├─ test_gerar_sinal_componentes_parciais()
├─ test_gerar_sinal_bloqueado_por_risk_gate()
├─ test_avaliar_componente_smc()
├─ test_ema_alignment_bullish()
├─ test_ema_alignment_bearish()
├─ test_rsi_oversold_deteccao()
├─ test_rsi_overbought_deteccao()
├─ test_adx_trend_confirmacao()
└─ test_score_confluencia_calculo()

GRUPO 4: Edge Cases (5+ testes)
├─ test_edge_case_baixa_liquidez()
├─ test_edge_case_flash_crash()
├─ test_edge_case_timeout_rede()
├─ test_edge_case_funding_rate_extremo()
└─ test_edge_case_dataframe_vazio()

GRUPO 5: Risk Gate Detalhado (3+ testes)
├─ test_risk_gate_limiar_max_drawdown()
├─ test_risk_gate_estado_persistente()
└─ test_risk_gate_reset_novo_pico()

GRUPO 6: Performance (3+ testes)
├─ test_latencia_baseline_execucao()
├─ test_footprint_memoria()
└─ test_geracao_sinal_batch()

GRUPO 7: Auditoria (2+ testes)
├─ test_auditoria_trail_logging()
└─ test_auditoria_campos_compliance()

TOTAL: 28+ testes (baseline 9+ mínimo)
```

**Cenários Edge Case:**

1. Baixa liquidez: volume < 10 BTC, RSI extremo
2. Flash crash: -8% intraday, rejeita sinal
3. Network timeout: dados faltando → graceful failure
4. Funding rate extremo: ADX=0 (sideways) → sem sinal
5. DataFrame vazio: erro validação → None + logged

**Baseline Performance:**

- Latência: < 100ms por símbolo
- Memória: < 2KB por sinal
- Batch 60 símbolos: < 6s total
- Throughput: ~10 sinais/seg aceitável

**Checkpoint:** 03:30 UTC → Todos 28+ testes PASS, QA approval

---

### FASE 3: CODE REVIEW & INTEGRAÇÃO (02:00 - 03:30 UTC) — 1.5h

**Participantes:** Dev, Brain, Audit, Blueprint (revisor código)

**Processo em Sequência:**

```
1️⃣ Dev Code Review (02:00 - 02:30)
   └─ Motor core (execution/heuristic_signals.py)
   └─ Verificar: Docstrings, tratamento erro, style
   └─ Checkpoint: Aprovação Blueprint

2️⃣ Brain Code Review (02:00 - 02:30)
   └─ Enhancements indicadores
   └─ Verificar: Vetorização (numpy/pandas), sem loops
   └─ Checkpoint: Aprovação Blueprint

3️⃣ Audit Code Review (02:00 - 02:30)
   └─ Suite testes + cobertura
   └─ Verificar: Mocking, fixtures, edge cases
   └─ Checkpoint: Aprovação Blueprint

4️⃣ Testes Integração (02:30 - 03:30)
   └─ Dev + Brain + Audit executam integração
   └─ Executar: pytest tests/test_heuristic_signals.py -v
   └─ Verificar: 100% pass, cobertura > 95%
   └─ Checkpoint: Pipeline CI/CD verde

5️⃣ Aprovação Final Blueprint (03:30)
   └─ Todos reviews passam
   └─ Pronto merge feature/TAREFA-001-heuristics → main
```

**Checklist Code Review:**

```
☐ Type hints em todas funções
☐ Docstrings (Google-style)
☐ Tratamento erro (log + return None, sem bubbles)
☐ Sem números mágicos hardcoded (constants definidas)
☐ Sem imports não usados
☐ Português em comentários críticos
☐ ASCII commit (até merge)
☐ Cobertura teste 100%
☐ Performance < 100ms por sinal
☐ Risk gates testados apropriadamente
☐ Auditoria trail logging completo
☐ Aprovação final Blueprint ✅
```

---

### FASE 4: MERGE & SINCRONIZAÇÃO (03:30 - 06:00 UTC) — 2.5h

**Participantes:** Dev (+ Git master), Planner, Audit

**Sequência:**

```
1️⃣ Verificação Status Final (03:30 - 03:45)
   ├─ Dev: Código revisado ✅
   ├─ Brain: Indicadores integrados ✅
   ├─ Audit: Testes 19+ todos pass ✅
   └─ Blueprint: Aprovação assinada ✅

2️⃣ Merge para Main (03:45 - 04:00)
   ├─ git merge feature/TAREFA-001-heuristics → main
   ├─ Mensagem commit: [SYNC] TAREFA-001 Heurísticas —
   │   prontas go-live
   ├─ Tag: TAREFA-001-v1.0
   └─ Push → origin main

3️⃣ Sincronização Documentação (04:00 - 04:30)
   ├─ Criar: TAREFA-001_COMPLETION_REPORT.md
   │   ├─ Entregáveis: 250 LOC + 19 testes +
   │   │   indicadores enhanced
   │   ├─ Cronograma: 6h total, no schedule
   │   ├─ Avaliacao risco: CLEARED (todos gates
   │   │   passando)
   │   └─ Prontidão: 100% (QA aprovado)
   │
   ├─ Atualizar: TASKS_TRACKER_REALTIME.md
   │   ├─ TAREFA-001: ✅ CONCLUÍDA (100%)
   │   ├─ Status: Pronto TAREFA-002 (testes QA)
   │   └─ Timestamp: 22 FEV 04:30 UTC
   │
   ├─ Atualizar: docs/SYNCHRONIZATION.md
   │   ├─ Código: execution/ + indicators/ + tests/
   │   ├─ Docs: TAREFA-001_COMPLETION_REPORT.md (novo)
   │   ├─ Timestamp: 22 FEV 04:30 UTC
   │   └─ Status: ✅ Sincronizado
   │
   └─ Atualizar: README.md (se necessário)
       └─ Adicionar TAREFA-001 seção FEATURES

4️⃣ Preparar Handoff TAREFA-002 (04:30 - 05:00)
   ├─ Planner: Notificar Audit (testes QA começam 06:00)
   ├─ Dev: Disponível para suporte during QA (se problemas)
   ├─ Brain: Standby perguntas indicadores
   ├─ Package: executable main.py com heuristics
   └─ Sanity: Um teste live (paper trading) antes 06:00

5️⃣ Verificação Sanidade Final (05:00 - 06:00)
   ├─ Teste Paper Trading (1h)
   │   ├─ Carregar últimas 100 barras D1/H4/H1
   │   ├─ Executar gerador sinal heurística
   │   ├─ Verificar: Sinais gerados (não null)
   │   ├─ Confirmar: Risk gates funcional (-3/-5%)
   │   └─ Checar: Latência < 100ms por sinal
   │
   ├─ Reviewed Log Erro
   │   └─ Zero tolerância erros (avisos aceitáveis)
   │
   └─ Sucesso Critérios Atingidos ✅
       ├─ Código merged para main
       ├─ Todos testes passam
       ├─ Docs sincronizados
       └─ Pronto TAREFA-002 (06:00 UTC)
```

---

## 🔄 MATRIZ SINCRONIZAÇÃO

### Pontos de Verificação (A cada 1.5h)

| Hora | Dev | Brain | Audit | Planner | Ação |
|------|-----|-------|-------|---------|------|
| 23:30 | Kickoff | Kickoff | Kickoff | Monitor | Confirmar starts |
| 00:45 | ~30% | ~30% | Prep testes | Monitor | Check progresso |
| 02:00 | ~50% | ~50% | ~33% | Monitor | Code review inicia |
| 03:30 | ~80% | ~80% | ~66% | Monitor | Testes integração |
| 05:00 | 100% | 100% | 100% | Monitor | Merge + sync |
| 06:00 | DONE ✅ | DONE ✅ | DONE ✅ | DONE ✅ | Handoff TAREFA-002 |

### Protocolo Comunicação

```
STATUS TEMPO-REAL:
├─ Canal Slack: #tarefa-001-dev
├─ Updates: A cada 30min status
├─ Blockers: Escalação imediata (resposta 2min)
└─ Líder Técnico: Disponível decisões

ESCALAÇÃO DECISÃO:
├─ Nível 1: Dev/Brain/Audit podem decidir (< 15min impacto)
├─ Nível 2: Líder Técnico decide (15-30min impacto)
└─ Nível 3: Blueprint/Planner decide (>30min impacto)

COMPARTILHAMENTO ARTEFATO:
├─ Código: GitHub (feature branch)
├─ Testes: pytest output (logs compartilhados)
├─ Docs: Google Docs (collab tempo-real)
└─ Status: Slack thread + TASKS_TRACKER.md
```

---

## ✅ CRITÉRIOS ACEITAÇÃO

### Entrega Código

- ✅ `execution/heuristic_signals.py` (250 LOC)
  - [ ] Classe HeuristicSignalGenerator completa
  - [ ] Proteção RiskGate inline funcional
  - [ ] Log auditoria integrado
  - [ ] 100% docstrings (Google-style)
  - [ ] Type hints todas funções
  - [ ] Sem avisos/erros flake8/mypy

- ✅ `indicators/*.py` aprimorado
  - [ ] Detecção order block, FVG, BOS
  - [ ] Cálculo EMA alignment + ADX + DI+/DI-
  - [ ] Fórmula confiança implementada
  - [ ] ~200 LOC adicionado (sem breaking changes)

- ✅ `tests/test_heuristic_signals.py` (19+ testes)
  - [ ] 9/9 testes unitários passando (RiskGate testado)
  - [ ] 10+ testes adicionais (edge cases, integração)
  - [ ] Cobertura 100% caminhos críticos
  - [ ] Edge cases: baixa liquidez, flash crash, timeout,
    funding rate, data vazia
  - [ ] Performance: latência < 100ms por sinal
  - [ ] Risk gates validação: todos cenários testados

### Validação QA

- ✅ Taxa pass teste 100%
  - [ ] Todos 19+ testes: PASS
  - [ ] 0 blockers
  - [ ] ≤2 avisos permitidos (não críticos)

- ✅ Edge cases cobertos
  - [ ] Baixa liquidez: tratado
  - [ ] Flash crash: bloqueado por risk gate
  - [ ] Network timeout: degradação graceful
  - [ ] Funding rate extremo: sem sinal
  - [ ] DataFrame vazio: erro validação

- ✅ Risk gates testados
  - [ ] Drawdown < 3%: CLEARED
  - [ ] Drawdown 3-5%: RISKY
  - [ ] Drawdown > 5%: BLOCKED

- ✅ Performance validada
  - [ ] Execução < 100ms por símbolo
  - [ ] Memória < 2KB por sinal
  - [ ] Batch 60 pares < 6s

- ✅ Compliance verificada
  - [ ] Auditoria trail completo
  - [ ] Todas decisões logged
  - [ ] Avaliacao risco documentada

### Sincronização Documentação

- ✅ `TAREFA-001_COMPLETION_REPORT.md`
  - [ ] Entregáveis documentados
  - [ ] Cronograma: entregue no schedule
  - [ ] QA sign-off
  - [ ] Pronto próxima task

- ✅ `backlog/TASKS_TRACKER_REALTIME.md`
  - [ ] TAREFA-001: 100% status atualizado
  - [ ] Próxima task (TAREFA-002): Cronograma confirmado

- ✅ `docs/SYNCHRONIZATION.md`
  - [ ] Mudanças código: documentadas
  - [ ] Timestamp: 22 FEV 04:30 UTC
  - [ ] Status: ✅ Sincronizado

### Critérios Merge

- ✅ Code review aprovado por Blueprint
- ✅ Todos testes passam (CI/CD verde)
- ✅ Sem merge conflicts
- ✅ Mensagem commit: `[SYNC] TAREFA-001 Heurísticas —
  prontas go-live`
- ✅ Tag: `TAREFA-001-v1.0`
- ✅ Documentação sincronizada
- ✅ Pronto TAREFA-002: Testes QA

---

## 🚨 MITIGAÇÃO RISCO

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---|---|---|
| Dev overruns | Médio | ALTO | Code review @ 02:00, parallelizar |
| Brain quebra | Baixo | MÉDIO | Unit test isolado + integração |
| QA bug late | Baixo | ALTO | Edge cases cedo (02:00) + teste |
| Merge conflict | Baixo | MÉDIO | Dev merge final, rebase rápido |
| Latência alta | Médio | MÉDIO | Profiling @ 03:00, otimizar |
| Docs não sincronizadas | Baixo | BAIXO | Script auto-sync @ 04:30 |

---

## 📊 MÉTRICAS SUCESSO

| Métrica | Target | Status |
|---------|--------|--------|
| Entrega Código | 250 LOC | 🎯 Em track |
| Cobertura Teste | 19+ testes | 🎯 Em track |
| Taxa Pass Teste | 100% | ⏳ Aguardando |
| Latência | < 100ms/sinal | ⏳ Aguardando |
| Risk Gates | PASS todos | ⏳ Aguardando |
| Cronograma | 6h (23:00 → 06:00) | 🎯 Em track |
| **PRONTO GO-LIVE** | **SIM** | ⏳ Aguardando |

---

## 🎬 PRÓXIMOS PASSOS

1. **AGORA (21 FEV 23:00):** Todos times iniciam Fase 1
   (Preparação)
2. **23:30:** Dev + Brain iniciam coding paralelo
3. **02:00:** Code review + testes integração iniciam
4. **04:00:** Merge para main
5. **06:00:** Handoff TAREFA-002 (Testes QA)

**Status Líder Técnico:** 🟢 **PRONTO PARA LANÇAR**

---

**Proprietário Documento:** The Architect (Líder Técnico)
**Última Atualização:** 22 FEV 2026 | 23:00 UTC
**Próxima Revisão:** 22 FEV 02:00 UTC (checkpoint mid-phase)
