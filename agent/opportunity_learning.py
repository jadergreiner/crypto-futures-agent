"""
Opportunity Learning: Avaliar decisões de ficar FORA do mercado.

O agente aprende que ficar fora pode ser:
1. SÁBIO: Drawdown extremo, mercado perigoso, entrada ruim (stay out = +reward)
2. DESPERDIÇADOR: Oportunidade boa passou, teria ganhado bem (stay out = -reward)
3. EQUILIBRADO: Contexto misto, trade teria sido ok mas não excelente (neutral)

Mecanismo:
- Rastreia "oportunidades não tomadas" (signal mas não entra)
- Simula hipoteticamente o que teria acontecido
- Depois de X candles, avalia se "ficação out" foi sábia ou não
- Retro-aprende: computa reward contextual
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Constantes de calibração
OPPORTUNITY_LOOKBACK_CANDLES = 20  # Quantos candles observar oportunidade
OPPORTUNITY_MIN_CONFLUENCE = 6.0   # Só rastrear signals com min confluence
OPPORTUNITY_MIN_PRICE_MOVE_PCT = 1.0  # Movimento mínimo para avaliar

# Pesos de aprendizado
OPPORTUNITY_REWARD_GOOD_MOVE = 0.25    # Se not entrante teria ganhado bem
OPPORTUNITY_PENALTY_GOOD_MOVE = -0.10   # Penalidade por desperdiçar boa oportunidade
OPPORTUNITY_REWARD_BAD_MOVE = 0.20    # Se não entrar evitou perda
OPPORTUNITY_PENALTY_BAD_MOVE = -0.02   # Penalidade mínima por ser conservador demais

DRAWDOWN_THRESHOLD_FOR_WISDOM = 3.0   # Drawdown >= 3% = stay out é sábio
CONFLUENCE_THRESHOLD_FOR_RISK = 8.0   # Confluence < 8 = alto risco mesmo sem drawdown


@dataclass
class MissedOpportunity:
    """Registro de uma oportunidade não tomada."""

    symbol: str
    timestamp: int
    entry_step: int
    direction: str  # LONG ou SHORT
    entry_price: float
    confluence: float

    # Contexto de por que não entrou
    drawdown_pct: float
    recent_trades_24h: int
    status: str = "TRACKING"  # TRACKING, EVALUATED, CLOSED

    # Simulação hipotética
    hypothetical_tp: float = 0.0
    hypothetical_sl: float = 0.0
    hypothetical_size: float = 1.0

    # Resultado (após OPPORTUNITY_LOOKBACK_CANDLES)
    max_price_reached: float = 0.0
    min_price_reached: float = 0.0
    final_price: float = 0.0

    # Análise
    would_have_been_winning: bool = False
    profit_pct_if_entered: float = 0.0
    opportunity_quality: str = "NEUTRAL"  # EXCELLENT, GOOD, OK, BAD

    # Aprendizado
    contextual_reward: float = 0.0
    reasoning: str = ""


class OpportunityLearner:
    """
    Aprende quando ficar fora é sábio vs desperdiçador.
    """

    def __init__(self):
        """Inicializa opportunity learner."""
        self.missed_opportunities: Dict[int, MissedOpportunity] = {}
        self.evaluated_opportunities: List[MissedOpportunity] = []
        self.episode_insights = {
            'opportunities_tracked': 0,
            'opportunities_evaluated': 0,
            'wise_decisions': 0,
            'desperate_decisions': 0,  # Ficou fora quando deveria ter entrado
            'total_contextual_reward': 0.0,
        }
        logger.info("OpportunityLearner initialized")

    def register_missed_opportunity(self,
                                   symbol: str,
                                   timestamp: int,
                                   step: int,
                                   direction: str,
                                   entry_price: float,
                                   confluence: float,
                                   atr: float,
                                   drawdown_pct: float,
                                   recent_trades_24h: int) -> int:
        """
        Registra uma oportunidade não tomada (signal gerado mas não entrou).

        Args:
            symbol: Símbolo (ex: BTCUSDT)
            timestamp: Timestamp em ms
            step: Step do episódio
            direction: LONG ou SHORT
            entry_price: Preço de entrada se tivesse entrado
            confluence: Score de confluence (0-14)
            atr: ATR para calcular TP/SL
            drawdown_pct: Drawdown atual
            recent_trades_24h: Número de trades últimas 24h

        Returns:
            opportunity_id para rastreamento
        """
        # Só rastrear signals com confluence razoável
        if confluence < OPPORTUNITY_MIN_CONFLUENCE:
            return -1

        # Calcular TP/SL hipotéticos
        if direction == "LONG":
            hypothetical_tp = entry_price + atr * 3.0
            hypothetical_sl = entry_price - atr * 1.5
        else:  # SHORT
            hypothetical_tp = entry_price - atr * 3.0
            hypothetical_sl = entry_price + atr * 1.5

        opportunity_id = step
        opp = MissedOpportunity(
            symbol=symbol,
            timestamp=timestamp,
            entry_step=step,
            direction=direction,
            entry_price=entry_price,
            confluence=confluence,
            drawdown_pct=drawdown_pct,
            recent_trades_24h=recent_trades_24h,
            hypothetical_tp=hypothetical_tp,
            hypothetical_sl=hypothetical_sl
        )

        self.missed_opportunities[opportunity_id] = opp
        self.episode_insights['opportunities_tracked'] += 1

        logger.debug(f"Registered opportunity: {symbol} {direction} @{entry_price:.2f} "
                    f"(confluence={confluence:.1f}, dd={drawdown_pct:.2f}%)")

        return opportunity_id

    def evaluate_opportunity(self,
                            opportunity_id: int,
                            current_price: float,
                            max_price_reached: float,
                            min_price_reached: float) -> Optional[MissedOpportunity]:
        """
        Avalia uma oportunidade rastreada com preço atual.

        Args:
            opportunity_id: ID da oportunidade
            current_price: Preço atual do mercado
            max_price_reached: Preço máximo atingido no lookback
            min_price_reached: Preço mínimo atingido no lookback

        Returns:
            MissedOpportunity avaliada com contextual_reward
        """
        if opportunity_id not in self.missed_opportunities:
            return None

        opp = self.missed_opportunities[opportunity_id]

        # Se já foi avaliada, skip
        if opp.status == "EVALUATED":
            return opp

        # Atualizar preços atingidos
        opp.max_price_reached = max_price_reached
        opp.min_price_reached = min_price_reached
        opp.final_price = current_price

        # Calcular resultado hipotético
        if opp.direction == "LONG":
            if max_price_reached >= opp.hypothetical_tp:
                opp.would_have_been_winning = True
                # Ganho = diferença entre TP e entrada
                opp.profit_pct_if_entered = ((opp.hypothetical_tp - opp.entry_price) /
                                             opp.entry_price * 100)
            else:
                # Verificar se teria batido stop
                if min_price_reached <= opp.hypothetical_sl:
                    opp.would_have_been_winning = False
                    opp.profit_pct_if_entered = ((opp.hypothetical_sl - opp.entry_price) /
                                                 opp.entry_price * 100)
                else:
                    # Movimento parcial
                    opp.would_have_been_winning = (current_price > opp.entry_price)
                    opp.profit_pct_if_entered = ((current_price - opp.entry_price) /
                                                 opp.entry_price * 100)
        else:  # SHORT
            if min_price_reached <= opp.hypothetical_tp:
                opp.would_have_been_winning = True
                opp.profit_pct_if_entered = ((opp.entry_price - opp.hypothetical_tp) /
                                             opp.entry_price * 100)
            else:
                if max_price_reached >= opp.hypothetical_sl:
                    opp.would_have_been_winning = False
                    opp.profit_pct_if_entered = ((opp.entry_price - opp.hypothetical_sl) /
                                                 opp.entry_price * 100)
                else:
                    opp.would_have_been_winning = (current_price < opp.entry_price)
                    opp.profit_pct_if_entered = ((opp.entry_price - current_price) /
                                                 opp.entry_price * 100)

        # Computar reward contextual
        self._compute_contextual_reward(opp)

        opp.status = "EVALUATED"
        self.evaluated_opportunities.append(opp)
        self.episode_insights['opportunities_evaluated'] += 1

        logger.debug(f"Evaluated opportunity: {opp.symbol} - "
                    f"Would have {'WON' if opp.would_have_been_winning else 'LOST'} "
                    f"{opp.profit_pct_if_entered:+.2f}% - "
                    f"Contextual reward: {opp.contextual_reward:+.3f}")

        return opp

    def _compute_contextual_reward(self, opp: MissedOpportunity) -> None:
        """
        Computa reward contextual baseado em:
        1. Qualidade da oportunidade perdida
        2. Contexto de desistência (drawdown, múltiplos trades)
        3. Resultado hipotético
        """

        # Classificar qualidade da oportunidade
        if opp.profit_pct_if_entered >= 3.0:
            opp.opportunity_quality = "EXCELLENT"
        elif opp.profit_pct_if_entered >= 1.5:
            opp.opportunity_quality = "GOOD"
        elif opp.profit_pct_if_entered >= 0.5:
            opp.opportunity_quality = "OK"
        else:
            opp.opportunity_quality = "BAD"

        # Analisar contexto de desistência
        high_drawdown = opp.drawdown_pct >= DRAWDOWN_THRESHOLD_FOR_WISDOM
        recent_activity = opp.recent_trades_24h >= 3
        high_confluence = opp.confluence >= CONFLUENCE_THRESHOLD_FOR_RISK

        # LÓGICA DE APRENDIZADO CONTEXTUAL

        if opp.would_have_been_winning:
            # OPORTUNIDADE BOA FOI DESPERDIÇADA

            if high_drawdown:
                # Contexto: Drawdown alto, mas oportunidade era excelente
                if opp.opportunity_quality == "EXCELLENT":
                    # Penalidade: Deveria ter entrado com menor size
                    opp.contextual_reward = OPPORTUNITY_PENALTY_GOOD_MOVE * 1.5
                    opp.reasoning = f"Desperdiçou oportunidade EXCELENTE (+{opp.profit_pct_if_entered:.2f}%) mesmo com drawdown {opp.drawdown_pct:.1f}%. Deveria ter entrado com size menor."
                    self.episode_insights['desperate_decisions'] += 1
                else:
                    # Recompensa leve: Drawdown extremo, decisão conservadora ok
                    opp.contextual_reward = OPPORTUNITY_REWARD_GOOD_MOVE * 0.5
                    opp.reasoning = f"Ficar fora durante drawdown {opp.drawdown_pct:.1f}% foi prudente, mesmo perdendo oportunidade {opp.opportunity_quality}."
                    self.episode_insights['wise_decisions'] += 1

            elif recent_activity:
                # Contexto: Múltiplos trades, oportunidade era boa
                if opp.opportunity_quality in ["EXCELLENT", "GOOD"]:
                    # Penalidade: Deveria ter descansado MENOS
                    opp.contextual_reward = OPPORTUNITY_PENALTY_GOOD_MOVE
                    opp.reasoning = f"Perdeu oportunidade {opp.opportunity_quality} (+{opp.profit_pct_if_entered:.2f}%) após {opp.recent_trades_24h} trades. Deveria ter reenergizado mais rápido."
                    self.episode_insights['desperate_decisions'] += 1
                else:
                    # OK: Descansar após atividade foi sábio
                    opp.contextual_reward = OPPORTUNITY_REWARD_GOOD_MOVE * 0.3
                    opp.reasoning = f"Descanso após atividade foi prudente."
                    self.episode_insights['wise_decisions'] += 1

            else:
                # Contexto: Sem extremos (sem drawdown, sem múltiplos trades)
                # Oportunidade boa foi desperdiçada, isso é ruim
                opp.contextual_reward = OPPORTUNITY_PENALTY_GOOD_MOVE * 2.0
                opp.reasoning = f"Em condições normais, desperdiçou oportunidade {opp.opportunity_quality} " \
                               f"(+{opp.profit_pct_if_entered:.2f}%). Deveria ter entrado."
                self.episode_insights['desperate_decisions'] += 1

        else:
            # OPORTUNIDADE RUIM FOI EVITADA (OU NEUTRO)

            if opp.profit_pct_if_entered <= -2.0:
                # Seria falha, decisão foi sábia
                opp.contextual_reward = OPPORTUNITY_REWARD_BAD_MOVE * 1.5
                opp.reasoning = f"Evitou perda {opp.profit_pct_if_entered:.2f}% ficando fora. Decisão clara sábia."
                self.episode_insights['wise_decisions'] += 1

            elif opp.profit_pct_if_entered <= -0.5:
                # Pequena perda evitada, ok
                opp.contextual_reward = OPPORTUNITY_REWARD_BAD_MOVE * 0.8
                opp.reasoning = f"Evitou pequena perda {opp.profit_pct_if_entered:.2f}%. Decisão prudente."
                self.episode_insights['wise_decisions'] += 1

            else:
                # Neutro mas poderia ter ganhado
                opp.contextual_reward = -OPPORTUNITY_PENALTY_BAD_MOVE
                opp.reasoning = f"Ficar fora foi seguro mas conservador demais. Oportunidade neutra/negativa evitada."
                self.episode_insights['wise_decisions'] += 1

        self.episode_insights['total_contextual_reward'] += opp.contextual_reward

    def get_episode_summary(self) -> Dict[str, Any]:
        """Retorna sumário de aprendizado do episódio."""
        return {
            'avg_contextual_reward': (
                self.episode_insights['total_contextual_reward'] /
                max(self.episode_insights['opportunities_evaluated'], 1)
            ),
            'wise_decisions_pct': (
                self.episode_insights['wise_decisions'] /
                max(self.episode_insights['opportunities_evaluated'], 1) * 100
            ),
            **self.episode_insights
        }

    def reset_episode(self) -> None:
        """Reset para novo episódio."""
        self.missed_opportunities.clear()
        self.evaluated_opportunities.clear()
        self.episode_insights = {
            'opportunities_tracked': 0,
            'opportunities_evaluated': 0,
            'wise_decisions': 0,
            'desperate_decisions': 0,
            'total_contextual_reward': 0.0,
        }
