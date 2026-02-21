#!/usr/bin/env python
"""
Script para verificar disponibilidade de dados de OGNUSDT e 1000PEPEUSDT.
"""
import sqlite3
import sys
from pathlib import Path

def check_data_availability():
    """Verifica dados disponíveis no banco de dados."""
    db_path = Path('crypto_agent.db')

    if not db_path.exists():
        print(f"[ERROR] Banco de dados não encontrado: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Verificar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"[INFO] Tabelas encontradas: {tables}")

    # Verificar dados para cada símbolo
    symbols = ['OGNUSDT', '1000PEPEUSDT']

    # Mapeamento de timeframe para nome de tabela
    tf_table_map = {
        '1h': 'ohlcv_h1',
        '4h': 'ohlcv_h4',
        'd1': 'ohlcv_d1'
    }

    results = {}
    for symbol in symbols:
        results[symbol] = {}
        for tf, table_name in [('1h', 'ohlcv_h1'), ('4h', 'ohlcv_h4')]:
            try:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE symbol='{symbol}'"
                cursor.execute(query)
                count = cursor.fetchone()[0]
                results[symbol][tf] = count
                print(f"[INFO] {symbol} {tf}: {count} candles")

                # Se temos dados, verifica primeira e última data
                if count > 0:
                    query_dates = f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name} WHERE symbol='{symbol}'"
                    cursor.execute(query_dates)
                    min_ts, max_ts = cursor.fetchone()
                    print(f"       Período: {min_ts} → {max_ts}")

            except Exception as e:
                print(f"[ERROR] {symbol} {tf}: {str(e)}")
                results[symbol][tf] = 0

    conn.close()

    # Verificar parquets
    print("\n[INFO] Verificando Parquet cache:")
    cache_dir = Path('backtest/cache')
    if cache_dir.exists():
        for pq_file in cache_dir.glob('*.parquet'):
            print(f"  - {pq_file.name}")

    return results

if __name__ == '__main__':
    results = check_data_availability()

    # Resumo
    print("\n" + "="*60)
    print("RESUMO DE DISPONIBILIDADE DE DADOS")
    print("="*60)

    ognusdt_h4 = results.get('OGNUSDT', {}).get('4h', 0)
    pepeusdt_h4 = results.get('1000PEPEUSDT', {}).get('4h', 0)

    print(f"OGNUSDT H4:      {ognusdt_h4}  candles", "✅ OK" if ognusdt_h4 >= 700 else "❌ INSUFICIENTE")
    print(f"1000PEPEUSDT H4: {pepeusdt_h4} candles", "✅ OK" if pepeusdt_h4 >= 700 else "❌ INSUFICIENTE")

    all_ok = ognusdt_h4 >= 700 and pepeusdt_h4 >= 700
    print("\n" + ("✅ Todos dados disponíveis!" if all_ok else "❌ Faltam dados críticos"))

    sys.exit(0 if all_ok else 1)
