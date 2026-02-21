"""
Smart Money Concepts - Detecção algorítmica de estruturas de mercado.
Inclui: Swing Points, BOS, CHoCH, Order Blocks, FVGs, Liquidity, Premium/Discount.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SwingType(Enum):
    """Tipos de swing points."""
    HH = "Higher High"
    HL = "Higher Low"
    LH = "Lower High"
    LL = "Lower Low"


class StructureType(Enum):
    """Tipos de estrutura de mercado."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"


class ZoneStatus(Enum):
    """Status de zonas SMC."""
    FRESH = "FRESH"
    TESTED = "TESTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    MITIGATED = "MITIGATED"
    OPEN = "OPEN"
    FILLED = "FILLED"


class LiquidityType(Enum):
    """Tipos de liquidez."""
    BSL = "Buy Side Liquidity"  # Above swing highs
    SSL = "Sell Side Liquidity"  # Below swing lows


class PremiumDiscountZone(Enum):
    """Zonas de Premium/Discount."""
    DEEP_DISCOUNT = "DEEP_DISCOUNT"
    DISCOUNT = "DISCOUNT"
    EQUILIBRIUM = "EQUILIBRIUM"
    PREMIUM = "PREMIUM"
    DEEP_PREMIUM = "DEEP_PREMIUM"


@dataclass
class SwingPoint:
    """Ponto de swing no gráfico."""
    timestamp: int
    price: float
    type: SwingType
    index: int


@dataclass
class MarketStructure:
    """Estrutura de mercado."""
    type: StructureType
    swings: List[SwingPoint]
    last_update: int


@dataclass
class BOS:
    """Break of Structure."""
    timestamp: int
    price: float
    direction: str  # "bullish" ou "bearish"
    index: int


@dataclass
class CHoCH:
    """Change of Character."""
    timestamp: int
    price: float
    direction: str  # "bullish" ou "bearish"
    index: int


@dataclass
class OrderBlock:
    """Order Block."""
    timestamp: int
    zone_high: float
    zone_low: float
    type: str  # "bullish" ou "bearish"
    status: ZoneStatus
    strength: float
    index: int
    zone_id: Optional[int] = None


@dataclass
class FairValueGap:
    """Fair Value Gap."""
    timestamp: int
    zone_high: float
    zone_low: float
    type: str  # "bullish" ou "bearish"
    status: ZoneStatus
    index: int


@dataclass
class BreakerBlock:
    """Breaker Block (Order Block que falhou)."""
    timestamp: int
    zone_high: float
    zone_low: float
    type: str  # "bullish" ou "bearish"
    index: int


@dataclass
class LiquidityLevel:
    """Nível de liquidez."""
    price: float
    type: LiquidityType
    touch_count: int
    swept: bool
    strength: float


@dataclass
class LiquiditySweep:
    """Sweep de liquidez."""
    timestamp: int
    level: float
    direction: str  # "up" ou "down"
    index: int


@dataclass
class PremiumDiscount:
    """Posição Premium/Discount."""
    position: float  # 0-1 (0=discount, 0.5=equilibrium, 1=premium)
    zone: PremiumDiscountZone


class SmartMoneyConcepts:
    """
    Implementação algorítmica de Smart Money Concepts.
    Detecta estruturas de mercado institucionais.
    """
    
    @staticmethod
    def detect_swing_points(df: pd.DataFrame, lookback: int = 5) -> List[SwingPoint]:
        """
        Detecta swing highs e lows usando fractals.
        
        Args:
            df: DataFrame com 'high', 'low', 'timestamp'
            lookback: Número de velas para cada lado do fractal
            
        Returns:
            Lista de SwingPoints
        """
        swings = []
        
        for i in range(lookback, len(df) - lookback):
            # Swing High: high[i] > todos os highs ao redor
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and df['high'].iloc[j] >= df['high'].iloc[i]:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                # Determinar tipo de swing high
                if len(swings) > 0 and swings[-1].price < df['high'].iloc[i]:
                    swing_type = SwingType.HH
                elif len(swings) > 0:
                    swing_type = SwingType.LH
                else:
                    swing_type = SwingType.HH
                
                swings.append(SwingPoint(
                    timestamp=int(df['timestamp'].iloc[i]),
                    price=float(df['high'].iloc[i]),
                    type=swing_type,
                    index=i
                ))
            
            # Swing Low: low[i] < todos os lows ao redor
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and df['low'].iloc[j] <= df['low'].iloc[i]:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                # Determinar tipo de swing low
                if len(swings) > 0 and swings[-1].price > df['low'].iloc[i]:
                    swing_type = SwingType.LL
                elif len(swings) > 0:
                    swing_type = SwingType.HL
                else:
                    swing_type = SwingType.LL
                
                swings.append(SwingPoint(
                    timestamp=int(df['timestamp'].iloc[i]),
                    price=float(df['low'].iloc[i]),
                    type=swing_type,
                    index=i
                ))
        
        # Ordenar por índice
        swings.sort(key=lambda x: x.index)
        
        logger.debug(f"Detected {len(swings)} swing points")
        return swings
    
    @staticmethod
    def detect_market_structure(swings: List[SwingPoint]) -> MarketStructure:
        """
        Classifica estrutura de mercado com base nos swings.
        
        Args:
            swings: Lista de swing points
            
        Returns:
            MarketStructure
        """
        if len(swings) < 4:
            return MarketStructure(
                type=StructureType.RANGE,
                swings=swings,
                last_update=swings[-1].timestamp if swings else 0
            )
        
        # Analisar últimos swings
        recent_swings = swings[-6:]
        
        hh_count = sum(1 for s in recent_swings if s.type == SwingType.HH)
        hl_count = sum(1 for s in recent_swings if s.type == SwingType.HL)
        lh_count = sum(1 for s in recent_swings if s.type == SwingType.LH)
        ll_count = sum(1 for s in recent_swings if s.type == SwingType.LL)
        
        # Bullish: predominância de HH e HL
        if (hh_count + hl_count) > (lh_count + ll_count):
            structure_type = StructureType.BULLISH
        # Bearish: predominância de LH e LL
        elif (lh_count + ll_count) > (hh_count + hl_count):
            structure_type = StructureType.BEARISH
        else:
            structure_type = StructureType.RANGE
        
        return MarketStructure(
            type=structure_type,
            swings=swings,
            last_update=swings[-1].timestamp
        )
    
    @staticmethod
    def detect_bos(df: pd.DataFrame, swings: List[SwingPoint]) -> List[BOS]:
        """
        Detecta Break of Structure.
        
        Args:
            df: DataFrame com OHLC
            swings: Lista de swing points
            
        Returns:
            Lista de BOS
        """
        bos_list = []
        
        if len(swings) < 3:
            return bos_list
        
        for i in range(2, len(swings)):
            current = swings[i]
            prev = swings[i-1]
            prev_prev = swings[i-2]
            
            # Bullish BOS: preço quebra acima do swing high anterior
            if (current.type in [SwingType.HH, SwingType.LH] and 
                prev_prev.type in [SwingType.HH, SwingType.LH] and
                current.price > prev_prev.price):
                
                bos_list.append(BOS(
                    timestamp=current.timestamp,
                    price=current.price,
                    direction="bullish",
                    index=current.index
                ))
            
            # Bearish BOS: preço quebra abaixo do swing low anterior
            elif (current.type in [SwingType.LL, SwingType.HL] and 
                  prev_prev.type in [SwingType.LL, SwingType.HL] and
                  current.price < prev_prev.price):
                
                bos_list.append(BOS(
                    timestamp=current.timestamp,
                    price=current.price,
                    direction="bearish",
                    index=current.index
                ))
        
        logger.debug(f"Detected {len(bos_list)} BOS")
        return bos_list
    
    @staticmethod
    def detect_choch(df: pd.DataFrame, swings: List[SwingPoint]) -> List[CHoCH]:
        """
        Detecta Change of Character.
        
        Args:
            df: DataFrame com OHLC
            swings: Lista de swing points
            
        Returns:
            Lista de CHoCH
        """
        choch_list = []
        
        if len(swings) < 3:
            return choch_list
        
        for i in range(2, len(swings)):
            current = swings[i]
            prev = swings[i-1]
            
            # CHoCH: mudança na sequência de swings
            # Bullish CHoCH: de LL para HL
            if (prev.type == SwingType.LL and current.type == SwingType.HL):
                choch_list.append(CHoCH(
                    timestamp=current.timestamp,
                    price=current.price,
                    direction="bullish",
                    index=current.index
                ))
            
            # Bearish CHoCH: de HH para LH
            elif (prev.type == SwingType.HH and current.type == SwingType.LH):
                choch_list.append(CHoCH(
                    timestamp=current.timestamp,
                    price=current.price,
                    direction="bearish",
                    index=current.index
                ))
        
        logger.debug(f"Detected {len(choch_list)} CHoCH")
        return choch_list
    
    @staticmethod
    def detect_order_blocks(df: pd.DataFrame, swings: List[SwingPoint], 
                           bos_list: List[BOS], max_obs: int = 10) -> List[OrderBlock]:
        """
        Detecta Order Blocks.
        
        Args:
            df: DataFrame com OHLCV
            swings: Lista de swing points
            bos_list: Lista de BOS
            max_obs: Máximo de OBs ativos por vez
            
        Returns:
            Lista de OrderBlocks
        """
        order_blocks = []
        
        for bos in bos_list:
            # Encontrar a vela que causou o BOS
            bos_idx = bos.index
            
            if bos_idx < 10:
                continue
            
            # Bullish OB: última vela bearish antes do impulso bullish
            if bos.direction == "bullish":
                for i in range(bos_idx - 1, max(0, bos_idx - 20), -1):
                    if df['close'].iloc[i] < df['open'].iloc[i]:  # Vela bearish
                        ob = OrderBlock(
                            timestamp=int(df['timestamp'].iloc[i]),
                            zone_high=float(df['high'].iloc[i]),
                            zone_low=float(df['low'].iloc[i]),
                            type="bullish",
                            status=ZoneStatus.FRESH,
                            strength=1.0,
                            index=i
                        )
                        order_blocks.append(ob)
                        break
            
            # Bearish OB: última vela bullish antes do impulso bearish
            elif bos.direction == "bearish":
                for i in range(bos_idx - 1, max(0, bos_idx - 20), -1):
                    if df['close'].iloc[i] > df['open'].iloc[i]:  # Vela bullish
                        ob = OrderBlock(
                            timestamp=int(df['timestamp'].iloc[i]),
                            zone_high=float(df['high'].iloc[i]),
                            zone_low=float(df['low'].iloc[i]),
                            type="bearish",
                            status=ZoneStatus.FRESH,
                            strength=1.0,
                            index=i
                        )
                        order_blocks.append(ob)
                        break
        
        # Limitar número de OBs ativos
        if len(order_blocks) > max_obs:
            order_blocks = order_blocks[-max_obs:]
        
        logger.debug(f"Detected {len(order_blocks)} Order Blocks")
        return order_blocks
    
    @staticmethod
    def update_order_block_status(ob: OrderBlock, current_price: float, 
                                  current_high: float, current_low: float) -> OrderBlock:
        """
        Atualiza status do Order Block.
        
        Args:
            ob: Order Block
            current_price: Preço atual
            current_high: High atual
            current_low: Low atual
            
        Returns:
            OrderBlock atualizado
        """
        # Bullish OB testado se preço toca a zona
        if ob.type == "bullish":
            if current_low <= ob.zone_high and current_low >= ob.zone_low:
                ob.status = ZoneStatus.TESTED
            # Mitigado se preço fecha abaixo da zona
            if current_price < ob.zone_low:
                ob.status = ZoneStatus.MITIGATED
        
        # Bearish OB testado se preço toca a zona
        elif ob.type == "bearish":
            if current_high >= ob.zone_low and current_high <= ob.zone_high:
                ob.status = ZoneStatus.TESTED
            # Mitigado se preço fecha acima da zona
            if current_price > ob.zone_high:
                ob.status = ZoneStatus.MITIGATED
        
        return ob
    
    @staticmethod
    def detect_fvg(df: pd.DataFrame, max_fvgs: int = 10) -> List[FairValueGap]:
        """
        Detecta Fair Value Gaps.
        
        Args:
            df: DataFrame com OHLC
            max_fvgs: Máximo de FVGs ativos
            
        Returns:
            Lista de FVGs
        """
        fvgs = []
        
        for i in range(2, len(df)):
            # Bullish FVG: candle[i].low > candle[i-2].high
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                fvg = FairValueGap(
                    timestamp=int(df['timestamp'].iloc[i]),
                    zone_high=float(df['low'].iloc[i]),
                    zone_low=float(df['high'].iloc[i-2]),
                    type="bullish",
                    status=ZoneStatus.OPEN,
                    index=i
                )
                fvgs.append(fvg)
            
            # Bearish FVG: candle[i].high < candle[i-2].low
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                fvg = FairValueGap(
                    timestamp=int(df['timestamp'].iloc[i]),
                    zone_high=float(df['low'].iloc[i-2]),
                    zone_low=float(df['high'].iloc[i]),
                    type="bearish",
                    status=ZoneStatus.OPEN,
                    index=i
                )
                fvgs.append(fvg)
        
        # Limitar FVGs ativos
        if len(fvgs) > max_fvgs:
            fvgs = fvgs[-max_fvgs:]
        
        logger.debug(f"Detected {len(fvgs)} FVGs")
        return fvgs
    
    @staticmethod
    def update_fvg_status(fvg: FairValueGap, current_price: float,
                         current_high: float, current_low: float) -> FairValueGap:
        """Atualiza status do FVG."""
        if fvg.status == ZoneStatus.FILLED:
            return fvg
        
        # Verificar se o gap foi preenchido
        if current_high >= fvg.zone_low and current_low <= fvg.zone_high:
            mid_point = (fvg.zone_high + fvg.zone_low) / 2
            
            if fvg.type == "bullish":
                if current_low <= mid_point:
                    fvg.status = ZoneStatus.FILLED
                else:
                    fvg.status = ZoneStatus.PARTIALLY_FILLED
            else:  # bearish
                if current_high >= mid_point:
                    fvg.status = ZoneStatus.FILLED
                else:
                    fvg.status = ZoneStatus.PARTIALLY_FILLED
        
        return fvg
    
    @staticmethod
    def detect_breaker_blocks(mitigated_obs: List[OrderBlock]) -> List[BreakerBlock]:
        """
        Converte Order Blocks mitigados em Breaker Blocks (polaridade oposta).
        
        Args:
            mitigated_obs: Lista de OBs mitigados
            
        Returns:
            Lista de Breaker Blocks
        """
        breakers = []
        
        for ob in mitigated_obs:
            if ob.status == ZoneStatus.MITIGATED:
                # Inverte o tipo
                breaker_type = "bearish" if ob.type == "bullish" else "bullish"
                
                breaker = BreakerBlock(
                    timestamp=ob.timestamp,
                    zone_high=ob.zone_high,
                    zone_low=ob.zone_low,
                    type=breaker_type,
                    index=ob.index
                )
                breakers.append(breaker)
        
        logger.debug(f"Created {len(breakers)} Breaker Blocks")
        return breakers
    
    @staticmethod
    def detect_liquidity_levels(swings: List[SwingPoint], tolerance_pct: float = 0.001) -> List[LiquidityLevel]:
        """
        Detecta níveis de liquidez em swing highs/lows.
        
        Args:
            swings: Lista de swing points
            tolerance_pct: Tolerância para igualdade de preços (0.1%)
            
        Returns:
            Lista de níveis de liquidez
        """
        liquidity_levels = []
        
        # Agrupar swings por preço similar
        swing_groups = {}
        
        for swing in swings:
            found_group = False
            for price_key in swing_groups:
                if abs(swing.price - price_key) / price_key < tolerance_pct:
                    swing_groups[price_key].append(swing)
                    found_group = True
                    break
            
            if not found_group:
                swing_groups[swing.price] = [swing]
        
        # Criar níveis de liquidez para grupos com 2+ swings
        for price, group in swing_groups.items():
            if len(group) >= 2:
                # Determinar tipo (BSL ou SSL)
                is_high = any(s.type in [SwingType.HH, SwingType.LH] for s in group)
                liq_type = LiquidityType.BSL if is_high else LiquidityType.SSL
                
                level = LiquidityLevel(
                    price=price,
                    type=liq_type,
                    touch_count=len(group),
                    swept=False,
                    strength=len(group) / 2.0
                )
                liquidity_levels.append(level)
        
        logger.debug(f"Detected {len(liquidity_levels)} liquidity levels")
        return liquidity_levels
    
    @staticmethod
    def detect_liquidity_sweep(df: pd.DataFrame, liquidity_levels: List[LiquidityLevel]) -> List[LiquiditySweep]:
        """
        Detecta sweeps de liquidez.
        
        Args:
            df: DataFrame com OHLC
            liquidity_levels: Níveis de liquidez
            
        Returns:
            Lista de sweeps
        """
        sweeps = []
        
        for i in range(1, len(df)):
            for level in liquidity_levels:
                if level.swept:
                    continue
                
                # BSL sweep: preço vai acima e depois fecha abaixo
                if level.type == LiquidityType.BSL:
                    if (df['high'].iloc[i] > level.price and 
                        df['close'].iloc[i] < level.price):
                        sweep = LiquiditySweep(
                            timestamp=int(df['timestamp'].iloc[i]),
                            level=level.price,
                            direction="up",
                            index=i
                        )
                        sweeps.append(sweep)
                        level.swept = True
                
                # SSL sweep: preço vai abaixo e depois fecha acima
                elif level.type == LiquidityType.SSL:
                    if (df['low'].iloc[i] < level.price and 
                        df['close'].iloc[i] > level.price):
                        sweep = LiquiditySweep(
                            timestamp=int(df['timestamp'].iloc[i]),
                            level=level.price,
                            direction="down",
                            index=i
                        )
                        sweeps.append(sweep)
                        level.swept = True
        
        logger.debug(f"Detected {len(sweeps)} liquidity sweeps")
        return sweeps
    
    @staticmethod
    def calculate_premium_discount(swing_high: float, swing_low: float, 
                                   current_price: float) -> PremiumDiscount:
        """
        Calcula posição Premium/Discount em relação ao range.
        
        Args:
            swing_high: Swing high do range
            swing_low: Swing low do range
            current_price: Preço atual
            
        Returns:
            PremiumDiscount
        """
        if swing_high == swing_low:
            return PremiumDiscount(position=0.5, zone=PremiumDiscountZone.EQUILIBRIUM)
        
        position = (current_price - swing_low) / (swing_high - swing_low)
        position = max(0, min(1, position))  # Clamp 0-1
        
        # Classificar zona
        if position < 0.2:
            zone = PremiumDiscountZone.DEEP_DISCOUNT
        elif position < 0.4:
            zone = PremiumDiscountZone.DISCOUNT
        elif position < 0.6:
            zone = PremiumDiscountZone.EQUILIBRIUM
        elif position < 0.8:
            zone = PremiumDiscountZone.PREMIUM
        else:
            zone = PremiumDiscountZone.DEEP_PREMIUM
        
        return PremiumDiscount(position=position, zone=zone)
    
    @classmethod
    def calculate_all_smc(cls, df: pd.DataFrame, swings: Optional[List[SwingPoint]] = None) -> dict:
        """
        Pipeline completo de SMC.
        
        Args:
            df: DataFrame com OHLCV
            swings: Swings pré-calculados (opcional)
            
        Returns:
            Dicionário com todas as estruturas SMC
        """
        if df.empty or len(df) < 10:
            logger.warning("Insufficient data for SMC analysis")
            return {}
        
        # Detect swings se não fornecidos
        if swings is None:
            swings = cls.detect_swing_points(df)
        
        # Market structure
        structure = cls.detect_market_structure(swings)
        
        # BOS e CHoCH
        bos_list = cls.detect_bos(df, swings)
        choch_list = cls.detect_choch(df, swings)
        
        # Order Blocks
        order_blocks = cls.detect_order_blocks(df, swings, bos_list)
        
        # FVGs
        fvgs = cls.detect_fvg(df)
        
        # Liquidity
        liquidity_levels = cls.detect_liquidity_levels(swings)
        liquidity_sweeps = cls.detect_liquidity_sweep(df, liquidity_levels)
        
        # Premium/Discount
        if len(swings) >= 2:
            recent_highs = [s.price for s in swings if s.type in [SwingType.HH, SwingType.LH]]
            recent_lows = [s.price for s in swings if s.type in [SwingType.LL, SwingType.HL]]
            
            if recent_highs and recent_lows:
                swing_high = max(recent_highs[-3:]) if len(recent_highs) >= 3 else max(recent_highs)
                swing_low = min(recent_lows[-3:]) if len(recent_lows) >= 3 else min(recent_lows)
                current_price = float(df['close'].iloc[-1])
                premium_discount = cls.calculate_premium_discount(swing_high, swing_low, current_price)
            else:
                premium_discount = None
        else:
            premium_discount = None
        
        result = {
            'swings': swings,
            'structure': structure,
            'bos': bos_list,
            'choch': choch_list,
            'order_blocks': order_blocks,
            'fvgs': fvgs,
            'liquidity_levels': liquidity_levels,
            'liquidity_sweeps': liquidity_sweeps,
            'premium_discount': premium_discount
        }
        
        logger.debug("Completed SMC analysis")
        return result
