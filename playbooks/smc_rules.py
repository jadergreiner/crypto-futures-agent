"""
Regras compartilhadas de Smart Money Concepts.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class SMCRules:
    """
    Regras SMC aplicáveis a todas as moedas.
    Avalia qualidade de entrada e define stops/targets estruturais.
    """
    
    @staticmethod
    def evaluate_entry_quality(order_block: Optional[Any],
                               fvg: Optional[Any],
                               structure: Optional[Any],
                               premium_discount: Optional[Any],
                               direction: str,
                               liquidity_sweep: Optional[Any] = None) -> int:
        """
        Avalia qualidade da entrada SMC (0-5 pontos).
        
        Args:
            order_block: Order Block válido
            fvg: Fair Value Gap válido
            structure: Estrutura de mercado
            premium_discount: Posição premium/discount
            direction: "LONG" ou "SHORT"
            liquidity_sweep: Sweep de liquidez recente
            
        Returns:
            Score 0-5
        """
        score = 0
        
        # +1 para Order Block válido e alinhado
        if order_block and order_block.status.value == "FRESH":
            if (direction == "LONG" and order_block.type == "bullish") or \
               (direction == "SHORT" and order_block.type == "bearish"):
                score += 1
                logger.debug("SMC: +1 for valid Order Block")
        
        # +1 para FVG válido e alinhado
        if fvg and fvg.status.value == "OPEN":
            if (direction == "LONG" and fvg.type == "bullish") or \
               (direction == "SHORT" and fvg.type == "bearish"):
                score += 1
                logger.debug("SMC: +1 for valid FVG")
        
        # +1 para BOS/CHoCH alinhado com direção
        if structure:
            if hasattr(structure, 'type'):
                if (direction == "LONG" and structure.type.value == "bullish") or \
                   (direction == "SHORT" and structure.type.value == "bearish"):
                    score += 1
                    logger.debug("SMC: +1 for aligned market structure")
        
        # +1 para Premium/Discount alinhado
        if premium_discount:
            if direction == "LONG":
                # Comprar em discount
                if premium_discount.zone.name in ["DEEP_DISCOUNT", "DISCOUNT"]:
                    score += 1
                    logger.debug("SMC: +1 for buying in discount zone")
            else:  # SHORT
                # Vender em premium
                if premium_discount.zone.name in ["PREMIUM", "DEEP_PREMIUM"]:
                    score += 1
                    logger.debug("SMC: +1 for selling in premium zone")
        
        # +1 BONUS para liquidez sweep + OB fresco
        if liquidity_sweep and order_block and order_block.status.value == "FRESH":
            if (direction == "LONG" and liquidity_sweep.direction == "down") or \
               (direction == "SHORT" and liquidity_sweep.direction == "up"):
                score += 1
                logger.debug("SMC: +1 BONUS for liquidity sweep + fresh OB")
        
        logger.info(f"SMC entry quality score: {score}/5 for {direction}")
        return score
    
    @staticmethod
    def get_structural_stop(order_block: Optional[Any], direction: str) -> Optional[float]:
        """
        Retorna stop estrutural baseado em Order Block.
        
        Args:
            order_block: Order Block
            direction: "LONG" ou "SHORT"
            
        Returns:
            Preço do stop ou None
        """
        if order_block is None:
            return None
        
        if direction == "LONG":
            # Stop abaixo do OB bullish
            stop = order_block.zone_low
            logger.debug(f"Structural stop for LONG: {stop:.2f} (below OB)")
        else:  # SHORT
            # Stop acima do OB bearish
            stop = order_block.zone_high
            logger.debug(f"Structural stop for SHORT: {stop:.2f} (above OB)")
        
        return stop
    
    @staticmethod
    def get_structural_targets(liquidity_levels: List[Any],
                              opposite_obs: List[Any],
                              direction: str,
                              entry_price: float,
                              atr: float) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Define alvos estruturais (TP1, TP2, TP3).
        
        Args:
            liquidity_levels: Níveis de liquidez
            opposite_obs: Order Blocks da direção oposta
            direction: "LONG" ou "SHORT"
            entry_price: Preço de entrada
            atr: ATR atual
            
        Returns:
            (TP1, TP2, TP3) - podem ser None
        """
        tp1 = None
        tp2 = None
        tp3 = None
        
        # TP1: Próximo nível de liquidez
        if liquidity_levels:
            relevant_liquidity = []
            for level in liquidity_levels:
                if not level.swept:
                    if direction == "LONG" and level.price > entry_price:
                        relevant_liquidity.append(level.price)
                    elif direction == "SHORT" and level.price < entry_price:
                        relevant_liquidity.append(level.price)
            
            if relevant_liquidity:
                if direction == "LONG":
                    tp1 = min(relevant_liquidity)  # Mais próximo acima
                else:
                    tp1 = max(relevant_liquidity)  # Mais próximo abaixo
                logger.debug(f"TP1 (liquidity): {tp1:.2f}")
        
        # TP2: Próximo OB oposto
        if opposite_obs:
            relevant_obs = []
            for ob in opposite_obs:
                if ob.status.value in ["FRESH", "TESTED"]:
                    if direction == "LONG":
                        if ob.type == "bearish" and ob.zone_low > entry_price:
                            relevant_obs.append(ob.zone_low)
                    else:  # SHORT
                        if ob.type == "bullish" and ob.zone_high < entry_price:
                            relevant_obs.append(ob.zone_high)
            
            if relevant_obs:
                if direction == "LONG":
                    tp2 = min(relevant_obs)
                else:
                    tp2 = max(relevant_obs)
                logger.debug(f"TP2 (opposite OB): {tp2:.2f}")
        
        # TP3: Fallback usando ATR (3x)
        if direction == "LONG":
            tp3 = entry_price + (atr * 3)
        else:
            tp3 = entry_price - (atr * 3)
        logger.debug(f"TP3 (ATR fallback): {tp3:.2f}")
        
        return tp1, tp2, tp3
    
    @staticmethod
    def is_valid_entry_zone(current_price: float,
                           order_block: Optional[Any],
                           fvg: Optional[Any],
                           premium_discount: Optional[Any],
                           direction: str) -> bool:
        """
        Verifica se o preço atual está em zona válida para entrada.
        
        Args:
            current_price: Preço atual
            order_block: Order Block
            fvg: Fair Value Gap
            premium_discount: Posição premium/discount
            direction: "LONG" ou "SHORT"
            
        Returns:
            True se está em zona válida
        """
        valid = False
        
        # Verificar se está dentro do Order Block
        if order_block:
            if order_block.zone_low <= current_price <= order_block.zone_high:
                if (direction == "LONG" and order_block.type == "bullish") or \
                   (direction == "SHORT" and order_block.type == "bearish"):
                    valid = True
                    logger.debug("Price is inside valid Order Block")
        
        # Verificar se está dentro do FVG
        if not valid and fvg:
            if fvg.zone_low <= current_price <= fvg.zone_high:
                if (direction == "LONG" and fvg.type == "bullish") or \
                   (direction == "SHORT" and fvg.type == "bearish"):
                    valid = True
                    logger.debug("Price is inside valid FVG")
        
        # Verificar premium/discount
        if not valid and premium_discount:
            if direction == "LONG":
                if premium_discount.zone.name in ["DEEP_DISCOUNT", "DISCOUNT"]:
                    valid = True
                    logger.debug("Price is in discount zone for LONG")
            else:  # SHORT
                if premium_discount.zone.name in ["PREMIUM", "DEEP_PREMIUM"]:
                    valid = True
                    logger.debug("Price is in premium zone for SHORT")
        
        return valid
    
    @staticmethod
    def calculate_smc_confluence_score(smc_data: Dict[str, Any], direction: str) -> int:
        """
        Calcula score de confluência SMC total (0-4 pontos).
        
        Args:
            smc_data: Dados SMC completos
            direction: "LONG" ou "SHORT"
            
        Returns:
            Score de confluência SMC
        """
        order_blocks = smc_data.get('order_blocks', [])
        fvgs = smc_data.get('fvgs', [])
        structure = smc_data.get('structure')
        premium_discount = smc_data.get('premium_discount')
        liquidity_sweeps = smc_data.get('liquidity_sweeps', [])
        
        # Filtrar OBs e FVGs relevantes
        relevant_ob = None
        for ob in order_blocks:
            if ob.status.value == "FRESH":
                if (direction == "LONG" and ob.type == "bullish") or \
                   (direction == "SHORT" and ob.type == "bearish"):
                    relevant_ob = ob
                    break
        
        relevant_fvg = None
        for fvg in fvgs:
            if fvg.status.value == "OPEN":
                if (direction == "LONG" and fvg.type == "bullish") or \
                   (direction == "SHORT" and fvg.type == "bearish"):
                    relevant_fvg = fvg
                    break
        
        # Sweep recente
        recent_sweep = liquidity_sweeps[-1] if liquidity_sweeps else None
        
        # Calcular score
        score = SMCRules.evaluate_entry_quality(
            relevant_ob, relevant_fvg, structure, premium_discount,
            direction, recent_sweep
        )
        
        # Limitar a 4 pontos (de 5) para o score de confluência geral
        return min(score, 4)
