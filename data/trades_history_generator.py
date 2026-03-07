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


def generate_sprint1_trades(num_trades=70, filepath="data/trades_history.json"):
    """
    Gera histórico de 70 trades Sprint 1 com características realistas.
    
    Args:
        num_trades: Número de trades a gerar (padrão: 70)
        filepath: Caminho para salvar o arquivo JSON
    """
    trades = []
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT']
    
    # Simulação: 70 trades ao longo de 30 dias
    start_date = datetime(2026, 1, 15, 0, 0, 0)
    
    np.random.seed(42)  # Reproduzibilidade
    
    for i in range(num_trades):
        symbol = symbols[i % len(symbols)]
        
        # Tempo: espaçado ao longo de 30 dias
        trade_date = start_date + timedelta(hours=10 + (i * 10))
        entry_time = trade_date.isoformat() + 'Z'
        exit_time = (trade_date + timedelta(hours=2)).isoformat() + 'Z'
        
        # Preço de entrada: simulação realista por símbolo
        if symbol == 'BTCUSDT':
            base_price = 42000
        elif symbol == 'ETHUSDT':
            base_price = 2500
        elif symbol == 'BNBUSDT':
            base_price = 600
        elif symbol == 'XRPUSDT':
            base_price = 2.5
        else:
            base_price = 1.0
        
        # Entrada com pequena variação
        entry_price = base_price * (1 + np.random.normal(0, 0.02))
        
        # Saída: varia de -2% a +3% (ganho típico)
        direction = 'LONG' if np.random.random() > 0.4 else 'SHORT'
        pnl_pct = np.random.uniform(-0.02, 0.03)
        
        if direction == 'SHORT':
            pnl_pct = -pnl_pct  # Inverte para short
        
        exit_price = entry_price * (1 + pnl_pct)
        
        # Quantidade e PnL
        qty = 1.0  # 1 contrato por trade
        pnl = (exit_price - entry_price) * qty
        
        # Reward normalizado (PnL / entrada)
        reward = pnl / entry_price
        
        trade = {
            'id': i + 1,
            'symbol': symbol,
            'entry_price': round(entry_price, 8),
            'exit_price': round(exit_price, 8),
            'qty': qty,
            'direction': direction,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': round(pnl, 8),
            'reward': round(reward, 6),
            'duration_hours': 2.0,
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
    generate_sprint1_trades(num_trades=70)
