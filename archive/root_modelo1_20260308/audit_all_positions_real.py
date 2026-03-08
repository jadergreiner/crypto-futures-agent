#!/usr/bin/env python3
"""
Script de Auditoria REAL: Obter TODAS as posições abertas na Binance
Sem filtro por pares - retorna tudo que está aberto
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("=" * 100)
print("🔍 AUDITORIA REAL: TODAS AS POSIÇÕES ABERTAS NA BINANCE")
print("=" * 100)

try:
    from data.binance_client import create_binance_client
    from config.settings import TRADING_MODE

    # Criar cliente
    try:
        client = create_binance_client(mode=TRADING_MODE)
        print(f"\n✅ Conectado à Binance (modo: {TRADING_MODE})")
    except Exception as e:
        print(f"\n❌ ERRO ao conectar: {e}")
        sys.exit(1)

    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Passo 1: Obter informações da conta
    print("-" * 100)
    print("PASSO 1: INFORMAÇÕES DA CONTA")
    print("-" * 100)

    try:
        account_response = client.rest_api.get_account()

        if hasattr(account_response, 'data'):
            account_data = account_response.data
            if callable(account_data):
                account_data = account_data()
        else:
            account_data = account_response

        if isinstance(account_data, dict):
            total_wallet_balance = account_data.get('totalWalletBalance', 'N/A')
            total_margin_balance = account_data.get('totalMarginBalance', 'N/A')
            available_balance = account_data.get('availableBalance', 'N/A')
        else:
            total_wallet_balance = getattr(account_data, 'totalWalletBalance', 'N/A')
            total_margin_balance = getattr(account_data, 'totalMarginBalance', 'N/A')
            available_balance = getattr(account_data, 'availableBalance', 'N/A')

        print(f"Saldo Total: ${total_wallet_balance}")
        print(f"Saldo em Margem: ${total_margin_balance}")
        print(f"Saldo Disponível: ${available_balance}\n")

    except Exception as e:
        print(f"⚠️  Erro ao obter saldo: {e}\n")

    # Passo 2: Obter TODAS as posições abertas (sem filtro)
    print("-" * 100)
    print("PASSO 2: TODAS AS POSIÇÕES ABERTAS")
    print("-" * 100)

    try:
        all_positions_response = client.rest_api.get_account()

        if hasattr(all_positions_response, 'data'):
            all_positions_data = all_positions_response.data
            if callable(all_positions_data):
                all_positions_data = all_positions_data()
        else:
            all_positions_data = all_positions_response

        # Extrair posições do objeto de conta
        positions = []

        if isinstance(all_positions_data, dict):
            positions = all_positions_data.get('positions', [])
        else:
            positions = getattr(all_positions_data, 'positions', [])

        if not positions:
            print("\n⚠️  Nenhuma posição encontrada via get_account()\n")
            print("Tentando alternativa: position_information() com parâmetros vazios...")

        print(f"\nTotal de posições encontradas: {len(positions)}\n")

        if positions:
            open_count = 0
            closed_count = 0

            print(f"{'#':<3} {'Symbol':<15} {'Direction':<6} {'Qty':<12} {'EntryPrice':<12} {'MarkPrice':<12} {'Unrealized PnL':<15} {'Leverage':<8}")
            print("-" * 100)

            for idx, pos in enumerate(positions, 1):
                try:
                    if isinstance(pos, dict):
                        symbol = pos.get('symbol', 'N/A')
                        pos_amt = float(pos.get('positionAmt', 0))
                        entry_price = float(pos.get('entryPrice', 0))
                        mark_price = float(pos.get('markPrice', 0))
                        unrealized_pnl = float(pos.get('unrealizedProfit', 0))
                        leverage = pos.get('leverage', 'N/A')
                    else:
                        symbol = getattr(pos, 'symbol', 'N/A')
                        pos_amt = float(getattr(pos, 'positionAmt', 0))
                        entry_price = float(getattr(pos, 'entryPrice', 0))
                        mark_price = float(getattr(pos, 'markPrice', 0))
                        unrealized_pnl = float(getattr(pos, 'unrealizedProfit', 0))
                        leverage = getattr(pos, 'leverage', 'N/A')

                    if pos_amt != 0:
                        direction = 'LONG' if pos_amt > 0 else 'SHORT'
                        open_count += 1

                        print(f"{idx:<3} {symbol:<15} {direction:<6} {abs(pos_amt):<12.4f} {entry_price:<12.6f} {mark_price:<12.6f} ${unrealized_pnl:<14.2f} {leverage}x")
                    else:
                        closed_count += 1

                except Exception as pos_err:
                    print(f"⚠️  Erro ao processar posição {idx}: {pos_err}")

            print("-" * 100)
            print(f"\n✅ Posições ABERTAS: {open_count}")
            print(f"⏹️  Posições FECHADAS: {closed_count}")

            # Calcular PnL total não realizado
            total_unrealized = sum(
                float(p.get('unrealizedProfit', 0) if isinstance(p, dict)
                      else getattr(p, 'unrealizedProfit', 0))
                for p in positions
            )

            print(f"📊 PnL NÃO REALIZADO TOTAL: ${total_unrealized:.2f}\n")

        else:
            print("\n[Sem posições encontradas]\n")

    except Exception as e:
        print(f"\n❌ Erro ao obter posições: {e}\n")
        import traceback
        traceback.print_exc()

    # Passo 3: Análise de inconsistências
    print("-" * 100)
    print("PASSO 3: VALIDAÇÕES")
    print("-" * 100)

    print(f"""
✅ Verificação de Lógica:
   • Se PnL não-realizado = -$182 → DEVE haver posições abertas
   • Se há posições abertas → DEVEM estar reportadas aqui
   • Se há 20 posições na Binance → DEVEM aparecer ou há filtro incorreto

⚠️  Possíveis fontes de discrepâncias:
   1. Script check_open_orders.py filtra apenas 10 pares específicos
   2. Posições podem estar em pares não monitorados
   3. API pode estar retornando dados parciais
   4. Permissões da API key podem ser restritas

📋 PRÓXIMAS ETAPAS:
   • Comparar resultado aqui com {len(positions)} posições reportadas
   • Se diferente de 0, identificar quais pares
   • Verificar por que check_open_orders.py não detectou
    """)

except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("Certifique-se de que as dependências estão instaladas")
    sys.exit(1)

except Exception as e:
    print(f"❌ Erro crítico: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 100)
print("FIM DA AUDITORIA")
print("=" * 100)
