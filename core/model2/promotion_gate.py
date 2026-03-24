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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


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

    def __init__(self, config: PromotionConfig | None = None) -> None:
        self._config = config or PromotionConfig()

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
