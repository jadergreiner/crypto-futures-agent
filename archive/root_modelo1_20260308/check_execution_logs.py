#!/usr/bin/env python3
"""
Verificar logs de execução para descobrir quando as posições foram fechadas
"""

import sqlite3
from datetime import datetime

DB_PATH = "db/crypto_agent.db"

print("=" * 120)
print("🔍 INVESTIGAÇÃO: Histórico de Fechamentos de Posições")
print("=" * 120)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verificar execution_log
    print("-" * 120)
    print("EXECUTION_LOG — Últimas 20 execuções")
    print("-" * 120)

    try:
        cursor.execute("SELECT * FROM execution_log ORDER BY timestamp DESC LIMIT 20")
        exec_logs = cursor.fetchall()

        if exec_logs:
            # Obter nomes das colunas
            col_names = [description[0] for description in cursor.description]
            print(f"Colunas: {col_names}\n")
            print(f"{str(exec_logs[:3])}\n")
        else:
            print("❌ Nenhum registro encontrado em execution_log\n")
    except Exception as e:
        print(f"⚠️  Erro ao ler execution_log: {e}\n")

    # Verificar trade_log
    print("-" * 120)
    print("TRADE_LOG — Últimas 20 operações fechadas")
    print("-" * 120)

    try:
        cursor.execute("SELECT * FROM trade_log ORDER BY timestamp_saida DESC LIMIT 20")
        trade_logs = cursor.fetchall()

        if trade_logs:
            col_names = [description[0] for description in cursor.description]
            print(f"Colunas: {col_names}\n")
            print(f"{str(trade_logs[:3])}\n")
        else:
            print("❌ Nenhum trade registrado\n")
    except Exception as e:
        print(f"⚠️  Erro ao ler trade_log: {e}\n")

    # Verificar position_snapshots (últimos snapshots)
    print("\n" + "-" * 120)
    print("POSITION_SNAPSHOTS — Últimas 10 posições capturadas")
    print("-" * 120)

    try:
        cursor.execute("SELECT * FROM position_snapshots ORDER BY timestamp DESC LIMIT 10")
        snapshots = cursor.fetchall()

        if snapshots:
            col_names = [description[0] for description in cursor.description]
            print(f"Colunas: {col_names}\n")
            print(f"{str(snapshots[:3])}\n")
        else:
            print("❌ Nenhum snapshot encontrado\n")
    except Exception as e:
        print(f"⚠️  Erro ao ler position_snapshots: {e}\n")

    # Estatísticas
    print("\n" + "=" * 120)
    print("📊 ESTATÍSTICAS")
    print("=" * 120)

    try:
        cursor.execute("SELECT COUNT(*) FROM execution_log")
        exec_count = cursor.fetchone()[0]
    except:
        exec_count = 0

    try:
        cursor.execute("SELECT COUNT(*) FROM trade_log")
        trade_count = cursor.fetchone()[0]
    except:
        trade_count = 0

    try:
        cursor.execute("SELECT COUNT(*) FROM position_snapshots")
        snapshot_count = cursor.fetchone()[0]
    except:
        snapshot_count = 0

    print(f"""
Total de registros em execution_log: {exec_count}
Total de trades fechados (trade_log): {trade_count}
Total de snapshots de posições: {snapshot_count}

ÚLTIMA EXECUÇÃO: Verifique os dados acima
    """)

    conn.close()

except sqlite3.Error as e:
    print(f"❌ Erro ao acessar banco de dados: {e}")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 120)
