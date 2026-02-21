#!/usr/bin/env python3
"""
Mock Revalidation Test — Simula modelo treinado + 6 risk gates

Objetivo:
- Simular backtest com modelo fictício
- Calcular 6 gates com números realistas
- Validar decision logic (GO/PARTIAL/NO-GO)
- Testar report generation

Executar: python scripts/test_revalidation_mock.py

Saída: Decision (GO/PARTIAL/NO-GO) + relatório com 6 gates
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List
import numpy as np

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class MockRevalidationValidator:
    """Simula revalidação do modelo treinado."""

    # Risk Clearance Gates (da backtest_metrics.py)
    SHARPE_MIN = 1.0
    MAX_DD_MAX = 15.0
    WIN_RATE_MIN = 45.0
    PROFIT_FACTOR_MIN = 1.5
    CONSECUTIVE_LOSSES_MAX = 5
    CALMAR_MIN = 2.0

    def __init__(self):
        """Inicializa mock validator."""
        logger.info("Mock Revalidation Validator initialized")
        self.results_dir = Path("reports/revalidation")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def simulate_backtest(self, scenario: str = "realistic") -> Dict[str, Any]:
        """
        Simula backtest com modelo treinado.

        Args:
            scenario: Tipo de simulação
              - "realistic": Modelo com convergência parcial
              - "good": Modelo bem treinado (pass 6/6)
              - "bad": Modelo não convergiram (fail 2/6)

        Returns:
            Dict com métricas do backtest
        """
        logger.info(f"Simulating backtest scenario: {scenario}")

        if scenario == "realistic":
            # F-12 baseline: 2/6 gates passed
            metrics = {
                "sharpe_ratio": 0.45,           # ❌ Need >= 1.0
                "max_drawdown_pct": 18.5,       # ❌ Need <= 15.0%
                "win_rate_pct": 51.2,           # ✅ Need >= 45.0%
                "profit_factor": 1.22,          # ❌ Need >= 1.5
                "consecutive_losses": 4,        # ✅ Need <= 5
                "calmar_ratio": 0.08,           # ❌ Need >= 2.0
                "total_trades": 47,
                "winning_trades": 24,
                "losing_trades": 23,
                "avg_win_pct": 2.3,
                "avg_loss_pct": -1.8,
                "total_return_pct": 15.6,
                "periods": 500_000
            }

        elif scenario == "good":
            # Modelo bem treinado (6/6 gates)
            metrics = {
                "sharpe_ratio": 1.45,           # ✅ >= 1.0
                "max_drawdown_pct": 12.3,       # ✅ <= 15.0%
                "win_rate_pct": 58.5,           # ✅ >= 45.0%
                "profit_factor": 2.15,          # ✅ >= 1.5
                "consecutive_losses": 3,        # ✅ <= 5
                "calmar_ratio": 3.2,            # ✅ >= 2.0
                "total_trades": 54,
                "winning_trades": 31,
                "losing_trades": 23,
                "avg_win_pct": 3.1,
                "avg_loss_pct": -1.5,
                "total_return_pct": 35.2,
                "periods": 500_000
            }

        elif scenario == "bad":
            # Modelo não convergiu (< 2/6 gates)
            metrics = {
                "sharpe_ratio": 0.15,           # ❌
                "max_drawdown_pct": 28.5,       # ❌
                "win_rate_pct": 42.1,           # ❌
                "profit_factor": 0.95,          # ❌
                "consecutive_losses": 7,        # ❌
                "calmar_ratio": 0.03,           # ❌
                "total_trades": 38,
                "winning_trades": 16,
                "losing_trades": 22,
                "avg_win_pct": 1.8,
                "avg_loss_pct": -2.2,
                "total_return_pct": -8.3,
                "periods": 500_000
            }

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        return metrics

    def validate_gates(self, metrics: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Valida 6 risk gates.

        Args:
            metrics: Métricas do backtest

        Returns:
            (gates_passed, list of gate results)
        """
        gates = []
        passed_count = 0

        # Gate 1: Sharpe Ratio
        gate_1 = {
            "name": "Sharpe Ratio",
            "value": metrics["sharpe_ratio"],
            "threshold": self.SHARPE_MIN,
            "passed": metrics["sharpe_ratio"] >= self.SHARPE_MIN,
            "requirement": f">= {self.SHARPE_MIN}"
        }
        gates.append(gate_1)
        if gate_1["passed"]:
            passed_count += 1

        # Gate 2: Max Drawdown
        gate_2 = {
            "name": "Max Drawdown",
            "value": metrics["max_drawdown_pct"],
            "threshold": self.MAX_DD_MAX,
            "passed": metrics["max_drawdown_pct"] <= self.MAX_DD_MAX,
            "requirement": f"<= {self.MAX_DD_MAX}%",
            "unit": "%"
        }
        gates.append(gate_2)
        if gate_2["passed"]:
            passed_count += 1

        # Gate 3: Win Rate
        gate_3 = {
            "name": "Win Rate",
            "value": metrics["win_rate_pct"],
            "threshold": self.WIN_RATE_MIN,
            "passed": metrics["win_rate_pct"] >= self.WIN_RATE_MIN,
            "requirement": f">= {self.WIN_RATE_MIN}%",
            "unit": "%"
        }
        gates.append(gate_3)
        if gate_3["passed"]:
            passed_count += 1

        # Gate 4: Profit Factor
        gate_4 = {
            "name": "Profit Factor",
            "value": metrics["profit_factor"],
            "threshold": self.PROFIT_FACTOR_MIN,
            "passed": metrics["profit_factor"] >= self.PROFIT_FACTOR_MIN,
            "requirement": f">= {self.PROFIT_FACTOR_MIN}"
        }
        gates.append(gate_4)
        if gate_4["passed"]:
            passed_count += 1

        # Gate 5: Consecutive Losses
        gate_5 = {
            "name": "Consecutive Losses",
            "value": metrics["consecutive_losses"],
            "threshold": self.CONSECUTIVE_LOSSES_MAX,
            "passed": metrics["consecutive_losses"] <= self.CONSECUTIVE_LOSSES_MAX,
            "requirement": f"<= {self.CONSECUTIVE_LOSSES_MAX}"
        }
        gates.append(gate_5)
        if gate_5["passed"]:
            passed_count += 1

        # Gate 6: Calmar Ratio
        gate_6 = {
            "name": "Calmar Ratio",
            "value": metrics["calmar_ratio"],
            "threshold": self.CALMAR_MIN,
            "passed": metrics["calmar_ratio"] >= self.CALMAR_MIN,
            "requirement": f">= {self.CALMAR_MIN}"
        }
        gates.append(gate_6)
        if gate_6["passed"]:
            passed_count += 1

        return passed_count, gates

    def make_decision(self, passed_count: int) -> str:
        """
        Toma decisão baseada em gates passados.

        Args:
            passed_count: Número de gates passados (0-6)

        Returns:
            Decision: "GO" / "PARTIAL" / "NO-GO"
        """
        if passed_count >= 6:
            return "GO"
        elif passed_count >= 4:
            return "PARTIAL"
        else:
            return "NO-GO"

    def generate_report(self, scenario: str = "realistic") -> Dict[str, Any]:
        """
        Gera relatório completo de revalidação.

        Args:
            scenario: Tipo de simulação

        Returns:
            Relatório com todos os detalhes
        """
        logger.info(f"Generating revalidation report for scenario: {scenario}")

        # 1. Simulate backtest
        metrics = self.simulate_backtest(scenario=scenario)

        # 2. Validate gates
        passed_count, gates = self.validate_gates(metrics)

        # 3. Make decision
        decision = self.make_decision(passed_count)

        # 4. Build report
        report = {
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario,
            "decision": decision,
            "gates_passed": f"{passed_count}/6",
            "metrics": metrics,
            "gates": gates,
            "summary": {
                "total_trades": metrics["total_trades"],
                "winning_trades": metrics["winning_trades"],
                "losing_trades": metrics["losing_trades"],
                "total_return_pct": metrics["total_return_pct"]
            }
        }

        return report

    def save_report(self, report: Dict[str, Any]) -> Path:
        """Salva relatório em arquivo."""
        filename = f"revalidation_{report['scenario']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.results_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved: {filepath}")
        return filepath

    def print_report(self, report: Dict[str, Any]) -> None:
        """Imprime relatório formatado."""
        print("\n" + "=" * 80)
        print(f"  REVALIDATION REPORT — {report['scenario'].upper()}")
        print("=" * 80)

        print(f"\nDECISION: {report['decision']}")
        print(f"Gates passed: {report['gates_passed']}\n")

        print("Risk Gates:")
        print("-" * 80)
        for i, gate in enumerate(report['gates'], 1):
            status = "✅ PASS" if gate['passed'] else "❌ FAIL"
            value_str = f"{gate['value']}"
            if "unit" in gate:
                value_str += gate["unit"]
            req_str = gate['requirement']
            print(f"  {i}. {gate['name']:<20} {status:<10} {value_str:<15} ({req_str})")

        print("\n" + "-" * 80)
        summary = report['summary']
        print(f"Backtest Summary:")
        print(f"  Total trades: {summary['total_trades']}")
        print(f"  Winning trades: {summary['winning_trades']}")
        print(f"  Losing trades: {summary['losing_trades']}")
        print(f"  Total return: {summary['total_return_pct']}%")

        print("\n" + "=" * 80)

        if report['decision'] == "GO":
            print("✅ DECISION: GO — Model meets all risk gates. Ready for deployment.")
        elif report['decision'] == "PARTIAL":
            print("⚠️  DECISION: PARTIAL — Model passes 4-5 gates, needs CTO review.")
        else:
            print("❌ DECISION: NO-GO — Model fails risk gates, needs retraining.")

        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test revalidation mock")
    parser.add_argument("--scenario", type=str, default="realistic",
                       choices=["realistic", "good", "bad"],
                       help="Simulation scenario")
    parser.add_argument("--save", action="store_true", help="Save report to file")
    args = parser.parse_args()

    validator = MockRevalidationValidator()

    # Test all scenarios
    scenarios_to_test = [args.scenario] if args.scenario != "realistic" else ["realistic", "good", "bad"]

    all_passed = True
    for scenario in scenarios_to_test:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing scenario: {scenario}")
        logger.info(f"{'='*80}")

        report = validator.generate_report(scenario=scenario)

        # Validar decision está correto
        expected_decision_map = {
            "realistic": "NO-GO",  # 2/6 gates
            "good": "GO",          # 6/6 gates
            "bad": "NO-GO"         # 0/6 gates
        }
        expected_decision = expected_decision_map[scenario]

        if report['decision'] != expected_decision:
            logger.error(f"❌ Unexpected decision for {scenario}: "
                        f"got {report['decision']}, expected {expected_decision}")
            all_passed = False
        else:
            logger.info(f"✅ Decision correct for {scenario}: {report['decision']}")

        # Print and save
        validator.print_report(report)
        if args.save:
            validator.save_report(report)

    if all_passed:
        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("=" * 80)
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 80)
        logger.error("❌ SOME TESTS FAILED")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
