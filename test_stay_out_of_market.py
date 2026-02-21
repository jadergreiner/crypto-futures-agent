#!/usr/bin/env python3
"""
Script de validação: Verificar se o novo componente de reward funciona.
Testa:
1. Imports dos novos módulos
2. Inicialização do RewardCalculator
3. Cálculo do novo componente r_out_of_market
4. Logging correto
"""

import sys
import logging
from typing import Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_reward_imports():
    """Teste 1: Verificar imports do módulo reward."""
    logger.info("=" * 70)
    logger.info("TESTE 1: Imports do módulo reward")
    logger.info("=" * 70)

    try:
        from agent.reward import RewardCalculator
        logger.info("✅ RewardCalculator importado com sucesso")

        # Verificar se constantes novas existem
        from agent.reward import (
            OUT_OF_MARKET_THRESHOLD_DD,
            OUT_OF_MARKET_BONUS,
            OUT_OF_MARKET_LOSS_AVOIDANCE,
            EXCESS_INACTIVITY_PENALTY
        )
        logger.info("✅ Todas as constantes do componente 'stay out' importadas")
        logger.info(f"   - OUT_OF_MARKET_THRESHOLD_DD = {OUT_OF_MARKET_THRESHOLD_DD}")
        logger.info(f"   - OUT_OF_MARKET_BONUS = {OUT_OF_MARKET_BONUS}")
        logger.info(f"   - OUT_OF_MARKET_LOSS_AVOIDANCE = {OUT_OF_MARKET_LOSS_AVOIDANCE}")
        logger.info(f"   - EXCESS_INACTIVITY_PENALTY = {EXCESS_INACTIVITY_PENALTY}")

        return True
    except ImportError as e:
        logger.error(f"❌ Erro ao importar: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False


def test_reward_calculator_initialization():
    """Teste 2: Inicializar RewardCalculator e verificar componentes."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 2: Inicialização do RewardCalculator")
    logger.info("=" * 70)

    try:
        from agent.reward import RewardCalculator

        calc = RewardCalculator()
        logger.info("✅ RewardCalculator inicializado")

        # Verificar weights
        weights = calc.get_weights()
        logger.info(f"✅ Pesos dos componentes: {weights}")

        # Verificar se o novo componente está lá
        if 'r_out_of_market' in weights:
            logger.info("✅ Componente 'r_out_of_market' presente nos pesos")
        else:
            logger.error("❌ Componente 'r_out_of_market' NÃO encontrado")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reward_calculation_no_position_with_drawdown():
    """Teste 3: Calcular reward quando sem posição e com drawdown."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 3: Reward sem posição com drawdown (proteção)")
    logger.info("=" * 70)

    try:
        from agent.reward import RewardCalculator

        calc = RewardCalculator()

        # Cenário: Sem posição, drawdown > threshold
        reward_dict = calc.calculate(
            trade_result=None,
            position_state={
                'has_position': False,
                'pnl_pct': 0,
                'pnl_momentum': 0
            },
            portfolio_state={
                'current_drawdown_pct': 2.5,  # > 2.0 threshold
                'trades_24h': 1
            },
            action_valid=True,
            trades_recent=[],
            flat_steps=10
        )

        logger.info(f"Reward components: {reward_dict}")

        if reward_dict['r_out_of_market'] > 0:
            logger.info(f"✅ Reward 'out_of_market' gerado: +{reward_dict['r_out_of_market']:.3f}")
            logger.info("   (Proteção em drawdown reconhecida)")
        else:
            logger.error(f"❌ Esperava r_out_of_market > 0, got {reward_dict['r_out_of_market']}")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reward_calculation_rest_after_trades():
    """Teste 4: Calcular reward por descanso após múltiplos trades."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 4: Reward por descanso após múltiplos trades")
    logger.info("=" * 70)

    try:
        from agent.reward import RewardCalculator

        calc = RewardCalculator()

        # Cenário: Sem posição, múltiplos trades recentes
        reward_dict = calc.calculate(
            trade_result=None,
            position_state={
                'has_position': False,
                'pnl_pct': 0,
                'pnl_momentum': 0
            },
            portfolio_state={
                'current_drawdown_pct': 0.5,  # < 2.0 threshold
                'trades_24h': 4  # >= 3 trades
            },
            action_valid=True,
            trades_recent=[],
            flat_steps=5
        )

        logger.info(f"Reward components: {reward_dict}")

        if reward_dict['r_out_of_market'] > 0:
            logger.info(f"✅ Reward 'out_of_market' gerado: +{reward_dict['r_out_of_market']:.3f}")
            logger.info("   (Descanso após atividade reconhecido)")
        else:
            logger.error(f"❌ Esperava r_out_of_market > 0, got {reward_dict['r_out_of_market']}")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reward_calculation_excess_inactivity():
    """Teste 5: Penalidade por inatividade excessiva."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 5: Penalidade por inatividade excessiva (>16 dias)")
    logger.info("=" * 70)

    try:
        from agent.reward import RewardCalculator

        calc = RewardCalculator()

        # Cenário: Sem posição, mas muito tempo inativo
        reward_dict = calc.calculate(
            trade_result=None,
            position_state={
                'has_position': False,
                'pnl_pct': 0,
                'pnl_momentum': 0
            },
            portfolio_state={
                'current_drawdown_pct': 0.1,
                'trades_24h': 0
            },
            action_valid=True,
            trades_recent=[],
            flat_steps=150  # > 96 H4 candles (~16 dias)
        )

        logger.info(f"Reward components: {reward_dict}")

        if reward_dict['r_out_of_market'] < 0:
            logger.info(f"✅ Penalidade de inatividade gerada: {reward_dict['r_out_of_market']:.3f}")
            logger.info("   (Inatividade excessiva penalizada)")
        else:
            logger.warning(f"⚠️  Esperava r_out_of_market < 0 para inatividade, got {reward_dict['r_out_of_market']}")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executar todos os testes."""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " VALIDAÇÃO: Aprendizado 'Ficar Fora do Mercado' ".center(68) + "║")
    logger.info("║" + " Agent Reward Round 5 ".center(68) + "║")
    logger.info("╚" + "=" * 68 + "╝")

    tests = [
        ("Imports", test_reward_imports),
        ("Inicialização", test_reward_calculator_initialization),
        ("Reward (Drawdown)", test_reward_calculation_no_position_with_drawdown),
        ("Reward (Rest)", test_reward_calculation_rest_after_trades),
        ("Penalidade (Inatividade)", test_reward_calculation_excess_inactivity),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"\n❌ TESTE '{name}' FALHOU: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Sumário
    logger.info("\n" + "=" * 70)
    logger.info("SUMÁRIO DOS TESTES")
    logger.info("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")

    logger.info("=" * 70)
    logger.info(f"Resultado: {passed}/{total} testes passaram")
    logger.info("=" * 70)

    if passed == total:
        logger.info("\n🎉 TODOS OS TESTES PASSARAM!")
        logger.info("Implementação do componente 'r_out_of_market' está funcionando corretamente.")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} testes falharam.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
