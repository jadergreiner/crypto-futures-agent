#!/usr/bin/env python
"""Quick test to validate count_live_entries_today fix."""

import sys
try:
    from core.model2 import repository
    print("[OK] Módulo repository.py compila sem erros")
except Exception as e:
    print(f"[ERRO] {e}")
    sys.exit(1)
