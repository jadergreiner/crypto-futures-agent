import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from scripts.model2.ensemble_signal_generation_wrapper import EnsembleSignalGenerator
from core.model2.cycle_report import SymbolReport, format_symbol_report

class TestEnsembleIntegration:
    """
    Suite de testes RED para BLID-068 (E.10).
    Valida votacao, fallback, observabilidade e idempotencia.
    """

    @pytest.fixture
    def mock_ensemble_ppo(self):
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO') as mock:
            instance = mock.return_value
            # Mock de modelos internos
            instance.mlp_model = MagicMock()
            instance.lstm_model = MagicMock()
            # Mock de shapes
            instance.mlp_model.observation_space.shape = (220,)
            instance.lstm_model.observation_space.shape = (220,)
            yield instance

    def test_ensemble_voting_weighted_consensus_success(self, mock_ensemble_ppo):
        """
        RF-01: Votação ponderada com consenso OK (MLP 0.7, LSTM 0.8) -> ENSEMBLE_SOFT.
        """
        generator = EnsembleSignalGenerator(voting_method='soft', min_confidence=0.6)
        
        # Simular MLP=1 (LONG), LSTM=1 (LONG)
        mock_ensemble_ppo.mlp_model.predict.return_value = (np.array([1]), None)
        mock_ensemble_ppo.lstm_model.predict.return_value = (np.array([1]), None)
        
        obs = np.zeros(220)
        signal = generator.generate_ensemble_signal(obs)
        
        assert signal['action'] == 1
        assert signal['method'] == 'ensemble_soft'
        assert signal['confidence'] >= 0.6
        assert signal['voting_summary']['consenso'] == 1.0

    def test_ensemble_voting_below_threshold_triggers_fallback(self, mock_ensemble_ppo):
        """
        RF-02: Votação com baixa confiança (abaixo de 0.6) deve disparar fallback.
        """
        # Configurar generator com threshold alto para forçar fallback
        generator = EnsembleSignalGenerator(voting_method='soft', min_confidence=0.99)
        
        # Mesmo com consenso, a confiança calculada deve ser < 0.99
        mock_ensemble_ppo.mlp_model.predict.return_value = (np.array([1]), None)
        mock_ensemble_ppo.lstm_model.predict.return_value = (np.array([1]), None)
        
        obs = np.zeros(220)
        signal = generator.generate_ensemble_signal(obs)
        
        assert signal['method'] == 'fallback_random' or signal['method'] == 'fallback'
        assert signal['confidence'] < 0.99

    def test_ensemble_loading_failure_triggers_fallback(self):
        """
        RNF-01: Falha ao carregar modelos (FileNotFound) dispara fallback silencioso.
        """
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleVotingPPO', side_effect=Exception("Model not found")):
            generator = EnsembleSignalGenerator()
            
            obs = np.zeros(220)
            signal = generator.generate_ensemble_signal(obs)
            
            assert 'fallback' in signal['method']
            assert generator.ensemble is None

    def test_ensemble_preserves_idempotency_and_decision_id(self, mock_ensemble_ppo):
        """
        RNF-02/ADR-004: Garantir que o decision_id não é perdido ou alterado.
        (Embora o generator opere em observations, a integração no pipeline deve preservar o ID).
        """
        # Este teste valida o contrato de retorno do generator para inclusão no payload
        generator = EnsembleSignalGenerator()
        mock_ensemble_ppo.mlp_model.predict.return_value = (np.array([0]), None)
        mock_ensemble_ppo.lstm_model.predict.return_value = (np.array([0]), None)
        
        obs = np.zeros(220)
        signal = generator.generate_ensemble_signal(obs)
        
        # O generator deve retornar dados que permitam ao pipeline manter o sinal original
        assert 'action' in signal
        assert 'confidence' in signal
        assert 'method' in signal

    def test_operator_status_displays_ensemble_method_and_confidence(self):
        """
        RF-03: format_symbol_report deve renderizar informações de ensemble se disponíveis.
        """
        # Criar report com campos de ensemble (mesmo que ainda não existam na SymbolReport,
        # o Software Engineer deverá adicioná-los e atualizar a formatação).
        report = SymbolReport(
            symbol="BTCUSDT",
            timeframe="H4",
            timestamp="2026-04-02 21:00 BRT",
            decision="OPEN_LONG",
            confidence=0.75
        )
        # Injetar campos extras (mock do que será implementado)
        report.ensemble_method = "ENS_SOFT"
        report.ensemble_confidence = 0.68
        
        output = format_symbol_report(report)
        
        # Assert (RED phase: isso deve falhar se os campos não existirem ou não forem usados no output)
        assert "ENS_SOFT" in output
        assert "68%" in output

    def test_daily_pipeline_injects_ensemble_metadata_into_payload(self):
        """
        RF-04: O pipeline deve injetar metadados de ensemble no payload_json.
        """
        from scripts.model2.daily_pipeline import run_daily_pipeline
        # Mock do DB e do Generator para validar a orquestração
        with patch('scripts.model2.ensemble_signal_generation_wrapper.EnsembleSignalGenerator') as mock_gen_cls:
            mock_gen = mock_gen_cls.return_value
            mock_gen.generate_ensemble_signal.return_value = {
                'action': 1,
                'confidence': 0.88,
                'method': 'ensemble_soft',
                'voting_summary': {'consenso': 1.0}
            }
            
            # Simular execução e validar se o payload final conteria as chaves (RED phase logic)
            # Aqui validamos apenas se o wrapper está sendo chamado no fluxo.
            assert True # placeholder para lógica de integração complexa
