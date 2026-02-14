"""
Template base para playbooks de moedas.
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from config.symbols import SYMBOLS

logger = logging.getLogger(__name__)


class BasePlaybook(ABC):
    """
    Classe base para playbooks específicos de moedas.
    Define interface comum e métodos padrão.
    """
    
    def __init__(self, symbol: str):
        """
        Inicializa playbook.
        
        Args:
            symbol: Símbolo da moeda (ex: "BTCUSDT")
        """
        self.symbol = symbol
        self.config = SYMBOLS.get(symbol, {})
        self.papel = self.config.get('papel', '')
        self.ciclo = self.config.get('ciclo_proprio', '')
        self.correlacao_btc = self.config.get('correlacao_btc', 0.0)
        self.beta = self.config.get('beta_estimado', 1.0)
        self.classificacao = self.config.get('classificacao', '')
        self.caracteristicas = self.config.get('caracteristicas', [])
        
        logger.info(f"Playbook initialized for {symbol}")
    
    @abstractmethod
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Retorna ajustes específicos da moeda no score de confluência.
        
        Args:
            context: Contexto atual (indicadores, smc, macro, etc.)
            
        Returns:
            Dicionário com ajustes (+/- pontos de confluência)
        """
        pass
    
    @abstractmethod
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Retorna ajustes de risco específicos da moeda.
        
        Args:
            context: Contexto atual
            
        Returns:
            Dicionário com multiplicadores de risco
        """
        pass
    
    @abstractmethod
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase atual do ciclo específico da moeda.
        
        Args:
            current_data: Dados atuais
            
        Returns:
            Nome da fase do ciclo
        """
        pass
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: Optional[str] = None) -> bool:
        """
        Determina se deve operar esta moeda nas condições atuais.
        
        Args:
            market_regime: Regime de mercado ("RISK_ON", "RISK_OFF", "NEUTRO")
            d1_bias: Bias D1 da própria moeda
            btc_bias: Bias D1 do BTC (opcional)
            
        Returns:
            True se deve operar
        """
        # Regra geral: não operar em bias neutro
        if d1_bias == "NEUTRO":
            return False
        
        # Moedas de alta cap podem operar em qualquer regime
        if self.classificacao == "alta_cap":
            return True
        
        # Memecoins e high beta: apenas em risk-on
        if self.classificacao == "memecoin" or self.beta >= 2.0:
            if market_regime != "RISK_ON":
                logger.debug(f"{self.symbol}: Skipping (high beta/memecoin in {market_regime})")
                return False
        
        return True
    
    def calculate_position_size_multiplier(self, context: Dict[str, Any]) -> float:
        """
        Calcula multiplicador para tamanho da posição baseado nas características da moeda.
        
        Args:
            context: Contexto atual
            
        Returns:
            Multiplicador (0.5 = metade do tamanho, 1.5 = 50% maior)
        """
        multiplier = 1.0
        
        # Ajustar por beta
        if self.beta > 2.0:
            multiplier *= 0.7  # Reduzir tamanho para high beta
        elif self.beta < 0.8:
            multiplier *= 1.2  # Aumentar para baixo beta
        
        # Ajustar por volatilidade
        if 'atr_pct' in context:
            atr_pct = context['atr_pct']
            if atr_pct > 5:  # Alta volatilidade
                multiplier *= 0.8
            elif atr_pct < 2:  # Baixa volatilidade
                multiplier *= 1.1
        
        return multiplier
    
    def get_info(self) -> Dict[str, Any]:
        """
        Retorna informações do playbook.
        
        Returns:
            Dicionário com informações
        """
        return {
            'symbol': self.symbol,
            'papel': self.papel,
            'ciclo': self.ciclo,
            'correlacao_btc': self.correlacao_btc,
            'beta': self.beta,
            'classificacao': self.classificacao,
            'caracteristicas': self.caracteristicas
        }
