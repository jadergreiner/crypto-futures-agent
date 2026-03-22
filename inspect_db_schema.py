#!/usr/bin/env python3
"""Investigar estrutura de episódios e onde rewards são armazenados."""

import sqlite3
from pathlib import Path

DB_PATH = Path("db/modelo2.db")

def inspect_training_episodes():
    """Inspecionar schema da tabela training_episodes."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    print("\n" + "=" * 70)
    print("SCHEMA: training_episodes")
    print("=" * 70)
    
    c.execute("PRAGMA table_info(training_episodes);")
    columns = c.fetchall()
    
    for col_id, col_name, col_type, not_null, default_val, pk in columns:
        nullable = "NOT NULL" if not_null else "NULL   "
        pk_marker = "PK" if pk else "  "
        print(f"  {pk_marker} | {col_name:20s} | {col_type:15s} | {nullable}")
    
    # Sample row
    print("\n" + "=" * 70)
    print("SAMPLE: Primeiros 2 episódios")
    print("=" * 70)
    
    c.execute("""
        SELECT * FROM training_episodes 
        ORDER BY id DESC 
        LIMIT 2
    """)
    
    col_names = [desc[0] for desc in c.description]
    rows = c.fetchall()
    
    for row in rows:
        print(f"\nEpisódio ID: {row[0]}")
        for col_name, val in zip(col_names[1:], row[1:]):
            if val is None:
                print(f"  {col_name:20s} = None")
            elif len(str(val)) > 60:
                print(f"  {col_name:20s} = {str(val)[:60]}...")
            else:
                print(f"  {col_name:20s} = {val}")
    
    # Verificar signal_executions
    print("\n" + "=" * 70)
    print("SCHEMA: signal_executions")
    print("=" * 70)
    
    c.execute("PRAGMA table_info(signal_executions);")
    columns = c.fetchall()
    
    for col_id, col_name, col_type, not_null, default_val, pk in columns:
        nullable = "NOT NULL" if not_null else "NULL   "
        pk_marker = "PK" if pk else "  "
        print(f"  {pk_marker} | {col_name:20s} | {col_type:15s} | {nullable}")
    
    # Sample executions
    print("\n" + "=" * 70)
    print("SAMPLE: signal_executions")
    print("=" * 70)
    
    c.execute("""
        SELECT * FROM signal_executions 
        ORDER BY id DESC 
        LIMIT 3
    """)
    
    col_names = [desc[0] for desc in c.description]
    rows = c.fetchall()
    
    for row in rows:
        print(f"\nExecution ID: {row[0]}")
        for col_name, val in zip(col_names[1:], row[1:]):
            if val is None:
                print(f"  {col_name:20s} = None")
            elif len(str(val)) > 60:
                print(f"  {col_name:20s} = {str(val)[:60]}...")
            else:
                print(f"  {col_name:20s} = {val}")
    
    # Verificar model_decisions
    print("\n" + "=" * 70)
    print("SCHEMA: model_decisions")
    print("=" * 70)
    
    c.execute("PRAGMA table_info(model_decisions);")
    columns = c.fetchall()
    
    for col_id, col_name, col_type, not_null, default_val, pk in columns:
        nullable = "NOT NULL" if not_null else "NULL   "
        pk_marker = "PK" if pk else "  "
        print(f"  {pk_marker} | {col_name:20s} | {col_type:15s} | {nullable}")
    
    conn.close()

if __name__ == "__main__":
    inspect_training_episodes()
