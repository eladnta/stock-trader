import numpy as np
from config import HORIZON_WEIGHTS, HORIZON_LABELS


def score_horizons(data: dict) -> dict:
    """
    Returns scores 1–10 for short / medium / long horizons.
    10 = most bullish / attractive for that timeframe.
    """
    info = data.get("info", {})
    history = data.get("history")
    recommendations = data.get("recommendations")
    targets = data.get("analyst_price_targets", {})
    financials = data.get("financials")

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    return {
        "short": _short_score(info, history, recommendations, current_price),
        "medium": _medium_score(info, targets, financials, current_price),
        "long": _long_score(info, financials, recommendations),
    }


def _short_score(info, history, recommendations, current_price) -> dict:
    scores = {}

    # Momentum: price vs 3-month ago
    if history is not None and not history.empty and len(history) >= 60:
        price_3m_ago = float(history["Close"].iloc[-60])
        price_now = float(history["Close"].iloc[-1])
        momentum = (price_now - price_3m_ago) / price_3m_ago
        # +20% → 9, 0% → 5, -20% → 1
        scores["price_momentum_3m"] = min(10, max(1, round(5 + momentum * 20)))
    else:
        scores["price_momentum_3m"] = 5

    # Analyst near-term recs (recent 90 days)
    scores["analyst_near_term"] = _recent_analyst_score(recommendations, days=90)

    # Earnings proximity (lower score = earnings soon = uncertainty)
    earnings_date = info.get("earningsTimestamp")
    if earnings_date:
        from datetime import datetime
        days_to_earnings = (datetime.fromtimestamp(earnings_date) - datetime.utcnow()).days
        if days_to_earnings < 0:
            scores["earnings_proximity"] = 5
        elif days_to_earnings < 14:
            scores["earnings_proximity"] = 3  # imminent uncertainty
        elif days_to_earnings < 30:
            scores["earnings_proximity"] = 6
        else:
            scores["earnings_proximity"] = 7
    else:
        scores["earnings_proximity"] = 5

    w = HORIZON_WEIGHTS["short"]
    total = sum(scores[k] * w[k] for k in scores if k in w)
    return {"score": round(total, 1), "breakdown": scores, "label": HORIZON_LABELS["short"]}


def _medium_score(info, targets, financials, current_price) -> dict:
    scores = {}

    # Price target upside
    target_mean = targets.get("mean") if isinstance(targets, dict) else None
    if target_mean and current_price and current_price > 0:
        upside = (target_mean - current_price) / current_price
        # >30% upside → 9, 0% → 5, -20% → 1
        scores["analyst_price_target_upside"] = min(10, max(1, round(5 + upside * 13)))
    else:
        scores["analyst_price_target_upside"] = 5

    # EPS growth fwd
    eps_fwd = info.get("forwardEps")
    eps_ttm = info.get("trailingEps")
    if eps_fwd and eps_ttm and eps_ttm != 0:
        growth = (eps_fwd - eps_ttm) / abs(eps_ttm)
        scores["eps_growth_fwd"] = min(10, max(1, round(5 + growth * 10)))
    else:
        scores["eps_growth_fwd"] = 5

    # Revenue growth YoY
    rev_growth = _calc_rev_growth_yoy(financials)
    if rev_growth is not None:
        scores["revenue_growth_yoy"] = min(10, max(1, round(5 + rev_growth * 15)))
    else:
        scores["revenue_growth_yoy"] = 5

    w = HORIZON_WEIGHTS["medium"]
    total = sum(scores[k] * w[k] for k in scores if k in w)
    return {"score": round(total, 1), "breakdown": scores, "label": HORIZON_LABELS["medium"]}


def _long_score(info, financials, recommendations) -> dict:
    scores = {}

    # Revenue CAGR 3Y
    cagr = _calc_rev_cagr(financials, years=3)
    if cagr is not None:
        scores["revenue_cagr_3y"] = min(10, max(1, round(5 + cagr * 20)))
    else:
        scores["revenue_cagr_3y"] = 5

    # FCF Yield
    fcf_yield = _calc_fcf_yield(info, financials)
    if fcf_yield is not None:
        # >8% → 9, 4% → 6, 0% → 3, negative → 1
        scores["fcf_yield"] = min(10, max(1, round(3 + fcf_yield * 75)))
    else:
        scores["fcf_yield"] = 5

    # PEG ratio (P/E relative to growth) — low PEG → attractive
    peg = info.get("pegRatio")
    if peg and peg > 0:
        # PEG <1 → 8, =1 → 5, =2 → 2
        scores["pe_relative_to_growth"] = min(10, max(1, round(9 - peg * 3.5)))
    else:
        scores["pe_relative_to_growth"] = 5

    # Analyst consensus strength
    scores["analyst_consensus_strength"] = _consensus_strength_score(recommendations)

    w = HORIZON_WEIGHTS["long"]
    total = sum(scores[k] * w[k] for k in scores if k in w)
    return {"score": round(total, 1), "breakdown": scores, "label": HORIZON_LABELS["long"]}


def _recent_analyst_score(recommendations, days: int = 90) -> int:
    if recommendations is None or recommendations.empty:
        return 5
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recs = recommendations.copy()
        recs.index = recs.index.tz_localize("UTC") if recs.index.tz is None else recs.index.tz_convert("UTC")
        recent = recs[recs.index >= cutoff]
        if recent.empty:
            return 5
        grade_col = "To Grade" if "To Grade" in recent.columns else (recent.columns[0] if len(recent.columns) else None)
        if not grade_col:
            return 5
        grade_map = {
            "Strong Buy": 10, "Buy": 8, "Outperform": 7, "Overweight": 7,
            "Neutral": 5, "Hold": 5, "Market Perform": 5,
            "Underperform": 3, "Underweight": 3, "Sell": 2, "Strong Sell": 1,
        }
        scores = recent[grade_col].map(grade_map).dropna()
        return round(scores.mean()) if not scores.empty else 5
    except Exception:
        return 5


def _consensus_strength_score(recommendations) -> int:
    if recommendations is None or recommendations.empty:
        return 5
    try:
        grade_col = "To Grade" if "To Grade" in recommendations.columns else None
        if not grade_col:
            return 5
        grade_map = {"Strong Buy": 10, "Buy": 8, "Outperform": 7, "Overweight": 7,
                     "Neutral": 5, "Hold": 5, "Market Perform": 5,
                     "Underperform": 3, "Underweight": 3, "Sell": 2, "Strong Sell": 1}
        scores = recommendations[grade_col].map(grade_map).dropna()
        return round(scores.tail(20).mean()) if not scores.empty else 5
    except Exception:
        return 5


def _calc_rev_growth_yoy(financials) -> float | None:
    if financials is None or financials.empty:
        return None
    try:
        rev = financials.loc["Total Revenue"].dropna().astype(float)
        if len(rev) < 2:
            return None
        return float((rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1]))
    except Exception:
        return None


def _calc_rev_cagr(financials, years: int = 3) -> float | None:
    if financials is None or financials.empty:
        return None
    try:
        rev = financials.loc["Total Revenue"].dropna().astype(float)
        if len(rev) < years:
            return None
        end = float(rev.iloc[0])
        start = float(rev.iloc[min(years, len(rev) - 1)])
        if start <= 0:
            return None
        return (end / start) ** (1 / years) - 1
    except Exception:
        return None


def _calc_fcf_yield(info, financials) -> float | None:
    market_cap = info.get("marketCap")
    if not market_cap or market_cap == 0:
        return None
    if financials is None or financials.empty:
        return None
    try:
        # Approximate FCF from operating cash flow (cashflow statement preferred)
        op_cash = financials.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in financials.index else None
        capex = financials.loc["Capital Expenditure"].iloc[0] if "Capital Expenditure" in financials.index else 0
        if op_cash is None:
            return None
        fcf = float(op_cash) - abs(float(capex))
        return fcf / market_cap
    except Exception:
        return None
