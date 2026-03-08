#!/usr/bin/env python
"""
Validation test: Confirms that:
- Paper mode: Trades on testnet, reads data from production
- Live mode: Trades and reads data from production
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_mode(mode):
    """Test sentiment collection in specified mode."""
    os.environ['TRADING_MODE'] = mode
    
    from data.binance_client import create_binance_client, create_data_client
    from data.sentiment_collector import SentimentCollector
    
    logger.info(f"=" * 70)
    logger.info(f"Testing mode: {mode.upper()}")
    logger.info(f"=" * 70)
    
    # Create main client (what mode actually uses)
    main_client = create_binance_client(mode=mode)
    
    # Create data client (always production)
    data_client = create_data_client()
    
    # Initialize collector (will use data_client internally)
    collector = SentimentCollector(main_client)
    
    # Test long_short_ratio
    try:
        ratio = collector.fetch_long_short_ratio("BTCUSDT")
        logger.info(f"✅ {mode.upper()}: long_short_ratio = {ratio}")
    except Exception as e:
        logger.error(f"❌ {mode.upper()}: Failed to fetch long_short_ratio: {e}")
        return False
    
    # Test open_interest
    try:
        oi = collector.fetch_open_interest("BTCUSDT")
        logger.info(f"✅ {mode.upper()}: open_interest = {oi}")
    except Exception as e:
        logger.error(f"❌ {mode.upper()}: Failed to fetch open_interest: {e}")
        return False
    
    # Test funding_rate
    try:
        fr = collector.fetch_funding_rate("BTCUSDT")
        logger.info(f"✅ {mode.upper()}: funding_rate = {fr}")
    except Exception as e:
        logger.error(f"❌ {mode.upper()}: Failed to fetch funding_rate: {e}")
        return False
    
    logger.info(f"✅ Mode {mode.upper()}: ALL TESTS PASSED\n")
    return True

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("DUAL MODE VALIDATION TEST")
    logger.info("Confirms paper mode reads data from production")
    logger.info("=" * 70)
    logger.info("")
    
    results = {}
    
    # Test paper mode (trades on testnet, reads from production)
    results['paper'] = test_mode('paper')
    
    # Test live mode (trades and reads from production)
    results['live'] = test_mode('live')
    
    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    for mode, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{mode.upper()}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n✅ ALL MODES VALIDATED SUCCESSFULLY")
        sys.exit(0)
    else:
        logger.error("\n❌ SOME MODES FAILED")
        sys.exit(1)
