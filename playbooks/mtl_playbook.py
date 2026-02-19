"""
Playbook específico para MTL (MTLUSDT).
Token de infraestrutura de IoT e dados.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class MTLPlaybook(BasePlaybook):
    """
    Playbook para MTL - Infraestrutura de IoT e segurança de dados.
    """
    
    def __init__(self):
        super().__init__("MTLUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para MTL.
        
        MTL beneficia de:
        - Narrativa de IoT e dados
        - Ciclos de altseason
        - Estrutura técnica clara
        """
        adjustments = {}
        
        # Bonus para altseason
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.55:
            adjustments['altseason'] = +0.7
            logger.debug("MTL: +0.7 confluence for altseason")
        
        # Bonus para estrutura técnica forte
        if 'structure_clarity' in context and context['structure_clarity'] > 0.65:
            adjustments['structure'] = +0.5
        
        # Bonus para suporte bem testado
        if 'support_proximity' in context and context['support_proximity'] < 0.025:
            adjustments['support'] = +0.3
        
        # Penalty em divergência
        if 'divergence' in context and context['divergence']:
            adjustments['divergence_penalty'] = -0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para MTL.
        
        MTL tem beta moderado-alto (2.9).
        """
        adjustments = {
            'position_size_multiplier': 0.77,  # 77% do tamanho padrão
            'stop_multiplier': 0.92  # Stop moderadamente apertado
        }
        
        # Em consolidação, reduzir
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.62
        
        # Em downtrend, reduzir muito
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.46
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para MTL.
        
        MTL segue ciclos de IoT e narrativa de dados.
        """
        altseason = current_data.get('altseason_intensity', 0)
        ema_alignment = current_data.get('ema_alignment_score', 0)
        
        if altseason > 0.55 and ema_alignment >= 3:
            return "IOT_NARRATIVE_UPTREND"
        elif ema_alignment <= -3:
            return "DOWNTREND"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """
        MTL é viável em uptrends e altseason.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False
    
    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para MTL."""
        return {
            "min_confluence_score": 8,
            "preferred_confluence_score": 10,
        }
