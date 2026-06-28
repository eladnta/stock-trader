"""
Order Engine — simulates realistic execution with delay and slippage.

Real human trader sitting at a desk:
- Sees signal → decides → types order → confirmation = 5-30 minutes
- Slippage on market order: 0.05-0.20% (liquid US large caps)
- Large orders (>1% of daily volume) get worse fills

This engine does NOT execute instantly. It logs pending orders and
processes them on the next `tick()` call (simulating time passing).
"""
import json
import os
import random
from datetime import datetime, timedelta

PENDING_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "pending_orders.json")

# Delay range in minutes for a human-paced trader
HUMAN_DELAY_MIN = 5
HUMAN_DELAY_MAX = 45

# Slippage range as fraction of price (0.05% to 0.20%)
SLIPPAGE_MIN = 0.0005
SLIPPAGE_MAX = 0.0020


def submit_order(
    action: str,       # "BUY" or "SELL"
    ticker: str,
    shares: float,
    current_price: float,
    note: str = "",
) -> dict:
    """Queue an order. Returns the pending order dict."""
    delay_minutes = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
    execute_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    order = {
        "action": action,
        "ticker": ticker,
        "shares": shares,
        "submitted_price": current_price,
        "submitted_at": datetime.utcnow().isoformat(),
        "execute_at": execute_at.isoformat(),
        "delay_minutes": round(delay_minutes, 1),
        "note": note,
        "status": "PENDING",
    }

    pending = _load_pending()
    pending.append(order)
    _save_pending(pending)
    return order


def get_due_orders(current_prices: dict[str, float]) -> list[dict]:
    """
    Returns orders whose execute_at has passed.
    Applies slippage to execution price.
    Removes them from the pending queue.
    """
    now = datetime.utcnow()
    pending = _load_pending()
    due, remaining = [], []

    for o in pending:
        execute_at = datetime.fromisoformat(o["execute_at"])
        if now >= execute_at:
            ticker = o["ticker"]
            market_price = current_prices.get(ticker, o["submitted_price"])
            slippage = random.uniform(SLIPPAGE_MIN, SLIPPAGE_MAX)
            if o["action"] == "BUY":
                exec_price = market_price * (1 + slippage)
            else:
                exec_price = market_price * (1 - slippage)
            o["exec_price"] = round(exec_price, 4)
            o["slippage_pct"] = round(slippage * 100, 3)
            o["executed_at"] = now.isoformat()
            o["status"] = "EXECUTED"
            due.append(o)
        else:
            remaining.append(o)

    _save_pending(remaining)
    return due


def get_pending_orders() -> list[dict]:
    return _load_pending()


def cancel_pending(ticker: str) -> int:
    """Cancel all pending orders for a ticker. Returns count cancelled."""
    pending = _load_pending()
    remaining = [o for o in pending if o["ticker"] != ticker]
    cancelled = len(pending) - len(remaining)
    _save_pending(remaining)
    return cancelled


def _load_pending() -> list:
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH) as f:
            return json.load(f)
    return []


def _save_pending(orders: list):
    os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
    with open(PENDING_PATH, "w") as f:
        json.dump(orders, f, indent=2)
