"""
Playbook especializado para PENGU (Penguin).

Característica: Memecoin com dinâmica comunitária
- Beta: 4.0 (low-cap memecoin, extremamente volátil)
- Classificação: Low-cap memecoin
- Sensibilidade: Narrativa social, momentum comunitário, hype
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class PENGUPlaybook(BasePlaybook):
    """
    Playbook para Penguin (PENGU).
    Memecoin com beta 4.0 (extremamente volátil, especulativo).
    """

    def __init__(self):
        super().__init__("PENGUUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para PENGU.

        Penguin é sensível a:
        - Narrativa de meme (comunidade, redes sociais)
        - Momentum especulativo extremo
        - Ciclos de hype viral
        """
        adjustments = {
            "social_sentiment": 1.5,     # MUITO sensível a sentimento social
            "memecoin_momentum": 1.5,    # Segue momentum de memecoins
            "speculative_flow": 1.25,    # Altamente especulativo
            "macro_risk_off": -3.0,      # Muito sensível a risk-off
            "btc_dominance": -1.0,       # Sofre quando BTC domina
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para PENGU.

        Beta 4.0 (memecoin extremo):
        - 40% de tamanho de posição (MUITO conservador)
        - SL APERTADO, TP PRÓXIMO
        - Exigir CONFLUÊNCIA EXTREMA para operar
        """
        adjustments = {
            "position_size_multiplier": 0.40,    # 40% do tamanho padrão
            "sl_atr_multiplier": 1.2,             # SL APERTADO (1.2x)
            "tp_atr_multiplier": 2.0,             # TP bem próximo (2.0x)
            "max_drawdown_percent": 2.0,          # Max drawdown 2.0% APENAS
            "min_confluence_required": 11,        # REQUER confluência 11+
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de PENGU.

        PENGU passa por:
        - Hype: Crescimento viralmente impulsionado
        - Peak: Máxima euforia
        - Crash: Realização abrupta
        - Graveyard: Abandono após dump
        """
        social_volume = current_data.get("social_volume", "low")
        price_action = current_data.get("price_action", "neutral")

        if social_volume == "viral" and price_action == "uptrend":
            return "hype"
        elif price_action == "downtrend":
            return "crash"
        elif social_volume == "low" and price_action == "sideways":
            return "graveyard"
        else:
            return "consolidation"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: Optional[str] = None) -> bool:
        """
        PENGU (memecoin 4.0) APENAS em:
        - Risk-on FORTE com D1 STRONG_LONG
        - NEVER em risk-off
        - NEVER em neutral market
        - RIESGOSO - opcionalmente desabilitar
        """
        if d1_bias != "STRONG_LONG":
            return False

        if market_regime == "RISK_ON":
            return True

        return False
