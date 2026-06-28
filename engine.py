"""
Analysis Engine — the central orchestrator.

Routes every symbol to the correct analysis pipeline based on asset class,
applies the cross-signal overlay (news + macro + alternatives), and returns
a unified recommendation in a single consistent shape — whether it's a
stock, an index ETF, a commodity, a currency, or crypto.

This is the single entry point the trader and CLIs call:
    rec = engine.analyze("AAPL")     # equity → fundamental pipeline
    rec = engine.analyze("GLD")      # commodity → technical pipeline
    rec = engine.analyze("EWJ")      # Japan ETF → technical + country macro
"""
import universe
from data.fetcher import fetch_stock_data, fetch_sec_recent_filings, fetch_instrument, fetch_history
from analysis.risk_scorer import score_risk
from analysis.horizon_scorer import score_horizons
from analysis.analyst_aggregator import aggregate_analysts
from analysis import technical
from analysis.recommender import build_recommendation, _opportunity_to_action
from signals import collector
from signals.base import SignalContext
from signals import registry
import signals.modules  # noqa: F401  (registers all signal modules)

_benchmark_cache = {}


def analyze(symbol: str, with_signals: bool = True) -> dict | None:
    """Analyze any tradeable instrument. Returns unified recommendation."""
    symbol = symbol.upper()
    asset = universe.classify(symbol)
    asset_class = asset["asset_class"]

    try:
        if asset_class == universe.EQUITY:
            rec, history = _analyze_equity(symbol)
        else:
            rec, history = _analyze_technical(symbol, asset)
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    if rec is None:
        return None

    rec["asset_class"] = asset_class
    rec["region"] = asset.get("region")

    if with_signals:
        rec = _apply_signal_overlay(rec, symbol, asset, history)

    return rec


def _analyze_equity(symbol: str):
    data = fetch_stock_data(symbol)
    info = data.get("info")
    if not info:
        return None, None
    sec = fetch_sec_recent_filings(symbol)
    risk = score_risk(data)
    horizons = score_horizons(data)
    analysts = aggregate_analysts(data, sec)
    rec = build_recommendation(symbol, info, risk, horizons, analysts)
    rec["pipeline"] = "fundamental"
    return rec, data.get("history")


def _analyze_technical(symbol: str, asset: dict):
    data = fetch_instrument(symbol)
    info = data.get("info") or {}
    history = data.get("history")
    if history is None or history.empty:
        return None, None

    bench = _get_benchmark()
    result = technical.analyze(history, bench, asset["asset_class"])

    # Build an info-like dict so the recommender works uniformly
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not price and not history.empty:
        price = float(history["Close"].iloc[-1])

    synth_info = {
        "shortName": asset["name"],
        "sector": asset.get("category", asset["asset_class"]),
        "currentPrice": price,
        "marketCap": info.get("totalAssets") or info.get("marketCap"),
    }

    rec = build_recommendation(
        symbol, synth_info, result["risk"], result["horizons"], result["analysts"]
    )
    rec["pipeline"] = "technical"
    rec["metrics"] = result.get("metrics", {})
    return rec, history


def _apply_signal_overlay(rec: dict, symbol: str, asset: dict, history) -> dict:
    """Run all registered signal modules and combine into an overlay."""
    try:
        macro = collector.get_macro()
    except Exception:
        macro = {}
    try:
        alt = collector.get_alternatives()
    except Exception:
        alt = {}

    if asset["asset_class"] == universe.EQUITY:
        try:
            news = collector.get_news(symbol)
        except Exception:
            news = {"news_score": 5, "event_tags": []}
    else:
        news = {"news_score": 5, "event_tags": []}

    sector = rec.get("sector", asset.get("category", "Unknown"))
    base = rec["opportunity_score"]

    ctx = SignalContext(
        symbol=symbol, asset_class=asset["asset_class"], sector=sector,
        base_score=base, info={}, history=history,
        macro=macro, alternatives=alt, news=news,
    )
    overlay = registry.evaluate_all(ctx)

    rec["signal_overlay"] = overlay
    rec["base_opportunity_score"] = base
    rec["opportunity_score"] = overlay["adjusted_score"]
    rec["action"] = _opportunity_to_action(overlay["adjusted_score"], rec["risk"]["score"])
    return rec


def _get_benchmark():
    """Cached SPY history for relative-strength calculations."""
    if "SPY" not in _benchmark_cache:
        _benchmark_cache["SPY"] = fetch_history("SPY", period="1y")
    return _benchmark_cache["SPY"]


def analyze_many(symbols: list[str], with_signals: bool = True) -> list[dict]:
    results = []
    for s in symbols:
        rec = analyze(s, with_signals=with_signals)
        if rec and not rec.get("error"):
            results.append(rec)
    return results
