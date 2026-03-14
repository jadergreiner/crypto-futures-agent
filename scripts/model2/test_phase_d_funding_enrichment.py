"""
Demonstração de integração: Feature Enricher + BinanceFundingCollector
Propósito: Validar que features são enriquecidas com dados de funding rates e OI
"""

import json
import sqlite3
import sys
from pathlib import Path

# Adicionar root ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.model2.binance_funding_collector import BinanceFundingCollector
from scripts.model2.feature_enricher import FeatureEnricher


def demo_enrichment_with_funding():
    """Demo: enriquecer features com funding data."""
    
    # Inicializar collector com dados simulados
    collector = BinanceFundingCollector()
    
    # Simular dados de mercado (funding + OI)
    import time
    now_ms = int(time.time() * 1000)
    
    print("1. Simulando dados de mercado...")
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        # Funding rates
        for i in range(8):
            ts = now_ms - (i * 3600 * 1000)
            fr = 0.00002 if i % 2 == 0 else -0.00001
            lev = 3.5 + (i * 0.1)
            collector.store_funding_rate_simulation(symbol, ts, fr, lev)
        
        # Open interest
        for i in range(4):
            ts = now_ms - (i * 6 * 3600 * 1000)
            oi = 100000 + (i * 5000)
            oi_usd = oi * 30000
            collector.store_open_interest_simulation(symbol, ts, oi, oi_usd)
    
    print("   ✓ 8 funding rates + 4 OI por símbolo armazenados")
    
    # Features base (simuladas)
    base_features = {
        "latest_candle": {
            "open": 42000.0,
            "high": 42500.0,
            "low": 41500.0,
            "close": 42250.0,
            "volume": 1000.0,
        },
        "symbol": "BTCUSDT",
        "timeframe": "H1",
    }
    
    print("\n2. Enriquecendo features com funding data...")
    enriched = FeatureEnricher.enrich_with_funding_data(
        base_features,
        "BTCUSDT",
        funding_collector=collector
    )
    
    # Exibir result
    print("   Features enriquecidas:")
    print(json.dumps(enriched, indent=2, default=str))
    
    # Validar campos
    assert "funding_rates" in enriched, "Funding rates não adicionadas!"
    assert "open_interest" in enriched, "Open interest não adicionado!"
    assert enriched["funding_rates"]["sentiment_24h"] in ["bullish", "neutral", "bearish"]
    assert enriched["open_interest"]["oi_sentiment"] in ["accumulating", "distributing", "neutral"]
    
    print("\n3. Validação:")
    print(f"   ✓ Funding rate atual: {enriched['funding_rates']['latest_rate']}")
    print(f"   ✓ Sentiment (24h): {enriched['funding_rates']['sentiment_24h']}")
    print(f"   ✓ OI atual: {enriched['open_interest']['current_oi']}")
    print(f"   ✓ OI sentiment: {enriched['open_interest']['oi_sentiment']}")
    
    # Salvar resultado
    with open("results/model2/phase_d_enrichment_demo.json", "w") as f:
        json.dump(enriched, f, indent=2, default=str)
    
    print("\n4. Resultado salvo em: results/model2/phase_d_enrichment_demo.json")
    print("\n[OK] Integração Phase D funcionando corretamente")


if __name__ == "__main__":
    demo_enrichment_with_funding()
