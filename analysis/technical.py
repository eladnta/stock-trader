"""
Technical Analysis — for instruments without company fundamentals
(indices, sector/country ETFs, commodities, currencies, bonds, crypto).

Produces risk + horizons + a trend-based "flow" score in the SAME shape
as the equity scorers, so the recommender, position sizer, portfolio,
and conviction tracker all work unchanged across asset classes.

Signals used (all price-derived, no fundamentals):
  - Cross-sectional momentum (12-1): return from t-252 to t-21
  - Trend: price vs 50d / 200d moving averages (golden/death cross)
  - Relative strength vs SPY (is it beating the market?)
  - Annualized volatility → risk score
  - Max drawdown over the window → risk score
"""
import numpy as np
import pandas as pd


def analyze(history: pd.DataFrame, benchmark_history: pd.DataFrame | None = None,
            asset_class: str = "index_etf") -> dict:
    """
    history: DataFrame with 'Close' column, ~1y of daily data.
    benchmark_history: SPY history for relative strength (optional).
    Returns: {risk, horizons, analysts} matching the equity pipeline shape.
    """
    if history is None or history.empty or len(history) < 30:
        return _degraded()

    close = history["Close"].dropna().astype(float)
    if len(close) < 30:
        return _degraded()

    metrics = _compute_metrics(close, benchmark_history)
    risk = _build_risk(metrics, asset_class)
    horizons = _build_horizons(metrics)
    analysts = _build_flow(metrics)

    return {"risk": risk, "horizons": horizons, "analysts": analysts, "metrics": metrics}


def _compute_metrics(close: pd.Series, bench: pd.DataFrame | None) -> dict:
    price_now = float(close.iloc[-1])
    n = len(close)

    # Moving averages
    ma50 = float(close.tail(50).mean()) if n >= 50 else price_now
    ma200 = float(close.tail(200).mean()) if n >= 200 else float(close.mean())

    # Momentum 12-1 (skip last ~21 days)
    if n >= 252:
        mom_12_1 = (float(close.iloc[-21]) - float(close.iloc[-252])) / float(close.iloc[-252])
    elif n >= 60:
        mom_12_1 = (price_now - float(close.iloc[0])) / float(close.iloc[0])
    else:
        mom_12_1 = 0.0

    # 3-month momentum
    if n >= 63:
        mom_3m = (price_now - float(close.iloc[-63])) / float(close.iloc[-63])
    else:
        mom_3m = (price_now - float(close.iloc[0])) / float(close.iloc[0])

    # 1-month momentum
    if n >= 21:
        mom_1m = (price_now - float(close.iloc[-21])) / float(close.iloc[-21])
    else:
        mom_1m = 0.0

    # Annualized volatility
    returns = close.pct_change().dropna()
    ann_vol = float(returns.std() * np.sqrt(252)) if len(returns) > 1 else 0.0

    # Max drawdown
    running_max = close.cummax()
    drawdown = ((close - running_max) / running_max).min()
    max_dd = abs(float(drawdown))

    # Relative strength vs benchmark (3-month)
    rel_strength = None
    if bench is not None and not bench.empty:
        bclose = bench["Close"].dropna().astype(float)
        if len(bclose) >= 63 and n >= 63:
            asset_3m = (price_now - float(close.iloc[-63])) / float(close.iloc[-63])
            bench_3m = (float(bclose.iloc[-1]) - float(bclose.iloc[-63])) / float(bclose.iloc[-63])
            rel_strength = asset_3m - bench_3m

    # Trend classification
    if price_now > ma50 > ma200:
        trend = "strong_uptrend"
    elif price_now > ma200:
        trend = "uptrend"
    elif price_now < ma50 < ma200:
        trend = "strong_downtrend"
    elif price_now < ma200:
        trend = "downtrend"
    else:
        trend = "sideways"

    return {
        "price": round(price_now, 2),
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "mom_12_1": round(mom_12_1, 4),
        "mom_3m": round(mom_3m, 4),
        "mom_1m": round(mom_1m, 4),
        "ann_vol": round(ann_vol, 4),
        "max_drawdown": round(max_dd, 4),
        "rel_strength_3m": round(rel_strength, 4) if rel_strength is not None else None,
        "trend": trend,
        "above_ma50": price_now > ma50,
        "above_ma200": price_now > ma200,
    }


def _build_risk(m: dict, asset_class: str) -> dict:
    scores = {}
    notes = {}

    # Volatility → risk. Crypto naturally higher; bonds lower.
    vol = m["ann_vol"]
    vol_score = min(10, max(1, round(vol * 22)))  # 0.20 vol → ~4, 0.45 → ~10
    scores["volatility"] = vol_score
    notes["volatility"] = f"{vol*100:.0f}% annualized"

    # Drawdown → risk
    dd = m["max_drawdown"]
    dd_score = min(10, max(1, round(dd * 25)))  # 0.20 dd → 5, 0.40 → 10
    scores["max_drawdown"] = dd_score
    notes["max_drawdown"] = f"-{dd*100:.0f}%"

    # Trend → risk (downtrend = higher risk)
    trend_risk = {
        "strong_uptrend": 2, "uptrend": 4, "sideways": 5,
        "downtrend": 7, "strong_downtrend": 9,
    }.get(m["trend"], 5)
    scores["trend"] = trend_risk
    notes["trend"] = m["trend"].replace("_", " ")

    # Asset-class baseline adjustment
    class_floor = {"bond": -1.5, "currency": -1, "index_etf": -0.5,
                   "crypto": +1.5, "commodity": +0.5}.get(asset_class, 0)

    weighted = (vol_score * 0.45 + dd_score * 0.30 + trend_risk * 0.25) + class_floor
    total = round(min(10, max(1, weighted)), 1)
    label = "Low" if total <= 3.5 else ("Medium" if total <= 6.5 else "High")

    return {"score": total, "label": label, "breakdown": scores, "notes": notes}


def _build_horizons(m: dict) -> dict:
    # Short: 1m + 3m momentum + MA50
    short = 5.0
    short += m["mom_1m"] * 25
    short += (1.5 if m["above_ma50"] else -1.5)
    short = round(min(10, max(1, short)), 1)

    # Medium: 3m momentum + relative strength
    medium = 5.0
    medium += m["mom_3m"] * 18
    if m["rel_strength_3m"] is not None:
        medium += m["rel_strength_3m"] * 20
    medium = round(min(10, max(1, medium)), 1)

    # Long: 12-1 momentum + MA200 trend
    long_ = 5.0
    long_ += m["mom_12_1"] * 15
    long_ += (2 if m["above_ma200"] else -2)
    long_ = round(min(10, max(1, long_)), 1)

    return {
        "short":  {"score": short,  "label": "1–3 months", "breakdown": {"mom_1m": m["mom_1m"]}},
        "medium": {"score": medium, "label": "3–12 months", "breakdown": {"mom_3m": m["mom_3m"], "rs": m["rel_strength_3m"]}},
        "long":   {"score": long_,  "label": "1–5 years", "breakdown": {"mom_12_1": m["mom_12_1"]}},
    }


def _build_flow(m: dict) -> dict:
    """
    Trend-following 'flow' score replaces analyst consensus for non-equities.
    Strong uptrend + positive RS + above MAs = high flow score.
    """
    score = 5.0
    score += {"strong_uptrend": 2.5, "uptrend": 1.2, "sideways": 0,
              "downtrend": -1.2, "strong_downtrend": -2.5}.get(m["trend"], 0)
    if m["rel_strength_3m"] is not None:
        score += min(1.5, max(-1.5, m["rel_strength_3m"] * 15))
    score += m["mom_3m"] * 8
    score = round(min(10, max(1, score)), 1)

    rating = ("Strong Buy" if score >= 7.5 else "Buy" if score >= 6 else
              "Hold" if score >= 4.5 else "Reduce" if score >= 3 else "Sell")

    return {
        "score": score,
        "rating": rating,
        "analyst_count": 0,           # no analysts for non-equity
        "price_target": None,
        "price_target_low": None,
        "price_target_high": None,
        "basis": f"trend-following ({m['trend'].replace('_',' ')})",
    }


def _degraded() -> dict:
    return {
        "risk": {"score": 5.0, "label": "Medium", "breakdown": {}, "notes": {"note": "insufficient data"}},
        "horizons": {
            "short":  {"score": 5.0, "label": "1–3 months", "breakdown": {}},
            "medium": {"score": 5.0, "label": "3–12 months", "breakdown": {}},
            "long":   {"score": 5.0, "label": "1–5 years", "breakdown": {}},
        },
        "analysts": {"score": 5.0, "rating": "Hold", "analyst_count": 0,
                     "price_target": None, "price_target_low": None, "price_target_high": None},
        "metrics": {},
    }
