import time
from core.model2.repository import Model2ThesisRepository
from core.model2.live_service import Model2LiveExecutionService

# Mock exchange to simulate reduce-only rejection then success
class MockExchange:
    def __init__(self, repo, execution):
        self.repo = repo
        self.execution = execution
        self.attempts = {"SL": 0, "TP": 0}

    def get_open_position(self, symbol):
        # Return a visible position to allow protection placement
        filled_qty = self.execution.get("filled_qty") or self.execution.get("filled_qty")
        filled_price = self.execution.get("filled_price")
        if filled_qty is None and filled_price is None:
            return None
        return {
            "symbol": symbol,
            "direction": self.execution.get("signal_side"),
            "position_size_qty": float(filled_qty or 0),
            "entry_price": float(filled_price or 0),
        }

    def get_protection_state(self, *, symbol, signal_side):
        # Initially no protections
        return {"has_sl": False, "has_tp": False, "sl_order_id": None, "tp_order_id": None}

    def place_protective_order(self, *, symbol, signal_side, trigger_price, order_type):
        key = "SL" if order_type.upper().startswith("STOP") else "TP"
        self.attempts[key] += 1
        # First attempt: raise reduce-only rejection, subsequent attempt: return mock order
        if self.attempts[key] == 1:
            raise Exception("-2022 ReduceOnly Order is rejected.")
        # return a mock order payload
        return {
            "orderId": f"mock-{order_type}-{int(time.time())}",
            "symbol": symbol,
            "type": order_type,
            "side": "SELL" if signal_side == "LONG" else "BUY",
            "executedQty": 0,
            "avgPrice": 0,
            "close_position": "true",
        }

    def extract_order_identifier(self, order):
        if isinstance(order, dict):
            return str(order.get("orderId") or order.get("order_id") or order.get("algoId") or order.get("clientOrderId") or "")
        return None

    def is_existing_protection_error(self, error: Exception) -> bool:
        txt = str(error).upper()
        return "OPEN STOP OR TAKE PROFIT ORDER" in txt or "CLOSEPOSITION IN THE DIRECTION IS EXISTING" in txt

    def close_position_market(self, *, symbol, signal_side, quantity):
        return {"result": "closed", "quantity": quantity}

    def calculate_entry_quantity(self, *args, **kwargs):
        return 0

    def get_available_balance(self):
        return 1000.0


if __name__ == "__main__":
    repo = Model2ThesisRepository(db_path="db/modelo2.db")
    execution_id = 15
    exec_row = repo.get_signal_execution(execution_id)
    if not exec_row:
        print(f"Execution id {execution_id} not found in DB")
        raise SystemExit(1)

    # Build a minimal config: execution_mode live for protection flow
    config = Model2LiveExecutionService.build_config(
        execution_mode="live",
        live_symbols=(exec_row["symbol"],),
        short_only=False,
        max_daily_entries=10,
        max_margin_per_position_usd=10.0,
        max_signal_age_ms=24 * 60 * 60 * 1000,
        symbol_cooldown_ms=0,
        funding_rate_max_for_short=0.0005,
        leverage=10,
    )

    mock_exchange = MockExchange(repo, exec_row)
    service = Model2LiveExecutionService(repository=repo, config=config, exchange=mock_exchange)

    now_ms = int(time.time() * 1000)
    print("Starting protection arm for execution", execution_id)
    result = service._arm_protection(exec_row, now_ms=now_ms)
    print("Result:", result)
