"""
Monitor de posições abertas na Binance Futures em tempo real.
Coleta dados, calcula indicadores, gera decisões e persiste tudo para aprendizado futuro.
"""

import time
import signal
import logging
import json
import traceback
import threading
import math
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

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
from config.settings import (
    MONITOR_MIN_CANDLES_H4,
    MONITOR_MIN_CANDLES_H1,
    MONITOR_FRESH_CANDLES
)

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Prioridades das ações para evitar downgrade de decisões críticas
ACTION_PRIORITY = {
    'HOLD': 0,
    'REDUCE_50': 1,
    'CLOSE': 2
}

# Threshold de PnL para considerar posição muito lucrativa
# Usado para ajuste de risk_score quando saldo da conta está indisponível
VERY_PROFITABLE_PNL_THRESHOLD = 10.0  # 10% PnL


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
        self._protection_bootstrap_done = set()
        self._last_market_structure_by_symbol: Dict[str, str] = {}
        self._symbol_price_precision_cache: Dict[str, Dict[str, Any]] = {}
        self._learning_profile_cache: Dict[str, Any] = {
            'timestamp': None,
            'profiles': {},
            'global': {
                'dominant_symbol': None,
                'dominant_share': 0.0,
                'total_labeled': 0,
            }
        }

        # Inicializar OrderExecutor para execução automática de ordens
        from execution.order_executor import OrderExecutor
        self.order_executor = OrderExecutor(client, db, mode=mode)

        logger.info(f"PositionMonitor inicializado em modo {mode}")


    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK e converte SDK objects em dicts.

        O SDK Binance retorna objetos com atributos snake_case mas o código pode
        esperar dicts com método .get() e chaves camelCase.

        Esta função:
        1. Extrai .data do ApiResponse wrapper
        2. Converte SDK objects em dicts Python
        3. Mapeia atributos snake_case → camelCase para compatibilidade
        4. Trata listas de SDK objects recursivamente
        """
        if response is None:
            return None

        # Passo 1: ApiResponse tem um atributo .data contendo o payload real
        if hasattr(response, 'data'):
            data = response.data
            # .data pode ser um método que precisa ser chamado
            if callable(data):
                data = data()
        else:
            # Se não tem .data, assumir que já são os dados diretos
            data = response

        # Passo 2: Converter SDK objects para dicts
        return self._convert_sdk_object_to_dict(data)

    def _convert_sdk_object_to_dict(self, obj):
        """
        Converte objetos SDK da Binance em dicts Python com mapeamento snake_case → camelCase.

        Args:
            obj: Pode ser None, dict, list, ou SDK object com atributos

        Returns:
            Dict, list de dicts, ou valor primitivo
        """
        if obj is None:
            return None

        # Se já é dict ou tipo primitivo, retornar como está
        if isinstance(obj, (dict, str, int, float, bool, bytes, type(None))):
            return obj

        # Se é lista, processar cada elemento recursivamente
        if isinstance(obj, list):
            return [self._convert_sdk_object_to_dict(item) for item in obj]

        # Se é um SDK object (tem __dict__ mas não é dict), converter para dict
        if hasattr(obj, '__dict__'):
            # Extrair atributos, filtrando os privados (começam com _)
            raw_dict = {
                key: value for key, value in vars(obj).items()
                if not key.startswith('_')
            }

            # Converter valores aninhados recursivamente
            converted_dict = {
                key: self._convert_sdk_object_to_dict(value)
                for key, value in raw_dict.items()
            }

            # Mapear snake_case → camelCase para compatibilidade com código existente
            camel_dict = self._map_to_camel_case(converted_dict)

            # Log para debug
            if converted_dict:  # Só logar se não for vazio
                logger.debug(f"[POSITION] SDK object convertido para dict: {type(obj).__name__} → {len(camel_dict)} campos")

            return camel_dict

        # Fallback: retornar o objeto como está
        return obj

    def _map_to_camel_case(self, data: dict) -> dict:
        """
        Mapeia chaves snake_case para camelCase mantendo ambas as versões.

        Mantemos tanto snake_case quanto camelCase para máxima compatibilidade.

        Args:
            data: Dict com chaves em snake_case

        Returns:
            Dict com chaves adicionais em camelCase
        """
        # Mapeamento explícito dos campos comuns da API Binance (position info)
        snake_to_camel = {
            'position_amt': 'positionAmt',
            'entry_price': 'entryPrice',
            'mark_price': 'markPrice',
            'unrealized_profit': 'unrealizedProfit',
            'liquidation_price': 'liquidationPrice',
            'isolated_wallet': 'isolatedWallet',
            'position_side': 'positionSide',
            'max_notional_value': 'maxNotionalValue',
            'update_time': 'updateTime',
            'notional': 'notional',
            'isolated_margin': 'isolatedMargin',
            'is_auto_add_margin': 'isAutoAddMargin',
            'margin_type': 'marginType',
            'break_even_price': 'breakEvenPrice',
        }

        result = dict(data)  # Cópia para não modificar original

        # Adicionar versões camelCase das chaves snake_case
        for snake_key, camel_key in snake_to_camel.items():
            if snake_key in result and camel_key not in result:
                result[camel_key] = result[snake_key]

        return result

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

    def fetch_open_positions(self, symbol: Optional[str] = None, log_each_position: bool = True) -> List[Dict[str, Any]]:
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
                if log_each_position:
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
        Combina dados históricos do banco com candles frescos da API.

        Args:
            symbol: Símbolo a buscar

        Returns:
            Dict com DataFrames de OHLCV e dados de sentimento
        """
        try:
            # Buscar dados históricos do banco + candles frescos da API
            df_h1 = self._fetch_combined_klines(symbol, "1h", MONITOR_MIN_CANDLES_H1)
            df_h4 = self._fetch_combined_klines(symbol, "4h", MONITOR_MIN_CANDLES_H4)

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

    def _fetch_combined_klines(self, symbol: str, timeframe: str, min_candles: int) -> pd.DataFrame:
        """
        Busca candles combinando dados históricos do banco com dados frescos da API.

        Args:
            symbol: Símbolo a buscar
            timeframe: Timeframe ("1h", "4h")
            min_candles: Número mínimo de candles necessários

        Returns:
            DataFrame com candles históricos + frescos, sem duplicatas
        """
        # Mapeamento de timeframe API para formato do banco
        TIMEFRAME_MAPPING = {
            '1h': 'H1',
            '4h': 'H4',
            '1d': 'D1'
        }

        try:
            # 1. Buscar dados históricos do banco
            # Converter timeframe para formato do banco: "1h" -> "H1", "4h" -> "H4"
            timeframe_db = TIMEFRAME_MAPPING.get(timeframe.lower())
            if not timeframe_db:
                raise ValueError(f"Timeframe não suportado: {timeframe}. Use '1h', '4h' ou '1d'")

            db_records = self.db.get_ohlcv(
                timeframe=timeframe_db,
                symbol=symbol,
                limit=min_candles
            )

            # Converter para DataFrame
            if db_records:
                df_historical = pd.DataFrame(db_records)
                logger.debug(f"Banco: {len(df_historical)} candles {timeframe} para {symbol}")
            else:
                df_historical = pd.DataFrame()
                logger.debug(f"Banco vazio para {symbol} {timeframe}")

            # 2. Buscar candles frescos da API
            # Se o banco tem dados suficientes, buscar apenas alguns candles frescos
            # Caso contrário, buscar com limit maior
            if len(df_historical) >= min_candles:
                fetch_limit = MONITOR_FRESH_CANDLES
            else:
                # Fallback: banco vazio ou insuficiente, buscar mais da API
                fetch_limit = min_candles
                logger.info(
                    f"Banco tem apenas {len(df_historical)} candles {timeframe} para {symbol}. "
                    f"Buscando {fetch_limit} da API."
                )

            df_fresh = self.collector.fetch_klines(symbol, timeframe, limit=fetch_limit)
            logger.debug(f"API: {len(df_fresh)} candles {timeframe} para {symbol}")

            # 3. Inserir candles frescos no banco para manter histórico atualizado
            # Nota: db.insert_ohlcv usa INSERT OR REPLACE, portanto duplicatas são tratadas automaticamente
            if not df_fresh.empty:
                self.db.insert_ohlcv(timeframe=timeframe_db, data=df_fresh)

            # 4. Combinar dados históricos com frescos
            if df_historical.empty:
                # Sem dados históricos, usar apenas frescos
                df_combined = df_fresh
            elif df_fresh.empty:
                # Sem dados frescos (erro na API?), usar apenas históricos
                df_combined = df_historical
            else:
                # Concatenar e remover duplicatas por timestamp
                df_combined = pd.concat([df_historical, df_fresh], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)

            logger.info(
                f"Dados combinados: {len(df_combined)} candles {timeframe} para {symbol} "
                f"(mínimo necessário: {min_candles})"
            )

            # 5. Validar se temos candles suficientes
            if len(df_combined) < min_candles:
                logger.warning(
                    f"AVISO: Apenas {len(df_combined)} candles {timeframe} disponíveis para {symbol}. "
                    f"Mínimo recomendado: {min_candles}"
                )

            return df_combined

        except Exception as e:
            logger.error(f"Erro ao buscar candles combinados {timeframe} para {symbol}: {e}")
            # Fallback: tentar apenas da API
            try:
                return self.collector.fetch_klines(symbol, timeframe, limit=min_candles)
            except Exception as fallback_error:
                logger.error(f"Erro no fallback para {symbol} {timeframe}: {fallback_error}")
                return pd.DataFrame()

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

    @staticmethod
    def _is_market_structure_adverse(direction: str, market_structure: str) -> bool:
        """
        Verifica se a estrutura de mercado SMC é adversa para a direção da posição.

        Args:
            direction: 'LONG' ou 'SHORT'
            market_structure: 'bullish', 'bearish' ou 'range'

        Returns:
            True se a estrutura é adversa (bearish para LONG ou bullish para SHORT)
        """
        if direction == 'LONG':
            return market_structure == 'bearish'
        else:  # SHORT
            return market_structure == 'bullish'

    @staticmethod
    def _is_market_structure_favorable(direction: str, market_structure: str) -> bool:
        """
        Verifica se a estrutura de mercado SMC é favorável para a direção da posição.

        Args:
            direction: 'LONG' ou 'SHORT'
            market_structure: 'bullish', 'bearish' ou 'range'

        Returns:
            True se a estrutura é favorável (bullish para LONG ou bearish para SHORT)
        """
        if direction == 'LONG':
            return market_structure == 'bullish'
        else:  # SHORT
            return market_structure == 'bearish'

    @staticmethod
    def _interpret_rsi(direction: str, rsi: float, mark_price: float, ema_72: float) -> Dict[str, Any]:
        """
        Interpreta o RSI e posição do preço contextualizado pela direção da posição.

        Args:
            direction: 'LONG' ou 'SHORT'
            rsi: Valor do RSI (0-100)
            mark_price: Preço atual de mercado
            ema_72: Valor da EMA 72

        Returns:
            Dict com 'is_reversal_signal' (bool), 'is_favorable' (bool), 'message' (str)
        """
        result = {
            'is_reversal_signal': False,
            'is_favorable': False,
            'message': ''
        }

        if direction == 'LONG':
            # LONG: sinal de reversão se RSI < 30 OU preço abaixo da EMA72
            if rsi < 30 or mark_price < ema_72:
                result['is_reversal_signal'] = True
                result['message'] = f"LONG em zona de risco (RSI: {rsi:.1f}, mark_price {mark_price:.4f} vs EMA72 {ema_72:.4f})"
            # LONG favorável: RSI > 50, preço acima EMAs
            elif rsi > 50 and mark_price > ema_72:
                result['is_favorable'] = True
                result['message'] = f"LONG em estrutura favorável (RSI: {rsi:.1f}, preço acima EMAs)"
        else:  # SHORT
            # SHORT: sinal de reversão se RSI > 70 OU preço acima da EMA72
            if rsi > 70 or mark_price > ema_72:
                result['is_reversal_signal'] = True
                result['message'] = f"SHORT em zona de risco (RSI: {rsi:.1f}, mark_price {mark_price:.4f} vs EMA72 {ema_72:.4f})"
            # SHORT favorável: RSI < 50, preço abaixo EMAs
            elif rsi < 50 and mark_price < ema_72:
                result['is_favorable'] = True
                result['message'] = f"SHORT em estrutura favorável (RSI: {rsi:.1f}, preço abaixo EMAs)"

        return result

    @staticmethod
    def _interpret_ema_alignment(direction: str, ema_17: float, ema_34: float,
                                ema_72: float, ema_144: float) -> Dict[str, Any]:
        """
        Interpreta o alinhamento das EMAs contextualizado pela direção da posição.

        Args:
            direction: 'LONG' ou 'SHORT'
            ema_17, ema_34, ema_72, ema_144: Valores das EMAs

        Returns:
            Dict com 'is_favorable' (bool), 'is_adverse' (bool), 'message' (str), 'risk_adjustment' (float)
        """
        result = {
            'is_favorable': False,
            'is_adverse': False,
            'message': '',
            'risk_adjustment': 0.0
        }

        if direction == 'LONG':
            if ema_17 > ema_34 > ema_72 > ema_144:
                result['is_favorable'] = True
                result['message'] = "EMAs alinhadas para alta - tendencia bullish confirmada"
                result['risk_adjustment'] = -0.5
            elif ema_17 < ema_34 < ema_72 < ema_144:
                result['is_adverse'] = True
                result['message'] = "[AVISO] EMAs alinhadas para baixa - contra posição LONG"
                result['risk_adjustment'] = 1.0
        else:  # SHORT
            if ema_17 < ema_34 < ema_72 < ema_144:
                result['is_favorable'] = True
                result['message'] = "EMAs alinhadas para baixa - tendencia bearish confirmada"
                result['risk_adjustment'] = -0.5
            elif ema_17 > ema_34 > ema_72 > ema_144:
                result['is_adverse'] = True
                result['message'] = "[AVISO] EMAs alinhadas para alta - contra posição SHORT"
                result['risk_adjustment'] = 1.0

        return result

    @staticmethod
    def _is_funding_rate_adverse(direction: str, funding_rate: float, threshold: float) -> bool:
        """
        Verifica se o funding rate é adverso para a direção da posição.

        Args:
            direction: 'LONG' ou 'SHORT'
            funding_rate: Taxa de funding em decimal (ex: 0.0001 = 0.01%)
            threshold: Threshold de funding considerado extremo (em % como 0.05 = 0.05%)

        Returns:
            True se funding é adverso (alto positivo para LONG ou alto negativo para SHORT)
        """
        # Converter funding_rate para percentual (0.0001 -> 0.01)
        funding_pct = funding_rate * 100

        if direction == 'LONG':
            # Funding muito positivo = muitos LONGs (ruim para LONG)
            # Comparar funding_pct com threshold (ambos em %)
            return funding_pct > threshold
        else:  # SHORT
            # Funding muito negativo = muitos SHORTs (ruim para SHORT)
            return funding_pct < -threshold

    @staticmethod
    def _calculate_suggested_stops(direction: str, entry_price: float, mark_price: float,
                                  atr: float, stop_multiplier: float, tp_multiplier: float,
                                  nearest_ob_dist: Optional[float] = None,
                                  liquidity_above_pct: Optional[float] = None,
                                  liquidity_below_pct: Optional[float] = None) -> Dict[str, Optional[float]]:
        """
        Calcula stop loss e take profit sugeridos baseado em ATR e níveis SMC.

        Args:
            direction: 'LONG' ou 'SHORT'
            entry_price: Preço de entrada da posição
            mark_price: Preço atual de mercado
            atr: Average True Range
            stop_multiplier: Multiplicador de ATR para stop loss
            tp_multiplier: Multiplicador de ATR para take profit
            nearest_ob_dist: Distância percentual até o Order Block mais próximo (opcional)
            liquidity_above_pct: Distância percentual até liquidez acima (BSL) (opcional)
            liquidity_below_pct: Distância percentual até liquidez abaixo (SSL) (opcional)

        Returns:
            Dict com stop/tp e fonte do cálculo
        """
        result = {
            'stop_loss': None,
            'take_profit': None,
            'stop_source': 'ATR',
            'tp_source': 'ATR'
        }

        if direction == 'LONG':
            # Para LONG: stop abaixo do nearest OB ou swing low
            atr_stop = entry_price - (atr * stop_multiplier)

            # Se temos OB próximo, usar ele com um buffer de ATR
            if nearest_ob_dist is not None:
                ob_price = mark_price * (1 - nearest_ob_dist / 100)
                # Stop abaixo do OB com buffer de 0.5 ATR
                smc_stop = ob_price - (atr * 0.5)
                # Usar o stop mais conservador (mais próximo do preço atual para limitar perda)
                result['stop_loss'] = max(smc_stop, atr_stop)
                result['stop_source'] = 'SMC_OB+ATR'
            else:
                result['stop_loss'] = atr_stop

            atr_tp = entry_price + (atr * tp_multiplier)
            liq_tp = None
            if liquidity_above_pct is not None and liquidity_above_pct > 0:
                liq_tp = mark_price * (1 + liquidity_above_pct / 100)

            # Para LONG, usar alvo válido mais próximo acima da entrada.
            tp_candidates = [tp for tp in [atr_tp, liq_tp] if tp is not None and tp > entry_price]
            if tp_candidates:
                result['take_profit'] = min(tp_candidates)
                if liq_tp is not None and result['take_profit'] == liq_tp:
                    result['tp_source'] = 'SMC_LIQUIDITY_BSL'
            else:
                result['take_profit'] = atr_tp
        else:  # SHORT
            # Para SHORT: stop acima do nearest OB ou swing high
            atr_stop = entry_price + (atr * stop_multiplier)

            # Se temos OB próximo, usar ele com um buffer de ATR
            if nearest_ob_dist is not None:
                ob_price = mark_price * (1 + nearest_ob_dist / 100)
                # Stop acima do OB com buffer de 0.5 ATR
                smc_stop = ob_price + (atr * 0.5)
                # Usar o stop mais conservador (mais próximo do preço atual)
                result['stop_loss'] = min(smc_stop, atr_stop)
                result['stop_source'] = 'SMC_OB+ATR'
            else:
                result['stop_loss'] = atr_stop

            atr_tp = entry_price - (atr * tp_multiplier)
            liq_tp = None
            if liquidity_below_pct is not None and liquidity_below_pct > 0:
                liq_tp = mark_price * (1 - liquidity_below_pct / 100)

            # Para SHORT, usar alvo válido mais próximo abaixo da entrada.
            tp_candidates = [tp for tp in [atr_tp, liq_tp] if tp is not None and tp < entry_price]
            if tp_candidates:
                result['take_profit'] = max(tp_candidates)
                if liq_tp is not None and result['take_profit'] == liq_tp:
                    result['tp_source'] = 'SMC_LIQUIDITY_SSL'
            else:
                result['take_profit'] = atr_tp

        return result

    def _get_learning_profiles_24h(self) -> Dict[str, Any]:
        """Consolida outcomes das últimas 24h por símbolo para ajuste adaptativo de risco."""
        cache_ttl_seconds = int(RISK_PARAMS.get('learning_profile_cache_ttl_seconds', 300))
        cached_ts = self._learning_profile_cache.get('timestamp')
        now_dt = datetime.utcnow()

        if cached_ts and (now_dt - cached_ts).total_seconds() <= cache_ttl_seconds:
            return self._learning_profile_cache

        lookback_hours = int(RISK_PARAMS.get('learning_profile_lookback_hours', 24))
        min_samples = int(RISK_PARAMS.get('learning_profile_min_samples', 5))
        adverse_loss_rate = float(RISK_PARAMS.get('learning_profile_adverse_loss_rate', 0.60))
        adverse_reward = float(RISK_PARAMS.get('learning_profile_adverse_avg_reward_threshold', -1.0))

        dominant_share_threshold = float(RISK_PARAMS.get('learning_profile_dominant_share_threshold', 0.70))
        dominant_min_samples = int(RISK_PARAMS.get('learning_profile_dominant_min_samples', 20))

        start_ms = int((now_dt - timedelta(hours=lookback_hours)).timestamp() * 1000)
        query = """
            SELECT
                symbol,
                COUNT(*) AS total,
                SUM(CASE WHEN outcome_label = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN outcome_label = 'loss' THEN 1 ELSE 0 END) AS losses,
                AVG(reward_calculated) AS avg_reward
            FROM position_snapshots
            WHERE timestamp >= ? AND outcome_label IS NOT NULL
            GROUP BY symbol
            ORDER BY total DESC
        """

        profiles: Dict[str, Dict[str, Any]] = {}
        total_labeled = 0
        dominant_symbol = None
        dominant_count = 0

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (start_ms,))
                rows = cursor.fetchall()

            for row in rows:
                symbol = str(row['symbol']).upper()
                total = int(row['total'] or 0)
                wins = int(row['wins'] or 0)
                losses = int(row['losses'] or 0)
                avg_reward = float(row['avg_reward'] or 0.0)
                win_rate = (wins / total) if total > 0 else 0.0
                loss_rate = (losses / total) if total > 0 else 0.0

                is_adverse = (
                    total >= min_samples
                    and (loss_rate >= adverse_loss_rate or avg_reward <= adverse_reward)
                )

                profiles[symbol] = {
                    'symbol': symbol,
                    'samples': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'loss_rate': loss_rate,
                    'avg_reward': avg_reward,
                    'is_adverse': is_adverse,
                    'is_dominant_positive': False,
                }

                total_labeled += total
                if total > dominant_count:
                    dominant_count = total
                    dominant_symbol = symbol

        except Exception as e:
            logger.debug(f"Falha ao calcular perfil de aprendizado 24h: {e}")

        dominant_share = (dominant_count / total_labeled) if total_labeled > 0 else 0.0
        if (
            dominant_symbol
            and dominant_symbol in profiles
            and dominant_share >= dominant_share_threshold
            and profiles[dominant_symbol]['samples'] >= dominant_min_samples
            and profiles[dominant_symbol]['avg_reward'] > 0
        ):
            profiles[dominant_symbol]['is_dominant_positive'] = True

        self._learning_profile_cache = {
            'timestamp': now_dt,
            'profiles': profiles,
            'global': {
                'dominant_symbol': dominant_symbol,
                'dominant_share': dominant_share,
                'total_labeled': total_labeled,
            }
        }
        return self._learning_profile_cache

    def _apply_learning_adaptive_controls(
        self,
        position: Dict[str, Any],
        decision: Dict[str, Any],
        risk_score: float,
        reasoning: List[str],
    ) -> float:
        """Aplica ajuste de risco/ação com base no aprendizado recente por símbolo."""
        symbol = str(position.get('symbol', '')).upper()
        pnl_pct = float(position.get('unrealized_pnl_pct', 0.0) or 0.0)

        learning_data = self._get_learning_profiles_24h()
        profile = learning_data.get('profiles', {}).get(symbol)
        global_data = learning_data.get('global', {})

        if not profile:
            return risk_score

        if profile.get('is_adverse'):
            risk_score += 1.2
            reasoning.append(
                f"[LEARNING] {symbol} com padrão adverso recente "
                f"(loss_rate={profile['loss_rate']*100:.1f}%, avg_reward={profile['avg_reward']:.2f})"
            )
            if decision['agent_action'] == 'HOLD':
                if pnl_pct <= 0:
                    self._update_action_if_higher_priority(
                        decision, 'CLOSE', 0.88, reasoning,
                        f"Desalavancagem: {symbol} adverso + posição em prejuízo"
                    )
                else:
                    self._update_action_if_higher_priority(
                        decision, 'REDUCE_50', 0.78, reasoning,
                        f"Redução preventiva: {symbol} adverso apesar de PnL positivo"
                    )
            elif decision['agent_action'] == 'REDUCE_50' and pnl_pct <= 0:
                self._update_action_if_higher_priority(
                    decision, 'CLOSE', 0.90, reasoning,
                    f"Escalonamento para CLOSE em {symbol} devido a histórico adverso"
                )

        if profile.get('is_dominant_positive'):
            dominant_share = float(global_data.get('dominant_share', 0.0) or 0.0)
            risk_score += 0.8
            reasoning.append(
                f"[LEARNING] Concentração elevada de aprendizado em {symbol} "
                f"({dominant_share*100:.1f}% dos outcomes 24h)"
            )
            if decision['agent_action'] == 'HOLD' and pnl_pct > 0:
                self._update_action_if_higher_priority(
                    decision, 'REDUCE_50', 0.72, reasoning,
                    f"Desconcentração tática de exposição em {symbol}"
                )

        return risk_score

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
                if pnl_pct > VERY_PROFITABLE_PNL_THRESHOLD:
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

        # 3. VERIFICAR ESTRUTURA SMC
        market_structure = indicators.get('market_structure', 'range')
        choch_recent = indicators.get('choch_recent', 0)
        bos_recent = indicators.get('bos_recent', 0)

        # Regra mandatória: se a direção de mercado inverter contra a posição,
        # fechar 100% sem exceções. Abertura na nova direção fica a cargo do
        # fluxo de oportunidades (camada de entrada).
        if self._is_market_structure_adverse(direction, market_structure):
            self._update_action_if_higher_priority(
                decision, 'CLOSE', 0.92, reasoning,
                f"Mudança de direção detectada ({market_structure}) contra posição {direction} - CLOSE 100% obrigatório"
            )
            risk_score += 2.5

        # Verificar se estrutura SMC favorece a posição usando helper
        if self._is_market_structure_favorable(direction, market_structure):
            if bos_recent:
                reasoning.append(f"Estrutura {market_structure} com BOS confirmado - favoravel para {direction}")
                risk_score -= 0.5
            else:
                reasoning.append(f"Estrutura de mercado {market_structure} - alinhada com {direction}")
                risk_score -= 0.3
        elif self._is_market_structure_adverse(direction, market_structure):
            reasoning.append(f"[AVISO] Estrutura {market_structure} contra posicao {direction}")
            risk_score += 1.0

        # Verificar CHoCH (mudança de caráter - sinal de reversão)
        if choch_recent and self._is_market_structure_adverse(direction, market_structure):
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
        ema_34 = indicators.get('ema_34')
        ema_72 = indicators.get('ema_72')
        ema_144 = indicators.get('ema_144')

        # Verificar alinhamento de EMAs usando helper
        if all(v is not None for v in [ema_17, ema_34, ema_72, ema_144]):
            ema_interpretation = self._interpret_ema_alignment(direction, ema_17, ema_34, ema_72, ema_144)
            if ema_interpretation['message']:
                reasoning.append(ema_interpretation['message'])
                risk_score += ema_interpretation['risk_adjustment']

        # Verificar RSI e posição do preço usando helper
        if rsi and ema_17 and ema_72:
            rsi_interpretation = self._interpret_rsi(direction, rsi, mark_price, ema_72)

            if rsi_interpretation['is_reversal_signal']:
                if pnl_pct > 5:
                    # Lucro bom, reduzir para garantir
                    self._update_action_if_higher_priority(
                        decision, 'REDUCE_50', 0.70, reasoning,
                        rsi_interpretation['message']
                    )
                    risk_score += 1.5
                elif pnl_pct < 0:
                    self._update_action_if_higher_priority(
                        decision, 'CLOSE', 0.80, reasoning,
                        f"{direction} em prejuízo e indicadores negativos (RSI: {rsi:.1f})"
                    )
                    risk_score += 2.5
            elif rsi_interpretation['is_favorable']:
                # Verificar também se está acima/abaixo da EMA17 conforme direção
                if (direction == 'LONG' and mark_price > ema_17) or \
                   (direction == 'SHORT' and mark_price < ema_17):
                    reasoning.append(rsi_interpretation['message'])
                    risk_score -= 1.0

        # 5. VERIFICAR FUNDING RATE EXTREMO usando helper
        funding_rate = indicators.get('funding_rate', 0)
        funding_threshold = RISK_PARAMS.get('extreme_funding_rate_threshold', 0.05)

        if funding_rate and self._is_funding_rate_adverse(direction, funding_rate, funding_threshold):
            funding_pct = funding_rate * 100
            self._update_action_if_higher_priority(
                decision, 'REDUCE_50', 0.65, reasoning,
                f"Funding rate extremo contra {direction} ({funding_pct:.4f}%)"
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

        # 7.1 Ajustes adaptativos com base em outcomes recentes por ativo
        risk_score = self._apply_learning_adaptive_controls(
            position=position,
            decision=decision,
            risk_score=risk_score,
            reasoning=reasoning,
        )
        risk_score = max(0.0, min(10.0, risk_score))

        # Aplicar multiplicador de risco para cross margin
        if margin_type == 'CROSS':
            cross_margin_multiplier = RISK_PARAMS.get('cross_margin_risk_multiplier', 1.5)
            risk_score = min(10.0, risk_score * cross_margin_multiplier)
            logger.debug(f"Risk score ajustado para cross margin: {risk_score:.2f}")

        decision['risk_score'] = risk_score
        decision['decision_reasoning'] = json.dumps(reasoning)

        # 8. CALCULAR STOPS E TARGETS SUGERIDOS
        # Usar níveis SMC quando disponíveis, caso contrário usar ATR
        nearest_ob_dist = indicators.get('nearest_ob_distance_pct')

        if atr:
            # Calcular stops e targets usando helper
            stop_multiplier = RISK_PARAMS['stop_loss_atr_multiplier']
            tp_multiplier = RISK_PARAMS['take_profit_atr_multiplier']
            liquidity_above_pct = indicators.get('liquidity_above_pct')
            liquidity_below_pct = indicators.get('liquidity_below_pct')

            stops = self._calculate_suggested_stops(
                direction, entry_price, mark_price, atr,
                stop_multiplier, tp_multiplier, nearest_ob_dist,
                liquidity_above_pct=liquidity_above_pct,
                liquidity_below_pct=liquidity_below_pct
            )

            decision['stop_loss_suggested'] = stops['stop_loss']
            decision['take_profit_suggested'] = stops['take_profit']
            decision['stop_loss_source'] = stops.get('stop_source')
            decision['take_profit_source'] = stops.get('tp_source')

            reasoning.append(
                f"TP/SL calculado com técnico+SMC (SL: {stops.get('stop_source', 'ATR')}, "
                f"TP: {stops.get('tp_source', 'ATR')})"
            )
            decision['decision_reasoning'] = json.dumps(reasoning)

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

    def _format_rsi_interpretation(self, rsi: float) -> str:
        """Interpreta valor do RSI."""
        if rsi < 30:
            return "Sobrevendido"
        elif rsi < 45:
            return "Fraco"
        elif rsi < 55:
            return "Neutro"
        elif rsi < 70:
            return "Moderado"
        else:
            return "Sobrecomprado"

    def _format_macd_interpretation(self, histogram: float) -> str:
        """Interpreta MACD histogram."""
        if histogram is None:
            return "N/D"
        return "Bullish" if histogram > 0 else "Bearish"

    def _format_adx_interpretation(self, adx: float, di_plus: float, di_minus: float) -> str:
        """Interpreta ADX e direção da tendência."""
        if adx is None:
            return "N/D"

        # Força da tendência
        if adx < 20:
            strength = "Sem Tendencia"
        elif adx < 25:
            strength = "Tendencia Fraca"
        elif adx < 40:
            strength = "Tendencia Moderada"
        else:
            strength = "Tendencia Forte"

        # Direção da tendência
        direction = ""
        if di_plus is not None and di_minus is not None:
            if di_plus > di_minus:
                direction = " - Bullish"
            else:
                direction = " - Bearish"

        return f"{strength}{direction}"

    def _format_bb_interpretation(self, percent_b: float) -> str:
        """Interpreta posição nas Bollinger Bands."""
        if percent_b is None:
            return "N/D"

        if percent_b > 0.8:
            return "Zona Superior"
        elif percent_b > 0.5:
            return "Acima da Media"
        elif percent_b > 0.2:
            return "Abaixo da Media"
        else:
            return "Zona Inferior"

    def _check_ema_alignment(self, ema_17: float, ema_34: float, ema_72: float, ema_144: float) -> str:
        """Verifica alinhamento das EMAs."""
        if None in [ema_17, ema_34, ema_72, ema_144]:
            return "N/D"

        if ema_17 > ema_34 > ema_72 > ema_144:
            return "Alinhadas para ALTA"
        elif ema_17 < ema_34 < ema_72 < ema_144:
            return "Alinhadas para BAIXA"
        else:
            return "Misturadas (sem tendencia clara)"

    def _format_premium_discount(self, zone: str) -> str:
        """Formata zona de premium/discount para exibição."""
        zone_map = {
            'deep_premium': 'DEEP PREMIUM',
            'premium': 'PREMIUM',
            'equilibrium': 'EQUILIBRIO',
            'discount': 'DISCOUNT',
            'deep_discount': 'DEEP DISCOUNT'
        }
        return zone_map.get(zone, zone.upper() if zone else 'N/D')

    def _log_analysis_report(self, position: Dict[str, Any], indicators: Dict[str, Any],
                            sentiment: Dict[str, Any], decision: Dict[str, Any]) -> None:
        """
        Registra relatório detalhado da análise da posição.

        Args:
            position: Dados da posição
            indicators: Indicadores calculados
            sentiment: Dados de sentimento
            decision: Decisão gerada
        """
        symbol = position['symbol']
        direction = position['direction']

        # Cabeçalho
        logger.info("=" * 60)
        logger.info(f"ANALISE DETALHADA: {symbol} {direction}")
        logger.info("=" * 60)

        # --- POSIÇÃO ---
        logger.info("")
        logger.info("--- POSICAO ---")
        entry = position['entry_price']
        mark = position['mark_price']
        margin = position.get('margin_invested', 0)
        pnl = position['unrealized_pnl']
        pnl_pct = position['unrealized_pnl_pct']
        leverage = position['leverage']
        margin_type = position.get('margin_type', 'ISOLATED')

        logger.info(f"  Direcao: {direction} | Entrada: {entry:.4f} | Mark: {mark:.4f} | Margem: {margin:.2f} USDT")
        logger.info(f"  PnL: {pnl:+.2f} USDT ({pnl_pct:+.2f}%) | Alavancagem: {leverage}x | Tipo: {margin_type}")

        # --- INDICADORES TÉCNICOS (H4) ---
        logger.info("")
        logger.info("--- INDICADORES TECNICOS (H4) ---")

        rsi = indicators.get('rsi_14')
        if rsi is not None:
            rsi_label = self._format_rsi_interpretation(rsi)
            logger.info(f"  RSI(14): {rsi:.1f} [{rsi_label}]")
        else:
            logger.info(f"  RSI(14): N/D")

        macd_line = indicators.get('macd_line')
        macd_signal = indicators.get('macd_signal')
        macd_hist = indicators.get('macd_histogram')
        if macd_line is not None and macd_signal is not None and macd_hist is not None:
            macd_label = self._format_macd_interpretation(macd_hist)
            logger.info(f"  MACD: Linha={macd_line:.6f} Sinal={macd_signal:.6f} Hist={macd_hist:+.6f} [{macd_label}]")
        else:
            logger.info(f"  MACD: N/D")

        ema_17 = indicators.get('ema_17')
        ema_34 = indicators.get('ema_34')
        ema_72 = indicators.get('ema_72')
        ema_144 = indicators.get('ema_144')
        if all(v is not None for v in [ema_17, ema_34, ema_72, ema_144]):
            logger.info(f"  EMAs: 17={ema_17:.4f} | 34={ema_34:.4f} | 72={ema_72:.4f} | 144={ema_144:.4f}")
            ema_alignment = self._check_ema_alignment(ema_17, ema_34, ema_72, ema_144)
            logger.info(f"  Tendencia EMA: {ema_alignment}")
        else:
            logger.info(f"  EMAs: N/D")

        adx = indicators.get('adx_14')
        di_plus = indicators.get('di_plus')
        di_minus = indicators.get('di_minus')
        if adx is not None:
            adx_label = self._format_adx_interpretation(adx, di_plus, di_minus)
            di_plus_str = f"{di_plus:.1f}" if di_plus is not None else "N/D"
            di_minus_str = f"{di_minus:.1f}" if di_minus is not None else "N/D"
            logger.info(f"  ADX(14): {adx:.1f} | DI+: {di_plus_str} | DI-: {di_minus_str} [{adx_label}]")
        else:
            logger.info(f"  ADX(14): N/D")

        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        bb_percent_b = indicators.get('bb_percent_b')
        if all(v is not None for v in [bb_upper, bb_lower, bb_percent_b]):
            bb_label = self._format_bb_interpretation(bb_percent_b)
            logger.info(f"  Bollinger: Upper={bb_upper:.4f} | Lower={bb_lower:.4f} | %B={bb_percent_b:.2f} [{bb_label}]")
        else:
            logger.info(f"  Bollinger: N/D")

        atr = indicators.get('atr_14')
        if atr is not None:
            logger.info(f"  ATR(14): {atr:.6f}")
        else:
            logger.info(f"  ATR(14): N/D")

        # --- ANÁLISE SMC (H1) ---
        logger.info("")
        logger.info("--- ANALISE SMC (H1) ---")

        market_structure = indicators.get('market_structure', 'range')
        logger.info(f"  Estrutura de Mercado: {market_structure.upper()}")

        bos_recent = indicators.get('bos_recent', 0)
        logger.info(f"  BOS Recente: {'Sim (Break of Structure confirmado)' if bos_recent else 'Nao'}")

        choch_recent = indicators.get('choch_recent', 0)
        logger.info(f"  CHoCH Recente: {'Sim (Change of Character detectado)' if choch_recent else 'Nao'}")

        premium_discount = indicators.get('premium_discount_zone')
        if premium_discount:
            zone_label = self._format_premium_discount(premium_discount)
            # Calculate position in range percentage if possible
            logger.info(f"  Zona Premium/Discount: {zone_label}")
        else:
            logger.info(f"  Zona Premium/Discount: N/D")

        nearest_ob = indicators.get('nearest_ob_distance_pct')
        if nearest_ob is not None:
            # Nota: nearest_ob_distance_pct é distância absoluta, não indica direção
            # Para LONG, assumimos OB abaixo; para SHORT, OB acima
            ob_price = mark * (1 + nearest_ob / 100) if direction == 'SHORT' else mark * (1 - nearest_ob / 100)
            logger.info(f"  Order Block mais proximo: {ob_price:.4f} (distancia: {nearest_ob:.1f}%)")
        else:
            logger.info(f"  Order Block mais proximo: N/D")

        nearest_fvg = indicators.get('nearest_fvg_distance_pct')
        if nearest_fvg is not None:
            fvg_price = mark * (1 + nearest_fvg / 100) if direction == 'SHORT' else mark * (1 - nearest_fvg / 100)
            logger.info(f"  Fair Value Gap mais proximo: {fvg_price:.4f} (distancia: {nearest_fvg:.1f}%)")
        else:
            logger.info(f"  Fair Value Gap mais proximo: N/D")

        liq_above = indicators.get('liquidity_above_pct')
        if liq_above is not None:
            bsl_price = mark * (1 + liq_above / 100)
            logger.info(f"  Liquidez acima: +{liq_above:.1f}% (BSL em {bsl_price:.4f})")
        else:
            logger.info(f"  Liquidez acima: N/D")

        liq_below = indicators.get('liquidity_below_pct')
        if liq_below is not None:
            ssl_price = mark * (1 - liq_below / 100)
            logger.info(f"  Liquidez abaixo: -{liq_below:.1f}% (SSL em {ssl_price:.4f})")
        else:
            logger.info(f"  Liquidez abaixo: N/D")

        # --- SENTIMENTO ---
        logger.info("")
        logger.info("--- SENTIMENTO ---")

        funding_rate = indicators.get('funding_rate')
        if funding_rate is not None:
            funding_pct = funding_rate * 100
            funding_label = "Neutro" if abs(funding_pct) < 0.01 else ("Positivo" if funding_pct > 0 else "Negativo")
            logger.info(f"  Funding Rate: {funding_pct:+.4f}% [{funding_label}]")
        else:
            logger.info(f"  Funding Rate: N/D")

        long_short_ratio = indicators.get('long_short_ratio')
        if long_short_ratio is not None:
            ratio_label = "Maioria Long" if long_short_ratio > 1 else "Maioria Short"
            logger.info(f"  Long/Short Ratio: {long_short_ratio:.2f} [{ratio_label}]")
        else:
            logger.info(f"  Long/Short Ratio: N/D")

        oi_change = indicators.get('open_interest_change_pct')
        if oi_change is not None:
            logger.info(f"  Variacao Open Interest: {oi_change:+.1f}%")
        else:
            logger.info(f"  Variacao Open Interest: N/D")

        # --- NÍVEIS DE DECISÃO ---
        logger.info("")
        logger.info("--- NIVEIS DE DECISAO ---")

        # Target baseado em SMC
        if direction == 'LONG':
            if liq_above is not None:
                target_price = mark * (1 + liq_above / 100)
                logger.info(f"  [ALVO SMC] Proximo alvo: {target_price:.4f} (BSL - Buy Side Liquidity) +{liq_above:.1f}%")
            elif nearest_ob is not None:
                target_price = mark * (1 + nearest_ob / 100)
                logger.info(f"  [ALVO SMC] Proximo alvo: {target_price:.4f} (OB de resistencia) +{nearest_ob:.1f}%")
            else:
                logger.info(f"  [ALVO SMC] Proximo alvo: N/D")
        else:  # SHORT
            if liq_below is not None:
                target_price = mark * (1 - liq_below / 100)
                logger.info(f"  [ALVO SMC] Proximo alvo: {target_price:.4f} (SSL - Sell Side Liquidity) -{liq_below:.1f}%")
            elif nearest_ob is not None:
                target_price = mark * (1 - nearest_ob / 100)
                logger.info(f"  [ALVO SMC] Proximo alvo: {target_price:.4f} (OB de suporte) -{nearest_ob:.1f}%")
            else:
                logger.info(f"  [ALVO SMC] Proximo alvo: N/D")

        # Stop Loss sugerido
        stop_loss = decision.get('stop_loss_suggested')
        if stop_loss is not None:
            stop_pct = abs((stop_loss - mark) / mark * 100)
            # Para LONG, stop é abaixo (negativo); para SHORT, stop é acima (positivo)
            if direction == 'LONG':
                logger.info(f"  [STOP LOSS] Sugerido: {stop_loss:.4f} (abaixo do OB bullish ou swing low) -{stop_pct:.1f}%")
            else:
                logger.info(f"  [STOP LOSS] Sugerido: {stop_loss:.4f} (acima do OB bearish ou swing high) +{stop_pct:.1f}%")
        else:
            logger.info(f"  [STOP LOSS] Sugerido: N/D")

        # Take Profit / Realização Parcial
        take_profit = decision.get('take_profit_suggested')
        if take_profit is not None:
            tp_pct = abs((take_profit - mark) / mark * 100)
            # Para LONG, TP é acima (positivo); para SHORT, TP é abaixo (negativo)
            if direction == 'LONG':
                logger.info(f"  [REALIZACAO PARCIAL] Considerar em: {take_profit:.4f} (proximo da resistencia) +{tp_pct:.1f}%")
            else:
                logger.info(f"  [REALIZACAO PARCIAL] Considerar em: {take_profit:.4f} (proximo do suporte) -{tp_pct:.1f}%")
        else:
            logger.info(f"  [REALIZACAO PARCIAL] Considerar em: N/D")

        # --- DECISÃO ---
        logger.info("")
        logger.info("--- DECISAO ---")

        action = decision['agent_action']
        confidence = decision['decision_confidence']
        risk_score = decision['risk_score']

        logger.info(f"  Acao: {action}")
        logger.info(f"  Confianca: {confidence:.2f}")
        logger.info(f"  Risco: {risk_score:.1f}/10")

        # Parse reasoning
        reasoning_json = decision.get('decision_reasoning', '[]')
        try:
            reasoning = json.loads(reasoning_json) if isinstance(reasoning_json, str) else reasoning_json
            if reasoning:
                logger.info(f"  Razoes:")
                for i, reason in enumerate(reasoning, 1):
                    logger.info(f"    {i}. {reason}")
        except:
            pass

        logger.info("=" * 60)

    def _generate_analysis_summary(self, position: Dict[str, Any], indicators: Dict[str, Any],
                                   decision: Dict[str, Any]) -> str:
        """
        Gera resumo estruturado da análise para persistência e RL.
        Este resumo facilita a revisão dos dados de treinamento.

        Args:
            position: Dados da posição
            indicators: Indicadores calculados
            decision: Decisão gerada

        Returns:
            String JSON com resumo estruturado da análise
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'position': {
                'symbol': position['symbol'],
                'direction': position['direction'],
                'entry': position['entry_price'],
                'mark': position['mark_price'],
                'pnl_pct': position['unrealized_pnl_pct'],
                'leverage': position['leverage'],
                'margin_type': position.get('margin_type', 'ISOLATED')
            },
            'technical': {
                'rsi': indicators.get('rsi_14'),
                'rsi_interpretation': self._format_rsi_interpretation(indicators.get('rsi_14')) if indicators.get('rsi_14') else None,
                'macd_histogram': indicators.get('macd_histogram'),
                'macd_signal': self._format_macd_interpretation(indicators.get('macd_histogram')),
                'ema_alignment': self._check_ema_alignment(
                    indicators.get('ema_17'),
                    indicators.get('ema_34'),
                    indicators.get('ema_72'),
                    indicators.get('ema_144')
                ),
                'adx': indicators.get('adx_14'),
                'bb_percent': indicators.get('bb_percent_b')
            },
            'smc': {
                'market_structure': indicators.get('market_structure', 'range'),
                'bos_recent': bool(indicators.get('bos_recent', 0)),
                'choch_recent': bool(indicators.get('choch_recent', 0)),
                'premium_discount': self._format_premium_discount(indicators.get('premium_discount_zone')),
                'nearest_ob_pct': indicators.get('nearest_ob_distance_pct'),
                'nearest_fvg_pct': indicators.get('nearest_fvg_distance_pct'),
                'liquidity_above_pct': indicators.get('liquidity_above_pct'),
                'liquidity_below_pct': indicators.get('liquidity_below_pct')
            },
            'sentiment': {
                'funding_rate': indicators.get('funding_rate'),
                'long_short_ratio': indicators.get('long_short_ratio'),
                'oi_change_pct': indicators.get('open_interest_change_pct')
            },
            'decision': {
                'action': decision['agent_action'],
                'confidence': decision['decision_confidence'],
                'risk_score': decision['risk_score'],
                'stop_loss': decision.get('stop_loss_suggested'),
                'take_profit': decision.get('take_profit_suggested'),
                'stop_loss_source': decision.get('stop_loss_source', 'ATR'),
                'take_profit_source': decision.get('take_profit_source', 'ATR')
            }
        }

        return json.dumps(summary, ensure_ascii=False)

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
            'outcome_label': None,

            # Resumo estruturado da análise para RL e revisão
            'analysis_summary': self._generate_analysis_summary(position, indicators, decision)
        }

        return snapshot

    def _opposite_side_for_close(self, direction: str) -> str:
        """Retorna o side necessário para fechar/reduzir posição existente."""
        return 'SELL' if direction == 'LONG' else 'BUY'

    def _extract_order_data(self, response) -> Optional[Any]:
        """Extrai payload de resposta da API para dict compatível."""
        try:
            if response is None:
                return None
            return self._extract_data(response)
        except Exception:
            return None

    def _flatten_order_payload(self, payload: Any) -> List[Dict[str, Any]]:
        """Normaliza payloads de listagem de ordens para lista de dicts."""
        if payload is None:
            return []

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            for key in ('orders', 'data', 'rows', 'list', 'result'):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            return [payload]

        return []

    def _is_existing_protection_error(self, error: Exception) -> bool:
        """Detecta erro de proteção já existente retornado pela Binance."""
        error_text = str(error).upper()
        return (
            '-4130' in error_text
            or 'OPEN STOP OR TAKE PROFIT ORDER' in error_text
            or 'CLOSEPOSITION IN THE DIRECTION IS EXISTING' in error_text
        )

    def _is_symbol_allowed_for_protection(self, symbol: str) -> bool:
        """Valida se símbolo pode receber criação/recriação de SL/TP no modo live."""
        if self.mode != 'live':
            return True

        authorized_symbols = set(getattr(self.order_executor, 'authorized_symbols', set()))
        if not authorized_symbols:
            return True

        return str(symbol).upper() in authorized_symbols

    def _normalize_market_structure(self, market_structure: Optional[str]) -> str:
        """Normaliza estrutura de mercado para comparação estável."""
        value = str(market_structure or 'range').strip().lower()
        return value if value else 'range'

    def _track_market_structure_change(self, symbol: str, market_structure: Optional[str]) -> Dict[str, Any]:
        """Rastreia mudança de estrutura por símbolo e retorna transição detectada."""
        current = self._normalize_market_structure(market_structure)
        previous = self._last_market_structure_by_symbol.get(symbol)
        self._last_market_structure_by_symbol[symbol] = current

        return {
            'changed': previous is not None and previous != current,
            'previous': previous,
            'current': current,
        }

    def _get_persisted_protection_state(self, symbol: str, direction: str) -> Dict[str, bool]:
        """Consulta estado persistido no execution_log para evitar recriação de SL/TP."""
        lookback_ms = int((datetime.now() - timedelta(hours=72)).timestamp() * 1000)
        has_sl = False
        has_tp = False

        try:
            logs = self.db.get_execution_log(symbol=symbol, start_time=lookback_ms, executed_only=True)
            for item in logs:
                if str(item.get('direction') or '').upper() != direction:
                    continue

                action = str(item.get('action') or '').upper()
                if action == 'SET_SL':
                    has_sl = True
                elif action == 'SET_TP':
                    has_tp = True

                if has_sl and has_tp:
                    break
        except Exception as e:
            logger.debug(f"Falha ao consultar estado persistido de proteção para {symbol}: {e}")

        return {'has_sl': has_sl, 'has_tp': has_tp}

    def _get_symbol_price_precision_info(self, symbol: str) -> Dict[str, Any]:
        """Obtém precision/tick_size de preço do símbolo via exchange_info."""
        if symbol in self._symbol_price_precision_cache:
            return self._symbol_price_precision_cache[symbol]

        default_info = {
            'price_precision': 8,
            'tick_size': None,
        }

        try:
            response = self._client.rest_api.exchange_information()
            data = self._extract_data(response)

            symbols = None
            if hasattr(data, 'symbols'):
                symbols = data.symbols
            elif isinstance(data, dict):
                symbols = data.get('symbols')

            if not symbols:
                self._symbol_price_precision_cache[symbol] = default_info
                return default_info

            for symbol_info in symbols:
                if isinstance(symbol_info, dict):
                    symbol_name = symbol_info.get('symbol')
                    price_precision = symbol_info.get('pricePrecision')
                    if price_precision is None:
                        price_precision = symbol_info.get('price_precision', 8)
                    filters = symbol_info.get('filters', [])
                else:
                    symbol_name = getattr(symbol_info, 'symbol', None)
                    price_precision = getattr(symbol_info, 'price_precision', 8)
                    filters = getattr(symbol_info, 'filters', [])

                if symbol_name != symbol:
                    continue

                tick_size = None
                for f in filters or []:
                    if isinstance(f, dict):
                        filter_type = f.get('filterType')
                        if filter_type is None:
                            filter_type = f.get('filter_type')

                        if filter_type == 'PRICE_FILTER':
                            raw_tick = f.get('tickSize')
                            if raw_tick is None:
                                raw_tick = f.get('tick_size', 0)
                            tick_size = float(raw_tick or 0)
                            break
                    else:
                        if getattr(f, 'filter_type', None) == 'PRICE_FILTER':
                            tick_size = float(getattr(f, 'tick_size', 0) or 0)
                            break

                info = {
                    'price_precision': int(price_precision) if price_precision is not None else 8,
                    'tick_size': tick_size if tick_size and tick_size > 0 else None,
                }
                self._symbol_price_precision_cache[symbol] = info
                return info
        except Exception as e:
            logger.warning(f"Falha ao obter precision de preço para {symbol}: {e}")

        self._symbol_price_precision_cache[symbol] = default_info
        return default_info

    def _normalize_trigger_price(self, symbol: str, trigger_price: float, side: str) -> str:
        """Normaliza trigger_price para precision/tick_size aceitos pela Binance."""
        info = self._get_symbol_price_precision_info(symbol)
        tick_size = info.get('tick_size')
        trigger_dec = Decimal(str(trigger_price))

        if tick_size:
            tick_dec = Decimal(str(tick_size))
            if tick_dec <= 0:
                tick_dec = Decimal('0.00000001')

            ratio = trigger_dec / tick_dec
            if side == 'BUY':
                steps = ratio.to_integral_value(rounding=ROUND_CEILING)
            else:
                steps = ratio.to_integral_value(rounding=ROUND_FLOOR)

            normalized = steps * tick_dec
            decimals = max(0, -tick_dec.as_tuple().exponent)
            return format(normalized, f'.{decimals}f')

        price_precision = info.get('price_precision', 8)
        quant = Decimal('1').scaleb(-int(price_precision))
        normalized = trigger_dec.quantize(quant)
        return format(normalized, f'.{int(price_precision)}f')

    def _persist_protection_execution(
        self,
        position: Dict[str, Any],
        decision: Dict[str, Any],
        action: str,
        order_response: Optional[Dict[str, Any]],
        executed: bool,
        reason: str,
        trigger_price: Optional[float],
        snapshot_id: Optional[int],
        side: str,
    ) -> None:
        """Persiste no execution_log o resultado de criação de SL/TP."""
        timestamp = int(datetime.now().timestamp() * 1000)
        order_id = None
        if order_response:
            order_id = order_response.get('orderId') or order_response.get('order_id')

        execution_data = {
            'timestamp': timestamp,
            'symbol': position['symbol'],
            'direction': position['direction'],
            'action': action,
            'side': side,
            'quantity': position.get('position_size_qty', 0.0),
            'order_type': 'CONDITIONAL_MARKET',
            'reduce_only': 1,
            'executed': 1 if executed else 0,
            'mode': self.mode,
            'reason': reason,
            'order_id': order_id,
            'fill_price': trigger_price,
            'fill_quantity': None,
            'commission': None,
            'entry_price': position.get('entry_price'),
            'mark_price': position.get('mark_price'),
            'unrealized_pnl': position.get('unrealized_pnl'),
            'unrealized_pnl_pct': position.get('unrealized_pnl_pct'),
            'risk_score': decision.get('risk_score'),
            'decision_confidence': decision.get('decision_confidence'),
            'decision_reasoning': decision.get('decision_reasoning'),
            'snapshot_id': snapshot_id,
        }

        try:
            self.db.insert_execution_log(execution_data)
        except Exception as e:
            logger.warning(f"Falha ao persistir execution_log de proteção ({action}): {e}")

    def _place_protective_order(
        self,
        symbol: str,
        direction: str,
        trigger_price: float,
        order_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Cria ordem condicional de proteção (SL/TP) para fechar posição existente.

        Usa endpoint de algo-order do SDK e close_position=true para fechar
        a posição integral no trigger.
        """
        side = self._opposite_side_for_close(direction)
        normalized_trigger_price = self._normalize_trigger_price(symbol, trigger_price, side)

        response = self._client.rest_api.new_algo_order(
            algo_type='CONDITIONAL',
            symbol=symbol,
            side=side,
            type=order_type,
            trigger_price=normalized_trigger_price,
            close_position='true',
            working_type='MARK_PRICE',
            recv_window=10000,
        )
        logger.info(
            f"Ordem de proteção enviada: {order_type} {symbol} side={side} "
            f"trigger={normalized_trigger_price}"
        )
        return self._extract_order_data(response)

    def _list_open_algo_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Lista ordens algo abertas do símbolo com fallback de métodos do SDK."""
        rest_api = self._client.rest_api
        candidates = [
            ('current_all_algo_open_orders', {'symbol': symbol}),
            ('query_all_algo_orders', {'symbol': symbol}),
            ('current_all_algo_open_orders', {}),
            ('query_all_algo_orders', {}),
        ]

        for method_name, kwargs in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(**kwargs)
                data = self._extract_order_data(response)
                if data is None:
                    return []

                data = self._flatten_order_payload(data)

                filtered = []
                for order in data:
                    order_symbol = self._safe_get(order, ['symbol'])
                    if order_symbol == symbol:
                        filtered.append(order)
                return filtered
            except Exception as e:
                logger.debug(f"Falha ao listar algo orders com {method_name} para {symbol}: {e}")
                continue

        return []

    def _list_open_standard_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Lista ordens abertas padrão com fallback para diferentes métodos do SDK."""
        rest_api = self._client.rest_api
        candidates = [
            ('current_all_open_orders', {'symbol': symbol}),
            ('query_current_all_open_orders', {'symbol': symbol}),
            ('current_all_open_orders', {}),
            ('query_current_all_open_orders', {}),
        ]

        for method_name, kwargs in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(**kwargs)
                data = self._extract_order_data(response)
                if data is None:
                    return []

                data = self._flatten_order_payload(data)
                filtered = []
                for order in data:
                    order_symbol = self._safe_get(order, ['symbol'])
                    if order_symbol == symbol:
                        filtered.append(order)
                return filtered
            except Exception as e:
                logger.debug(f"Falha ao listar open orders com {method_name} para {symbol}: {e}")
                continue

        return []

    def _extract_order_identifier(self, order: Dict[str, Any]) -> Optional[str]:
        """Extrai identificador de ordem (order/algo/client id) com fallback de campos."""
        for key in ('orderId', 'order_id', 'algoId', 'algo_id', 'clientOrderId', 'client_order_id'):
            value = self._safe_get(order, [key])
            if value is not None and str(value).strip() != '':
                return str(value)
        return None

    def _cancel_single_protection_order(self, symbol: str, order: Dict[str, Any]) -> bool:
        """Cancela ordem de proteção usando múltiplos métodos/assinaturas do SDK."""
        rest_api = self._client.rest_api
        identifier = self._extract_order_identifier(order)
        if not identifier:
            return False

        method_candidates = [
            ('cancel_algo_order', [
                {'symbol': symbol, 'order_id': identifier},
                {'symbol': symbol, 'algo_id': identifier},
                {'symbol': symbol, 'orderId': identifier},
                {'symbol': symbol, 'algoId': identifier},
            ]),
            ('cancel_order', [
                {'symbol': symbol, 'order_id': identifier},
                {'symbol': symbol, 'orderId': identifier},
                {'symbol': symbol, 'orig_client_order_id': identifier},
                {'symbol': symbol, 'origClientOrderId': identifier},
            ]),
        ]

        for method_name, kwargs_list in method_candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            for kwargs in kwargs_list:
                try:
                    method(**kwargs)
                    logger.info(f"Ordem de proteção cancelada: {symbol} {identifier} via {method_name}")
                    return True
                except Exception as e:
                    logger.debug(
                        f"Falha ao cancelar ordem {identifier} em {symbol} com {method_name}({kwargs}): {e}"
                    )

        return False

    def _cancel_open_protection_orders(self, symbol: str, direction: str) -> Dict[str, int]:
        """Cancela SL/TP abertos da posição para permitir recriação com nova estrutura."""
        side = self._opposite_side_for_close(direction)
        has_seen_ids = set()
        cancelled_sl = 0
        cancelled_tp = 0

        for order in self._list_open_algo_orders(symbol) + self._list_open_standard_orders(symbol):
            order_type = str(self._safe_get(order, ['type']) or '').upper()
            order_side = str(self._safe_get(order, ['side']) or '').upper()
            close_position = self._safe_get(order, ['close_position', 'closePosition'])
            is_close_position = str(close_position).lower() in ('true', '1')
            reduce_only = self._safe_get(order, ['reduce_only', 'reduceOnly'])
            is_reduce_only = str(reduce_only).lower() in ('true', '1')
            order_status = str(self._safe_get(order, ['status']) or '').upper()
            is_open_status = (not order_status) or order_status in ('NEW', 'PARTIALLY_FILLED', 'PENDING_NEW')

            if order_side != side or not is_open_status:
                continue
            if not is_close_position and not is_reduce_only:
                continue
            if order_type not in ('STOP_MARKET', 'STOP', 'TAKE_PROFIT_MARKET', 'TAKE_PROFIT'):
                continue

            order_id = self._extract_order_identifier(order)
            if order_id and order_id in has_seen_ids:
                continue

            cancelled = self._cancel_single_protection_order(symbol, order)
            if cancelled:
                if order_id:
                    has_seen_ids.add(order_id)
                if order_type in ('STOP_MARKET', 'STOP'):
                    cancelled_sl += 1
                else:
                    cancelled_tp += 1

        return {
            'cancelled_sl': cancelled_sl,
            'cancelled_tp': cancelled_tp,
        }

    def refresh_protection_on_structure_change(
        self,
        position: Dict[str, Any],
        decision: Dict[str, Any],
        snapshot_id: Optional[int],
        previous_structure: Optional[str],
        current_structure: str,
    ) -> Dict[str, Any]:
        """
        Em mudança de estrutura, cancela SL/TP atuais e cria novas proteções.
        """
        symbol = position['symbol']
        if not self._is_symbol_allowed_for_protection(symbol):
            return {
                'ok': False,
                'reason': f"Símbolo fora da whitelist para proteção: {symbol}",
                'sl_created': False,
                'tp_created': False,
                'cancelled_sl': 0,
                'cancelled_tp': 0,
            }

        direction = position['direction']
        side = self._opposite_side_for_close(direction)
        mark_price = float(position['mark_price'])

        stop_price = decision.get('stop_loss_suggested')
        tp_price = decision.get('take_profit_suggested')

        valid_sl = False
        if stop_price is not None:
            if direction == 'LONG' and float(stop_price) < mark_price:
                valid_sl = True
            if direction == 'SHORT' and float(stop_price) > mark_price:
                valid_sl = True

        valid_tp = False
        if tp_price is not None:
            if direction == 'LONG' and float(tp_price) > mark_price:
                valid_tp = True
            if direction == 'SHORT' and float(tp_price) < mark_price:
                valid_tp = True

        if not valid_sl and not valid_tp:
            return {
                'ok': False,
                'reason': 'Sem SL/TP válidos para refresh de estrutura',
                'sl_created': False,
                'tp_created': False,
                'cancelled_sl': 0,
                'cancelled_tp': 0,
            }

        cancelled = self._cancel_open_protection_orders(symbol, direction)
        reason_prefix = (
            f"Refresh por mudança de estrutura ({previous_structure or 'desconhecida'} -> {current_structure})"
        )

        sl_created = False
        tp_created = False

        if valid_sl:
            try:
                sl_response = self._place_protective_order(
                    symbol=symbol,
                    direction=direction,
                    trigger_price=float(stop_price),
                    order_type='STOP_MARKET',
                )
                sl_created = sl_response is not None
                self._persist_protection_execution(
                    position=position,
                    decision=decision,
                    action='SET_SL',
                    order_response=sl_response,
                    executed=sl_created,
                    reason=f'{reason_prefix} - SL recriado' if sl_created else f'{reason_prefix} - Falha ao recriar SL',
                    trigger_price=float(stop_price),
                    snapshot_id=snapshot_id,
                    side=side,
                )
            except Exception as e:
                if self._is_existing_protection_error(e):
                    sl_created = True
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_SL',
                        order_response=None,
                        executed=True,
                        reason=f'{reason_prefix} - SL já existente após refresh',
                        trigger_price=float(stop_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                else:
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_SL',
                        order_response=None,
                        executed=False,
                        reason=f'{reason_prefix} - Falha ao recriar SL: {e}',
                        trigger_price=float(stop_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                    logger.error(f"Erro ao recriar STOP_MARKET para {symbol}: {e}")

        if valid_tp:
            try:
                tp_response = self._place_protective_order(
                    symbol=symbol,
                    direction=direction,
                    trigger_price=float(tp_price),
                    order_type='TAKE_PROFIT_MARKET',
                )
                tp_created = tp_response is not None
                self._persist_protection_execution(
                    position=position,
                    decision=decision,
                    action='SET_TP',
                    order_response=tp_response,
                    executed=tp_created,
                    reason=f'{reason_prefix} - TP recriado' if tp_created else f'{reason_prefix} - Falha ao recriar TP',
                    trigger_price=float(tp_price),
                    snapshot_id=snapshot_id,
                    side=side,
                )
            except Exception as e:
                if self._is_existing_protection_error(e):
                    tp_created = True
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_TP',
                        order_response=None,
                        executed=True,
                        reason=f'{reason_prefix} - TP já existente após refresh',
                        trigger_price=float(tp_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                else:
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_TP',
                        order_response=None,
                        executed=False,
                        reason=f'{reason_prefix} - Falha ao recriar TP: {e}',
                        trigger_price=float(tp_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                    logger.error(f"Erro ao recriar TAKE_PROFIT_MARKET para {symbol}: {e}")

        return {
            'ok': (sl_created or not valid_sl) and (tp_created or not valid_tp),
            'reason': reason_prefix,
            'sl_created': sl_created,
            'tp_created': tp_created,
            'cancelled_sl': cancelled['cancelled_sl'],
            'cancelled_tp': cancelled['cancelled_tp'],
        }

    def _has_existing_protection_orders(self, symbol: str, direction: str) -> Dict[str, bool]:
        """Verifica se já existem ordens SL/TP de proteção abertas para a posição."""
        side = self._opposite_side_for_close(direction)
        algo_orders = self._list_open_algo_orders(symbol)
        regular_orders = self._list_open_standard_orders(symbol)

        has_sl = False
        has_tp = False

        for order in algo_orders + regular_orders:
            order_type = str(self._safe_get(order, ['type']) or '').upper()
            order_side = str(self._safe_get(order, ['side']) or '').upper()
            close_position = self._safe_get(order, ['close_position', 'closePosition'])
            is_close_position = str(close_position).lower() in ('true', '1')
            reduce_only = self._safe_get(order, ['reduce_only', 'reduceOnly'])
            is_reduce_only = str(reduce_only).lower() in ('true', '1')
            order_status = str(self._safe_get(order, ['status']) or '').upper()
            is_open_status = (not order_status) or order_status in ('NEW', 'PARTIALLY_FILLED', 'PENDING_NEW')

            if not is_open_status or order_side != side:
                continue

            if not is_close_position and not is_reduce_only:
                continue

            if order_type in ('STOP_MARKET', 'STOP'):
                has_sl = True
            elif order_type in ('TAKE_PROFIT_MARKET', 'TAKE_PROFIT'):
                has_tp = True

        return {'has_sl': has_sl, 'has_tp': has_tp}

    def adopt_position_with_protection(self, symbol: str) -> Dict[str, Any]:
        """
        Assume uma posição aberta específica e cria SL/TP reais na Binance.

        Fluxo:
        1) Busca posição aberta
        2) Calcula indicadores e decisão
        3) Persiste snapshot inicial
        4) Cria ordens reais de STOP_MARKET e TAKE_PROFIT_MARKET (close_position)
        """
        positions = self.fetch_open_positions(symbol=symbol)
        if not positions:
            return {
                'ok': False,
                'reason': f'Nenhuma posição aberta para {symbol}',
                'sl_created': False,
                'tp_created': False,
            }

        position = positions[0]

        if not self._is_symbol_allowed_for_protection(symbol):
            logger.info(f"[PROTEÇÃO] Criação de SL/TP ignorada para {symbol}: fora da whitelist")
            return {
                'ok': False,
                'reason': f'Símbolo fora da whitelist para proteção: {symbol}',
                'sl_created': False,
                'tp_created': False,
                'sl_ready': False,
                'tp_ready': False,
            }

        try:
            market_data = self.fetch_current_market_data(symbol)
            indicators = self.calculate_indicators_snapshot(symbol, market_data)
            sentiment = market_data.get('sentiment', {})
            decision = self.evaluate_position(position, indicators, sentiment)

            snapshot = self.create_snapshot(position, indicators, sentiment, decision)
            snapshot_id = self.db.insert_position_snapshot(snapshot)

            mark_price = float(position['mark_price'])
            direction = position['direction']

            stop_price = decision.get('stop_loss_suggested')
            tp_price = decision.get('take_profit_suggested')

            existing_protection_exchange = self._has_existing_protection_orders(symbol, direction)
            existing_protection_persisted = self._get_persisted_protection_state(symbol, direction)

            sl_created = existing_protection_exchange['has_sl']
            tp_created = existing_protection_exchange['has_tp']
            side = self._opposite_side_for_close(direction)

            if existing_protection_persisted['has_sl'] and not existing_protection_exchange['has_sl']:
                logger.info(
                    f"SL encontrado no estado persistido para {symbol}, mas sem ordem aberta na Binance; "
                    f"tentando recriar proteção"
                )
            if existing_protection_persisted['has_tp'] and not existing_protection_exchange['has_tp']:
                logger.info(
                    f"TP encontrado no estado persistido para {symbol}, mas sem ordem aberta na Binance; "
                    f"tentando recriar proteção"
                )

            # Validar coerência dos gatilhos para evitar trigger imediato/rejeição
            valid_sl = False
            if stop_price is not None:
                if direction == 'LONG' and float(stop_price) < mark_price:
                    valid_sl = True
                if direction == 'SHORT' and float(stop_price) > mark_price:
                    valid_sl = True

            valid_tp = False
            if tp_price is not None:
                if direction == 'LONG' and float(tp_price) > mark_price:
                    valid_tp = True
                if direction == 'SHORT' and float(tp_price) < mark_price:
                    valid_tp = True

            if valid_sl and not sl_created:
                try:
                    sl_response = self._place_protective_order(
                        symbol=symbol,
                        direction=direction,
                        trigger_price=float(stop_price),
                        order_type='STOP_MARKET',
                    )
                    sl_created = sl_response is not None
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_SL',
                        order_response=sl_response,
                        executed=sl_created,
                        reason='SL de proteção criado no modo adoção' if sl_created else 'Falha ao criar SL',
                        trigger_price=float(stop_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                except Exception as e:
                    if self._is_existing_protection_error(e):
                        sl_created = True
                        self._persist_protection_execution(
                            position=position,
                            decision=decision,
                            action='SET_SL',
                            order_response=None,
                            executed=True,
                            reason='SL já existente na Binance (detecção de duplicidade)',
                            trigger_price=float(stop_price),
                            snapshot_id=snapshot_id,
                            side=side,
                        )
                        logger.info(f"SL já existente para {symbol}; erro de duplicidade tratado")
                    else:
                        self._persist_protection_execution(
                            position=position,
                            decision=decision,
                            action='SET_SL',
                            order_response=None,
                            executed=False,
                            reason=f'Falha ao criar SL: {e}',
                            trigger_price=float(stop_price),
                            snapshot_id=snapshot_id,
                            side=side,
                        )
                        logger.error(f"Erro ao criar STOP_MARKET para {symbol}: {e}")
            elif valid_sl and sl_created:
                logger.info(f"SL já existente para {symbol}; não será recriado")
                if existing_protection_exchange['has_sl'] and not existing_protection_persisted['has_sl']:
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_SL',
                        order_response=None,
                        executed=True,
                        reason='SL já existente na Binance (detectado no bootstrap)',
                        trigger_price=float(stop_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
            else:
                logger.warning(f"SL sugerido inválido/ausente para {symbol}. mark={mark_price}, sl={stop_price}")

            if valid_tp and not tp_created:
                try:
                    tp_response = self._place_protective_order(
                        symbol=symbol,
                        direction=direction,
                        trigger_price=float(tp_price),
                        order_type='TAKE_PROFIT_MARKET',
                    )
                    tp_created = tp_response is not None
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_TP',
                        order_response=tp_response,
                        executed=tp_created,
                        reason='TP de proteção criado no modo adoção' if tp_created else 'Falha ao criar TP',
                        trigger_price=float(tp_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
                except Exception as e:
                    if self._is_existing_protection_error(e):
                        tp_created = True
                        self._persist_protection_execution(
                            position=position,
                            decision=decision,
                            action='SET_TP',
                            order_response=None,
                            executed=True,
                            reason='TP já existente na Binance (detecção de duplicidade)',
                            trigger_price=float(tp_price),
                            snapshot_id=snapshot_id,
                            side=side,
                        )
                        logger.info(f"TP já existente para {symbol}; erro de duplicidade tratado")
                    else:
                        self._persist_protection_execution(
                            position=position,
                            decision=decision,
                            action='SET_TP',
                            order_response=None,
                            executed=False,
                            reason=f'Falha ao criar TP: {e}',
                            trigger_price=float(tp_price),
                            snapshot_id=snapshot_id,
                            side=side,
                        )
                        logger.error(f"Erro ao criar TAKE_PROFIT_MARKET para {symbol}: {e}")
            elif valid_tp and tp_created:
                logger.info(f"TP já existente para {symbol}; não será recriado")
                if existing_protection_exchange['has_tp'] and not existing_protection_persisted['has_tp']:
                    self._persist_protection_execution(
                        position=position,
                        decision=decision,
                        action='SET_TP',
                        order_response=None,
                        executed=True,
                        reason='TP já existente na Binance (detectado no bootstrap)',
                        trigger_price=float(tp_price),
                        snapshot_id=snapshot_id,
                        side=side,
                    )
            else:
                logger.warning(f"TP sugerido inválido/ausente para {symbol}. mark={mark_price}, tp={tp_price}")

            sl_ready = sl_created
            tp_ready = tp_created

            return {
                'ok': sl_ready and tp_ready,
                'reason': 'Proteções configuradas' if (sl_ready and tp_ready) else 'Não foi possível configurar SL/TP',
                'sl_created': sl_created,
                'tp_created': tp_created,
                'sl_ready': sl_ready,
                'tp_ready': tp_ready,
                'snapshot_id': snapshot_id,
                'stop_loss_suggested': stop_price,
                'take_profit_suggested': tp_price,
            }
        except Exception as e:
            logger.error(f"Erro no bootstrap de adoção para {symbol}: {e}", exc_info=True)
            return {
                'ok': False,
                'reason': str(e),
                'sl_created': False,
                'tp_created': False,
            }

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
        positions = self.fetch_open_positions(symbol, log_each_position=False)

        if not positions:
            logger.info("Nenhuma posição aberta encontrada")
            return snapshots

        # Em modo live, monitoramos TODAS as posições abertas para evitar pontos cegos.
        # A whitelist continua sendo aplicada no OrderExecutor durante execução de ordens.
        authorized_symbols = set(getattr(self.order_executor, 'authorized_symbols', set()))
        if self.mode == 'live' and authorized_symbols:
            in_scope = sum(1 for p in positions if p.get('symbol') in authorized_symbols)
            out_scope = len(positions) - in_scope
            if out_scope > 0:
                logger.info(
                    f"Escopo de execução: {in_scope} símbolo(s) na whitelist e {out_scope} fora. "
                    f"Monitoramento/gestão analítica seguirá para todos; execução automática respeita whitelist."
                )

        logger.info(f"Encontradas {len(positions)} posição(ões) aberta(s) para gestão neste ciclo")

        for p in positions:
            logger.info(
                f"Posição em gestão: {p['symbol']} {p['direction']} [{p['margin_type']}] "
                f"Margem: {p['margin_invested']:.2f} USDT | "
                f"PnL: {p['unrealized_pnl']:.2f} USDT ({p['unrealized_pnl_pct']:.2f}%)"
            )

        # 2. Para cada posição, fazer avaliação completa
        for position in positions:
            try:
                pos_symbol = position['symbol']
                logger.info(f"\n--- Analisando {pos_symbol} {position['direction']} ---")

                # Em modo live, garantir bootstrap de proteções (SL/TP) para posições em gestão.
                # Executa uma vez por símbolo por sessão para evitar chamadas redundantes.
                if self.mode == 'live' and pos_symbol not in self._protection_bootstrap_done:
                    if authorized_symbols and pos_symbol not in authorized_symbols:
                        self._protection_bootstrap_done.add(pos_symbol)
                        logger.info(
                            f"[PROTEÇÃO] Bootstrap de SL/TP ignorado para {pos_symbol}: fora da whitelist"
                        )
                        continue

                    try:
                        protection_result = self.adopt_position_with_protection(pos_symbol)
                        if protection_result.get('sl_ready') and protection_result.get('tp_ready'):
                            self._protection_bootstrap_done.add(pos_symbol)
                            logger.info(f"[PROTEÇÃO] SL/TP ativos para {pos_symbol}")
                        else:
                            logger.warning(
                                f"[PROTEÇÃO] Bootstrap parcial para {pos_symbol}: "
                                f"{protection_result.get('reason', 'sem detalhes')}"
                            )
                    except Exception as e:
                        logger.error(f"[PROTEÇÃO] Erro no bootstrap de {pos_symbol}: {e}")

                # a. Buscar dados de mercado
                market_data = self.fetch_current_market_data(pos_symbol)

                # b. Calcular indicadores
                indicators = self.calculate_indicators_snapshot(pos_symbol, market_data)

                # c. Avaliar posição e gerar decisão
                sentiment = market_data.get('sentiment', {})
                decision = self.evaluate_position(position, indicators, sentiment)

                # c2. Exibir relatório detalhado da análise
                self._log_analysis_report(position, indicators, sentiment, decision)

                # d. Criar snapshot completo
                snapshot = self.create_snapshot(position, indicators, sentiment, decision)

                # e. Persistir no banco
                snapshot_id = self.db.insert_position_snapshot(snapshot)
                snapshot['id'] = snapshot_id

                # e1. Em modo live, se a estrutura mudou, renovar SL/TP.
                # Em CLOSE, a execução principal encerrará a posição, então não há refresh.
                if self.mode == 'live' and decision['agent_action'] != 'CLOSE':
                    structure_transition = self._track_market_structure_change(
                        pos_symbol,
                        indicators.get('market_structure', 'range')
                    )
                    if structure_transition['changed']:
                        refresh_result = self.refresh_protection_on_structure_change(
                            position=position,
                            decision=decision,
                            snapshot_id=snapshot_id,
                            previous_structure=structure_transition['previous'],
                            current_structure=structure_transition['current'],
                        )
                        if refresh_result.get('ok'):
                            logger.info(
                                f"[PROTEÇÃO] Estrutura mudou em {pos_symbol} "
                                f"({structure_transition['previous']} -> {structure_transition['current']}); "
                                f"SL/TP renovados (cancelados: SL={refresh_result['cancelled_sl']}, "
                                f"TP={refresh_result['cancelled_tp']})"
                            )
                        else:
                            logger.warning(
                                f"[PROTEÇÃO] Falha no refresh por mudança de estrutura em {pos_symbol}: "
                                f"{refresh_result.get('reason', 'sem detalhes')}"
                            )
                elif self.mode == 'live':
                    # Ainda assim, manter baseline de estrutura atualizado para próximos ciclos.
                    self._track_market_structure_change(
                        pos_symbol,
                        indicators.get('market_structure', 'range')
                    )

                # e2. EXECUTAR DECISÃO (se não for HOLD)
                if decision['agent_action'] != 'HOLD':
                    execution_result = self.order_executor.execute_decision(
                        position=position,
                        decision=decision,
                        snapshot_id=snapshot_id
                    )

                    if execution_result['executed']:
                        logger.info(
                            f"[EXECUÇÃO] {execution_result['action']} {pos_symbol}: "
                            f"side={execution_result['side']}, qty={execution_result['quantity']:.6f}, "
                            f"mode={execution_result['mode']}"
                        )

                        # Se foi CLOSE e executou com sucesso, atualizar past outcomes
                        if execution_result['action'] == 'CLOSE' and execution_result.get('order_response'):
                            fill_price = execution_result.get('fill_price', position['mark_price'])
                            self.update_past_outcomes(
                                symbol=pos_symbol,
                                exit_price=fill_price,
                                exit_timestamp=int(datetime.now().timestamp() * 1000)
                            )
                    else:
                        logger.info(
                            f"[EXECUÇÃO BLOQUEADA] {decision['agent_action']} {pos_symbol}: "
                            f"{execution_result['reason']}"
                        )

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

    def stop(self):
        """
        Para o loop de monitoramento contínuo de forma segura.
        Útil para testes e shutdown gracioso.
        """
        self._running = False
        logger.info("Monitor solicitado a parar")

    def _sleep_with_countdown(self, interval_seconds: int):
        """
        Aguarda interval_seconds com progresso a cada 30 segundos.

        Args:
            interval_seconds: Tempo total de espera em segundos
        """
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

    def run_continuous(self, symbol: Optional[str] = None, interval_seconds: int = 300):
        """
        Loop contínuo que roda monitor_cycle a cada interval_seconds.

        Args:
            symbol: Símbolo específico (opcional)
            interval_seconds: Intervalo entre ciclos em segundos (default: 300 = 5 min)
        """
        self._running = True

        # Handler para graceful shutdown (apenas na thread principal)
        def signal_handler(sig, frame):
            logger.info("\nSinal de interrupção recebido. Finalizando...")
            self._running = False

        if threading.current_thread() is threading.main_thread():
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

                # Consolidado visual de todos os símbolos
                try:
                    from monitoring.cycle_summary import print_cycle_summary
                    from config.symbols import ALL_SYMBOLS
                    print_cycle_summary(ALL_SYMBOLS)
                except Exception as e:
                    logger.error(f"Erro ao exibir consolidado do ciclo: {e}")

                # Aguardar próximo ciclo
                if self._running:
                    logger.info(f"\n[AGUARDANDO] Próximo ciclo em {interval_seconds}s...")
                    self._sleep_with_countdown(interval_seconds)

            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}")
                if self._running:
                    logger.info(f"Aguardando {interval_seconds}s antes de tentar novamente...")
                    self._sleep_with_countdown(interval_seconds)

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
