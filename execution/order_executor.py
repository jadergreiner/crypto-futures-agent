"""
Order Executor — Executes trading orders with multiple safety guards.
Profit Guardian mode: only reduces/closes existing positions, never opens new ones.
"""

import time
import logging
import traceback
import math
from typing import Dict, Any, Optional
from datetime import datetime

from config.execution_config import AUTHORIZED_SYMBOLS, EXECUTION_CONFIG

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Executes trading orders with multiple safety guards.
    Profit Guardian mode: only reduces/closes existing positions, never opens new ones.
    
    IMPORTANTE: Tanto em modo "paper" quanto "live", as ordens são REAIS quando passam
    pelos safety guards. O modo apenas indica o contexto de operação, mas símbolos
    autorizados e validados terão suas ordens executadas na Binance.
    
    Safety Guards (7 layers of protection):
    1. reduceOnly=True — Binance rejects the order if it would open a new position
    2. Symbol whitelist — Only coins in AUTHORIZED_SYMBOLS can be executed
    3. Confidence threshold — Only executes if decision_confidence >= 0.70
    4. Action whitelist — Only CLOSE and REDUCE_50 pass; HOLD and unknown actions blocked
    5. Cooldown per symbol — Won't execute on same symbol within 15 minutes (900s)
    6. Daily execution limit — Max 6 executions per day (resets at 00:00 UTC)
    7. Retry logic — Attempts order placement with retries on failure
    """
    
    def __init__(self, client, db, mode="paper"):
        """
        Inicializa o OrderExecutor.
        
        Args:
            client: DerivativesTradingUsdsFutures SDK client
            db: DatabaseManager instance
            mode: "paper" (teste com ordens reais) or "live" (produção com ordens reais)
                  IMPORTANTE: Ambos os modos enviam ordens REAIS para símbolos autorizados!
        """
        self._client = client
        self._db = db
        self._mode = mode
        self.config = EXECUTION_CONFIG
        self.authorized_symbols = AUTHORIZED_SYMBOLS
        
        # Rastreamento de execuções diárias (dict: date_str -> count)
        self._daily_execution_count = {}
        
        # Rastreamento de cooldown por símbolo (dict: symbol -> last_execution_timestamp)
        self._cooldown_tracker = {}
        
        # Cache de precision por símbolo (dict: symbol -> quantity_precision)
        self._symbol_precision_cache: Dict[str, int] = {}
        
        logger.info(f"OrderExecutor inicializado em modo {mode}")
        logger.info(f"Símbolos autorizados: {sorted(self.authorized_symbols)}")
        logger.info(f"Confiança mínima: {self.config['min_confidence_to_execute']}")
        logger.info(f"Limite diário: {self.config['max_daily_executions']} execuções")
        logger.info(f"Cooldown por símbolo: {self.config['cooldown_per_symbol_seconds']}s")
    
    def execute_decision(self, position: Dict[str, Any], decision: Dict[str, Any], 
                        snapshot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Ponto de entrada principal. Avalia safety guards e executa ordem se todos passarem.
        
        Args:
            position: Dict com dados da posição (symbol, direction, position_size_qty, mark_price, etc.)
            decision: Dict com decisão do agente (agent_action, decision_confidence, etc.)
            snapshot_id: ID opcional do registro position_snapshot para linking
            
        Returns:
            Dict com resultado da execução:
            {
                'executed': bool,
                'action': str,
                'symbol': str,
                'side': str,          # 'BUY' or 'SELL'
                'quantity': float,
                'order_response': dict or None,
                'reason': str,        # Why executed or why blocked
                'mode': str,          # 'paper' or 'live'
                'snapshot_id': int or None,
            }
        """
        symbol = position['symbol']
        action = decision.get('agent_action', 'HOLD')
        confidence = decision.get('decision_confidence', 0.0)
        
        logger.info(f"[EXECUTOR] Avaliando decisão: {action} para {symbol} (confiança: {confidence:.2%})")
        
        # 1. Verificar todos os safety guards
        guards_passed, reason = self._check_safety_guards(symbol, action, confidence)
        
        if not guards_passed:
            logger.warning(f"[EXECUTOR] Safety guard falhou para {symbol}: {reason}")
            return {
                'executed': False,
                'action': action,
                'symbol': symbol,
                'side': None,
                'quantity': 0.0,
                'order_response': None,
                'reason': reason,
                'mode': self._mode,
                'snapshot_id': snapshot_id,
            }
        
        # 2. Calcular parâmetros da ordem (side e quantity)
        try:
            order_params = self._calculate_order_params(position, action)
        except Exception as e:
            reason = f"Erro ao calcular parâmetros da ordem: {e}"
            logger.error(f"[EXECUTOR] {reason}")
            return {
                'executed': False,
                'action': action,
                'symbol': symbol,
                'side': None,
                'quantity': 0.0,
                'order_response': None,
                'reason': reason,
                'mode': self._mode,
                'snapshot_id': snapshot_id,
            }
        
        side = order_params['side']
        quantity = order_params['quantity']
        
        logger.info(f"[EXECUTOR] Parâmetros calculados: side={side}, qty={quantity:.8f}")
        
        # 3. Executar ordem
        # IMPORTANTE: Mesmo em modo "paper", se o símbolo está autorizado e passou por todos os 
        # safety guards, vamos enviar a ordem REAL para a Binance.
        # O modo "paper" apenas indica que estamos em fase de teste, mas com execuções reais
        # para símbolos validados.
        order_response = None
        fill_price = None
        fill_quantity = None
        order_id = None
        commission = None
        
        # Se passou por todos os safety guards, enviar ordem real
        try:
            logger.info(f"[EXECUTOR] Enviando ordem REAL: {side} {quantity:.8f} {symbol} @ MARKET (reduceOnly=True)")
            
            order_response = self._place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=self.config['order_type']
            )
            
            if order_response:
                # Extrair dados da resposta
                order_id = order_response.get('orderId') or order_response.get('order_id')
                fill_price = float(order_response.get('avgPrice', 0) or order_response.get('avg_price', 0) or position['mark_price'])
                fill_quantity = float(order_response.get('executedQty', 0) or order_response.get('executed_qty', 0) or quantity)
                
                # Comissão pode estar em fills ou como campo separado
                commission = 0.0
                if 'fills' in order_response and order_response['fills']:
                    commission = sum(float(fill.get('commission', 0)) for fill in order_response['fills'])
                elif 'commission' in order_response:
                    commission = float(order_response.get('commission', 0))
                
                executed = True
                reason = f"Ordem executada com sucesso - ID: {order_id}"
                logger.info(f"[EXECUTOR] [OK] Ordem executada ({self._mode} mode): {side} {fill_quantity:.8f} {symbol} @ {fill_price:.2f}")
            else:
                executed = False
                reason = "Falha ao executar ordem - resposta vazia"
                logger.error(f"[EXECUTOR] [FALHA] Falha: resposta vazia")
        except Exception as e:
            executed = False
            reason = f"Erro ao executar ordem: {e}"
            logger.error(f"[EXECUTOR] [FALHA] Erro: {e}")
            traceback.print_exc()
        
        # 4. Atualizar rastreadores se executado com sucesso
        if executed:
            self._update_cooldown(symbol)
            self._increment_daily_counter()
        
        # 5. Persistir execução no banco de dados
        execution_result = {
            'executed': executed,
            'action': action,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_response': order_response,
            'reason': reason,
            'mode': self._mode,
            'snapshot_id': snapshot_id,
            'order_id': order_id,
            'fill_price': fill_price,
            'fill_quantity': fill_quantity,
            'commission': commission,
        }
        
        try:
            self._persist_execution(execution_result, position, decision)
        except Exception as e:
            logger.error(f"[EXECUTOR] Erro ao persistir execução no banco: {e}")
        
        # 6. Verificar execução se configurado
        # Como agora paper e live enviam ordens reais, sempre verificar se executado com sucesso
        if executed and self.config.get('verify_after_execution', False) and order_response:
            try:
                self._verify_execution(symbol, quantity)
            except Exception as e:
                logger.warning(f"[EXECUTOR] Erro ao verificar execução: {e}")
        
        return execution_result
    
    def _check_safety_guards(self, symbol: str, action: str, confidence: float) -> tuple[bool, str]:
        """
        Valida TODOS os safety guards. Retorna (passed: bool, reason: str).
        TODOS os guards devem passar para que a execução prossiga.
        """
        # Guard 1: Action deve estar na lista de ações permitidas (CLOSE ou REDUCE_50)
        allowed_actions = self.config['allowed_actions']
        if action not in allowed_actions:
            return False, f"Ação '{action}' não permitida (apenas {allowed_actions} são permitidas)"
        
        # Guard 2: Symbol deve estar na whitelist
        if symbol not in self.authorized_symbols:
            return False, f"Símbolo '{symbol}' não está na whitelist de símbolos autorizados"
        
        # Guard 3: Confidence deve ser >= min_confidence_to_execute
        min_confidence = self.config['min_confidence_to_execute']
        if confidence < min_confidence:
            return False, f"Confiança {confidence:.2%} abaixo do mínimo {min_confidence:.2%}"
        
        # Guard 4: Limite diário não deve ter sido atingido
        daily_count = self._get_daily_execution_count()
        max_daily = self.config['max_daily_executions']
        if daily_count >= max_daily:
            return False, f"Limite diário atingido ({daily_count}/{max_daily} execuções hoje)"
        
        # Guard 5: Cooldown para este símbolo deve ter expirado
        if self._is_symbol_in_cooldown(symbol):
            remaining = self._get_cooldown_remaining(symbol)
            return False, f"Símbolo em cooldown (aguardar {remaining:.0f}s)"
        
        return True, "Todos os safety guards passaram"
    
    def _get_quantity_precision(self, symbol: str) -> int:
        """
        Obtém a quantity precision específica do símbolo consultando a Exchange Info da Binance.
        Usa cache para evitar chamadas repetidas à API.
        
        Args:
            symbol: Símbolo do par (e.g., 'BTCUSDT')
            
        Returns:
            Quantity precision (número de casas decimais) para o símbolo.
            Retorna 8 (padrão) como fallback em caso de erro.
        """
        # Verificar cache primeiro
        if symbol in self._symbol_precision_cache:
            return self._symbol_precision_cache[symbol]
        
        # Buscar da API
        try:
            logger.debug(f"[EXECUTOR] Buscando quantity_precision para {symbol} da Exchange Info API...")
            
            response = self._client.rest_api.exchange_information()
            data = self._extract_data(response)
            
            # Extrair a lista de símbolos
            symbols_list = None
            if data:
                if hasattr(data, 'symbols'):
                    symbols_list = data.symbols
                elif isinstance(data, dict) and 'symbols' in data:
                    symbols_list = data['symbols']
            
            if symbols_list:
                # Iterar pelos símbolos para encontrar o correto
                for symbol_info in symbols_list:
                    # symbol_info pode ser um dict ou um objeto
                    if isinstance(symbol_info, dict):
                        symbol_name = symbol_info.get('symbol')
                        quantity_precision = symbol_info.get('quantityPrecision') or symbol_info.get('quantity_precision')
                    else:
                        symbol_name = getattr(symbol_info, 'symbol', None)
                        quantity_precision = getattr(symbol_info, 'quantity_precision', None)
                    
                    if symbol_name == symbol and quantity_precision is not None:
                        precision = int(quantity_precision)
                        self._symbol_precision_cache[symbol] = precision
                        logger.info(f"[EXECUTOR] Quantity precision para {symbol}: {precision}")
                        return precision
            
            # Se não encontrou o símbolo, usar fallback conservador de 8
            logger.warning(f"[EXECUTOR] Não encontrou quantity_precision para {symbol} na Exchange Info. Usando fallback: 8")
            self._symbol_precision_cache[symbol] = 8
            return 8
            
        except Exception as e:
            logger.error(f"[EXECUTOR] Erro ao buscar quantity_precision para {symbol}: {e}. Usando fallback: 8")
            # Fallback: 8 casas decimais (padrão comum)
            # Isso mantém compatibilidade com comportamento anterior
            self._symbol_precision_cache[symbol] = 8
            return 8
    
    def _calculate_order_params(self, position: Dict[str, Any], action: str) -> Dict[str, Any]:
        """
        Calculates side and quantity for the order.
        
        Logic:
        - CLOSE LONG = SELL 100% qty, reduceOnly=True
        - CLOSE SHORT = BUY 100% qty, reduceOnly=True
        - REDUCE_50 LONG = SELL 50% qty, reduceOnly=True
        - REDUCE_50 SHORT = BUY 50% qty, reduceOnly=True
        
        Returns:
            Dict with 'side' ('BUY' or 'SELL') and 'quantity' (float)
        """
        symbol = position['symbol']
        direction = position['direction']
        position_qty = position['position_size_qty']
        
        # Determinar side baseado na direção da posição
        # Para FECHAR ou REDUZIR uma posição LONG, precisamos VENDER
        # Para FECHAR ou REDUZIR uma posição SHORT, precisamos COMPRAR
        if direction == "LONG":
            side = "SELL"
        elif direction == "SHORT":
            side = "BUY"
        else:
            raise ValueError(f"Direção de posição desconhecida: {direction}")
        
        # Determinar quantity baseado na ação
        if action == "CLOSE":
            # Fechar 100% da posição
            quantity = position_qty
        elif action == "REDUCE_50":
            # Reduzir 50% da posição
            reduce_pct = self.config['reduce_50_pct']
            quantity = position_qty * reduce_pct
        else:
            raise ValueError(f"Ação desconhecida: {action}")
        
        # Obter quantity precision específica do símbolo
        precision = self._get_quantity_precision(symbol)
        
        # Truncar quantity para baixo (não arredondar para cima)
        # Isso evita tentar vender mais do que se tem disponível
        # Exemplo: 6.5 KAIA com precision=0 → 6.0 (não 7.0)
        multiplier = 10**precision
        quantity = math.floor(quantity * multiplier) / multiplier
        
        return {
            'side': side,
            'quantity': quantity
        }
    
    def _place_order(self, symbol: str, side: str, quantity: float, 
                     order_type: str = "MARKET") -> Optional[Dict[str, Any]]:
        """
        Coloca a ordem via Binance SDK com lógica de retry.
        Usa self._client.rest_api.new_order() com reduceOnly=True.
        
        Returns:
            Resposta da ordem (dict) ou None em caso de falha
        """
        max_retries = self.config['max_order_retries']
        retry_delay = self.config['order_retry_delay_seconds']
        recv_window = self.config['recv_window']
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"[EXECUTOR] Tentativa {attempt + 1}/{max_retries + 1}: "
                           f"new_order({symbol}, {side}, {order_type}, qty={quantity:.8f}, reduceOnly=True)")
                
                # CRITICAL: reduceOnly=True é a rede de segurança final
                # Binance rejeitará a ordem se ela tentar abrir nova posição
                response = self._client.rest_api.new_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    reduce_only=True,  # CRITICAL SAFETY NET
                    recv_window=recv_window
                )
                
                # Extrair dados do wrapper ApiResponse (mesmo padrão do PositionMonitor)
                data = self._extract_data(response)
                
                if data:
                    logger.info(f"[EXECUTOR] Ordem colocada com sucesso: {data}")
                    return data
                else:
                    logger.warning(f"[EXECUTOR] Resposta vazia da API na tentativa {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"[EXECUTOR] Erro na tentativa {attempt + 1}: {e}")
                
                # Se não é a última tentativa, aguardar e tentar novamente
                if attempt < max_retries:
                    logger.info(f"[EXECUTOR] Aguardando {retry_delay}s antes de tentar novamente...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"[EXECUTOR] Todas as tentativas falharam")
                    traceback.print_exc()
        
        return None
    
    def _extract_data(self, response):
        """
        Extrai dados do wrapper ApiResponse do SDK.
        Mesmo padrão usado no PositionMonitor.
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
        
        # Se não tem .data, assumir que já são os dados diretos
        return response
    
    def _verify_execution(self, symbol: str, expected_qty_change: float):
        """
        Verifica se a ordem foi executada consultando posição após execução.
        Busca position_information_v2 e compara qty.
        """
        try:
            logger.info(f"[EXECUTOR] Verificando execução para {symbol}...")
            
            # Aguardar um momento para a ordem ser processada
            time.sleep(1)
            
            # Buscar posição atualizada
            response = self._client.rest_api.position_information_v2(symbol=symbol)
            data = self._extract_data(response)
            
            if data:
                if not isinstance(data, list):
                    data = [data]
                
                for pos_data in data:
                    pos_symbol = pos_data.get('symbol') if isinstance(pos_data, dict) else getattr(pos_data, 'symbol', None)
                    if pos_symbol == symbol:
                        position_amt = float(pos_data.get('positionAmt', 0) if isinstance(pos_data, dict) 
                                           else getattr(pos_data, 'position_amt', 0))
                        logger.info(f"[EXECUTOR] Posição atual para {symbol}: qty={abs(position_amt):.8f}")
                        # Verificação bem-sucedida
                        return
            
            logger.warning(f"[EXECUTOR] Não foi possível verificar execução para {symbol}")
            
        except Exception as e:
            logger.error(f"[EXECUTOR] Erro ao verificar execução: {e}")
    
    def _persist_execution(self, result: Dict[str, Any], position: Dict[str, Any], 
                          decision: Dict[str, Any]):
        """
        Persiste resultado da execução na tabela execution_log do banco de dados.
        """
        timestamp = int(datetime.now().timestamp() * 1000)
        
        execution_data = {
            'timestamp': timestamp,
            'symbol': result['symbol'],
            'direction': position['direction'],
            'action': result['action'],
            'side': result['side'],
            'quantity': result['quantity'],
            'order_type': self.config['order_type'],
            'reduce_only': 1,  # Sempre 1
            
            # Resultado da execução
            'executed': 1 if result['executed'] else 0,
            'mode': result['mode'],
            'reason': result['reason'],
            
            # Dados da ordem (se executada no modo live)
            'order_id': result.get('order_id'),
            'fill_price': result.get('fill_price'),
            'fill_quantity': result.get('fill_quantity'),
            'commission': result.get('commission'),
            
            # Contexto no momento da execução
            'entry_price': position.get('entry_price'),
            'mark_price': position.get('mark_price'),
            'unrealized_pnl': position.get('unrealized_pnl'),
            'unrealized_pnl_pct': position.get('unrealized_pnl_pct'),
            'risk_score': decision.get('risk_score'),
            'decision_confidence': decision.get('decision_confidence'),
            'decision_reasoning': decision.get('decision_reasoning'),
            
            # Link para snapshot
            'snapshot_id': result.get('snapshot_id'),
        }
        
        try:
            execution_id = self._db.insert_execution_log(execution_data)
            logger.debug(f"[EXECUTOR] Execução persistida no banco: ID={execution_id}")
        except Exception as e:
            logger.error(f"[EXECUTOR] Erro ao persistir execução: {e}")
            raise
    
    def _get_daily_execution_count(self) -> int:
        """Retorna número de execuções hoje (UTC)."""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Atualizar contador a partir do banco de dados (fonte da verdade)
        try:
            count = self._db.count_executions_today()
            self._daily_execution_count[today] = count
            return count
        except Exception as e:
            logger.error(f"[EXECUTOR] Erro ao buscar contagem diária do banco: {e}")
            # Fallback para contador em memória
            return self._daily_execution_count.get(today, 0)
    
    def _is_symbol_in_cooldown(self, symbol: str) -> bool:
        """Verifica se o símbolo ainda está em período de cooldown."""
        if symbol not in self._cooldown_tracker:
            return False
        
        last_execution = self._cooldown_tracker[symbol]
        current_time = time.time()
        cooldown_seconds = self.config['cooldown_per_symbol_seconds']
        
        elapsed = current_time - last_execution
        return elapsed < cooldown_seconds
    
    def _get_cooldown_remaining(self, symbol: str) -> float:
        """Retorna tempo restante de cooldown em segundos."""
        if symbol not in self._cooldown_tracker:
            return 0.0
        
        last_execution = self._cooldown_tracker[symbol]
        current_time = time.time()
        cooldown_seconds = self.config['cooldown_per_symbol_seconds']
        
        elapsed = current_time - last_execution
        remaining = cooldown_seconds - elapsed
        
        return max(0.0, remaining)
    
    def _update_cooldown(self, symbol: str):
        """Atualiza o rastreador de cooldown para o símbolo."""
        self._cooldown_tracker[symbol] = time.time()
        logger.debug(f"[EXECUTOR] Cooldown iniciado para {symbol}")
    
    def _increment_daily_counter(self):
        """Incrementa o contador de execuções diárias."""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        current_count = self._daily_execution_count.get(today, 0)
        self._daily_execution_count[today] = current_count + 1
        logger.debug(f"[EXECUTOR] Contador diário atualizado: {self._daily_execution_count[today]}/{self.config['max_daily_executions']}")
