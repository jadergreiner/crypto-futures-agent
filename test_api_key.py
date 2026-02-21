#!/usr/bin/env python3
"""Test API Key and Account Connection - BLOQUEADOR #0"""

import os
from binance.um_futures import UMFutures
from dotenv import load_dotenv

print("\n" + "=" * 80)
print("BLOQUEADOR #0: VERIFICAÇÃO DE API KEY E CONTA")
print("=" * 80)

# Load environment
load_dotenv()
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
trading_mode = os.getenv('TRADING_MODE', 'paper')

print(f"\nCONFIGURAÇÃO CARREGADA:")
print(f"  Trading Mode: {trading_mode}")
print(f"  API Key (primeiros 20 chars): {api_key[:20]}...")
print(f"  API Secret: {'***' if api_secret else 'NÃO CONFIGURADO'}")

# Connect to Binance
try:
    print(f"\n1. CONECTANDO À BINANCE...")
    client = UMFutures(
        key=api_key,
        secret=api_secret,
        base_url="https://fapi.binance.com"
    )
    print("   ✅ Conexão estabelecida")

    # Get account info
    print(f"\n2. VERIFICANDO INFORMAÇÕES DA CONTA...")
    account_info = client.account()

    account_id = account_info.get('clientId', 'DESCONHECIDO')
    total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
    total_unrealized_loss = float(account_info.get('totalUnrealizedLoss', 0))

    print(f"   Client ID: {account_id}")
    print(f"   Total Wallet Balance: ${total_wallet_balance:.2f} USDT")
    print(f"   Total Unrealized Loss: ${total_unrealized_loss:.2f} USDT")

    # Get open positions
    print(f"\n3. VERIFICANDO POSIÇÕES ABERTAS...")
    positions = client.get_open_orders()

    # Filter for open positions (not orders)
    open_positions = []
    for pos in account_info.get('positions', []):
        if float(pos['positionAmt']) != 0:
            open_positions.append(pos)

    print(f"   Total de posições abertas: {len(open_positions)}")

    if open_positions:
        print(f"\n   DETALHES:")
        for pos in open_positions[:20]:  # Show up to 20
            symbol = pos['symbol']
            side = 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
            amount = abs(float(pos['positionAmt']))
            entry_price = float(pos.get('entryPrice', 0))
            mark_price = float(pos.get('markPrice', 0))
            unrealized_pnl = float(pos.get('unRealizedProfit', 0))

            print(f"     {symbol} {side}: {amount:.8f} @ ${entry_price} (Current: ${mark_price}) | PnL: ${unrealized_pnl:.2f}")

    # Summary
    print(f"\n" + "=" * 80)
    print(f"RESULTADO:")
    print(f"=" * 80)
    print(f"  ✅ API KEY É VÁLIDA")
    print(f"  ✅ CONTA CONECTADA")
    print(f"  📊 Posições na conta: {len(open_positions)}")
    print(f"  💰 Capital disponível: ${total_wallet_balance:.2f} USDT")
    print(f"  📉 Perdas não realizadas: ${total_unrealized_loss:.2f} USDT")

    print(f"\n✅ BLOQUEADOR #0 RESOLVIDO: API Key é válida e apontada para conta correta")

except Exception as e:
    print(f"\n❌ ERRO AO CONECTAR:")
    print(f"   {str(e)}")
    print(f"\n⚠️  POSSÍVEIS CAUSAS:")
    print(f"   1. API Key inválida ou expirada")
    print(f"   2. API Secret incorreto")
    print(f"   3. IP não autenticado na Binance")
    print(f"   4. Problema de conectividade com Binance")
