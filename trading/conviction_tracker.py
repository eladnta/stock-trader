"""
Conviction Tracker — the core of the system's self-improvement loop.

For every recommendation made, we record:
  - What we predicted (action, score, price target, timeframe)
  - What actually happened (measured at 1W, 1M, 3M, 6M, 12M)

Over time this builds a reliability score per:
  - Sector
  - Horizon (short/medium/long)
  - Risk tier
  - Overall system accuracy

This is the key differentiator vs a single analyst:
the system can quantify its own prediction accuracy and improve.
"""
import json
import os
from datetime import datetime, timedelta

CONVICTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "convictions.json")

CHECKPOINTS = {
    "1W":  7,
    "1M":  30,
    "3M":  90,
    "6M":  180,
    "12M": 365,
}


def record_prediction(rec: dict, entry_price: float):
    """Log a new prediction at time of trade entry."""
    now = datetime.utcnow()
    conviction = {
        "id": _next_id(),
        "ticker": rec["ticker"],
        "sector": rec.get("sector", "Unknown"),
        "action": rec["action"],
        "entry_price": entry_price,
        "entry_date": now.isoformat(),
        "opportunity_score": rec["opportunity_score"],
        "risk_score": rec["risk"]["score"],
        "risk_label": rec["risk"]["label"],
        "analyst_score": rec["analysts"]["score"],
        "price_target": rec["analysts"].get("price_target"),
        "horizon_short": rec["horizons"]["short"]["score"],
        "horizon_medium": rec["horizons"]["medium"]["score"],
        "horizon_long": rec["horizons"]["long"]["score"],
        "checkpoints": {
            label: {
                "due_date": (now + timedelta(days=days)).isoformat(),
                "measured": False,
                "price": None,
                "return_pct": None,
                "correct_direction": None,
            }
            for label, days in CHECKPOINTS.items()
        },
    }
    convictions = _load()
    convictions.append(conviction)
    _save(convictions)
    return conviction


def update_checkpoints(current_prices: dict[str, float]):
    """
    Called periodically. Fills in checkpoint measurements for due dates.
    Returns list of newly measured checkpoints.
    """
    now = datetime.utcnow()
    convictions = _load()
    measured = []

    for cv in convictions:
        ticker = cv["ticker"]
        price_now = current_prices.get(ticker)
        if not price_now:
            continue

        entry_price = cv["entry_price"]
        is_long = cv["action"] in ("Strong Buy", "Buy", "Buy (elevated risk)")

        for label, cp in cv["checkpoints"].items():
            if cp["measured"]:
                continue
            due = datetime.fromisoformat(cp["due_date"])
            if now >= due:
                ret = (price_now - entry_price) / entry_price
                # Correct if: long + positive return, or sell + negative return
                correct = (ret > 0 and is_long) or (ret < 0 and not is_long)
                cp["measured"] = True
                cp["price"] = price_now
                cp["return_pct"] = round(ret * 100, 2)
                cp["correct_direction"] = correct
                measured.append({
                    "ticker": ticker,
                    "checkpoint": label,
                    "return_pct": cp["return_pct"],
                    "correct": correct,
                })

    _save(convictions)
    return measured


def accuracy_report() -> dict:
    """Compute accuracy stats across all measured checkpoints."""
    convictions = _load()
    if not convictions:
        return {"total_predictions": 0, "message": "No predictions yet"}

    overall = []
    by_sector: dict[str, list] = {}
    by_horizon: dict[str, list] = {}
    by_risk: dict[str, list] = {}

    for cv in convictions:
        sector = cv.get("sector", "Unknown")
        risk = cv.get("risk_label", "Unknown")

        for label, cp in cv["checkpoints"].items():
            if not cp["measured"] or cp["correct_direction"] is None:
                continue
            correct = cp["correct_direction"]
            ret = cp["return_pct"] or 0

            overall.append((correct, ret))
            by_sector.setdefault(sector, []).append((correct, ret))
            by_horizon.setdefault(label, []).append((correct, ret))
            by_risk.setdefault(risk, []).append((correct, ret))

    def stats(items):
        if not items:
            return None
        n = len(items)
        win_rate = sum(1 for c, _ in items if c) / n
        avg_return = sum(r for _, r in items) / n
        return {"n": n, "win_rate": round(win_rate * 100, 1), "avg_return_pct": round(avg_return, 2)}

    return {
        "total_predictions": len(convictions),
        "total_measured": len(overall),
        "overall": stats(overall),
        "by_horizon": {k: stats(v) for k, v in sorted(by_horizon.items())},
        "by_sector": {k: stats(v) for k, v in sorted(by_sector.items())},
        "by_risk": {k: stats(v) for k, v in sorted(by_risk.items())},
    }


def pending_checkpoints() -> list[dict]:
    """Return checkpoints not yet due or not yet measured."""
    now = datetime.utcnow()
    result = []
    for cv in _load():
        for label, cp in cv["checkpoints"].items():
            if not cp["measured"]:
                due = datetime.fromisoformat(cp["due_date"])
                days_left = (due - now).days
                result.append({
                    "ticker": cv["ticker"],
                    "checkpoint": label,
                    "due_date": cp["due_date"][:10],
                    "days_left": max(0, days_left),
                    "entry_price": cv["entry_price"],
                    "action": cv["action"],
                })
    return sorted(result, key=lambda x: x["due_date"])


def _next_id() -> int:
    convictions = _load()
    return len(convictions) + 1


def _load() -> list:
    if os.path.exists(CONVICTIONS_PATH):
        with open(CONVICTIONS_PATH) as f:
            return json.load(f)
    return []


def _save(data: list):
    os.makedirs(os.path.dirname(CONVICTIONS_PATH), exist_ok=True)
    with open(CONVICTIONS_PATH, "w") as f:
        json.dump(data, f, indent=2)
