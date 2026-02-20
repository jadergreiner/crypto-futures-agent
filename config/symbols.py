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
    "SXTUSDT": {
        "papel": "Space and Time (SXT). Token orientado a infraestrutura de dados e narrativa de Web3/AI.",
        "ciclo_proprio": "Sensível a fluxo de narrativa tecnológica e rotação de altcoins, com volatilidade elevada.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.2,
        "classificacao": "mid_cap_data_infra",
        "caracteristicas": [
            "data_infrastructure",
            "narrative_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "SIGNUSDT": {
        "papel": "Token de narrativa emergente com comportamento de alta volatilidade e fluxo especulativo.",
        "ciclo_proprio": "Movimentos acelerados em rotação de altcoins, sensível a liquidez e eventos.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.4,
        "classificacao": "mid_cap_speculative",
        "caracteristicas": [
            "high_volatility",
            "narrative_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "APEUSDT": {
        "papel": "ApeCoin (APE). Token de ecossistema Web3/NFT com dinâmica especulativa e alta sensibilidade a fluxo.",
        "ciclo_proprio": "Segue ciclo de altcoins com forte impacto de narrativa de mercado e liquidez.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.0,
        "classificacao": "mid_cap_web3",
        "caracteristicas": [
            "web3_narrative",
            "high_volatility",
            "high_beta",
            "speculative"
        ]
    },
    "IDUSDT": {
        "papel": "SPACE ID (ID). Token de infraestrutura de identidade Web3, com dinâmica de altcoin e fluxo especulativo.",
        "ciclo_proprio": "Sensível a narrativa Web3 e rotação de capital em tokens de média capitalização.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.1,
        "classificacao": "mid_cap_web3_infra",
        "caracteristicas": [
            "web3_narrative",
            "identity_infrastructure",
            "high_beta",
            "speculative"
        ]
    },
    "4USDT": {
        "papel": "Token alfanumérico de alta volatilidade e baixa previsibilidade, sensível a liquidez de curto prazo.",
        "ciclo_proprio": "Oscilação acelerada em ciclos de altcoins, com reação forte a fluxo especulativo.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 3.8,
        "classificacao": "high_beta_speculative",
        "caracteristicas": [
            "high_volatility",
            "low_liquidity",
            "high_beta",
            "speculative"
        ]
    },
    "ASTERUSDT": {
        "papel": "Token de narrativa emergente com dinâmica de alta volatilidade e sensibilidade a eventos de mercado.",
        "ciclo_proprio": "Movimentos rápidos em ciclos de altcoins, com forte dependência de fluxo de liquidez.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.5,
        "classificacao": "high_beta_speculative",
        "caracteristicas": [
            "high_volatility",
            "narrative_sensitive",
            "event_sensitive",
            "speculative"
        ]
    },
    "ZAMAUSDT": {
        "papel": "Token de infraestrutura criptográfica com perfil especulativo e volatilidade elevada.",
        "ciclo_proprio": "Sensível a narrativas técnicas e rotação de capital em altcoins.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.3,
        "classificacao": "mid_cap_infra",
        "caracteristicas": [
            "infra_narrative",
            "high_volatility",
            "high_beta",
            "speculative"
        ]
    },
    "ANKRUSDT": {
        "papel": "Ankr (ANKR). Token de infraestrutura Web3, com liquidez moderada e dinâmica de altcoin.",
        "ciclo_proprio": "Acompanha ciclos de infraestrutura Web3 com sensibilidade a momentum de mercado.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_web3_infra",
        "caracteristicas": [
            "web3_infrastructure",
            "momentum_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "DOTUSDT": {
        "papel": "Polkadot (DOT). Token de camada 1 com liquidez ampla e ciclo próprio ligado ao ecossistema multichain.",
        "ciclo_proprio": "Segue ciclos macro de L1s e rotação de capital entre grandes altcoins.",
        "correlacao_btc": [0.45, 0.80],
        "beta_estimado": 2.2,
        "classificacao": "large_cap_l1",
        "caracteristicas": [
            "layer1",
            "multichain_ecosystem",
            "broad_liquidity",
            "trend_sensitive"
        ]
    },
    "SANDUSDT": {
        "papel": "The Sandbox (SAND). Token de metaverso/gaming com comportamento cíclico e sensibilidade a narrativa.",
        "ciclo_proprio": "Movimentos fortes em ciclos de narrativa gaming e varejo.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 2.9,
        "classificacao": "mid_cap_gaming",
        "caracteristicas": [
            "gaming_narrative",
            "retail_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "AVAXUSDT": {
        "papel": "Avalanche (AVAX). Token de camada 1 com alta liquidez e volatilidade relevante.",
        "ciclo_proprio": "Acompanha ciclos de L1 e condições gerais de risco do mercado cripto.",
        "correlacao_btc": [0.45, 0.80],
        "beta_estimado": 2.4,
        "classificacao": "large_cap_l1",
        "caracteristicas": [
            "layer1",
            "high_liquidity",
            "high_beta",
            "trend_sensitive"
        ]
    },
    "TRXUSDT": {
        "papel": "TRON (TRX). Token de infraestrutura com liquidez ampla e dinâmica de grande altcoin.",
        "ciclo_proprio": "Acompanha ciclos macro do mercado com sensibilidade moderada a risco.",
        "correlacao_btc": [0.50, 0.85],
        "beta_estimado": 1.9,
        "classificacao": "large_cap_infra",
        "caracteristicas": [
            "high_liquidity",
            "infrastructure",
            "trend_sensitive",
            "market_beta"
        ]
    },
    "GRTUSDT": {
        "papel": "The Graph (GRT). Token de indexação Web3 com perfil de altcoin de infraestrutura.",
        "ciclo_proprio": "Sensível a narrativas Web3 e rotação de capital em mid caps.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 2.7,
        "classificacao": "mid_cap_web3_infra",
        "caracteristicas": [
            "web3_infrastructure",
            "narrative_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "WLDUSDT": {
        "papel": "Worldcoin (WLD). Token de alta atenção de mercado e volatilidade elevada.",
        "ciclo_proprio": "Movimentos acelerados por narrativa e fluxo de risco.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.2,
        "classificacao": "high_beta_narrative",
        "caracteristicas": [
            "high_volatility",
            "narrative_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "METUSDT": {
        "papel": "Token de média capitalização com dinâmica especulativa e volatilidade relevante.",
        "ciclo_proprio": "Sensível a rotação de altcoins e liquidez intradiária.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.1,
        "classificacao": "mid_cap_speculative",
        "caracteristicas": [
            "high_volatility",
            "low_liquidity",
            "high_beta",
            "speculative"
        ]
    },
    "XAIUSDT": {
        "papel": "XAI. Token ligado a narrativa de gaming/infra com comportamento volátil.",
        "ciclo_proprio": "Oscila com narrativa setorial e fluxo de risco em altcoins.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.0,
        "classificacao": "mid_cap_gaming_infra",
        "caracteristicas": [
            "gaming_narrative",
            "narrative_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "SNXUSDT": {
        "papel": "Synthetix (SNX). Token DeFi com histórico de alta volatilidade.",
        "ciclo_proprio": "Reage fortemente a ciclos DeFi e liquidez de mercado.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 2.9,
        "classificacao": "mid_cap_defi",
        "caracteristicas": [
            "defi_narrative",
            "high_volatility",
            "high_beta",
            "speculative"
        ]
    },
    "BLURUSDT": {
        "papel": "BLUR. Token relacionado ao ecossistema NFT com dinâmica especulativa.",
        "ciclo_proprio": "Movimentos rápidos conforme narrativa NFT e fluxo varejo.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.3,
        "classificacao": "mid_cap_nft",
        "caracteristicas": [
            "nft_narrative",
            "high_volatility",
            "high_beta",
            "speculative"
        ]
    },
    "ZEREBROUSDT": {
        "papel": "Token de nicho de alta volatilidade e baixa previsibilidade.",
        "ciclo_proprio": "Sensível a eventos e fluxo especulativo de curto prazo.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 3.9,
        "classificacao": "niche_token",
        "caracteristicas": [
            "high_volatility",
            "low_liquidity",
            "event_sensitive",
            "speculative"
        ]
    },
    "XMRUSDT": {
        "papel": "Monero (XMR). Token de privacidade com liquidez moderada e comportamento próprio.",
        "ciclo_proprio": "Correlação parcial ao mercado amplo, com dinâmica idiossincrática.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 2.1,
        "classificacao": "large_cap_privacy",
        "caracteristicas": [
            "privacy_token",
            "medium_liquidity",
            "trend_sensitive",
            "market_beta"
        ]
    },
    "ZENUSDT": {
        "papel": "Horizen (ZEN). Token de infraestrutura/privacy com volatilidade elevada.",
        "ciclo_proprio": "Segue ciclos de altcoins com sensibilidade a sentimento de risco.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_infra",
        "caracteristicas": [
            "privacy_infrastructure",
            "high_beta",
            "medium_liquidity",
            "speculative"
        ]
    },
    "DOLOUSDT": {
        "papel": "Token de média/baixa capitalização com dinâmica especulativa e volatilidade alta.",
        "ciclo_proprio": "Sensível a eventos, narrativa e liquidez de curto prazo.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 3.6,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "high_volatility",
            "event_sensitive",
            "high_beta",
            "speculative"
        ]
    },
    "DASHUSDT": {
        "papel": "Dash (DASH). Token legacy com liquidez moderada e dinâmica própria.",
        "ciclo_proprio": "Acompanha tendência do mercado com menor amplitude que mid caps.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 2.0,
        "classificacao": "mid_cap_payment",
        "caracteristicas": [
            "payment_token",
            "medium_liquidity",
            "trend_sensitive",
            "market_beta"
        ]
    },
    "XAGUSDT": {
        "papel": "Par temático de prata (XAG) tokenizado, com comportamento sensível a macro e liquidez cripto.",
        "ciclo_proprio": "Pode divergir de altcoins por influência de ativos reais e sentimento macro.",
        "correlacao_btc": [0.20, 0.55],
        "beta_estimado": 2.3,
        "classificacao": "tokenized_macro_asset",
        "caracteristicas": [
            "macro_sensitive",
            "event_sensitive",
            "medium_liquidity",
            "speculative"
        ]
    },
    "LAUSDT": {
        "papel": "Token de baixa/média capitalização com elevada sensibilidade a fluxo especulativo.",
        "ciclo_proprio": "Movimentos abruptos em ciclos de risco e baixa liquidez.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 3.7,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "high_volatility",
            "low_liquidity",
            "high_beta",
            "speculative"
        ]
    },
    "ZKPUSDT": {
        "papel": "Token ligado a narrativa zero-knowledge com comportamento de alta volatilidade.",
        "ciclo_proprio": "Sensível a narrativa técnica e rotação de capital em altcoins de infraestrutura.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.4,
        "classificacao": "mid_cap_zk_infra",
        "caracteristicas": [
            "zk_narrative",
            "narrative_sensitive",
            "high_beta",
            "speculative"
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
    },
    "ZKUSDT": {
        "papel": "ZK (Infraestrutura de privacidade). Token de narrativa zero-knowledge commitment.",
        "ciclo_proprio": "Sensível a adoção de protocolo e narrativa de privacidade/escalabilidade.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.2,
        "classificacao": "mid_cap_zk_infra",
        "caracteristicas": [
            "zk_narrative",
            "privacy_infrastructure",
            "high_beta",
            "narrative_sensitive"
        ]
    },
    "1000WHYUSDT": {
        "papel": "1000WHY. Token de meme/comunidade com dinâmica especulativa.",
        "ciclo_proprio": "Movimentos de hype e participação comunitária. Altamente volátil.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 4.2,
        "classificacao": "low_cap_memecoin",
        "caracteristicas": [
            "memecoin_narrative",
            "community_driven",
            "very_high_beta",
            "speculative"
        ]
    },
    "XIAUSDT": {
        "papel": "XAI. Token de infraestrutura/gaming com foco em AI.",
        "ciclo_proprio": "Sensível a narrativa de AI e adoção em gaming/aplicações.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 3.0,
        "classificacao": "mid_cap_ai_narrative",
        "caracteristicas": [
            "ai_narrative",
            "gaming_integration",
            "high_beta",
            "narrative_sensitive"
        ]
    },
    "GTCUSDT": {
        "papel": "Gitcoin (GTC). Token de infraestrutura/governança focado em funding público.",
        "ciclo_proprio": "Sensível a ciclos de funding Web3 e governança descentralizada.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_web3_infra",
        "caracteristicas": [
            "web3_infrastructure",
            "governance",
            "high_beta",
            "altseason_sensitive"
        ]
    },
    "CELOUSDT": {
        "papel": "Celo (CELO). Layer 1 orientado a pagamentos móveis.",
        "ciclo_proprio": "Ciclo de adoção em regiões emergentes. Segue narrativa de inclusão financeira.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.7,
        "classificacao": "mid_cap_l1_mobile",
        "caracteristicas": [
            "mobile_payments",
            "emerging_markets",
            "high_beta",
            "altseason_sensitive"
        ]
    },
    "HYPERUSDT": {
        "papel": "Hyper. Token com dinâmica de alta volatilidade e narrativa em desenvolvimento.",
        "ciclo_proprio": "Seguidor de ciclos de alternativo. Alta sensibilidade a liquidez e momentum.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.5,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "high_volatility",
            "low_liquidity",
            "very_high_beta",
            "speculative"
        ]
    },
    "MTLUSDT": {
        "papel": "Metal (MTL). Token de infraestrutura de IoT e dados.",
        "ciclo_proprio": "Sensível a narrativa IoT e segurança de dados.",
        "correlacao_btc": [0.40, 0.70],
        "beta_estimado": 2.9,
        "classificacao": "mid_cap_iot_infra",
        "caracteristicas": [
            "iot_infrastructure",
            "data_security",
            "high_beta",
            "narrative_sensitive"
        ]
    },
    "POLYXUSDT": {
        "papel": "Polymath (POLYX). Token de infraestrutura para tokens de segurança.",
        "ciclo_proprio": "Sensível a adoção de securities tokens e regulação cripto.",
        "correlacao_btc": [0.40, 0.75],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_securities_infra",
        "caracteristicas": [
            "securities_tokens",
            "regulatory_sensitive",
            "high_beta",
            "compliance_focused"
        ]
    },
    "1000BONKUSDT": {
        "papel": "1000BONK. Memecoin com dinâmica comunitária elevada.",
        "ciclo_proprio": "Ciclos de pump-dump baseados em comunidade e hype social.",
        "correlacao_btc": [0.20, 0.55],
        "beta_estimado": 4.5,
        "classificacao": "low_cap_memecoin",
        "caracteristicas": [
            "memecoin_narrative",
            "social_hype",
            "extremely_high_beta",
            "speculative"
        ]
    },
    "FILUSDT": {
        "papel": "Filecoin (FIL). Infraestrutura de armazenamento descentralizado.",
        "ciclo_proprio": "Sensível a narrativa de armazenamento descentralizado e Web3 infra.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.5,
        "classificacao": "mid_cap_storage_infra",
        "caracteristicas": [
            "decentralized_storage",
            "web3_infrastructure",
            "data_narrative",
            "high_beta"
        ]
    },
    "GRTUSDT": {
        "papel": "The Graph (GRT). Token de protocolo de indexação descentralizada.",
        "ciclo_proprio": "Segue narrativa de infraestrutura DeFi e indexação de dados.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 2.8,
        "classificacao": "mid_cap_infra",
        "caracteristicas": [
            "indexing_protocol",
            "defi_infrastructure",
            "data_narrative",
            "high_beta"
        ]
    },
    "ATAUSDT": {
        "papel": "Automata (ATA). Rede de privacidade e computação segura.",
        "ciclo_proprio": "Sensível a narrativa de privacidade e segurança de dados.",
        "correlacao_btc": [0.35, 0.70],
        "beta_estimado": 3.2,
        "classificacao": "low_cap_privacy_infra",
        "caracteristicas": [
            "privacy_technology",
            "privacy_narrative",
            "high_beta",
            "speculative"
        ]
    },
    "PENGUUSDT": {
        "papel": "Penguin (PENGU). Memecoin com dinâmica especulativa elevada.",
        "ciclo_proprio": "Ciclos de hype social e momentum baseado em comunidade.",
        "correlacao_btc": [0.25, 0.60],
        "beta_estimado": 4.0,
        "classificacao": "low_cap_memecoin",
        "caracteristicas": [
            "memecoin_narrative",
            "community_driven",
            "very_high_beta",
            "speculative"
        ]
    },
    "GPSUSDT": {
        "papel": "GPS. Token de utilidade com narrativa emergente.",
        "ciclo_proprio": "Seguidor de ciclos especulativos de altcoins com alta volatilidade.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.5,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "speculative_flow",
            "narrative_sensitive",
            "very_high_beta",
            "low_liquidity"
        ]
    },
    "GUNUSDT": {
        "papel": "Gunbot (GUN). Token de bot de trading com comunidade especializada.",
        "ciclo_proprio": "Sensível a ciclos de propriedade de trading bots e narrativa de automação.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.8,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "trading_bot_ecosystem",
            "automation_narrative",
            "very_high_beta",
            "niche_community"
        ]
    },
    "POWERUSDT": {
        "papel": "Power. Token de governança/utilidade com dinâmica especulativa.",
        "ciclo_proprio": "Ciclos de altcoin com sensibilidade a narrativas emergentes.",
        "correlacao_btc": [0.30, 0.65],
        "beta_estimado": 3.6,
        "classificacao": "low_cap_speculative",
        "caracteristicas": [
            "governance_token",
            "speculative_flow",
            "very_high_beta",
            "emerging_narrative"
        ]
    },
    "TWTUSDT": {
        "papel": "Trust Wallet Token (TWT). Token de wallet crypto com utilidade em ecossistema Binance.",
        "ciclo_proprio": "Sensível a adoção de wallet e dinâmica de Binance ecosystem.",
        "correlacao_btc": [0.50, 0.80],
        "beta_estimado": 2.0,
        "classificacao": "mid_cap_utility",
        "caracteristicas": [
            "wallet_ecosystem",
            "binance_integration",
            "utility_token",
            "adoption_driven"
        ]
    },
    "LINKUSDT": {
        "papel": "Chainlink (LINK). Oracle descentralizado, líder em dados on-chain para contratos inteligentes.",
        "ciclo_proprio": "Sensível a DeFi TVL, adoção de smart contracts e inovação em oracles.",
        "correlacao_btc": [0.60, 0.85],
        "beta_estimado": 2.3,
        "classificacao": "mid_cap_oracle_infra",
        "caracteristicas": [
            "oracle_network",
            "defi_infrastructure",
            "smart_contract_data",
            "institutional_adoption"
        ]
    },
    "OGNUSDT": {
        "papel": "Origin Protocol (OGN). Protocolo de e-commerce/marketplace descentralizado.",
        "ciclo_proprio": "Sensível a ciclos de inovação em Web3 commerce e marketplace.",
        "correlacao_btc": [0.40, 0.70],
        "beta_estimado": 3.2,
        "classificacao": "low_cap_commerce",
        "caracteristicas": [
            "defi_commerce",
            "marketplace_protocol",
            "web3_adoption",
            "high_beta"
        ]
    },
    "IMXUSDT": {
        "papel": "Immutable X (IMX). Layer 2 para NFTs/gaming, escalabilidade Ethereum.",
        "ciclo_proprio": "Sensível a narrativa NFT/gaming e adoção de Layer 2 solutions.",
        "correlacao_btc": [0.45, 0.75],
        "beta_estimado": 3.0,
        "classificacao": "low_cap_l2_nft",
        "caracteristicas": [
            "layer2_nft",
            "gaming_narrative",
            "ethereumscaling",
            "high_beta"
        ]
    }
}

# List of all symbols for easy iteration
ALL_SYMBOLS: List[str] = list(SYMBOLS.keys())
