"""
Playbook especifico para Algorand (ALGOUSDT).
Foco em pagamentos, tokenizacao e adocao institucional.
"""

import logging
from typing import Any, Dict

from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class ALGOPlaybook(BasePlaybook):
    """Playbook para ALGOUSDT com foco em pagamentos e tokenizacao."""

    def __init__(self) -> None:
        super().__init__("ALGOUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para ALGOUSDT."""
        ajustes: Dict[str, float] = {}

        if context.get("institutional_flows"):
            ajustes["institutional_flows"] = 0.8
            logger.debug("ALGO: +0.8 confluencia por fluxo institucional")

        if context.get("payment_partnerships"):
            ajustes["payment_partnerships"] = 0.6
            logger.debug("ALGO: +0.6 confluencia por parceria de pagamentos")

        btc_bias = context.get("btc_bias")
        d1_bias = context.get("d1_bias")
        if btc_bias and d1_bias and btc_bias == d1_bias and btc_bias != "NEUTRO":
            ajustes["btc_alignment"] = 0.5

        return ajustes

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco moderados para ALGOUSDT."""
        ajustes: Dict[str, float] = {
            "position_size_multiplier": 0.9,
            "stop_multiplier": 1.1,
        }

        atr_pct = float(context.get("atr_pct", 3.0))
        if atr_pct > 5.0:
            ajustes["position_size_multiplier"] = 0.75
            ajustes["stop_multiplier"] = 1.25
        elif atr_pct < 2.0:
            ajustes["position_size_multiplier"] = 1.0

        return ajustes

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """Identifica a fase de ciclo predominante de ALGOUSDT."""
        narrative = current_data.get("market_narrative", "")
        d1_bias = current_data.get("d1_bias", "NEUTRO")

        if narrative == "TOKENIZATION" and d1_bias == "LONG":
            return "ALGO_TOKENIZATION_EXPANSION"
        if narrative == "PAYMENTS" and d1_bias == "LONG":
            return "ALGO_PAYMENT_EXPANSION"
        if d1_bias == "SHORT":
            return "ALGO_CONTRACAO"
        if d1_bias == "LONG":
            return "ALGO_ACUMULACAO"
        return "ALGO_LATERALIZACAO"
