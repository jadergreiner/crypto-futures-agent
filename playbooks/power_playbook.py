"""
Playbook especializado para POWER.

Característica: Token de governança/utilidade com dinâmica especulativa
- Beta: 3.6 (low-cap especulativo, volatilidade alta)
- Classificação: Low-cap speculative emerging
- Sensibilidade: Narrativa emergente, ciclos especulativos, fluxo varejo
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class POWERPlaybook(BasePlaybook):
    """
    Playbook para Power.
    Low-cap especulativo com beta 3.6 (narrativa emergente, volatilidade alta).
    """
    
    def __init__(self):
        super().__init__("POWERUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para POWER.
        
        Power é sensível a:
        - Narrativa de governança emergente
        - Ciclos especulativos de altcoins
        - Momentum de fluxo varejo
        """
        adjustments = {
            "governance_narrative": 0.75,        # Narrativa governança
            "emerging_narrative": 1.0,           # Sensível a narrativa emergente
            "altcoin_momentum": 1.0,             # Segue momentum altcoin
            "retail_flow": 0.75,                 # Fluxo varejo especulativo
            "macro_risk_off": -2.5,              # Sofre bastante em risk-off
        }
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para POWER.
        
        Beta 3.6 (low-cap, volatilidade alta):
        - 48% de tamanho de posição (conservador)
        - SL moderadamente apertado, TP próximo
        """
        adjustments = {
            "position_size_multiplier": 0.48,    # 48% do tamanho padrão
            "sl_atr_multiplier": 1.4,             # SL um pouco apertado
            "tp_atr_multiplier": 2.3,             # TP próximo
            "max_drawdown_percent": 2.3,          # Max drawdown 2.3%
            "min_confluence_required": 10,        # Requer confluência 10+
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de POWER.
        
        POWER passa por:
        - Launch: Token novo/re-listagem
        - Growth: Narrativa se estabelece
        - Hype: Euforia especulativa
        - Dump: Realização
        - Recovery: Estabilização
        """
        launch_status = current_data.get("launch_status", "established")
        price_action = current_data.get("price_action", "neutral")
        
        if launch_status == "new" or price_action == "breakout":
            return "launch"
        elif price_action == "uptrend" and launch_status != "new":
            return "growth"
        elif price_action == "downtrend":
            return "dump"
        else:
            return "recovery"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: Optional[str] = None) -> bool:
        """
        POWER (low-cap emergent 3.6) deve operar em:
        - Risk-on com D1 long (preferencialmente strong long)
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
