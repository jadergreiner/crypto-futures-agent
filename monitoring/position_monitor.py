"""
Monitor de posições abertas na Binance Futures em tempo real.
Coleta dados, calcula indicadores, gera decisões e persiste tudo para aprendizado futuro.
"""

import time
import signal
import logging
import json
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
)

from data.database import DatabaseManager
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts, SwingType
from agent.risk_manager import RiskManager
from monitoring.alerts import AlertManager
from monitoring.logger import AgentLogger
from config.risk_params import RISK_PARAMS

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Prioridades das ações para evitar downgrade de decisões críticas
ACTION_PRIORITY = {
    'HOLD': 0,
    'REDUCE_50': 1,
    'CLOSE': 2
}


class PositionMonitor:
    """
    Monitora posições abertas na Binance Futures em tempo real.
    Coleta dados, calcula indicadores, gera decisão e persiste tudo.
    """
    
    def __init__(self, client: DerivativesTradingUsdsFutures, db: DatabaseManager, mode: str = "paper"):
        """
        Inicializa o monitor de posições.
        
        Args:
            client: Cliente SDK Binance
            db: Gerenciador de banco de dados
            mode: Modo de operação ("paper" ou "live")
        """
        self._client = client
        self.db = db
        self.mode = mode
        self.collector = BinanceCollector(client)
        self.sentiment_collector = SentimentCollector(client)
        self.technical = TechnicalIndicators()
        self.smc = SmartMoneyConcepts()
        self.risk_manager = RiskManager()
        self.alert_manager = AlertManager()
        self._running = False
        
        logger.info(f"PositionMonitor inicializado em modo {mode}")
    
    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK.
        
        O SDK Binance encapsula respostas em um objeto ApiResponse.
        O atributo .data pode ser uma property (acesso direto) ou um método (precisa chamar).
        
        Args:
            response: Resposta bruta do SDK (ApiResponse ou dados diretos)
            
        Returns:
            Os dados reais (list, dict, etc.)
        """
        if response is None:
            return None
        
        # ApiResponse tem um atributo .data contendo o payload real
        if hasattr(response, 'data'):
            data = response.data
            # .data pode ser um método que precisa ser chamado
            if callable(data):
                return data()
            return data
        
        # Se já são os dados brutos (list, dict), retorna como está
        return response
    
    def _safe_get(self, obj, attr, default=None):
        """
        Extrai atributo de objeto SDK ou dict de forma segura.
        Suporta múltiplas variantes de nomes (camelCase e snake_case).
        
        Args:
            obj: Objeto SDK ou dict
            attr: Nome do atributo ou lista de variantes (ex: ['positionAmt', 'position_amt'])
            default: Valor padrão se não encontrado (None por padrão)
            
        Returns:
            Valor do atributo ou default
        """
        # Se attr é uma lista, tenta cada variante
        if isinstance(attr, list):
            for attr_name in attr:
                result = self._safe_get(obj, attr_name, default=None)
                if result is not None:
                    return result
            return default
        
        # Caso base: attr é uma string
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
    
    def fetch_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca posições abertas na Binance via SDK.
        
        Args:
            symbol: Símbolo específico (opcional). Se None, busca todas.
            
        Returns:
            Lista de dicts com dados das posições
        """
        try:
            # Método correto do SDK: position_information_v2()
            response = self._client.rest_api.position_information_v2(symbol=symbol)
            data = self._extract_data(response)
            
            positions = []
            
            if data is None:
                return positions
            
            # Garantir que é lista
            if not isinstance(data, list):
                data = [data]
            
            for pos_data in data:
                # Extrair position_amt — pode ser atributo Pydantic ou dict
                # SDK retorna objetos Pydantic com atributos snake_case
                position_amt = float(self._safe_get(pos_data, ['position_amt', 'positionAmt'], 0))
                
                # Filtrar apenas posições abertas (positionAmt != 0)
                if position_amt == 0:
                    continue
                
                # Determinar direção
                direction = "LONG" if position_amt > 0 else "SHORT"
                
                # Construir dict estruturado usando _safe_get para compatibilidade
                # Nota: SDK v2 retorna objetos Pydantic com snake_case, mas mantemos fallback para camelCase
                
                # Normalizar margin_type: API pode retornar 'cross', 'CROSS', 'isolated', 'ISOLATED', None, ou ''
                raw_margin_type = self._safe_get(pos_data, ['margin_type', 'marginType'], 'isolated')
                # Tratar None e strings vazias como 'ISOLATED'
                margin_type = str(raw_margin_type).upper() if raw_margin_type and str(raw_margin_type).strip() else 'ISOLATED'
                
                position = {
                    'symbol': self._safe_get(pos_data, 'symbol', ''),
                    'direction': direction,
                    'entry_price': float(self._safe_get(pos_data, ['entry_price', 'entryPrice'], 0)),
                    'mark_price': float(self._safe_get(pos_data, ['mark_price', 'markPrice'], 0)),
                    'liquidation_price': float(self._safe_get(pos_data, ['liquidation_price', 'liquidationPrice'], 0)),
                    'position_size_qty': abs(position_amt),
                    'leverage': int(self._safe_get(pos_data, 'leverage', 1)),
                    'margin_type': margin_type,
                    'unrealized_pnl': float(self._safe_get(pos_data, ['un_realized_profit', 'unRealizedProfit'], 0)),
                    'isolated_wallet': float(self._safe_get(pos_data, ['isolated_wallet', 'isolatedWallet'], 0)),
                }
                
                # Calcular tamanho em USDT (valor nocional)
                position['position_size_usdt'] = position['position_size_qty'] * position['mark_price']
                
                # Calcular margem investida (notional / leverage)
                # Esta é a margem real usada para abrir a posição
                if position['leverage'] > 0:
                    position['margin_invested'] = position['position_size_usdt'] / position['leverage']
                else:
                    position['margin_invested'] = position['position_size_usdt']
                
                # Calcular PnL % baseado na margem investida (não no valor nocional)
                # Isso reflete o retorno real sobre o capital investido
                if position['margin_invested'] > 0:
                    position['unrealized_pnl_pct'] = (position['unrealized_pnl'] / position['margin_invested']) * 100
                else:
                    position['unrealized_pnl_pct'] = 0
                
                # Margin balance (para isolated) ou wallet isolada
                position['margin_balance'] = position['isolated_wallet']
                
                positions.append(position)
                logger.info(f"Posição encontrada: {position['symbol']} {position['direction']} "
                           f"[{position['margin_type']}] Margem: {position['margin_invested']:.2f} USDT "
                           f"PnL: {position['unrealized_pnl']:.2f} USDT ({position['unrealized_pnl_pct']:.2f}%)")
            
            return positions
            
        except Exception as e:
            logger.error(f"Erro ao buscar posições: {e}")
            traceback.print_exc()
            return []
    
    def fetch_account_balance(self) -> float:
        """
        Busca o saldo total da conta (para cálculo de risco em cross margin).
        
        Returns:
            Saldo total disponível em USDT, ou 0 em caso de erro
        """
        # Tentativa 1: chamada normal com recv_window para tolerância de clock
        try:
            # recv_window aumenta tolerância para diferenças de clock (10 segundos)
            response = self._client.rest_api.account_information_v2(recv_window=10000)
            data = self._extract_data(response)
            
            if data is None:
                return 0
            
            # Extrair available balance (total disponível)
            # SDK retorna objeto com atributo available_balance ou availableBalance
            available_balance = float(self._safe_get(data, ['available_balance', 'availableBalance'], 0))
            
            logger.debug(f"Saldo disponível na conta: {available_balance:.2f} USDT")
            return available_balance
            
        except Exception as e:
            # Verificar se é erro de timestamp (-1021)
            error_str = str(e)
            if '-1021' in error_str or 'Timestamp' in error_str:
                logger.warning(f"Erro de timestamp detectado (-1021). Aguardando 500ms e tentando novamente...")
                try:
                    # Aguardar 500ms e tentar novamente
                    time.sleep(0.5)
                    response = self._client.rest_api.account_information_v2(recv_window=10000)
                    data = self._extract_data(response)
                    
                    if data is None:
                        return 0
                    
                    available_balance = float(self._safe_get(data, ['available_balance', 'availableBalance'], 0))
                    logger.debug(f"Saldo disponível na conta (retry): {available_balance:.2f} USDT")
                    return available_balance
                    
                except Exception as retry_error:
                    logger.warning(f"Erro ao buscar saldo da conta (retry): {retry_error}")
                    return 0
            else:
                logger.warning(f"Erro ao buscar saldo da conta: {e}")
                return 0
    
    def fetch_current_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Busca dados de mercado atuais para um símbolo.
        
        Args:
            symbol: Símbolo a buscar
            
        Returns:
            Dict com DataFrames de OHLCV e dados de sentimento
        """
        try:
            # Buscar candles H1 (últimas 200 para cálculo de indicadores)
            # fetch_klines já retorna DataFrame
            df_h1 = self.collector.fetch_klines(symbol, "1h", limit=200)
            
            # Buscar candles H4 (últimas 200)
            df_h4 = self.collector.fetch_klines(symbol, "4h", limit=200)
            
            # Buscar sentiment
            sentiment = self.sentiment_collector.fetch_all_sentiment(symbol)
            
            return {
                'h1': df_h1,
                'h4': df_h4,
                'sentiment': sentiment
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de mercado para {symbol}: {e}")
            return {'h1': pd.DataFrame(), 'h4': pd.DataFrame(), 'sentiment': {}}
    
    def calculate_indicators_snapshot(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula indicadores técnicos e SMC para o momento atual.
        
        Args:
            symbol: Símbolo
            market_data: Dados de mercado (candles + sentiment)
            
        Returns:
            Dict com todos os indicadores calculados
        """
        indicators = {}
        
        try:
            # Calcular indicadores técnicos no H4
            df_h4 = market_data.get('h4')
            if df_h4 is not None and not df_h4.empty:
                df_h4 = self.technical.calculate_all(df_h4)
                
                # Pegar última linha (momento atual)
                last_row = df_h4.iloc[-1]
                
                indicators['rsi_14'] = last_row.get('rsi_14')
                indicators['ema_17'] = last_row.get('ema_17')
                indicators['ema_34'] = last_row.get('ema_34')
                indicators['ema_72'] = last_row.get('ema_72')
                indicators['ema_144'] = last_row.get('ema_144')
                indicators['macd_line'] = last_row.get('macd_line')
                indicators['macd_signal'] = last_row.get('macd_signal')
                indicators['macd_histogram'] = last_row.get('macd_histogram')
                indicators['bb_upper'] = last_row.get('bb_upper')
                indicators['bb_lower'] = last_row.get('bb_lower')
                indicators['bb_percent_b'] = last_row.get('bb_percent_b')
                indicators['atr_14'] = last_row.get('atr_14')
                indicators['adx_14'] = last_row.get('adx_14')
                indicators['di_plus'] = last_row.get('di_plus')
                indicators['di_minus'] = last_row.get('di_minus')
            
            # Calcular SMC no H1
            df_h1 = market_data.get('h1')
            if df_h1 is not None and not df_h1.empty:
                # 1. Detectar swing points primeiro
                swings = self.smc.detect_swing_points(df_h1, lookback=5)
                
                # 2. Detectar estrutura de mercado (precisa de lista de swings, não DataFrame)
                if swings:
                    structure = self.smc.detect_market_structure(swings)
                    # Defensive: verificar se structure e structure.type existem
                    indicators['market_structure'] = structure.type.value if (structure and hasattr(structure, 'type') and structure.type) else 'range'
                else:
                    indicators['market_structure'] = 'range'
                
                # 3. Detectar BOS e CHoCH
                bos_list = self.smc.detect_bos(df_h1, swings) if swings else []
                choch_list = self.smc.detect_choch(df_h1, swings) if swings else []
                
                indicators['bos_recent'] = 1 if bos_list else 0
                indicators['choch_recent'] = 1 if choch_list else 0
                
                # 4. Order Blocks (precisa de df, swings, bos_list)
                obs = self.smc.detect_order_blocks(df_h1, swings, bos_list) if swings else []
                current_price = df_h1.iloc[-1]['close']
                
                # Calcular distância até OB mais próximo
                # Order Blocks são dataclasses, não dicts - usar atributos
                if obs:
                    closest_ob_distance = min([
                        abs((ob.zone_high + ob.zone_low) / 2 - current_price) / current_price * 100
                        for ob in obs
                    ])
                    indicators['nearest_ob_distance_pct'] = closest_ob_distance
                else:
                    indicators['nearest_ob_distance_pct'] = None
                
                # 5. Fair Value Gaps (método correto é detect_fvg)
                fvgs = self.smc.detect_fvg(df_h1)
                
                # FVGs também são dataclasses - usar zone_high e zone_low
                if fvgs:
                    closest_fvg_distance = min([
                        abs((fvg.zone_high + fvg.zone_low) / 2 - current_price) / current_price * 100
                        for fvg in fvgs
                    ])
                    indicators['nearest_fvg_distance_pct'] = closest_fvg_distance
                else:
                    indicators['nearest_fvg_distance_pct'] = None
                
                # 6. Premium/Discount Zone
                swing_high = df_h1['high'].rolling(20).max().iloc[-1]
                swing_low = df_h1['low'].rolling(20).min().iloc[-1]
                range_size = swing_high - swing_low
                
                if range_size > 0:
                    position_in_range = (current_price - swing_low) / range_size
                    
                    if position_in_range > 0.75:
                        indicators['premium_discount_zone'] = 'deep_premium'
                    elif position_in_range > 0.6:
                        indicators['premium_discount_zone'] = 'premium'
                    elif position_in_range > 0.4:
                        indicators['premium_discount_zone'] = 'equilibrium'
                    elif position_in_range > 0.25:
                        indicators['premium_discount_zone'] = 'discount'
                    else:
                        indicators['premium_discount_zone'] = 'deep_discount'
                else:
                    indicators['premium_discount_zone'] = 'equilibrium'
                
                # 7. Liquidez (calcular a partir dos swings, detect_liquidity não existe)
                # Estimar liquidez a partir dos swing points
                if swings:
                    # Buy Side Liquidity (BSL) = pontos de swing high (HH e LH)
                    bsl_points = [s.price for s in swings if s.type in [SwingType.HH, SwingType.LH]]
                    # Sell Side Liquidity (SSL) = pontos de swing low (LL e HL)
                    ssl_points = [s.price for s in swings if s.type in [SwingType.LL, SwingType.HL]]
                    
                    if bsl_points:
                        max_bsl = max(bsl_points)
                        indicators['liquidity_above_pct'] = ((max_bsl - current_price) / current_price) * 100
                    else:
                        indicators['liquidity_above_pct'] = None
                    
                    if ssl_points:
                        min_ssl = min(ssl_points)
                        indicators['liquidity_below_pct'] = ((current_price - min_ssl) / current_price) * 100
                    else:
                        indicators['liquidity_below_pct'] = None
                else:
                    indicators['liquidity_above_pct'] = None
                    indicators['liquidity_below_pct'] = None
            
            # Sentimento
            sentiment = market_data.get('sentiment', {})
            indicators['funding_rate'] = sentiment.get('funding_rate')
            indicators['long_short_ratio'] = sentiment.get('long_short_ratio')
            indicators['open_interest_change_pct'] = sentiment.get('open_interest_change_pct')
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores para {symbol}: {e}")
        
        return indicators
    
    def _update_action_if_higher_priority(self, decision: Dict[str, Any], new_action: str, 
                                         new_confidence: float, reasoning: List[str], 
                                         reasoning_msg: str) -> None:
        """
        Atualiza a ação apenas se a nova ação tem prioridade estritamente maior.
        Isso evita downgrade de decisões críticas (ex: CLOSE -> REDUCE_50).
        
        Comportamento por prioridade:
        - Upgrade (new > current): Atualiza ação e confiança, adiciona reasoning com marcador UPGRADE
        - Igual (new == current): Mantém ação, atualiza confiança se maior, adiciona marcador CONFIRMAÇÃO
        - Downgrade (new < current): Bloqueia completamente, não adiciona reasoning
        
        Args:
            decision: Dict da decisão a ser atualizado
            new_action: Nova ação proposta
            new_confidence: Nova confiança
            reasoning: Lista de raciocínios (modificada in-place)
            reasoning_msg: Mensagem de raciocínio a adicionar
        """
        current_priority = ACTION_PRIORITY.get(decision['agent_action'])
        new_priority = ACTION_PRIORITY.get(new_action)
        
        # Validar que as ações são conhecidas
        if current_priority is None:
            logger.warning(f"Ação desconhecida no dicionário de prioridades: {decision['agent_action']}")
            current_priority = 0
        if new_priority is None:
            logger.warning(f"Ação desconhecida no dicionário de prioridades: {new_action}")
            new_priority = 0
        
        if new_priority > current_priority:
            # Upgrade permitido
            decision['agent_action'] = new_action
            decision['decision_confidence'] = new_confidence
            reasoning.append(f"[UPGRADE] {reasoning_msg}")
        elif new_priority == current_priority:
            # Mesma prioridade - atualizar confiança se for maior
            if new_confidence > decision['decision_confidence']:
                decision['decision_confidence'] = new_confidence
            reasoning.append(f"[CONFIRMAÇÃO] {reasoning_msg}")
        # Se new_priority < current_priority, não faz nada (downgrade bloqueado)
    
    def evaluate_position(self, position: Dict[str, Any], indicators: Dict[str, Any], 
                         sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avalia a posição e gera decisão baseada em regras.
        Core da lógica de decisão antes do RL estar treinado.
        
        Args:
            position: Dados da posição
            indicators: Indicadores calculados
            sentiment: Dados de sentimento
            
        Returns:
            Dict com decisão e parâmetros de risco
        """
        decision = {
            'agent_action': 'HOLD',
            'decision_confidence': 0.5,
            'decision_reasoning': [],
            'risk_score': 5.0,
            'stop_loss_suggested': None,
            'take_profit_suggested': None,
            'trailing_stop_price': None
        }
        
        reasoning = []
        risk_score = 0.0
        
        # Extrair dados importantes
        direction = position['direction']
        pnl_pct = position['unrealized_pnl_pct']
        mark_price = position['mark_price']
        entry_price = position['entry_price']
        liquidation_price = position['liquidation_price']
        margin_type = position.get('margin_type', 'ISOLATED')
        
        # VERIFICAR SE É CROSS MARGIN E AJUSTAR RISCO
        # Cross margin significa que TODO o saldo da conta está em risco, não apenas a margem isolada
        if margin_type == 'CROSS':
            cross_margin_multiplier = RISK_PARAMS.get('cross_margin_risk_multiplier', 1.5)
            risk_score += 2.0  # Risco base aumentado para cross margin
            reasoning.append(f"[AVISO] Posição em CROSS MARGIN - todo saldo da conta está em risco")
            
            # Buscar saldo total da conta para contexto de risco
            account_balance = self.fetch_account_balance()
            if account_balance > 0:
                # Calcular margem ratio baseado no saldo total
                margin_invested = position.get('margin_invested', 0)
                if margin_invested > 0:
                    account_risk_pct = (margin_invested / account_balance) * 100
                    reasoning.append(f"Exposição da conta: {account_risk_pct:.1f}% do saldo total")
                    
                    # Se a posição usa uma grande parte do saldo, aumentar ainda mais o risco
                    if account_risk_pct > 50:
                        risk_score += 1.5
                        reasoning.append(f"[ATENÇÃO] Alta exposição em cross margin (>{account_risk_pct:.0f}% do saldo)")
                else:
                    # margin_invested ausente ou zero indica inconsistência nos dados
                    logger.warning(f"margin_invested ausente ou zero para posição cross margin {position.get('symbol')}")
                    reasoning.append(f"[AVISO] Não foi possível calcular exposição da conta (margin_invested ausente)")
            else:
                # account_balance == 0 significa que a API falhou
                # Para posições lucrativas, reduzir risk_score para compensar multiplicador cross margin
                # Para posições em prejuízo, adicionar pequena penalidade
                if pnl_pct > 10:
                    # Posição muito lucrativa: reduzir risco significativamente
                    # para compensar o efeito do multiplicador cross margin (1.5x)
                    risk_score -= 2.5
                    reasoning.append(f"[INFO] Saldo da conta indisponível - avaliação de risco baseada apenas em dados da posição")
                elif pnl_pct > 0:
                    # Posição lucrativa: reduzir risco moderadamente
                    risk_score -= 1.0
                    reasoning.append(f"[INFO] Saldo da conta indisponível - avaliação de risco baseada apenas em dados da posição")
                else:
                    # Posição em prejuízo: adicionar pequena penalidade
                    risk_score += 0.5
                    reasoning.append(f"[INFO] Saldo da conta indisponível - avaliação de risco baseada apenas em dados da posição")
        
        # 1. VERIFICAR PROXIMIDADE DA LIQUIDAÇÃO (CRÍTICO)
        if liquidation_price and liquidation_price > 0:
            distance_to_liq_pct = abs((mark_price - liquidation_price) / mark_price) * 100
            
            # Para cross margin, o risco é ainda maior pois afeta todo o saldo
            liquidation_threshold = 5  # 5% base
            if margin_type == 'CROSS':
                liquidation_threshold = 8  # Mais margem de segurança para cross
                
            if distance_to_liq_pct < liquidation_threshold:
                decision['agent_action'] = 'CLOSE'
                decision['decision_confidence'] = 0.95
                reasoning.append(f"Preço muito próximo da liquidação ({distance_to_liq_pct:.1f}%)")
                if margin_type == 'CROSS':
                    reasoning.append(f"[CRÍTICO] Liquidação em cross margin afetaria TODO o saldo da conta")
                risk_score += 5.0
        
        # 2. VERIFICAR STOP LOSS (PnL NEGATIVO GRANDE)
        max_stop_distance = RISK_PARAMS['max_stop_distance_pct'] * 100  # 3%
        if pnl_pct < -max_stop_distance:
            decision['agent_action'] = 'CLOSE'
            decision['decision_confidence'] = 0.90
            reasoning.append(f"PnL excedeu stop loss máximo ({pnl_pct:.2f}% < -{max_stop_distance}%)")
            risk_score += 3.0
        
        # 3. VERIFICAR REVERSÃO DE ESTRUTURA (CHoCH contra a posição)
        market_structure = indicators.get('market_structure', 'range')
        choch_recent = indicators.get('choch_recent', 0)
        
        if choch_recent:
            if (direction == 'LONG' and market_structure == 'bearish') or \
               (direction == 'SHORT' and market_structure == 'bullish'):
                if pnl_pct > 0:
                    self._update_action_if_higher_priority(
                        decision, 'REDUCE_50', 0.75, reasoning,
                        f"CHoCH detectado contra posição {direction} (estrutura: {market_structure})"
                    )
                    risk_score += 2.0
                else:
                    self._update_action_if_higher_priority(
                        decision, 'CLOSE', 0.85, reasoning,
                        f"CHoCH + PnL negativo em {direction}"
                    )
                    risk_score += 3.0
        
        # 4. VERIFICAR INDICADORES TÉCNICOS
        rsi = indicators.get('rsi_14')
        ema_17 = indicators.get('ema_17')
        ema_72 = indicators.get('ema_72')
        
        if rsi and ema_17 and ema_72:
            if direction == 'LONG':
                # LONG: sinal de reversão se RSI < 30 OU preço abaixo da EMA72
                if rsi < 30 or mark_price < ema_72:
                    if pnl_pct > 5:
                        # Lucro bom, reduzir para garantir
                        self._update_action_if_higher_priority(
                            decision, 'REDUCE_50', 0.70, reasoning,
                            f"LONG em zona de risco (RSI: {rsi:.1f}, preço abaixo EMA72)"
                        )
                        risk_score += 1.5
                    elif pnl_pct < 0:
                        self._update_action_if_higher_priority(
                            decision, 'CLOSE', 0.80, reasoning,
                            f"LONG em prejuízo e indicadores negativos"
                        )
                        risk_score += 2.5
                        
                # LONG favorável: RSI > 50, preço acima EMAs
                elif rsi > 50 and mark_price > ema_17 and mark_price > ema_72:
                    reasoning.append(f"LONG em estrutura favorável (RSI: {rsi:.1f})")
                    risk_score -= 1.0
            
            elif direction == 'SHORT':
                # SHORT: sinal de reversão se RSI > 70 OU preço acima da EMA72
                if rsi > 70 or mark_price > ema_72:
                    if pnl_pct > 5:
                        self._update_action_if_higher_priority(
                            decision, 'REDUCE_50', 0.70, reasoning,
                            f"SHORT em zona de risco (RSI: {rsi:.1f}, preço acima EMA72)"
                        )
                        risk_score += 1.5
                    elif pnl_pct < 0:
                        self._update_action_if_higher_priority(
                            decision, 'CLOSE', 0.80, reasoning,
                            f"SHORT em prejuízo e indicadores negativos"
                        )
                        risk_score += 2.5
                
                # SHORT favorável: RSI < 50, preço abaixo EMAs
                elif rsi < 50 and mark_price < ema_17 and mark_price < ema_72:
                    reasoning.append(f"SHORT em estrutura favorável (RSI: {rsi:.1f})")
                    risk_score -= 1.0
        
        # 5. VERIFICAR FUNDING RATE EXTREMO
        funding_rate = indicators.get('funding_rate', 0)
        funding_threshold = RISK_PARAMS.get('extreme_funding_rate_threshold', 0.05)
        
        if funding_rate:
            funding_pct = funding_rate * 100
            
            # Funding muito positivo = muitos LONGs (ruim para LONG)
            if direction == 'LONG' and funding_pct > funding_threshold:
                self._update_action_if_higher_priority(
                    decision, 'REDUCE_50', 0.65, reasoning,
                    f"Funding rate extremo contra LONG ({funding_pct:.4f}%)"
                )
                risk_score += 1.0
            
            # Funding muito negativo = muitos SHORTs (ruim para SHORT)
            elif direction == 'SHORT' and funding_pct < -funding_threshold:
                self._update_action_if_higher_priority(
                    decision, 'REDUCE_50', 0.65, reasoning,
                    f"Funding rate extremo contra SHORT ({funding_pct:.4f}%)"
                )
                risk_score += 1.0
        
        # 6. VERIFICAR ATR EXPANSION (volatilidade aumentando)
        atr = indicators.get('atr_14')
        if atr:
            # Se ATR > 5% do preço, volatilidade alta
            atr_pct = (atr / mark_price) * 100
            if atr_pct > 5:
                reasoning.append(f"Alta volatilidade (ATR: {atr_pct:.2f}%)")
                risk_score += 1.0
        
        # 7. CALCULAR RISK SCORE FINAL
        risk_score = max(0.0, min(10.0, 5.0 + risk_score))  # Normalizar 0-10
        
        # Aplicar multiplicador de risco para cross margin
        if margin_type == 'CROSS':
            cross_margin_multiplier = RISK_PARAMS.get('cross_margin_risk_multiplier', 1.5)
            risk_score = min(10.0, risk_score * cross_margin_multiplier)
            logger.debug(f"Risk score ajustado para cross margin: {risk_score:.2f}")
        
        decision['risk_score'] = risk_score
        decision['decision_reasoning'] = json.dumps(reasoning)
        
        # 8. CALCULAR STOPS E TARGETS SUGERIDOS
        if atr:
            # Stop loss baseado em ATR
            stop_multiplier = RISK_PARAMS['stop_loss_atr_multiplier']
            tp_multiplier = RISK_PARAMS['take_profit_atr_multiplier']
            
            if direction == 'LONG':
                decision['stop_loss_suggested'] = entry_price - (atr * stop_multiplier)
                decision['take_profit_suggested'] = entry_price + (atr * tp_multiplier)
            else:  # SHORT
                decision['stop_loss_suggested'] = entry_price + (atr * stop_multiplier)
                decision['take_profit_suggested'] = entry_price - (atr * tp_multiplier)
            
            # Trailing stop (ativar se PnL > activation_r)
            activation_r = RISK_PARAMS.get('trailing_stop_activation_r_multiple', 1.5)
            if pnl_pct > (stop_multiplier * activation_r):
                trail_multiplier = RISK_PARAMS['trailing_stop_atr_multiplier']
                if direction == 'LONG':
                    decision['trailing_stop_price'] = mark_price - (atr * trail_multiplier)
                else:
                    decision['trailing_stop_price'] = mark_price + (atr * trail_multiplier)
        
        # 9. AJUSTAR CONFIANÇA
        if decision['agent_action'] == 'HOLD':
            # Confiança proporcional ao risco (risco baixo = confiança alta)
            decision['decision_confidence'] = 1.0 - (risk_score / 10.0)
        
        # Se não há reasoning, adicionar motivo padrão
        if not reasoning:
            reasoning.append("Posição estável, sem sinais de reversão")
            decision['decision_reasoning'] = json.dumps(reasoning)
        
        logger.info(f"Decisão para {position['symbol']} {direction}: {decision['agent_action']} "
                   f"(confiança: {decision['decision_confidence']:.2f}, risco: {risk_score:.1f}/10)")
        
        return decision
    
    def create_snapshot(self, position: Dict[str, Any], indicators: Dict[str, Any], 
                       sentiment: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monta o dict completo com TODOS os campos da tabela position_snapshots.
        
        Args:
            position: Dados da posição
            indicators: Indicadores calculados
            sentiment: Dados de sentimento
            decision: Decisão gerada
            
        Returns:
            Dict completo para inserção no banco
        """
        snapshot = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'symbol': position['symbol'],
            
            # Dados da posição
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'mark_price': position['mark_price'],
            'liquidation_price': position.get('liquidation_price'),
            'position_size_qty': position['position_size_qty'],
            'position_size_usdt': position['position_size_usdt'],
            'leverage': position['leverage'],
            'margin_type': position['margin_type'],
            'margin_invested': position.get('margin_invested'),  # Margem real investida
            'unrealized_pnl': position['unrealized_pnl'],
            'unrealized_pnl_pct': position['unrealized_pnl_pct'],
            'margin_balance': position.get('margin_balance'),
            
            # Indicadores técnicos
            'rsi_14': indicators.get('rsi_14'),
            'ema_17': indicators.get('ema_17'),
            'ema_34': indicators.get('ema_34'),
            'ema_72': indicators.get('ema_72'),
            'ema_144': indicators.get('ema_144'),
            'macd_line': indicators.get('macd_line'),
            'macd_signal': indicators.get('macd_signal'),
            'macd_histogram': indicators.get('macd_histogram'),
            'bb_upper': indicators.get('bb_upper'),
            'bb_lower': indicators.get('bb_lower'),
            'bb_percent_b': indicators.get('bb_percent_b'),
            'atr_14': indicators.get('atr_14'),
            'adx_14': indicators.get('adx_14'),
            'di_plus': indicators.get('di_plus'),
            'di_minus': indicators.get('di_minus'),
            
            # SMC
            'market_structure': indicators.get('market_structure'),
            'bos_recent': indicators.get('bos_recent', 0),
            'choch_recent': indicators.get('choch_recent', 0),
            'nearest_ob_distance_pct': indicators.get('nearest_ob_distance_pct'),
            'nearest_fvg_distance_pct': indicators.get('nearest_fvg_distance_pct'),
            'premium_discount_zone': indicators.get('premium_discount_zone'),
            'liquidity_above_pct': indicators.get('liquidity_above_pct'),
            'liquidity_below_pct': indicators.get('liquidity_below_pct'),
            
            # Sentimento
            'funding_rate': indicators.get('funding_rate'),
            'long_short_ratio': indicators.get('long_short_ratio'),
            'open_interest_change_pct': indicators.get('open_interest_change_pct'),
            
            # Decisão
            'agent_action': decision['agent_action'],
            'decision_confidence': decision['decision_confidence'],
            'decision_reasoning': decision['decision_reasoning'],
            
            # Avaliação de risco
            'risk_score': decision['risk_score'],
            'stop_loss_suggested': decision.get('stop_loss_suggested'),
            'take_profit_suggested': decision.get('take_profit_suggested'),
            'trailing_stop_price': decision.get('trailing_stop_price'),
            
            # Para treinamento RL (preenchido depois)
            'reward_calculated': None,
            'outcome_label': None
        }
        
        return snapshot
    
    def monitor_cycle(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executa um ciclo completo de monitoramento.
        
        Args:
            symbol: Símbolo específico (opcional)
            
        Returns:
            Lista de snapshots gerados
        """
        logger.info("="*60)
        logger.info(f"INICIANDO CICLO DE MONITORAMENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        snapshots = []
        
        # 1. Buscar posições abertas
        positions = self.fetch_open_positions(symbol)
        
        if not positions:
            logger.info("Nenhuma posição aberta encontrada")
            return snapshots
        
        logger.info(f"Encontradas {len(positions)} posição(ões) aberta(s)")
        
        # 2. Para cada posição, fazer avaliação completa
        for position in positions:
            try:
                pos_symbol = position['symbol']
                logger.info(f"\n--- Analisando {pos_symbol} {position['direction']} ---")
                
                # a. Buscar dados de mercado
                market_data = self.fetch_current_market_data(pos_symbol)
                
                # b. Calcular indicadores
                indicators = self.calculate_indicators_snapshot(pos_symbol, market_data)
                
                # c. Avaliar posição e gerar decisão
                sentiment = market_data.get('sentiment', {})
                decision = self.evaluate_position(position, indicators, sentiment)
                
                # d. Criar snapshot completo
                snapshot = self.create_snapshot(position, indicators, sentiment, decision)
                
                # e. Persistir no banco
                snapshot_id = self.db.insert_position_snapshot(snapshot)
                snapshot['id'] = snapshot_id
                
                # f. Verificar alertas de risco
                risk_score = decision['risk_score']
                if risk_score >= 8:
                    self.alert_manager.alert_system_error(
                        f"PositionRisk-{pos_symbol}",
                        f"Risk score alto: {risk_score:.1f}/10 - Ação: {decision['agent_action']}"
                    )
                
                # Verificar funding extremo
                funding_rate = indicators.get('funding_rate', 0)
                if funding_rate and abs(funding_rate) > 0.05:
                    self.alert_manager.alert_funding_extreme(pos_symbol, funding_rate)
                
                # g. Log da decisão
                AgentLogger.log_decision(logger, {
                    'symbol': pos_symbol,
                    'direction': position['direction'],
                    'action': decision['agent_action'],
                    'confidence': decision['decision_confidence'],
                    'risk_score': risk_score,
                    'pnl_pct': position['unrealized_pnl_pct']
                })
                
                snapshots.append(snapshot)
                
            except Exception as e:
                logger.error(f"Erro ao processar posição {position.get('symbol')}: {e}")
        
        logger.info(f"\nCiclo completo. {len(snapshots)} snapshot(s) criado(s).")
        return snapshots
    
    def run_continuous(self, symbol: Optional[str] = None, interval_seconds: int = 300):
        """
        Loop contínuo que roda monitor_cycle a cada interval_seconds.
        
        Args:
            symbol: Símbolo específico (opcional)
            interval_seconds: Intervalo entre ciclos em segundos (default: 300 = 5 min)
        """
        self._running = True
        
        # Handler para graceful shutdown
        def signal_handler(sig, frame):
            logger.info("\nSinal de interrupção recebido. Finalizando...")
            self._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info(f"Monitor contínuo iniciado (intervalo: {interval_seconds}s)")
        logger.info("Pressione Ctrl+C para parar")
        
        cycle_count = 0
        
        while self._running:
            try:
                cycle_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"CICLO #{cycle_count}")
                logger.info(f"{'='*60}")
                
                # Executar ciclo de monitoramento
                snapshots = self.monitor_cycle(symbol)
                
                # Resumo do ciclo
                if snapshots:
                    logger.info(f"\n[RESUMO] CICLO #{cycle_count}:")
                    for snap in snapshots:
                        logger.info(f"  • {snap['symbol']} {snap['direction']}: "
                                   f"{snap['agent_action']} (risco: {snap['risk_score']:.1f}/10, "
                                   f"PnL: {snap['unrealized_pnl_pct']:.2f}%)")
                else:
                    logger.info(f"\n[OK] Ciclo #{cycle_count} completo - Nenhuma posição aberta")
                
                # Aguardar próximo ciclo
                if self._running:
                    logger.info(f"\n[AGUARDANDO] Próximo ciclo em {interval_seconds}s...")
                    # Countdown ativo com progresso a cada 30 segundos
                    elapsed = 0
                    while elapsed < interval_seconds and self._running:
                        remaining = interval_seconds - elapsed
                        if remaining > 30:
                            time.sleep(30)
                            elapsed += 30
                            remaining = interval_seconds - elapsed
                            logger.info(f"  Aguardando... {remaining}s restantes")
                        else:
                            time.sleep(remaining)
                            elapsed = interval_seconds
                    
            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}")
                if self._running:
                    logger.info(f"Aguardando {interval_seconds}s antes de tentar novamente...")
                    # Countdown ativo mesmo em caso de erro
                    elapsed = 0
                    while elapsed < interval_seconds and self._running:
                        remaining = interval_seconds - elapsed
                        if remaining > 30:
                            time.sleep(30)
                            elapsed += 30
                            remaining = interval_seconds - elapsed
                            logger.info(f"  Aguardando... {remaining}s restantes")
                        else:
                            time.sleep(remaining)
                            elapsed = interval_seconds
        
        logger.info("Monitor finalizado com sucesso")
    
    def update_past_outcomes(self, symbol: str, exit_price: float, exit_timestamp: int):
        """
        Atualiza outcomes retroativamente quando uma posição é fechada.
        
        Args:
            symbol: Símbolo da posição fechada
            exit_price: Preço de saída
            exit_timestamp: Timestamp da saída
        """
        try:
            # Buscar snapshots pendentes (sem outcome) desta posição
            snapshots = self.db.get_position_snapshots(symbol)
            
            for snapshot in snapshots:
                if snapshot['outcome_label'] is not None:
                    continue  # Já processado
                
                # Calcular se a decisão foi boa
                mark_price = snapshot['mark_price']
                direction = snapshot['direction']
                action = snapshot['agent_action']
                
                # Calcular movimento de preço após a decisão
                price_change_pct = ((exit_price - mark_price) / mark_price) * 100
                
                if direction == 'LONG':
                    price_pnl = price_change_pct
                else:  # SHORT
                    price_pnl = -price_change_pct
                
                # Determinar outcome
                if action == 'CLOSE':
                    # Se fechou, reward baseado em PnL no momento
                    reward = snapshot['unrealized_pnl_pct'] / 10  # Normalizar
                    if snapshot['unrealized_pnl_pct'] > 0:
                        outcome = 'win'
                    else:
                        outcome = 'loss'
                
                elif action == 'REDUCE_50':
                    # Se reduziu, reward positivo se protegeu de perda
                    if price_pnl < 0:
                        reward = abs(price_pnl) / 10  # Protegeu bem
                        outcome = 'win'
                    else:
                        reward = -abs(price_pnl) / 10  # Saiu cedo demais
                        outcome = 'loss'
                
                else:  # HOLD
                    # Se segurou, reward baseado no resultado final
                    reward = price_pnl / 10
                    if price_pnl > 0:
                        outcome = 'win'
                    else:
                        outcome = 'loss'
                
                # Atualizar no banco
                self.db.update_snapshot_outcome(snapshot['id'], reward, outcome)
                
            logger.info(f"Outcomes atualizados para {symbol} - {len(snapshots)} snapshot(s)")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar outcomes para {symbol}: {e}")
