"""
Playbook específico para SKRUSDT — Modelo Swing Trade Autônomo.

Estratégia: swing trade de médio prazo (dias a semanas) sem parâmetros fixos.
O agente aprende, treina e evolui seus próprios padrões a partir dos dados.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class SKRPlaybook(BasePlaybook):
    """
    Playbook para SKRUSDT — Swing Trade autônomo de baixa capitalização.

    Características principais:
    - Beta 2.8: amplifica movimentos do BTC
    - Swing trade: posições mantidas por dias/semanas, não horas
    - Aprendizado autônomo: sem parâmetros fixos passados ao agente
    - Apenas opera em regime RISK_ON com confirmação D1
    - Stop mais largo (volatilidade alta) e alvo maior (10-30%)
    """

    def __init__(self):
        super().__init__("SKRUSDT")

    # ------------------------------------------------------------------
    # Ajustes de confluência
    # ------------------------------------------------------------------

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para SKRUSDT swing trade.

        Bônus aplicados quando confluências de swing trade estão presentes.
        O agente usa esses ajustes como contexto adicional para decisões autônomas.
        """
        ajustes: Dict[str, float] = {}

        # Regime risk-on é pré-requisito para swing trade em low-cap
        regime = context.get("market_regime", "")
        if regime == "RISK_ON":
            ajustes["regime_risk_on"] = +1.0
            logger.debug("SKR: +1 confluência — regime RISK_ON")

        # Alinhamento com BTC reforça a tendência de swing
        btc_bias = context.get("btc_bias", "")
        d1_bias = context.get("d1_bias", "")
        if btc_bias and btc_bias == d1_bias and btc_bias != "NEUTRO":
            ajustes["alinhamento_btc"] = +0.8
            logger.debug("SKR: +0.8 confluência — alinhamento com BTC")

        # Estrutura de mercado D1 definida é fundamental para swing trade
        smc_d1 = context.get("smc_d1_structure", "")
        if smc_d1 in ("bullish", "bearish"):
            ajustes["estrutura_d1_clara"] = +0.7
            logger.debug(f"SKR: +0.7 confluência — estrutura D1 {smc_d1}")

        # Volume acima da média confirma movimento de swing
        volume_ratio = context.get("volume_ratio", 1.0)
        if volume_ratio > 1.5:
            ajustes["volume_confirmacao"] = +0.5
            logger.debug(f"SKR: +0.5 confluência — volume {volume_ratio:.1f}x acima da média")

        # Fear & Greed: zona de ganância moderada favorece swing long
        fear_greed = context.get("fear_greed_value", 50)
        if 55 <= fear_greed <= 80:
            ajustes["sentimento_favoravel"] = +0.3
            logger.debug(f"SKR: +0.3 confluência — fear/greed {fear_greed} (zona favorável)")

        # Penalidade: mercado em extrema ganância — risco de reversão
        if fear_greed > 85:
            ajustes["extrema_ganancia"] = -0.5
            logger.debug(f"SKR: -0.5 confluência — fear/greed {fear_greed} (extrema ganância)")

        return ajustes

    # ------------------------------------------------------------------
    # Ajustes de risco
    # ------------------------------------------------------------------

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para swing trade em SKRUSDT.

        Posição conservadora (beta 2.8) com stop mais largo para
        absorver volatilidade intraday sem sair do swing.
        """
        ajustes = {
            # Beta 2.8 → reduzir tamanho da posição para controlar risco
            "position_size_multiplier": 0.45,
            # Stop mais largo para não ser estopado por ruído intraday
            "stop_multiplier": 1.5,
        }

        # Ajuste adicional por volatilidade atual (ATR%)
        atr_pct = context.get("atr_pct", 3.0)
        if atr_pct > 6.0:
            # Volatilidade muito alta: reduzir posição ainda mais
            # (beta 2.8 × ATR alto = risco concentrado)
            ajustes["position_size_multiplier"] = 0.35
            ajustes["stop_multiplier"] = 1.8
            logger.debug(f"SKR: ATR% {atr_pct:.1f} — posição reduzida para 35%, stop 1.8x")
        elif atr_pct < 2.0:
            # Volatilidade baixa: pode aumentar levemente (mercado comprimido)
            ajustes["position_size_multiplier"] = 0.55
            logger.debug(f"SKR: ATR% {atr_pct:.1f} — posição aumentada para 55%")

        return ajustes

    # ------------------------------------------------------------------
    # Fase do ciclo
    # ------------------------------------------------------------------

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de swing trade do SKR.

        SKR amplifica ciclos do BTC e apresenta padrões autônomos de
        acumulação/distribuição que o agente aprende progressivamente.
        """
        btc_phase = current_data.get("btc_cycle_phase", "ACCUMULATION")
        d1_bias = current_data.get("d1_bias", "NEUTRO")

        # SKR com beta 2.8 exagera as fases do BTC
        if btc_phase == "BULL_RUN" and d1_bias == "LONG":
            return "SWING_IMPULSO"
        elif btc_phase == "BULL_RUN" and d1_bias != "LONG":
            return "SWING_DISTRIBUICAO"
        elif btc_phase == "BEAR_MARKET" and d1_bias == "SHORT":
            return "SWING_QUEDA"
        elif btc_phase == "BEAR_MARKET":
            return "SWING_CAPITULACAO"
        elif d1_bias == "LONG":
            return "SWING_ACUMULACAO_LONG"
        elif d1_bias == "SHORT":
            return "SWING_ACUMULACAO_SHORT"
        else:
            return "SWING_LATERALIZACAO"

    # ------------------------------------------------------------------
    # Decisão de operar
    # ------------------------------------------------------------------

    def should_trade(self, market_regime: str, d1_bias: str,
                     btc_bias: str = None) -> bool:
        """
        SKR swing trade: apenas em RISK_ON com bias D1 direcional confirmado.

        Sem parâmetros rígidos: o agente aprende quais setups têm melhor
        relação risco/retorno ao longo do tempo (evolução autônoma).
        """
        # Bias neutro: sem tendência clara para swing trade
        if d1_bias == "NEUTRO":
            logger.debug("SKR: aguardando — bias D1 neutro (sem tendência de swing)")
            return False

        # Low-cap com beta alto: exige regime de risco favorável
        if market_regime != "RISK_ON":
            logger.debug(f"SKR: aguardando — regime {market_regime} (exige RISK_ON)")
            return False

        # Conflito com BTC: precaução para evitar operações contra a tendência macro
        if btc_bias and btc_bias not in (d1_bias, "NEUTRO"):
            logger.debug(
                f"SKR: precaução — conflito BTC ({btc_bias}) vs D1 ({d1_bias})"
            )
            return False

        return True
