"""
Aggregates analyst signals from all available sources:
  1. Yahoo Finance consensus (via yfinance recommendations + price targets)
  2. SEC filing recency signal (recent 8-K / 10-Q = transparency score)
  3. News sentiment placeholder (can be wired to NewsAPI later)

Returns a unified analyst_score 1–10 and a weighted summary.
"""
from config import ANALYST_SITE_WEIGHTS


def aggregate_analysts(data: dict, sec_filings: list[dict] | None = None) -> dict:
    info = data.get("info", {})
    recommendations = data.get("recommendations")
    targets = data.get("analyst_price_targets", {})

    yahoo = _yahoo_consensus(info, recommendations, targets)
    sec = _sec_transparency(sec_filings)
    news = _news_sentiment_placeholder(info)

    components = {
        "yahoo_consensus": yahoo,
        "sec_filing_sentiment": sec,
        "news_sentiment": news,
    }

    weighted = sum(components[k]["score"] * ANALYST_SITE_WEIGHTS[k] for k in components)
    overall = round(weighted, 1)

    return {
        "score": overall,
        "rating": _score_to_rating(overall),
        "components": components,
        "analyst_count": yahoo.get("analyst_count", 0),
        "price_target": targets.get("mean") if isinstance(targets, dict) else None,
        "price_target_low": targets.get("low") if isinstance(targets, dict) else None,
        "price_target_high": targets.get("high") if isinstance(targets, dict) else None,
    }


def _yahoo_consensus(info: dict, recommendations, targets: dict) -> dict:
    """Scores Yahoo Finance consensus signals."""
    score_parts = []
    details = {}

    # Recommendation key: 1=Strong Buy 2=Buy 3=Hold 4=Underperform 5=Sell
    rec_mean = info.get("recommendationMean")
    if rec_mean:
        # invert: 1→10, 3→5, 5→1
        score_parts.append(round((6 - rec_mean) * 2.2))
        details["consensus_mean"] = f"{rec_mean:.1f}"

    analyst_count = info.get("numberOfAnalystOpinions", 0)
    details["analyst_count"] = analyst_count

    # Confidence boost: more analysts = more reliable
    confidence = min(1.2, 0.8 + analyst_count * 0.01) if analyst_count else 1.0

    # Price target upside
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    target_mean = targets.get("mean") if isinstance(targets, dict) else None
    if target_mean and current_price and current_price > 0:
        upside = (target_mean - current_price) / current_price
        target_score = min(10, max(1, round(5 + upside * 13)))
        score_parts.append(target_score)
        details["price_target_upside"] = f"{upside*100:.1f}%"

    if not score_parts:
        return {"score": 5, "details": details, "analyst_count": analyst_count}

    raw = sum(score_parts) / len(score_parts)
    final = min(10, max(1, round(raw * confidence, 1)))
    return {"score": final, "details": details, "analyst_count": analyst_count}


def _sec_transparency(sec_filings: list[dict] | None) -> dict:
    """
    Scores based on recency of SEC filings.
    Recent 10-K or 10-Q = transparent = lower uncertainty = higher score.
    """
    if not sec_filings:
        return {"score": 5, "details": {"note": "no SEC data"}}

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    forms_recent = [f for f in sec_filings if f.get("form") in ("10-K", "10-Q")]
    if not forms_recent:
        return {"score": 5, "details": {"note": "no 10-K/10-Q found"}}

    latest_date_str = sorted([f["date"] for f in forms_recent], reverse=True)[0]
    try:
        latest = datetime.strptime(latest_date_str, "%Y-%m-%d")
        days_ago = (now - latest).days
        # <30 days → 9, <90 → 7, <180 → 6, <365 → 5, older → 3
        if days_ago < 30:
            score = 9
        elif days_ago < 90:
            score = 7
        elif days_ago < 180:
            score = 6
        elif days_ago < 365:
            score = 5
        else:
            score = 3
        return {"score": score, "details": {"latest_filing": latest_date_str, "days_ago": days_ago}}
    except Exception:
        return {"score": 5, "details": {"note": "date parse error"}}


def _news_sentiment_placeholder(info: dict) -> dict:
    """
    Placeholder for news sentiment.
    In production: wire to NewsAPI, Benzinga, or Refinitiv.
    Currently returns a neutral-leaning score based on 52-week price position.
    """
    high_52 = info.get("fiftyTwoWeekHigh")
    low_52 = info.get("fiftyTwoWeekLow")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    if high_52 and low_52 and current and high_52 != low_52:
        position = (current - low_52) / (high_52 - low_52)
        # near 52w high = positive momentum proxy
        score = round(3 + position * 5, 1)
        return {"score": score, "details": {"52w_position": f"{position*100:.0f}%", "note": "price-proxy (no live news)"}}
    return {"score": 5, "details": {"note": "insufficient price data"}}


def _score_to_rating(score: float) -> str:
    if score >= 7.5:
        return "Strong Buy"
    elif score >= 6.0:
        return "Buy"
    elif score >= 4.5:
        return "Hold"
    elif score >= 3.0:
        return "Underperform"
    else:
        return "Sell"
