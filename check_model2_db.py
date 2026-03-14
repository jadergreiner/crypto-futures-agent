#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()

# Listar todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print('=== TABELAS NO BANCO MODELO2 ===')
for table in tables:
    table_name = table[0]
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = cursor.fetchone()[0]
    print(f'{table_name}: {count} registros')

print('')
print('=== DETALHES DAS TABELAS ===')

# Mostrar detalhes de algumas tabelas importantes
for table_pattern in ['episode', 'training', 'signal', 'candidate']:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%{table_pattern}%'")
    tables = cursor.fetchall()
    if tables:
        for table in tables:
            table_name = table[0]
            print(f'\nTabela: {table_name}')
            cursor.execute(f'PRAGMA table_info({table_name})')
            cols = cursor.fetchall()
            for col in cols:
                print(f'  - {col[1]} ({col[2]})')
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'  Total: {count} registros')

conn.close()
