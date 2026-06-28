"""
Combines risk, horizon, and analyst scores into a final recommendation.
"""


def build_recommendation(
    ticker: str,
    info: dict,
    risk: dict,
    horizons: dict,
    analysts: dict,
) -> dict:
    risk_score = risk["score"]  # 1=low risk, 10=high risk
    analyst_score = analysts["score"]  # 1=sell, 10=buy

    short = horizons["short"]["score"]
    medium = horizons["medium"]["score"]
    long_ = horizons["long"]["score"]

    # Overall opportunity score (higher = more attractive)
    # Invert risk: low risk boosts opportunity
    risk_penalty = (risk_score - 5) * 0.3  # subtracts if risky, adds if safe
    opportunity = (short * 0.2 + medium * 0.35 + long_ * 0.25 + analyst_score * 0.2) - risk_penalty
    opportunity = min(10, max(1, round(opportunity, 1)))

    action = _opportunity_to_action(opportunity, risk_score)

    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "sector": info.get("sector", "N/A"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": _fmt_market_cap(info.get("marketCap")),
        "opportunity_score": opportunity,
        "action": action,
        "risk": {
            "score": risk_score,
            "label": risk["label"],
            "breakdown": risk.get("notes", {}),
        },
        "horizons": {
            "short": {"score": short, "label": horizons["short"]["label"]},
            "medium": {"score": medium, "label": horizons["medium"]["label"]},
            "long": {"score": long_, "label": horizons["long"]["label"]},
        },
        "analysts": {
            "score": analyst_score,
            "rating": analysts["rating"],
            "count": analysts.get("analyst_count", 0),
            "price_target": analysts.get("price_target"),
            "price_target_range": f"{analysts.get('price_target_low', '?')} – {analysts.get('price_target_high', '?')}",
        },
    }


def _opportunity_to_action(score: float, risk_score: float) -> str:
    if score >= 7.5:
        return "Strong Buy" if risk_score <= 5 else "Buy (elevated risk)"
    elif score >= 6.0:
        return "Buy"
    elif score >= 4.5:
        return "Hold"
    elif score >= 3.0:
        return "Reduce"
    else:
        return "Sell"


def _fmt_market_cap(cap) -> str:
    if not cap:
        return "N/A"
    if cap >= 1e12:
        return f"${cap/1e12:.2f}T"
    elif cap >= 1e9:
        return f"${cap/1e9:.1f}B"
    elif cap >= 1e6:
        return f"${cap/1e6:.0f}M"
    return str(cap)
