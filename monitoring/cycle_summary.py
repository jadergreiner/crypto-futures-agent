"""
Consolidado visual de ciclo de monitoramento (5 minutos).

Mostra resumido por símbolo:
- Cotação atual
- Indicadores (SMC confluence, direção, regime)
- Sinal gerado
- Posição aberta (tipo, quantidade, PnL)
- Status de treinamento
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def get_symbol_status(cursor, symbol: str) -> dict:
    """Coleta status consolidado de um símbolo."""
    status = {"symbol": symbol}
    
    try:
        # Última cotação
        cursor.execute(
            "SELECT price FROM market_data WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
            (symbol,)
        )
        price = cursor.fetchone()
        status["price"] = f"{price[0]:.6f}" if price else "NA"
    except Exception:
        status["price"] = "NA"
    
    try:
        # Últimos indicadores (H4)
        cursor.execute(
            "SELECT confluence, direction, regime FROM indicator_cache WHERE symbol=? AND timeframe='H4' ORDER BY timestamp DESC LIMIT 1",
            (symbol,)
        )
        indicators = cursor.fetchone()
        if indicators:
            status["confluence"] = f"{int(indicators[0])}/14"
            status["direction"] = indicators[1][:4] if indicators[1] else "NA"
            status["regime"] = indicators[2][:5] if indicators[2] else "NA"
        else:
            status["confluence"] = "NA"
            status["direction"] = "NA"
            status["regime"] = "NA"
    except Exception:
        status["confluence"] = "NA"
        status["direction"] = "NA"
        status["regime"] = "NA"
    
    try:
        # Último sinal
        cursor.execute(
            "SELECT signal_type FROM trade_signals WHERE symbol=? ORDER BY timestamp DESC LIMIT 1",
            (symbol,)
        )
        signal = cursor.fetchone()
        status["signal"] = signal[0][:4] if signal else "NA"
    except Exception:
        status["signal"] = "NA"
    
    try:
        # Posição aberta
        cursor.execute(
            "SELECT position_type, quantity, entry_price, current_price, pnl_usd FROM positions WHERE symbol=? AND status='OPEN' LIMIT 1",
            (symbol,)
        )
        position = cursor.fetchone()
        if position:
            pos_type = "UP" if position[0] == "LONG" else "DN"
            qty = position[1]
            entry = position[2]
            current = position[3]
            pnl = position[4]
            color = "[+]" if pnl > 0 else "[-]"
            status["position"] = f"{color}{pos_type} {qty:.2e}@{entry:.6f} | PnL:{pnl:+.2f}$"
        else:
            status["position"] = "NA"
    except Exception:
        status["position"] = "NA"
    
    try:
        # Status de treinamento (% de wins na janela recente)
        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) * 100.0 / COUNT(*) 
            FROM positions 
            WHERE symbol=? AND status='CLOSED'
            LIMIT 100
            """,
            (symbol,)
        )
        win_rate = cursor.fetchone()
        training_pct = int(win_rate[0]) if win_rate and win_rate[0] else 0
        status["training"] = f"{training_pct}%"
    except Exception:
        status["training"] = "NA"
    
    return status


def print_cycle_summary(symbols: list[str], db_path: str = "db/crypto_agent.db") -> None:
    """
    Imprime consolidado visual de um ciclo de monitoramento (5 minutos).
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"⚠️  Banco de dados não encontrado: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*160}")
        print(f"[CICLO] MONITORAMENTO - {now}")
        print(f"{'='*160}")
        print(f"{'SYMBOL':<12} {'PRICE':<12} {'CONF':<6} {'DIR':<5} {'REGIME':<6} {'SIGNAL':<6} {'POSITION':<50} {'TRAINING':<8}")
        print(f"{'-'*160}")
        
        for symbol in sorted(symbols):
            status = get_symbol_status(cursor, symbol)
            
            line = (
                f"{status['symbol']:<12} "
                f"{status['price']:<12} "
                f"{status['confluence']:<6} "
                f"{status['direction']:<5} "
                f"{status['regime']:<6} "
                f"{status['signal']:<6} "
                f"{status['position']:<50} "
                f"{status['training']:<8}"
            )
            print(line)
        
        print(f"{'='*160}\n")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERRO] Ao consolidar ciclo: {e}")


# Script standalone para testes
if __name__ == "__main__":
    from config.symbols import ALL_SYMBOLS
    print_cycle_summary(ALL_SYMBOLS)
