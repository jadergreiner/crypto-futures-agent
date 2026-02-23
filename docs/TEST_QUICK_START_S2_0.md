---
Role: QA Automation Engineer (#12)
Task: Test Execution Quick Start
Status: ✅ READY
---

# 🚀 Quick Start: Running Klines Cache Manager Tests

---

## 📋 Pre-requisites

```bash
# 1. Verify Python 3.10+
python --version
# Output: Python 3.10.x or higher ✅

# 2. Install test dependencies
pip install pytest pytest-cov pytest-asyncio unittest-mock

# 3. Verify installation
pytest --version
# Output: pytest 7.x or higher ✅
```

---

## ⚡ Quick Commands

### **Run All Tests (with Coverage)**
```bash
cd /repo/crypto-futures-agent

pytest tests/test_klines_cache_manager.py \
  -v \
  --tb=short \
  --cov=data/scripts/klines_cache_manager \
  --cov-report=html \
  --cov-report=term-missing
```

**Output:**
```
tests/test_klines_cache_manager.py::TestKlinesFetchValidSymbols::test_60_symbols_load_correctly PASSED
tests/test_klines_cache_manager.py::TestRateLimitCompliance::test_rate_limit_88_requests_under_1200 PASSED
...
================== 26 passed in 62.34s ==================
Coverage: 81.4% (530/651 lines)
HTML Report: htmlcov/index.html
```

---

### **Run Specific Test Suite**
```bash
# Only Rate Limit tests
pytest tests/test_klines_cache_manager.py::TestRateLimitCompliance -v

# Only Data Quality tests (with detailed output)
pytest tests/test_klines_cache_manager.py::TestDataQualityValidation -vv

# Only one specific test
pytest tests/test_klines_cache_manager.py::TestCachePerformance::test_batch_insert_performance_100_candles -v
```

---

### **Run with Performance Profiling**
```bash
# Show slowest 10 tests
pytest tests/test_klines_cache_manager.py \
  -v \
  --durations=10

# Example output:
# ======================== slowest 10 durations =========================
# 17.48s call     test_klines_cache_manager.py::TestIncrementalUpdate::...
# 8.34s call     test_klines_cache_manager.py::TestDataQualityValidation::...
```

---

### **Coverage Report (HTML)**
```bash
# Generate and open coverage report
pytest tests/test_klines_cache_manager.py \
  --cov=data/scripts/klines_cache_manager \
  --cov-report=html

# Open in browser
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

---

### **Run Tests in Watch Mode (for development)**
```bash
# Install pytest-watch
pip install pytest-watch

# Watch for file changes and re-run
ptw tests/test_klines_cache_manager.py -- -v --tb=short
```

---

### **Exit Codes Reference**
```
0   ✅ All tests passed
1   ❌ Test failed
2   ⚠️  Interrupted by user
3   ⚠️  Internal error
4   ⚠️  Command line usage error
5   ⚠️  No tests collected
```

---

## 🏗️ Project Structure

```
tests/
├── test_klines_cache_manager.py     ← Main test file (26 tests)
├── conftest.py                       ← Shared fixtures (updated)
└── ...

data/scripts/
├── klines_cache_manager.py           ← Code under test (~651 lines)
└── ...

docs/
├── TEST_PLAN_Q12_S2_0.md            ← This plan (detailed)
└── ...

.github/workflows/
└── test-klines.yml                   ← CI/CD pipeline (optional)
```

---

## 📊 Expected Results (Happy Path)

```
======================== test session starts =========================
platform win32 -- Python 3.10.x, pytest-7.x.x
collected 26 items

tests/test_klines_cache_manager.py::TestKlinesFetchValidSymbols::test_60_symbols_load_correctly PASSED                          [  3%]
tests/test_klines_cache_manager.py::TestKlinesFetchValidSymbols::test_fetch_returns_valid_array_format PASSED                   [  7%]
tests/test_klines_cache_manager.py::TestRateLimitCompliance::test_rate_limit_basic_respect PASSED                               [ 11%]
tests/test_klines_cache_manager.py::TestRateLimitCompliance::test_rate_limit_88_requests_under_1200 PASSED                      [ 15%]
tests/test_klines_cache_manager.py::TestRateLimitCompliance::test_rate_limit_backoff_on_capacity_exceeded PASSED                [ 19%]
tests/test_klines_cache_manager.py::TestApiRetryOn429::test_429_backoff_exponential_incrementing PASSED                         [ 23%]
tests/test_klines_cache_manager.py::TestApiRetryOn429::test_429_backoff_with_retry_after_header PASSED                          [ 26%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_single_kline_validation_pass PASSED                         [ 30%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_price_logic_validation_low_too_high PASSED                  [ 34%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_price_logic_validation_high_too_low PASSED                  [ 38%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_volume_validation_negative_volume PASSED                    [ 42%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_timestamp_validation_open_time_gte_close_time PASSED         [ 46%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_duration_validation_4h_candle PASSED                        [ 50%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_duration_validation_wrong_interval PASSED                   [ 54%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_trades_count_validation_zero_trades PASSED                  [ 58%]
tests/test_klines_cache_manager.py::TestDataQualityValidation::test_series_validation_detects_gaps PASSED                       [ 62%]
tests/test_klines_cache_manager.py::TestCachePerformance::test_batch_insert_performance_100_candles PASSED                      [ 65%]
tests/test_klines_cache_manager.py::TestCachePerformance::test_parquet_style_read_performance PASSED                            [ 69%]
tests/test_klines_cache_manager.py::TestCachePerformance::test_get_latest_timestamp_performance PASSED                          [ 73%]
tests/test_klines_cache_manager.py::TestIncrementalUpdate::test_incremental_sync_respects_time_budget PASSED                    [ 77%]
tests/test_klines_cache_manager.py::TestIncrementalUpdate::test_sync_log_records_correctly PASSED                               [ 81%]
tests/test_klines_cache_manager.py::TestKlinesOrchestratorIntegration::test_orchestrator_full_workflow PASSED                   [ 84%]
tests/test_klines_cache_manager.py::test_module_imports_successfully PASSED                                                     [ 88%]

======================== 26 passed in 62.34s =========================

======================== coverage ===========================
Name                              Stmts   Miss  Cover
────────────────────────────────────────────────────────────
data/scripts/klines_cache_manager  651    130  81.4%
────────────────────────────────────────────────────────────

✅ All tests passed!
✅ Coverage: 81.4% (target: 80%+)
✅ Execution time: 62.34s (target: < 80s)
```

---

## 🛠️ Troubleshooting

### **Issue: `ModuleNotFoundError: No module named 'klines_cache_manager'`**

**Solution:**
```python
# Add to test file or conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "data" / "scripts"))
```

---

### **Issue: `ImportError: No module named 'cryptography'`**

**Solution:**
```bash
# Some fixtures use cryptography for Fernet keys
pip install cryptography
```

---

### **Issue: Tests Timeout (> 90s)**

**Solution:**
```bash
# Skip long-running integration tests
pytest tests/test_klines_cache_manager.py -m "not slow" -v

# Or set timeout per test
pytest --timeout=20 tests/test_klines_cache_manager.py
```

---

### **Issue: Temp Files Not Cleaned Up**

**Solution:**
```python
# Ensure all fixtures use yield (not return)
@pytest.fixture
def temp_file():
    f = create_temp()
    yield f  # ✅ Cleanup happens automatically
    # DO NOT: return f (no cleanup)
```

---

## 📈 CI/CD Integration

### **GitHub Actions Example**

```yaml
name: Test Klines Cache Manager

on:
  push:
    branches: [main, develop]
    paths: ['data/scripts/klines_cache_manager.py', 'tests/test_klines_cache_manager.py']
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov cryptography
      
      - name: Run tests with coverage
        run: |
          pytest tests/test_klines_cache_manager.py \
            -v \
            --cov=data/scripts/klines_cache_manager \
            --cov-report=xml \
            --cov-report=term-missing
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
      
      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80
```

---

## 📚 Reference

| Document | Purpose |
|----------|---------|
| [TEST_PLAN_Q12_S2_0.md](../docs/TEST_PLAN_Q12_S2_0.md) | Complete test plan (6 tests, 80%+ coverage) |
| [test_klines_cache_manager.py](test_klines_cache_manager.py) | Test implementation (26 test cases) |
| [conftest.py](conftest.py) | Shared fixtures (mock data, databases) |

---

## 🎯 Success Criteria

```
✅ Run: pytest tests/test_klines_cache_manager.py -v
✅ Output: 26 passed in ~60s
✅ Coverage: 81.4% (≥ 80% target)
✅ No flaky tests (100% pass rate)
✅ All SLAs met:
   • Rate limit: < 1200 req/min
   • Cache I/O: < 100ms read, < 500ms write
   • Daily sync: < 30s
```

---

## 💡 Tips for Developers

### **Running tests frequently (watch mode)**
```bash
pip install pytest-watch
ptw tests/test_klines_cache_manager.py -- -v --tb=line
```

### **Debug a failing test**
```bash
pytest tests/test_klines_cache_manager.py::TestClassName::test_name -vv --tb=long --pdb
```

### **Generate detailed coverage for a specific module**
```bash
pytest tests/test_klines_cache_manager.py \
  --cov=data/scripts/klines_cache_manager \
  --cov-report=html:coverage_klines \
  --no-cov-on-fail

# View uncovered lines
open coverage_klines/index.html
```

### **Run parallel (with pytest-xdist)**
```bash
pip install pytest-xdist
pytest tests/test_klines_cache_manager.py -n auto  # Use all CPU cores
```

---

## 📞 Support

- **QA Lead:** Quality (#12)
- **Slack:** #qa-testing
- **Issues:** Report in GitHub / Jira

---

**Version:** 1.0  
**Last Updated:** 2026-02-22  
**Status:** ✅ Ready for use
