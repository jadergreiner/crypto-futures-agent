#!/usr/bin/env python3
"""
Validação ML Final — Testa todos componentes críticos

Testa:
1. config/ppo_config.py → 11 hiperparâmetros
2. agent/reward.py → RewardCalculator
3. BacktestEnvironment → instanciação
4. scripts/revalidate_model.py → RevalidationValidator
5. Risk gates → 6/6 corretos

Saída: "✅ All ML components OK" ou lista de problemas
"""

import logging
import sys
from typing import Dict, List, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class MLValidationFinal:
    """Validação final de todos componentes ML."""

    def __init__(self):
        """Inicializa validador."""
        self.issues: List[str] = []
        self.checks_passed = 0
        self.checks_total = 5

    def check_ppo_config(self) -> bool:
        """
        Tarefa 1.1: Testar ppo_config.py
        Verificar todos 11 hiperparâmetros.
        """
        logger.info("CHECK 1: PPO Config (11 hyperparameters)")

        try:
            from config.ppo_config import get_ppo_config, PPOConfig

            config = get_ppo_config('phase4')

            # Verificar classe
            if not isinstance(config, PPOConfig):
                raise TypeError("get_ppo_config não retornou PPOConfig")

            # Verificar 11 hiperparâmetros
            required_params = [
                'learning_rate',
                'batch_size',
                'n_steps',
                'n_epochs',
                'gamma',
                'gae_lambda',
                'ent_coef',
                'clip_range',
                'vf_coef',
                'max_grad_norm',
                'total_timesteps'
            ]

            missing_params = []
            for param in required_params:
                if not hasattr(config, param):
                    missing_params.append(param)
                else:
                    value = getattr(config, param)
                    logger.info(f"  ✓ {param}: {value}")

            if missing_params:
                raise AttributeError(f"Parâmetros faltando: {missing_params}")

            # Validar valores
            if config.learning_rate <= 0:
                raise ValueError("learning_rate deve ser > 0")
            if config.batch_size <= 0:
                raise ValueError("batch_size deve ser > 0")
            if config.total_timesteps <= 0:
                raise ValueError("total_timesteps deve ser > 0")

            logger.info("✅ PPO Config OK (11/11 hiperparâmetros)")
            self.checks_passed += 1
            return True

        except Exception as e:
            msg = f"❌ PPO Config FAILED: {str(e)}"
            logger.error(msg)
            self.issues.append(msg)
            return False

    def check_reward_function(self) -> bool:
        """
        Tarefa 1.2: Testar reward function
        Verificar RewardCalculator com 4 componentes.
        """
        logger.info("CHECK 2: Reward Function (4 components)")

        try:
            from agent.reward import RewardCalculator

            calc = RewardCalculator()

            # Verificar método calculate
            if not hasattr(calc, 'calculate'):
                raise AttributeError("RewardCalculator sem método calculate")

            # Executar calulação dummy
            result = calc.calculate()

            # Verificar 4 componentes
            required_components = [
                'r_pnl',
                'r_hold_bonus',
                'r_invalid_action',
                'r_out_of_market'
            ]

            for component in required_components:
                if component not in result:
                    raise KeyError(f"Componente faltando: {component}")
                logger.info(f"  ✓ {component}: {result[component]}")

            logger.info("✅ Reward Function OK (4/4 componentes)")
            self.checks_passed += 1
            return True

        except Exception as e:
            msg = f"❌ Reward Function FAILED: {str(e)}"
            logger.error(msg)
            self.issues.append(msg)
            return False

    def check_backtest_environment(self) -> bool:
        """
        Tarefa 1.3: Testar BacktestEnvironment
        Verificar que funciona com PPO config.
        """
        logger.info("CHECK 3: BacktestEnvironment")

        try:
            from backtest.backtest_environment import BacktestEnvironment
            import pandas as pd
            import numpy as np

            # Criar dados mock
            mock_data = {
                'h4': pd.DataFrame({
                    'open': np.random.rand(100),
                    'high': np.random.rand(100),
                    'low': np.random.rand(100),
                    'close': np.random.rand(100),
                    'volume': np.random.rand(100)
                }),
                'symbol': 'TESTUSDT'
            }

            # Tentar instanciar
            env = BacktestEnvironment(
                data=mock_data,
                initial_capital=10000,
                episode_length=50,
                deterministic=True,
                seed=42
            )

            # Verificar atributos básicos
            if not hasattr(env, 'step') or not hasattr(env, 'reset'):
                raise AttributeError("BacktestEnvironment sem métodos step/reset")

            # Tentar reset
            obs, info = env.reset()
            if obs is None:
                raise RuntimeError("reset() retornou obs=None")

            logger.info(f"  ✓ Environment instanciado")
            logger.info(f"  ✓ Observation shape: {obs.shape if hasattr(obs, 'shape') else 'unknown'}")
            logger.info("✅ BacktestEnvironment OK")
            self.checks_passed += 1
            return True

        except Exception as e:
            msg = f"❌ BacktestEnvironment FAILED: {str(e)}"
            logger.error(msg)
            self.issues.append(msg)
            return False

    def check_revalidation_script(self) -> bool:
        """
        Tarefa 1.4: Testar revalidate_model.py
        Verificar que RevalidationValidator pode ser instanciado.
        """
        logger.info("CHECK 4: Revalidation Script")

        try:
            from scripts.revalidate_model import RevalidationValidator

            # Tentar instanciar
            validator = RevalidationValidator(model_dir="models/ppo_phase4")

            # Verificar atributos
            if not hasattr(validator, 'load_model'):
                raise AttributeError("RevalidationValidator sem método load_model")

            if not hasattr(validator, 'run_backtest'):
                raise AttributeError("RevalidationValidator sem método run_backtest")

            logger.info("  ✓ RevalidationValidator instanciado")
            logger.info("  ✓ Métodos required presentes")
            logger.info("✅ Revalidation Script OK")
            self.checks_passed += 1
            return True

        except Exception as e:
            msg = f"❌ Revalidation Script FAILED: {str(e)}"
            logger.error(msg)
            self.issues.append(msg)
            return False

    def check_risk_gates(self) -> bool:
        """
        Tarefa 1.5: Validar 6 risk gates
        Verificar que valores dos gates estão corretos.
        """
        logger.info("CHECK 5: Risk Gates (6/6)")

        try:
            from scripts.revalidate_model import RevalidationValidator

            # Verificar constantes
            gates_expected = {
                "SHARPE_MIN": 1.0,
                "MAX_DD_MAX": 15.0,
                "WIN_RATE_MIN": 45.0,
                "PROFIT_FACTOR_MIN": 1.5,
                "CONSECUTIVE_LOSSES_MAX": 5,
                "CALMAR_MIN": 2.0
            }

            for gate_name, expected_value in gates_expected.items():
                actual_value = getattr(RevalidationValidator, gate_name)
                if actual_value != expected_value:
                    raise ValueError(f"{gate_name}: esperado {expected_value}, got {actual_value}")
                logger.info(f"  ✓ {gate_name}: {actual_value}")

            logger.info("✅ Risk Gates OK (6/6 corretos)")
            self.checks_passed += 1
            return True

        except Exception as e:
            msg = f"❌ Risk Gates FAILED: {str(e)}"
            logger.error(msg)
            self.issues.append(msg)
            return False

    def run_all_checks(self) -> Tuple[bool, Dict[str, any]]:
        """
        Executa todos checks e retorna resultado.

        Returns:
            (success, result_dict)
        """
        logger.info("\n" + "=" * 80)
        logger.info("  ML FINAL VALIDATION — ALL CHECKS")
        logger.info("=" * 80 + "\n")

        # Executar checks
        self.check_ppo_config()
        self.check_reward_function()
        self.check_backtest_environment()
        self.check_revalidation_script()
        self.check_risk_gates()

        # Resultado final
        logger.info("\n" + "=" * 80)
        logger.info(f"  RESULT: {self.checks_passed}/{self.checks_total} checks passed")
        logger.info("=" * 80)

        success = len(self.issues) == 0

        if success:
            logger.info("\n✅ ALL ML COMPONENTS OK")
            logger.info("System ready for 23 FEV 14:00 UTC training launch\n")
        else:
            logger.error("\n❌ BLOCKERS FOUND:\n")
            for issue in self.issues:
                logger.error(f"  {issue}")

        result = {
            "validation_status": "OK" if success else "FAILED",
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "blockers": self.issues,
            "components_validated": {
                "ppo_config": "OK" if self.checks_passed >= 1 else "FAILED",
                "reward_function": "OK" if self.checks_passed >= 2 else "FAILED",
                "backtest_environment": "OK" if self.checks_passed >= 3 else "FAILED",
                "revalidation_script": "OK" if self.checks_passed >= 4 else "FAILED",
                "risk_gates": "OK" if self.checks_passed >= 5 else "FAILED"
            }
        }

        return success, result


def main():
    """Main entry point."""
    validator = MLValidationFinal()
    success, result = validator.run_all_checks()

    # Print JSON result
    import json
    print("\n" + json.dumps(result, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
