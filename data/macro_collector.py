"""
Macro economic data collector.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class MacroCollector:
    """
    Collects macro economic data from various sources.
    Implements Fear & Greed Index and BTC Dominance (free APIs).
    Other endpoints as placeholders with clear interfaces.
    """
    
    def __init__(self):
        """Initialize macro collector."""
        self.session = requests.Session()
    
    def fetch_fear_greed_index(self) -> Dict[str, Any]:
        """
        Fetch Fear & Greed Index from alternative.me.
        
        Returns:
            Fear & Greed data
        """
        try:
            response = self.session.get('https://api.alternative.me/fng/?limit=1', timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and 'data' in data and len(data['data']) > 0:
                fng_data = data['data'][0]
                return {
                    'fear_greed_value': int(fng_data.get('value', 50)),
                    'fear_greed_classification': fng_data.get('value_classification', 'Neutral')
                }
            
            logger.warning("Fear & Greed Index returned empty data")
            return {'fear_greed_value': 50, 'fear_greed_classification': 'Neutral'}
            
        except Exception as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            return {'fear_greed_value': 50, 'fear_greed_classification': 'Neutral'}
    
    def fetch_btc_dominance(self) -> Dict[str, Any]:
        """
        Fetch BTC dominance from CoinGecko.
        
        Returns:
            BTC dominance data
        """
        try:
            response = self.session.get('https://api.coingecko.com/api/v3/global', timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and 'data' in data:
                global_data = data['data']
                current_dominance = global_data.get('market_cap_percentage', {}).get('btc', 0)
                
                return {
                    'btc_dominance': round(current_dominance, 2),
                    'btc_dominance_change_pct': 0.0  # Would need historical data for change
                }
            
            logger.warning("BTC dominance returned empty data")
            return {'btc_dominance': 50.0, 'btc_dominance_change_pct': 0.0}
            
        except Exception as e:
            logger.error(f"Failed to fetch BTC dominance: {e}")
            return {'btc_dominance': 50.0, 'btc_dominance_change_pct': 0.0}
    
    def fetch_dxy(self) -> Dict[str, Any]:
        """
        Fetch DXY (US Dollar Index).
        
        PLACEHOLDER: Would integrate with Yahoo Finance or FRED API.
        
        Returns:
            DXY data
        """
        logger.debug("DXY fetch is placeholder - returning neutral values")
        return {
            'dxy': 100.0,
            'dxy_change_pct': 0.0
        }
    
    def fetch_stablecoin_flow(self) -> Dict[str, Any]:
        """
        Fetch stablecoin exchange flow.
        
        PLACEHOLDER: Would integrate with DefiLlama or similar.
        
        Returns:
            Stablecoin flow data
        """
        logger.debug("Stablecoin flow fetch is placeholder - returning neutral values")
        return {
            'stablecoin_exchange_flow_net': 0.0
        }
    
    def fetch_fed_rate(self) -> Dict[str, Any]:
        """
        Fetch Federal Funds Rate.
        
        PLACEHOLDER: Would integrate with FRED API.
        
        Returns:
            Fed rate data
        """
        logger.debug("Fed rate fetch is placeholder - returning neutral values")
        return {
            'fed_rate': 5.0
        }
    
    def fetch_cpi(self) -> Dict[str, Any]:
        """
        Fetch CPI (Consumer Price Index) data.
        
        PLACEHOLDER: Would integrate with FRED API or similar.
        
        Returns:
            CPI data
        """
        logger.debug("CPI fetch is placeholder - returning neutral values")
        return {
            'cpi_actual': 3.0,
            'cpi_expected': 3.0,
            'cpi_surprise': 0.0
        }
    
    def fetch_all_macro(self) -> Dict[str, Any]:
        """
        Fetch all macro data.
        
        Returns:
            Consolidated macro data
        """
        result = {
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        try:
            # Fully implemented
            result.update(self.fetch_fear_greed_index())
            result.update(self.fetch_btc_dominance())
            
            # Placeholders
            result.update(self.fetch_dxy())
            result.update(self.fetch_stablecoin_flow())
            result.update(self.fetch_fed_rate())
            result.update(self.fetch_cpi())
            
            logger.info("Collected all macro data")
            
        except Exception as e:
            logger.error(f"Error collecting macro data: {e}")
            # Return neutral defaults
            result.update({
                'dxy': 100.0, 'dxy_change_pct': 0.0,
                'fed_rate': 5.0,
                'cpi_actual': 3.0, 'cpi_expected': 3.0, 'cpi_surprise': 0.0,
                'fear_greed_value': 50, 'fear_greed_classification': 'Neutral',
                'btc_dominance': 50.0, 'btc_dominance_change_pct': 0.0,
                'stablecoin_exchange_flow_net': 0.0
            })
        
        return result
