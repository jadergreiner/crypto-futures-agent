"""
Utilitários para Stable-Baselines3 no Windows.

Soluciona problema: OSError: [Errno 22] Invalid argument durante model.learn()

Problema: SB3 tenta criar arquivos de log interno com nomes/paths inválidos no Windows.
Solução: Desabilitar ou redirecionar logger para local seguro.
"""

import logging
from typing import Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


def create_safe_sb3_logger(
    folder: Optional[Union[str, Path]] = None,
    use_csv: bool = False,
    use_stdout: bool = False,
):
    """
    Cria um logger seguro do Stable-Baselines3 para Windows.

    Evita OSError durante model.learn() desabilitando formatos problemáticos
    (especialmente TensorBoard).

    Args:
        folder: Diretório para salvar logs. Se None, não salva em arquivos.
        use_csv: Se deve salvar métricas em CSV (recomendado com folder válido).
        use_stdout: Se deve imprimir em stdout durante training.

    Returns:
        Logger do SB3 configurado com formato seguro.

    Example:
        >>> logger = create_safe_sb3_logger(use_stdout=True)
        >>> model = PPO("MlpPolicy", env)
        >>> model.set_logger(logger)
        >>> model.learn(100000)
    """
    from stable_baselines3.common.logger import configure

    formats = []

    if use_stdout:
        formats.append("stdout")

    if use_csv and folder:
        formats.append("csv")

    # Se não tem nenhum formato, logger vazio (mais seguro)
    if not formats:
        logger.info(
            "Criando logger vazio do SB3 (nenhum arquivo será salvo)"
        )
    else:
        logger.info(
            f"Criando logger SB3 com formatos: {formats}"
            + (f" em {folder}" if folder else "")
        )

    # Nunca usar 'tensorboard' no Windows - causa OSError
    # Formatos seguros: csv, log, json, stdout

    return configure(folder=str(folder) if folder else None, format_strings=formats)


def attach_safe_logger_to_model(
    model,
    folder: Optional[Union[str, Path]] = None,
    use_csv: bool = False,
    use_stdout: bool = False,
):
    """
    Anexa um logger seguro a um modelo PPO/A2C/DDPG/etc do SB3.

    Deve ser chamado antes de model.learn().

    Args:
        model: Modelo do SB3 (PPO, A2C, etc.)
        folder: Diretório para logs (nullptr = sem arquivo).
        use_csv: Se deve salvar em CSV.
        use_stdout: Se deve imprimir em stdout.

    Returns:
        Model com logger anexado (para encadeamento).

    Example:
        >>> model = PPO("MlpPolicy", env)
        >>> model = attach_safe_logger_to_model(model, use_stdout=True)
        >>> model.learn(100000)
    """
    logger_obj = create_safe_sb3_logger(
        folder=folder,
        use_csv=use_csv,
        use_stdout=use_stdout,
    )
    model.set_logger(logger_obj)
    logger.info("Logger seguro anexado ao modelo SB3")
    return model


def make_ppo_windows_safe(
    policy: str,
    env,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    clip_range: float = 0.2,
    ent_coef: float = 0.001,
    vf_coef: float = 0.5,
    max_grad_norm: float = 0.5,
    device: str = "auto",
    log_csv: bool = False,
    log_stdout: bool = False,
    **kwargs,
):
    """
    Cria um modelo PPO pré-configurado e seguro para Windows.

    Automaticamente desabilita TensorBoard e anexa logger seguro.

    Args:
        policy: Tipo de policy ("MlpPolicy", "CnnPolicy", etc.)
        env: Ambiente Gym/Gymnasium
        learning_rate: Taxa de aprendizado
        n_steps: Steps antes de update
        batch_size: Tamanho do batch
        n_epochs: Épocas de treinamento por rollout
        gamma: Desconto
        gae_lambda: GAE lambda
        clip_range: Clipping de PPO
        ent_coef: Coef de entropia
        vf_coef: Coef de value function
        max_grad_norm: Gradient norm máximo
        device: Device ("auto", "cuda", "cpu")
        log_csv: Se deve salvar em CSV
        log_stdout: Se deve imprimir em stdout
        **kwargs: Argumentos adicionais para PPO

    Returns:
        Modelo PPO pronto para treino sem OSError.

    Example:
        >>> model = make_ppo_windows_safe(
        ...     "MlpPolicy",
        ...     env,
        ...     learning_rate=3e-4,
        ...     log_stdout=True
        ... )
        >>> model.learn(100000)
    """
    from stable_baselines3 import PPO

    # Sempre desabilitar verbose e tensorboard no Windows
    kwargs.setdefault("verbose", 0)
    kwargs.setdefault("tensorboard_log", None)

    # Criar modelo com hiperparâmetros seguros
    model = PPO(
        policy=policy,
        env=env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        max_grad_norm=max_grad_norm,
        device=device,
        **kwargs,
    )

    # Anexar logger seguro
    attach_safe_logger_to_model(
        model,
        folder=None,  # Não salvar em arquivo por padrão
        use_csv=log_csv,
        use_stdout=log_stdout,
    )

    logger.info("Modelo PPO criado com segurança para Windows")
    return model


def validate_sb3_setup():
    """
    Valida que o SB3 está instalado corretamente.

    Verifica imports e imprime configuração do ambiente.

    Raises:
        ImportError: Se SB3 não está instalado.
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.logger import configure
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info("✅ Stable-Baselines3: OK")
        logger.info(f"✅ PyTorch: OK (device={device})")
        logger.info(f"✅ SB3 Logger: OK")

        return True

    except ImportError as e:
        logger.error(f"❌ Erro ao importar SB3: {e}")
        raise ImportError(
            "Stable-Baselines3 não instalado. "
            "Execute: pip install stable-baselines3"
        ) from e


if __name__ == "__main__":
    # Teste rápido
    logging.basicConfig(level=logging.INFO)

    print("\n=== Validando setup SB3 ===")
    validate_sb3_setup()

    print("\n=== Testando criar logger seguro ===")
    logger_obj = create_safe_sb3_logger(use_stdout=True)
    print(f"Logger type: {type(logger_obj)}")
    print(f"Logger dir: {logger_obj.get_dir()}")

    print("\n✅ Validação completa")
