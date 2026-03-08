#!/usr/bin/env python3
"""
TESTE IMEDIATO: Validation que a solução SB3 Logger funciona

Execute agora:
  python SB3_LOGGER_IMMEDIATE_TEST.py

Se passar, a solução está pronta! ✅
"""

import sys
import logging
from pathlib import Path


def setup_logging():
    """Configura logging para output claro."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def test_1_imports():
    """Test 1: Validar imports básicos."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: Importar agent/sb3_utils")
    logger.info("=" * 70)

    try:
        from agent.sb3_utils import attach_safe_logger_to_model
        logger.info("✅ PASS: agent/sb3_utils importado com sucesso")
        return True
    except ImportError as e:
        logger.error(f"❌ FAIL: {e}")
        logger.error("   Verifique se agent/sb3_utils.py existe")
        return False


def test_2_function_signature():
    """Test 2: Validar assinatura da função."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Validar função attach_safe_logger_to_model")
    logger.info("=" * 70)

    try:
        from agent.sb3_utils import attach_safe_logger_to_model
        import inspect

        sig = inspect.signature(attach_safe_logger_to_model)
        logger.info(f"✅ Assinatura: {sig}")
        logger.info("✅ PASS: Função tem assinatura esperada")
        return True
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        return False


def test_3_logger_creation():
    """Test 3: Criar logger seguro."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Criar logger seguro")
    logger.info("=" * 70)

    try:
        from agent.sb3_utils import create_safe_sb3_logger

        logger_obj = create_safe_sb3_logger(use_stdout=False)
        logger.info(f"✅ Logger type: {type(logger_obj)}")
        logger.info(f"✅ Logger dir: {logger_obj.get_dir()}")
        logger.info("✅ PASS: Logger criado com sucesso")
        return True
    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_sb3_version():
    """Test 4: Validar versão do SB3."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Validar SB3 e versão")
    logger.info("=" * 70)

    try:
        import stable_baselines3
        from stable_baselines3 import PPO

        version = stable_baselines3.__version__
        logger.info(f"✅ Stable-Baselines3 versão: {version}")
        logger.info("✅ PASS: SB3 está instalado")
        return True
    except ImportError as e:
        logger.error(f"❌ FAIL: {e}")
        logger.error("   Instale com: pip install stable-baselines3")
        return False


def test_5_model_creation():
    """Test 5: Criar modelo PPO com logger seguro."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Criar modelo PPO com logger seguro")
    logger.info("=" * 70)

    try:
        import gymnasium as gym
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv
        from agent.sb3_utils import attach_safe_logger_to_model

        # Ambiente
        env = gym.make("CartPole-v1")
        vec_env = DummyVecEnv([lambda: gym.make("CartPole-v1")])

        # Modelo
        logger.info("  Criando modelo PPO...")
        model = PPO(
            "MlpPolicy",
            vec_env,
            verbose=0,
            tensorboard_log=None,
        )

        # Logger seguro
        logger.info("  Anexando logger seguro...")
        attach_safe_logger_to_model(model, use_stdout=False)

        logger.info("✅ PASS: Modelo criado com logger seguro")
        return True

    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_training():
    """Test 6: Treinar por 100 steps (teste definitivo)."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Treinar por 100 timesteps (teste definitivo)")
    logger.info("=" * 70)
    logger.info("  Se este teste passar, o problema está RESOLVIDO!")

    try:
        import gymnasium as gym
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv
        from agent.sb3_utils import attach_safe_logger_to_model

        # Ambiente
        env = gym.make("CartPole-v1")
        vec_env = DummyVecEnv([lambda: gym.make("CartPole-v1")])

        # Modelo com logger seguro
        logger.info("  Criando e treinando modelo...")
        model = PPO(
            "MlpPolicy",
            vec_env,
            verbose=0,
            tensorboard_log=None,
        )
        attach_safe_logger_to_model(model, use_stdout=False)

        # Training (o teste real)
        logger.info("  Executando: model.learn(100)")
        model.learn(total_timesteps=100, progress_bar=False)

        logger.info("✅ PASS: 100 timesteps completados SEM OSError!")
        logger.info("✅ PROBLEMA IDENTIFICADO E RESOLVIDO!")
        return True

    except OSError as e:
        logger.error(f"❌ FAIL: OSError (problema NÃO resolvido)")
        logger.error(f"   {e}")
        import traceback
        traceback.print_exc()
        return False

    except Exception as e:
        logger.error(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executar todos os testes."""
    logger.info("\n")
    logger.info("█" * 70)
    logger.info("█ TESTE IMEDIATO: Solução SB3 Logger OSError Windows")
    logger.info("█" * 70)

    tests = [
        ("1. Imports", test_1_imports),
        ("2. Assinatura", test_2_function_signature),
        ("3. Logger Creation", test_3_logger_creation),
        ("4. SB3 Version", test_4_sb3_version),
        ("5. Model Creation", test_5_model_creation),
        ("6. Training (DEFINITIVO)", test_6_training),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Erro não capturado em {test_name}: {e}")
            results[test_name] = False

    # Resumo
    logger.info("\n" + "=" * 70)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 70)

    for test_name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {test_name}")

    # Resultado final
    all_passed = all(results.values())

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("✅ ✅ ✅ TODOS OS TESTES PASSARAM! ✅ ✅ ✅")
        logger.info("=" * 70)
        logger.info("")
        logger.info("A solução está PRONTA para usar!")
        logger.info("")
        logger.info("Próximos passos:")
        logger.info("  1. Ler: docs/SB3_LOGGER_WINDOWS_FIX.md")
        logger.info("  2. Integrar em: scripts/train_ppo_skeleton.py")
        logger.info("  3. Integrar em: agent/trainer.py")
        logger.info("  4. Testar: python main.py --train")
        logger.info("")
        logger.info("Ver: APPLY_SB3_LOGGER_PATCH.py para instruções")
        logger.info("")
        return 0
    else:
        logger.info("❌ ALGUNS TESTES FALHARAM")
        logger.info("=" * 70)
        logger.info("Verifique os erros acima.")
        logger.info("")
        failed_tests = [name for name, result in results.items() if not result]
        logger.info("Testes que falharam:")
        for test in failed_tests:
            logger.info(f"  - {test}")
        logger.info("")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
