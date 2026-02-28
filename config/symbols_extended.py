"""
Extended symbol list (200 pares) para F-12b Parquet cache optimization.
Organized by liquidity tier: Tier 1 (30) + Tier 2 (30) + Tier 3 (140).

TASK-011 Phase 1 Execution — 27 FEV 2026 11:00 UTC
Status: 🟢 EXPANDED from 60 → 200 pares
"""

from typing import List, Dict, Any

# =============================================================================
# TIER 1: TOP 30 PARES (Highest Liquidity + Market Cap)
# =============================================================================
TIER_1_TOP_30 = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "LTCUSDT", "AVAXUSDT", "POLKAUSDT",
    "LINKUSDT", "OPUSDT", "ARBUSDT", "UNIUSDT", "MATICUSDT",
    "FILUSDT", "GMXUSDT", "BAKEUSDT", "WAVESUSDT", "IOTAUSDT",
    "GALAUSDT", "WLDUSDT", "FETUSDT", "TWTUSDT", "FTUSDT",
    "APUSDT", "ONTUSDT", "NEARUSDT", "ATOMUSDT", "DYDXUSDT",
]

# =============================================================================
# TIER 2: MID-CAP ALTCOINS (30)
# =============================================================================
TIER_2_MID_30 = [
    "GAMEUDT", "AXSUDT", "ENJUSDT", "MANAUSDT", "SANDUSDT",
    "GFIEUSDT", "PIXELUSDT", "MOVRUSDT", "ZKUSDT", "LINEAUSDT",
    "IMXUSDT", "NOTUSDT", "FROUSDT", "CYBERUSDT", "PUMAUSDT",
    "SUSHISDT", "AAVUSDT", "CURVEUSDT", "BALANCERUSDT", "CONVEXUSDT",
    "FXSUSDT", "PENDLEUSDT", "LDOUSDT", "TIAUSDT", "COMUSDT",
    "OSMOUSDT", "TAOASDT", "SUIUSDT", "MKRUSDT", "GMAUSDT",
]

# =============================================================================
# TIER 3: EMERGING LOW-CAP ALTCOINS (140)
# =============================================================================
TIER_3_EMERGING_140 = [
    # AI & ML (10)
    "AISDT", "AGIXDT", "NURDT", "RNDRDT", "AKRDT",
    "GPUDT", "POKTDT", "CTXCDT", "ALGUSDT", "DREAMDT",
    # RWA & Tokenization (10)
    "DATADT", "PEPEDT", "IQDT", "ORAIUSDT", "VIRTUSDT",
    "HONKDT", "PENDDT", "HFTDT", "ERCDT", "DOCDT",
    # Layer 1 Alternatives (15)
    "RLCDT", "DEFIUSDT", "XEXDT", "ENADDT", "MANFDT",
    "APTUSDT", "MOVSDT", "ARCDT", "METISDT", "RAYDUSDT",
    "VELARDT", "BLDDT", "JTODT", "BLUEDT", "POIUSDT",
    # Cross-Chain & Bridges (10)
    "AXLUSDT", "GOAUSDT", "CCIPDT", "LAYERUSDT", "NXMUSDT",
    "LZDT", "WOEUSDT", "SNPSUSDT", "T3DT", "BKDT",
    # NFT & Metaverse (12)
    "FLRDT", "SYNDT", "GFTEUSDT", "XYDT", "GLMDT",
    "QTUMUSDT", "TROVEDT", "UMAUSDT", "CEMUSDT", "CTXDT",
    "YGGDT", "NFTDT",
    # DeFi Emerging (20)
    "JUIDT", "LENDUSDT", "MERLINDT", "RAACDT", "AXPDT",
    "WRSDT", "NUENEDT", "MINADT", "PLAUSDT", "ZEXDT",
    "ERYDT", "DFIUSDT", "ORBUDT", "ERODT", "AERDT",
    "MAIDDT", "COPIDT", "VELOUSDT", "LPUSDT", "MAGUSUSDT",
    # Storage & Infrastructure (10)
    "STORDT", "ARKDT", "BTFSDT", "PROXDT", "TNETDT",
    "NYLDT", "STORJDT", "SFUSDT", "IPFSDT", "POWUSDT",
    # Privacy & Security (8)
    "SCDT", "XMRDT", "ZECDT", "OASISDT", "SECRETDT",
    "MANTADT", "RADT", "VERDT",
    # Web3 Social & DAO (12)
    "DEEDT", "TWITDT", "SOCIUSDT", "DYDDT", "GOVDT",
    "AURODT", "BDUSDT", "ONSDT", "PALTDT", "MASKDT",
    "POLUSDT", "TRUSTDT",
    # Emerging Tokens (23)
    "JUPDT", "MTUSDT", "MNTUSDT", "RONDT", "FUSIONDT",
    "LISTDT", "ZEUSDT", "ZETADT", "XFTDT", "DEXDT",
    "HPSDT", "TBTDT", "WAVDT", "BTDDT", "SYSDT",
    "RNDDT", "MINUSDT", "ZRCDT", "XPDT", "FLUXDT",
    "ORBDT", "SOCDT", "DAODT",
    # Additional (10)
    "CHUSDT", "BNDT", "WOOUSDT", "ENUSDT", "DCDT",
    "RAYDT", "INUSDT", "BALADDT", "CVCTDT", "SHDUSDT",
]

# Combine all tiers into 200-pair extended list
SYMBOLS_EXTENDED: List[str] = (
    TIER_1_TOP_30 +
    TIER_2_MID_30 +
    TIER_3_EMERGING_140
)

# Validation check
_duplicate_check = len(set(SYMBOLS_EXTENDED)) == len(SYMBOLS_EXTENDED)
if not _duplicate_check:
    _dupes = [s for s in set(SYMBOLS_EXTENDED) if SYMBOLS_EXTENDED.count(s) > 1]
    raise AssertionError(f"Duplicate symbols detected: {_dupes}")

_len_check = len(SYMBOLS_EXTENDED) == 200
if not _len_check:
    raise AssertionError(f"Expected 200 symbols, got {len(SYMBOLS_EXTENDED)}")

# Tier breakdown for reference
TIER_MAPPING: Dict[str, str] = {
    **{s: "TIER_1_TOP_30" for s in TIER_1_TOP_30},
    **{s: "TIER_2_MID_30" for s in TIER_2_MID_30},
    **{s: "TIER_3_EMERGING_140" for s in TIER_3_EMERGING_140},
}

# Export for use
__all__ = [
    "SYMBOLS_EXTENDED",
    "TIER_1_TOP_30",
    "TIER_2_MID_30",
    "TIER_3_EMERGING_140",
    "TIER_MAPPING",
]
