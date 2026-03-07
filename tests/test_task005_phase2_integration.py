"""
Integration Test para TASK-005 Phase 2 — Valida todos componentes.

Testa:
- Data loader
- CryptoTradingEnv
- PPO Trainer initialization
- Training loop kickoff
"""

import sys
import os
from pathlib import Path

# Muda para diretório do repo
os.chdir(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.rl.data_loader import TradeHistoryLoader
from agent.rl.training_env import CryptoTradingEnv
from agent.rl.ppo_trainer import PPOTrainer
from agent.rl.training_loop import Task005TrainingLoop


def test_data_loader():
    """Testa carregamento de dados."""
    print("\n📂 Test 1: Data Loader...")
    try:
        loader = TradeHistoryLoader("data/trades_history.json")
        trades = loader.load()
        print(f"  ✅ Carregados {len(trades)} trades")
        loader.print_statistics()
        return True
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False


def test_environment():
    """Testa criação e execução do ambiente."""
    print("\n🎮 Test 2: CryptoTradingEnv...")
    try:
        loader = TradeHistoryLoader("data/trades_history.json")
        trades = loader.load()
        
        # Cria environment
        env = CryptoTradingEnv(trade_data=trades)
        print("  ✅ Ambiente criado")
        
        # Reset
        obs, info = env.reset()
        print(f"  ✅ Reset: obs shape {obs.shape}, inicial equity ${env.equity:.2f}")
        
        # Alguns passos
        for i in range(5):
            action = env.action_space.sample()  # Ação aleatória
            obs, reward, terminated, truncated, info = env.step(action)
            print(f"    Step {i+1}: action={action}, reward={reward:.6f}, equity=${info['equity']:.2f}")
            if terminated:
                break
        
        env.close()
        print("  ✅ Environment funcionando")
        return True
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trainer_initialization():
    """Testa inicialização do trainer."""
    print("\n🤖 Test 3: PPO Trainer Initialization...")
    try:
        loader = TradeHistoryLoader("data/trades_history.json")
        trades = loader.load()
        
        env = CryptoTradingEnv(trade_data=trades[:20])  # Usa subset menor
        
        # Cria trainer (sem TensorBoard para evitar conflitos)
        trainer = PPOTrainer(
            env=env,
            learning_rate=1e-4,
            batch_size=64,
            use_tensorboard=False,  # Desabilita TensorBoard em testes
        )
        print("  ✅ Trainer criado")
        
        # Cria modelo
        model = trainer.create_model()
        print(f"  ✅ Modelo PPO criado: {model}")
        
        # Teste rápido de learn (1000 steps)
        print("  Running quick 1000-step training...")
        model.learn(total_timesteps=1000)
        print("  ✅ Quick training succeeded")
        
        env.close()
        return True
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_training_loop_initialization():
    """Testa inicialização do training loop."""
    print("\n🚀 Test 4: Training Loop Initialization...")
    try:
        loop = Task005TrainingLoop()
        print("  ✅ Training loop criado")
        
        # Inicializa
        if loop.initialize():
            print("  ✅ Training loop inicializado")
            print(f"     - Environment: {loop.env}")
            print(f"     - Trainer: {loop.trainer}")
            print(f"     - Model: {loop.model}")
            return True
        else:
            print("  ❌ Falha na inicialização")
            return False
    
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("🧪 TASK-005 PHASE 2 INTEGRATION TESTS")
    print("="*70)
    
    results = []
    
    # Test 1
    results.append(("Data Loader", test_data_loader()))
    
    # Test 2
    results.append(("Environment", test_environment()))
    
    # Test 3
    results.append(("Trainer Init", test_trainer_initialization()))
    
    # Test 4
    results.append(("Training Loop Init", test_training_loop_initialization()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED — Phase 2 Ready!\n")
        return True
    else:
        print("❌ SOME TESTS FAILED\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
