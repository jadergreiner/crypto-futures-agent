"""
Demonstração e teste da reward function estendida vs baseline.

Executa scenario de teste para comparar rewards.
"""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.reward_extended import RewardCalculatorExtended


def scenario_1_winning_trade():
    """Scenario: Trade vencedor com recuperação rápida."""
    calc = RewardCalculatorExtended()

    capital_history = [
        1000.0, 1010.0, 1020.0, 1025.0, 1030.0, 1032.0, 1035.0,
        1031.0, 1025.0, 1020.0, 1045.0, 1050.0, 1055.0
    ]  # Queda, então recuperação

    returns_history = [0.01, 0.01, 0.005, 0.005, 0.002, 0.003, -0.004, -0.006, -0.005, 0.025, 0.005, 0.005]

    components = calc.calculate_reward_extended(
        traded=True,
        pnl=0.05,  # 5% de lucro
        capital_history=capital_history,
        returns_history=returns_history,
        action_valid=True,
    )

    return {
        "name": "Winning Trade with Quick Recovery",
        "pnl": 0.05,
        "components": components,
    }


def scenario_2_losing_trade():
    """Scenario: Trade perdedor."""
    calc = RewardCalculatorExtended()

    capital_history = [
        1000.0, 990.0, 980.0, 970.0, 965.0, 960.0, 950.0,
        940.0, 935.0, 930.0, 925.0, 920.0
    ]  # Drawdown contínuo

    returns_history = [-0.01, -0.01, -0.01, -0.005, -0.005, -0.01, -0.01, -0.005, -0.005, -0.005, -0.005]

    components = calc.calculate_reward_extended(
        traded=True,
        pnl=-0.08,  # -8% de perda
        capital_history=capital_history,
        returns_history=returns_history,
        action_valid=True,
    )

    return {
        "name": "Losing Trade",
        "pnl": -0.08,
        "components": components,
    }


def scenario_3_no_trade():
    """Scenario: Sem trade (stay out of market)."""
    calc = RewardCalculatorExtended()

    capital_history = [1000.0] * 10  # Capital congelado
    returns_history = [0.0] * 10  # Zero retorno

    components = calc.calculate_reward_extended(
        traded=False,
        pnl=0.0,
        capital_history=capital_history,
        returns_history=returns_history,
        action_valid=True,
    )

    return {
        "name": "No Trade (Stay Out in Volatility)",
        "pnl": 0.0,
        "components": components,
    }


def scenario_4_slow_recovery():
    """Scenario: Trade com recuperação lenta."""
    calc = RewardCalculatorExtended()

    capital_history = [
        1000.0, 950.0, 920.0, 900.0, 890.0, 880.0, 875.0,
        880.0, 890.0, 900.0, 920.0, 940.0, 960.0, 980.0,
        1000.0, 1020.0
    ]  # Recuperação lenta (muitos passos)

    # Retornos simulando recuperação gradual
    returns_history = list(np.diff(capital_history) / capital_history[:-1])

    components = calc.calculate_reward_extended(
        traded=True,
        pnl=-0.05,  # Perdeu 5% inicialmente
        capital_history=capital_history,
        returns_history=returns_history,
        action_valid=True,
    )

    return {
        "name": "Trade with Slow Recovery",
        "pnl": -0.05,
        "components": components,
    }


def main():
    """Executa cenários de teste e mostra comparações."""
    print("=" * 80)
    print("REWARD FUNCTION EXTENDED - SCENARIO TESTING")
    print("=" * 80)
    print()

    scenarios = [
        scenario_1_winning_trade(),
        scenario_2_losing_trade(),
        scenario_3_no_trade(),
        scenario_4_slow_recovery(),
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*80}")
        print(f"SCENARIO {i}: {scenario['name']}")
        print(f"{'='*80}")
        print(f"\nPnL: {scenario['pnl']:.2%}")
        print("\nReward Components:")
        for key, value in scenario["components"].items():
            if key in ['total', 'sharpe', 'max_dd_pct', 'recovery_steps']:
                if key == 'sharpe':
                    print(f"  {key:.<40} {value:.4f}")
                elif key == 'max_dd_pct':
                    print(f"  {key:.<40} {value:.2f}%")
                elif key == 'recovery_steps':
                    recovery_str = f"{int(value)} steps" if value > 0 else "not recovered"
                    print(f"  {key:.<40} {recovery_str}")
                else:
                    print(f"  {key:.<40} {value:.4f}")
            elif isinstance(value, float):
                print(f"  {key:.<40} {value:+.4f}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Comparação de totais
    print("\nTotal Reward Ranking:")
    sorted_scenarios = sorted(scenarios, key=lambda x: x["components"]["total"], reverse=True)
    for rank, scenario in enumerate(sorted_scenarios, 1):
        total = scenario["components"]["total"]
        print(f"  {rank}. {scenario['name']:<45} {total:+.4f}")

    # Exportar para JSON
    output = {
        "status": "ok",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenarios": scenarios,
        "weights_used": RewardCalculatorExtended().get_weights(),
    }

    output_file = REPO_ROOT / "results" / "model2" / "extended_reward_test.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    from datetime import datetime, timezone

    raise SystemExit(main())
