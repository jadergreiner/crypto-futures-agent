"""
M2-016.3 Phase D.2: Demonstração de Integração Completa.

Fluxo:
1. Daemon coleta funding rates + open interest via API
2. Feature enricher consulta dados coletados
3. Training episodes enriquecidas com contexto de mercado real
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.model2.binance_funding_daemon import BinanceFundingDaemon
from scripts.model2.feature_enricher import FeatureEnricher
from scripts.model2.binance_funding_api_client import BinanceFundingAPIClient


def demo_phase_d2_integration():
    """Demo completo: API → Daemon → Features → Enrichment."""
    
    print("=" * 70)
    print("M2-016.3 Phase D.2: Integração API Binance Real (Mock Demo)")
    print("=" * 70)
    
    # 1. Inicializar daemon
    print("\n1. DAEMON INITIALIZATION")
    print("-" * 70)
    daemon = BinanceFundingDaemon(use_mock=True)
    print(f"   Daemon criado para {len(daemon.symbols)} símbolos")
    
    # 2. Executar coleta (substitui simulador anterior)
    print("\n2. COLLECTING DATA VIA DAEMON")
    print("-" * 70)
    result = daemon.run_once(price_map={s: 40000 for s in daemon.symbols})
    print(f"   Collected: {result['fr_collected']} FR, {result['oi_collected']} OI")
    
    # 3. Verificar dados armazenados
    print("\n3. VERIFICATION: Data stored in SQLite")
    print("-" * 70)
    stats = daemon.get_collection_stats()
    print(f"   FR total: {stats['funding_rates_total']} ({stats['funding_rate_symbols']} symbols)")
    print(f"   OI total: {stats['open_interest_total']} ({stats['open_interest_symbols']} symbols)")
    
    # 4. Enriquecer features usando dados API
    print("\n4. ENRICHING FEATURES WITH API DATA")
    print("-" * 70)
    
    api_client = BinanceFundingAPIClient(use_mock=False)  # Query dados persistidos
    
    base_features = {
        "symbol": "BTCUSDT",
        "timeframe": "H1",
        "latest_candle": {
            "open": 42000.0,
            "high": 42500.0,
            "low": 41500.0,
            "close": 42250.0,
        }
    }
    
    enriched = FeatureEnricher.enrich_with_funding_data(
        base_features,
        "BTCUSDT",
        funding_collector=api_client
    )
    
    print(f"   ✓ Features enriquecidas com API data:")
    if "funding_rates" in enriched:
        print(f"     - FR: {enriched['funding_rates']['latest_rate']}")
        print(f"     - Sentiment: {enriched['funding_rates']['sentiment_24h']}")
    if "open_interest" in enriched:
        print(f"     - OI: {enriched['open_interest']['current_oi']}")
        print(f"     - OI Sentiment: {enriched['open_interest']['oi_sentiment']}")
    
    # 5. Salvar resultado completo
    print("\n5. SAVING COMPLETE ENRICHED FEATURES")
    print("-" * 70)
    
    result_file = "results/model2/phase_d2_integration_demo.json"
    with open(result_file, "w") as f:
        json.dump(enriched, f, indent=2, default=str)
    
    print(f"   Salvo em: {result_file}")
    
    # 6. Fluxo esperado na produção
    print("\n6. PRODUCTION FLOW (Roadmap)")
    print("-" * 70)
    print("""
   Baseline (Fase D):
   - Feature enricher com simulator (demo)
   
   Phase D.2 (AGORA):
   - Daemon coletando API real
   - Feature enricher consultando dados persistidos
   
   Phase D.3 (Próximo):
   - Integrar com persist_training_episodes.py
   - Episodes recebem features com funding data real
   - RL treina com contexto completo de mercado
   
   Phase D.4:
   - Análise de correlação FR/OI vs performance RL
   - Tune reward weights based on funding sentiment
   """)
    
    print("\n" + "=" * 70)
    print("[OK] Phase D.2 Integration Demo funcionando")
    print("=" * 70)


if __name__ == "__main__":
    demo_phase_d2_integration()
