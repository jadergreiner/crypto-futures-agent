#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/crypto_futures.db')
cursor = conn.cursor()

# Ver todas as tabelas
print('=== TABELAS ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f'  {table[0]}')

# Ver schema de trade_log se existir
print('\n=== SCHEMA trade_log ===')
try:
    cursor.execute("PRAGMA table_info(trade_log)")
    columns = cursor.fetchall()
    if columns:
        for col in columns:
            print(f'  {col[1]:25} {col[2]}')
    else:
        print('  Tabela não encontrada ou vazia')
except Exception as e:
    print(f'  Erro: {e}')

# Ver últimos registros
print('\n=== ÚLTIMOS REGISTROS trade_log ===')
try:
    cursor.execute('SELECT * FROM trade_log ORDER BY rowid DESC LIMIT 5')
    rows = cursor.fetchall()
    if rows:
        # Get column names
        cursor.execute("PRAGMA table_info(trade_log)")
        cols = [col[1] for col in cursor.fetchall()]
        for row in rows:
            print(f'  {dict(zip(cols, row))}')
    else:
        print('  Nenhum registro')
except Exception as e:
    print(f'  Erro: {e}')

conn.close()
