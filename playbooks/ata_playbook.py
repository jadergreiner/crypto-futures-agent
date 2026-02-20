"""
Playbook especializado para ATA (Automata).

Característica: Rede de privacidade e computação segura
- Beta: 3.2 (low-cap, volatilidade elevada)
- Classificação: Privacy infrastructure
- Sensibilidade: Narrativa de privacidade, ciclos especulativos
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class ATAPlaybook(BasePlaybook):
    """
    Playbook para Automata (ATA).
    Privacy infrastructure com beta 3.2 (low-cap especulativo).
    """

    def __init__(self):
        super().__init__("ATAUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para ATA.

        Automata é sensível a:
        - Narrativa de privacidade emergente
        - Ciclos especulativos de altcoins
        - Momentum de tokens low-cap
        """
        adjustments = {
            "privacy_narrative": 1.0,    # Foco em narrativa privacidade
            "altcoin_momentum": 1.0,     # Segue momentum altcoin
            "speculative_flow": 0.75,    # Seguos fluxos especulativos
            "macro_risk_off": -2.0,      # Sofre bastante em risk-off
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para ATA.

        Beta 3.2 (low-cap, volatilidade elevada):
        - 50% de tamanho de posição (conservador)
        - SL mais apertado, TP mais próximo
        """
        adjustments = {
            "position_size_multiplier": 0.50,    # 50% do tamanho padrão
            "sl_atr_multiplier": 1.5,             # SL padrão
            "tp_atr_multiplier": 2.5,             # TP um pouco mais próximo
            "max_drawdown_percent": 2.5,          # Max drawdown 2.5%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de ATA.

        ATA passa por:
        - Breakout: Saída de consolidação
        - Pump: Movimento de euforia
        - Dump: Realização de ganhos
        - Recovery: Reconsolidação
        """
        momentum = current_data.get("momentum", "neutral")
        price_action = current_data.get("price_action", "neutral")

        if price_action == "uptrend" and momentum == "strong":
            return "pump"
        elif price_action == "downtrend":
            return "dump"
        elif price_action == "breakout":
            return "breakout"
        else:
            return "recovery"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: Optional[str] = None) -> bool:
        """
        ATA (low-cap 3.2) deve operar em:
        - Risk-on FORTE com D1 long apenas
        - NEVER em risk-off
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
