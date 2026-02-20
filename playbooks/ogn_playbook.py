"""
Playbook especializado para OGN (Origin Protocol).

Característica: Protocolo de e-commerce/marketplace descentralizado
- Beta: 3.2 (low-cap especulativo)
- Classificação: DeFi commerce protocol
- Sensibilidade: Ciclos de inovação Web3, narrativa de marketplace
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class OGNPlaybook(BasePlaybook):
    """
    Playbook para Origin Protocol (OGN).
    DeFi commerce protocol com beta 3.2 (especulativo).
    """

    def __init__(self):
        super().__init__("OGNUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para OGN.

        Origin Protocol é sensível a:
        - Ciclos de inovação em Web3 commerce
        - Narrativa de marketplace descentralizado
        - Altcoin momentum geral
        """
        adjustments = {
            "web3_commerce_narrative": 1.0,  # Core: narrativa Web3 commerce
            "marketplace_innovation": 0.8,   # Sensível a inovação em marketplace
            "altcoin_momentum": 0.7,         # Segue momentum de altcoins
            "macro_risk_off": -1.2,          # Fortemente afetado em risk-off
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para OGN.

        Beta 3.2 (low-cap especulativo):
        - 50% de tamanho de posição em relação ao baseline
        - SL mais apertado, TP mais próximo
        """
        adjustments = {
            "position_size_multiplier": 0.50,    # 50% do tamanho padrão (CONSERVADOR)
            "sl_atr_multiplier": 1.4,             # SL apertado (ATR 1.4x)
            "tp_atr_multiplier": 2.5,             # TP próximo (ATR 2.5x)
            "max_drawdown_percent": 2.5,          # Max drawdown 2.5%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de OGN.

        Origin Protocol passa por:
        - Accumulation: Preparação para crescimento
        - Growth: Fase de expansão de narrativa
        - Maturity: Consolidação
        - Decline: Redução de interesse
        """
        price_action = current_data.get("price_action", "neutral")
        volume = current_data.get("volume_profile", "normal")

        if price_action == "uptrend" and volume == "high":
            return "growth"
        elif price_action == "downtrend":
            return "decline"
        elif volume == "accumulation":
            return "accumulation"
        else:
            return "consolidation"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: Optional[str] = None) -> bool:
        """
        OGN (low-cap, beta 3.2) deve operar APENAS em:
        - Risk-on com D1 STRONG_LONG (mais restritivo)
        - Avoid em qualquer outro modo
        """
        if d1_bias == "NEUTRO":
            return False

        if market_regime == "RISK_ON":
            # Mais restritivo: apenas STRONG_LONG
            return d1_bias == "STRONG_LONG"
        else:
            # RISK_OFF ou NEUTRO_MERCADO: não operar
            return False
