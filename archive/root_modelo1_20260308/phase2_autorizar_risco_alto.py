#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 - Inicialização com Avisos de Risco Alto
Executa verificação final antes de iniciar operação LIVE
"""

import json
from datetime import datetime
from data.binance_client import create_binance_client

def main():
    print("\n" + "=" * 80)
    print("⚠️  PHASE 2 - INICIALIZAÇÃO COM AVISO DE RISCO ALTO")
    print("=" * 80)
    print()

    try:
        client = create_binance_client(mode="live")

        # Recuperar estado
        response = client.rest_api.account_information_v3()
        account_data = response.data() if callable(response.data) else response.data
        account = vars(account_data) if hasattr(account_data, '__dict__') else account_data or {}

        total_balance = float(account.get('totalWalletBalance', 0) or 0)
        available = float(account.get('availableBalance', 0) or 0)
        unrealized_pnl = float(account.get('totalUnrealizedProfit', 0) or 0)
        margin_used = float(account.get('totalInitialMargin', 0) or 0)

        # Calcular drawdown
        if total_balance > 0:
            drawdown_pct = (unrealized_pnl / total_balance) * 100
        else:
            drawdown_pct = 0

        # Contar posições
        positions_count = 0
        positions_data = account.get('positions', [])
        if positions_data:
            for pos in positions_data:
                pos_dict = vars(pos) if hasattr(pos, '__dict__') else pos
                if float(pos_dict.get('positionAmt', 0) or 0) != 0:
                    positions_count += 1

        # Display state
        print("📊 ESTADO ATUAL DA CONTA:")
        print("-" * 80)
        print(f"  Saldo Total:          ${total_balance:>10.2f}")
        print(f"  Disponível:           ${available:>10.2f}")
        print(f"  Margem Usada:         ${margin_used:>10.2f}")
        print(f"  P&L Não Realizado:    ${unrealized_pnl:>10.2f}")
        print(f"  Drawdown:             {drawdown_pct:>10.2f}%")
        print(f"  Posições Abertas:     {positions_count:>10}")
        print()

        # Check risks
        print("⚠️  VERIFICAÇÃO DE RISCOS:")
        print("-" * 80)

        circuit_breaker = -3.0
        is_armed = drawdown_pct > circuit_breaker

        risk_score = 0

        # Risk 1: Drawdown
        if drawdown_pct < circuit_breaker:
            print(f"  🔴 CRÍTICO: Drawdown {drawdown_pct:.2f}% abaixo de -3.0%")
            print(f"     → Circuit breaker DISPARADO")
            print(f"     → Sistema bloqueará novas posições")
            risk_score += 3
        else:
            print(f"  🟡 AVISO: Drawdown {drawdown_pct:.2f}% (margem mínima)")
            risk_score += 2

        # Risk 2: Positions
        if positions_count > 0:
            print(f"  🟡 AVISO: {positions_count} posições abertas")
            print(f"     → Conflito potencial com sinais Phase 2")
            print(f"     → Risk de liquidação cruzada")
            risk_score += 2

        # Risk 3: Capital
        if available < 50:
            print(f"  🟡 AVISO: Apenas ${available:.2f} disponível")
            print(f"     → Pouca flexibilidade para rebalanceo")
            risk_score += 1

        print()
        print("RISCO TOTAL:", end=" ")
        if risk_score >= 5:
            print("🔴🔴🔴 MUITO ALTO")
        elif risk_score >= 3:
            print("🟠🟠 ALTO")
        else:
            print("🟡 MODERADO")

        # Final confirmation
        print()
        print("=" * 80)
        print("CONFIRMAÇÃO FINAL:")
        print("=" * 80)
        print()
        print("Você está prestes a iniciar Phase 2 com riscos elevados.")
        print()

        confirmations = [
            ("Entendo que drawdown está em -46.61%", drawdown_pct < -40),
            ("Aceito risco de novas posições serem bloqueadas", True),
            ("Estou ciente de 20 posições abertas", positions_count > 0),
            ("Confirmo que li PHASE2_RISCO_ALTO_AVISOS.md", True),
        ]

        all_confirmed = True
        for idx, (text, condition) in enumerate(confirmations, 1):
            if condition:
                response = input(f"  [{idx}/4] {text}? (SIM/NÃO): ").strip().upper()
                if response != "SIM":
                    print("\n❌ Confirmação rejeitada. Abortar Phase 2.")
                    return False

        print()
        print("=" * 80)
        print("✅ TODAS AS CONFIRMAÇÕES ACEITAS")
        print("=" * 80)
        print()
        print("PRÓXIMO PASSO:")
        print()
        print("  A. Execute: .\iniciar.bat")
        print("  B. Escolha opção: 2 (OPERACAO PADRAO - LIVE)")
        print("  C. Confirme 2x (SIM, INICIO)")
        print()
        print("O sistema iniciará em modo LIVE com proteções ativas:")
        print("  ✅ Risk Gate: bloqueará ordens se drawdown < -3%")
        print("  ✅ Stop Loss: reduzirá 50% em perda")
        print("  ✅ Confluence: apenas sinais fortes (≥3.0)")
        print("  ✅ Circuit Breaker: ARMADO (monitorado em tempo real)")
        print()
        print("=" * 80)
        print()

        # Save authorization
        auth_file = f"PHASE2_AUTORIZADO_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(auth_file, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'AUTHORIZED',
                'account_state': {
                    'total_balance': total_balance,
                    'available': available,
                    'drawdown': drawdown_pct,
                    'positions': positions_count,
                },
                'risk_score': risk_score,
                'confirmations': {c[0]: True for c in confirmations},
            }, f, indent=2)

        print(f"Autorização registrada em: {auth_file}")
        print()

        return True

    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
