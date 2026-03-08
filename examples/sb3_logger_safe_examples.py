"""
Exemplo: Integração do SB3 Logger Safe com Train PPO Skeleton

Este arquivo mostra como usar agent/sb3_utils.py para evitar OSError
durante model.learn() no Windows.

Três abordagens diferentes conforme o contexto:
1. Função helper simples
2. Context manager
3. Modificação direta em train_ppo_skeleton.py
"""

# ============================================================================
# ABORDAGEM 1: Uso direto da função helper
# ============================================================================

def training_example_simple():
    """Forma mais simples: uma linha de código."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from agent.sb3_utils import attach_safe_logger_to_model
    from gymnasium import Env

    # Seus setup anterior
    # env = YourCryptoEnvironment()
    # vec_env = DummyVecEnv([lambda: env])

    # ✅ Passo 1: Criar modelo com verbose=0 e tensorboard_log=None
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        verbose=0,  # Importante
        tensorboard_log=None,  # Importante
    )

    # ✅ Passo 2: Uma linha que resolve o problema
    attach_safe_logger_to_model(model, use_stdout=True)

    # ✅ Passo 3: Treinar sem OSError
    model.learn(total_timesteps=1000)

    return model


# ============================================================================
# ABORDAGEM 2: Context manager
# ============================================================================

from contextlib import contextmanager
from stable_baselines3.common.logger import configure


@contextmanager
def sb3_training_safe_context(use_stdout=False):
    """
    Context manager para garantir cleanup seguro do logger SB3.

    Usage:
        with sb3_training_safe_context(use_stdout=True):
            model = PPO("MlpPolicy", env)
            model.learn(100000)
    """
    from agent.sb3_utils import create_safe_sb3_logger

    logger = create_safe_sb3_logger(use_stdout=use_stdout)
    try:
        yield logger
    finally:
        if logger is not None:
            logger.close()


def training_example_context():
    """Usar context manager para segurança."""
    from stable_baselines3 import PPO

    # env = YourCryptoEnvironment()
    # vec_env = DummyVecEnv([lambda: env])

    with sb3_training_safe_context(use_stdout=True) as logger:
        model = PPO("MlpPolicy", env=vec_env, verbose=0, tensorboard_log=None)
        model.set_logger(logger)
        model.learn(total_timesteps=1000)

    return model


# ============================================================================
# ABORDAGEM 3: Integração em train_ppo_skeleton.py (PATCH)
# ============================================================================

PATCH_TRAIN_PPO_SKELETON = """
# Arquivo: scripts/train_ppo_skeleton.py
# Adicionar na seção de imports:

from agent.sb3_utils import attach_safe_logger_to_model

# ...

class PPOTrainer:
    # ... código existente ...

    def train(self, symbol: str = 'OGNUSDT') -> dict:
        '''Treina modelo PPO com config Phase 4.'''

        if not HAS_ML:
            logger.error("Bibliotecas ML nao disponiveis")
            return {"error": "ML libraries missing"}

        logger.info(f"[TRAINING] Iniciando treinamento para {symbol}")
        logger.info(f"  Total timesteps: {self.config.total_timesteps:,}")
        logger.info(f"  Learning rate: {self.config.learning_rate}")
        logger.info(f"  Batch size: {self.config.batch_size}")

        try:
            # 1. Preparar ambiente
            env, vec_env = self.prepare_environment(symbol)

            # 2. Criar modelo PPO com config
            logger.info("Criando modelo PPO com config Phase 4...")
            model = PPO(
                policy="MlpPolicy",
                env=vec_env,
                learning_rate=self.config.learning_rate,
                n_steps=self.config.n_steps,
                batch_size=self.config.batch_size,
                n_epochs=self.config.n_epochs,
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
                clip_range=self.config.clip_range,
                ent_coef=self.config.ent_coef,
                vf_coef=self.config.vf_coef,
                max_grad_norm=self.config.max_grad_norm,
                device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
                verbose=0,  # ✅ Adicionar
                tensorboard_log=None,  # ✅ Adicionar
            )

            # ✅ NOVA LINHA: Anexar logger seguro
            attach_safe_logger_to_model(model, use_stdout=True)

            # 3. Callbacks
            checkpoint_callback = CheckpointCallback(
                save_freq=self.config.save_interval,
                save_path=str(self.checkpoint_dir),
                name_prefix=f"{symbol}_ppo"
            )

            # 4. Treinar
            logger.info(f"Iniciando treinamento para {symbol}...")
            model.learn(
                total_timesteps=self.config.total_timesteps,
                callback=checkpoint_callback
            )

            # 5. Salvar modelo final e stats
            model_path = self.checkpoint_dir / f"{symbol}_ppo_final.zip"
            model.save(str(model_path))
            logger.info(f"[OK] Modelo salvo: {model_path}")

            # Salvar VecNormalize stats
            vecnorm_path = self.checkpoint_dir / f"{symbol}_ppo_vecnorm.pkl"
            vec_env.save(str(vecnorm_path))
            logger.info(f"[OK] VecNormalize stats salvo: {vecnorm_path}")

            return {
                "status": "SUCCESS",
                "symbol": symbol,
                "model_path": str(model_path),
                "vecnorm_path": str(vecnorm_path),
                "timesteps": self.config.total_timesteps,
                "config": self.config.to_dict()
            }

        except Exception as e:
            logger.error(f"[ERROR] Erro durante treinamento: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "ERROR",
                "symbol": symbol,
                "error": str(e)
            }
"""


# ============================================================================
# ABORDAGEM 4: Factory pattern para mais controle
# ============================================================================


class TrainingSessionWindowsSafe:
    """Classe para gerenciar treinamento seguro do SB3 no Windows."""

    def __init__(
        self,
        env,
        vec_env,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        use_logger: bool = False,
    ):
        """
        Inicializa uma sessão de treinamento segura.

        Args:
            env: Ambiente
            vec_env: Ambiente vetorizado
            learning_rate: Taxa de aprendizado
            n_steps: N-steps
            batch_size: Batch size
            n_epochs: N-epochs
            use_logger: Se deve usar logger (CSV + stdout)
        """
        self.env = env
        self.vec_env = vec_env
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.use_logger = use_logger
        self._model = None

    def create_model(self, policy: str = "MlpPolicy"):
        """Cria modelo PPO pré-configurado para Windows."""
        from stable_baselines3 import PPO

        self._model = PPO(
            policy=policy,
            env=self.vec_env,
            learning_rate=self.learning_rate,
            n_steps=self.n_steps,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            verbose=0,
            tensorboard_log=None,
        )

        # Anexar logger se solicitado
        if self.use_logger:
            attach_safe_logger_to_model(self._model, use_stdout=True)

        return self._model

    def train(self, total_timesteps: int, callback=None):
        """Executa treinamento."""
        if self._model is None:
            self.create_model()

        self._model.learn(total_timesteps=total_timesteps, callback=callback)

        return self._model

    def save(self, path: str):
        """Salva modelo."""
        if self._model:
            self._model.save(path)


def training_example_factory():
    """Usar factory pattern."""
    from stable_baselines3.common.callbacks import CheckpointCallback

    # env = YourCryptoEnvironment()
    # vec_env = DummyVecEnv([lambda: env])

    session = TrainingSessionWindowsSafe(
        env=env,
        vec_env=vec_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        use_logger=True,
    )

    callback = CheckpointCallback(save_freq=10000, save_path="./checkpoints")

    model = session.create_model()
    session.train(total_timesteps=100000, callback=callback)
    session.save("model_final.zip")

    return model


# ============================================================================
# TESTE: Validar que tudo funciona
# ============================================================================

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 70)
    print("EXEMPLOS: Desabilitar Logger SB3 no Windows")
    print("=" * 70)

    print("\n[1] Função Helper (RECOMENDADO)")
    print("   Código: attach_safe_logger_to_model(model, use_stdout=True)")

    print("\n[2] Context Manager")
    print("   Código: with sb3_training_safe_context(): ...")

    print("\n[3] Factory Pattern")
    print("   Código: TrainingSessionWindowsSafe(env, vec_env)")

    print("\n[4] Patch para train_ppo_skeleton.py")
    print("   Ver PATCH_TRAIN_PPO_SKELETON acima")

    print("\n" + "=" * 70)
    print("Para usar em seu código:")
    print("=" * 70)
    print("""
from agent.sb3_utils import attach_safe_logger_to_model

model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
attach_safe_logger_to_model(model, use_stdout=True)
model.learn(1000000)
    """)

    print("✅ Pronto para usar!")
