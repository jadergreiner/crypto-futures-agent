"""
Symbol configuration with playbook characteristics for each cryptocurrency.
"""

from typing import Dict, List, Any

SYMBOLS: Dict[str, Dict[str, Any]] = {
    "BTCUSDT": {
        "papel": "Líder de mercado. Define o ciclo macro.",
        "ciclo_proprio": "Halving → Acumulação → Bull Run → Distribuição → Bear Market",
        "correlacao_btc": 1.0,
        "beta_estimado": 1.0,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "halving_cycles",
            "institutional",
            "etf_flows",
            "inverse_dxy"
        ]
    },
    "ETHUSDT": {
        "papel": "Segunda maior. Ecossistema DeFi/NFT.",
        "ciclo_proprio": "Segue ciclo BTC com atraso de 2-6 semanas no topo/fundo",
        "correlacao_btc": [0.85, 0.95],
        "beta_estimado": 1.2,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "network_upgrades",
            "defi_tvl",
            "gas_fees",
            "staking_yield"
        ]
    },
    "SOLUSDT": {
        "papel": "Altcoin de alta performance. Ecossistema DeFi/memecoins.",
        "ciclo_proprio": "Amplifica movimentos do BTC. Lidera em fases de risk-on.",
        "correlacao_btc": [0.75, 0.90],
        "beta_estimado": 2.0,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "high_beta",
            "memecoin_ecosystem",
            "tvl_growth"
        ]
    },
    "BNBUSDT": {
        "papel": "Token utilitário da Binance. Queimas trimestrais.",
        "ciclo_proprio": "Ciclos de burn trimestral + ciclo geral cripto",
        "correlacao_btc": [0.80, 0.90],
        "beta_estimado": 1.1,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "quarterly_burn",
            "binance_ecosystem",
            "launchpad"
        ]
    },
    "DOGEUSDT": {
        "papel": "Memecoin líder. Alta influência de sentimento social.",
        "ciclo_proprio": "Surtos de hype → pump → dump. Segue BTC no macro.",
        "correlacao_btc": [0.50, 0.85],
        "beta_estimado": 2.5,
        "classificacao": "memecoin",
        "caracteristicas": [
            "social_sentiment",
            "elon_musk",
            "hype_driven"
        ]
    },
    "XRPUSDT": {
        "papel": "Foco institucional/pagamentos. Sensível a regulação.",
        "ciclo_proprio": "Regulação-driven + ciclo geral cripto",
        "correlacao_btc": [0.60, 0.80],
        "beta_estimado": 1.3,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "regulation_sensitive",
            "escrow_monthly",
            "payments"
        ]
    },
    "LTCUSDT": {
        "papel": "Silver to Bitcoin's gold. Halving próprio.",
        "ciclo_proprio": "Halving próprio + correlação forte com ciclo BTC",
        "correlacao_btc": [0.80, 0.92],
        "beta_estimado": 1.1,
        "classificacao": "alta_cap",
        "caracteristicas": [
            "own_halving",
            "payments",
            "stable_correlation"
        ]
    },
    "C98USDT": {
        "papel": "Token DeFi (Coin98). Multi-chain wallet/DeFi gateway.",
        "ciclo_proprio": "Segue ciclo altcoin geral. Sensível a narrativa DeFi.",
        "correlacao_btc": [0.50, 0.75],
        "beta_estimado": 3.0,
        "classificacao": "low_cap_defi",
        "caracteristicas": [
            "defi_narrative",
            "low_liquidity",
            "high_beta",
            "multi_chain"
        ]
    }
}

# List of all symbols for easy iteration
ALL_SYMBOLS: List[str] = list(SYMBOLS.keys())
