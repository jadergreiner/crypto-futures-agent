#!/usr/bin/env python3
"""Final integration test before training launch."""

import json
import sys
from datetime import datetime
from pathlib import Path

print("\n" + "="*70)
print("TESTE FINAL DE INTEGRACAO - PRÉ-LAUNCH VALIDATION")
print("="*70 + "\n")

results = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "tests_executed": 0,
    "tests_passed": 0,
    "tests_failed": 0,
    "details": []
}

# Test 1: Can import all critical modules
print("[1/5] Testando importacoes criticas...")
try:
    from config.ppo_config import get_ppo_config
    from backtest.backtest_environment import BacktestEnvironment
    from backtest.data_cache import ParquetCache
    from config.symbols import ALL_SYMBOLS
    results["tests_passed"] += 1
    results["details"].append("PASS: All critical imports working")
    print("  [OK] All imports OK")
except Exception as e:
    results["tests_failed"] += 1
    results["details"].append(f"FAIL: Import error: {e}")
    print(f"  [ERROR] Import error: {e}")
results["tests_executed"] += 1

# Test 2: Validate config values
print("[2/5] Validando valores de configuracao...")
try:
    config = get_ppo_config("phase4")
    assert config.learning_rate == 3e-4
    assert config.batch_size == 64
    assert config.total_timesteps == 500000
    results["tests_passed"] += 1
    results["details"].append("PASS: Config values correct")
    print("  [OK] Config values correct")
except Exception as e:
    results["tests_failed"] += 1
    results["details"].append(f"FAIL: Config validation: {e}")
    print(f"  [ERROR] Config error: {e}")
results["tests_executed"] += 1

# Test 3: Verify data files
print("[3/5] Verificando arquivos de dados...")
try:
    data_files = [
        "backtest/cache/OGNUSDT_4h.parquet",
        "backtest/cache/1000PEPEUSDT_4h.parquet",
        "data/training_datasets/dataset_info.json",
        "db/crypto_agent.db"
    ]
    for f in data_files:
        assert Path(f).exists(), f"Missing: {f}"
    results["tests_passed"] += 1
    results["details"].append("PASS: All data files present")
    print("  [OK] All data files present")
except Exception as e:
    results["tests_failed"] += 1
    results["details"].append(f"FAIL: Data files: {e}")
    print(f"  [ERROR] Data files error: {e}")
results["tests_executed"] += 1

# Test 4: Verify directory structure
print("[4/5] Verificando estrutura de diretorios...")
try:
    dirs = [
        "checkpoints/ppo_training",
        "logs/ppo_training",
        "logs/ppo_training/daily_summaries",
        "models/trained",
        "backtest/cache"
    ]
    for d in dirs:
        assert Path(d).exists(), f"Missing: {d}"
    results["tests_passed"] += 1
    results["details"].append("PASS: Directory structure OK")
    print("  [OK] Directory structure OK")
except Exception as e:
    results["tests_failed"] += 1
    results["details"].append(f"FAIL: Directory structure: {e}")
    print(f"  [ERROR] Directory error: {e}")
results["tests_executed"] += 1

# Test 5: Dry-run script test
print("[5/5] Testando dry-run do script de training...")
try:
    import subprocess
    result = subprocess.run(
        ["python", "scripts/start_ppo_training.py", "--dry-run"],
        capture_output=True,
        timeout=30,
        text=True
    )
    if result.returncode == 0:
        results["tests_passed"] += 1
        results["details"].append("PASS: Dry-run successful")
        print("  [OK] Dry-run successful")
    else:
        results["tests_failed"] += 1
        results["details"].append(f"FAIL: Dry-run failed with code {result.returncode}")
        print(f"  [ERROR] Dry-run error (code {result.returncode})")
except Exception as e:
    results["tests_failed"] += 1
    results["details"].append(f"FAIL: Dry-run execution: {e}")
    print(f"  [ERROR] Dry-run execution error: {e}")
results["tests_executed"] += 1

# Summary
print("\n" + "="*70)
print(f"RESULTADO: {results['tests_passed']}/{results['tests_executed']} testes passou")
print("="*70 + "\n")

if results["tests_failed"] == 0:
    print("[OK] SISTEMA 100% READY PARA TRAINING LAUNCH EM 23 FEV 14:00 UTC\n")
    exit_code = 0
else:
    print(f"[ERROR] {results['tests_failed']} teste(s) falharam\n")
    for detail in results["details"]:
        print(f"   - {detail}")
    exit_code = 1

# Save results
with open("FINAL_INTEGRATION_TEST.json", "w") as f:
    json.dump(results, f, indent=2)
    print(f"Resultados salvos em: FINAL_INTEGRATION_TEST.json\n")

sys.exit(exit_code)
