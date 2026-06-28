"""
Benchmark — tracks S&P 500 (SPY) performance vs the portfolio.

Simulates: "If I had put all $10,000 into SPY instead, what would I have now?"
Also tracks QQQ (Nasdaq 100) as a second reference.
"""
import json
import os
from datetime import datetime

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "benchmark.json")
INITIAL_CASH = 10_000.0
BENCHMARKS = ["SPY", "QQQ"]


def initialize(spy_price: float, qqq_price: float):
    """Call once when the portfolio is first created."""
    if os.path.exists(BENCHMARK_PATH):
        return  # already initialized
    data = {
        "start_date": datetime.utcnow().isoformat(),
        "initial_cash": INITIAL_CASH,
        "benchmarks": {
            "SPY": {"start_price": spy_price, "shares": INITIAL_CASH / spy_price},
            "QQQ": {"start_price": qqq_price, "shares": INITIAL_CASH / qqq_price},
        },
        "snapshots": [],
    }
    os.makedirs(os.path.dirname(BENCHMARK_PATH), exist_ok=True)
    with open(BENCHMARK_PATH, "w") as f:
        json.dump(data, f, indent=2)


def snapshot(portfolio_value: float, current_prices: dict[str, float]):
    """Record a point-in-time comparison. Call daily or weekly."""
    data = _load()
    if not data:
        return

    entry = {
        "date": datetime.utcnow().isoformat(),
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_return_pct": round((portfolio_value - INITIAL_CASH) / INITIAL_CASH * 100, 2),
    }
    for b in BENCHMARKS:
        bdata = data["benchmarks"].get(b, {})
        price_now = current_prices.get(b, bdata.get("start_price", 1))
        value = bdata.get("shares", 0) * price_now
        entry[f"{b}_value"] = round(value, 2)
        entry[f"{b}_return_pct"] = round((value - INITIAL_CASH) / INITIAL_CASH * 100, 2)

    data["snapshots"].append(entry)
    _save(data)


def compare(portfolio_value: float, current_prices: dict[str, float]) -> dict:
    """Returns current performance vs benchmarks."""
    data = _load()
    if not data:
        return {"error": "Benchmark not initialized"}

    portfolio_return = (portfolio_value - INITIAL_CASH) / INITIAL_CASH * 100
    result = {
        "start_date": data["start_date"][:10],
        "portfolio": {
            "value": round(portfolio_value, 2),
            "return_pct": round(portfolio_return, 2),
        },
        "benchmarks": {},
        "alpha": {},
    }

    for b in BENCHMARKS:
        bdata = data["benchmarks"].get(b, {})
        price_now = current_prices.get(b, bdata.get("start_price", 1))
        value = bdata.get("shares", 0) * price_now
        b_return = (value - INITIAL_CASH) / INITIAL_CASH * 100
        result["benchmarks"][b] = {
            "value": round(value, 2),
            "return_pct": round(b_return, 2),
        }
        result["alpha"][b] = round(portfolio_return - b_return, 2)

    return result


def days_since_start() -> int:
    data = _load()
    if not data:
        return 0
    start = datetime.fromisoformat(data["start_date"])
    return (datetime.utcnow() - start).days


def get_snapshots() -> list[dict]:
    data = _load()
    return data.get("snapshots", []) if data else []


def _load() -> dict | None:
    if os.path.exists(BENCHMARK_PATH):
        with open(BENCHMARK_PATH) as f:
            return json.load(f)
    return None


def _save(data: dict):
    with open(BENCHMARK_PATH, "w") as f:
        json.dump(data, f, indent=2)
