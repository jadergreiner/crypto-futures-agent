"""Suite RED para M2-019.3 em SubAgentManager."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.sub_agent_manager import SubAgentManager


class _FakePolicy:
    def predict_values(self, observation):
        _ = observation
        return 0.42


class _FakePPO:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.policy = _FakePolicy()
        self.saved_paths: list[str] = []
        self.learn_calls: list[int] = []

    def set_env(self, env) -> None:
        self.env = env

    def learn(self, total_timesteps: int, reset_num_timesteps: bool = False):
        _ = reset_num_timesteps
        self.learn_calls.append(total_timesteps)
        return self

    def predict(self, observation, deterministic: bool = True):
        _ = observation
        _ = deterministic
        return 2, None

    def save(self, path: str) -> None:
        self.saved_paths.append(path)
        Path(path).write_text("fake-entry-model", encoding="utf-8")

    @classmethod
    def load(cls, path: str, env=None):
        _ = env
        instance = cls()
        instance.loaded_from = path
        return instance


@pytest.fixture
def manager(tmp_path: Path) -> SubAgentManager:
    return SubAgentManager(base_dir=str(tmp_path / "sub_agents"))


@pytest.fixture
def episodios_minimos() -> list[dict[str, object]]:
    return [
        {
            "id": idx,
            "symbol": "BTCUSDT",
            "features": [0.0] * 36,
            "reward_proxy": 0.1,
            "label": "win",
            "metadata": {"created_at": idx},
        }
        for idx in range(25)
    ]


def test_train_entry_agent_treina_com_entry_decision_env(
    manager: SubAgentManager,
    episodios_minimos: list[dict[str, object]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_calls: list[dict[str, object]] = []

    def _fake_entry_env(*, episodes, symbol, seed=None):
        env_calls.append({"episodes": episodes, "symbol": symbol, "seed": seed})
        return SimpleNamespace(observation_space=SimpleNamespace(shape=(36,)))

    monkeypatch.setattr(
        "agent.sub_agent_manager.EntryDecisionEnv",
        _fake_entry_env,
        raising=False,
    )
    monkeypatch.setattr(
        "agent.sub_agent_manager.DummyVecEnv",
        lambda factories: factories[0](),
        raising=False,
    )
    monkeypatch.setattr("agent.sub_agent_manager.PPO", _FakePPO, raising=False)

    result = manager.train_entry_agent(
        symbol="BTCUSDT",
        episodes=episodios_minimos,
        total_timesteps=1000,
    )

    assert result["success"] is True
    assert env_calls[0]["symbol"] == "BTCUSDT"
    assert env_calls[0]["episodes"] == episodios_minimos


def test_predict_entry_modelo_existente_retorna_acao_valida(
    manager: SubAgentManager,
) -> None:
    manager._entry_agents["BTCUSDT"] = _FakePPO()

    action, confidence = manager.predict_entry("BTCUSDT", [0.0] * 36)

    assert action in {0, 1, 2}
    assert isinstance(action, int)
    assert isinstance(confidence, float)


def test_predict_entry_modelo_ausente_retorna_neutral(
    manager: SubAgentManager,
) -> None:
    action, confidence = manager.predict_entry("ETHUSDT", [0.0] * 36)

    assert (action, confidence) == (0, 0.0)


def test_predict_entry_excecao_retorna_neutral_sem_raise(
    manager: SubAgentManager,
) -> None:
    class _BrokenModel(_FakePPO):
        def predict(self, observation, deterministic: bool = True):
            _ = observation
            _ = deterministic
            raise RuntimeError("falha inferencia")

    manager._entry_agents["BTCUSDT"] = _BrokenModel()

    action, confidence = manager.predict_entry("BTCUSDT", [0.0] * 36)

    assert (action, confidence) == (0, 0.0)


def test_nome_arquivo_entry_separado_de_gestao(
    manager: SubAgentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agent.sub_agent_manager.PPO", _FakePPO, raising=False)
    manager.agents["BTCUSDT"] = _FakePPO()
    manager._entry_agents["BTCUSDT"] = _FakePPO()

    manager.save_all()

    assert (manager.base_dir / "BTCUSDT_ppo.zip").exists()
    assert (manager.base_dir / "BTCUSDT_entry_ppo.zip").exists()


def test_load_all_carrega_modelos_de_entrada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_dir = tmp_path / "sub_agents"
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "BTCUSDT_entry_ppo.zip").write_text("fake", encoding="utf-8")
    monkeypatch.setattr("agent.sub_agent_manager.PPO", _FakePPO)

    manager = SubAgentManager(base_dir=str(base_dir))

    assert "BTCUSDT" in manager._entry_agents
