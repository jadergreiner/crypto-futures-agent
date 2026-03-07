#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapeamento de Uso de Bancos - Identificar qual módulo usa qual banco

Procura no código por referências a db_path, database.py, etc.

Uso:
    python scripts/map_database_usage.py
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Padrões de busca
patterns = {
    'crypto_agent.db': r'crypto_agent\.db',
    'crypto_futures.db': r'crypto_futures\.db',
    'DatabaseManager': r'DatabaseManager\(',
    'get_db_connection': r'get_db_connection\(',
}

def scan_file(filepath, patterns):
    """Escaneia arquivo e retorna matches."""
    matches = defaultdict(int)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern_name, pattern in patterns.items():
                matches[pattern_name] = len(re.findall(pattern, content))
    except:
        pass
    return matches

def main():
    print("\n" + "="*80)
    print("MAPEAMENTO DE USO DE BANCO DE DADOS")
    print("="*80)

    root_dir = Path('.')
    python_files = list(root_dir.glob('**/*.py'))

    results_by_db = defaultdict(list)

    for py_file in python_files:
        # Skip venv e __pycache__
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        matches = scan_file(str(py_file), patterns)

        if matches['crypto_agent.db'] > 0:
            results_by_db['crypto_agent.db'].append({
                'file': str(py_file),
                'count': matches['crypto_agent.db']
            })

        if matches['crypto_futures.db'] > 0:
            results_by_db['crypto_futures.db'].append({
                'file': str(py_file),
                'count': matches['crypto_futures.db']
            })

    # Imprimir resultados
    print("\n📊 REFERÊNCIAS A crypto_agent.db:")
    print("-"*80)
    if results_by_db['crypto_agent.db']:
        for item in results_by_db['crypto_agent.db']:
            print(f"  {item['count']:>3}x  {item['file']}")
    else:
        print("  (Nenhuma referência encontrada)")

    print("\n📊 REFERÊNCIAS A crypto_futures.db:")
    print("-"*80)
    if results_by_db['crypto_futures.db']:
        for item in results_by_db['crypto_futures.db']:
            print(f"  {item['count']:>3}x  {item['file']}")
    else:
        print("  (Nenhuma referência encontrada)")

    print("\n" + "="*80)
    print("HIPÓTESIS:")
    print("="*80)

    agent_count = sum(item['count'] for item in results_by_db['crypto_agent.db'])
    futures_count = sum(item['count'] for item in results_by_db['crypto_futures.db'])

    if agent_count > futures_count:
        print(f"✓ crypto_agent.db é usado mais ({agent_count}x) → Provavelmente é PRINCIPAL")
    elif futures_count > agent_count:
        print(f"✓ crypto_futures.db é usado mais ({futures_count}x) → Provavelmente é PRINCIPAL")
    else:
        print("? Uso similar - necessário análise manual")

if __name__ == "__main__":
    main()
