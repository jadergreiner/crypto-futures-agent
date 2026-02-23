# 🚪 QA Gates S2-0 — Data Strategy (1Y × 60 Symbols)

**Versão:** 1.0.0
**Data:** 22 FEV 2026
**Role:** Audit (#8) — QA Lead & Documentation Officer
**Status:** 🟡 EM DEFINIÇÃO → 🟢 PRONTO PARA VALIDAÇÃO

---

## 📋 Resumo Executivo

Dois gates de auditoria **simples e mensuráveis** definem quando S2-0 (Data Strategy) está pronto para desbloquear S2-3 (Backtesting).

| Gate | Nome | Complexidade | Owner | Critério | Métrica |
|------|------|-------------|-------|----------|---------|
| **1** | Dados & Integridade | 🟢 Simples | Data Engineer | All 60 symbols loaded, valid, cache < 100ms | ✅ Binance + SQLite |
| **2** | Qualidade & Testes | 🟠 Moderado | QA Lead | 5 testes PASS, 80% coverage, 0 regressions | ✅ pytest + coverage |

**Gating Logic:** S2-0 → GO somente se **ambos os gates** = ✅ GREEN.

---

## 🚪 Gate 1 — Dados & Integridade [SIMPLES]

**Responsável:** Data Engineer (#11) — Binance Integration Lead  
**Duração:** ~5 minutos (validação; 15-20 min = carga inicial)  
**Automação:** ✅ 100% (CLI + validadores)

### ✅ Critérios de Aceite

| # | Critério | Como Validar | Evidência | Pass/Fail |
|---|----------|------------|-----------|-----------|
| 1.1 | **60 símbolos carregados** | `klines_cache_manager.py fetch-all` + count | `SELECT COUNT(DISTINCT symbol) FROM klines` = 60 | ✅ GO |
| 1.2 | **Sem gaps (integridade)** | `klines_cache_manager.py validate-gaps` | Log: "0 gaps detected" | ✅ GO |
| 1.3 | **Sem duplicatas** | `klines_cache_manager.py validate-duplicates` | Log: "0 duplicates" | ✅ GO |
| 1.4 | **Preços válidos** | `klines_cache_manager.py validate-prices` | Log: "All prices ≥ 0.00001" | ✅ GO |
| 1.5 | **Cache read < 100ms** | `time klines_cache_manager.py query-symbol BTCUSDT` | Tempo: 42-98 ms | ✅ GO |
| 1.6 | **1Y de dados** | `SELECT MAX(timestamp) - MIN(timestamp)` | Diferença ≥ 360 dias | ✅ GO |
| 1.7 | **Tamanho SQLite esperado** | `ls -lh db/klines_cache.db` | ~650 KB (±100 KB) | ✅ GO |

### ❌ Critérios de Rejeição (NO-GO)

| # | Rejeição | Ação Mitigadora |
|---|----------|-----------------|
| 1.A | Qualquer símbolo com < 2000 candles | Re-fetch com retry exponencial; escalate se Binance 429 |
| 1.B | Gap > 1 vela (4h) em qualquer série | Re-fetch período faltante; validar timestamps |
| 1.C | Preço zero, NaN, ou negativo em > 0.1% | Rollback para backup anterior; investigar source |
| 1.D | Cache read > 150 ms em 3 tentativas | Index otimização; considerar Parquet para read paths |

### 📊 Checklist de Validação

```bash
# Rodas sequencialmente - interromper em qualquer falha
./data/scripts/klines_cache_manager.py fetch-all --check-rate-limits
./data/scripts/klines_cache_manager.py validate-gaps
./data/scripts/klines_cache_manager.py validate-duplicates
./data/scripts/klines_cache_manager.py validate-prices
time ./data/scripts/klines_cache_manager.py query-symbol BTCUSDT
sqlite3 db/klines_cache.db "SELECT COUNT(*), COUNT(DISTINCT symbol), MAX(timestamp)-MIN(timestamp) FROM klines;"
```

**Saída esperada (GO):**
```
✅ 131,400 candles loaded
✅ 0 gaps detected
✅ 0 duplicates
✅ All prices valid
✅ Cache read: 64 ms
✅ Date range: 365 days
✅ File size: 647 KB
```

---

## 🎯 Gate 2 — Qualidade & Testes [MODERADO]

**Responsável:** QA Lead (#8) — Audit Authority  
**Duração:** ~10 minutos (testes) + code review  
**Automação:** ✅ 80% (pytest + coverage); ❌ 20% (manual review)

### ✅ Critérios de Aceite

| # | Critério | Como Validar | Evidência | Pass/Fail |
|---|----------|------------|-----------|-----------|
| 2.1 | **5 testes PASS** (unit + integration) | `pytest tests/data/test_klines_*.py -v` | `5 passed` | ✅ GO |
| 2.2 | **Cobertura ≥ 80%** | `pytest --cov=data --cov-report=html` | Relatório: 80%+ | ✅ GO |
| 2.3 | **Nenhuma regressão Sprint 1** | `pytest tests/ -v` | Resultado: 70 PASS (sem novo FAIL) | ✅ GO |
| 2.4 | **Docstrings (100% classes/funções)** | Code review `data/scripts/*.py` | ✓ Revisado | ✅ GO |
| 2.5 | **README.md (data/)** | Arquivo existe, ≥ 300 palavras | ✓ Arquivo OK | ✅ GO |
| 2.6 | **Sem warnings (pylint < 5)** | `pylint data/scripts/klines_cache_manager.py` | Score ≥ 8.0 | ✅ GO |

### ❌ Critérios de Rejeição (NO-GO)

| # | Rejeição | Ação Mitigadora |
|---|----------|-----------------|
| 2.A | Qualquer teste FAIL | Fix + re-run; escalate se > 3 rejeições |
| 2.B | Cobertura < 75% | Adicionar unit tests para linhas uncovered |
| 2.C | Regressão em Sprint 1 (novo FAIL em 70) | Rollback mudança culpada; merge apenas com green |
| 2.D | Docstring missing (> 5% de funções) | Completar antes de sign-off |
| 2.E | README.md ausente ou < 150 palavras | Criar conforme template em `docs/` |

### 📊 Checklist de Testes

```bash
# Testes unitários
pytest tests/data/test_klines_cache_manager.py -v
pytest tests/data/test_rate_limiter.py -v
pytest tests/data/test_validator.py -v

# Cobertura
pytest --cov=data/scripts --cov-report=html

# Sem regressions
pytest tests/ -v --tb=short

# Qualidade código
pylint data/scripts/klines_cache_manager.py
```

**Saída esperada (GO):**
```
test_klines_cache_manager.py::test_fetch_all PASSED
test_klines_cache_manager.py::test_validate_gaps PASSED
test_rate_limiter.py::test_exponential_backoff PASSED
test_validator.py::test_price_validation PASSED
test_validator.py::test_timestamp_validation PASSED

============ 5 passed in 2.34s ============

Coverage: data/scripts/klines_cache_manager.py: 84%
Coverage: Total: 81%

All Sprint 1 tests: 70 PASSED

pylint score: 8.7/10
```

---

## 📋 Checklist de Documentação [6 itens]

**Responsável:** Documentation Officer (#8)  
**Status:** Antes de sign-off, todos abaixo = ✅

| # | Item | Arquivo | Critério | ✅ |
|---|------|---------|----------|-----|
| **D1** | Docstrings em classes/funções | `data/scripts/klines_cache_manager.py` | 100% cobertura em PT | ☐ |
| **D2** | README.md (data/) | `data/README.md` | ≥ 300 palavras, setup + troubleshooting | ☐ |
| **D3** | CRITERIOS atualizado | `docs/CRITERIOS_DE_ACEITE_MVP.md` | Seção S2-0 criada com Gates 1-2 | ☐ |
| **D4** | Trade-offs documentados | `docs/DECISIONS.md` | Nova seção "S2-0: Cache Strategy" | ☐ |
| **D5** | Sync registry | `docs/SYNCHRONIZATION.md` | Entry [SYNC] S2-0 criada | ☐ |
| **D6** | Status atualizado | `docs/STATUS_ENTREGAS.md` | Item S2-0 marcado como "🟢 VALIDADO" | ☐ |

### D1 — Docstrings Checklist

```python
# Exemplo esperado (PT):
def fetch_all_symbols(num_retries: int = 3) -> pd.DataFrame:
    """
    Busca candles de 1 ano para todos os 60 símbolos de Binance.
    
    Parâmetros:
        num_retries: Número de tentativas em caso de erro (rate limit).
    
    Retorna:
        DataFrame com colunas [symbol, timestamp, open, high, low, close, volume].
    
    Levanta:
        BinanceException: Se Binance retorna erro permanente.
        RateLimitError: Se excedem rate limits após retries.
    
    Exemplo:
        >>> df = fetch_all_symbols()
        >>> len(df)
        131400
    """
```

### D2 — README.md Template

```markdown
# Data Pipeline S2-0

## Overview
Carga e cache de 1 ano × 60 símbolos (Binance Futures 4h).

## Instalação

## Como usar
- Fetch ...
- Query ...
- Validate ...

## Troubleshooting
- Rate limit 429 → exponential backoff
- Gaps em dados → re-fetch
```

---

## 👥 Matriz de Responsabilidades

| Gate | Validador Principal | Validador Secundário | Escalation | Sign-Off |
|------|-------------------|----------------------|-----------|----------|
| **Gate 1** (Dados) | Data Engineer (#11) | Arch (#6) | Dr. Risk → Angel | Data Engineer (#11) |
| **Gate 2** (Qualidade) | QA Lead (#8) | Arch (#6) | Guardian (#5) | QA Lead (#8) |
| **Sign-Off Final** | — | — | Audit (#8) | Angel (#1) |

### Definições de Papéis

**Data Engineer (#11):**
- Executa validações Gate 1
- Interpreta logs de Binance
- Re-fetch em caso de falha
- Assina Gate 1 com timestamp

**QA Lead (#8):**
- Executa testes Gate 2
- Valida cobertura + regressions
- Auditoria de documentação (6 itens)
- Assina Gate 2 com timestamp

**Arch (#6) — Validador Secundário:**
- Spot-check: performance > requisitos?
- Cache design ainda ótimo?
- Trade-offs documentados?

**Guardian (#5) — Escalation:**
- Se Gate 1 falhar > 2 vezes: rate limits podem estar comprometendo segurança?
- Se Gate 2 falhar: cobertura insuficiente para backtesting crítico?

**Angel (#1) — Sign-Off Final:**
- Revisa ambos os gates ✅
- Autoriza bloqueio de S2-3
- Documenta decisão em DECISIONS.md

---

## 🎯 Critério de "PRONTO" (Ready for S2-3)

| Condição | Status |
|----------|--------|
| Gate 1 ✅ | Data Engineer assinou |
| Gate 2 ✅ | QA Lead assinou |
| Documentação ✅ | 6/6 itens concluídos |
| Sem riscos abertos | Todos escalados resolvidos |
| Board aprovação | Angel assinou |
| **Status Final** | **🟢 GO → Desbloqueia S2-3** |

### Fluxo de Aprovação

```
S2-0 Pronto para Validação
        ↓
    [Gate 1: Dados]
    Data Engineer (#11)
        ↓ ✅ PASS
    [Gate 2: Qualidade]
    QA Lead (#8)
        ↓ ✅ PASS
    [Documentação]
    Documentation Officer
        ↓ ✅ 6/6 Itens
    [Sign-Off Final]
    Angel (#1)
        ↓ ✅ APPROVE
    🟢 S2-0 VALIDADO
        ↓
    🔵 S2-3 DESBLOQUEADO (Backtesting)
```

---

## 📅 Timeline Esperada

| Fase | Duração | Owner |
|------|---------|-------|
| **Setup inicial** | 15-20 min | Data Engineer (#11) |
| **Gate 1 validação** | 5-10 min | Data Engineer (#11) |
| **Gate 2 testes** | 10-15 min | QA Lead (#8) |
| **Documentação review** | 10-15 min | Documentation Officer (#8) |
| **Sign-off final** | 5 min | Angel (#1) |
| **Total** | **~60 minutos** | — |

---

## 🔴 Procedimento de Rejeição

Se **qualquer gate FAIL** ou documentação incompleta:

1. **Log da falha** → arquivo em `logs/gate-failures/s2-0-gate-X-YYYYMMDD-HHMM.txt`
2. **Root cause** → Data Engineer ou QA Lead investiga
3. **Correção** → Fix enviado para branch `data-strategy-fixes` (feito)
4. **Re-validação** → Gate re-executa (máx 2 rejeições)
5. **Escalate** → Se > 2 rejeições: Guardian → Dr. Risk → Angel

---

## 📊 Registro de Validações

**A preencher após cada validação:**

| Data | Gate | Owner | Status | Evidência | Notas |
|------|------|-------|--------|-----------|-------|
| 2026-02-22 | 1 | Data Engineer | TBD | TBD | — |
| 2026-02-22 | 2 | QA Lead | TBD | TBD | — |
| 2026-02-22 | Final | Angel | TBD | TBD | — |

---

## 🔗 Links Relacionados

- [DATA_STRATEGY_BACKTESTING_1YEAR.md](DATA_STRATEGY_BACKTESTING_1YEAR.md) — Spec técnica
- [DATA_PIPELINE_QUICK_START.md](DATA_PIPELINE_QUICK_START.md) — Setup runbook
- [CRITERIOS_DE_ACEITE_MVP.md](CRITERIOS_DE_ACEITE_MVP.md) — Critérios MVP (atualizar S2-0)
- [DECISIONS.md](DECISIONS.md) — Trade-offs (atualizar S2-0)
- [SYNCHRONIZATION.md](SYNCHRONIZATION.md) — Audit trail (registrar [SYNC])
- [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) — Dashboard (marcar 🟢 quando GO)

---

*Documento criado: Audit (#8) — QA Lead & Documentation Officer*  
*Última atualização: 2026-02-22 23:58 UTC*
