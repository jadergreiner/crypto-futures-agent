from backtest.data_cache import ParquetCache
import logging

logging.basicConfig(level=logging.INFO)

pc = ParquetCache(db_path='db/crypto_agent.db', cache_dir='backtest/cache')

# Tenta carregar BTCUSDT ou o primeiro símbolo disponível
print("Testing ParquetCache.load_ohlcv_for_symbol()...")

# Obter símbolos disponíveis do banco de dados
import sqlite3
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT symbol FROM ohlcv_h4 LIMIT 5")
symbols = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"Símbolos encontrados: {symbols}")

if symbols:
    symbol = symbols[0]
    print(f"\nTestando carregamento de {symbol}...")

    df = pc.load_ohlcv_for_symbol(symbol, timeframe='h4')
    print(f"✅ Carregamento bem-sucedido: {len(df)} candles")
    print(f"   Colunas: {list(df.columns)}")

    # Validar continuidade
    is_valid, error = pc.validate_candle_continuity(symbol, 'h4')
    if is_valid:
        print(f"✅ Continuidade validada")
    else:
        print(f"⚠️ Erro de continuidade: {error}")

    # Testar get_cached_data_as_arrays
    print(f"\nTestando get_cached_data_as_arrays()...")
    arrays = pc.get_cached_data_as_arrays(symbol)
    print(f"✅ Arrays carregados:")
    for tf, arr in arrays.items():
        print(f"   {tf}: {arr.shape}")
else:
    print("❌ Nenhum símbolo encontrado no banco de dados")
