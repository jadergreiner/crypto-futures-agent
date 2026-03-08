# ⚡ TAREFA-001: QUICK START ENGENHEIROS

**Status:** Iniciação rápida para 3 papéis
**Linguagem:** Português
**Encoding:** UTF-8
**Lint:** 80 caracteres máximo

---

## 🚀 PRÓXIMOS 15 MINUTOS (21 FEV 23:00-23:15)

### DEV: Engenheiro Software

```
1️⃣ CLONE & SETUP (5 min):
   git clone ...
   git checkout develop
   git checkout -b feature/TAREFA-001-heuristics
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt

2️⃣ ABRIR ARQUIVO (2 min):
   Arquivo: execution/heuristic_signals.py
   Estado atual: 566 LOC (RiskGate +
                          SignalComponent)
   Seu trabalho: Adicionar ~250 LOC motor

3️⃣ REVISAR SPECS (8 min):
   📄 TASK-001_PLANO_TECNICO_LIDER.md
      → Seção "TEMPLATE 1: MOTOR CORE"
   📄 TASK-001_TEMPLATES_IMPLEMENTACAO.md
      → Código skeleton pronto
   ✅ Entender: Classe HeuristicSignalGenerator
      (8+ métodos key)
   ✅ Entender: Integração RiskGate + auditoria
   ✅ Entender: Type hints obrigatórios

4️⃣ READY? (1 min):
   ✅ VS Code aberto
   ✅ Terminal pronto (venv ativo)
   ✅ Specs revisadas
   ✅ Templates copiados local
   → PROCEDER 23:30 @ coding kickoff
```

### BRAIN: Engenheiro Machine Learning

```
1️⃣ CLONE & SETUP (5 min):
   git clone ...
   git checkout develop
   git checkout -b feature/TAREFA-001-brain
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt

2️⃣ ABRIR ARQUIVOS (2 min):
   📄 indicators/smc.py (748 LOC)
   📄 indicators/technical.py (435 LOC)
   📄 indicators/multi_timeframe.py (265 LOC)

   Seu trabalho: +190 LOC total
                 (100+50+40 split)

3️⃣ REVISAR SPECS (8 min):
   📄 TASK-001_PLANO_TECNICO_LIDER.md
      → Seção "TEMPLATE 2: INDICADORES"
   📄 TASK-001_TEMPLATES_IMPLEMENTACAO.md
      → Specs dos 3 indicadores

   ✅ Entender: 3 métodos SMC (order blocks,
      FVG, BOS)
   ✅ Entender: 3 métodos Technical (EMA, DI+,
      DI-)
   ✅ Entender: 1 método MultiTimeframe
      (regime)
   ✅ Entender: Fórmula agregação confiança
   ✅ Vetorização: Usar numpy/pandas (SEM
      loops)

4️⃣ READY? (1 min):
   ✅ VS Code + Jupyter (optional)
   ✅ Terminal pronto
   ✅ Specs revisadas
   ✅ Templates copiados
   → PROCEDER 23:30
```

### AUDIT: Gerente QA

```
1️⃣ CLONE & SETUP (5 min):
   git clone ...
   git checkout develop
   git checkout -b feature/TAREFA-001-audit
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements-test.txt

2️⃣ ABRIR ARQUIVO (2 min):
   📄 tests/test_heuristic_signals.py
   Estado: Framework básico exist (378 LOC)
   Seu trabalho: Adicionar ~150 LOC testes

3️⃣ REVISAR SPECS (8 min):
   📄 TASK-001_PLANO_TECNICO_LIDER.md
      → Seção "Matriz Plano Testes"
   📄 TASK-001_TEMPLATES_IMPLEMENTACAO.md
      → Template TEMPLATE 3: TESTES QA

   ✅ Entender: 7 grupos testes (RiskGate,
      Component, Generator, EdgeCases,
      Performance, Auditoria, Regime)
   ✅ Entender: 19+ testes OBRIGATÓRIOS
      (baseline)
   ✅ Entender: Edge cases críticos
      (5: baixa liquidez, flash crash,
      timeout, funding rate, data vazia)
   ✅ Entender: Performance targets
      (<100ms, <2KB, <6s/60pares)

   Fixtures + Mocks:
   - Mock OHLCV data (prepreparado)
   - Mock generator instance
   - Patch llamadas externas (se needed)

4️⃣ READY? (1 min):
   ✅ pytest pronto (pytest --version)
   ✅ Terminal ativo
   ✅ Specs revisadas
   ✅ Templates copiados
   ✅ Fixtures framework pronto
   → PROCEDER 23:30
```

---

## 📅 CRONOGRAMA VISUAL

```
21 FEV 23:00 ┬─────────────── 6 HORAS ─────────────┬ 22 FEV 06:00
              │                                       │
              ├─ FASE 1: PREP (23:00-23:30)          │
              │  └─ DEV/BRAIN/AUDIT setup ✅         │
              │                                       │
              ├─ FASE 2: CODING (23:30-02:00) ▮▮▮▮  │ ← PARALLEL
              │  ├─ Dev: Motor core      ████        │
              │  ├─ Brain: Indicators    ████        │
              │  └─ Audit: Fixtures prep ████        │
              │                                       │
              ├─ FASE 3: REVIEW (02:00-03:30)        │
              │  ├─ Code review         ████        │
              │  └─ Integration test    ████        │
              │                                       │
              ├─ FASE 4: MERGE (03:30-06:00)         │
              │  ├─ Merge main          ████        │
              │  ├─ Sync docs           ████        │
              │  └─ Sanidade final      ████        │
              │                                       │
              └─ ✅ GO-LIVE READY (06:00) ✅ ✅ ✅ ✅
```

---

## ✅ DO's & DON'Ts

### DEV: Implementador Motor Core

**DO's:**
- ✅ Comece com scaffolding classe
  (métodos stub)
- ✅ Implemente método gerar_sinal()
  primeiro (orquestrador)
- ✅ Use type hints em TUDO
- ✅ Log + return None (nunca raise
  exceção)
- ✅ Docstrings Google-style
- ✅ Teste local regularmente
  (pytest tests/test_heuristic_signals.py)
- ✅ Commit small (após cada método
  completo)

**DON'Ts:**
- ❌ Não implementar lógica business
  dentro indicadores (Brain responsável)
- ❌ Não mudar RiskGate limites
  (usar -3%/-5% default)
- ❌ Não fazer magic numbers (usar
  constants)
- ❌ Não esquecer validação entradas
- ❌ Não deixar debugging leftover
  (print, breakpoints)
- ❌ Não push sem testar local

### BRAIN: Aprimorador Indicadores

**DO's:**
- ✅ Use numpy/pandas vetorizado
  (ZERO loops)
- ✅ Retornar tipos corretos (float,
  str, List)
- ✅ Implementar fórmula confiança
  (agregação ponderada)
- ✅ Testar cada indicador isolado
  (unit test)
- ✅ Type hints + docstrings
- ✅ Integração com Dev @ 02:00

**DON'Ts:**
- ❌ Não deixar métodos partial/stub
- ❌ Não mudar assinatura função
  (quebra compat)
- ❌ Não usar loops (use pandas
  apply/vectorize)
- ❌ Não hardcode valores (use
  constants/params)
- ❌ Não implementar lógica RiskGate
  (Dev responsável)

### AUDIT: Gestor Testes

**DO's:**
- ✅ Prepare fixtures/mocks EARLY
  (23:00-23:30)
- ✅ Use pytest parametrize
  (múltiplos cenários)
- ✅ Teste edge cases PRIMEIRO
  (são críticos)
- ✅ Valide risk gates (CLEARED, RISKY,
  BLOCKED)
- ✅ Medir performance (timing, memory)
- ✅ 100% cobertura caminhos críticos

**DON'Ts:**
- ❌ Não esperar tudo pronto pra testar
  (testar incrementalmente)
- ❌ Não deixar tests com skip/xfail
  (exceto known blockers)
- ❌ Não testar apenas happy path
  (edge cases!)
- ❌ Não confiar mock 100% (validar
  integração real @ 03:00)

---

## 🎯 OBJETIVO FINAL CADA PAPEL

**Dev:** 250 LOC motor funcional, 100%
type hints, ZERO exceções não-tratadas
✅

**Brain:** 190 LOC indicadores
aprimorados, 100% vetorizado, fórmula
confiança clara ✅

**Audit:** 28+ testes PASS rate 100%,
edge cases covered, performance
validated ✅

**Todos:** Merge main @ 04:00 UTC,
go-live 06:00 UTC ✅

---

**Comece agora!** ⏱️ 00:00 UTC

Próxima stop: 23:30 → Coding kickoff

Última atualização: 22 FEV 2026
