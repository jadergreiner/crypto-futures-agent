import unittest
from unittest.mock import MagicMock, patch
import json
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Import target modules (even if they don't exist yet, we write the test first - TDD)
# Note: we might need to mock the imports if the files don't exist
try:
    from scripts.model2.ensemble_signal_generation_wrapper import EnsembleSignalGenerator
except ImportError:
    EnsembleSignalGenerator = MagicMock()

class TestEnsembleRecalibrationRed(unittest.TestCase):
    """
    Suite RED para BLID-110: Refino Adaptativo de Pesos do Ensemble.
    
    Valida:
    1. RF-110.1: Monitor 48h (Win Rate calculation)
    2. RF-110.2: Weight Sugestion (Adaptive weighting)
    3. RF-110.3: Fallback (Default weights)
    4. RF-110.4: Payload Audit (applied_weights in JSON)
    """

    def setUp(self):
        self.db_path = ":memory:"
        self.conn = sqlite3.connect(self.db_path)
        self._create_mock_tables()

    def tearDown(self):
        self.conn.close()

    def _create_mock_tables(self):
        self.conn.execute("""
            CREATE TABLE signal_executions (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                source TEXT,
                sub_model TEXT,
                pnl_net REAL,
                executed_at INTEGER
            )
        """)
        self.conn.commit()

    def _insert_trades(self, trades):
        self.conn.executemany(
            "INSERT INTO signal_executions (symbol, source, sub_model, pnl_net, executed_at) VALUES (?, ?, ?, ?, ?)",
            trades
        )
        self.conn.commit()

    @patch('core.model2.ensemble_recalibrator.sqlite3.connect')
    def test_recalibrator_calculates_correct_weights_from_db(self, mock_connect):
        """RF-110.1/RF-110.2: Monitor 48h e Sugestao de Pesos"""
        from core.model2.ensemble_recalibrator import EnsembleRecalibrator
        
        mock_connect.return_value = self.conn
        now = int(datetime.utcnow().timestamp() * 1000)
        
        # Simular performance: MLP melhor que LSTM
        # MLP: 4 wins, 1 loss (80% WR)
        # LSTM: 2 wins, 3 losses (40% WR)
        trades = [
            ('BTCUSDT', 'RL_MODEL', 'MLP', 10.0, now - 1000),
            ('BTCUSDT', 'RL_MODEL', 'MLP', 10.0, now - 2000),
            ('BTCUSDT', 'RL_MODEL', 'MLP', 10.0, now - 3000),
            ('BTCUSDT', 'RL_MODEL', 'MLP', 10.0, now - 4000),
            ('BTCUSDT', 'RL_MODEL', 'MLP', -5.0, now - 5000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', 10.0, now - 1000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', 10.0, now - 2000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', -5.0, now - 3000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', -5.0, now - 4000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', -5.0, now - 5000),
        ]
        self._insert_trades(trades)
        
        recalibrator = EnsembleRecalibrator(db_path=self.db_path)
        weights = recalibrator.calculate_weights(symbol='BTCUSDT', window_hours=48)
        
        # Pesos devem estar inclinados para MLP (original 0.48)
        self.assertGreater(weights['mlp_weight'], 0.48)
        self.assertLess(weights['lstm_weight'], 0.52)
        self.assertAlmostEqual(weights['mlp_weight'] + weights['lstm_weight'], 1.0)

    @patch('core.model2.ensemble_recalibrator.sqlite3.connect')
    def test_recalibrator_uses_default_weights_if_insufficient_data(self, mock_connect):
        """RF-110.3: Fallback para pesos estáticos se < 5 trades"""
        from core.model2.ensemble_recalibrator import EnsembleRecalibrator
        
        mock_connect.return_value = self.conn
        now = int(datetime.utcnow().timestamp() * 1000)
        
        # Apenas 2 trades - insuficiente
        trades = [
            ('BTCUSDT', 'RL_MODEL', 'MLP', 10.0, now - 1000),
            ('BTCUSDT', 'RL_MODEL', 'LSTM', 10.0, now - 1000),
        ]
        self._insert_trades(trades)
        
        recalibrator = EnsembleRecalibrator(db_path=self.db_path)
        weights = recalibrator.calculate_weights(symbol='BTCUSDT', window_hours=48)
        
        self.assertEqual(weights['mlp_weight'], 0.48)
        self.assertEqual(weights['lstm_weight'], 0.52)

    @patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO')
    def test_ensemble_signal_generator_applies_recalibrated_weights(self, mock_ppo):
        """RF-110.4: Visibilidade dos pesos aplicados no payload"""
        from scripts.model2.ensemble_signal_generation_wrapper import EnsembleSignalGenerator
        
        # Mocking models to avoid loading heavy weights
        # EnsembleVotingPPO is initialized in __init__
        mock_ppo_instance = MagicMock()
        mock_ppo.return_value = mock_ppo_instance
        
        # Setup specific weights
        custom_mlp = 0.60
        custom_lstm = 0.40
        
        generator = EnsembleSignalGenerator(
            mlp_weight=custom_mlp,
            lstm_weight=custom_lstm
        )
        
        # Mock predict to return consensus
        mock_ppo_instance.mlp_model.predict.return_value = (np.array([1]), None)
        mock_ppo_instance.lstm_model.predict.return_value = (np.array([1]), None)
        mock_ppo_instance.mlp_model.observation_space.shape = (220,)
        mock_ppo_instance.lstm_model.observation_space.shape = (220,)
        
        obs = np.zeros(220)
        signal = generator.generate_ensemble_signal(obs)
        
        # Verificar se os pesos aplicados estao no summary
        payload = signal.get('voting_summary', {})
        self.assertIn('applied_weights', payload)
        self.assertAlmostEqual(payload['applied_weights']['mlp'], 0.60)
        self.assertAlmostEqual(payload['applied_weights']['lstm'], 0.40)

    @patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO')
    def test_ensemble_signal_generator_fails_safe_on_recalibration_error(self, mock_ppo):
        """RNF-110.3: Fail-safe para pesos default em caso de exception"""
        from scripts.model2.ensemble_signal_generation_wrapper import EnsembleSignalGenerator
        
        # Se passarmos pesos invalidos ou ocorrer erro na carga, deve usar default
        # No construtor atual ele ja normaliza (total_weight > 0 else 0.5)
        generator = EnsembleSignalGenerator(mlp_weight=-1, lstm_weight=-1)
        
        self.assertEqual(generator.mlp_weight, 0.5) # Fallback hardcoded no __init__ se total <= 0
        self.assertEqual(generator.lstm_weight, 0.5)

if __name__ == '__main__':
    unittest.main()
