#!/usr/bin/env python3
"""
Script SIMPLES para verificar posições reais na Binance
"""

import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

print("=" * 100)
print("🔍 AUDITORIA REAL DE POSIÇÕES - VERSÃO SIMPLES")
print("=" * 100)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

try:
    from data.binance_client import create_binance_client
    from config.settings import TRADING_MODE

    client = create_binance_client(mode=TRADING_MODE)
    print(f"✅ Conectado à Binance ({TRADING_MODE})\n")

    # Tentar obter posições via position_information_v2 SEM especificar símbolo
    # (ou com lista vazia para ver se retorna tudo)

    print("-" * 100)
    print("TENTATIVA 1: Obter posições sem filtro por símbolo")
    print("-" * 100)

    try:
        # Alguns SDKs aceitam None ou "" ou vazio
        response = client.rest_api.position_information_v2()
        print(f"✅ Resposta obtida: {type(response)}")

        if hasattr(response, 'data'):
            data = response.data
            if callable(data):
                data = data()
        else:
            data = response

        if isinstance(data, list):
            print(f"\n📊 Total de posições retornadas: {len(data)}\n")

            # DEBUG: Mostrar primeiras 5 posições para ver estrutura
            print("DEBUG: Primeiras 5 posições (estrutura):")
            for idx, pos in enumerate(data[:5]):
                if isinstance(pos, dict):
                    print(f"  {idx}: keys={list(pos.keys())}")
                    print(f"       symbol={pos.get('symbol')}, positionAmt={pos.get('positionAmt')}, unrealizedProfit={pos.get('unrealizedProfit')}")
                else:
                    # É um PositionInformationV2Response object
                    print(f"  {idx}: type={type(pos).__name__}")
                    # Tentar converter para dict
                    try:
                        pos_dict = pos.dict() if hasattr(pos, 'dict') else vars(pos)
                        symbol = pos_dict.get('symbol', 'N/A')
                        pos_amt = float(pos_dict.get('positionAmt', 0))
                        unrealized_pnl = float(pos_dict.get('unrealizedProfit', 0))
                        print(f"       symbol={symbol}, positionAmt={pos_amt}, unrealizedProfit={unrealized_pnl}")
                    except Exception as e:
                        print(f"       Erro ao converter: {e}")

            print("\n" + "-" * 100 + "\n")

            open_positions = []
            all_positions_with_pnl = []

            for idx, pos in enumerate(data, 1):
                try:
                    # Converter SDK object para dict
                    if hasattr(pos, 'dict'):
                        pos_dict = pos.dict()
                    elif isinstance(pos, dict):
                        pos_dict = pos
                    else:
                        pos_dict = vars(pos)

                    symbol = pos_dict.get('symbol', 'N/A')
                    pos_amt = float(pos_dict.get('positionAmt', 0))
                    unrealized_pnl = float(pos_dict.get('unrealizedProfit', 0))

                    # Registrar todas com PnL != 0, mesmo que positionAmt = 0
                    if unrealized_pnl != 0:
                        all_positions_with_pnl.append({
                            'symbol': symbol,
                            'quantity': pos_amt,
                            'unrealized_pnl': unrealized_pnl
                        })

                    if pos_amt != 0:
                        direction = 'LONG' if pos_amt > 0 else 'SHORT'
                        open_positions.append({
                            'symbol': symbol,
                            'direction': direction,
                            'quantity': abs(pos_amt),
                            'unrealized_pnl': unrealized_pnl
                        })
                except Exception as e:
                    print(f"⚠️  Erro ao processar posição {idx}: {e}")

            if open_positions:
                print(f"🟢 POSIÇÕES ABERTAS ENCONTRADAS: {len(open_positions)}\n")
                print(f"{'#':<3} {'Symbol':<15} {'Direction':<6} {'Quantity':<15} {'Unrealized PnL':<15}")
                print("-" * 100)
                for idx, pos in enumerate(open_positions, 1):
                    print(f"{idx:<3} {pos['symbol']:<15} {pos['direction']:<6} {pos['quantity']:<15.4f} ${pos['unrealized_pnl']:<14.2f}")

                total_pnl = sum(p['unrealized_pnl'] for p in open_positions)
                print("-" * 100)
                print(f"TOTAL PnL NÃO REALIZADO: ${total_pnl:.2f}\n")
            else:
                print("🔴 NENHUMA POSIÇÃO ABERTA ENCONTRADA (positionAmt = 0)\n")

            # Mostrar posições com PnL mesmo que fechadas (positionAmt = 0)
            if all_positions_with_pnl:
                print(f"\n⚠️  POSIÇÕES COM PnL (mesmo que fechadas): {len(all_positions_with_pnl)}")
                print("-" * 100)
                print(f"{'#':<3} {'Symbol':<15} {'Quantity':<15} {'Unrealized PnL':<15}")
                print("-" * 100)
                for idx, pos in enumerate(all_positions_with_pnl, 1):
                    print(f"{idx:<3} {pos['symbol']:<15} {pos['quantity']:<15.4f} ${pos['unrealized_pnl']:<14.2f}")

                total_pnl_all = sum(p['unrealized_pnl'] for p in all_positions_with_pnl)
                print("-" * 100)
                print(f"TOTAL PnL (Incluindo fechadas): ${total_pnl_all:.2f}\n")
            else:
                print("ℹ️  Nenhuma posição com PnL encontrada\n")
        else:
            print(f"Tipo de retorno: {type(data)}")
            print(f"Conteúdo: {data}\n")

    except AttributeError as e:
        print(f"❌ Método position_information_v2() não existe ou diferente: {e}\n")

        print("-" * 100)
        print("TENTATIVA 2: Listar métodos disponíveis no client")
        print("-" * 100)

        print("\nMétodos disponíveis em client.rest_api:")
        for attr in dir(client.rest_api):
            if not attr.startswith('_') and 'position' in attr.lower():
                print(f"  • {attr}")

        for attr in dir(client.rest_api):
            if not attr.startswith('_') and ('account' in attr.lower() or 'balance' in attr.lower()):
                print(f"  • {attr}")

except ImportError as e:
    print(f"❌ Erro de importação: {e}")

except Exception as e:
    print(f"❌ Erro crítico: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
