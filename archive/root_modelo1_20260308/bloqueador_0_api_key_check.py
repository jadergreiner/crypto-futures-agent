#!/usr/bin/env python3
"""Test API Key and Account Connection - BLOQUEADOR #0 (usando BinanceClientFactory)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.binance_client import BinanceClientFactory
from config.settings import TRADING_MODE

print("\n" + "=" * 80)
print("BLOQUEADOR #0: VERIFICAÇÃO DE API KEY E CONTA")
print("=" * 80)

print(f"\nCONFIGURAÇÃO:")
print(f"  Trading Mode: {TRADING_MODE}")

try:
    print(f"\n1. CONECTANDO À BINANCE...")
    factory = BinanceClientFactory(mode='live')
    client = factory.create_client()
    print("   ✅ Conexão estabelecida")

    # Test connection by getting account info
    print(f"\n2. VERIFICANDO INFORMAÇÕES DA CONTA...")
    account_info = client.rest_api.account()

    total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
    total_unrealized_loss = float(account_info.get('totalUnrealizedLoss', 0))

    print(f"   Total Wallet Balance: ${total_wallet_balance:.2f} USDT")
    print(f"   Total Unrealized Loss: ${total_unrealized_loss:.2f} USDT")

    # Get open positions
    print(f"\n3. VERIFICANDO POSIÇÕES ABERTAS...")
    positions = account_info.get('positions', [])

    # Filter for open positions (positionAmt != 0)
    open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]

    print(f"   Total de posições abertas: {len(open_positions)}")

    if open_positions:
        print(f"\n   PRIMEIRAS 20 POSIÇÕES:")
        for pos in open_positions[:20]:
            symbol = pos['symbol']
            side = 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
            amount = abs(float(pos['positionAmt']))
            entry_price = float(pos.get('entryPrice', 0))
            mark_price = float(pos.get('markPrice', 0))
            unrealized_pnl = float(pos.get('unRealizedProfit', 0))

            print(f"     {symbol} {side}: {amount:.8f} | Entry: ${entry_price} | Current: ${mark_price} | PnL: ${unrealized_pnl:.2f}")

        if len(open_positions) > 20:
            print(f"     ... mais {len(open_positions) - 20} posições")

    # Summary
    print(f"\n" + "=" * 80)
    print(f"RESULTADO:")
    print(f"=" * 80)
    print(f"  ✅ API KEY É VÁLIDA")
    print(f"  ✅ CONTA CONECTADA (LIVE)")
    print(f"  📊 Total de posições abertas: {len(open_positions)}")
    print(f"  💰 Capital total: ${total_wallet_balance:.2f} USDT")
    print(f"  📉 Perdas não realizadas: ${total_unrealized_loss:.2f} USDT")

    print(f"\n✅ BLOQUEADOR #0 RESOLVIDO: API Key é válida")

except Exception as e:
    print(f"\n❌ ERRO AO CONECTAR:")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
    print(f"\n⚠️  POSSÍVEIS CAUSAS:")
    print(f"   1. API Key inválida ou expirada")
    print(f"   2. API Secret incorreto")
    print(f"   3. IP não autenticado na Binance")
    print(f"   4. Problema de conectividade com Binance")
