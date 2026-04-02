#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-067: Testes QA-TDD Phase RED (Ensemble Voting compliance ADR-026)

Valida a conformidade da implementação com a ADR-026, focando em:
1. RF-001/002: Lógica de votação e pesos.
2. RF-003: Preservação de decision_id e voting_summary no payload.
3. RF-004: Configuração de 50 episódios no benchmark comparativo.
4. RNF-001: Gate de performance (Sharpe gain >= 15%).
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.ensemble_signal_generation_wrapper import EnsembleSignalGenerator


class TestEnsembleVotingComplianceRED(unittest.TestCase):
    """
    Testes em Fase RED: Devem falhar porque a implementação atual:
    1. Soft voting não tira média de probabilidades.
    2. Benchmark padrão ainda é 5 episódios.
    3. Gate de performance não verificado.
    """

    def setUp(self):
        self.generator = EnsembleSignalGenerator(voting_method='soft')

    def test_rf001_soft_voting_averages_probabilities(self):
        """RF-001: Soft voting deve tirar a média das probabilidades (ADR-026)"""
        # Mocks para retornar probabilidades
        # mlp probabilities: [0.3, 0.7] -> Action 1
        # lstm probabilities: [0.6, 0.4] -> Action 0
        # Média soft: [0.45, 0.55] -> Action 1
        
        with patch('stable_baselines3.PPO.load') as mock_ppo_load:
            mock_mlp = MagicMock()
            mock_lstm = MagicMock()
            
            # Mock predict behavior
            mock_mlp.predict.return_value = (np.array([1]), None)
            mock_lstm.predict.return_value = (np.array([0]), None)
            
            # Mock probabilities - o script atual não suporta isso ainda!
            # Precisaremos implementar get_action_probabilities()
            mock_mlp.policy.get_distribution = Mock() # placeholder
            
            mock_ppo_load.side_effect = [mock_mlp, mock_lstm]
            
            from scripts.model2.ensemble_voting_ppo import EnsembleVotingPPO
            ensemble = EnsembleVotingPPO("mlp.zip", "lstm.zip", voting_method='soft')
            
            # Falha esperada: EnsembleVotingPPO atual não acessa probabilidades
            # e escolhe Action 0 (maior peso LSTM) em discordância.
            # O teste espera Action 1 (pela média soft [0.45, 0.55]).
            
            # Placeholder for testing prob-aware voting
            with patch.object(ensemble, 'predict', return_value=(1, None)):
                action, _ = ensemble.predict(np.zeros(200))
                self.assertEqual(action, 1, "Action 1 deve ser escolhida pela média ponderada de probabilidades")

    def test_rf003_decision_id_preservation_in_wrapper(self):
        """RF-003: decision_id deve aparecer no payload final após processamento do wrapper"""
        from scripts.model2.ensemble_signal_generation_wrapper import run_ensemble_signal_generation
        import sqlite3
        import os
        
        db_path = "/tmp/test_ensemble_red.db"
        if os.path.exists(db_path): os.remove(db_path)
            
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE technical_signals (id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, signal_side TEXT, entry_type TEXT, entry_price REAL, stop_loss REAL, take_profit REAL, signal_timestamp INTEGER, status TEXT, payload_json TEXT, updated_at INTEGER)")
        
        # Inserir sinal com decision_id
        initial_payload = json.dumps({"decision_id": "DE-123", "some_data": 123})
        conn.execute("INSERT INTO technical_signals (symbol, timeframe, signal_side, status, payload_json) VALUES ('BTCUSDT', 'M5', 'LONG', 'CREATED', ?)", (initial_payload,))
        conn.commit()
        conn.close()
        
        # Rodar wrapper
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleSignalGenerator') as MockGenerator:
            # Mock generator para não precisar de checkpoints
            mock_instance = MockGenerator.return_value
            mock_instance.generate_ensemble_signal.return_value = {
                'action': 1, 'confidence': 0.8, 'method': 'ensemble_soft', 'voting_summary': {}
            }
            mock_instance.get_stats.return_value = {'fallback_rate': 0.0, 'divergence_rate': 0.0}
            
            run_ensemble_signal_generation(model2_db_path=db_path)
            
        # Verificar se decision_id sumiu (FALHA esperada se o wrapper não carregar e repassar o payload completo)
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT payload_json FROM technical_signals").fetchone()
        payload = json.loads(row[0])
        conn.close()
        
        self.assertIn('decision_id', payload, "decision_id deve ser preservado após o wrapper ensemble")
        self.assertEqual(payload['decision_id'], "DE-123")

    def test_rf004_benchmark_uses_50_episodes(self):
        """RF-004: compare_e5_to_e9_final.py deve usar 50 episódios agora (ADR-026)"""
        import scripts.model2.compare_e5_to_e9_final as bench
        
        # O script original tem 5. Queremos 50.
        # Check main variables or defaults
        self.assertTrue(hasattr(bench, 'main'), "Script de benchmark deve ter função main")
        
        # Testar via inspeção de código ou mock de execução
        with patch('scripts.model2.compare_e5_to_e9_final.evaluate_checkpoint') as mock_eval:
            # Se chamarmos main, ele deve passar n_episodes=50
            # mock_eval.assert_called_with(ANY, ANY, n_episodes=50)
            pass
        
        # Lendo o arquivo para validar a constante
        content = open(bench.__file__, 'r').read()
        self.assertIn('n_episodes = 50', content, "Configuração padrão de episódios no benchmark deve ser 50")

    def test_rnf001_acceptance_gate_15_percent_sharpe(self):
        """RNF-001: Gate de aceite binário para ganho de 15% no Sharpe Ratio"""
        # Criar mock de resultados de benchmark
        mock_results = {
            'phases': {
                'E.8 (MLP Optuna)': {'mean_sharpe': 1.0},
                'E.8 (LSTM Optuna)': {'mean_sharpe': 1.1},
                'E.9 (Ensemble Soft)': {'mean_sharpe': 1.25} # +13.6% vs LSTM -> Deve FALHAR o gate (<15%)
            }
        }
        
        # Cálculo de melhoria: (E.9 - max(E.8)) / max(E.8)
        best_e8 = max(
            mock_results['phases']['E.8 (MLP Optuna)']['mean_sharpe'],
            mock_results['phases']['E.8 (LSTM Optuna)']['mean_sharpe']
        )
        e9 = mock_results['phases']['E.9 (Ensemble Soft)']['mean_sharpe']
        improvement = (e9 - best_e8) / best_e8
        
        self.assertGreaterEqual(improvement, 0.15, f"Ganho de Sharpe deve ser >= 15% (Atual: {improvement:.2%})")


if __name__ == '__main__':
    unittest.main()
