#!/usr/bin/env python3
"""
Testes de validação: Opportunity Learning (Aprendizado Contextual).

Testa:
1. Registro de oportunidades perdidas
2. Avaliação de resultados hipotéticos
3. Cálculo de reward contextual
4. Diferentes cenários de decisão
"""

import sys
import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_opportunity_learner_imports():
    """Teste 1: Verificar imports do módulo."""
    logger.info("=" * 70)
    logger.info("TESTE 1: Imports do módulo OpportunityLearner")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner, MissedOpportunity
        logger.info("✅ OpportunityLearner importado com sucesso")
        logger.info("✅ MissedOpportunity importado com sucesso")
        return True
    except ImportError as e:
        logger.error(f"❌ Erro ao importar: {e}")
        return False


def test_opportunity_learner_initialization():
    """Teste 2: Inicializar OpportunityLearner."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 2: Inicialização do OpportunityLearner")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner
        
        learner = OpportunityLearner()
        logger.info("✅ OpportunityLearner inicializado")
        
        # Verificar estado inicial
        summary = learner.get_episode_summary()
        logger.info(f"✅ Estado inicial: {summary}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_register_opportunity():
    """Teste 3: Registrar oportunidade perdida."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 3: Registrar oportunidade perdida")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner
        
        learner = OpportunityLearner()
        
        # Registrar uma oportunidade
        opp_id = learner.register_missed_opportunity(
            symbol="BTCUSDT",
            timestamp=1709012400000,
            step=10,
            direction="LONG",
            entry_price=45000.0,
            confluence=8.5,
            atr=500.0,
            drawdown_pct=0.5,
            recent_trades_24h=0
        )
        
        logger.info(f"✅ Oportunidade registrada com ID: {opp_id}")
        
        # Verificar que foi registrada
        if opp_id in learner.missed_opportunities:
            opp = learner.missed_opportunities[opp_id]
            logger.info(f"   - Símbolo: {opp.symbol}")
            logger.info(f"   - Direction: {opp.direction}")
            logger.info(f"   - Entry Price: {opp.entry_price}")
            logger.info(f"   - Confluence: {opp.confluence}")
            logger.info(f"   - TP Hipotético: {opp.hypothetical_tp}")
            logger.info(f"   - SL Hipotético: {opp.hypothetical_sl}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluate_winning_opportunity():
    """Teste 4: Avaliar oportunidade que teria ganhado bem."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 4: Avaliar oportunidade VENCEDORA")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner
        
        learner = OpportunityLearner()
        
        # Registrar oportunidade
        opp_id = learner.register_missed_opportunity(
            symbol="ETHUSDT",
            timestamp=1709012400000,
            step=10,
            direction="LONG",
            entry_price=3500.0,
            confluence=8.5,
            atr=100.0,
            drawdown_pct=0.5,  # Sem drawdown, condições normais
            recent_trades_24h=0
        )
        
        # Simular que preço subiu muito (teria atingido TP)
        # TP = 3500 + 100*3 = 3800
        # Max price = 3900 (ultrapassou TP)
        opp = learner.evaluate_opportunity(
            opportunity_id=opp_id,
            current_price=3850.0,
            max_price_reached=3900.0,
            min_price_reached=3450.0
        )
        
        logger.info(f"✅ Oportunidade avaliada")
        logger.info(f"   - Quality: {opp.opportunity_quality}")
        logger.info(f"   - Would have won: {opp.would_have_been_winning}")
        logger.info(f"   - Profit if entered: {opp.profit_pct_if_entered:+.2f}%")
        logger.info(f"   - Contextual Reward: {opp.contextual_reward:+.3f}")
        logger.info(f"   - Reasoning: {opp.reasoning}")
        
        # Verificar se foi penalizada por desperdiçar
        if opp.contextual_reward < -0.05:
            logger.info("✅ Penalidade aplicada por desperdiçar oportunidade boa")
            return True
        else:
            logger.error(f"❌ Esperava penalidade < -0.05, got {opp.contextual_reward}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluate_losing_opportunity():
    """Teste 5: Avaliar oportunidade que teria perdido."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 5: Avaliar oportunidade PERDEDORA (evitada com sucesso)")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner
        
        learner = OpportunityLearner()
        
        # Registrar oportunidade em alta drawdown
        # TP = 45000 + 500*3 = 46500
        # SL = 45000 - 500*1.5 = 43750
        opp_id = learner.register_missed_opportunity(
            symbol="BTCUSDT",
            timestamp=1709012400000,
            step=20,
            direction="LONG",
            entry_price=45000.0,
            confluence=8.2,
            atr=500.0,
            drawdown_pct=3.5,  # Drawdown alto
            recent_trades_24h=1
        )
        
        # Simular que preço desceu (teria batido stop loss)
        opp = learner.evaluate_opportunity(
            opportunity_id=opp_id,
            current_price=43800.0,
            max_price_reached=45200.0,
            min_price_reached=43600.0  # Abaixo do SL
        )
        
        logger.info(f"✅ Oportunidade avaliada")
        logger.info(f"   - Quality: {opp.opportunity_quality}")
        logger.info(f"   - Would have won: {opp.would_have_been_winning}")
        logger.info(f"   - Profit if entered: {opp.profit_pct_if_entered:+.2f}%")
        logger.info(f"   - Contextual Reward: {opp.contextual_reward:+.3f}")
        logger.info(f"   - Reasoning: {opp.reasoning}")
        
        # Verificar se foi recompensada por evitar perda
        if opp.contextual_reward > 0.10:
            logger.info("✅ Recompensa aplicada por evitar perda")
            return True
        else:
            logger.error(f"❌ Esperava recompensa > 0.10, got {opp.contextual_reward}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_episode_summary():
    """Teste 6: Resumo de aprendizado do episódio."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTE 6: Sumário de aprendizado do episódio")
    logger.info("=" * 70)
    
    try:
        from agent.opportunity_learning import OpportunityLearner
        
        learner = OpportunityLearner()
        
        # Registrar 2 oportunidades
        opp1 = learner.register_missed_opportunity(
            symbol="BTCUSDT", timestamp=1000, step=10, direction="LONG",
            entry_price=45000.0, confluence=8.5, atr=500.0,
            drawdown_pct=0.5, recent_trades_24h=0
        )
        
        opp2 = learner.register_missed_opportunity(
            symbol="ETHUSDT", timestamp=2000, step=20, direction="SHORT",
            entry_price=3500.0, confluence=8.0, atr=100.0,
            drawdown_pct=3.0, recent_trades_24h=2
        )
        
        # Avaliar ambas
        learner.evaluate_opportunity(opp1, 45500.0, 45800.0, 44800.0)
        learner.evaluate_opportunity(opp2, 3400.0, 3450.0, 3380.0)
        
        # Verificar sumário
        summary = learner.get_episode_summary()
        
        logger.info(f"✅ Sumário do episódio:")
        logger.info(f"   - Oportunidades rastreadas: {summary['opportunities_tracked']}")
        logger.info(f"   - Oportunidades avaliadas: {summary['opportunities_evaluated']}")
        logger.info(f"   - Decisões sábias: {summary['wise_decisions']}")
        logger.info(f"   - Decisões desesperadas: {summary['desperate_decisions']}")
        logger.info(f"   - Reward contextual total: {summary['total_contextual_reward']:+.4f}")
        logger.info(f"   - Reward contextual médio: {summary['avg_contextual_reward']:+.4f}")
        logger.info(f"   - % de decisões sábias: {summary['wise_decisions_pct']:.1f}%")
        
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
    logger.info("║" + " VALIDAÇÃO: Aprendizado Contextual de Decisões ".center(68) + "║")
    logger.info("║" + " OpportunityLearner - Meta-Learning ".center(68) + "║")
    logger.info("╚" + "=" * 68 + "╝")
    
    tests = [
        ("Imports", test_opportunity_learner_imports),
        ("Inicialização", test_opportunity_learner_initialization),
        ("Registrar Opp", test_register_opportunity),
        ("Avaliar Vencedora", test_evaluate_winning_opportunity),
        ("Avaliar Perdedora", test_evaluate_losing_opportunity),
        ("Sumário", test_episode_summary),
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
        logger.info("OpportunityLearner está funcionando corretamente.")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} testes falharam.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
