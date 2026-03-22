#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-068 E.10: Testes de Geracao de Sinais Ensemble em Mock Environment

Validar gerador ensemble com votação soft/hard em ambiente mock,
sem dependência de checkpoints reais ou banco de dados.
"""

import json
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class MockModel:
    """Mock de modelo PPO compatível com SB3."""

    def __init__(self, forced_action: int = 0, observation_shape: tuple = (200,)):
        self.forced_action = forced_action
        self.observation_space = Mock(shape=observation_shape)

    def predict(self, observation, deterministic=True):
        """Retorna acao e valor V mock."""
        return np.array([self.forced_action]), np.array([0.5])


class TestEnsembleSignalGeneratorE10(unittest.TestCase):
    """Suite de testes para BLID-068 E.10"""

    def setUp(self):
        """Setup común para todos os testes"""
        # Import aqui para evitar erros de path na importacao
        try:
            from scripts.model2.ensemble_signal_generation_wrapper import (
                EnsembleSignalGenerator,
            )
            self.EnsembleSignalGenerator = EnsembleSignalGenerator
        except ImportError as e:
            self.skipTest(f"Nao foi possivel importar ensemble wrapper: {e}")

    def test_01_ensemble_generator_soft_voting_consenso(self):
        """T01: Soft voting com consenso (ambos votam 1)"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            # Mock ensemble com ambas votadas 1
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=1)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator(
                voting_method='soft',
                mlp_weight=0.48,
                lstm_weight=0.52,
                min_confidence=0.6
            )
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)
            result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertEqual(result['action'], 1, "Acao deve ser 1 (consenso)")
            self.assertGreater(result['confidence'], 0.7, "Confidence > 0.7 em consenso")
            self.assertEqual(result['method'], 'ensemble_soft')
            self.assertEqual(result['voting_summary']['consenso'], 1.0)
            self.assertFalse(result['voting_summary']['divergence'])

    def test_02_ensemble_generator_hard_voting_divergencia(self):
        """T02: Hard voting com divergência (MLP=0, LSTM=1)"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=0)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator(
                voting_method='hard',
                mlp_weight=0.48,
                lstm_weight=0.52,
                min_confidence=0.5
            )
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)
            result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertIn(result['action'], [0, 1], "Acao deve ser 0 ou 1")
            self.assertLess(result['voting_summary']['consenso'], 1.0, "Consenso < 1.0 em divergencia")
            self.assertTrue(result['voting_summary']['divergence'])
            self.assertEqual(gen.votes_diverged, 1)

    def test_03_ensemble_confidence_acima_threshold(self):
        """T03: Confidence acima do threshold mínimo"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=1)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator(
                voting_method='soft',
                min_confidence=0.8
            )
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)
            result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertGreaterEqual(
                result['confidence'],
                gen.min_confidence,
                "Confidence deve estar acima do threshold"
            )
            self.assertEqual(result['method'], 'ensemble_soft')
            self.assertEqual(gen.fallback_used, 0)

    def test_04_ensemble_fallback_baixa_confidence(self):
        """T04: Fallback acionado por confidence baixa"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=0)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator(
                voting_method='soft',
                min_confidence=0.95  # Threshold muito alto
            )
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)

            with patch('numpy.random.choice', return_value=0):
                result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertEqual(result['method'], 'fallback_random', "Deve usar fallback")
            self.assertEqual(gen.fallback_used, 1, "Contador fallback deve incrementar")

    def test_05_ensemble_peso_normalizacao(self):
        """T05: Pesos são normalizados corretamente"""
        gen = self.EnsembleSignalGenerator(
            mlp_weight=40,
            lstm_weight=60,
            min_confidence=0.5
        )

        # Asserts: sum deve ser 1.0
        self.assertAlmostEqual(
            gen.mlp_weight + gen.lstm_weight,
            1.0,
            places=5,
            msg="Soma de pesos deve ser 1.0"
        )
        # LSTM com weight maior
        self.assertGreater(gen.lstm_weight, gen.mlp_weight)

    def test_06_ensemble_observation_shape_adaptation(self):
        """T06: Adaptacao de shape de observacao"""
        gen = self.EnsembleSignalGenerator()

        # Teste com observation flat 200
        obs_flat = np.random.randn(200).astype(np.float32)
        adapted = gen._adapt_observation_for_model(obs_flat, MockModel())
        self.assertEqual(adapted.shape, (200,))

        # Teste com observation sequencial (10, 20)
        obs_seq = np.random.randn(10, 20).astype(np.float32)
        adapted = gen._adapt_observation_for_model(obs_seq, MockModel(observation_shape=(10, 20)))
        self.assertEqual(adapted.shape, (10, 20))

    def test_07_ensemble_action_normalization(self):
        """T07: Normalizacao de acoes para inteiro"""
        gen = self.EnsembleSignalGenerator()

        # Teste com array 1D
        action_array = np.array([1.5])
        action_int = gen._action_to_int(action_array)
        self.assertEqual(action_int, 1)
        self.assertIsInstance(action_int, int)

        # Teste com escalar
        action_scalar = 0.9
        action_int = gen._action_to_int(action_scalar)
        self.assertEqual(action_int, 0)

    def test_08_ensemble_stats_tracking(self):
        """T08: Rastreamento de stats (calls, divergencias, fallbacks)"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=0)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator()
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)

            # Fazer 5 chamadas
            for _ in range(5):
                result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertEqual(gen.total_calls, 5, "Total calls deve ser 5")
            self.assertGreater(gen.votes_diverged, 0, "Deve ter divergencias")

    def test_09_ensemble_metadata_inclusion(self):
        """T09: Metadata incluso na resposta"""
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') \
             as MockEnsemble:
            mock_ensemble = MagicMock()
            mock_ensemble.mlp_model = MockModel(forced_action=1)
            mock_ensemble.lstm_model = MockModel(forced_action=1)
            MockEnsemble.return_value = mock_ensemble

            gen = self.EnsembleSignalGenerator()
            gen.ensemble = mock_ensemble

            obs = np.random.randn(200).astype(np.float32)
            result = gen.generate_ensemble_signal(obs)

            # Asserts
            self.assertIn('metadata', result)
            self.assertIn('timestamp', result['metadata'])
            self.assertIn('observation_shape', result['metadata'])
            self.assertEqual(result['metadata']['observation_shape'], (200,))

    def test_10_run_ensemble_signal_generation_mock_db(self):
        """T10: Teste de run_ensemble_signal_generation com mock DB (SKIP)"""
        # SKIP: Teste requer schema completo de modelo2.db
        # Equivalente é validado por integracao com daily_pipeline
        self.skipTest("Requer schema completo do DB - testado em integracao diaria")


class TestEnsembleIntegrationE10(unittest.TestCase):
    """Testes de integração do ensemble com daily_pipeline"""

    def test_11_ensemble_importable_in_daily_pipeline(self):
        """T11: Ensemble pode ser importado e utilizado em daily_pipeline"""
        try:
            from scripts.model2.ensemble_signal_generation_wrapper import (
                run_ensemble_signal_generation,
            )
            from scripts.model2.daily_pipeline import STAGES

            # Verificar se ensemble está na pipeline
            stage_names = [stage[0] for stage in STAGES]
            self.assertIn('ensemble_signal_generation', stage_names)

        except ImportError as e:
            self.skipTest(f"Nao foi possivel importar ensemble ou pipeline: {e}")

    def test_12_ensemble_config_parameters(self):
        """T12: Parametros de configuracao do ensemble sao validados"""
        gen = self.EnsembleSignalGenerator(
            voting_method='soft',
            min_confidence=0.6
        )

        self.assertIn(gen.voting_method, ['soft', 'hard'])
        self.assertGreaterEqual(gen.min_confidence, 0.0)
        self.assertLessEqual(gen.min_confidence, 1.0)

    def setUp(self):
        """Setup para testes de integração"""
        try:
            from scripts.model2.ensemble_signal_generation_wrapper import (
                EnsembleSignalGenerator,
            )
            self.EnsembleSignalGenerator = EnsembleSignalGenerator
        except ImportError:
            pass


if __name__ == '__main__':
    unittest.main()
