#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnóstico: Por que a conta está vazia?"""

from data.binance_client import create_binance_client

try:
    print("\n[DIAGNOSTICO] Analisando conta Binance...\n")

    client = create_binance_client('live')

    # Recupera informações completas
    account = client.rest_api.account_information_v3()

    # Converter para dict
    if hasattr(account, '__dict__'):
        acc_dict = vars(account)
    else:
        acc_dict = account if isinstance(account, dict) else {}

    # Mostrar estrutura
    print("Chaves disponíveis na resposta:")
    for key in sorted(acc_dict.keys())[:20]:
        print(f"  - {key}")

    print("\n" + "=" * 70)
    print("VALORES PRINCIPAIS:")
    print("=" * 70)

    total_wallet = acc_dict.get('totalWalletBalance') or acc_dict.get('total_wallet_balance')
    available = acc_dict.get('availableBalance') or acc_dict.get('available_balance')
    uid = acc_dict.get('uid')
    can_trade = acc_dict.get('canTrade') or acc_dict.get('can_trade')

    print(f"UID da Conta: {uid}")
    print(f"Total Wallet Balance: {total_wallet}")
    print(f"Available Balance: {available}")
    print(f"Can Trade: {can_trade}")

    print("\n" + "=" * 70)
    print("DIAGNOSTICO:")
    print("=" * 70)

    if total_wallet == 0 or total_wallet == '0' or total_wallet is None:
        print("\n❌ SALDO ZERADO - Possíveis motivos:")
        print("  1. Credenciais API apontam para conta TESTNET (não live)")
        print("  2. Credenciais API apontam para conta live MAS sem capital")
        print("  3. API credentials estão erradas/inválidas")
        print("  4. Conta foi resetada/deletada")

        print("\n✅ SOLUÇÕES:")
        print("  - Verifique se .env tem BINANCE_API_KEY e SECRET CORRETOS")
        print("  - Teste em: https://testnet.binancefuture.com (credentials testnet)")
        print("  - Para live: use credentials da conta com capital")
    else:
        print(f"\n✅ CONTA COM CAPITAL: ${total_wallet:.2f}")

except Exception as e:
    print(f"ERRO na conexão: {str(e)}")
    import traceback
    traceback.print_exc()
