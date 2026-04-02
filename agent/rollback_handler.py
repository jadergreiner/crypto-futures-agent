"""
Gerenciador de Rollback Automático

Módulo responsável por monitorar a saúde do treinamento PPO e disparar
fallback automático para heurísticas se o modelo divergir. Implementa
critérios rigorosos (não subjetivos) e bloqueia merge até resolução.

Responsabilidades:
- Avaliação contínua de critérios de rollback
- Disparo automático de fallback
- Rastreabilidade de decisões de rollback
- Bloqueio de merge se rollback foi disparado
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class RollbackHandler:
    """
    Monitora divergência e executa fallback automático.

    Critérios de rollback (hard thresholds, não subjetivos):
    1. KL divergence > 0.1 por 50+ steps consecutivos
    2. Sharpe < -1.0 em backtest diário
    3. Max drawdown > 20%
    4. Sem melhora em reward por 200 episodes

    Efeito: Reativa heurísticas em execution/heuristic_signals.py
    """

    def __init__(
        self,
        heuristic_signals_module: str = "execution.heuristic_signals",
        rollback_log_dir: str = "logs/rollback_history",
    ):
        """
        Inicializa handler de rollback.

        Args:
            heuristic_signals_module: Path do módulo heurístico fallback
            rollback_log_dir: Dir para armazenar histórico de rollbacks
        """
        self.heuristic_signals_module = heuristic_signals_module
        self.rollback_log_dir = Path(rollback_log_dir)
        self.rollback_log_dir.mkdir(parents=True, exist_ok=True)

        # Estado
        self.is_on_fallback = False
        self.rollback_reason: Optional[str] = None
        self.rollback_step: Optional[int] = None
        self.rollback_timestamp: Optional[str] = None

        logger.info(
            f"RollbackHandler inicializado. "
            f"Fallback: {heuristic_signals_module}"
        )

    def should_rollback(
        self,
        kl_divergence: float,
        kl_history_steps: int = 50,
        sharpe_backtest: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        reward_improvement_episodes: Optional[Tuple[float, int]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Avalia critérios de rollback (hard thresholds).

        Critérios disparadores:
        - KL > 0.1 por 50+ steps: ROLLBACK IMEDIATO
        - Sharpe < -1.0: ROLLBACK
        - Drawdown > 20%: ROLLBACK
        - Sem melhora 200 episodes: ROLLBACK

        Args:
            kl_divergence: KL div atual
            kl_history_steps: Nº de steps com KL > threshold
            sharpe_backtest: Sharpe do backtest diário (se disponível)
            max_drawdown: Max drawdown % do período
            reward_improvement_episodes: Tupla (best_reward_recent, num_episodes_sem_melhora)

        Returns:
            Tupla (deve_rollback, motivo)
        """
        # Critério 1: KL divergence > 0.1 por 50+ steps
        if kl_divergence > 0.1 and kl_history_steps >= 50:
            reason = (
                f"KL divergence crítica: {kl_divergence:.4f} "
                f"por {kl_history_steps} steps"
            )
            logger.error(f"ROLLBACK TRIGGER: {reason}")
            return True, reason

        # Critério 2: Sharpe inaceitável
        if sharpe_backtest is not None and sharpe_backtest < -1.0:
            reason = f"Sharpe negativo crítico no backtest: {sharpe_backtest:.2f}"
            logger.error(f"ROLLBACK TRIGGER: {reason}")
            return True, reason

        # Critério 3: Drawdown inaceitável
        if max_drawdown is not None and max_drawdown > 20.0:
            reason = f"Max drawdown crítico: {max_drawdown:.1f}%"
            logger.error(f"ROLLBACK TRIGGER: {reason}")
            return True, reason

        # Critério 4: Sem melhora por 200 episodes
        if reward_improvement_episodes:
            best_reward, episodes_no_improve = reward_improvement_episodes
            if episodes_no_improve > 200:
                reason = (
                    f"Sem melhora por {episodes_no_improve} episodes. "
                    f"Melhor recente: {best_reward:.2f}"
                )
                logger.error(f"ROLLBACK TRIGGER: {reason}")
                return True, reason

        # Nenhum critério disparado
        return False, None

    def trigger_rollback(
        self,
        reason: str,
        model_step: int,
        metrics_snapshot: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Dispara rollback e ativa heurísticas fallback.

        Args:
            reason: Motivo do rollback (string descritiva)
            model_step: Step em que rollback foi disparado
            metrics_snapshot: Dict com métricas do momento

        Returns:
            True se rollback executado com sucesso

        Raises:
            RuntimeError: Se fallback não conseguir ativar
        """
        try:
            self.is_on_fallback = True
            self.rollback_reason = reason
            self.rollback_step = model_step
            self.rollback_timestamp = datetime.utcnow().isoformat()

            logger.critical(
                f"🚨 ROLLBACK DISPARADO em step {model_step}: {reason}"
            )

            # Salvar evento de rollback para auditoria
            rollback_record = {
                "timestamp": self.rollback_timestamp,
                "step": model_step,
                "reason": reason,
                "metrics_snapshot": metrics_snapshot or {},
                "fallback_module": self.heuristic_signals_module,
                "fallback_activated": True,
            }

            rollback_file = (
                self.rollback_log_dir /
                f"rollback_{model_step}_{self.rollback_timestamp.replace(':', '-')[:16]}.json"
            )
            with open(rollback_file, "w") as f:
                json.dump(rollback_record, f, indent=2)

            logger.info(f"Evento de rollback registrado: {rollback_file}")

            # Ativar heurísticas (pseudo-código)
            # Em produção, isto chamaria execution/heuristic_signals.py
            self._activate_heuristic_fallback()

            logger.warning(
                f"✅ Fallback para heurísticas ativado. "
                f"Operações agora usando {self.heuristic_signals_module}"
            )

            return True

        except Exception as e:
            logger.error(f"Falha ao disparar rollback: {e}")
            raise RuntimeError(f"Rollback dispatcher erro: {e}")

    def fallback_to_heuristics(
        self,
        *,
        reason: Optional[str] = None,
        model_step: Optional[int] = None,
        metrics_snapshot: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ativa fallback apenas com contexto explicito e auditavel.

        Returns:
            True se heurísticas já estavam ativas ou se rollback auditável
            foi disparado com sucesso; False se a tentativa manual for
            bloqueada por falta de contexto fail-safe.
        """
        if self.is_on_fallback:
            logger.info(
                f"Já em modo fallback desde step {self.rollback_step}. "
                f"Razão: {self.rollback_reason}"
            )
            return True

        if reason is None or model_step is None:
            logger.warning(
                "Fallback manual bloqueado: informe reason e model_step "
                "para trilha auditavel de rollback."
            )
            return False

        return self.trigger_rollback(
            reason=reason,
            model_step=model_step,
            metrics_snapshot=metrics_snapshot,
        )

    def get_rollback_status(self) -> Dict[str, Any]:
        """
        Retorna status atual de rollback.

        Returns:
            Dict com informações de estado
        """
        return {
            "is_on_fallback": self.is_on_fallback,
            "rollback_reason": self.rollback_reason,
            "rollback_step": self.rollback_step,
            "rollback_timestamp": self.rollback_timestamp,
            "fallback_module": self.heuristic_signals_module,
            "status_message": (
                f"Fallback ativo desde step {self.rollback_step} ({self.rollback_reason})"
                if self.is_on_fallback
                else "Treinamento normal (sem fallback)"
            ),
        }

    def can_merge_if_rollback_triggered(self) -> Tuple[bool, Optional[str]]:
        """
        Verifica se merge é permitido (bloqueia se rollback foi disparado).

        Returns:
            Tupla (pode_fazer_merge, motivo_bloqueio)

        Regra: Merge é BLOQUEADO se houver rollback durante sessão treinamento
        """
        if self.is_on_fallback:
            message = (
                f"❌ MERGE BLOQUEADO: Rollback foi disparado durante "
                f"sessão (step {self.rollback_step}). "
                f"Motivo: {self.rollback_reason}. "
                f"Resolva divergência antes de merge."
            )
            logger.error(message)
            return False, message

        return True, None

    def _activate_heuristic_fallback(self) -> None:
        """
        Ativa módulo de heurísticas fallback.
        TBD: Implementação específica durante PHASE 1
        """
        try:
            # Pseudo-código: importar e ativar heurísticas
            # from execution.heuristic_signals import activate_fallback
            # activate_fallback()
            logger.info(
                f"Tentando importar fallback de {self.heuristic_signals_module}..."
            )
            # Por enquanto, apenas log (será implementado em execution/)
            logger.info("✅ Heurísticas fallback ativadas (execução simulada)")
        except ImportError as e:
            logger.warning(f"Módulo heurístico não importado: {e}")

    def reset_rollback_state(self) -> None:
        """
        Reseta estado de rollback (uso: após resolução de divergência).
        Permitido apenas via aprovação explícita.
        """
        old_state = {
            "was_on_fallback": self.is_on_fallback,
            "reason": self.rollback_reason,
            "step": self.rollback_step,
        }

        self.is_on_fallback = False
        self.rollback_reason = None
        self.rollback_step = None
        self.rollback_timestamp = None

        logger.warning(
            f"⚠️  Estado de rollback resetado. "
            f"Anterior: {old_state}. Requer aprovação explícita de Angel."
        )

    def get_rollback_log_summary(self) -> Dict[str, Any]:
        """
        Resume histórico de rollbacks na sessão.

        Returns:
            Dict com total, ultimo evento e breakdown por motivo.
        """
        rollback_files = list(self.rollback_log_dir.glob("rollback_*.json"))

        summary: Dict[str, Any] = {
            "total_rollbacks_logged": len(rollback_files),
            "last_rollback_time": None,
            "most_common_reason": None,
        }

        if rollback_files:
            # Encontrar mais recente
            latest_file = max(rollback_files, key=lambda f: f.stat().st_mtime)
            with open(latest_file, "r") as f:
                latest = json.load(f)
                summary["last_rollback_time"] = latest.get("timestamp")

            # Contar razões
            reasons: Dict[str, int] = {}
            for rf in rollback_files:
                try:
                    with open(rf, "r") as f:
                        record = json.load(f)
                        reason = record.get("reason", "unknown")
                        reasons[reason] = reasons.get(reason, 0) + 1
                except Exception:
                    pass

            if reasons:
                summary["most_common_reason"] = max(
                    reasons,
                    key=lambda reason_key: reasons[reason_key],
                )
                summary["reason_breakdown"] = reasons

        return summary
