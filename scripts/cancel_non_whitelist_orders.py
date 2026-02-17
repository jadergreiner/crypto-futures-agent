"""
Cancel open Binance Futures orders for symbols outside whitelist.

Usage examples:
  python scripts/cancel_non_whitelist_orders.py --mode live --dry-run
  python scripts/cancel_non_whitelist_orders.py --mode live
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.execution_config import AUTHORIZED_SYMBOLS
from data.binance_client import create_binance_client

logger = logging.getLogger("cancel_non_whitelist_orders")


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def _convert_sdk_object_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (dict, str, int, float, bool, bytes, type(None))):
        return obj
    if isinstance(obj, list):
        return [_convert_sdk_object_to_dict(item) for item in obj]
    if hasattr(obj, "__dict__"):
        raw_dict = {key: value for key, value in vars(obj).items() if not key.startswith("_")}
        return {key: _convert_sdk_object_to_dict(value) for key, value in raw_dict.items()}
    return obj


def _extract_data(response: Any) -> Any:
    if response is None:
        return None
    if hasattr(response, "data"):
        data = response.data
        if callable(data):
            data = data()
        return _convert_sdk_object_to_dict(data)
    return _convert_sdk_object_to_dict(response)


def _flatten_order_payload(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("orders", "data", "rows", "list", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def _safe_get(obj: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def _order_symbol(order: Dict[str, Any]) -> Optional[str]:
    symbol = _safe_get(order, ["symbol"])
    if symbol is None:
        return None
    return str(symbol).upper()


def _order_identifier(order: Dict[str, Any]) -> Optional[str]:
    value = _safe_get(
        order,
        ["orderId", "order_id", "algoId", "algo_id", "clientOrderId", "client_order_id"],
    )
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _order_type(order: Dict[str, Any]) -> str:
    return str(_safe_get(order, ["type"], "")).upper()


def _is_open_status(order: Dict[str, Any]) -> bool:
    status = str(_safe_get(order, ["status"], "")).upper()
    return not status or status in ("NEW", "PARTIALLY_FILLED", "PENDING_NEW")


def _dedupe_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for order in orders:
        symbol = _order_symbol(order) or ""
        identifier = _order_identifier(order) or ""
        kind = _order_type(order)
        key = (symbol, identifier, kind)
        if key in seen:
            continue
        seen.add(key)
        result.append(order)
    return result


class NonWhitelistOrderCanceler:
    def __init__(self, mode: str):
        self.client = create_binance_client(mode=mode)
        self.rest_api = self.client.rest_api
        self.authorized_symbols = {str(symbol).upper() for symbol in AUTHORIZED_SYMBOLS}

    def _list_orders_with_methods(self, candidates: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        aggregated: List[Dict[str, Any]] = []
        for method_name, kwargs in candidates:
            method = getattr(self.rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(**kwargs)
                payload = _extract_data(response)
                orders = _flatten_order_payload(payload)
                if orders:
                    logger.debug("Fetched %s orders via %s", len(orders), method_name)
                    aggregated.extend(orders)
            except Exception as exc:
                logger.debug("Failed listing with %s: %s", method_name, exc)
        return _dedupe_orders(aggregated)

    def list_open_standard_orders(self) -> List[Dict[str, Any]]:
        candidates = [
            ("current_all_open_orders", {}),
            ("query_current_all_open_orders", {}),
        ]
        orders = self._list_orders_with_methods(candidates)
        return [order for order in orders if _is_open_status(order)]

    def list_open_algo_orders(self) -> List[Dict[str, Any]]:
        candidates = [
            ("current_all_algo_open_orders", {}),
            ("query_all_algo_orders", {}),
        ]
        orders = self._list_orders_with_methods(candidates)
        return [order for order in orders if _is_open_status(order)]

    def filter_non_whitelist(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for order in orders:
            symbol = _order_symbol(order)
            if not symbol:
                continue
            if symbol not in self.authorized_symbols:
                filtered.append(order)
        return filtered

    def _cancel_order(self, symbol: str, order: Dict[str, Any], is_algo: bool) -> Tuple[bool, str]:
        identifier = _order_identifier(order)
        if not identifier:
            return False, "missing order identifier"

        if is_algo:
            algo_id_int = int(identifier) if identifier.isdigit() else None
            methods = []
            if algo_id_int is not None:
                methods.append(("cancel_algo_order", {"algo_id": algo_id_int}))
            methods.append(("cancel_algo_order", {"client_algo_id": identifier}))
        else:
            methods = [
                ("cancel_order", {"symbol": symbol, "order_id": identifier}),
                ("cancel_order", {"symbol": symbol, "orderId": identifier}),
                ("cancel_order", {"symbol": symbol, "orig_client_order_id": identifier}),
                ("cancel_order", {"symbol": symbol, "origClientOrderId": identifier}),
            ]

        for method_name, kwargs in methods:
            method = getattr(self.rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                method(**kwargs)
                return True, f"cancelled via {method_name}"
            except Exception as exc:
                last_error = str(exc)
        return False, last_error if 'last_error' in locals() else "no cancel method available"

    def run(self, dry_run: bool) -> Dict[str, Any]:
        standard_orders = self.list_open_standard_orders()
        algo_orders = self.list_open_algo_orders()

        standard_targets = self.filter_non_whitelist(standard_orders)
        algo_targets = self.filter_non_whitelist(algo_orders)

        logger.info("Whitelist symbols: %s", sorted(self.authorized_symbols))
        logger.info("Open standard orders: %s | outside whitelist: %s", len(standard_orders), len(standard_targets))
        logger.info("Open algo orders: %s | outside whitelist: %s", len(algo_orders), len(algo_targets))

        summary = {
            "dry_run": dry_run,
            "standard_total": len(standard_targets),
            "algo_total": len(algo_targets),
            "cancelled": 0,
            "failed": 0,
            "failures": [],
        }

        if dry_run:
            for order in standard_targets:
                logger.info("[DRY-RUN] standard %s id=%s type=%s", _order_symbol(order), _order_identifier(order), _order_type(order))
            for order in algo_targets:
                logger.info("[DRY-RUN] algo %s id=%s type=%s", _order_symbol(order), _order_identifier(order), _order_type(order))
            return summary

        for is_algo, orders in ((False, standard_targets), (True, algo_targets)):
            tag = "algo" if is_algo else "standard"
            for order in orders:
                symbol = _order_symbol(order)
                if not symbol:
                    summary["failed"] += 1
                    summary["failures"].append({"symbol": None, "id": _order_identifier(order), "type": tag, "error": "missing symbol"})
                    continue

                ok, msg = self._cancel_order(symbol, order, is_algo=is_algo)
                if ok:
                    summary["cancelled"] += 1
                    logger.info("Cancelled %s order: %s id=%s (%s)", tag, symbol, _order_identifier(order), msg)
                else:
                    summary["failed"] += 1
                    summary["failures"].append({"symbol": symbol, "id": _order_identifier(order), "type": tag, "error": msg})
                    logger.error("Failed cancel %s order: %s id=%s (%s)", tag, symbol, _order_identifier(order), msg)

        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Cancel open orders outside whitelist symbols")
    parser.add_argument("--mode", choices=["paper", "live"], default="live", help="Binance environment mode")
    parser.add_argument("--dry-run", action="store_true", help="List orders that would be cancelled without sending cancel requests")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs")
    args = parser.parse_args()

    setup_logging(args.verbose)

    canceler = NonWhitelistOrderCanceler(mode=args.mode)
    summary = canceler.run(dry_run=args.dry_run)

    logger.info(
        "Summary | dry_run=%s | standard=%s | algo=%s | cancelled=%s | failed=%s",
        summary["dry_run"],
        summary["standard_total"],
        summary["algo_total"],
        summary["cancelled"],
        summary["failed"],
    )

    if summary["failed"] > 0 and not args.dry_run:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
