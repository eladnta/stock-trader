"""
Position Sizer — determines how much capital to allocate per trade.

Logic:
- Risk score (1-10) sets the ceiling: low risk → up to 15%, high risk → up to 4%
- Opportunity score (1-10) scales the actual size within that ceiling
- Never exceed max_single_position of portfolio
- Min position size = $100 (not worth smaller)
- Total positions limit: 20 (diversification)
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading.portfolio import Portfolio

# Max allocation per position by risk tier
RISK_TIER_MAX = {
    "Low":    0.15,   # up to 15% of portfolio
    "Medium": 0.08,   # up to 8%
    "High":   0.04,   # up to 4%
}

MAX_POSITIONS = 20
MIN_POSITION_USD = 100.0


def calc_position_size(
    rec: dict,
    portfolio: "Portfolio",
    current_prices: dict[str, float],
) -> dict:
    """
    Returns: {
        action: "BUY" | "SKIP" | "SELL" | "REDUCE",
        shares: float,
        value_usd: float,
        reason: str,
    }
    """
    ticker = rec["ticker"]
    action = rec["action"]
    opportunity = rec["opportunity_score"]
    risk_label = rec["risk"]["label"]
    current_price = rec.get("price") or current_prices.get(ticker)

    if not current_price or current_price <= 0:
        return _skip("No price data")

    portfolio_value = portfolio.total_value(current_prices)
    already_invested = portfolio.is_invested(ticker)
    current_weight = portfolio.weight(ticker, current_prices)
    position_count = len(portfolio.positions)

    # --- SELL signals ---
    if action in ("Sell", "Reduce"):
        if not already_invested:
            return _skip(f"Signal={action} but no position")
        if action == "Sell":
            shares = portfolio.positions[ticker]["shares"]
            return {"action": "SELL", "shares": shares,
                    "value_usd": shares * current_price, "reason": "Sell signal"}
        else:
            # Reduce by 50%
            shares = portfolio.positions[ticker]["shares"] * 0.5
            return {"action": "SELL", "shares": shares,
                    "value_usd": shares * current_price, "reason": "Reduce signal — trim 50%"}

    # --- BUY/HOLD signals ---
    if action not in ("Strong Buy", "Buy", "Buy (elevated risk)"):
        if already_invested:
            return _skip("Hold — keep existing position")
        return _skip("Hold — not entering new position")

    # Position limit
    if not already_invested and position_count >= MAX_POSITIONS:
        return _skip(f"Max positions ({MAX_POSITIONS}) reached")

    # Determine target allocation
    tier_max = RISK_TIER_MAX[risk_label]
    # Scale within ceiling: opportunity 5→50%, 7→70%, 9→90% of ceiling
    conviction_factor = min(1.0, max(0.2, (opportunity - 4) / 6))
    target_weight = tier_max * conviction_factor

    # How much more to buy (if already holding)
    additional_weight = max(0, target_weight - current_weight)
    if additional_weight < 0.005:  # less than 0.5% → not worth it
        return _skip(f"Already at target weight ({current_weight*100:.1f}% ≈ {target_weight*100:.1f}% target)")

    value_to_deploy = portfolio_value * additional_weight
    value_to_deploy = min(value_to_deploy, portfolio.cash)

    if value_to_deploy < MIN_POSITION_USD:
        return _skip(f"Order too small: ${value_to_deploy:.0f} < ${MIN_POSITION_USD:.0f} min")

    shares = value_to_deploy / current_price

    return {
        "action": "BUY",
        "shares": round(shares, 4),
        "value_usd": round(value_to_deploy, 2),
        "reason": (
            f"Risk={risk_label} → max {tier_max*100:.0f}% | "
            f"Conviction={conviction_factor:.0%} | "
            f"Target weight={target_weight*100:.1f}% | "
            f"Buying {additional_weight*100:.1f}% more"
        ),
    }


def _skip(reason: str) -> dict:
    return {"action": "SKIP", "shares": 0, "value_usd": 0, "reason": reason}
