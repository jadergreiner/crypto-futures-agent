"""
Modulo de gate de promocao GO/NO-GO para o pipeline M2.

Implementa M2-028.1: Contrato de promocao GO/NO-GO shadow→paper.
Avalia criterios objetivos (win_rate, episodios, drawdown) e retorna
PromotionResult imutavel com decisao e motivos de bloqueio.

Guardrails:
- PromotionResult e frozen (imutavel apos criacao).
- evaluate() nunca lanca excecao; entrada invalida resulta em NO-GO.
- Thresholds padrao conservadores derivados de config/risk_params.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List


# ---------------------------------------------------------------------------
# Configuracao de thresholds
# ---------------------------------------------------------------------------

@dataclass
class PromotionConfig:
    """Thresholds configuráveis para avaliacao GO/NO-GO.

    Defaults conservadores alinhados com config/risk_params.py:
    - max_daily_drawdown_pct: 5% → drawdown maximo aceitavel para promocao
    - Episodios minimos: 30 para amostra estatisticamente relevante
    - Win-rate minimo: 55% conservador acima de aleatorio
    """

    min_win_rate: float = 0.55
    min_episodes: int = 30
    max_drawdown_pct: float = 0.05


@dataclass
class LivePromotionConfig:
    """Thresholds para promocao paper→live (M2-028.2)."""

    min_sharpe_ratio: float = 1.0
    min_reconciliation_rate: float = 0.99
    max_critical_errors: int = 0


# ---------------------------------------------------------------------------
# Resultado imutavel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromotionResult:
    """Resultado imutavel de avaliacao GO/NO-GO.

    Atributos:
        go: True se todos os criterios foram atendidos.
        reasons: Lista de motivos de bloqueio (vazia se GO=True).
        win_rate: Win-rate observado na avaliacao.
        episode_count: Numero de episodios na avaliacao.
        max_drawdown_pct: Drawdown maximo observado.
        evaluated_at: Timestamp ISO UTC da avaliacao.
    """

    go: bool
    reasons: List[str]
    win_rate: float
    episode_count: int
    max_drawdown_pct: float
    evaluated_at: str


@dataclass(frozen=True)
class LivePromotionResult:
    """Resultado imutavel da avaliacao paper→live."""

    go: bool
    reasons: List[str]
    sharpe_ratio: float
    reconciliation_rate: float
    critical_errors: int
    manual_approved: bool
    approver_id: str | None
    approval_justification: str | None
    rollback_to_paper: bool
    evaluated_at: str


# ---------------------------------------------------------------------------
# Avaliador principal
# ---------------------------------------------------------------------------

class PromotionEvaluator:
    """Avalia criterios de promocao GO/NO-GO shadow→paper.

    Uso:
        config = PromotionConfig(min_win_rate=0.55, min_episodes=30, max_drawdown_pct=0.05)
        evaluator = PromotionEvaluator(config=config)
        result = evaluator.evaluate(win_rate=0.60, episode_count=50, max_drawdown_pct=0.03)
        if result.go:
            # promover para paper
    """

    def __init__(
        self,
        config: PromotionConfig | None = None,
        live_config: LivePromotionConfig | None = None,
    ) -> None:
        self._config = config or PromotionConfig()
        self._live_config = live_config or LivePromotionConfig()

    def evaluate(
        self,
        win_rate: float,
        episode_count: int,
        max_drawdown_pct: float,
    ) -> PromotionResult:
        """Avalia criterios e retorna PromotionResult imutavel.

        Nunca lanca excecao. Entrada invalida (NaN, negativa) resulta em NO-GO.

        Args:
            win_rate: Taxa de acerto no periodo avaliado (0.0 a 1.0).
            episode_count: Numero de episodios capturados.
            max_drawdown_pct: Drawdown maximo observado no periodo (0.0 a 1.0).

        Returns:
            PromotionResult com decisao GO/NO-GO e lista de motivos.
        """
        reasons: List[str] = []
        evaluated_at = datetime.now(tz=timezone.utc).isoformat()

        try:
            # Validacao de entrada — qualquer valor invalido vira NO-GO
            _win_rate = float(win_rate)
            _episode_count = int(episode_count)
            _drawdown = float(max_drawdown_pct)

            if math.isnan(_win_rate) or math.isnan(_drawdown):
                reasons.append("entrada_invalida: valor NaN detectado")
                _win_rate = -1.0
                _drawdown = float("inf")
                _episode_count = -1

            if _win_rate < 0 or _episode_count < 0 or _drawdown < 0:
                reasons.append("entrada_invalida: valor negativo detectado")
                # Normaliza para garantir que todos os checks abaixo falhem
                if _win_rate < 0:
                    _win_rate = -1.0
                if _episode_count < 0:
                    _episode_count = -1
                if _drawdown < 0:
                    _drawdown = float("inf")

            # Avaliacao de criterios
            if _win_rate < self._config.min_win_rate:
                reasons.append(
                    f"win_rate {_win_rate:.3f} < minimo {self._config.min_win_rate:.3f}"
                )

            if _episode_count < self._config.min_episodes:
                reasons.append(
                    f"episode_count {_episode_count} < minimo {self._config.min_episodes}"
                )

            if _drawdown > self._config.max_drawdown_pct:
                reasons.append(
                    f"drawdown {_drawdown:.3f} > maximo {self._config.max_drawdown_pct:.3f}"
                )

        except Exception as exc:  # guardrail: nunca lanca
            reasons.append(f"erro_interno: {exc}")
            _win_rate = win_rate if isinstance(win_rate, float) else 0.0
            _episode_count = episode_count if isinstance(episode_count, int) else 0
            _drawdown = max_drawdown_pct if isinstance(max_drawdown_pct, float) else 1.0

        return PromotionResult(
            go=len(reasons) == 0,
            reasons=reasons,
            win_rate=_win_rate if "_win_rate" in dir() else 0.0,
            episode_count=_episode_count if "_episode_count" in dir() else 0,
            max_drawdown_pct=_drawdown if "_drawdown" in dir() else 1.0,
            evaluated_at=evaluated_at,
        )

    def evaluate_paper_to_live(
        self,
        *,
        sharpe_ratio: float,
        reconciliation_rate: float,
        critical_errors: int,
        manual_approved: bool,
        approver_id: str | None,
        approval_justification: str | None,
        post_promotion_critical_event: bool = False,
    ) -> LivePromotionResult:
        """Avalia promocao paper→live com aprovacao manual obrigatoria.

        Guardrails:
        - Manual approval e obrigatorio para GO.
        - Erro critico pos-promocao sinaliza rollback_to_paper=True.
        - Fail-safe: entrada invalida retorna NO-GO sem excecao.
        """
        reasons: List[str] = []
        evaluated_at = datetime.now(tz=timezone.utc).isoformat()
        rollback_to_paper = bool(post_promotion_critical_event)
        _sharpe = 0.0
        _reconciliation = 0.0
        _critical_errors = 999

        try:
            _sharpe = float(sharpe_ratio)
            _reconciliation = float(reconciliation_rate)
            _critical_errors = int(critical_errors)
            _manual_approved = bool(manual_approved)
            _approver_id = approver_id.strip() if isinstance(approver_id, str) and approver_id.strip() else None
            _justification = (
                approval_justification.strip()
                if isinstance(approval_justification, str) and approval_justification.strip()
                else None
            )

            if math.isnan(_sharpe) or math.isnan(_reconciliation):
                reasons.append("entrada_invalida: sharpe/reconciliation NaN")
                _sharpe = float("-inf")
                _reconciliation = -1.0
                _critical_errors = 999

            if _sharpe < self._live_config.min_sharpe_ratio:
                reasons.append(
                    f"sharpe_ratio {_sharpe:.3f} < minimo {self._live_config.min_sharpe_ratio:.3f}"
                )

            if _reconciliation < self._live_config.min_reconciliation_rate:
                reasons.append(
                    "reconciliation_rate "
                    f"{_reconciliation:.3f} < minimo {self._live_config.min_reconciliation_rate:.3f}"
                )

            if _critical_errors > self._live_config.max_critical_errors:
                reasons.append(
                    f"critical_errors {_critical_errors} > maximo {self._live_config.max_critical_errors}"
                )

            if not _manual_approved:
                reasons.append("manual_approval_required")
            if _manual_approved and _approver_id is None:
                reasons.append("approver_id_required")
            if _manual_approved and _justification is None:
                reasons.append("approval_justification_required")

        except Exception as exc:  # guardrail: nunca lanca
            reasons.append(f"erro_interno: {exc}")
            _manual_approved = False
            _approver_id = None
            _justification = None

        if rollback_to_paper:
            reasons.append("post_promotion_critical_event_detected")

        return LivePromotionResult(
            go=len(reasons) == 0,
            reasons=reasons,
            sharpe_ratio=_sharpe,
            reconciliation_rate=_reconciliation,
            critical_errors=_critical_errors,
            manual_approved=_manual_approved if "_manual_approved" in locals() else False,
            approver_id=_approver_id if "_approver_id" in locals() else None,
            approval_justification=_justification if "_justification" in locals() else None,
            rollback_to_paper=rollback_to_paper,
            evaluated_at=evaluated_at,
        )


def is_preflight_compatible_for_live(preflight_summary: dict[str, Any]) -> bool:
    """Retorna True quando o preflight esta apto para promocao paper→live."""
    status = str(preflight_summary.get("status", "")).strip().lower()
    return status == "ok"
