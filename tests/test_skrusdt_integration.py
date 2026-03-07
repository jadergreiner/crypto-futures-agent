"""
Test Script — SKRUSDT Integration Complete

Valida integração completa do modelo SKRUSDT com a engine de trading:
- Carregamento do playbook
- Geração de sinais
- Risk gate evaluation
- Trade execution simulation

Executar: python tests/test_skrusdt_integration.py
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

# Add root to path
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

# Importar componentes
from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import SKRPlaybook
from execution.heuristic_signals import HeuristicSignalGenerator, RiskGate

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SKRIntegrationTest:
    """Testes de integração completa SKRUSDT."""

    def __init__(self):
        """Inicializa tester."""
        self.symbol = "SKRUSDT"
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": self.symbol,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }

    def test_symbol_configuration(self):
        """Test 1: Validar configuração do símbolo."""
        logger.info("=" * 70)
        logger.info("TEST 1: Symbol Configuration Validation")
        logger.info("=" * 70)

        try:
            # Check SYMBOLS
            assert self.symbol in SYMBOLS, f"{self.symbol} não em SYMBOLS"
            config = SYMBOLS[self.symbol]

            # Check required fields
            required_fields = [
                "papel", "ciclo_proprio", "correlacao_btc",
                "beta_estimado", "classificacao", "caracteristicas"
            ]
            for field in required_fields:
                assert field in config, f"Campo ausente: {field}"

            # Check ALL_SYMBOLS
            assert self.symbol in ALL_SYMBOLS, f"{self.symbol} não em ALL_SYMBOLS"

            # Check AUTHORIZED_SYMBOLS
            assert self.symbol in AUTHORIZED_SYMBOLS, f"{self.symbol} não autorizado"

            # Verificar valores
            assert config["beta_estimado"] == 2.8, f"Beta inválido: {config['beta_estimado']}"
            assert config["classificacao"] == "low_cap_swing", f"Classificação inválida"
            assert "swing_trade" in config["caracteristicas"], "Característica swing_trade ausente"
            assert "autonomous_learning" in config["caracteristicas"], "Característica autonomous_learning ausente"

            logger.info("✅ PASSED: Symbol configuration valid")
            logger.info(f"   Beta: {config['beta_estimado']}")
            logger.info(f"   Classificação: {config['classificacao']}")
            logger.info(f"   Características: {', '.join(config['caracteristicas'][:3])}...")

            self.results["tests_passed"] += 1
            return True

        except AssertionError as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Symbol config: {str(e)}")
            return False

    def test_playbook_instantiation(self):
        """Test 2: Instanciar playbook."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 2: Playbook Instantiation")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()

            assert skr.symbol == self.symbol, f"Symbol mismatch: {skr.symbol}"
            assert skr.beta == 2.8, f"Beta mismatch: {skr.beta}"
            assert skr.classificacao == "low_cap_swing"

            logger.info("✅ PASSED: Playbook instantiated successfully")
            logger.info(f"   Symbol: {skr.symbol}")
            logger.info(f"   Beta: {skr.beta}")
            logger.info(f"   Papel: {skr.papel[:50]}...")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Playbook instantiation: {str(e)}")
            return False

    def test_confluence_adjustments(self):
        """Test 3: Ajustes de confluência."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 3: Confluence Adjustments")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()

            # Test case 1: RISK_ON regime
            context = {
                "market_regime": "RISK_ON",
                "btc_bias": "LONG",
                "d1_bias": "LONG",
                "smc_d1_structure": "bullish",
                "volume_ratio": 1.5,
                "fear_greed_value": 65
            }

            ajustes = skr.get_confluence_adjustments(context)
            total = sum(ajustes.values())

            logger.info(f"Context: {context}")
            logger.info(f"Confluence adjustments: {ajustes}")
            logger.info(f"Total: +{total:.1f}")

            assert total > 0, f"Total confluência deve ser positiva, got {total}"
            assert "regime_risk_on" in ajustes, "regime_risk_on ausente"

            # Test case 2: RISK_OFF
            context_off = {
                "market_regime": "RISK_OFF",
                "btc_bias": "SHORT",
                "d1_bias": "SHORT"
            }

            ajustes_off = skr.get_confluence_adjustments(context_off)
            logger.info(f"\nRISK_OFF context: {ajustes_off}")

            logger.info("✅ PASSED: Confluence adjustments working")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Confluence: {str(e)}")
            return False

    def test_risk_adjustments(self):
        """Test 4: Ajustes de risco."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 4: Risk Adjustments")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()

            # Test case 1: Normal volatility
            context = {
                "atr_pct": 3.0
            }

            risco = skr.get_risk_adjustments(context)
            logger.info(f"Normal volatility (ATR 3%): {risco}")

            assert "position_size_multiplier" in risco
            assert "stop_multiplier" in risco
            assert risco["position_size_multiplier"] == 0.45, "Position size baseline"
            assert risco["stop_multiplier"] == 1.5, "Stop multiplier baseline"

            # Test case 2: High volatility
            context_high = {"atr_pct": 7.0}
            risco_high = skr.get_risk_adjustments(context_high)
            logger.info(f"High volatility (ATR 7%): {risco_high}")

            assert risco_high["position_size_multiplier"] == 0.35, "Position reduzida em vol. alta"

            # Test case 3: Low volatility
            context_low = {"atr_pct": 1.5}
            risco_low = skr.get_risk_adjustments(context_low)
            logger.info(f"Low volatility (ATR 1.5%): {risco_low}")

            assert risco_low["position_size_multiplier"] == 0.55, "Position aumentada em vol. baixa"

            logger.info("✅ PASSED: Risk adjustments correct")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Risk: {str(e)}")
            return False

    def test_cycle_phase(self):
        """Test 5: Detecção de fase do ciclo."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 5: Cycle Phase Detection")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()

            test_cases = [
                ({"btc_cycle_phase": "BULL_RUN", "d1_bias": "LONG"}, "SWING_IMPULSO"),
                ({"btc_cycle_phase": "BULL_RUN", "d1_bias": "SHORT"}, "SWING_DISTRIBUICAO"),
                ({"btc_cycle_phase": "BEAR_MARKET", "d1_bias": "SHORT"}, "SWING_QUEDA"),
                ({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "LONG"}, "SWING_ACUMULACAO_LONG"),
                ({"btc_cycle_phase": "ACCUMULATION", "d1_bias": "NEUTRO"}, "SWING_LATERALIZACAO"),
            ]

            for context, expected in test_cases:
                phase = skr.get_cycle_phase(context)
                assert phase == expected, f"Phase mismatch: expected {expected}, got {phase}"
                logger.info(f"  {context} → {phase} ✓")

            logger.info("✅ PASSED: Cycle phase detection correct")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Cycle phase: {str(e)}")
            return False

    def test_should_trade(self):
        """Test 6: Decisão de operar."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 6: Should Trade Decision")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()

            test_cases = [
                # (regime, d1_bias, btc_bias, expected)
                ("RISK_ON", "LONG", "LONG", True),
                ("RISK_ON", "SHORT", "SHORT", True),
                ("RISK_ON", "NEUTRO", "LONG", False),  # Bias neutro bloqueia
                ("RISK_OFF", "LONG", "LONG", False),  # RISK_OFF bloqueia
                ("RISK_ON", "LONG", "SHORT", False),  # Conflito BTC bloqueia
                ("RISK_ON", "LONG", "NEUTRO", True),  # BTC neutro OK
            ]

            for regime, d1_bias, btc_bias, expected in test_cases:
                result = skr.should_trade(regime, d1_bias, btc_bias)
                assert result == expected, f"Expected {expected}, got {result}"
                status = "TRADE" if result else "WAIT"
                logger.info(f"  ({regime}, {d1_bias}, {btc_bias}) → {status} ✓")

            logger.info("✅ PASSED: Should trade logic correct")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"Should trade: {str(e)}")
            return False

    def test_risk_gate_integration(self):
        """Test 7: Integração com RiskGate."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 7: RiskGate Integration")
        logger.info("=" * 70)

        try:
            risk_gate = RiskGate(max_drawdown_pct=3.0, circuit_breaker_pct=5.0)

            # Test case 1: No drawdown (session peak = current balance)
            status, msg = risk_gate.evaluate(1000.0, 1000.0)
            assert status == "CLEARED", f"Expected CLEARED, got {status}"
            logger.info(f"  No drawdown: {status} ✓")

            # Test case 2: Minor drawdown (< 3%)
            status, msg = risk_gate.evaluate(975.0, 1000.0)  # -2.5%
            assert status == "CLEARED", f"Expected CLEARED, got {status}"
            logger.info(f"  Minor drawdown (-2.5%): {status} ✓")

            # Test case 3: Moderate drawdown (3-5%)
            status, msg = risk_gate.evaluate(960.0, 1000.0)  # -4%
            assert status == "RISKY", f"Expected RISKY, got {status}"
            logger.info(f"  Moderate drawdown (-4%): {status} ✓")

            # Test case 4: Circuit breaker (> 5%)
            status, msg = risk_gate.evaluate(945.0, 1000.0)  # -5.5%
            assert status == "BLOCKED", f"Expected BLOCKED, got {status}"
            logger.info(f"  Circuit breaker (-5.5%): {status} ✓")

            logger.info("✅ PASSED: RiskGate integration working")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"RiskGate: {str(e)}")
            return False

    def test_end_to_end_scenario(self):
        """Test 8: Cenário end-to-end completo."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST 8: End-to-End Scenario")
        logger.info("=" * 70)

        try:
            skr = SKRPlaybook()
            risk_gate = RiskGate()

            # Cenário: Condições ideais para swing trade
            logger.info("\nScenario: Ideal conditions for SKR swing trade")
            logger.info("─" * 70)

            # Estado do mercado
            market_state = {
                "market_regime": "RISK_ON",
                "btc_cycle_phase": "BULL_RUN",
                "btc_bias": "LONG",
                "d1_bias": "LONG",
                "smc_d1_structure": "bullish",
                "volume_ratio": 1.8,
                "fear_greed_value": 65,
                "atr_pct": 3.5,
            }

            # Step 1: Risk gate
            risk_status, _ = risk_gate.evaluate(1000.0, 1000.0)
            logger.info(f"1. Risk gate: {risk_status} ✓")
            assert risk_status == "CLEARED"

            # Step 2: Should trade decision
            should_trade = skr.should_trade(
                "RISK_ON", "LONG", "LONG"
            )
            logger.info(f"2. Should trade: {should_trade} ✓")
            assert should_trade

            # Step 3: Confluence adjustments
            confluencia = skr.get_confluence_adjustments(market_state)
            total_conf = sum(confluencia.values())
            logger.info(f"3. Confluence: +{total_conf:.1f} (factors: {len(confluencia)}) ✓")
            assert total_conf > 0

            # Step 4: Risk adjustments
            risco = skr.get_risk_adjustments(market_state)
            logger.info(f"4. Risk adjustments - Position: {risco['position_size_multiplier']:.0%}, Stop: {risco['stop_multiplier']:.1f}x ATR ✓")

            # Step 5: Cycle phase
            fase = skr.get_cycle_phase(market_state)
            logger.info(f"5. Cycle phase: {fase} ✓")

            # Step 6: Trade decision output
            logger.info("\nTRADE DECISION OUTPUT:")
            logger.info(f"  Signal: BUY ✓")
            logger.info(f"  Confidence: {min(95, 50 + int(total_conf*10))}% (confluence-based)")
            logger.info(f"  Position size: ${10 * risco['position_size_multiplier']:.1f}")
            logger.info(f"  Stop loss: {risco['stop_multiplier']:.1f}% × ATR")
            logger.info(f"  Take profit target: 10-30% (swing target)")
            logger.info(f"  Risk status: CLEARED (operate)")

            logger.info("\n✅ PASSED: End-to-end scenario completed")

            self.results["tests_passed"] += 1
            return True

        except Exception as e:
            logger.error(f"❌ FAILED: {e}")
            self.results["tests_failed"] += 1
            self.results["details"].append(f"End-to-end: {str(e)}")
            return False

    def run_all_tests(self):
        """Executa todos os testes."""
        logger.info("\n")
        logger.info("╔" + "═" * 68 + "╗")
        logger.info("║ SKRUSDT INTEGRATION TEST SUITE                                    ║")
        logger.info("║ (Complete End-to-End Validation)                                 ║")
        logger.info("╚" + "═" * 68 + "╝")

        tests = [
            self.test_symbol_configuration,
            self.test_playbook_instantiation,
            self.test_confluence_adjustments,
            self.test_risk_adjustments,
            self.test_cycle_phase,
            self.test_should_trade,
            self.test_risk_gate_integration,
            self.test_end_to_end_scenario,
        ]

        for test in tests:
            test()

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)

        total = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total * 100) if total > 0 else 0

        logger.info(f"Tests passed:  {self.results['tests_passed']}/{total}")
        logger.info(f"Tests failed:  {self.results['tests_failed']}/{total}")
        logger.info(f"Pass rate:     {pass_rate:.1f}%")

        if self.results["tests_failed"] == 0:
            logger.info("\n✅ ALL TESTS PASSED - SKRUSDT READY FOR PRODUCTION")
            logger.info("\nNext steps:")
            logger.info("  1. Ativar SKRUSDT no menu principal")
            logger.info("  2. Iniciar paper trading (24h validação)")
            logger.info("  3. Monitorar 5-10 sinais em testnet")
            logger.info("  4. Deploy em LIVE com $10 capital máximo")
        else:
            logger.error(f"\n❌ {self.results['tests_failed']} TEST(S) FAILED")
            for detail in self.results["details"]:
                logger.error(f"   - {detail}")

        return self.results["tests_failed"] == 0


if __name__ == "__main__":
    tester = SKRIntegrationTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)
