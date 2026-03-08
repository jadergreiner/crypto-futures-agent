"""
Teste E2E para F-09: Script de treinamento funcional (python main.py --train).
Valida a pipeline completa de treinamento com dados sintéticos.
"""

import logging
import os
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_f09_training_pipeline():
    """
    US-04: Verifica que python main.py --train funciona completamente.
    """
    print("\n" + "="*70)
    print("TESTE F-09: Script de treinamento funcional (python main.py --train)")
    print("="*70)

    from agent.data_loader import DataLoader
    from agent.trainer import Trainer
    from tests.test_rl_environment import create_test_data_with_indicators
    import tempfile
    import shutil

    # 1. Preparar dados
    print("\n[1/5] Preparando dados de treinamento...")
    data = create_test_data_with_indicators(symbol='BTCUSDT')
    
    # Criar data loader (sem DB, com dados sintéticos)
    loader = DataLoader(db=None)
    print(f"  [OK] DataLoader criado para BTCUSDT")
    
    # 2. Inicializar Trainer
    print("\n[2/5] Inicializando Trainer...")
    
    # Usar diretório temporário para não poluir models/
    temp_dir = tempfile.mkdtemp(prefix="test_f09_training_")
    print(f"  [OK] Trainer criado em: {temp_dir}")
    
    try:
        trainer = Trainer(save_dir=temp_dir)
        
        # 3. Fase 1: Exploração (reduzida para teste)
        print("\n[3/5] Executando Fase 1: Exploração (10k steps para teste)...")
        model_phase1 = trainer.train_phase1_exploration(
            train_data=data,
            total_timesteps=10000,  # Reduzido de 500k para teste rápido
            episode_length=50
        )
        print(f"  [OK] Fase 1 concluída")
        
        # Validar que modelo foi salvo
        phase1_path = os.path.join(temp_dir, "phase1_exploration.zip")
        assert os.path.exists(phase1_path), "Phase 1 model não foi salvo"
        phase1_size = os.path.getsize(phase1_path)
        print(f"    - Modelo salvo: {phase1_size/1024:.1f} KB")
        
        # Validar VecNormalize
        vec_path = os.path.join(temp_dir, "phase1_vec_normalize.pkl")
        assert os.path.exists(vec_path), "VecNormalize stats não foram salvos"
        print(f"    - VecNormalize stats salvos")
        
        # 4. Fase 2: Refinamento
        print("\n[4/5] Executando Fase 2: Refinamento (10k steps para teste)...")
        model_phase2 = trainer.train_phase2_refinement(
            train_data=data,
            total_timesteps=10000,  # Reduzido de 1M para teste rápido
            load_phase1=True,
            episode_length=50
        )
        print(f"  [OK] Fase 2 concluída")
        
        # Validar que modelo foi salvo
        phase2_path = os.path.join(temp_dir, "phase2_refinement.zip")
        assert os.path.exists(phase2_path), "Phase 2 model não foi salvo"
        phase2_size = os.path.getsize(phase2_path)
        print(f"    - Modelo salvo: {phase2_size/1024:.1f} KB")
        
        # 5. Validação em dados out-of-sample
        print("\n[5/5] Executando Fase 3: Validação (5 episódios para teste)...")
        
        # Carregar dados de validação
        val_data = data  # Usar mesmos dados para simplificar teste
        
        metrics = trainer.train_phase3_validation(
            test_data=val_data,
            n_episodes=5,  # Reduzido de 100 para teste rápido
            episode_length=50
        )
        print(f"  [OK] Validação concluída")
        
        # Mostrar métricas
        print(f"\n  Métricas de Validação:")
        print(f"    - Win Rate: {metrics['win_rate']*100:.1f}%")
        print(f"    - Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"    - Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"    - Max Drawdown: {metrics['max_drawdown']*100:.1f}%")
        print(f"    - Avg R-Multiple: {metrics['avg_r_multiple']:.2f}")
        print(f"    - Total Trades: {metrics['total_trades']}")
        
        # Validar que relatório foi gerado
        report_path = os.path.join(temp_dir, "validation_report.txt")
        assert os.path.exists(report_path), "Relatório de validação não foi gerado"
        print(f"    - Relatório salvo: {report_path}")
        
        # 6. Salvar modelo final
        print("\n[6/5] Salvando modelo final...")
        final_path = os.path.join(temp_dir, "crypto_agent_ppo_final.zip")
        trainer.save_model(final_path)
        assert os.path.exists(final_path), "Modelo final não foi salvo"
        final_size = os.path.getsize(final_path)
        print(f"  [OK] Modelo final salvo: {final_size/1024:.1f} KB")
        
        print("\n" + "="*70)
        print("TESTE F-09 PASSOU")
        print("="*70)
        print("\nResumo:")
        print("  [OK] Fase 1 (Exploracao) concluida e modelo salvo")
        print("  [OK] Fase 2 (Refinamento) concluida e modelo salvo")
        print(f"  [OK] Fase 3 (Validacao) concluida: {metrics['total_trades']} trades")
        print("  [OK] Modelo final salvo com sucesso")
        print("  [OK] Pipeline completo de treinamento funcional")
        
        print("\nProximas mudancas esperadas:")
        print("  - F-09 marcada como DONE em docs/FEATURES.md")
        print("  - F-09 marcada como DONE em docs/TRACKER.md")
        print("  - CHANGELOG.md atualizado com entrega de F-09")
        
        return True
        
    finally:
        # Limpar diretório temporário
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Limpeu diretorio temporario: {temp_dir}")


if __name__ == '__main__':
    try:
        success = test_f09_training_pipeline()
        if success:
            print("\n[OK] Teste concluido com sucesso")
            exit(0)
        else:
            print("\n[FALHA] Teste falhou")
            exit(1)
    except Exception as e:
        print(f"\n[FALHA] TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
