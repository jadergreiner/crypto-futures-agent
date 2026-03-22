"""
Testes para EntryDecisionEnv.

Modulo: tests/test_entry_decision_env.py
Escopo: Validar Gym.Env, action/observation spaces, reset, step e edge cases
"""

import json
import pytest
import numpy as np
from agent.entry_decision_env import EntryDecisionEnv, check_entry_decision_env


class TestEntryDecisionEnvInit:
    """Testes de inicializacao"""

    def test_init_empty_episodes(self):
        """Deve inicializar com lista vazia"""
        env = EntryDecisionEnv(episodes=[], symbol="TEST")
        assert env.episodes == []
        assert env.current_episode is None
        assert env.step_count == 0
        env.close()

    def test_init_with_episodes(self):
        """Deve inicializar com episodios"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes, symbol="BTCUSDT")
        assert len(env.episodes) == 1
        assert env.symbol == "BTCUSDT"
        env.close()

    def test_action_space(self):
        """Action space deve ser Discrete(3)"""
        env = EntryDecisionEnv()
        assert env.action_space.n == 3
        env.close()

    def test_observation_space(self):
        """Observation space deve ser Box(36,)"""
        env = EntryDecisionEnv()
        assert env.observation_space.shape == (36,)
        assert env.observation_space.low.min() == -1.0
        assert env.observation_space.high.max() == 1.0
        env.close()


class TestEntryDecisionEnvReset:
    """Testes de reset"""

    def test_reset_empty(self):
        """Reset com episodios vazios deve retornar dummy"""
        env = EntryDecisionEnv(episodes=[], symbol="TEST")
        obs, info = env.reset()
        assert obs.shape == (36,)
        assert np.all(obs == 0.0)  # Dummy e zerado
        assert isinstance(info, dict)
        assert "episode" in info
        env.close()

    def test_reset_with_episodes(self):
        """Reset com episodios deve retornar state valido"""
        episodes = [
            {
                "state_t_json": json.dumps(np.random.randn(36).tolist()),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)
        obs, info = env.reset()
        assert obs.shape == (36,)
        assert np.all(np.isfinite(obs))
        assert np.all(obs >= -1.0) and np.all(obs <= 1.0)
        env.close()

    def test_reset_selects_random_episode(self):
        """Reset deve selecionar episodios aleatorios"""
        episodes = [
            {
                "state_t_json": json.dumps([float(i)] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            }
            for i in range(5)
        ]
        env = EntryDecisionEnv(episodes=episodes, seed=42)
        obs1, _ = env.reset()
        obs2, _ = env.reset()
        # Pode ser igual ou diferente (aleatorio)
        assert obs1.shape == obs2.shape == (36,)
        env.close()

    def test_reset_with_seed(self):
        """Reset com seed deve ser reproducivel"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env1 = EntryDecisionEnv(episodes=episodes, seed=42)
        env2 = EntryDecisionEnv(episodes=episodes, seed=42)
        obs1, _ = env1.reset(seed=42)
        obs2, _ = env2.reset(seed=42)
        np.testing.assert_array_almost_equal(obs1, obs2)
        env1.close()
        env2.close()


class TestEntryDecisionEnvStep:
    """Testes de step"""

    def test_step_returns_correct_types(self):
        """Step deve retornar (obs, reward, terminated, truncated, info)"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)
        env.reset()
        obs, reward, terminated, truncated, info = env.step(1)

        assert isinstance(obs, np.ndarray)
        assert obs.shape == (36,)
        assert isinstance(reward, float)
        assert isinstance(terminated, (bool, np.bool_))
        assert isinstance(truncated, (bool, np.bool_))
        assert isinstance(info, dict)
        env.close()

    def test_step_extracts_reward(self):
        """Step deve extrair reward retroativo"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.75,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)
        env.reset()
        _, reward, _, _, _ = env.step(1)
        assert reward == 0.75
        env.close()

    def test_step_respects_done_flag(self):
        """Step deve respeitar flag done"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": False,
                "outcome_json": json.dumps({"status": "ok"}),
            },
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)

        # Episodio 1 (done=False)
        env.reset()
        _, _, terminated, _, _ = env.step(1)
        assert terminated is False

        # Episodio 2 (done=True)
        env.reset()
        _, _, terminated, _, _ = env.step(1)
        assert terminated is True

        env.close()

    def test_step_without_reset_raises(self):
        """Step sem reset deve levantar erro"""
        env = EntryDecisionEnv()
        with pytest.raises(RuntimeError):
            env.step(1)
        env.close()


class TestEntryDecisionEnvObservationExtraction:
    """Testes de extracao de features"""

    def test_extract_observation_from_list(self):
        """Deve extrair features de lista JSON"""
        env = EntryDecisionEnv()
        # Usar features no range esperado [-1, 1]
        features = [float(i) / 36.0 for i in range(36)]
        state_json = json.dumps(features)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        np.testing.assert_array_almost_equal(obs, np.array(features, dtype=np.float32))
        env.close()

    def test_extract_observation_from_dict(self):
        """Deve extrair features de dict JSON"""
        env = EntryDecisionEnv()
        features_dict = {"features": [0.1 * i for i in range(36)]}
        state_json = json.dumps(features_dict)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        env.close()

    def test_extract_observation_padding(self):
        """Deve fazer padding se features < 36"""
        env = EntryDecisionEnv()
        features = [0.1] * 20
        state_json = json.dumps(features)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        np.testing.assert_array_almost_equal(obs[:20], np.array(features, dtype=np.float32))
        np.testing.assert_array_almost_equal(obs[20:], np.zeros(16, dtype=np.float32))
        env.close()

    def test_extract_observation_truncation(self):
        """Deve truncar se features > 36"""
        env = EntryDecisionEnv()
        features = [0.1 * i for i in range(50)]
        state_json = json.dumps(features)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        env.close()

    def test_extract_observation_nan_handling(self):
        """Deve converter NaN para 0"""
        env = EntryDecisionEnv()
        features = [0.1] * 36
        features[5] = float("nan")
        state_json = json.dumps(features)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        assert obs[5] == 0.0  # NaN -> 0
        env.close()

    def test_extract_observation_clipping(self):
        """Deve clipar para [-1, 1]"""
        env = EntryDecisionEnv()
        features = [10.0] * 36  # Valores fora do range
        state_json = json.dumps(features)
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        assert np.all(obs >= -1.0) and np.all(obs <= 1.0)
        env.close()

    def test_extract_observation_invalid_json(self):
        """Deve retornar zeros em caso de JSON invalido"""
        env = EntryDecisionEnv()
        state_json = "invalid json"
        obs = env._extract_observation(state_json)

        assert obs.shape == (36,)
        np.testing.assert_array_equal(obs, np.zeros(36, dtype=np.float32))
        env.close()


class TestEntryDecisionEnvDummyEpisode:
    """Testes de episodio dummy"""

    def test_dummy_episode_structure(self):
        """Dummy episode deve ter estrutura valida"""
        env = EntryDecisionEnv()
        dummy = env._load_dummy_episode()

        assert "state_t_json" in dummy
        assert "action_t" in dummy
        assert "reward_t" in dummy
        assert "state_t1_json" in dummy
        assert "done" in dummy
        assert "outcome_json" in dummy
        env.close()

    def test_dummy_episode_is_neutral(self):
        """Dummy episode deve ter acao NEUTRAL (0)"""
        env = EntryDecisionEnv()
        dummy = env._load_dummy_episode()
        assert dummy["action_t"] == 0

    def test_dummy_episode_zero_reward(self):
        """Dummy episode deve ter reward 0"""
        env = EntryDecisionEnv()
        dummy = env._load_dummy_episode()
        assert dummy["reward_t"] == 0.0


class TestEntryDecisionEnvSetEpisodes:
    """Testes de set_episodes"""

    def test_set_episodes(self):
        """Deve atualizar lista de episodios"""
        env = EntryDecisionEnv(episodes=[])
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env.set_episodes(episodes)
        assert len(env.episodes) == 1
        env.close()


class TestEntryDecisionEnvStatistics:
    """Testes de get_statistics"""

    def test_statistics_empty(self):
        """Deve retornar zeros quando sem episodios"""
        env = EntryDecisionEnv(episodes=[])
        stats = env.get_statistics()

        assert stats["n_episodes"] == 0
        assert stats["mean_reward"] == 0.0
        assert stats["std_reward"] == 0.0
        env.close()

    def test_statistics_with_episodes(self):
        """Deve calcular estatisticas corretas"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 1.0,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)
        stats = env.get_statistics()

        assert stats["n_episodes"] == 2
        assert stats["mean_reward"] == 0.75
        assert stats["min_reward"] == 0.5
        assert stats["max_reward"] == 1.0
        env.close()


class TestEntryDecisionEnvValidation:
    """Testes de validacao Gym"""

    def test_gym_check_env(self):
        """Deve passar em gym.utils.check_env"""
        result = check_entry_decision_env()
        assert result is True


class TestEntryDecisionEnvIntegration:
    """Testes de integracao ponta-a-ponta"""

    def test_full_episode_loop(self):
        """Deve completar loop completo reset -> steps"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)

        obs, info = env.reset()
        assert obs.shape == (36,)

        obs, reward, terminated, truncated, info = env.step(1)
        assert obs.shape == (36,)
        assert reward == 0.5
        assert terminated is True
        assert truncated is False

        env.close()

    def test_multiple_resets(self):
        """Deve suportar multiplos resets sequenciais"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": 1,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            },
        ]
        env = EntryDecisionEnv(episodes=episodes)

        for _ in range(3):
            obs, info = env.reset()
            assert obs.shape == (36,)
            env.step(1)

        env.close()

    def test_all_actions(self):
        """Deve aceitar todas as actions (0, 1, 2)"""
        episodes = [
            {
                "state_t_json": json.dumps([0.1] * 36),
                "action_t": i,
                "reward_t": 0.5,
                "state_t1_json": json.dumps([0.2] * 36),
                "done": True,
                "outcome_json": json.dumps({"status": "ok"}),
            }
            for i in range(3)
        ]
        env = EntryDecisionEnv(episodes=episodes)

        for action in [0, 1, 2]:
            env.reset()
            obs, reward, _, _, info = env.step(action)
            assert obs.shape == (36,)
            assert "action" in info
            assert info["action"] == env.action_to_str[action]

        env.close()
