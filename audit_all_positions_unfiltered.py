#!/usr/bin/env python3
"""
Script de Auditoria COMPLETO:
- Sem filtro de pares específicos
- Lista TODAS as posições (abertas ou fechadas)
- Mostra aquelas com PnL não-realizado
"""

import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("=" * 120)
print("🔍 AUDITORIA COMPLETA: TODAS AS POSIÇÕES +PnL")
print("=" * 120)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

try:
    from data.binance_client import create_binance_client
    from config.settings import TRADING_MODE

    client = create_binance_client(mode=TRADING_MODE)
    print(f"✅ Conectado à Binance ({TRADING_MODE})\n")

    # Obter TODAS as posições sem filtro
    print("-" * 120)
    print("PASSO 1: Obter TODAS as posições")
    print("-" * 120)

    try:
        response = client.rest_api.position_information_v2()

        if hasattr(response, 'data'):
            data = response.data
            if callable(data):
                data = data()
        else:
            data = response

        print(f"✅ Resposta obtida: {len(data)} posições totais returnadas\n")

        # Processar TODAS as posições
        open_positions = []
        closed_positions_with_pnl = []

        print("-" * 120)
        print("PASSO 2: Filtrar posições")
        print("-" * 120)

        for idx, pos in enumerate(data):
            try:
                # Converter para dict
                if hasattr(pos, 'model_dump'):
                    pos_dict = pos.model_dump()
                elif hasattr(pos, 'dict'):
                    pos_dict = pos.dict()
                else:
                    pos_dict = vars(pos)

                symbol = pos_dict.get('symbol', 'N/A')
                pos_amt = float(pos_dict.get('positionAmt', 0))
                unrealized_pnl = float(pos_dict.get('unrealizedProfit', 0))
                entry_price = float(pos_dict.get('entryPrice', 0))
                mark_price = float(pos_dict.get('markPrice', 0))

                # Posições com quantidade (ABERTAS)
                if pos_amt != 0:
                    direction = 'LONG' if pos_amt > 0 else 'SHORT'
                    open_positions.append({
                        'symbol': symbol,
                        'direction': direction,
                        'quantity': abs(pos_amt),
                        'entry_price': entry_price,
                        'mark_price': mark_price,
                        'unrealized_pnl': unrealized_pnl
                    })

                # Posições FECHADAS mas com PnL não-realizado (ainda gerando perda)
                elif pos_amt == 0 and unrealized_pnl != 0:
                    closed_positions_with_pnl.append({
                        'symbol': symbol,
                        'unrealized_pnl': unrealized_pnl,
                        'entry_price': entry_price,
                        'mark_price': mark_price
                    })

            except Exception as e:
                print(f"⚠️  Erro ao processar posição {idx}: {e}")

        print(f"\n✅ POSIÇÕES ABERTAS (positionAmt ≠ 0): {len(open_positions)}")
        print(f"⚠️  POSIÇÕES FECHADAS C/ PnL (positionAmt = 0, PnL ≠ 0): {len(closed_positions_with_pnl)}\n")

        # Mostrar posições abertas
        if open_positions:
            print("\n" + "=" * 120)
            print("📊 POSIÇÕES ABERTAS")
            print("=" * 120)
            print(f"{'#':<3} {'Symbol':<15} {'Direction':<6} {'Qty':<12} {'Entry':<12} {'Mark':<12} {'Unrealized PnL':<15}")
            print("-" * 120)

            total_open_pnl = 0
            for idx, pos in enumerate(open_positions, 1):
                print(f"{idx:<3} {pos['symbol']:<15} {pos['direction']:<6} {pos['quantity']:<12.4f} {pos['entry_price']:<12.6f} {pos['mark_price']:<12.6f} ${pos['unrealized_pnl']:<14.2f}")
                total_open_pnl += pos['unrealized_pnl']

            print("-" * 120)
            print(f"TOTAL PnL NÃO-REALIZADO (ABERTAS): ${total_open_pnl:.2f}\n")

        # Mostrar posições fechadas com PnL
        if closed_positions_with_pnl:
            print("\n" + "=" * 120)
            print("⚠️  POSIÇÕES FECHADAS COM PnL (positionAmt = 0, mas PnL ≠ 0)")
            print("=" * 120)
            print(f"{'#':<3} {'Symbol':<15} {'Entry':<12} {'Mark':<12} {'Unrealized PnL':<15}")
            print("-" * 120)

            total_pnl_closed = 0
            for idx, pos in enumerate(closed_positions_with_pnl, 1):
                print(f"{idx:<3} {pos['symbol']:<15} {pos['entry_price']:<12.6f} {pos['mark_price']:<12.6f} ${pos['unrealized_pnl']:<14.2f}")
                total_pnl_closed += pos['unrealized_pnl']

            print("-" * 120)
            print(f"TOTAL PnL (FECHADAS): ${total_pnl_closed:.2f}\n")

        # Resumo final
        print("\n" + "=" * 120)
        print("📋 RESUMO FINAL")
        print("=" * 120)

        grand_total_pnl = sum(p['unrealized_pnl'] for p in open_positions) + sum(p['unrealized_pnl'] for p in closed_positions_with_pnl)

        print(f"""
Posições Abertas (positionAmt ≠ 0):        {len(open_positions):>3}
Posições Fechadas (positionAmt = 0):       {len(data) - len(open_positions) - len(closed_positions_with_pnl):>3}
Posições Fechadas c/ PnL:                  {len(closed_positions_with_pnl):>3}
─────────────────────────────────────────────────
TOTAL de Posições (abertas+fechadas+PnL): {len(open_positions) + len(closed_positions_with_pnl):>3}

TOTAL PnL NÃO-REALIZADO (GERAL):           ${grand_total_pnl:>10.2f}

COMPARAÇÃO COM DADOS DO INVESTIDOR:
└─ Reportou: 20 posições abertas, -$182 PnL
└─ Sistema retorna: {len(open_positions)} abertas, ${grand_total_pnl:.2f} PnL
└─ Status: {'✅ MATCH!' if len(open_positions) == 20 and abs(grand_total_pnl + 182) < 1 else '❌ DESACORDO CRÍTICO'}
        """)

    except Exception as e:
        print(f"❌ Erro ao obter posições: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"❌ Erro de importação: {e}")

except Exception as e:
    print(f"❌ Erro crítico: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 120)
