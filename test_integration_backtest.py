"""
Teste de integracao F-12b ParquetCache com BacktestEnvironment.
"""

from backtest.data_cache import ParquetCache
from backtest.backtest_environment import BacktestEnvironment
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 70)
print("TESTE INTEGRACAO F-12b ParquetCache + BacktestEnvironment")
print("=" * 70)

# PASSO 1: Carregar dados via ParquetCache
print("\n[1] Carregando dados via ParquetCache...")
pc = ParquetCache(db_path='db/crypto_agent.db', cache_dir='backtest/cache')

# Obter simbolo disponivel
import sqlite3
conn = sqlite3.connect('db/crypto_agent.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT symbol FROM ohlcv_h4 LIMIT 1")
symbol = cursor.fetchone()[0]
conn.close()

print(f"   Simbolo: {symbol}")

# Carregar dados
h1_df = pc.load_ohlcv_for_symbol(symbol, 'h1')
h4_df = pc.load_ohlcv_for_symbol(symbol, 'h4')
d1_df = pc.load_ohlcv_for_symbol(symbol, 'd1')

print(f"   [OK] H1: {len(h1_df)} candles")
print(f"   [OK] H4: {len(h4_df)} candles")
print(f"   [OK] D1: {len(d1_df)} candles")

# PASSO 2: Preparar dicionario de dados para BacktestEnvironment
print("\n[2] Preparando dicionario de dados para BacktestEnvironment...")

# Criar dados dummy para features que nao temos
dummy_sentiment = pd.DataFrame({
    'timestamp': h4_df['timestamp'],
    'sentiment_score': [0.5] * len(h4_df)
})

dummy_macro = pd.DataFrame({
    'timestamp': h4_df['timestamp'],
    'vix_close': [20.0] * len(h4_df)
})

dummy_smc = pd.DataFrame({
    'timestamp': h4_df['timestamp'],
    'resistance': [0.0] * len(h4_df),
    'support': [0.0] * len(h4_df)
})

data_dict = {
    'h1': h1_df,
    'h4': h4_df,
    'd1': d1_df if not d1_df.empty else pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']),
    'symbol': symbol,
    'sentiment': dummy_sentiment,
    'macro': dummy_macro,
    'smc': dummy_smc
}

print(f"   [OK] Dicionario preparado com {len(data_dict)} chaves")

# PASSO 3: Inicializar BacktestEnvironment
print("\n[3] Inicializando BacktestEnvironment...")

try:
    env = BacktestEnvironment(
        data=data_dict,
        initial_capital=10000,
        episode_length=min(100, len(h4_df) - 1),
        deterministic=True,
        seed=42
    )
    print(f"   [OK] BacktestEnvironment inicializado")
    print(f"      Episode length: {env.episode_length}")
    print(f"      Action space: {env.action_space}")
    print(f"      Observation space: {env.observation_space}")

    # PASSO 4: Reset e primeiro step
    print("\n[4] Testando reset() e primeiro step()...")
    obs, info = env.reset()
    print(f"   [OK] Reset bem-sucedido")
    print(f"      Observation shape: {obs.shape}")
    print(f"      Info keys: {list(info.keys())}")

    # Executar um step
    action = 0  # HOLD
    obs, reward, terminated, truncated, info = env.step(action)
    print(f"   [OK] Step bem-sucedido")
    print(f"      Reward: {reward:.4f}")
    print(f"      Terminated: {terminated}, Truncated: {truncated}")

    print("\n" + "=" * 70)
    print("OK - INTEGRACAO PRONTA PARA FULL BACKTEST RUN")
    print("=" * 70)
    print("RESULT: SUCCESS")

except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()
    print("RESULT: FAILED")
