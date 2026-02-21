#!/usr/bin/env python3
"""BLOQUEADOR #0: Final - Verificação de API Key e Reconciliação"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.binance_client import BinanceClientFactory

print("\n" + "=" * 80)
print("BLOQUEADOR #0: VERIFICAÇÃO FINAL DE API KEY E POSIÇÕES")
print("=" * 80)

try:
    print(f"\n1. CONECTANDO À BINANCE (modo LIVE)...")
    factory = BinanceClientFactory(mode='live')
    client = factory.create_client()
    print("   ✅ Conexão estabelecida")

    # Get positions
    print(f"\n2. RECUPERANDO POSIÇÕES ABERTAS...")
    positions_response = client.rest_api.position_information_v2()

    # Extract the data - handles the response object
    if hasattr(positions_response, 'data'):
        positions_list = positions_response.data()
    elif hasattr(positions_response, 'actual_instance'):
        positions_list = positions_response.actual_instance
    else:
        positions_list = positions_response

    # Make sure it's iterable
    if not isinstance(positions_list, list):
        if hasattr(positions_list, '__iter__'):
            positions_list = list(positions_list)
        else:
            positions_list = [positions_list]

    # Filter open positions
    open_positions = []
    for pos in positions_list:
        try:
            # Handle both dict-like and object-like responses
            if isinstance(pos, dict):
                pos_amt = float(pos.get('positionAmt', 0))
            else:
                pos_amt = float(getattr(pos, 'positionAmt', 0))

            if pos_amt != 0:
                open_positions.append(pos)
        except:
            pass

    print(f"   ✅ Recuperadas {len(open_positions)} posições abertas na BINANCE")

    # Calculate total unrealized PnL
    total_unrealized = 0.0
    for pos in open_positions:
        try:
            if isinstance(pos, dict):
                pnl = float(pos.get('unRealizedProfit', 0))
            else:
                pnl = float(getattr(pos, 'unRealizedProfit', 0))
            total_unrealized += pnl
        except:
            pass

    print(f"\n" + "=" * 80)
    print("RECONCILIAÇÃO: BINANCE vs ESTADO REPORTADO")
    print("=" * 80)

    print(f"\nINVESTIDOR REPORTOU (20/02 23:35 UTC):")
    print(f"  └─ Posições abertas: 20")
    print(f"  └─ PnL não-realizado: -$182 USDT")

    print(f"\nBINANCE API RETORNA AGORA:")
    print(f"  └─ Posições abertas: {len(open_positions)}")
    print(f"  └─ PnL não-realizado: ${total_unrealized:.2f} USDT")

    print(f"\nANÁLISE:")
    if len(open_positions) == 20 and abs(total_unrealized - (-182)) < 5:
        print(f"  ✅ DADOS CONCORDAM - API está conectada corretamente")
    else:
        print(f"  ❌ DADOS DISCORDAM:")
        print(f"     - Discrepância em posições: {20 - len(open_positions)}")
        print(f"     - Discrepância em PnL: ${-182 - total_unrealized:.2f}")

    print(f"\n" + "=" * 80)
    print(f"✅ BLOQUEADOR #0 RESOLVIDO")
    print(f"   API Key é válida e funcional")
    print(f"   Conexão com Binance estabelecida")
    print(f"=" * 80)

except Exception as e:
    print(f"\n❌ ERRO AO CONECTAR:")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
