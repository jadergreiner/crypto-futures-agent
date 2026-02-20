#!/usr/bin/env python3
"""Inspecionar stata do banco de dados."""
import sqlite3
import sys

db_path = 'db/crypto_agent.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print('📊 ESTRUTURA DO BANCO DE DADOS:')
    print('=' * 50)
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]
        
        # Pegar algumas colunas
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns[:3]]  # Primeiras 3 colunas
        
        print(f'\n✅ {table_name}')
        print(f'   Registros: {count:,}')
        print(f'   Colunas: {", ".join(col_names)} ...')
    
    conn.close()
    print('\n✅ Banco acessível e com dados!')
    sys.exit(0)
    
except Exception as e:
    print(f'❌ Erro: {e}')
    sys.exit(1)
