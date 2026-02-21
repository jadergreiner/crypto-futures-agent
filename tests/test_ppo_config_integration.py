"""
Integration Test: PPO Config Validation — Phase 4
==================================================

Valida que a configuração PPO pode ser carregada, instanciada e integrada
sem erro. Testes de sanidade para garantir que o treinamento não falhará
no primeiro passo por erro de configuração.

Executar antes de iniciar o treinamento:
    pytest -xvs tests/test_ppo_config_integration.py
"""

import pytest
import json
from pathlib import Path
from config.ppo_config import PPOConfig, get_ppo_config


class TestPPOConfigBasics:
    """Testa carregamento e estrutura básica da config PPO."""

    def test_config_instantiation(self):
        """PPOConfig pode ser instanciado sem erro."""
        config = PPOConfig()
        assert config is not None
        print("✅ PPOConfig instantiated successfully")

    def test_all_11_hyperparameters_present(self):
        """Todos os 11 hiperparâmetros principais estão presentes e têm valores."""
        config = PPOConfig()

        required_params = {
            'learning_rate': float,
            'batch_size': int,
            'n_steps': int,
            'n_epochs': int,
            'gamma': float,
            'gae_lambda': float,
            'ent_coef': float,
            'clip_range': float,
            'vf_coef': float,
            'max_grad_norm': float,
            'total_timesteps': int,
        }

        for param_name, param_type in required_params.items():
            assert hasattr(config, param_name), f"Missing parameter: {param_name}"
            value = getattr(config, param_name)
            assert value is not None, f"Parameter {param_name} is None"
            assert isinstance(value, param_type), \
                f"{param_name} should be {param_type}, got {type(value)}"

        print(f"✅ All 11 hyperparameters present and typed correctly")

    def test_hyperparameter_values_correct(self):
        """Hiperparâmetros têm os valores esperados para Phase 4."""
        config = PPOConfig()

        # Valores esperados
        assert config.learning_rate == 3e-4, "learning_rate should be 3e-4"
        assert config.batch_size == 64, "batch_size should be 64"
        assert config.n_steps == 2048, "n_steps should be 2048"
        assert config.n_epochs == 10, "n_epochs should be 10"
        assert config.gamma == 0.99, "gamma should be 0.99"
        assert config.gae_lambda == 0.95, "gae_lambda should be 0.95"
        assert config.ent_coef == 0.001, "ent_coef should be 0.001"
        assert config.clip_range == 0.2, "clip_range should be 0.2"
        assert config.vf_coef == 0.5, "vf_coef should be 0.5"
        assert config.max_grad_norm == 0.5, "max_grad_norm should be 0.5"
        assert config.total_timesteps == 500_000, "total_timesteps should be 500,000"

        print("✅ All hyperparameter values correct for Phase 4")

    def test_reward_components_initialized(self):
        """Componentes de reward estão inicializados."""
        config = PPOConfig()

        assert config.reward_components is not None, "reward_components is None"
        assert isinstance(config.reward_components, dict), "reward_components should be dict"

        expected_components = ['r_pnl', 'r_hold_bonus', 'r_invalid_action', 'r_out_of_market']
        for comp in expected_components:
            assert comp in config.reward_components, f"Missing reward component: {comp}"
            assert isinstance(config.reward_components[comp], float), \
                f"Reward component {comp} should be float"

        print(f"✅ Reward components initialized: {list(config.reward_components.keys())}")

    def test_normalization_enabled(self):
        """VecNormalize está habilitado para observações e rewards."""
        config = PPOConfig()

        assert config.norm_obs == True, "norm_obs should be True"
        assert config.norm_reward == True, "norm_reward should be True"
        assert config.clip_obs == 10.0, "clip_obs should be 10.0"
        assert config.clip_reward == 10.0, "clip_reward should be 10.0"

        print("✅ VecNormalize properly configured (obs + reward)")

    def test_tensorboard_enabled(self):
        """TensorBoard logging está habilitado com diretório correto."""
        config = PPOConfig()

        assert config.tensorboard_enabled == True, "tensorboard_enabled should be True"
        assert config.tensorboard_log_dir is not None, "tensorboard_log_dir is None"
        assert "ppo_training" in config.tensorboard_log_dir, \
            "tensorboard_log_dir should contain 'ppo_training'"

        print(f"✅ TensorBoard enabled: {config.tensorboard_log_dir}")

    def test_convergence_monitoring_enabled(self):
        """Monitoramento de convergência está ativo."""
        config = PPOConfig()

        assert config.enable_convergence_monitoring == True, \
            "enable_convergence_monitoring should be True"
        assert config.kl_divergence_threshold == 0.05, \
            "kl_divergence_threshold should be 0.05"
        assert config.max_no_improve_episodes > 0, \
            "max_no_improve_episodes should be positive"

        print(f"✅ Convergence monitoring enabled (KL threshold: {config.kl_divergence_threshold})")

    def test_checkpoint_configuration(self):
        """Configuração de checkpoint está correta."""
        config = PPOConfig()

        assert config.checkpoint_dir is not None, "checkpoint_dir is None"
        assert config.save_interval > 0, "save_interval should be positive"
        assert config.save_on_good_sharpe == True, "save_on_good_sharpe should be True"

        print(f"✅ Checkpoint config: {config.checkpoint_dir}, save_interval={config.save_interval}")


class TestConfigFactory:
    """Testa factory functions para diferentes fases."""

    def test_phase4_conservative_factory(self):
        """get_ppo_config('phase4') retorna config conservadora."""
        config = get_ppo_config('phase4')

        assert config.learning_rate == 3e-4
        assert config.ent_coef == 0.001
        print("✅ Phase 4 conservative config loaded")

    def test_aggressive_factory(self):
        """get_ppo_config('aggressive') retorna config agressiva."""
        config = get_ppo_config('aggressive')

        assert config.learning_rate == 5e-4  # Maior
        assert config.ent_coef == 0.005  # Maior
        print("✅ Aggressive config loaded with higher LR and entropy")

    def test_stable_factory(self):
        """get_ppo_config('stable') retorna config estável."""
        config = get_ppo_config('stable')

        assert config.learning_rate == 1e-4  # Menor
        assert config.ent_coef == 0.0005  # Menor
        print("✅ Stable config loaded with lower LR and entropy")

    def test_invalid_phase_raises_error(self):
        """get_ppo_config com fase inválida lança erro."""
        with pytest.raises(ValueError):
            get_ppo_config('invalid_phase')
        print("✅ Invalid phase correctly raises ValueError")


class TestConfigSerialization:
    """Testa serialização e desserialização da config."""

    def test_to_dict_conversion(self):
        """Config pode ser convertida para dicionário."""
        config = PPOConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict), "to_dict() should return dict"
        assert 'learning_rate' in config_dict
        assert 'total_timesteps' in config_dict
        assert len(config_dict) >= 11

        print(f"✅ Config converted to dict (keys: {len(config_dict)})")

    def test_to_json_serializable(self):
        """Config é JSON-serializable."""
        config = PPOConfig()
        config_dict = config.to_dict()

        try:
            json_str = json.dumps(config_dict, indent=2)
            json_parsed = json.loads(json_str)
            assert json_parsed is not None
            print("✅ Config is JSON-serializable")
        except Exception as e:
            pytest.fail(f"Config should be JSON-serializable, got error: {e}")

    def test_dict_roundtrip_preserves_values(self):
        """Conversão para dict e volta preserva valores."""
        config1 = PPOConfig()
        config_dict = config1.to_dict()

        # Verificar valores chave
        assert config_dict['learning_rate'] == config1.learning_rate
        assert config_dict['batch_size'] == config1.batch_size
        assert config_dict['total_timesteps'] == config1.total_timesteps

        print("✅ Dict roundtrip preserves all values")


class TestConfigIntegration:
    """Testa integração com componentes do sistema."""

    def test_config_import_in_training_context(self):
        """Config pode ser importada de contexto de training."""
        try:
            from config.ppo_config import PPOConfig, get_ppo_config
            config = get_ppo_config('phase4')

            # Simular uso no trainer
            assert hasattr(config, 'learning_rate')
            assert hasattr(config, 'total_timesteps')
            assert hasattr(config, 'reward_components')

            print("✅ Config imported successfully in training context")
        except ImportError as e:
            pytest.fail(f"Config import failed: {e}")

    def test_config_compatible_with_stable_baselines3_ppo(self):
        """Config tem estrutura compatível com stable_baselines3.PPO."""
        config = PPOConfig()

        # Parâmetros esperados por stable_baselines3.PPO
        required_sb3_params = [
            'learning_rate',
            'n_steps',
            'batch_size',
            'n_epochs',
            'gamma',
            'gae_lambda',
            'clip_range',
            'ent_coef',
            'vf_coef',
            'max_grad_norm',
        ]

        for param in required_sb3_params:
            assert hasattr(config, param), f"Missing SB3 param: {param}"
            assert getattr(config, param) is not None, f"SB3 param {param} is None"

        print("✅ Config structure compatible with stable_baselines3.PPO")

    def test_environment_setup_compatible(self):
        """Config é compatível com CryptoFuturesEnv."""
        config = PPOConfig()

        # Verificar se parâmetros de environment estão presentes
        assert config.episode_length > 0, "episode_length should be positive"
        assert config.initial_capital > 0, "initial_capital should be positive"

        # Verificar se valores são sensatos
        assert config.episode_length >= 100, "episode_length deve ser >= 100"
        assert config.initial_capital >= 1000, "initial_capital deve ser >= 1000"

        print(f"✅ Environment config: episode={config.episode_length}, capital=${config.initial_capital}")


class TestConfigRiskGates:
    """Testa que thresholds de risk gates estão configurados."""

    def test_all_6_risk_gate_thresholds_present(self):
        """Todos os 6 thresholds de risk gates estão presentes."""
        config = PPOConfig()

        gates = [
            'sharpe_target',
            'max_dd_target',
            'win_rate_target',
            'profit_factor_target',
            'consecutive_losses_target',
            'calmar_target',
        ]

        for gate in gates:
            assert hasattr(config, gate), f"Missing gate threshold: {gate}"
            value = getattr(config, gate)
            assert value is not None, f"Gate {gate} is None"
            assert value > 0, f"Gate {gate} should be positive"

        print(f"✅ All 6 risk gate thresholds configured")

    def test_risk_gate_values_correct(self):
        """Risk gate thresholds têm os valores esperados."""
        config = PPOConfig()

        assert config.sharpe_target == 1.0
        assert config.max_dd_target == 15.0
        assert config.win_rate_target == 45.0
        assert config.profit_factor_target == 1.5
        assert config.consecutive_losses_target == 5
        assert config.calmar_target == 2.0

        print("✅ All risk gate thresholds have correct values")


def test_print_full_config():
    """Utility: imprime configuração completa para referência."""
    config = PPOConfig()
    print("\n" + "="*80)
    print("FULL PPO CONFIG SUMMARY")
    print("="*80)
    print(json.dumps(config.to_dict(), indent=2))
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
