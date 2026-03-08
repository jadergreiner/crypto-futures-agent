import pandas as pd
from pathlib import Path

parquet_path = Path('backtest/cache/OGNUSDT_h4_2026.parquet')
cache_dir = Path('backtest/cache')

if parquet_path.exists():
    df = pd.read_parquet(parquet_path)
    print(f'✅ OGNUSDT loaded: {len(df)} candles')
    print(f'   Columns: {list(df.columns)}')
    if len(df) > 0:
        print(f'   Date range: {df.index[0]} to {df.index[-1]}')
else:
    print('⚠️ OGNUSDT Parquet cache not found')
    if cache_dir.exists():
        print('   Available cache files:')
        parquet_files = list(cache_dir.glob('*.parquet'))
        if parquet_files:
            for f in parquet_files:
                print(f'     - {f.name}')
        else:
            print('     (no .parquet files found)')
