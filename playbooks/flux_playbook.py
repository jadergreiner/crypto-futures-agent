"""
Playbook especifico para FLUXUSDT — Infraestrutura cross-chain e computacao descentralizada.

Estrategia: swing trade orientado a narrativa DeFi/cross-chain com aprendizado autonomo.
O agente aprende, treina e evolui seus proprios padroes a partir dos dados.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class FLUXPlaybook(BasePlaybook):
    """
    Playbook para FLUXUSDT — Mid-cap cross-chain DeFi infrastructure.

    Caracteristicas principais:
    - Beta 2.9: amplifica movimentos do BTC com sensibilidade DeFi
    - Swing trade: posicoes mantidas por dias/semanas, nao horas
    - Aprendizado autonomo: sem parametros fixos passados ao agente
    - Apenas opera em regime RISK_ON com confirmacao D1
    - Narrativa DeFi/cross-chain como fator de confluencia adicional
    """

    def __init__(self) -> None:
        super().__init__("FLUXUSDT")

    # ------------------------------------------------------------------
    # Ajustes de confluencia
    # ------------------------------------------------------------------

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluencia para FLUXUSDT swing trade.

        Bonus aplicados quando confluencias de swing trade estao presentes.
        O agente usa esses ajustes como contexto adicional para decisoes autonomas.
        """
        ajustes: Dict[str, float] = {}

        # Regime risk-on e pre-requisito para operar mid-cap com beta alto
        regime = context.get("market_regime", "")
        if regime == "RISK_ON":
            ajustes["regime_risk_on"] = +0.9
            logger.debug("FLUX: +0.9 confluencia — regime RISK_ON")

        # Alinhamento BTC + D1 reforca tendencia de swing
        btc_bias = context.get("btc_bias", "")
        d1_bias = context.get("d1_bias", "")
        if btc_bias and btc_bias == d1_bias and btc_bias != "NEUTRO":
            ajustes["alinhamento_btc"] = +0.7
            logger.debug("FLUX: +0.7 confluencia — alinhamento com BTC")

        # Estrutura D1 definida e fundamental para entrada de swing
        smc_d1 = context.get("smc_d1_structure", "")
        if smc_d1 in ("bullish", "bearish"):
            ajustes["estrutura_d1_clara"] = +0.6
            logger.debug(f"FLUX: +0.6 confluencia — estrutura D1 {smc_d1}")

        # Narrativa DeFi/cross-chain ativa: fear & greed em zona favoravel
        fear_greed = context.get("fear_greed_value", 50)
        if 55 <= fear_greed <= 80:
            ajustes["defi_narrativa_ativa"] = +0.4
            logger.debug(f"FLUX: +0.4 confluencia — narrativa DeFi ativa (fear/greed {fear_greed})")

        # Penalidade: extrema ganancia aumenta risco de reversao em altcoins
        if fear_greed > 85:
            ajustes["extrema_ganancia"] = -0.5
            logger.debug(f"FLUX: -0.5 confluencia — fear/greed {fear_greed} (extrema ganancia)")

        return ajustes

    # ------------------------------------------------------------------
    # Ajustes de risco
    # ------------------------------------------------------------------

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para swing trade em FLUXUSDT.

        Posicao conservadora (beta 2.9) com stop calibrado para absorver
        volatilidade intraday sem sair do swing de medio prazo.
        """
        ajustes: Dict[str, float] = {
            # Beta 2.9 → posicao reduzida para controlar risco absoluto
            "position_size_multiplier": 0.45,
            # Stop moderado: FLUX tem estrutura SMC mais clara que memecoins
            "stop_multiplier": 1.4,
        }

        # Ajuste adicional por volatilidade atual (ATR%)
        atr_pct = context.get("atr_pct", 3.0)
        if atr_pct > 6.0:
            # Volatilidade muito alta: reduzir posicao para controlar risco (beta 2.9)
            ajustes["position_size_multiplier"] = 0.35
            ajustes["stop_multiplier"] = 1.7
            logger.debug(f"FLUX: ATR% {atr_pct:.1f} — posicao reduzida para 35%, stop 1.7x")
        elif atr_pct < 2.0:
            # Volatilidade baixa: pode aumentar levemente (mercado comprimido)
            ajustes["position_size_multiplier"] = 0.55
            logger.debug(f"FLUX: ATR% {atr_pct:.1f} — posicao aumentada para 55%")

        return ajustes

    # ------------------------------------------------------------------
    # Fase do ciclo
    # ------------------------------------------------------------------

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de swing trade do FLUX.

        FLUX amplifica ciclos do BTC com sensibilidade adicional a narrativas
        DeFi e cross-chain que o agente aprende progressivamente.
        """
        btc_phase = current_data.get("btc_cycle_phase", "ACCUMULATION")
        d1_bias = current_data.get("d1_bias", "NEUTRO")

        # Beta 2.9 exagera as fases do BTC com componente DeFi
        if btc_phase == "BULL_RUN" and d1_bias == "LONG":
            return "FLUX_IMPULSO_DEFI"
        elif btc_phase == "BULL_RUN":
            return "FLUX_DISTRIBUICAO"
        elif btc_phase == "BEAR_MARKET" and d1_bias == "SHORT":
            return "FLUX_QUEDA"
        elif btc_phase == "BEAR_MARKET":
            return "FLUX_CAPITULACAO"
        elif d1_bias == "LONG":
            return "FLUX_ACUMULACAO"
        elif d1_bias == "SHORT":
            return "FLUX_ACUMULACAO_SHORT"
        else:
            return "FLUX_LATERALIZACAO"

    # ------------------------------------------------------------------
    # Decisao de operar
    # ------------------------------------------------------------------

    def should_trade(  # type: ignore[override]
        self,
        market_regime: str,
        d1_bias: str,
        btc_bias: str = "NEUTRO",
    ) -> bool:
        """
        FLUX swing trade: apenas em RISK_ON com bias D1 direcional confirmado.

        Sem parametros rigidos: o agente aprende quais setups tem melhor
        relacao risco/retorno ao longo do tempo (evolucao autonoma).
        """
        # Bias neutro: sem tendencia clara para swing trade
        if d1_bias == "NEUTRO":
            logger.debug("FLUX: aguardando — bias D1 neutro (sem tendencia de swing)")
            return False

        # Mid-cap com beta alto: exige regime de risco favoravel
        if market_regime != "RISK_ON":
            logger.debug(f"FLUX: aguardando — regime {market_regime} (exige RISK_ON)")
            return False

        # Conflito com BTC: precaucao para evitar operacoes contra tendencia macro
        if btc_bias and btc_bias not in (d1_bias, "NEUTRO"):
            logger.debug(
                f"FLUX: precaucao — conflito BTC ({btc_bias}) vs D1 ({d1_bias})"
            )
            return False

        return True
