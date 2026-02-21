#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Proteções - Status Visual
"""

import sqlite3
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_protection_dashboard():
    """Exibir dashboard com status das proteções."""

    try:
        from data.binance_client import BinanceClientFactory

        factory = BinanceClientFactory(mode="live")
        client = factory.create_client()

        conn = sqlite3.connect("db/crypto_futures.db")
        cursor = conn.cursor()

        # Buscar trades abertos
        cursor.execute("""
            SELECT trade_id, symbol, direcao, entry_price, stop_loss, take_profit,
                   leverage, position_size_usdt, timestamp_entrada, binance_order_id
            FROM trade_log
            WHERE timestamp_saida IS NULL
        """)

        open_trades = cursor.fetchall()
        conn.close()

        print("\n" + "=" * 100)
        print("🛡️  PROTEÇÕES DE POSIÇÕES ABERTAS - DASHBOARD".center(100))
        print("=" * 100)

        if not open_trades:
            print("\n   ℹ️  Nenhuma posição aberta\n")
            return

        print(f"\n   ✓ Total de posições abertas: {len(open_trades)}\n")

        for i, trade in enumerate(open_trades, 1):
            trade_id, symbol, direcao, entry_price, stop_loss, take_profit, \
                leverage, position_size_usdt, timestamp_entrada, binance_order_id = trade

            # Obter preço atual
            try:
                mark_price_response = client.rest_api.mark_price(symbol=symbol)
                price_data = mark_price_response.data()
                current_price = float(price_data.actual_instance.mark_price)
            except:
                current_price = entry_price

            # Calcular métricas
            if direcao == "LONG":
                pnl = (current_price - entry_price) * (position_size_usdt / entry_price)
            else:
                pnl = (entry_price - current_price) * (position_size_usdt / entry_price)

            pnl_pct = (pnl / position_size_usdt) * 100

            # Liquidação
            if direcao == "LONG":
                liquidation_price = entry_price * (1 - 1/leverage)
                dist_liq = ((current_price - liquidation_price) / entry_price) * 100
            else:
                liquidation_price = entry_price * (1 + 1/leverage)
                dist_liq = ((liquidation_price - current_price) / entry_price) * 100

            # Tempo aberta
            tempo_aberta_min = (datetime.now().timestamp() * 1000 - timestamp_entrada) / 60000

            # Status do SL
            if direcao == "LONG":
                sl_triggered = current_price <= stop_loss
                tp_triggered = current_price >= take_profit
            else:
                sl_triggered = current_price >= stop_loss
                tp_triggered = current_price <= take_profit

            # Cores/Status
            status_sl = "🔴 ACIONADO" if sl_triggered else "🟢 ATIVO"
            status_tp = "🟢 ACIONADO" if tp_triggered else "🟢 ATIVO"
            status_liq = "🔴 CRÍTICO" if dist_liq < 1 else "🟢 SEGURO"
            status_timeout = "⚠️  (1h50m)" if tempo_aberta_min > 110 else "🟢"

            # Print formatado
            print(f"\n   {'─' * 96}")
            print(f"   📊 POSIÇÃO {i}: {symbol} {direcao}")
            print(f"   {'─' * 96}")
            print(f"   │ Trade ID: {trade_id:4d} │ Order ID: {binance_order_id:15s} │ Atuais: ${position_size_usdt:.2f}")
            print(f"   │")
            print(f"   ├─ 💰 PREÇO")
            print(f"   │   Entry:        ${entry_price:.8f}")
            print(f"   │   Atual:        ${current_price:.8f}")
            print(f"   │   Diferença:    {((current_price - entry_price) / entry_price * 100):+.2f}%")
            print(f"   │")
            print(f"   ├─ 📈 PnL")
            print(f"   │   USDT:         ${pnl:+.2f}")
            print(f"   │   %:            {pnl_pct:+.2f}%")
            print(f"   │")
            print(f"   ├─ 🛡️  PROTEÇÕES")
            print(f"   │   Stop Loss:    ${stop_loss:.8f}  {status_sl}")
            print(f"   │   Take Profit:  ${take_profit:.8f}  {status_tp}")
            print(f"   │   Liquidação:   ${liquidation_price:.8f}  {status_liq} ({dist_liq:.1f}%)")
            print(f"   │   Timeout:      {tempo_aberta_min:.0f}m  {status_timeout}")
            print(f"   │")
            print(f"   └─ ⚙️  CONFIGURAÇÃO")
            print(f"       Leverage:    {leverage}x | Size: ${position_size_usdt:.2f}")

        print(f"\n   {'═' * 96}\n")

    except Exception as e:
        print(f"\n❌ Erro: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print_protection_dashboard()
