"""
Gate de promocao GO/NO-GO shadow->paper/live.
Baseado na ADR-007: Promocao por evidencia.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import math

@dataclass(frozen=True)
class PromotionResult:
    """Resultado imutavel de uma avaliacao de promocao."""
    go: bool
    reasons: List[str]
    win_rate: float
    episode_count: int
    max_drawdown_pct: float
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass(frozen=True)
class PromotionConfig:
    """Configuracao de thresholds para promocao."""
    min_win_rate: float = 0.55
    min_episodes: int = 30
    max_drawdown_pct: float = 0.05

class PromotionEvaluator:
    """Avalia se um modelo candidato pode ser promovido para producao."""
    
    def __init__(self, config: Optional[PromotionConfig] = None):
        self.config = config or PromotionConfig()

    def evaluate(
        self, 
        win_rate: float, 
        episode_count: int, 
        max_drawdown_pct: float
    ) -> PromotionResult:
        """
        Executa a avaliacao binaria GO/NO-GO.
        
        Guardrail: Nunca lanca excecao, entrada invalida vira NO-GO.
        """
        reasons: List[str] = []
        
        # Validar entradas (Failsafe)
        try:
            if math.isnan(win_rate) or win_rate < 0:
                reasons.append(f"win_rate invalido: {win_rate}")
            if episode_count < 0:
                reasons.append(f"episode_count invalido: {episode_count}")
            if math.isnan(max_drawdown_pct) or max_drawdown_pct < 0:
                reasons.append(f"max_drawdown_pct invalido: {max_drawdown_pct}")
        except Exception as exc:
            return PromotionResult(
                go=False,
                reasons=[f"Erro de validacao: {exc}"],
                win_rate=0.0,
                episode_count=0,
                max_drawdown_pct=1.0
            )

        if reasons:
             return PromotionResult(
                go=False,
                reasons=reasons,
                win_rate=float(win_rate),
                episode_count=int(episode_count),
                max_drawdown_pct=float(max_drawdown_pct)
            )

        # Criterios de Promocao
        if win_rate < self.config.min_win_rate:
            reasons.append(f"win_rate {win_rate:.2f} abaixo do threshold {self.config.min_win_rate:.2f}")
            
        if episode_count < self.config.min_episodes:
            reasons.append(f"episode_count {episode_count} abaixo da exigencia minima {self.config.min_episodes}")
            
        if max_drawdown_pct > self.config.max_drawdown_pct:
            reasons.append(f"max_drawdown_pct {max_drawdown_pct:.2f} excede o limite {self.config.max_drawdown_pct:.2f}")

        return PromotionResult(
            go=len(reasons) == 0,
            reasons=reasons,
            win_rate=float(win_rate),
            episode_count=int(episode_count),
            max_drawdown_pct=float(max_drawdown_pct)
        )
