#!/usr/bin/env python
"""
Diagnostic script to test sentiment API connectivity.
"""

import logging
import os
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

load_dotenv()

# Import after loading .env
from data.binance_client import create_binance_client
from data.sentiment_collector import SentimentCollector

logger = logging.getLogger(__name__)

def main():
    """Run sentiment API diagnostics."""
    logger.info("======== SENTIMENT API DIAGNOSTIC ========")

    # Get trading mode
    mode = os.getenv("TRADING_MODE", "paper")
    logger.info(f"Trading mode: {mode}")
    logger.info(f"API Key configured: {'Yes' if os.getenv('BINANCE_API_KEY') else 'No'}")

    try:
        # Create client
        logger.info("Creating Binance client...")
        client = create_binance_client(mode=mode)
        logger.info("✅ Client created successfully")

        # Initialize sentiment collector
        logger.info("Initializing SentimentCollector...")
        collector = SentimentCollector(client)
        logger.info("✅ SentimentCollector initialized")

        # Run diagnostics
        logger.info("\n======== RUNNING DIAGNOSTICS ========\n")
        results = collector.diagnose_api("BTCUSDT")

        # Print results
        logger.info("\n======== DIAGNOSTIC RESULTS ========")
        logger.info(f"Summary: {results['summary']['working_endpoints']}/{results['summary']['total_endpoints']} endpoints working")
        logger.info(f"All OK: {results['summary']['all_ok']}")

        logger.info("\nEndpoint Details:")
        for endpoint, detail in results['endpoints'].items():
            status = detail['status'].upper()
            logger.info(f"  {endpoint}: {status}")
            if detail['status'] == 'failure':
                logger.error(f"    Error: {detail.get('error', 'Unknown')}")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
