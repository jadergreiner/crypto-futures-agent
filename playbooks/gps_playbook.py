"""
Playbook especializado para GPS (GPS).

Característica: Token de utilidade com narrativa emergente
- Beta: 3.5 (low-cap especulativo, volatilidade alta)
- Classificação: Low-cap speculative
- Sensibilidade: Narrativa emergente, ciclos especulativos, liquidez
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class GPSPlaybook(BasePlaybook):
    """
    Playbook para GPS.
    Low-cap especulativo com beta 3.5 (volatilidade elevada).
    """
    
    def __init__(self):
        super().__init__("GPSUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para GPS.
        
        GPS é sensível a:
        - Narrativa emergente do token
        - Ciclos especulativos de altcoins
        - Momentum e liquidez de mercado
        """
        adjustments = {
            "emerging_narrative": 1.0,   # Sensível a narrativa emergente
            "altcoin_momentum": 1.0,     # Segue momentum altcoin
            "speculative_flow": 1.0,     # Fluxo especulativo direto
            "macro_risk_off": -2.5,      # Sofre bastante em risk-off
            "liquidity_profile": 0.5,    # Sensível a liquidez
        }
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para GPS.
        
        Beta 3.5 (low-cap, volatilidade alta):
        - 50% de tamanho de posição (conservador)
        - SL moderadamente apertado, TP próximo
        """
        adjustments = {
            "position_size_multiplier": 0.50,    # 50% do tamanho padrão
            "sl_atr_multiplier": 1.4,             # SL um pouco apertado
            "tp_atr_multiplier": 2.5,             # TP próximo
            "max_drawdown_percent": 2.4,          # Max drawdown 2.4%
            "min_confluence_required": 10,        # Requer confluência 10+
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de GPS.
        
        GPS passa por:
        - Discovery: Narrativa emerge
        - Adoption: Momentum crescente
        - Saturation: Pico de interesse
        - Decline: Perda de narrativa
        """
        narrative_strength = current_data.get("narrative_strength", "weak")
        price_action = current_data.get("price_action", "neutral")
        
        if narrative_strength == "strong" and price_action == "uptrend":
            return "adoption"
        elif narrative_strength == "peak" and price_action == "uptrend":
            return "saturation"
        elif price_action == "downtrend":
            return "decline"
        else:
            return "discovery"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: Optional[str] = None) -> bool:
        """
        GPS (low-cap 3.5) deve operar em:
        - Risk-on com D1 long (principalmente strong long)
        - AVOID em risk-off
        - Cautela em neutro
        """
        if d1_bias in ["NEUTRO", "SHORT"]:
            return False
        
        if market_regime == "RISK_ON":
            return d1_bias in ["LONG", "STRONG_LONG"]
        elif market_regime == "RISK_OFF":
            return False
        else:  # NEUTRO_MERCADO
            return d1_bias == "STRONG_LONG"
        
        return False
