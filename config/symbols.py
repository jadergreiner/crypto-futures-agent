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
    },
    "0GUSDT": {
        "papel": "Token da rede 0G (Zero Gravity). Infraestrutura AI/data modular.",
        "ciclo_proprio": "Segue narrativa AI/infra. Amplifica movimentos de risk-on altcoin.",
        "correlacao_btc": [0.40, 0.70],
        "beta_estimado": 3.5,
        "classificacao": "low_cap_ai_infra",
        "caracteristicas": [
            "ai_narrative",
            "modular_data",
            "low_liquidity",
            "high_beta"
        ]
    },
    "KAIAUSDT": {
        "papel": "Token Kaia. Layer 1 focado em messaging/social integrado (ex-Klaytn+LINE).",
        "ciclo_proprio": "Sensivel a adocao em Asia. Ciclo altcoin geral + parcerias messaging.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.8,
        "classificacao": "low_cap_l1",
        "caracteristicas": [
            "asia_adoption",
            "messaging_integration",
            "social_network",
            "high_beta"
        ]
    },
    "AXLUSDT": {
        "papel": "Axelar. Protocolo de interoperabilidade cross-chain.",
        "ciclo_proprio": "Segue narrativa cross-chain/interop. Beneficia de multichain expansion.",
        "correlacao_btc": [0.50, 0.80],
        "beta_estimado": 2.5,
        "classificacao": "low_cap_interop",
        "caracteristicas": [
            "cross_chain",
            "interoperability",
            "defi_infrastructure",
            "high_beta"
        ]
    },
    "NILUSDT": {
        "papel": "Nillion. Rede de computacao descentralizada focada em dados privados.",
        "ciclo_proprio": "Segue narrativa privacy/AI compute. Novo, alta volatilidade.",
        "correlacao_btc": [0.35, 0.65],
        "beta_estimado": 4.0,
        "classificacao": "low_cap_privacy_compute",
        "caracteristicas": [
            "privacy_compute",
            "decentralized_data",
            "ai_narrative",
            "very_high_beta",
            "low_liquidity"
        ]
    },
    "FOGOUSDT": {
        "papel": "Fogo. Layer 1 de alta performance (fork SUI) com foco em velocidade.",
        "ciclo_proprio": "Segue narrativa L1 alta performance. Amplifica movimentos de mercado.",
        "correlacao_btc": [0.40, 0.70],
        "beta_estimado": 3.8,
        "classificacao": "low_cap_l1_performance",
        "caracteristicas": [
            "high_performance_l1",
            "sui_fork",
            "speed_narrative",
            "very_high_beta",
            "low_liquidity"
        ]
    },
    "KNCUSDT": {
        "papel": "Kyber Network Crystal. Token de infraestrutura DeFi/DEX agregadora.",
        "ciclo_proprio": "Segue narrativa DeFi e liquidez on-chain. Sensível a ciclos de altseason.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.7,
        "classificacao": "mid_cap_defi",
        "caracteristicas": [
            "defi_liquidity",
            "dex_aggregator",
            "altseason_sensitive",
            "high_beta"
        ]
    },
    "GMTUSDT": {
        "papel": "STEPN (GMT). Token GameFi focado em move-to-earn.",
        "ciclo_proprio": "Segue narrativa GameFi e altcoin. Alta sensibilidade a sentimento de varejo.",
        "correlacao_btc": [0.40, 0.70],
        "beta_estimado": 3.0,
        "classificacao": "mid_cap_gamefi",
        "caracteristicas": [
            "gamefi_narrative",
            "move_to_earn",
            "retail_sentiment",
            "high_beta"
        ]
    },
    "ICPUSDT": {
        "papel": "Internet Computer (ICP). Infraestrutura de computação descentralizada/Web3.",
        "ciclo_proprio": "Segue ciclo altcoin com sensibilidade a narrativas de infraestrutura e adoção de dApps.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.6,
        "classificacao": "mid_cap_infra",
        "caracteristicas": [
            "web3_infrastructure",
            "dapp_adoption",
            "high_beta",
            "altseason_sensitive"
        ]
    },
    "OPUSDT": {
        "papel": "Optimism (OP). Token de governança/ecossistema Layer 2 Ethereum.",
        "ciclo_proprio": "Segue narrativa L2 e escalabilidade Ethereum, com alta sensibilidade a altseason.",
        "correlacao_btc": [0.50, 0.80],
        "beta_estimado": 2.7,
        "classificacao": "mid_cap_l2",
        "caracteristicas": [
            "ethereum_l2",
            "scaling_narrative",
            "ecosystem_incentives",
            "high_beta"
        ]
    },
    "BELUSDT": {
        "papel": "Bella Protocol (BEL). Token DeFi de otimização de rendimento e produtos on-chain.",
        "ciclo_proprio": "Segue narrativa DeFi/altseason com maior sensibilidade a fluxo especulativo.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_defi",
        "caracteristicas": [
            "defi_narrative",
            "yield_optimization",
            "altseason_sensitive",
            "high_beta"
        ]
    },
    "BARDUSDT": {
        "papel": "Bard Protocol (BARD). Token de baixa/média capitalização com dinâmica especulativa.",
        "ciclo_proprio": "Segue ciclo altcoin com forte sensibilidade a narrativas e liquidez de mercado.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.1,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "speculative_flow",
            "narrative_sensitive",
            "high_beta",
            "low_liquidity"
        ]
    },
    "JASMYUSDT": {
        "papel": "JasmyCoin (JASMY). Token focado em dados/IoT com dinâmica de varejo.",
        "ciclo_proprio": "Segue ciclo altcoin e narrativa de dados/IoT, com alta sensibilidade a momentum.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 2.9,
        "classificacao": "mid_cap_data_iot",
        "caracteristicas": [
            "data_narrative",
            "iot_theme",
            "high_beta",
            "retail_momentum"
        ]
    },
    "FIGHTUSDT": {
        "papel": "Token de nicho. Alta volatilidade e sensível a eventos de mercado.",
        "ciclo_proprio": "Narrativa de nicho. Amplifica movimentos de alta e baixa.",
        "correlacao_btc": [0.30, 0.60],
        "beta_estimado": 4.0,
        "classificacao": "niche_token",
        "caracteristicas": [
            "high_volatility",
            "event_sensitive",
            "low_liquidity",
            "speculative"
        ]
    }
}

# List of all symbols for easy iteration
ALL_SYMBOLS: List[str] = list(SYMBOLS.keys())
