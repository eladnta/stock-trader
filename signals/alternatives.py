"""
Alternative Assets Monitor — tracks non-equity signals that influence stock prices.

Assets monitored:
  Gold, Silver, Oil (WTI), Natural Gas, Copper
  Bitcoin, Ethereum
  10Y Bond (TLT), High Yield (HYG), Investment Grade (LQD)
  Dollar Index (DXY)
  Real Estate (VNQ)

Each asset returns: value, change_1d%, change_1m%, direction, signal_for_stocks
"""
import yfinance as yf
from datetime import datetime

ASSETS = {
    # Commodities
    "gold":        {"ticker": "GC=F",     "name": "Gold (futures)"},
    "silver":      {"ticker": "SI=F",     "name": "Silver (futures)"},
    "oil_wti":     {"ticker": "CL=F",     "name": "Crude Oil WTI"},
    "nat_gas":     {"ticker": "NG=F",     "name": "Natural Gas"},
    "copper":      {"ticker": "HG=F",     "name": "Copper"},
    # Crypto
    "bitcoin":     {"ticker": "BTC-USD",  "name": "Bitcoin"},
    "ethereum":    {"ticker": "ETH-USD",  "name": "Ethereum"},
    # Bonds / rates
    "long_bond":   {"ticker": "TLT",      "name": "20Y Treasury Bond"},
    "high_yield":  {"ticker": "HYG",      "name": "High Yield Bonds"},
    "inv_grade":   {"ticker": "LQD",      "name": "Investment Grade Bonds"},
    # Dollar
    "dollar":      {"ticker": "DX-Y.NYB", "name": "US Dollar Index"},
    # Real estate
    "reits":       {"ticker": "VNQ",      "name": "US REITs"},
}


def fetch_all() -> dict:
    results = {}
    for key, meta in ASSETS.items():
        results[key] = _fetch_asset(key, meta)

    results["snapshot"] = _build_snapshot(results)
    results["fetched_at"] = datetime.utcnow().isoformat()
    return results


def _fetch_asset(key: str, meta: dict) -> dict:
    try:
        ticker = meta["ticker"]
        hist = yf.Ticker(ticker).history(period="35d")
        if hist.empty:
            return {"name": meta["name"], "available": False}

        price = float(hist["Close"].iloc[-1])
        prev_day = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
        month_ago = float(hist["Close"].iloc[0])

        change_1d = (price - prev_day) / prev_day * 100
        change_1m = (price - month_ago) / month_ago * 100

        return {
            "name": meta["name"],
            "ticker": ticker,
            "price": round(price, 4),
            "change_1d_pct": round(change_1d, 2),
            "change_1m_pct": round(change_1m, 2),
            "direction_1d": "up" if change_1d > 0 else "down",
            "direction_1m": "up" if change_1m > 0 else "down",
            "signal": _asset_signal(key, change_1d, change_1m),
        }
    except Exception as e:
        return {"name": meta["name"], "available": False, "error": str(e)}


def _asset_signal(key: str, d1: float, d1m: float) -> dict:
    """Interprets what this asset's move means for equity markets."""
    signals = {
        "gold": {
            "up_impact": "risk_off — investors fleeing to safety; bearish for cyclicals",
            "down_impact": "risk_on — confidence returning; bullish for growth",
            "sector_impact": {"mining": +1 if d1 > 0 else -1, "tech": -0.3 if d1 > 1 else 0.2},
        },
        "oil_wti": {
            "up_impact": "positive for energy, negative for airlines/transport",
            "down_impact": "negative for energy, positive for airlines/consumers",
            "sector_impact": {"energy": +1 if d1 > 0 else -1, "airlines": -0.5 if d1 > 2 else 0.5},
        },
        "copper": {
            "up_impact": "bullish signal — 'Dr. Copper' signals economic growth",
            "down_impact": "bearish signal — economic slowdown indicator",
            "sector_impact": {"industrials": +0.7 if d1 > 0 else -0.7, "tech": +0.3 if d1 > 0 else -0.3},
        },
        "bitcoin": {
            "up_impact": "risk appetite high — bullish for high-beta tech",
            "down_impact": "risk appetite low — caution for speculative stocks",
            "sector_impact": {"tech": +0.4 if d1 > 0 else -0.4, "fintech": +0.6 if d1 > 0 else -0.6},
        },
        "long_bond": {
            "up_impact": "yields falling — bullish for growth stocks, REITs",
            "down_impact": "yields rising — bearish for growth, bullish for banks",
            "sector_impact": {"tech": +0.5 if d1 > 0 else -0.5, "banks": -0.3 if d1 > 0 else 0.3},
        },
        "high_yield": {
            "up_impact": "credit spreads tightening — risk-on, bullish",
            "down_impact": "credit stress — broad market bearish signal",
            "sector_impact": {"financials": +0.5 if d1 > 0 else -0.5},
        },
        "dollar": {
            "up_impact": "strong dollar — bearish for multinationals, commodities",
            "down_impact": "weak dollar — bullish for multinationals, commodities",
            "sector_impact": {"multinationals": -0.5 if d1 > 0 else +0.5, "energy": -0.3 if d1 > 0 else 0.3},
        },
        "reits": {
            "up_impact": "real estate demand strong — falling rate environment",
            "down_impact": "rising rates hurting real estate",
            "sector_impact": {"real_estate": +1 if d1 > 0 else -1},
        },
        "nat_gas": {
            "up_impact": "energy cost rising — bullish energy, bearish utilities/industrials",
            "down_impact": "energy cost falling — bearish energy producers",
            "sector_impact": {"energy": +0.7 if d1 > 0 else -0.7, "utilities": -0.5 if d1 > 2 else 0.2},
        },
    }
    s = signals.get(key, {})
    impact_text = s.get("up_impact", "") if d1 > 0 else s.get("down_impact", "")
    magnitude = "strong" if abs(d1) > 3 else ("moderate" if abs(d1) > 1 else "mild")
    return {
        "direction": "up" if d1 > 0 else "down",
        "magnitude": magnitude,
        "interpretation": impact_text,
        "sector_multipliers": s.get("sector_impact", {}),
    }


def _build_snapshot(results: dict) -> dict:
    """High-level risk-on/risk-off reading from all alternatives."""
    scores = []
    # Risk-on signals: copper up, HYG up, BTC up, gold down, dollar down
    copper = results.get("copper", {})
    hyg = results.get("high_yield", {})
    btc = results.get("bitcoin", {})
    gold = results.get("gold", {})
    dollar = results.get("dollar", {})

    def sign(asset, positive_direction="up"):
        d = asset.get("direction_1d")
        return 1 if d == positive_direction else -1 if d else 0

    risk_score = (
        sign(copper, "up") * 2 +
        sign(hyg, "up") * 2 +
        sign(btc, "up") * 1 +
        sign(gold, "down") * 1.5 +
        sign(dollar, "down") * 1
    )

    max_score = 7.5
    normalized = (risk_score + max_score) / (2 * max_score)

    if normalized > 0.65:
        regime = "risk_on"
        label = "Broad risk appetite — alternatives signal equity bullishness"
    elif normalized < 0.35:
        regime = "risk_off"
        label = "Flight to safety — alternatives signal equity caution"
    else:
        regime = "mixed"
        label = "Mixed alternative signals — no clear directional bias"

    return {
        "risk_regime": regime,
        "label": label,
        "score": round(normalized * 10, 1),
    }


def get_asset_impact_for_sector(sector: str, alt_data: dict) -> float:
    """
    Returns an adjustment score for a specific sector based on alternative assets.
    Positive = bullish tailwind, Negative = bearish headwind.
    Range: -2.0 to +2.0
    """
    sector_lower = sector.lower().replace(" ", "_")
    total = 0.0
    count = 0

    for key, data in alt_data.items():
        if key in ("snapshot", "fetched_at") or not isinstance(data, dict):
            continue
        signal = data.get("signal", {})
        multipliers = signal.get("sector_multipliers", {})
        for sec_key, mult in multipliers.items():
            if sec_key in sector_lower or sector_lower in sec_key:
                total += mult
                count += 1

    return round(total / max(count, 1), 2) if count else 0.0
