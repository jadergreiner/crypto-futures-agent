# 📊 Issue #67 — Data Strategy Implementation (S2-0 Phase 2) Specification

**Sprint:** 2-3 | **Lead:** Data (#11) | **Squad:** Data (#11) + Arch (#6) + Doc Advocate (#17)
**Deadline:** 26 FEV 18:00 UTC (~60h) | **Blocker:** Issue #65 QA (soft dependency)
**Status:** 📋 QUEUE → Kick-off 24 FEV ~15:00 UTC | **GitHash:** 9e8dd1c

---

## 📋 Objetivo

Implementar pipeline Data Strategy completo — 1Y × 60 símbolos OHLCV para backtesting + live trading:
- ✅ Carregamento automático 1 ano dados Binance
- ✅ Validação integridade (gaps, duplicatas, preços inválidos)
- ✅ Cache SQLite + Parquet (< 100ms read)
- ✅ 60 símbolos operacionais validados
- ✅ Production-ready documentado

**Critério Aceite:** [CRITERIOS_DE_ACEITE_MVP.md#s2-0](CRITERIOS_DE_ACEITE_MVP.md#s2-0) Gates 1+2 ✅

---

## 🎬 Timeline — 3 Fases (~60h / ~3 dias)

| Phase | Lead | Time | Output | Bloqueio |
|-------|------|------|--------|----------|
| **1: Design & Setup** | Data (#11) + Arch (#6) | 24 FEV 15:00–26 FEV 10:00 (19h) | Architecture review + scaffolding | Issue #65 Phase 1 ✅ |
| **2: Data Ingestion** | Data (#11) | 26 FEV 10:00–16:00 (6h) | 1Y data loaded + validation | Phase 1 ✅ |
| **3: Testing & Docs** | Data (#11) + Audit (#8) | 26 FEV 16:00–18:00 (2h) | Gate 1+2 ✅ + coverage ≥80% | Phase 2 ✅ |

---

## 📝 Phase 1: Design & Setup (24 FEV 15:00–26 FEV 10:00 UTC)

**Lead:** Data (#11) + Arch (#6)

### Tasks

- [ ] **Architecture Consensus** (Arch lead)
  - [ ] Pipeline flow: Binance REST → SQLite → Parquet cache
  - [ ] Performance targets: 1Y data < 5min, cache hit < 100ms
  - [ ] Data folder structure: `data/cache/`, `data/klines/`, `data/backups/`
  - [ ] Versioning strategy: `klines_cache_v1.db` (allows rollback)
  
- [ ] **Binance Integration Setup** (Data lead)
  - [ ] Reuse existing `data/binance_client.py` connector
  - [ ] Batch fetching: 1000-candle chunks to avoid rate limits
  - [ ] Retry logic: exponential backoff on 429/500 errors
  - [ ] Error handling: log failures, allow resume from checkpoint
  
- [ ] **Database Schema Design**
  - [ ] Table: `klines` (symbol, timestamp, open, high, low, close, volume)
  - [ ] Indexes: (symbol, timestamp) composite for fast queries
  - [ ] Checkpoints: track fetch progress per symbol
  - [ ] Audit table: (symbol, timestamp_start, timestamp_end, record_count)
  
- [ ] **Cache Layer**
  - [ ] Cache misses → SQLite query
  - [ ] Cache hits → in-memory Parquet file (< 100mb each symbol)
  - [ ] TTL policy: 24h cache validity
  - [ ] Eviction: LRU on memory pressure

### Deliverables
- ✅ Architecture Design Doc (review + sign-off)
- ✅ `data/scripts/klines_cache_manager.py` — Core module skeleton
- ✅ `data/schema.sql` — Database schema
- ✅ `.gitignore` additions for cache files
- ✅ Phase 1 checklist (Arch + Data sign-off)

---

## 🧪 Phase 2: Data Ingestion (26 FEV 10:00–16:00 UTC)

**Lead:** Data (#11)

### Ingestion Checklist

- [ ] **Kandle Fetch — 60 Symbols**
  - [ ] Symbol list validation (60 active pairs)
  - [ ] Parallel fetch (max 5 concurrent, respect rate limits)
  - [ ] Progress logging: "Symbol 15/60 complete — ETA 2h"
  - [ ] Failure recovery: resume from checkpoint on network error
  
- [ ] **Validation Layer** (Gate 1 criteria)
  - [ ] [ ] Gaps detection: `SELECT COUNT(*) WHERE timestamp_gap > 60s`
  - [ ] [ ] Duplicates check: `SELECT COUNT(*) HAVING count > 1`
  - [ ] [ ] Price validation: `WHERE price < 0.00001` → REJECT
  - [ ] [ ] Volume validation: `WHERE volume = 0` → FLAG (low-liq)
  - [ ] [ ] Timestamp ordering: `ORDER BY timestamp` verify

- [ ] **Cache Creation**
  - [ ] SQLite: `db/klines_cache.db` ~ 650KB
  - [ ] Parquet: per-symbol backup `data/backups/SYMBOL.parquet`
  - [ ] Manifest: `data/manifest.json` (metadata + checksums)

### Output Files
- ✅ `db/klines_cache.db` (✅ 60 symbols, 1Y, validated)
- ✅ `data/manifest.json` (metadata + record counts)
- ✅ `data/logs/ingestion_26FEV_TIMESTAMP.log` (detailed fetch log)
- ✅ Gate 1 validation report

**Success Condition:** Zero gaps, zero invalid prices, 360+ days per symbol

---

## ✅ Phase 3: Testing & Documentation (26 FEV 16:00–18:00 UTC)

**Lead:** Data (#11) + Audit (#8)

### Gate 1 Validation (Data lead)

| Componente | Critério | Verificação | ✅/❌ |
|-----------|----------|------------|------|
| Símbolos | 60 pares carregados | `SELECT COUNT(DISTINCT symbol) = 60` | |
| Integridade | Sem gaps | `klines_cache_manager.py validate-gaps` | |
| Duplicatas | Zero duplicatas | `klines_cache_manager.py validate-duplicate` | |
| Preços | Válidos (≥ 0.00001) | `klines_cache_manager.py validate-prices` | |
| Cache | Read < 100ms | `time klines_cache_manager.py query BTCUSDT` | |
| Dados | 1Y mínimo | `MAX(ts) - MIN(ts) ≥ 360 days` | |
| Tamanho BD | ~650 KB ±100 KB | `ls -lh db/klines_cache.db` | |

### Gate 2 Validation (Audit lead)

| Componente | Critério | Verificação | ✅/❌ |
|-----------|----------|------------|------|
| Testes | 5+ PASS | `pytest tests/data/test_klines_*.py -v` | |
| Cobertura | ≥80% | `pytest --cov=data --cov-report=html` | |
| Não-regressão | 70 testes Sprint 1 | `pytest tests/` | |
| Docstrings | 100% (PT) | Code review | |
| README | ≥300 palavras | `data/README.md` review | |
| Lint | pylint ≥ 8.0 | `pylint data/scripts/klines_cache_manager.py` | |

### Implementation

- [ ] **Test Suite**
  - [ ] `tests/data/test_klines_fetcher.py` (fetch logic)
  - [ ] `tests/data/test_klines_validator.py` (validation)
  - [ ] `tests/data/test_klines_cache.py` (caching)
  - [ ] `tests/data/test_klines_e2e.py` (end-to-end)
  - [ ] `tests/data/test_klines_performance.py` (latency)
  
- [ ] **Documentation**
  - [ ] `data/README.md` — Architecture + usage guide
  - [ ] `data/scripts/KLINES_CACHE_MANAGER.md` — CLI reference
  - [ ] Inline docstrings (PT) in all modules
  - [ ] Example: `data/examples/fetch_and_validate.py`
  
- [ ] **Git & Quality**
  - [ ] No hardcoded API keys (use config/settings.py)
  - [ ] No large binary files (.db in .gitignore)
  - [ ] All tests passing
  - [ ] Coverage report generated

### Output Files
- ✅ `tests/data/test_klines_*.py` (5 tests)
- ✅ `data/README.md`
- ✅ `coverage_report_data_26FEV.html`
- ✅ `test_results_phase3_data_26FEV.json`
- ✅ Audit sign-off checklist

---

## 🔗 Integration Points

**Ready for:**
- ✅ Issue #62 Backtesting Engine (uses klines_cache)
- ✅ TASK-005 PPO training (1Y data for 60 symbols)
- ✅ Live trading (daily sync via cron job)

**Dependencies:**
- ✅ Issue #65 QA (soft — independent paths)
- ✅ Binance API connectivity (Issue #55 ✅)
- ✅ Risk Gate protections (Issue #57 ✅)

---

## 🚀 Post-Launch (26 FEV 18:00+)

- [ ] Schedule daily sync cron job: `0 2 * * * /scripts/daily_candle_sync.py`
- [ ] Monitor: size, gap detection, validation errors
- [ ] Backup rotation: keep 3 versions of `klines_cache.db`
- [ ] Alert on validation failure → notify Ops team

---

## 📊 Success Metrics

| Métrica | Target | Verificação |
|---------|--------|------------|
| Símbolos Carregados | 60/60 = 100% | DATA manifest |
| Integridade | 0 gaps, 0 invalid | Validation log |
| Cache Latency | < 100ms P99 | Benchmark |
| Test Pass Rate | 5/5 = 100% | CI logs |
| Code Coverage | ≥ 80% | pytest --cov |
| Não-regressão | 70/70 Sprint 1 PASS | Full test suite |
| Documentation | 100% complete | README + docstrings |
| Go-Live Ready | All Gates ✅ | Audit sign-off |

---

## 🔗 Referências

- **Critérios de Aceite:** [CRITERIOS_DE_ACEITE_MVP.md#s2-0](CRITERIOS_DE_ACEITE_MVP.md#s2-0) Gates 1–2
- **Architecture Approved:** [ARCH_DESIGN_REVIEW_S2_0_CACHE.md](ARCH_DESIGN_REVIEW_S2_0_CACHE.md)
- **Data Strategy Guide:** [DATA_STRATEGY_START_HERE.md](DATA_STRATEGY_START_HERE.md)
- **Binance Integration:** [data/binance_client.py](../data/binance_client.py)
- **Risk Gate:** [docs/BINANCE_REAL_PROTECTIONS.md](BINANCE_REAL_PROTECTIONS.md)

---

**Squad Ready:** ✅ Data (#11) + Arch (#6) + Doc Advocate (#17)
**Kick-off:** 24 FEV ~15:00 UTC (pós Issue #65 Phase 1)
**Deadline:** 26 FEV 18:00 UTC (~60h wall-time)
**Status:** 📋 QUEUED & READY
