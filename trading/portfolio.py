"""
Portfolio — tracks cash, positions, order history, and P&L.
State is persisted to state/portfolio.json between runs.
"""
import json
import os
from datetime import datetime
from typing import Optional

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "portfolio.json")
INITIAL_CASH = 10_000.0


class Portfolio:
    def __init__(self):
        self.cash: float = INITIAL_CASH
        self.positions: dict[str, dict] = {}  # ticker → {shares, avg_cost, entry_date}
        self.orders: list[dict] = []           # full order history
        self.created_at: str = datetime.utcnow().isoformat()

    # ── Persistence ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> "Portfolio":
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH) as f:
                data = json.load(f)
            p = cls.__new__(cls)
            p.cash = data["cash"]
            p.positions = data["positions"]
            p.orders = data["orders"]
            p.created_at = data.get("created_at", datetime.utcnow().isoformat())
            return p
        return cls()

    def save(self):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w") as f:
            json.dump({
                "cash": self.cash,
                "positions": self.positions,
                "orders": self.orders,
                "created_at": self.created_at,
            }, f, indent=2)

    # ── Trade Execution ───────────────────────────────────────────────────────

    def buy(self, ticker: str, shares: float, price: float, note: str = "") -> dict:
        cost = shares * price
        if cost > self.cash:
            raise ValueError(f"Insufficient cash: need ${cost:.2f}, have ${self.cash:.2f}")

        self.cash -= cost
        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos["shares"] + shares
            pos["avg_cost"] = (pos["shares"] * pos["avg_cost"] + cost) / total_shares
            pos["shares"] = total_shares
        else:
            self.positions[ticker] = {
                "shares": shares,
                "avg_cost": price,
                "entry_date": datetime.utcnow().isoformat(),
            }

        order = self._record_order("BUY", ticker, shares, price, note)
        self.save()
        return order

    def sell(self, ticker: str, shares: float, price: float, note: str = "") -> dict:
        if ticker not in self.positions:
            raise ValueError(f"No position in {ticker}")
        pos = self.positions[ticker]
        if shares > pos["shares"]:
            shares = pos["shares"]  # sell all if over

        proceeds = shares * price
        cost_basis = shares * pos["avg_cost"]
        pnl = proceeds - cost_basis

        self.cash += proceeds
        pos["shares"] -= shares
        if pos["shares"] < 0.001:
            del self.positions[ticker]
        else:
            self.positions[ticker] = pos

        order = self._record_order("SELL", ticker, shares, price, note, pnl=pnl)
        self.save()
        return order

    def sell_all(self, ticker: str, price: float, note: str = "") -> Optional[dict]:
        if ticker not in self.positions:
            return None
        return self.sell(ticker, self.positions[ticker]["shares"], price, note)

    # ── Valuation ─────────────────────────────────────────────────────────────

    def total_value(self, current_prices: dict[str, float]) -> float:
        equity = sum(
            pos["shares"] * current_prices.get(ticker, pos["avg_cost"])
            for ticker, pos in self.positions.items()
        )
        return self.cash + equity

    def total_pnl(self, current_prices: dict[str, float]) -> float:
        return self.total_value(current_prices) - INITIAL_CASH

    def position_value(self, ticker: str, current_price: float) -> float:
        if ticker not in self.positions:
            return 0.0
        return self.positions[ticker]["shares"] * current_price

    def unrealized_pnl(self, ticker: str, current_price: float) -> float:
        if ticker not in self.positions:
            return 0.0
        pos = self.positions[ticker]
        return (current_price - pos["avg_cost"]) * pos["shares"]

    def realized_pnl(self) -> float:
        return sum(o.get("pnl", 0) for o in self.orders if o["action"] == "SELL")

    # ── Queries ───────────────────────────────────────────────────────────────

    def weight(self, ticker: str, current_prices: dict[str, float]) -> float:
        tv = self.total_value(current_prices)
        if tv == 0:
            return 0.0
        return self.position_value(ticker, current_prices.get(ticker, 0)) / tv

    def is_invested(self, ticker: str) -> bool:
        return ticker in self.positions and self.positions[ticker]["shares"] > 0

    # ── Private ───────────────────────────────────────────────────────────────

    def _record_order(self, action, ticker, shares, price, note, pnl=None) -> dict:
        order = {
            "id": len(self.orders) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "ticker": ticker,
            "shares": round(shares, 4),
            "price": price,
            "value": round(shares * price, 2),
            "note": note,
        }
        if pnl is not None:
            order["pnl"] = round(pnl, 2)
        self.orders.append(order)
        return order
