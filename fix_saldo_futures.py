#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Solução: Recuperar saldo de Futures corretamente"""

from data.binance_client import create_binance_client
import json

try:
    print("\n" + "=" * 70)
    print("OBTENDO SALDO REAL DE FUTURES")
    print("=" * 70 + "\n")

    client = create_binance_client('live')

    # ============================================================
    # Tentar obter dados brutos da API response
    # ============================================================
    print("[1/2] Testando get account info via method direto...")

    try:
        # Chamar o método que retorna response bruta
        response = client.rest_api.account_information_v3()

        # Tentar obter dados brutos dentro do ApiResponse object
        print(f"  Response type: {type(response)}")
        print(f"  Response.__dict__ keys: {list(vars(response).keys())}\n")

        # O objeto ApiResponse tem um método especial para desserializar?
        if hasattr(response, 'data'):
            print(f"  ✅ Encontrado 'data': {response.data}\n")

        # Ou talvez tenha já os dados como atributo?
        response_dict = vars(response)
        for key, value in response_dict.items():
            if isinstance(value, dict) and 'totalWalletBalance' in str(value):
                print(f"  ✅ Encontrado em {key}: {value}\n")

        print("Tentando alternativa: verificar se response tem método __str__ útil...")
        print(f"  str(response)[:200]: {str(response)[:200]}\n")

    except Exception as e:
        print(f"  ❌ Erro: {str(e)}\n")

    # ============================================================
    # Tentar usar um método que NÃO precisa de timestamp
    # ============================================================
    print("[2/2] Testando market data (não precisa timestamp rigoroso)...")

    try:
        # mark_price não precisa de assinatura, então não tem erro de timestamp
        mark_price = client.rest_api.mark_price('BTCUSDT')

        mark_dict = vars(mark_price) if hasattr(mark_price, '__dict__') else mark_price
        print(f"  ✅ Mark price BTCUSDT:")
        for key, val in mark_dict.items():
            if not callable(val) and not key.startswith('_'):
                print(f"    {key}: {val}")

    except Exception as e:
        print(f"  ❌ Erro: {str(e)}\n")

    print("\n" + "=" * 70)
    print("RESULTADO:")
    print("=" * 70)
    print("""
Problema identificado:
  1. API response retorna objeto genérico sem dados deserializados
  2. Timestamp está desincronizado (1s de diferença)

SOLUÇÕES:
  A) Sincronizar relógio do sistema (Windows):
     - Settings → Time & Language → Sync now
     - Ou: ntpdate server (terminal admin)

  B) Usar método que não precisa timestamp rigoroso:
     - Usar dados de mark_price + posições abertas
     - Calcular saldo baseado em posições

Qual quer que eu implemente primeiro?
    """)

except Exception as e:
    print(f"ERRO: {str(e)}")
    import traceback
    traceback.print_exc()
