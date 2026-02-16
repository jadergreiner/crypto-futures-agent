"""
Script de demonstração das correções implementadas no reward calculator.
Mostra como o novo sistema incentiva deixar lucros correrem e cortar perdas rápido.
"""

from agent.reward import RewardCalculator


def print_separator():
    """Imprime separador visual."""
    print("=" * 80)


def demonstrate_hold_bonus():
    """Demonstra o novo hold bonus assimétrico."""
    print_separator()
    print("DEMONSTRAÇÃO 1: HOLD BONUS ASSIMÉTRICO")
    print_separator()
    print()
    
    calc = RewardCalculator()
    
    print("Cenário A: Posição lucrativa (+2%)")
    print("-" * 40)
    result = calc.calculate(
        position_state={'has_position': True, 'pnl_pct': 2.0},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_hold_bonus: {result['r_hold_bonus']:.4f}")
    print(f"  Peso: {calc.weights['r_hold_bonus']}")
    print(f"  Contribuição total: {result['r_hold_bonus'] * calc.weights['r_hold_bonus']:.4f}")
    print(f"  → INCENTIVA segurar posições lucrativas!")
    print()
    
    print("Cenário B: Posição com perda pequena (-0.3%)")
    print("-" * 40)
    result = calc.calculate(
        position_state={'has_position': True, 'pnl_pct': -0.3},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_hold_bonus: {result['r_hold_bonus']:.4f}")
    print(f"  Peso: {calc.weights['r_hold_bonus']}")
    print(f"  Contribuição total: {result['r_hold_bonus'] * calc.weights['r_hold_bonus']:.4f}")
    print(f"  → Sem penalidade (perda ainda pequena)")
    print()
    
    print("Cenário C: Posição com perda significativa (-1.5%)")
    print("-" * 40)
    result = calc.calculate(
        position_state={'has_position': True, 'pnl_pct': -1.5},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_hold_bonus: {result['r_hold_bonus']:.4f}")
    print(f"  Peso: {calc.weights['r_hold_bonus']}")
    print(f"  Contribuição total: {result['r_hold_bonus'] * calc.weights['r_hold_bonus']:.4f}")
    print(f"  → PENALIZA segurar posições perdedoras!")
    print()


def demonstrate_exit_quality():
    """Demonstra o novo componente r_exit_quality."""
    print_separator()
    print("DEMONSTRAÇÃO 2: QUALIDADE DA SAÍDA (r_exit_quality)")
    print_separator()
    print()
    
    calc = RewardCalculator()
    
    print("Cenário A: Fechar trade com R=2.0 (bom)")
    print("-" * 40)
    result = calc.calculate(
        trade_result={'pnl': 200, 'pnl_pct': 2.0, 'r_multiple': 2.0, 'exit_reason': 'take_profit'},
        position_state={'has_position': True},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_exit_quality: {result['r_exit_quality']:.4f}")
    print(f"  Peso: {calc.weights['r_exit_quality']}")
    print(f"  Contribuição total: {result['r_exit_quality'] * calc.weights['r_exit_quality']:.4f}")
    print(f"  → RECOMPENSA por bom R-multiple!")
    print()
    
    print("Cenário B: Stop loss com R=-0.5 (gestão de risco correta)")
    print("-" * 40)
    result = calc.calculate(
        trade_result={'pnl': -50, 'pnl_pct': -0.5, 'r_multiple': -0.5, 'exit_reason': 'stop_loss'},
        position_state={'has_position': True},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_exit_quality: {result['r_exit_quality']:.4f}")
    print(f"  Peso: {calc.weights['r_exit_quality']}")
    print(f"  Contribuição total: {result['r_exit_quality'] * calc.weights['r_exit_quality']:.4f}")
    print(f"  → SEM penalidade (stop loss = gestão de risco)")
    print()
    
    print("Cenário C: Manual close com R=-1.0 (fechar no prejuízo)")
    print("-" * 40)
    result = calc.calculate(
        trade_result={'pnl': -100, 'pnl_pct': -1.0, 'r_multiple': -1.0, 'exit_reason': 'manual_close'},
        position_state={'has_position': True},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_exit_quality: {result['r_exit_quality']:.4f}")
    print(f"  Peso: {calc.weights['r_exit_quality']}")
    print(f"  Contribuição total: {result['r_exit_quality'] * calc.weights['r_exit_quality']:.4f}")
    print(f"  → PENALIZA fechar manualmente no prejuízo!")
    print()


def demonstrate_inactivity_changes():
    """Demonstra as mudanças na penalidade de inatividade."""
    print_separator()
    print("DEMONSTRAÇÃO 3: PENALIDADE DE INATIVIDADE REDUZIDA")
    print_separator()
    print()
    
    calc = RewardCalculator()
    
    from agent.reward import INACTIVITY_THRESHOLD, INACTIVITY_PENALTY_RATE
    
    print(f"Configuração anterior:")
    print(f"  - Threshold: 10 steps (~40h)")
    print(f"  - Taxa: 0.02")
    print(f"  - Peso: 0.5")
    print()
    
    print(f"Configuração nova:")
    print(f"  - Threshold: {INACTIVITY_THRESHOLD} steps (~60h)")
    print(f"  - Taxa: {INACTIVITY_PENALTY_RATE}")
    print(f"  - Peso: {calc.weights['r_inactivity']}")
    print()
    
    print("Cenário: 20 steps sem posição")
    print("-" * 40)
    result = calc.calculate(
        position_state={'has_position': False, 'flat_steps': 20},
        portfolio_state={'total_capital': 10000.0}
    )
    print(f"  r_inactivity: {result['r_inactivity']:.4f}")
    print(f"  Contribuição total: {result['r_inactivity'] * calc.weights['r_inactivity']:.4f}")
    print(f"  → Penalidade mais branda, dá mais tempo ao agente")
    print()


def demonstrate_combined_scenario():
    """Demonstra cenário completo com múltiplos componentes."""
    print_separator()
    print("DEMONSTRAÇÃO 4: CENÁRIO COMPLETO")
    print_separator()
    print()
    
    calc = RewardCalculator()
    
    print("Situação: Trade fechado com R=2.5 após segurar posição lucrativa")
    print("-" * 40)
    result = calc.calculate(
        trade_result={'pnl': 250, 'pnl_pct': 2.5, 'r_multiple': 2.5, 'exit_reason': 'take_profit'},
        position_state={'has_position': True, 'pnl_pct': 2.5},
        portfolio_state={'total_capital': 10000.0}
    )
    
    print("\nComponentes de reward:")
    for key, value in result.items():
        if key != 'total' and value != 0:
            weight = calc.weights.get(key, 0)
            contribution = value * weight
            print(f"  {key:20s}: {value:7.4f} × {weight:3.1f} = {contribution:7.4f}")
    
    print(f"\n  {'TOTAL':20s}: {result['total']:7.4f}")
    print()
    print("✓ Agente foi recompensado por:")
    print("  - Segurar posição lucrativa (r_hold_bonus)")
    print("  - Fechar com bom R-multiple (r_exit_quality + r_pnl)")
    print("  - PnL não realizado positivo (r_unrealized)")
    print()


def main():
    """Executa todas as demonstrações."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "DEMONSTRAÇÃO: CORREÇÕES DO AGENTE RL" + " " * 27 + "║")
    print("║" + " " * 10 + "Incentivo para deixar lucros correrem e cortar perdas" + " " * 14 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    demonstrate_hold_bonus()
    demonstrate_exit_quality()
    demonstrate_inactivity_changes()
    demonstrate_combined_scenario()
    
    print_separator()
    print("RESUMO DAS MUDANÇAS")
    print_separator()
    print()
    print("✓ Hold bonus assimétrico: Incentiva segurar lucros, cortar perdas")
    print("✓ r_exit_quality: Recompensa bons R-multiples, penaliza fechamentos ruins")
    print("✓ Inatividade reduzida: Mais tempo para o agente encontrar setups")
    print("✓ Pesos ajustados: Prioriza qualidade sobre quantidade de operações")
    print()
    print("Resultado esperado:")
    print("  → Profit Factor > 1.0")
    print("  → Avg R-Multiple > 0")
    print("  → Win Rate mantido ~50%")
    print()


if __name__ == "__main__":
    main()
