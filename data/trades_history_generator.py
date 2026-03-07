"""
Gerador de histórico de trades Sprint 1 para treinamento PPO.

Este script cria um arquivo JSON com 70 trades históricos baseados em
padrões realistas de mercado crypto para uso no treinamento do agente PPO.

Estrutura esperada de cada trade:
{
    'symbol': str,
    'entry_price': float,
    'exit_price': float,
    'qty': float,
    'direction': 'LONG' | 'SHORT',
    'entry_time': str (ISO 8601),
    'exit_time': str (ISO 8601),
    'pnl': float,
    'reward': float,
}
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_sprint1_trades(num_trades=500, filepath="data/trades_history.json"):
    """
    Gera histórico de 500+ trades Sprint 1 com características realistas e diversificadas.

    Args:
        num_trades: Número de trades a gerar (padrão: 500)
        filepath: Caminho para salvar o arquivo JSON
    """
    trades = []
    # 20 símbolos para melhor diversidade (vs 5 original)
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
        'DOGEUSDT', 'SOLUSDT', 'LTCUSDT', 'LINKUSDT', 'MATICUSDT',
        'AVAXUSDT', 'UNIUSDT', 'ATOMUSDT', 'XLMUSDT', 'FILUSDT',
        'CHZUSDT', 'ICPUSDT', 'VECUSDT', 'WOOUSDT', 'INJUSDT',
    ]

    # Simulação: 500 trades ao longo de 60 dias (7x mais dados)
    start_date = datetime(2026, 1, 1, 0, 0, 0)

    np.random.seed(42)  # Reproduzibilidade

    for i in range(num_trades):
        symbol = symbols[i % len(symbols)]

        # Tempo: distribuído mais densamente ao longo de 60 dias
        days_offset = (i // len(symbols)) * 0.5  # ~45 days spread for 500 trades
        hours_offset = (i % len(symbols)) * 3  # Distribuído entre símbolos
        trade_date = start_date + timedelta(days=days_offset, hours=hours_offset)

        # Duração aleatória: 30min a 8h (vs 2h fixo original)
        duration_hours = np.random.choice([0.5, 1.0, 2.0, 4.0, 8.0], p=[0.15, 0.25, 0.35, 0.15, 0.1])
        entry_time = trade_date.isoformat() + 'Z'
        exit_time = (trade_date + timedelta(hours=duration_hours)).isoformat() + 'Z'

        # Preço de entrada: simulação realista por símbolo
        symbol_prices = {
            'BTCUSDT': 42000, 'ETHUSDT': 2500, 'BNBUSDT': 600, 'XRPUSDT': 2.5,
            'ADAUSDT': 0.95, 'DOGEUSDT': 0.28, 'SOLUSDT': 140, 'LTCUSDT': 180,
            'LINKUSDT': 28, 'MATICUSDT': 0.75, 'AVAXUSDT': 38, 'UNIUSDT': 24,
            'ATOMUSDT': 7.5, 'XLMUSDT': 0.12, 'FILUSDT': 8.2, 'CHZUSDT': 0.32,
            'ICPUSDT': 12, 'VECUSDT': 0.065, 'WOOUSDT': 0.28, 'INJUSDT': 42,
        }
        base_price = symbol_prices.get(symbol, 1.0)

        # Entrada com variação maior (2-5% vs 2% original)
        entry_price = base_price * (1 + np.random.normal(0, 0.03))

        # Saída: distribuição mais realista com 50% win rate balanceada
        # 50% ganhos: +0.5% a +3.0%, 50% perdas: -3.0% a -0.5%
        is_win = np.random.random() < 0.5  # 50% win rate (vs 40% original)
        if is_win:
            pnl_pct = np.random.uniform(0.005, 0.03)  # +0.5% a +3% ganhos
            direction = 'LONG' if np.random.random() > 0.5 else 'SHORT'
        else:
            pnl_pct = np.random.uniform(-0.03, -0.005)  # -0.5% a -3% perdas
            direction = 'SHORT' if np.random.random() > 0.5 else 'LONG'

        # Aplicar direção
        if direction == 'SHORT':
            pnl_pct = -pnl_pct  # Inverte para short

        exit_price = entry_price * (1 + pnl_pct)

        # Quantidade: varia de 0.5 a 2.0 contratos
        qty = np.random.uniform(0.5, 2.0)
        pnl = (exit_price - entry_price) * qty

        # Reward normalizado (PnL / entrada)
        reward = pnl / entry_price

        trade = {
            'id': i + 1,
            'symbol': symbol,
            'entry_price': round(entry_price, 8),
            'exit_price': round(exit_price, 8),
            'qty': round(qty, 2),
            'direction': direction,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': round(pnl, 8),
            'reward': round(reward, 6),
            'duration_hours': round(duration_hours, 2),
        }

        trades.append(trade)

    # Salvar JSON
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(trades, f, indent=2)

    # Estatísticas
    pnls = [t['pnl'] for t in trades]
    rewards = [t['reward'] for t in trades]

    print(f"✅ Gerados {num_trades} trades Sprint 1")
    print(f"   Caminho: {filepath}")
    print(f"   PnL Médio: ${np.mean(pnls):.2f}")
    print(f"   PnL Std Dev: ${np.std(pnls):.2f}")
    print(f"   Trades Lucrativos: {sum(1 for p in pnls if p > 0)}/{num_trades}")
    print(f"   Win Rate: {sum(1 for p in pnls if p > 0) / num_trades * 100:.1f}%")
    print(f"   Reward Médio: {np.mean(rewards):.6f}")

    return trades


if __name__ == "__main__":
    # Gerar dados quando executado diretamente
    # Aumentado de 70 para 500 trades para melhor treinamento
    generate_sprint1_trades(num_trades=500)
