"""
Configuração PPO Phase 4 — Hiperparâmetros Conservadores
=========================================================

Baseado em F-12 Reward Function (7/7 ML-validated).
Objetivo: Treinar agente por 5-7 dias com convergência estável.

Data: 2026-02-22
Deadline: 2026-02-23 14:00 UTC
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PPOConfig:
    """Configuração PPO Phase 4 — Implementação conservadora."""

    # ============================================================================
    # ALGORITMO PPO — Hiperparâmetros Principais
    # ============================================================================

    # Learning rate conservador (evita divergência, controla mudanças de política)
    learning_rate: float = 3e-4
    """
    Taxa de aprendizado do agente.
    - 3e-4: Conservador, evita divergência em RL
    - Alternativas: 1e-3 (agressivo), 5e-5 (muito lento)
    - Recomendado começar conservador, aumentar se convergência muito lenta
    """

    # Batch size — balanceado para 700 candles histórico
    batch_size: int = 64
    """
    Tamanho do batch para update da política.
    - 64: Balanced para ~700 candles histórico
    - Depende de n_steps (2048) → 2048/64 = 32 mini-batches
    - Alternatives: 32 (mais steps), 128 (menos steps)
    """

    # N-steps: Número de environment steps antes de policy update
    n_steps: int = 2048
    """
    Número de steps antes de fazer update da política (PPO rollout).
    - 2048: ~4-5 episódios completos (500 steps cada)
    - Recalcular se episode length mudar significativamente
    - Fórmula: n_steps = num_episodes * episode_length
    """

    # N-epochs: Quantas vezes treinar no mesmo batch
    n_epochs: int = 10
    """
    Número de vezes que o PPO treina no mesmo batch antes do próximo rollout.
    - 10: Standard, balanço entre convergência e computation
    - Alternatives: 5 (convergência mais rápida), 20 (convergência lenta)
    """

    # Gamma: Desconto de rewards futuros
    gamma: float = 0.99
    """
    Fator de desconto para rewards futuros.
    - 0.99: Padrão em RL, "pesa" o futuro próximo
    - Alternatives: 0.95 (future less important), 0.999 (future more important)
    """

    # GAE Lambda: Generalized Advantage Estimation
    gae_lambda: float = 0.95
    """
    Balanceamento entre bias e variance na estimativa de vantagem.
    - 0.95: Padrão, reduz variance mantendo alguns bias
    - Alternatives: 0.9 (menos variance), 0.99 (mais variance)
    """

    # Entropy coefficient: Exploração vs Exploitation
    ent_coef: float = 0.001
    """
    Coefficient de penalidade por entropia baixa (menos exploração).
    - 0.001: BAIXO — modelo já converged, não queremos exploração excessiva
    - Alternatives: 0.01 (mais exploração), 0.0001 (menos exploração)
    - Recomendação: Começar com 0.001, aumentar a 0.005 se converge muito rápido
    """

    # Clipping de política: Limita mudanças por step
    clip_range: float = 0.2
    """
    PPO clipping range — limita how much policy can change per update.
    - 0.2: Padrão, evita large policy changes
    - Alternatives: 0.1 (mais conservador), 0.3 (mais agressivo)
    """

    # Value function coefficient
    vf_coef: float = 0.5
    """
    Weight da value function loss na loss total.
    - 0.5: Balanço padrão
    - Alternatives: 0.1 (menos importância do value), 1.0 (mais importância)
    """

    # Gradient clipping
    max_grad_norm: float = 0.5
    """
    Máximo valor absoluto de gradient antes de clipping.
    - 0.5: Conservador, evita exploding gradients
    - Alternatives: 1.0 (less clipping), 0.1 (more aggressive clipping)
    """

    # ============================================================================
    # TREINAMENTO — Timesteps e Duração
    # ============================================================================

    # Total de timesteps a treinar
    total_timesteps: int = 500_000
    """
    Total de environment steps para treinar.
    - 500k: ~5-7 dias de treinamento
    - Cálculo: 500k steps / ~1000 steps/hora = ~500 horas = ~21 dias CPU
      (Mas com GPU/parallelization pode ser 5-7 dias)
    - Resumo: 2048 steps → 244 rollouts → 10 epochs → ~25 min por 100k steps
    """

    # ============================================================================
    # REWARD INTEGRATION — F-12 Reward Function
    # ============================================================================

    reward_clip: float = 10.0
    """
    Limita rewards a ±10.0 para estabilidade numérica.
    - 10.0: Padrão da F-12 reward function
    - Evita que outliers dominem o treinamento
    """

    reward_components: Dict[str, float] = None
    """Componentes de reward (r_pnl, r_hold_bonus, etc)."""

    def __post_init__(self):
        """Inicializa componentes de reward padrão."""
        if self.reward_components is None:
            self.reward_components = {
                'r_pnl': 1.0,
                'r_hold_bonus': 1.0,
                'r_invalid_action': 1.0,
                'r_out_of_market': 1.0
            }

    # ============================================================================
    # NORMALIZATION (VecNormalize)
    # ============================================================================

    norm_obs: bool = True
    """Normalizar observações (padronizar features)."""

    norm_reward: bool = True
    """Normalizar rewards (important para estabilidade)."""

    clip_obs: float = 10.0
    """Clip observações a ±10.0 para evitar outliers."""

    clip_reward: float = 10.0
    """Clip rewards a ±10.0 (mesmo valor que reward_clip)."""

    # ============================================================================
    # LOGGING & MONITORAMENTO
    # ============================================================================

    verbose: int = 1
    """Nível de logging (0=silent, 1=info, 2=debug)."""

    log_interval: int = 1000
    """Log a cada N steps."""

    tensorboard_enabled: bool = True
    """Se TensorBoard logging deve ser ativado."""

    tensorboard_log_dir: str = "logs/ppo_training/tensorboard"
    """Diretório para logs de TensorBoard."""

    # ============================================================================
    # VALIDAÇÃO DURANTE TREINAMENTO
    # ============================================================================

    enable_convergence_monitoring: bool = True
    """Ativar monitoramento de convergência."""

    check_interval: int = 50  # Episodes
    """Validar convergência a cada N episódios."""

    max_no_improve_episodes: int = 100
    """Para treinamento se não melhorar por N episódios."""

    kl_divergence_threshold: float = 0.05
    """Aviso se KL divergence > isso (indicador de mudança de policy)."""

    # ============================================================================
    # CHECKPOINTING
    # ============================================================================

    checkpoint_dir: str = "models/ppo_phase4"
    """Diretório para salvar checkpoints."""

    save_interval: int = 50_000  # Steps
    """Salvar checkpoint a cada N steps."""

    save_on_good_sharpe: bool = True
    """Salvar checkpoint automático se Sharpe > 0.7 (good checkpoint)."""

    # ============================================================================
    # ENVIRONMENT
    # ============================================================================

    episode_length: int = 500
    """Número de H4 candles por episódio."""

    initial_capital: float = 10000
    """Capital inicial por episódio."""

    # ============================================================================
    # DEFAULT VALIDATION THRESHOLDS (para monitoring)
    # ============================================================================

    # These match backtest_metrics.py gates
    sharpe_target: float = 1.0  # Minimum acceptable Sharpe
    max_dd_target: float = 15.0  # Maximum acceptable drawdown %
    win_rate_target: float = 45.0  # Minimum acceptable win rate %
    profit_factor_target: float = 1.5  # Minimum acceptable profit factor
    consecutive_losses_target: int = 5  # Maximum acceptable consecutive losses
    calmar_target: float = 2.0  # Minimum acceptable Calmar ratio

    def to_dict(self) -> Dict[str, Any]:
        """Retorna configuração como dicionário."""
        return {
            'learning_rate': self.learning_rate,
            'batch_size': self.batch_size,
            'n_steps': self.n_steps,
            'n_epochs': self.n_epochs,
            'gamma': self.gamma,
            'gae_lambda': self.gae_lambda,
            'ent_coef': self.ent_coef,
            'clip_range': self.clip_range,
            'vf_coef': self.vf_coef,
            'max_grad_norm': self.max_grad_norm,
            'total_timesteps': self.total_timesteps,
            'reward_clip': self.reward_clip,
            'norm_obs': self.norm_obs,
            'norm_reward': self.norm_reward,
            'clip_obs': self.clip_obs,
            'clip_reward': self.clip_reward,
            'verbose': self.verbose,
            'log_interval': self.log_interval,
            'tensorboard_enabled': self.tensorboard_enabled,
            'tensorboard_log_dir': self.tensorboard_log_dir,
            'checkpoint_dir': self.checkpoint_dir,
            'episode_length': self.episode_length,
            'initial_capital': self.initial_capital,
            'sharpe_target': self.sharpe_target,
            'max_dd_target': self.max_dd_target,
            'win_rate_target': self.win_rate_target,
            'profit_factor_target': self.profit_factor_target,
            'consecutive_losses_target': self.consecutive_losses_target,
            'calmar_target': self.calmar_target,
        }

    @staticmethod
    def phase4_conservative() -> 'PPOConfig':
        """Retorna configuração Phase 4 recomendada (conservadora)."""
        return PPOConfig()


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def get_ppo_config(phase: str = "phase4") -> PPOConfig:
    """
    Retorna configuração PPO para uma fase específica.

    Args:
        phase: 'phase4' (padrão), 'aggressive', 'stable'

    Returns:
        PPOConfig configurado
    """
    if phase == "phase4":
        return PPOConfig.phase4_conservative()
    elif phase == "aggressive":
        config = PPOConfig.phase4_conservative()
        config.learning_rate = 5e-4
        config.ent_coef = 0.005
        return config
    elif phase == "stable":
        config = PPOConfig.phase4_conservative()
        config.learning_rate = 1e-4
        config.ent_coef = 0.0005
        return config
    else:
        raise ValueError(f"Unknown phase: {phase}")


if __name__ == "__main__":
    """Teste da configuração."""
    config = PPOConfig.phase4_conservative()
    print("Phase 4 PPO Config (Conservative)")
    print("=" * 80)
    import json
    print(json.dumps(config.to_dict(), indent=2))
    print("\nReward Components:")
    print(json.dumps(config.reward_components, indent=2))
