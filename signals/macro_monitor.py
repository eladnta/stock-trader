"""
Macro Monitor — collects broad macro signals:
  - VIX (fear index)
  - US 10Y yield + 2Y yield (yield curve)
  - Dollar Index (DXY)
  - Fed Funds Rate expectation proxy
  - Geopolitical risk keywords from news headlines
  - FRED economic data: CPI, unemployment (if API key provided)

Each signal returns a standardized dict:
  { value, direction, magnitude (0-1), label, impact_type }
"""
import yfinance as yf
from datetime import datetime, timedelta

FRED_API_KEY = None  # Set via env var FRED_API_KEY if available


def fetch_all() -> dict:
    """Returns all macro signals as a unified dict."""
    vix = _fetch_vix()
    yields = _fetch_yields()
    dxy = _fetch_dollar()
    geo = _fetch_geopolitical_proxy()

    return {
        "fetched_at": datetime.utcnow().isoformat(),
        "vix": vix,
        "yields": yields,
        "dollar": dxy,
        "geopolitical": geo,
        "regime": _classify_regime(vix, yields, dxy),
    }


def _fetch_vix() -> dict:
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return _na("VIX")
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change = (current - prev) / prev

        if current < 15:
            label, stress = "Low fear", "calm"
        elif current < 20:
            label, stress = "Normal", "normal"
        elif current < 30:
            label, stress = "Elevated", "caution"
        elif current < 40:
            label, stress = "High fear", "stress"
        else:
            label, stress = "Extreme fear", "crisis"

        return {
            "value": round(current, 2),
            "change_pct": round(change * 100, 2),
            "label": label,
            "stress_regime": stress,
            "magnitude": min(1.0, current / 80),
            "direction": "up" if change > 0 else "down",
            "market_impact": "bearish" if current > 25 else ("bullish" if current < 15 else "neutral"),
        }
    except Exception as e:
        return _na(f"VIX ({e})")


def _fetch_yields() -> dict:
    try:
        t10 = yf.Ticker("^TNX").history(period="5d")
        t2 = yf.Ticker("^IRX").history(period="5d")  # 13-week (proxy for 2Y)
        if t10.empty:
            return _na("yields")

        y10 = float(t10["Close"].iloc[-1])
        y10_prev = float(t10["Close"].iloc[-2]) if len(t10) > 1 else y10
        y2 = float(t2["Close"].iloc[-1]) if not t2.empty else y10 - 0.5
        spread = y10 - y2  # positive = normal, negative = inverted

        return {
            "ten_year": round(y10, 3),
            "two_year": round(y2, 3),
            "spread_bp": round(spread * 100, 1),
            "curve": "inverted" if spread < 0 else "normal",
            "direction": "rising" if y10 > y10_prev else "falling",
            "change_bp": round((y10 - y10_prev) * 100, 1),
            "impact_on_growth_stocks": "bearish" if y10 > 4.5 else ("bullish" if y10 < 3.5 else "neutral"),
            "impact_on_banks": "bullish" if spread > 0.5 else ("bearish" if spread < 0 else "neutral"),
            "recession_signal": spread < -0.5,
        }
    except Exception as e:
        return _na(f"yields ({e})")


def _fetch_dollar() -> dict:
    try:
        dxy = yf.Ticker("DX-Y.NYB").history(period="10d")
        if dxy.empty:
            return _na("DXY")
        current = float(dxy["Close"].iloc[-1])
        month_ago = float(dxy["Close"].iloc[0])
        change_1m = (current - month_ago) / month_ago

        return {
            "value": round(current, 2),
            "change_1m_pct": round(change_1m * 100, 2),
            "direction": "strengthening" if change_1m > 0 else "weakening",
            "impact_on_multinationals": "bearish" if change_1m > 0.02 else "neutral",
            "impact_on_emerging_markets": "bearish" if change_1m > 0.01 else "neutral",
            "impact_on_commodities": "bearish" if change_1m > 0.01 else "bullish",
        }
    except Exception as e:
        return _na(f"DXY ({e})")


def _fetch_geopolitical_proxy() -> dict:
    """
    Proxy for geopolitical risk using VIX term structure and OVX (oil vol).
    In production: wire to GDELT, NewsAPI, or geopolitical risk index.
    """
    try:
        # OVX = Oil Volatility Index (spikes during geopolitical events)
        ovx = yf.Ticker("^OVX").history(period="5d")
        if not ovx.empty:
            ovx_val = float(ovx["Close"].iloc[-1])
            if ovx_val > 50:
                level = "high"
            elif ovx_val > 35:
                level = "elevated"
            else:
                level = "low"
            return {
                "oil_volatility": round(ovx_val, 2),
                "risk_level": level,
                "proxy": "OVX (oil volatility as geopolitical proxy)",
                "note": "Wire GDELT/NewsAPI for real geopolitical scoring",
            }
    except Exception:
        pass
    return {"risk_level": "unknown", "proxy": "unavailable"}


def _classify_regime(vix: dict, yields: dict, dxy: dict) -> dict:
    """Overall market regime classification."""
    stress = vix.get("stress_regime", "unknown")
    curve = yields.get("curve", "unknown")
    recession_sig = yields.get("recession_signal", False)

    if stress in ("crisis", "stress") and recession_sig:
        regime = "crisis"
        bias = "strong_defensive"
    elif stress in ("crisis", "stress"):
        regime = "risk_off"
        bias = "defensive"
    elif stress == "calm" and curve == "normal":
        regime = "risk_on"
        bias = "growth"
    elif recession_sig:
        regime = "late_cycle"
        bias = "value_defensive"
    else:
        regime = "neutral"
        bias = "balanced"

    return {
        "regime": regime,
        "portfolio_bias": bias,
        "description": {
            "crisis": "Extreme stress — preserve capital, max defensive",
            "risk_off": "Elevated fear — reduce exposure, favor quality",
            "risk_on": "Low fear + normal yield curve — favor growth",
            "late_cycle": "Inverted yield curve — recession watch, reduce cyclicals",
            "neutral": "Mixed signals — balanced allocation",
        }.get(regime, "Unknown"),
    }


def _na(name: str) -> dict:
    return {"available": False, "name": name}
