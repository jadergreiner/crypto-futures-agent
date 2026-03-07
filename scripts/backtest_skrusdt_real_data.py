#!/usr/bin/env python3
"""Backtest SKRUSDT com dados reais - versão simplificada."""

import sqlite3
import sys
import json
from pathlib import Path
from typing import List, Dict

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_candles(symbol: str, db_path: str = "data/klines_cache.db") -> List[Dict]:
    """Carrega candles reais do banco de dados."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT symbol, open_time, open, high, low, close, volume, 
                   quote_volume, trades
            FROM klines 
            WHERE symbol = ? 
            ORDER BY open_time ASC
        """, (symbol,))
        
        rows = cur.fetchall()
        conn.close()
        
        candles = []
        for row in rows:
            candles.append({
                'symbol': row['symbol'],
                'timestamp': row['open_time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
                'quote_volume': float(row['quote_volume']),
            })
        
        return candles
    
    except Exception as e:
        print(f"❌ Erro ao carregar candles: {e}")
        return []


def run_backtest(candles: List[Dict]) -> Dict:
    """Executa backtest simples com dados reais."""
    
    if len(candles) < 20:
        return {"error": "Insuficientes candles"}
    
    capital = 1000.0
    position = None
    wins = 0
    losses = 0
    total_trades = 0
    equity = [capital]
    
    print(f"\n🚀 Iniciando backtest com {len(candles)} candles...")
    print(f"   Capital inicial: ${capital:.2f}\n")
    
    closes = [float(c['close']) for c in candles]
    
    for idx in range(20, len(candles) - 1):
        candle = candles[idx]
        close_price = candle['close']
        
        # Indicadores simples
        sma20 = sum(closes[idx-20:idx]) / 20
        volatility = (candle['high'] - candle['low']) / close_price * 100
        confluence_score = min(10, 5 + (volatility / 2))
        
        # Bias e sinal
        bias = "UP" if close_price > sma20 else "DOWN"
        risco_ok = volatility < 5.0
        
        should_trade = (confluence_score > 4.0 and bias == "UP" and risco_ok)
        
        # Lógica de entrada/saída
        if should_trade and position is None:
            position = {
                'entry': close_price,
                'entry_idx': idx,
                'sl': close_price * 0.98,
                'tp': close_price * 1.05,
                'size': capital * 0.1 / close_price,
            }
            print(f"   [{idx:3d}] 📈 BUY @ ${close_price:.6f}")
        
        elif position is not None:
            exit_price = None
            exit_type = None
            pnl = 0
            
            if close_price <= position['sl']:
                exit_price = position['sl']
                exit_type = "SL"
                pnl = (position['sl'] - position['entry']) * position['size']
                losses += 1
            elif close_price >= position['tp']:
                exit_price = position['tp']
                exit_type = "TP"
                pnl = (position['tp'] - position['entry']) * position['size']
                wins += 1
            elif idx - position['entry_idx'] > 20:
                exit_price = close_price
                exit_type = "TIMEOUT"
                pnl = (close_price - position['entry']) * position['size']
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
            
            if exit_price:
                total_trades += 1
                capital += pnl
                equity.append(capital)
                
                trade_ret = (pnl / (position['entry'] * position['size'])) * 100
                print(f"   [{idx:3d}] 📉 {exit_type:7s} @ ${exit_price:.6f} | PnL: ${pnl:+7.3f} ({trade_ret:+6.2f}%)")
                position = None
        
        # Atualiza equity diária
        if position:
            current_equity = capital + (close_price - position['entry']) * position['size']
            equity.append(current_equity)
    
    # Calcula stats
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    profit_factor = wins / max(losses, 1) if losses > 0 else (wins if wins > 0 else 0)
    
    stats = {
        'symbol': 'SKRUSDT',
        'candles': len(candles),
        'trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 2),
        'profit_factor': round(profit_factor, 2),
        'final_capital': round(capital, 2),
        'total_pnl': round(capital - 1000, 2),
        'return_pct': round((capital - 1000) / 1000 * 100, 2),
    }
    
    # Resume final
    print(f"\n" + "="*70)
    print(f"📊 RESULTADO FINAL DO BACKTEST")
    print(f"="*70)
    print(f"   Símbolo: SKRUSDT")
    print(f"   Candles: {stats['candles']}")
    print(f"   Operações: {stats['trades']} (Wins: {stats['wins']}, Losses: {stats['losses']})")
    print(f"   Win Rate: {stats['win_rate']}%")
    print(f"   Profit Factor: {stats['profit_factor']}x")
    print(f"   Capital Inicial: $1000.00")
    print(f"   Capital Final: ${stats['final_capital']:.2f}")
    print(f"   Resultado: ${stats['total_pnl']:+.2f} ({stats['return_pct']:+.2f}%)")
    print(f"="*70)
    
    if win_rate >= 45 and total_trades >= 3:
        print(f"✅ MODELO VALIDADO! ({win_rate:.1f}% >= 45%)")
        print(f"   Pronto para paper trading (Opção 1 no menu)")
    elif total_trades < 3:
        print(f"⚠️  Poucos sinais ({total_trades} trades)")
        print(f"   Aguarde mais candles ou integre mais confluências")
    else:
        print(f"⚠️  Win rate baixa ({win_rate:.1f}% < 45%)")
        print(f"   Modelo precisa de ajustes antes do trading")
    
    return stats


if __name__ == "__main__":
    print("📊 BACKTEST SKRUSDT COM DADOS REAIS")
    print("="*70)
    
    candles = load_candles("SKRUSDT")
    
    if not candles:
        print("❌ Nenhum candle encontrado!")
        sys.exit(1)
    
    print(f"✅ Carregado: {len(candles)} candles de SKRUSDT")
    
    stats = run_backtest(candles)
    
    # Salva resultado
    Path("results").mkdir(exist_ok=True)
    with open("results/backtest_skrusdt_real_results.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n💾 Resultado salvo em: results/backtest_skrusdt_real_results.json")
