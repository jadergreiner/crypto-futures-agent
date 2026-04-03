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


@dataclass(frozen=True)
class EvidenceGateResult:
    """Resultado imutavel da avaliacao de evidencia do gate de saude.

    Campos:
        go: True quando todos os pilares de evidencia estao ok.
        decision: 'GO' ou 'NO_GO'.
        reasons: Lista de motivos de bloqueio (vazia em GO).
        decision_id: Correlacao idempotente da decisao.
        evidence_ref: Caminho ou referencia do artefato de evidencia.
        risk_evidence_ok: True quando evidencia de risco esta ok.
        stability_evidence_ok: True quando evidencia de estabilidade ok.
        consistency_evidence_ok: True quando evidencia de consistencia ok.
        evidence_sufficient: True quando go=True.
        evaluated_at: Timestamp ISO 8601 da avaliacao.
    """
    go: bool
    decision: str
    reasons: List[str]
    decision_id: str
    evidence_ref: Optional[str]
    risk_evidence_ok: bool
    stability_evidence_ok: bool
    consistency_evidence_ok: bool
    evidence_sufficient: bool
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


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

    def evaluate_evidence_gate(
        self,
        decision_id: str,
        risk_evidence_ok: bool,
        stability_evidence_ok: bool,
        consistency_evidence_ok: bool,
        evidence_ref: Optional[str] = None,
    ) -> EvidenceGateResult:
        """Avalia gate de evidencia do healthcheck M2 (ADR-007 + ADR-009).

        Retorna GO quando os tres pilares (risco, estabilidade, consistencia)
        estao todos ok. Fail-safe: nunca lanca excecao.

        Args:
            decision_id: Identificador idempotente da decisao.
            risk_evidence_ok: True quando risco do ciclo esta dentro dos
                limites (sem posicoes desprotegidas ou divergencias).
            stability_evidence_ok: True quando estabilidade esta ok
                (sem entradas stale ou dashboard desatualizado).
            consistency_evidence_ok: True quando consistencia esta ok
                (dashboard valido, contratos de simbolo presentes).
            evidence_ref: Caminho ou referencia do artefato de evidencia.

        Returns:
            EvidenceGateResult com decisao GO/NO_GO e rastreabilidade.
        """
        reasons: List[str] = []

        try:
            if not risk_evidence_ok:
                reasons.append(
                    "evidencia_risco_insuficiente: posicoes desprotegidas "
                    "ou divergencias de posicao detectadas"
                )
            if not stability_evidence_ok:
                reasons.append(
                    "evidencia_estabilidade_insuficiente: dashboard stale "
                    "ou entradas antigas detectadas"
                )
            if not consistency_evidence_ok:
                reasons.append(
                    "evidencia_consistencia_insuficiente: dashboard ausente "
                    "ou contratos de simbolo incompletos"
                )
        except Exception as exc:
            return EvidenceGateResult(
                go=False,
                decision="NO_GO",
                reasons=[f"erro_avaliacao: {exc}"],
                decision_id=str(decision_id),
                evidence_ref=evidence_ref,
                risk_evidence_ok=False,
                stability_evidence_ok=False,
                consistency_evidence_ok=False,
                evidence_sufficient=False,
            )

        go = len(reasons) == 0
        return EvidenceGateResult(
            go=go,
            decision="GO" if go else "NO_GO",
            reasons=reasons,
            decision_id=str(decision_id),
            evidence_ref=evidence_ref,
            risk_evidence_ok=risk_evidence_ok,
            stability_evidence_ok=stability_evidence_ok,
            consistency_evidence_ok=consistency_evidence_ok,
            evidence_sufficient=go,
        )

