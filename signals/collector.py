"""
Signal Collector — single source of truth for fetching signals with caching.

Both monitor.py and engine.py use these. First call fetches live (slow);
subsequent calls within the TTL serve from the SQLite cache (fast).
This is what makes the system get faster over time.
"""
from signals.macro_monitor import fetch_all as _fetch_macro
from signals.alternatives import fetch_all as _fetch_alt
from signals.news_analyzer import analyze_ticker_news
from signals.event_db import cache_get, cache_set, log_event


def get_macro(force: bool = False) -> dict:
    if not force:
        cached = cache_get("macro")
        if cached:
            return cached
    data = _fetch_macro()
    cache_set("macro", data)
    return data


def get_alternatives(force: bool = False) -> dict:
    if not force:
        cached = cache_get("alt")
        if cached:
            return cached
    data = _fetch_alt()
    cache_set("alt", data)
    return data


def get_news(ticker: str, force: bool = False, log_events: bool = True) -> dict:
    if not force:
        cached = cache_get("news", ticker)
        if cached:
            return cached
    data = analyze_ticker_news(ticker)
    cache_set("news", data, ticker)

    if log_events and data.get("event_tags"):
        macro = get_macro()
        vix_val = macro.get("vix", {}).get("value")
        regime = macro.get("regime", {}).get("regime")
        for tag in data["event_tags"]:
            log_event(
                event_type=tag,
                description=f"{ticker}: {data.get('sentiment_summary', tag)}",
                ticker=ticker,
                tags=data.get("event_tags"),
                macro_regime=regime,
                vix=vix_val,
            )
    return data
