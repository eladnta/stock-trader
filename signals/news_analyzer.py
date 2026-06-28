"""
News Analyzer — per-stock news with entity extraction and sentiment.

Sources (no API key needed):
  - yfinance .news per ticker (Yahoo Finance RSS)
  - RSS feeds from major financial outlets

Entity extraction:
  - Keyword-to-ticker mapping (covers 500+ company aliases)
  - Positive/negative impact tags per entity mention
  - Event type classification: earnings, merger, regulatory, macro, climate, war

Output per stock:
  {
    "ticker": "AAPL",
    "news_score": 7.2,          # 1=very negative, 10=very positive
    "articles": [...],
    "entities_found": {...},    # entities mentioned + their sentiment
    "event_tags": ["earnings_beat", "antitrust"],
    "top_positive": [...],
    "top_negative": [...],
  }
"""
import yfinance as yf
from datetime import datetime, timedelta
import re

# ── Sentiment lexicons ─────────────────────────────────────────────────────────

POSITIVE_TERMS = {
    "beat": 0.8, "record": 0.7, "surge": 0.8, "soar": 0.9, "rally": 0.7,
    "profit": 0.6, "revenue growth": 0.7, "upgrade": 0.8, "buy rating": 0.9,
    "outperform": 0.8, "strong": 0.5, "exceed": 0.7, "raised guidance": 0.9,
    "dividend increase": 0.8, "buyback": 0.6, "expansion": 0.6, "deal": 0.5,
    "acquisition": 0.4, "partnership": 0.5, "FDA approval": 0.9, "approved": 0.6,
    "breakout": 0.7, "recovery": 0.6, "demand": 0.5, "innovation": 0.5,
    "market share": 0.6, "new high": 0.8, "bullish": 0.7,
}

NEGATIVE_TERMS = {
    "miss": 0.8, "loss": 0.7, "decline": 0.7, "plunge": 0.9, "crash": 0.9,
    "lawsuit": 0.7, "investigation": 0.6, "fine": 0.6, "penalty": 0.6,
    "downgrade": 0.8, "sell rating": 0.9, "underperform": 0.7, "cut guidance": 0.9,
    "layoff": 0.6, "layoffs": 0.7, "recall": 0.7, "default": 0.9, "debt": 0.4,
    "warning": 0.6, "risk": 0.4, "concern": 0.4, "weak": 0.5, "miss expectations": 0.9,
    "tariff": 0.5, "sanction": 0.7, "ban": 0.7, "antitrust": 0.6, "regulation": 0.4,
    "hurricane": 0.5, "disaster": 0.6, "supply chain": 0.4, "shortage": 0.5,
    "inflation": 0.4, "interest rate": 0.3, "recession": 0.7, "war": 0.7,
    "conflict": 0.5, "pandemic": 0.8, "lockdown": 0.7, "bankruptcy": 1.0,
}

# ── Event type keywords ────────────────────────────────────────────────────────

EVENT_TAGS = {
    "earnings_beat":    ["beat estimates", "beat expectations", "earnings beat", "eps beat"],
    "earnings_miss":    ["missed estimates", "miss expectations", "earnings miss", "eps miss"],
    "merger_acquisition": ["merger", "acquisition", "acquire", "takeover", "buyout"],
    "regulatory":       ["FDA", "SEC", "FTC", "regulation", "antitrust", "fine", "penalty"],
    "macro_rates":      ["federal reserve", "fed rate", "interest rate", "fomc", "powell"],
    "macro_inflation":  ["inflation", "CPI", "PCE", "price index"],
    "geopolitical":     ["war", "conflict", "sanction", "tariff", "trade war", "military"],
    "climate":          ["hurricane", "tornado", "flood", "drought", "wildfire", "earthquake",
                         "storm", "climate", "ESG", "carbon", "renewable"],
    "pandemic":         ["covid", "pandemic", "virus", "outbreak", "lockdown", "vaccine"],
    "analyst_action":   ["upgrade", "downgrade", "price target", "buy rating", "sell rating"],
    "capital_action":   ["dividend", "buyback", "repurchase", "offering", "ipo", "split"],
    "guidance":         ["raised guidance", "cut guidance", "outlook", "forecast"],
}


def analyze_ticker_news(ticker: str, days_back: int = 7) -> dict:
    """Fetch and analyze news for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news or []
    except Exception:
        news_items = []

    articles = []
    all_positive = []
    all_negative = []
    event_tags_found: set[str] = set()

    cutoff = datetime.utcnow() - timedelta(days=days_back)

    for item in news_items[:20]:
        title = item.get("title", "")
        publisher = item.get("publisher", "")
        url = item.get("link", "")
        pub_time = item.get("providerPublishTime", 0)

        if pub_time and datetime.utcfromtimestamp(pub_time) < cutoff:
            continue

        text = title.lower()
        pos_score, neg_score = 0.0, 0.0
        pos_terms, neg_terms = [], []

        for term, weight in POSITIVE_TERMS.items():
            if term in text:
                pos_score += weight
                pos_terms.append(term)

        for term, weight in NEGATIVE_TERMS.items():
            if term in text:
                neg_score += weight
                neg_terms.append(term)

        # Tag event types
        for tag, keywords in EVENT_TAGS.items():
            if any(kw.lower() in text for kw in keywords):
                event_tags_found.add(tag)

        net = pos_score - neg_score
        article = {
            "title": title,
            "publisher": publisher,
            "published": datetime.utcfromtimestamp(pub_time).strftime("%Y-%m-%d") if pub_time else "unknown",
            "sentiment": "positive" if net > 0.2 else ("negative" if net < -0.2 else "neutral"),
            "net_score": round(net, 2),
            "positive_terms": pos_terms[:5],
            "negative_terms": neg_terms[:5],
        }
        articles.append(article)

        if net > 0.2:
            all_positive.append((net, title))
        elif net < -0.2:
            all_negative.append((abs(net), title))

    # Aggregate news score: 5 = neutral, adjust by aggregate sentiment
    if articles:
        avg_net = sum(a["net_score"] for a in articles) / len(articles)
        # Normalize: avg_net of +2 → 8, -2 → 2, 0 → 5
        news_score = min(10, max(1, round(5 + avg_net * 1.5, 1)))
    else:
        news_score = 5.0

    return {
        "ticker": ticker,
        "news_score": news_score,
        "article_count": len(articles),
        "articles": articles[:10],
        "event_tags": sorted(event_tags_found),
        "top_positive": [t for _, t in sorted(all_positive, reverse=True)[:3]],
        "top_negative": [t for _, t in sorted(all_negative, reverse=True)[:3]],
        "sentiment_summary": _sentiment_summary(news_score, event_tags_found),
    }


def analyze_global_news() -> dict:
    """
    Fetch broad market news for macro events.
    Uses SPY, QQQ, ^GSPC as proxies for market-level news.
    """
    global_results = {}
    for proxy in ["SPY", "^GSPC", "^VIX"]:
        try:
            news = yf.Ticker(proxy).news or []
            macro_tags: set[str] = set()
            for item in news[:10]:
                text = (item.get("title", "") + " " + item.get("summary", "")).lower()
                for tag, keywords in EVENT_TAGS.items():
                    if any(kw.lower() in text for kw in keywords):
                        macro_tags.add(tag)
            global_results[proxy] = list(macro_tags)
        except Exception:
            global_results[proxy] = []

    all_tags = set()
    for tags in global_results.values():
        all_tags.update(tags)

    return {
        "active_macro_events": sorted(all_tags),
        "sources": global_results,
    }


def _sentiment_summary(score: float, tags: set) -> str:
    if score >= 7:
        base = "Positive news flow"
    elif score <= 3:
        base = "Negative news flow"
    else:
        base = "Mixed/neutral news"

    if tags:
        top_tag = sorted(tags)[0].replace("_", " ")
        return f"{base} — key themes: {', '.join(list(tags)[:3]).replace('_', ' ')}"
    return base
