"""
Stock Impact Engine — the critical layer that maps ALL signals to a specific stock.

This is what separates sector-level analysis from stock-level analysis.
For each stock, it computes:
  - News impact score (per entity / event tags found in news)
  - Macro regime adjustment (VIX, yield curve, dollar)
  - Alternative asset tailwind/headwind (oil, gold, crypto, bonds)
  - Fear/greed adjustment
  - Combined signal overlay: adds/subtracts from base recommendation score

Importantly: a stock in the "energy" sector is NOT identically affected
by oil price as every other energy stock. XOM (integrated) vs SLB (services)
have different sensitivities. These are encoded per ticker.
"""

# ── Ticker-level sensitivities ────────────────────────────────────────────────
# Format: { ticker: { signal_key: sensitivity_multiplier } }
# Multiplier: +1.0 means full positive response, -1.0 means inverse response
# Missing = use sector default

TICKER_SENSITIVITIES: dict[str, dict[str, float]] = {
    # Energy — differentiated
    "XOM":  {"oil_wti": 0.9, "nat_gas": 0.4, "dollar": -0.3, "gold": -0.1},
    "CVX":  {"oil_wti": 0.8, "nat_gas": 0.3, "dollar": -0.3},
    "COP":  {"oil_wti": 1.0, "nat_gas": 0.5, "dollar": -0.3},
    "SLB":  {"oil_wti": 0.6, "nat_gas": 0.3},   # oilfield services, lags
    "EOG":  {"oil_wti": 1.1, "nat_gas": 0.6},   # E&P, high leverage to oil
    # Banks — rate sensitive
    "JPM":  {"long_bond": -0.6, "high_yield": 0.5, "dollar": 0.2},
    "BAC":  {"long_bond": -0.7, "high_yield": 0.5},
    "GS":   {"high_yield": 0.6, "bitcoin": 0.3, "long_bond": -0.4},
    "WFC":  {"long_bond": -0.8, "reits": 0.3},
    # Tech growth — rate sensitive + risk appetite
    "NVDA": {"bitcoin": 0.4, "long_bond": -0.5, "dollar": -0.3, "copper": 0.3},
    "META": {"long_bond": -0.4, "dollar": -0.4, "bitcoin": 0.2},
    "GOOGL":{"long_bond": -0.4, "dollar": -0.4},
    "MSFT": {"long_bond": -0.3, "dollar": -0.3},
    "AAPL": {"dollar": -0.5, "long_bond": -0.2, "copper": 0.2},
    "TSLA": {"bitcoin": 0.5, "copper": 0.4, "long_bond": -0.5},
    # Consumer defensive — low sensitivity
    "WMT":  {"oil_wti": -0.2, "dollar": 0.1},
    "PG":   {"dollar": -0.3, "oil_wti": -0.1},
    "KO":   {"dollar": -0.3, "sugar": 0.0},
    # Airlines — high oil sensitivity
    "DAL":  {"oil_wti": -0.9, "nat_gas": -0.3},
    "UAL":  {"oil_wti": -1.0, "nat_gas": -0.4},
    # Mining / materials
    "NEM":  {"gold": 1.2, "silver": 0.3, "dollar": -0.4},
    "FCX":  {"copper": 1.1, "gold": 0.3, "dollar": -0.4},
    # Real estate
    "AMT":  {"long_bond": -0.8, "reits": 0.6},
    "PLD":  {"long_bond": -0.6, "reits": 0.7},
    # Healthcare — defensive
    "JNJ":  {"dollar": -0.2, "gold": 0.1},
    "PFE":  {"dollar": -0.3},
    "UNH":  {"long_bond": -0.1},
}

# Sector-level defaults (used when ticker not in TICKER_SENSITIVITIES)
SECTOR_SENSITIVITIES: dict[str, dict[str, float]] = {
    "Technology":           {"long_bond": -0.4, "bitcoin": 0.2, "dollar": -0.3},
    "Financial Services":   {"long_bond": -0.5, "high_yield": 0.4},
    "Healthcare":           {"dollar": -0.2, "long_bond": -0.1},
    "Consumer Cyclical":    {"oil_wti": -0.3, "copper": 0.3, "bitcoin": 0.1},
    "Consumer Defensive":   {"dollar": -0.2, "oil_wti": -0.1},
    "Industrials":          {"copper": 0.5, "oil_wti": -0.2, "dollar": -0.3},
    "Energy":               {"oil_wti": 0.8, "nat_gas": 0.4, "dollar": -0.3},
    "Communication Services": {"dollar": -0.3, "long_bond": -0.3},
    "Utilities":            {"long_bond": -0.7, "nat_gas": -0.3},
    "Real Estate":          {"long_bond": -0.8},
    "Basic Materials":      {"gold": 0.5, "copper": 0.6, "dollar": -0.4},
}

# Event-type impacts per sector (from news tags)
EVENT_SECTOR_IMPACT: dict[str, dict[str, float]] = {
    "earnings_beat":      {"all": +1.5},
    "earnings_miss":      {"all": -1.5},
    "merger_acquisition": {"all": +0.8},
    "regulatory":         {"all": -0.7, "Healthcare": -1.0, "Financial Services": -0.8},
    "macro_rates":        {"Technology": -0.6, "Real Estate": -0.8, "Utilities": -0.6,
                           "Financial Services": +0.5},
    "macro_inflation":    {"Consumer Defensive": -0.3, "Energy": +0.5, "Utilities": -0.4},
    "geopolitical":       {"Energy": +0.6, "Defense": +0.8, "Airlines": -0.5,
                           "Technology": -0.3},
    "climate":            {"Energy": -0.3, "Utilities": -0.4, "Insurance": -0.5,
                           "Real Estate": -0.3},
    "pandemic":           {"Healthcare": +0.5, "Technology": +0.3, "Airlines": -1.0,
                           "Consumer Cyclical": -0.5},
    "analyst_action":     {"all": +0.5},     # analyst upgrade/downgrade included in base
    "capital_action":     {"all": +0.6},
    "guidance":           {"all": +0.5},
}


def compute_signal_overlay(
    ticker: str,
    sector: str,
    news: dict,
    macro: dict,
    alt_data: dict,
    base_opportunity: float,
) -> dict:
    """
    Computes total signal adjustment for this specific stock.
    Returns adjusted opportunity score + breakdown.
    """
    adjustments = {}

    # 1. Alternative asset sensitivity
    sensitivities = TICKER_SENSITIVITIES.get(
        ticker, SECTOR_SENSITIVITIES.get(sector, {})
    )
    alt_adj = 0.0
    alt_details = {}
    for asset_key, sensitivity in sensitivities.items():
        asset = alt_data.get(asset_key, {})
        if not asset.get("available", True) or "change_1d_pct" not in asset:
            continue
        d1 = asset["change_1d_pct"] / 100
        impact = sensitivity * d1 * 20  # scale to score units
        impact = max(-1.5, min(1.5, impact))
        alt_adj += impact
        if abs(impact) > 0.1:
            alt_details[asset_key] = round(impact, 2)

    adjustments["alternatives"] = {"total": round(alt_adj, 2), "details": alt_details}

    # 2. News event tag impact
    event_tags = news.get("event_tags", [])
    news_adj = 0.0
    news_details = {}
    for tag in event_tags:
        tag_impact = EVENT_SECTOR_IMPACT.get(tag, {})
        impact = tag_impact.get(sector, tag_impact.get("all", 0))
        news_adj += impact
        if impact != 0:
            news_details[tag] = impact

    # Add raw news score adjustment (news_score 5=neutral)
    news_score = news.get("news_score", 5)
    news_adj += (news_score - 5) * 0.3
    adjustments["news"] = {"total": round(news_adj, 2), "event_details": news_details,
                           "news_score": news_score}

    # 3. Macro regime adjustment
    regime = macro.get("regime", {}).get("regime", "neutral")
    macro_adj = {
        "crisis": -2.0, "risk_off": -1.0, "late_cycle": -0.5,
        "neutral": 0.0, "risk_on": +0.5,
    }.get(regime, 0)

    # Soften macro impact for defensive sectors
    if sector in ("Consumer Defensive", "Utilities", "Healthcare"):
        macro_adj *= 0.4

    adjustments["macro"] = {"total": round(macro_adj, 2), "regime": regime}

    # 4. VIX adjustment (fear premium)
    vix = macro.get("vix", {})
    vix_val = vix.get("value", 20)
    if vix_val > 35:
        vix_adj = -1.5
    elif vix_val > 25:
        vix_adj = -0.8
    elif vix_val < 15:
        vix_adj = +0.5
    else:
        vix_adj = 0.0
    adjustments["vix"] = {"total": vix_adj, "vix_value": vix_val}

    # Total overlay
    total_overlay = alt_adj + news_adj + macro_adj + vix_adj
    total_overlay = max(-3.0, min(3.0, total_overlay))

    adjusted_score = round(min(10, max(1, base_opportunity + total_overlay)), 1)

    return {
        "ticker": ticker,
        "base_score": base_opportunity,
        "total_overlay": round(total_overlay, 2),
        "adjusted_score": adjusted_score,
        "adjustments": adjustments,
        "signal_narrative": _build_narrative(ticker, adjustments, total_overlay),
    }


def _build_narrative(ticker: str, adj: dict, total: float) -> str:
    parts = []
    if adj["alternatives"]["total"] > 0.3:
        parts.append(f"asset prices tailwind ({adj['alternatives']['total']:+.1f})")
    elif adj["alternatives"]["total"] < -0.3:
        parts.append(f"asset prices headwind ({adj['alternatives']['total']:+.1f})")

    tags = list(adj["news"]["event_details"].keys())
    if tags:
        parts.append(f"news: {', '.join(tags[:2]).replace('_', ' ')}")

    macro = adj["macro"]["regime"]
    if macro not in ("neutral",):
        parts.append(f"macro={macro}")

    if adj["vix"]["vix_value"] > 25:
        parts.append(f"elevated fear (VIX={adj['vix']['vix_value']:.0f})")

    direction = "+" if total >= 0 else ""
    base = f"Overlay {direction}{total:.1f} pts"
    return base + (f" — {'; '.join(parts)}" if parts else "")
