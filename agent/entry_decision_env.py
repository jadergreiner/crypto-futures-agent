"""
Ambiente Gym para decisao de entrada por simbolo via RL.

Modulo: agent/entry_decision_env.py
Autor: Agente de Desenvolvimento M2-019.1
Data: 2026-03-22

Responsabilidade:
- Encapsular ciclo de decisao de entrada (LONG/SHORT/NEUTRAL)
- Carregar episodios de treinamento da tabela learning_episodes
- Fornecer interface Gym.Env para treinamento PPO

Action Space:
- Discrete(3): 0=NEUTRAL, 1=LONG, 2=SHORT

Observation Space:
- Box(36,): Estado consolidado normalizado em [-1, 1]
  * 24 features OHLCV multi-TF (H1, H4, D1)
  * 6 features tecnicas (RSI, MACD, BB, ATR, Stoch, Williams)
  * 3 features fundamentais (FR, LS-ratio, OI)
  * 3 features SMC context (zona, tendencia, invalidacao)

Reward:
- Retroativo: outcome real de signal_execution
- Range estiamdo: [-1.0, 1.0]

Reset:
- Seleciona episodio aleatorio de lista ou dummy se vazio
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import gymnasium as gym
from gymnasium import spaces


logger = logging.getLogger(__name__)


class EntryDecisionEnv(gym.Env):
    """
    Ambiente Gym para decisao RL de entrada por simbolo.

    Atributos:
        episodes (List[Dict]): Lista de episodios de treinamento
        current_episode (Optional[Dict]): Episodio atual
        step_count (int): Numero de steps no episodio
        metadata (Dict): Configuracoes de renderizacao
        action_to_str (Dict): Mapeamento de indice para string de acao
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        episodes: Optional[List[Dict]] = None,
        symbol: str = "UNKNOWN",
        seed: Optional[int] = None,
    ):
        """
        Inicializa o ambiente.

        Args:
            episodes: Lista de episodios de treinamento (pode ser vazio)
            symbol: Simbolo do ativo (para logging)
            seed: Seed para reprodutibilidade (np.random.seed)
        """
        super().__init__()

        self.symbol = symbol
        self.episodes = episodes or []
        self.current_episode = None
        self.step_count = 0
        self.episode_count = 0

        # Seed para reproducibilidade
        if seed is not None:
            np.random.seed(seed)

        # Action space: 0=NEUTRAL, 1=LONG, 2=SHORT
        self.action_space = spaces.Discrete(3)
        self.action_to_str = {0: "NEUTRAL", 1: "LONG", 2: "SHORT"}

        # Observation space: 36 features normalizadas em [-1, 1]
        # 24 (OHLCV multi-TF) + 6 (tecnicas) + 3 (fundamentais)
        # + 3 (SMC context)
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(36,),
            dtype=np.float32
        )

        logger.info(
            f"EntryDecisionEnv({symbol}) inicializado com "
            f"{len(self.episodes)} episodios"
        )

    def _load_dummy_episode(self) -> Dict[str, Any]:
        """
        Gera episodio dummy quando nenhum treinamento disponivel.

        Returns:
            Dict com estrutura minima (state_t, action_t, reward_t, etc)
        """
        dummy = {
            "state_t_json": json.dumps(
                [0.0] * 36  # 36 features zeradas
            ),
            "action_t": 0,  # NEUTRAL
            "reward_t": 0.0,  # Sem reward
            "state_t1_json": json.dumps(
                [0.0] * 36
            ),
            "done": True,
            "outcome_json": json.dumps(
                {"status": "dummy", "reason": "no_episodes"}
            ),
        }
        return dummy

    def _extract_observation(self, state_json: str) -> np.ndarray:
        """
        Extrai features de estado JSON e retorna array normalizado.

        Args:
            state_json: JSON string com features (pode ser lista ou dict)

        Returns:
            Array np.ndarray de shape (36,) com valores em [-1, 1]
        """
        try:
            state_obj = json.loads(state_json)

            # Se for lista, converter direto para array
            if isinstance(state_obj, list):
                obs_list = state_obj[:36]  # Garantir max 36 features
            # Se for dict, extrair chave 'features' ou usar valores dict
            elif isinstance(state_obj, dict):
                obs_list = state_obj.get("features", list(state_obj.values()))
            else:
                obs_list = []

            # Padding se necessario
            while len(obs_list) < 36:
                obs_list.append(0.0)

            # Converter para array float32
            obs = np.array(obs_list[:36], dtype=np.float32)

            # Substituir NaN por 0 ANTES de clip
            obs = np.nan_to_num(obs, nan=0.0)

            # Clip para [-1, 1] (normalizacao de range)
            obs = np.clip(obs, -1.0, 1.0)

            return obs

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(
                f"Erro ao extrair state_json: {e}. "
                f"Retornando state zerado."
            )
            return np.zeros(36, dtype=np.float32)

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Remove ambiente para novo episodio.

        Args:
            seed: Seed para reproducibilidade
            options: Opcoes adicionais (nao usado)

        Returns:
            (observation, info)
        """
        if seed is not None:
            np.random.seed(seed)
            self.np_random, seed = gym.utils.seeding.np_random(seed)

        # Selecionar episodio aleatorio ou dummy
        if self.episodes:
            self.current_episode = self.episodes[
                np.random.randint(0, len(self.episodes))
            ]
            self.episode_count += 1
        else:
            self.current_episode = self._load_dummy_episode()
            logger.debug("Nenhum episodio disponivel. Usando dummy.")

        self.step_count = 0

        # Extrair estado inicial
        obs = self._extract_observation(
            self.current_episode.get("state_t_json", "{}")
        )

        info = {
            "episode": self.episode_count,
            "symbol": self.symbol,
            "action_label": self.current_episode.get(
                "action_t", 0
            ),
        }

        return obs, info

    def step(
        self,
        action: int,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executa um step no ambiente.

        Args:
            action: Indice de acao (0=NEUTRAL, 1=LONG, 2=SHORT)

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        if self.current_episode is None:
            raise RuntimeError("Chamar reset() antes de step()")

        # Extrair reward retroativo do episodio
        reward = float(
            self.current_episode.get("reward_t", 0.0)
        )

        # Verificar se episodio ja terminou
        done = bool(
            self.current_episode.get("done", True)
        )

        # Próximo estado
        next_obs = self._extract_observation(
            self.current_episode.get("state_t1_json", "{}")
        )

        self.step_count += 1

        info = {
            "step": self.step_count,
            "action": self.action_to_str.get(action, "UNKNOWN"),
            "reward": reward,
            "outcome": self.current_episode.get(
                "outcome_json", "{}"
            ),
        }

        # Terminated: episodio chegou ao final
        # Truncated: limite de steps atingido (nao aplicavel aqui)
        return next_obs, reward, done, False, info

    def render(self) -> None:
        """
        Renderizacao nao implementada para este ambiente.
        """
        pass

    def close(self) -> None:
        """
        Fecha recursos do ambiente.
        """
        pass

    def set_episodes(self, episodes: List[Dict]) -> None:
        """
        Define lista de episodios para o ambiente.

        Args:
            episodes: Lista de episodios de treinamento
        """
        self.episodes = episodes or []
        logger.info(
            f"{self.symbol}: Carregados {len(self.episodes)} episodios"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatisticas do ambiente.

        Returns:
            Dict com contagem, media de reward, etc
        """
        if not self.episodes:
            return {
                "n_episodes": 0,
                "mean_reward": 0.0,
                "std_reward": 0.0,
                "min_reward": 0.0,
                "max_reward": 0.0,
            }

        rewards = [
            float(ep.get("reward_t", 0.0))
            for ep in self.episodes
        ]

        return {
            "n_episodes": len(self.episodes),
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "min_reward": float(np.min(rewards)),
            "max_reward": float(np.max(rewards)),
        }


def check_entry_decision_env() -> bool:
    """
    Valida o ambiente com testes basicos de consistencia.

    Returns:
        True se passou todas as validacoes
    """
    try:
        env = EntryDecisionEnv(
            episodes=[],
            symbol="TEST",
            seed=42
        )

        # Teste 1: Reset
        obs, info = env.reset()
        assert obs.shape == (36,)
        assert np.all(np.isfinite(obs))

        # Teste 2: Step
        obs, reward, terminated, truncated, info = env.step(1)
        assert obs.shape == (36,)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)

        # Teste 3: Action space
        assert env.action_space.n == 3

        # Teste 4: Observation space
        assert env.observation_space.shape == (36,)

        logger.info("Environment validation: PASSED")
        env.close()
        return True
    except Exception as e:
        logger.error(f"Environment validation FAILED: {e}")
        return False
