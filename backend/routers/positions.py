from fastapi import APIRouter
from backend.services.engine_bridge import get_portfolio_summary

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("")
def get_positions():
    summary = get_portfolio_summary()
    positions_raw = summary.get("positions", {})
    result = []
    for ticker, pos in positions_raw.items():
        result.append({
            "ticker": ticker,
            "shares": pos.get("shares", 0),
            "avg_cost": pos.get("avg_cost", 0),
            "current_price": pos.get("current_price", pos.get("avg_cost", 0)),
            "pnl_pct": pos.get("pnl_pct", 0),
            "action": pos.get("action", "HOLD"),
            "signal_scores": pos.get("signal_scores", {}),
        })
    return result
