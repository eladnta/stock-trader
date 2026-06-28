import numpy as np
from config import RISK_WEIGHTS, RISK_THRESHOLDS


def score_risk(data: dict) -> dict:
    """
    Returns risk score 1–10 (1=lowest risk, 10=highest risk)
    and per-metric breakdown.
    """
    info = data.get("info", {})
    financials = data.get("financials")
    balance_sheet = data.get("balance_sheet")
    history = data.get("history")

    scores = {}
    notes = {}

    # --- Beta ---
    beta = info.get("beta")
    if beta is not None:
        # beta <0.5 → 1, beta=1 → 4, beta=1.5 → 7, beta>2 → 10
        scores["beta"] = min(10, max(1, round(beta * 4.5)))
        notes["beta"] = f"{beta:.2f}"
    else:
        scores["beta"] = 5
        notes["beta"] = "N/A"

    # --- Debt to Equity ---
    de = info.get("debtToEquity")
    if de is not None:
        # <50 → 1, 100 → 4, 200 → 7, >400 → 10
        scores["debt_to_equity"] = min(10, max(1, round(de / 45)))
        notes["debt_to_equity"] = f"{de:.1f}%"
    else:
        scores["debt_to_equity"] = 5
        notes["debt_to_equity"] = "N/A"

    # --- Current Ratio ---
    cr = info.get("currentRatio")
    if cr is not None:
        # >2.5 → 1, 1.5 → 3, 1.0 → 5, <0.5 → 10
        scores["current_ratio"] = min(10, max(1, round(12 - cr * 3.5)))
        notes["current_ratio"] = f"{cr:.2f}"
    else:
        scores["current_ratio"] = 5
        notes["current_ratio"] = "N/A"

    # --- Interest Coverage (EBIT / Interest Expense) ---
    ic = _calc_interest_coverage(financials)
    if ic is not None:
        # >15 → 1, 5 → 5, 1.5 → 8, <0 → 10
        if ic > 15:
            scores["interest_coverage"] = 1
        elif ic > 5:
            scores["interest_coverage"] = max(1, round(6 - (ic - 5) / 2))
        elif ic > 0:
            scores["interest_coverage"] = min(9, round(9 - ic))
        else:
            scores["interest_coverage"] = 10
        notes["interest_coverage"] = f"{ic:.1f}x" if ic else "N/A"
    else:
        scores["interest_coverage"] = 5
        notes["interest_coverage"] = "N/A"

    # --- P/E vs Sector ---
    pe = info.get("trailingPE")
    sector_pe = _sector_median_pe(info.get("sector"))
    if pe and sector_pe:
        ratio = pe / sector_pe
        # ratio <0.7 → 1, =1 → 5, >1.5 → 8, >2 → 10
        scores["pe_vs_sector"] = min(10, max(1, round(ratio * 5)))
        notes["pe_vs_sector"] = f"P/E {pe:.1f} vs sector {sector_pe:.1f}"
    else:
        scores["pe_vs_sector"] = 5
        notes["pe_vs_sector"] = f"P/E {pe:.1f}" if pe else "N/A"

    # --- Revenue Growth Stability ---
    stab = _revenue_growth_stability(financials)
    if stab is not None:
        # low std dev & positive growth → low risk
        scores["revenue_growth_stability"] = min(10, max(1, round(stab * 10)))
        notes["revenue_growth_stability"] = f"volatility={stab:.2f}"
    else:
        scores["revenue_growth_stability"] = 5
        notes["revenue_growth_stability"] = "N/A"

    # Weighted average
    weighted = sum(scores[k] * RISK_WEIGHTS[k] for k in scores if k in RISK_WEIGHTS)
    total = round(weighted, 1)
    label = _risk_label(total)

    return {
        "score": total,
        "label": label,
        "breakdown": scores,
        "notes": notes,
    }


def _calc_interest_coverage(financials) -> float | None:
    if financials is None or financials.empty:
        return None
    try:
        ebit = financials.loc["EBIT"].iloc[0] if "EBIT" in financials.index else None
        interest = financials.loc["Interest Expense"].iloc[0] if "Interest Expense" in financials.index else None
        if ebit is not None and interest is not None and interest != 0:
            return abs(float(ebit) / abs(float(interest)))
    except Exception:
        pass
    return None


def _revenue_growth_stability(financials) -> float | None:
    if financials is None or financials.empty:
        return None
    try:
        rev = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else None
        if rev is None:
            return None
        rev = rev.dropna().astype(float)
        if len(rev) < 2:
            return None
        growth_rates = rev.pct_change().dropna()
        std = float(growth_rates.std())
        mean = float(growth_rates.mean())
        # normalize: high std + negative mean → high risk
        return min(1.0, max(0.0, std - min(0, mean)))
    except Exception:
        return None


def _sector_median_pe(sector: str | None) -> float | None:
    sector_pe_map = {
        "Technology": 28.0,
        "Healthcare": 22.0,
        "Financial Services": 14.0,
        "Consumer Cyclical": 20.0,
        "Consumer Defensive": 18.0,
        "Industrials": 20.0,
        "Energy": 12.0,
        "Communication Services": 18.0,
        "Utilities": 16.0,
        "Real Estate": 30.0,
        "Basic Materials": 15.0,
    }
    return sector_pe_map.get(sector)


def _risk_label(score: float) -> str:
    lo, hi = RISK_THRESHOLDS["low"]
    if score <= hi:
        return "Low"
    lo, hi = RISK_THRESHOLDS["medium"]
    if score <= hi:
        return "Medium"
    return "High"
