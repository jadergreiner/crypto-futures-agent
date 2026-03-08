#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnóstico: Por que API não está vendo o saldo de Futures?"""

import json
from data.binance_client import create_binance_client

try:
    print("\n" + "=" * 70)
    print("DIAGNOSTICO DETALHADO - SALDO FUTURES NAO APARECENDO")
    print("=" * 70 + "\n")

    client = create_binance_client('live')

    # ============================================================
    # 1. Testar método account_information_v3()
    # ============================================================
    print("[1/3] Testando account_information_v3()...")
    try:
        response = client.rest_api.account_information_v3()
        print(f"  Tipo: {type(response)}")
        print(f"  Atributos: {dir(response)[:5]}")

        # Tentar acessar como dict
        if hasattr(response, '_data_function'):
            print(f"  Tem _data_function: {response._data_function}")
        if hasattr(response, 'headers'):
            print(f"  Headers: {response.headers}")
        if hasattr(response, 'status'):
            print(f"  Status: {response.status}")

        print("  ⚠️  Resposta incompleta/vazia\n")
    except Exception as e:
        print(f"  ❌ ERRO: {str(e)}\n")

    # ============================================================
    # 2. Testar method futures_account_balance_v3()
    # ============================================================
    print("[2/3] Testando futures_account_balance_v3()...")
    try:
        balance = client.rest_api.futures_account_balance_v3()
        print(f"  Tipo: {type(balance)}")

        # Converter para dict se possível
        if isinstance(balance, list):
            print(f"  ✅ Retornou LISTA com {len(balance)} items")
            if balance:
                for idx, item in enumerate(balance[:3]):
                    print(f"    Item {idx}: {item}")
        elif hasattr(balance, '__dict__'):
            balance_dict = vars(balance)
            print(f"  ✅ Retornou OBJETO com chaves:")
            for key in list(balance_dict.keys())[:10]:
                value = balance_dict[key]
                if isinstance(value, (str, int, float, bool, type(None))):
                    print(f"    - {key}: {value}")
                else:
                    print(f"    - {key}: {type(value).__name__}")
        else:
            print(f"  Resposta: {balance}\n")

    except Exception as e:
        print(f"  ❌ ERRO: {str(e)}\n")

    # ============================================================
    # 3. Testar position_information_v3()
    # ============================================================
    print("[3/3] Testando position_information_v3()...")
    try:
        positions = client.rest_api.position_information_v3()
        print(f"  Tipo: {type(positions)}")

        if isinstance(positions, list):
            print(f"  ✅ Retornou LISTA com {len(positions)} posições")
            if positions:
                for idx, pos in enumerate(positions[:2]):
                    print(f"    Posição {idx}: {pos}")
        else:
            print(f"  Resposta: {positions}\n")

    except Exception as e:
        print(f"  ❌ ERRO: {str(e)}\n")

    # ============================================================
    # CONCLUSÃO
    # ============================================================
    print("\n" + "=" * 70)
    print("PROXIMOS PASSOS:")
    print("=" * 70)
    print("""
Se acima viu dados de saldo/posição sendo retornados:
  → Problema é no PARSING (como extrair os dados da resposta)
  → Preciso ajustar phase2_retrieve_data.py para usar o método correto

Se continuou retornando vazio/None:
  → As credenciais podem estar para SPOT, não FUTURES
  → Ou API credentials não têm permissão para ler Futures account
  → Verifique em: https://app.binance.com/en/user/setting/manage-api

Compartilhe a saída acima para que eu ajuste!
    """)

except Exception as e:
    print(f"ERRO GERAL: {str(e)}")
    import traceback
    traceback.print_exc()
