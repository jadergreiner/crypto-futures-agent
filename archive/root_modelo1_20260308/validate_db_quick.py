#!/usr/bin/env python3
"""
Quick database validation script — ESP-ML Task
Check both databases for OHLCV data
"""

import sqlite3
import sys

db_paths = ['db/crypto_futures.db', 'db/crypto_agent.db']

for db_path in db_paths:
    print(f'\n{"="*60}')
    print(f'Checking: {db_path}')
    print(f'{"="*60}')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        print(f'Tables found: {len(tables)}')
        for table in tables[:15]:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f'  - {table:30s}: {count:8d} rows')

        conn.close()

    except Exception as e:
        print(f'Error: {e}')
        continue

print("\n" + "="*60)
print("VALIDATION COMPLETE")
print("="*60)
