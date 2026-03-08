#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 - Registro de Autorização de Risco Alto
Registra a decisão do usuário de iniciar com riscos elevados
"""

import json
from datetime import datetime

def main():
    print("\n" + "=" * 80)
    print("PHASE 2 - REGISTRO DE AUTORIZAÇÃO DE RISCO ALTO")
    print("=" * 80)
    print()

    # Estado conhecido da conta
    account_state = {
        'total_balance': 413.38,
        'available': 157.38,
        'unrealized_pnl': -192.68,
        'margin_used': 63.21,
        'drawdown_pct': -46.61,
        'positions_open': 20,
        'circuit_breaker_target': -3.0,
        'circuit_breaker_status': 'DISPARADO',
    }

    print("📊 ESTADO DA CONTA CONFIRMADO:")
    print("-" * 80)
    for key, value in account_state.items():
        if isinstance(value, float):
            print(f"  {key:.<40} ${value:>10.2f}")
        else:
            print(f"  {key:.<40} {value:>10}")
    print()

    print("⚠️  RISCOS ACEITOS:")
    print("-" * 80)
    print("  ✓ Drawdown em -46.61% (43.61 pontos acima do limite -3%)")
    print("  ✓ 20 posições abertas em múltiplos altcoins")
    print("  ✓ Posições com baixa liquidez (BROCCOLI, PTBUSDT, etc)")
    print("  ✓ Circuit breaker DISPARADO (bloqueará novas ordens)")
    print("  ✓ Risco de liquidação em cascata")
    print()

    # Criar autorização
    authorization = {
        'timestamp': datetime.utcnow().isoformat(),
        'phase': 'PHASE_2',
        'status': 'AUTHORIZED_HIGH_RISK',
        'decision': 'CONTINUAR_MESMO_COM_RISCOS',
        'user_choice': 'C',
        'risks_acknowledged': [
            'Drawdown crítico (-46.61%)',
            'Circuit breaker disparado',
            'Posições abertas (20)',
            'Altcoins de baixa liquidez',
        ],
        'protections_active': [
            'Risk Gate (bloqueia se drawdown < -3%)',
            'Stop Loss (reduz 50% em perda)',
            'Confluence mínima (3.0)',
            'Confidence > 70%',
            'Circuit Breaker monitorado',
        ],
        'account_state': account_state,
        'next_step': 'Executar: .\\iniciar.bat → Opção 2 → Confirmar SIM + INICIO',
    }

    # Salvar autorização
    auth_file = f"PHASE2_AUTORIZADO_RISCO_ALTO_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(auth_file, 'w') as f:
        json.dump(authorization, f, indent=2, default=str)

    print("=" * 80)
    print("✅ AUTORIZAÇÃO REGISTRADA")
    print("=" * 80)
    print(f"Arquivo: {auth_file}")
    print()

    print("🚀 PRÓXIMOS PASSOS PARA INICIAR PHASE 2:")
    print("-" * 80)
    print()
    print("  1. ABRA um terminal PowerShell no repositório")
    print()
    print("  2. EXECUTE:")
    print("     .\\iniciar.bat")
    print()
    print("  3. NO MENU, ESCOLHA:")
    print("     2 (OPERACAO PADRAO - INICIAR AGENTE LIVE COM TREINAMENTO)")
    print()
    print("  4. CONFIRME DUAS VEZES:")
    print("     [1/2] Os orders são REAIS? Digite 'SIM': SIM")
    print("     [2/2] Você é o operador autorizado? Digite 'INICIO': INICIO")
    print()
    print("  5. SISTEMA INICIARÁ EM MODO LIVE")
    print("     Monitoramento: Tenha o painel_dashboard.html aberto")
    print()

    print("=" * 80)
    print("⚠️  ADVERTÊNCIA FINAL")
    print("=" * 80)
    print()
    print("  RISCO: Seu portfólio pode ser LIQUIDADO se drawdown piorar")
    print("  PROTEÇÃO: Risk gates bloquearão posições novas se < -3%")
    print("  MONITORAMENTO: Você DEVE acompanhar em tempo real")
    print()
    print("  Todos os sinais gerados terão:")
    print("    - Stop Loss obrigatório (reduz 50% em perda)")
    print("    - Confidence > 70% (apenas sinais fortes)")
    print("    - Confluence ≥ 3.0 (multi-timeframe validado)")
    print()
    print("=" * 80)
    print()

    return True


if __name__ == "__main__":
    main()
