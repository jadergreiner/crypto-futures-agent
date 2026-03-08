#!/usr/bin/env python3
"""
Teste rápido: Validar que SB3 logger seguro funciona no Windows.

Executar: python tests/test_sb3_logger_safe.py

Este teste vai:
1. Criar um ambiente dummy
2. Criar um modelo PPO com logger seguro
3. Executar 1000 timesteps de treinamento
4. Validar que não ocorre OSError

Se passa, o problema está resolvido!
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def test_sb3_imports():
    """Testa se SB3 está instalado."""
    logger.info("=" * 70)
    logger.info("TESTE 1: Importar Stable-Baselines3")
    logger.info("=" * 70)

    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.logger import configure
        from stable_baselines3.common.vec_env import DummyVecEnv

        logger.info("✅ Imports SB3 OK")
        return True

    except ImportError as e:
        logger.error(f"❌ Erro ao importar SB3: {e}")
        logger.error("Solução: pip install stable-baselines3")
        return False


def test_sb3_utils():
    """Testa se agent/sb3_utils.py funciona."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 2: Importar agent/sb3_utils")
    logger.info("=" * 70)

    try:
        from agent.sb3_utils import (
            create_safe_sb3_logger,
            attach_safe_logger_to_model,
            validate_sb3_setup,
        )

        logger.info("✅ Imports agent/sb3_utils OK")

        # Validar setup
        validate_sb3_setup()
        logger.info("✅ Setup validado")

        return True

    except ImportError as e:
        logger.error(f"❌ Erro ao importar sb3_utils: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao validar setup: {e}")
        return False


def test_logger_creation():
    """Testa criação de logger seguro."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 3: Criar logger seguro")
    logger.info("=" * 70)

    try:
        from agent.sb3_utils import create_safe_sb3_logger

        # Teste 1: Logger vazio
        logger_empty = create_safe_sb3_logger(use_stdout=False)
        logger.info(f"✅ Logger vazio criado")

        # Teste 2: Logger com stdout
        logger_stdout = create_safe_sb3_logger(use_stdout=True)
        logger.info(f"✅ Logger com stdout criado")

        return True

    except Exception as e:
        logger.error(f"❌ Erro ao criar logger: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ppo_training():
    """Testa treinamento PPO com logger seguro (o teste definitivo)."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 4: Treinar modelo PPO com logger seguro (1000 steps)")
    logger.info("=" * 70)

    try:
        import gymnasium as gym
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv
        from agent.sb3_utils import attach_safe_logger_to_model

        # Criar ambiente dummy (CartPole é seguro)
        logger.info("Criando ambiente...")
        env = gym.make("CartPole-v1")
        vec_env = DummyVecEnv([lambda: gym.make("CartPole-v1")])

        # Criar modelo com logger seguro
        logger.info("Criando modelo PPO com logger seguro...")
        model = PPO(
            policy="MlpPolicy",
            env=vec_env,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=32,
            verbose=0,
            tensorboard_log=None,
        )

        # Anexar logger seguro
        logger.info("Anexando logger seguro...")
        attach_safe_logger_to_model(model, use_stdout=False)

        # Treinar por 1000 steps
        logger.info("Iniciando treinamento (1000 timesteps)...")
        logger.info("   (sem OSError, isto é o que esperamos!)")

        model.learn(total_timesteps=1000, progress_bar=False)

        logger.info("✅ Treinamento completado SEM ERRO!")
        logger.info("✅ Problema do logger SB3 foi RESOLVIDO!")

        return True

    except OSError as e:
        logger.error(f"❌ OSError durante training (problema NÃO resolvido):")
        logger.error(f"   {e}")
        import traceback

        traceback.print_exc()
        return False

    except Exception as e:
        logger.error(f"❌ Erro inesperado durante training:")
        logger.error(f"   {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Executar todos os testes."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE: Solução para SB3 Logger OSError no Windows")
    logger.info("=" * 70)

    results = {
        "SB3 Imports": test_sb3_imports(),
        "sb3_utils Imports": test_sb3_utils(),
        "Logger Creation": test_logger_creation(),
        "PPO Training": test_ppo_training(),
    }

    # Resumo
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    # Resultado final
    all_passed = all(results.values())

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("✅ TODOS OS TESTES PASSARAM!")
        logger.info("A solução está pronta para ser integrada.")
        logger.info("\nPróximos passos:")
        logger.info("1. Integrar attach_safe_logger_to_model() em train_ppo_skeleton.py")
        logger.info("2. Integrar em agent/trainer.py")
        logger.info("3. Executar: python main.py --train")
        return 0
    else:
        logger.error("❌ ALGUNS TESTES FALHARAM")
        logger.error("Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
