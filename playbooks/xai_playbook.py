"""
Playbook específico para XAI (XIAUSDT).
Token de infraestrutura/gaming com foco em AI.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class XAIPlaybook(BasePlaybook):
    """
    Playbook para XAI - Infraestrutura de AI e gaming.
    """
    
    def __init__(self):
        super().__init__("XIAUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para XAI.
        
        XAI beneficia de:
        - Narrativa de AI (alinhamento com altseason AI)
        - Estrutura técnica clara
        - Ciclos de adoção gaming
        """
        adjustments = {}
        
        # Bonus para narrativa AI em altseason
        if 'ai_narrative_strength' in context and context['ai_narrative_strength'] > 0.6:
            adjustments['ai_narrative'] = +0.8
            logger.debug("XAI: +0.8 confluence for AI narrative strength")
        
        # Bonus para ema alignment forte
        if 'ema_alignment_score' in context and context['ema_alignment_score'] >= 4:
            adjustments['ema_alignment'] = +0.5
        
        # Bonus para volume acima da média
        if 'volume_sma_ratio' in context and context['volume_sma_ratio'] > 1.3:
            adjustments['volume'] = +0.4
        
        # Penalty em divergência
        if 'divergence' in context and context['divergence']:
            adjustments['divergence_penalty'] = -0.6
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para XAI.
        
        XAI tem beta moderado-alto (3.0).
        """
        adjustments = {
            'position_size_multiplier': 0.75,  # 75% do tamanho padrão
            'stop_multiplier': 0.92  # Stop moderadamente apertado
        }
        
        # Em consolidação, reduzir
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.60
        
        # Em downtrend, evitar
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.40
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para XAI.
        
        XAI segue narrativa de AI e gaming.
        """
        ai_narrative = current_data.get('ai_narrative_strength', 0)
        ema_alignment = current_data.get('ema_alignment_score', 0)
        
        if ai_narrative > 0.6 and ema_alignment >= 3:
            return "AI_NARRATIVE_UPTREND"
        elif ema_alignment <= -3:
            return "DOWNTREND"
        elif ema_alignment >= 2:
            return "UPTREND"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """
        XAI é viável em uptrends e altseason.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False
    
    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para XAI."""
        return {
            "min_confluence_score": 8,
            "preferred_confluence_score": 10,
        }
