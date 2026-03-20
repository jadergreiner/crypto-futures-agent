"""Exchange adapter used by Model 2.0 live execution services."""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class Model2LiveExchange:
    """Thin wrapper around Binance SDK methods used by the M2 live path."""

    def __init__(self, client: Any, *, recv_window: int = 10_000, leverage: int = 10):
        self._client = client
        self._recv_window = int(recv_window)
        self._leverage = int(leverage)
        self._symbol_precision_cache: dict[str, dict[str, Any]] = {}

    def _extract_data(self, response: Any) -> Any:
        if response is None:
            return None
        if hasattr(response, "data"):
            data = response.data
            if callable(data):
                data = data()
        else:
            data = response
        return self._convert_sdk_object_to_dict(data)

    def _convert_sdk_object_to_dict(self, obj: Any) -> Any:
        if obj is None:
            return None
        if isinstance(obj, (dict, str, int, float, bool, bytes, type(None), Decimal)):
            return obj
        if isinstance(obj, list):
            return [self._convert_sdk_object_to_dict(item) for item in obj]
        if hasattr(obj, "__dict__"):
            raw_dict = {
                key: value
                for key, value in vars(obj).items()
                if not key.startswith("_")
            }
            converted_dict = {
                key: self._convert_sdk_object_to_dict(value)
                for key, value in raw_dict.items()
            }
            return self._map_to_camel_case(converted_dict)
        return obj

    @staticmethod
    def _map_to_camel_case(data: dict[str, Any]) -> dict[str, Any]:
        snake_to_camel = {
            "order_id": "orderId",
            "avg_price": "avgPrice",
            "executed_qty": "executedQty",
            "algo_id": "algoId",
            "client_order_id": "clientOrderId",
            "reduce_only": "reduceOnly",
            "close_position": "closePosition",
            "trigger_price": "triggerPrice",
            "position_amt": "positionAmt",
            "entry_price": "entryPrice",
            "mark_price": "markPrice",
            "liquidation_price": "liquidationPrice",
            "margin_type": "marginType",
            "available_balance": "availableBalance",
        }
        result = dict(data)
        for snake_key, camel_key in snake_to_camel.items():
            if snake_key in result and camel_key not in result:
                result[camel_key] = result[snake_key]
        return result

    @staticmethod
    def _safe_get(obj: Any, attr: str | list[str], default: Any = None) -> Any:
        if isinstance(attr, list):
            for attr_name in attr:
                value = Model2LiveExchange._safe_get(obj, attr_name, default=None)
                if value is not None:
                    return value
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _get_symbol_precision_info(self, symbol: str) -> dict[str, Any]:
        normalized = str(symbol).upper()
        cached = self._symbol_precision_cache.get(normalized)
        if cached is not None:
            return cached

        default_info = {
            "quantity_precision": 8,
            "price_precision": 8,
            "tick_size": None,
        }
        try:
            response = self._client.rest_api.exchange_information()
            data = self._extract_data(response)
            symbols = None
            if isinstance(data, dict):
                symbols = data.get("symbols")
            elif hasattr(data, "symbols"):
                symbols = data.symbols

            if not symbols:
                self._symbol_precision_cache[normalized] = default_info
                return default_info

            for symbol_info in symbols:
                symbol_name = self._safe_get(symbol_info, ["symbol"])
                if str(symbol_name).upper() != normalized:
                    continue

                quantity_precision = self._safe_get(
                    symbol_info, ["quantityPrecision", "quantity_precision"], 8
                )
                price_precision = self._safe_get(
                    symbol_info, ["pricePrecision", "price_precision"], 8
                )
                tick_size = None
                filters = self._safe_get(symbol_info, ["filters"], [])
                for current_filter in filters or []:
                    filter_type = self._safe_get(current_filter, ["filterType", "filter_type"])
                    if str(filter_type).upper() != "PRICE_FILTER":
                        continue
                    raw_tick_size = self._safe_get(current_filter, ["tickSize", "tick_size"])
                    try:
                        tick_size = float(raw_tick_size) if raw_tick_size is not None else None
                    except (TypeError, ValueError):
                        tick_size = None
                    break

                # Buscar minNotional (ou min_notional) se presente
                min_notional = None
                for current_filter in filters or []:
                    filter_type = self._safe_get(current_filter, ["filterType", "filter_type"])
                    if str(filter_type).upper() in {"MIN_NOTIONAL", "MINNOTIONAL"}:
                        raw_min_notional = self._safe_get(current_filter, ["minNotional", "min_notional", "minNotionalValue"]) 
                        try:
                            min_notional = float(raw_min_notional) if raw_min_notional is not None else None
                        except (TypeError, ValueError):
                            min_notional = None
                        break

                info = {
                    "quantity_precision": int(quantity_precision) if quantity_precision is not None else 8,
                    "price_precision": int(price_precision) if price_precision is not None else 8,
                    "tick_size": tick_size if tick_size and tick_size > 0 else None,
                    "min_notional": min_notional if min_notional and min_notional > 0 else None,
                }
                self._symbol_precision_cache[normalized] = info
                return info
        except Exception as exc:
            logger.warning("Failed to load exchange precision for %s: %s", normalized, exc)

        self._symbol_precision_cache[normalized] = default_info
        return default_info

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        precision = self._get_symbol_precision_info(symbol)["quantity_precision"]
        multiplier = 10 ** precision
        return math.floor(float(quantity) * multiplier) / multiplier

    def _normalize_trigger_price(self, symbol: str, trigger_price: float, close_side: str) -> float:
        info = self._get_symbol_precision_info(symbol)
        tick_size = info.get("tick_size")
        if tick_size:
            if str(close_side).upper() == "BUY":
                return math.ceil(float(trigger_price) / tick_size) * tick_size
            return math.floor(float(trigger_price) / tick_size) * tick_size
        precision = info.get("price_precision", 8)
        return round(float(trigger_price), int(precision))

    def get_available_balance(self) -> float | None:
        try:
            response = self._client.rest_api.account_information_v2(recv_window=self._recv_window)
            data = self._extract_data(response)
            raw_balance = self._safe_get(
                data,
                ["available_balance", "availableBalance", "total_available_balance", "totalAvailableBalance"],
            )
            if raw_balance is None:
                return None
            return float(raw_balance)
        except Exception as exc:
            logger.warning("Failed to fetch available balance: %s", exc)
            return None

    def list_open_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        try:
            response = self._client.rest_api.position_information_v2(symbol=symbol)
            data = self._extract_data(response)
        except Exception as exc:
            logger.warning("Failed to list open positions for %s: %s", symbol, exc)
            return []

        if data is None:
            return []
        if not isinstance(data, list):
            data = [data]

        positions: list[dict[str, Any]] = []
        for row in data:
            try:
                position_amt = float(self._safe_get(row, ["position_amt", "positionAmt"], 0))
            except (TypeError, ValueError):
                position_amt = 0.0
            if position_amt == 0:
                continue
            direction = "LONG" if position_amt > 0 else "SHORT"
            positions.append(
                {
                    "symbol": str(self._safe_get(row, ["symbol"], "")),
                    "direction": direction,
                    "position_size_qty": abs(position_amt),
                    "entry_price": float(self._safe_get(row, ["entry_price", "entryPrice"], 0) or 0),
                    "mark_price": float(self._safe_get(row, ["mark_price", "markPrice"], 0) or 0),
                    "leverage": int(self._safe_get(row, ["leverage"], self._leverage) or self._leverage),
                    "margin_type": str(self._safe_get(row, ["margin_type", "marginType"], "CROSS") or "CROSS"),
                }
            )
        return positions

    def get_open_position(self, symbol: str) -> dict[str, Any] | None:
        for position in self.list_open_positions(symbol=symbol):
            if str(position.get("symbol")).upper() == str(symbol).upper():
                return position
        return None

    def calculate_entry_quantity(self, symbol: str, entry_price: float, margin_usd: float, leverage: int) -> float:
        if entry_price <= 0:
            return 0.0
        # Calcular notional alvo e quantidade bruta
        notional_usd = float(margin_usd) * float(leverage)
        raw_qty = notional_usd / float(entry_price)

        # Aplicar precisao/tick
        qty = self._round_quantity(symbol, raw_qty)

        # Validar min_notional do simbolo (se disponivel)
        info = self._get_symbol_precision_info(symbol)
        min_notional = info.get("min_notional")
        try:
            qty_notional = float(qty) * float(entry_price)
        except (TypeError, ValueError):
            qty_notional = 0.0

        # Se mesmo apos arredondamento o notional estiver abaixo do minimo, retornar 0.0
        if min_notional is not None and qty_notional < float(min_notional):
            return 0.0

        # Retornar quantidade arredondada conforme precisao do simbolo
        return float(qty)

    def place_market_entry(
        self,
        *,
        symbol: str,
        signal_side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict[str, Any]:
        side = "BUY" if str(signal_side).upper() == "LONG" else "SELL"
        response = self._client.rest_api.new_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=float(quantity),
            recv_window=self._recv_window,
            new_client_order_id=client_order_id,
        )
        return self._extract_data(response) or {}

    def place_protective_order(
        self,
        *,
        symbol: str,
        signal_side: str,
        trigger_price: float,
        order_type: str,
    ) -> dict[str, Any]:
        close_side = "SELL" if str(signal_side).upper() == "LONG" else "BUY"
        normalized_trigger = self._normalize_trigger_price(symbol, trigger_price, close_side)
        response = self._client.rest_api.new_algo_order(
            algo_type="CONDITIONAL",
            symbol=symbol,
            side=close_side,
            type=order_type,
            trigger_price=normalized_trigger,
            close_position="true",
            working_type="MARK_PRICE",
            recv_window=self._recv_window,
        )
        return self._extract_data(response) or {}

    @staticmethod
    def is_existing_protection_error(error: Exception) -> bool:
        error_text = str(error).upper()
        return (
            "-4130" in error_text
            or "OPEN STOP OR TAKE PROFIT ORDER" in error_text
            or "CLOSEPOSITION IN THE DIRECTION IS EXISTING" in error_text
        )

    def _flatten_order_payload(self, payload: Any) -> list[dict[str, Any]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            if {"symbol", "type"} <= set(payload.keys()):
                return [payload]
            for value in payload.values():
                if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                    return [item for item in value if isinstance(item, dict)]
            return [payload]
        return []

    def _list_open_algo_orders(self, symbol: str) -> list[dict[str, Any]]:
        rest_api = self._client.rest_api
        candidates = [
            ("current_all_algo_open_orders", {"symbol": symbol}),
            ("query_all_algo_orders", {"symbol": symbol}),
            ("current_all_algo_open_orders", {}),
            ("query_all_algo_orders", {}),
        ]
        for method_name, kwargs in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(**kwargs)
                payload = self._extract_data(response)
                orders = self._flatten_order_payload(payload)
                return [
                    order
                    for order in orders
                    if str(self._safe_get(order, ["symbol"], "")).upper() == str(symbol).upper()
                ]
            except Exception:
                continue
        return []

    def _list_open_standard_orders(self, symbol: str) -> list[dict[str, Any]]:
        rest_api = self._client.rest_api
        candidates = [
            ("current_all_open_orders", {"symbol": symbol}),
            ("query_current_all_open_orders", {"symbol": symbol}),
            ("current_all_open_orders", {}),
            ("query_current_all_open_orders", {}),
        ]
        for method_name, kwargs in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(**kwargs)
                payload = self._extract_data(response)
                orders = self._flatten_order_payload(payload)
                return [
                    order
                    for order in orders
                    if str(self._safe_get(order, ["symbol"], "")).upper() == str(symbol).upper()
                ]
            except Exception:
                continue
        return []

    @staticmethod
    def extract_order_identifier(order: dict[str, Any]) -> str | None:
        for key in ("orderId", "order_id", "algoId", "algo_id", "clientOrderId", "client_order_id"):
            value = order.get(key)
            if value is not None and str(value).strip():
                return str(value)
        return None

    def get_protection_state(self, *, symbol: str, signal_side: str) -> dict[str, Any]:
        close_side = "SELL" if str(signal_side).upper() == "LONG" else "BUY"
        has_sl = False
        has_tp = False
        sl_order_id = None
        tp_order_id = None
        for order in self._list_open_algo_orders(symbol) + self._list_open_standard_orders(symbol):
            order_type = str(self._safe_get(order, ["type"], "") or "").upper()
            order_side = str(self._safe_get(order, ["side"], "") or "").upper()
            close_position = self._safe_get(order, ["close_position", "closePosition"])
            reduce_only = self._safe_get(order, ["reduce_only", "reduceOnly"])
            order_status = str(self._safe_get(order, ["status"], "") or "").upper()
            is_open_status = (not order_status) or order_status in {"NEW", "PARTIALLY_FILLED", "PENDING_NEW"}
            is_close_position = str(close_position).lower() in {"true", "1"}
            is_reduce_only = str(reduce_only).lower() in {"true", "1"}
            if order_side != close_side or not is_open_status:
                continue
            if not is_close_position and not is_reduce_only:
                continue
            order_id = self.extract_order_identifier(order)
            if order_type in {"STOP_MARKET", "STOP"}:
                has_sl = True
                sl_order_id = order_id or sl_order_id
            elif order_type in {"TAKE_PROFIT_MARKET", "TAKE_PROFIT"}:
                has_tp = True
                tp_order_id = order_id or tp_order_id
        return {
            "has_sl": has_sl,
            "has_tp": has_tp,
            "sl_order_id": sl_order_id,
            "tp_order_id": tp_order_id,
        }

    def close_position_market(self, *, symbol: str, signal_side: str, quantity: float) -> dict[str, Any]:
        close_side = "SELL" if str(signal_side).upper() == "LONG" else "BUY"
        response = self._client.rest_api.new_order(
            symbol=symbol,
            side=close_side,
            type="MARKET",
            quantity=float(quantity),
            reduce_only=True,
            recv_window=self._recv_window,
        )
        return self._extract_data(response) or {}
