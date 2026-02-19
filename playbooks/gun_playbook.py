"""
Playbook especializado para GUN (Gunbot).

Característica: Token de bot de trading com comunidade especializada
- Beta: 3.8 (low-cap especulativo, volatilidade muito alta)
- Classificação: Low-cap speculative niche
- Sensibilidade: Comunidade de traders, ciclos de adoção de bots
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class GUNPlaybook(BasePlaybook):
    """
    Playbook para Gunbot (GUN).
    Low-cap especulativo com beta 3.8 (comunidade niche, volatilidade alta).
    """
    
    def __init__(self):
        super().__init__("GUNUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para GUN.
        
        Gunbot é sensível a:
        - Narrativa de trading automation
        - Comunidade especializada de traders
        - Ciclos especulativos niche
        """
        adjustments = {
            "trading_automation_narrative": 1.0,  # Foco em automação
            "bot_ecosystem_adoption": 0.75,       # Comunidade botters
            "altcoin_momentum": 0.75,             # Segue altcoins
            "macro_risk_off": -2.5,               # Sofre em risk-off
            "niche_community_sentiment": 0.5,     # Comunidade pequena
        }
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para GUN.
        
        Beta 3.8 (low-cap niche, volatilidade muito alta):
        - 45% de tamanho de posição (bastante conservador)
        - SL apertado, TP próximo, breakout-only
        """
        adjustments = {
            "position_size_multiplier": 0.45,    # 45% do tamanho padrão
            "sl_atr_multiplier": 1.3,             # SL apertado (1.3x)
            "tp_atr_multiplier": 2.2,             # TP bem próximo (2.2x)
            "max_drawdown_percent": 2.2,          # Max drawdown 2.2%
            "min_confluence_required": 10,        # Requer confluência 10+
            "breakout_only": True,                # APENAS breakouts
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de GUN.
        
        GUN passa por:
        - Breakout: Saída de consolidação niche
        - Community_Hype: Crescimento comunidade
        - Peak_Interest: Máximo interesse
        - Abandonment: Volta ao esquecimento
        """
        community_participation = current_data.get("community_participation", "low")
        price_action = current_data.get("price_action", "neutral")
        
        if price_action == "breakout":
            return "breakout"
        elif community_participation == "high" and price_action == "uptrend":
            return "community_hype"
        elif price_action == "downtrend":
            return "abandonment"
        else:
            return "consolidation"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: Optional[str] = None) -> bool:
        """
        GUN (low-cap niche 3.8) APENAS em:
        - Risk-on com D1 STRONG_LONG + breakout confirmado
        - NEVER em risk-off
        - VERY RISKY - comunidade niche
        """
        if d1_bias != "STRONG_LONG":
            return False
        
        if market_regime == "RISK_ON":
            return True
        
        return False
