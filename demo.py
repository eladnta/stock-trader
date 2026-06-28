"""
Demo mode — runs the full analysis pipeline with mock data.
Run: python demo.py
No internet required. Shows how the system works end-to-end.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from rich.console import Console
from rich.rule import Rule
from analysis.risk_scorer import score_risk
from analysis.horizon_scorer import score_horizons
from analysis.analyst_aggregator import aggregate_analysts
from analysis.recommender import build_recommendation
from main import _print_full_report, _print_summary_table

console = Console()

MOCK_STOCKS = {
    "AAPL": {
        "info": {
            "shortName": "Apple Inc.", "sector": "Technology",
            "currentPrice": 213.5, "marketCap": 3_300_000_000_000,
            "beta": 1.25, "debtToEquity": 148.0, "currentRatio": 0.99,
            "trailingPE": 32.5, "forwardEps": 7.85, "trailingEps": 6.57,
            "pegRatio": 2.4, "recommendationMean": 1.9, "numberOfAnalystOpinions": 38,
            "fiftyTwoWeekHigh": 237.0, "fiftyTwoWeekLow": 163.0,
            "earningsTimestamp": 1753920000,
        },
        "analyst_price_targets": {"mean": 235.0, "low": 185.0, "high": 270.0},
        "revenue_growth_mock": 0.06,
        "rev_values": [394_329_000_000, 383_285_000_000, 365_817_000_000],
        "interest_coverage_mock": 30.0,
        "fcf_yield_mock": 0.038,
        "rev_cagr_mock": 0.032,
        "eps_growth_mock": 0.19,
        "recent_rec_score": 8,
    },
    "NVDA": {
        "info": {
            "shortName": "NVIDIA Corporation", "sector": "Technology",
            "currentPrice": 137.0, "marketCap": 3_370_000_000_000,
            "beta": 1.9, "debtToEquity": 42.0, "currentRatio": 4.2,
            "trailingPE": 52.0, "forwardEps": 4.10, "trailingEps": 2.57,
            "pegRatio": 0.95, "recommendationMean": 1.4, "numberOfAnalystOpinions": 57,
            "fiftyTwoWeekHigh": 153.0, "fiftyTwoWeekLow": 78.0,
            "earningsTimestamp": 1756512000,
        },
        "analyst_price_targets": {"mean": 175.0, "low": 120.0, "high": 220.0},
        "revenue_growth_mock": 1.22,
        "rev_values": [60_922_000_000, 26_974_000_000, 16_675_000_000],
        "interest_coverage_mock": 82.0,
        "fcf_yield_mock": 0.025,
        "rev_cagr_mock": 0.56,
        "eps_growth_mock": 0.60,
        "recent_rec_score": 9,
    },
    "JPM": {
        "info": {
            "shortName": "JPMorgan Chase & Co.", "sector": "Financial Services",
            "currentPrice": 268.0, "marketCap": 760_000_000_000,
            "beta": 1.05, "debtToEquity": 122.0, "currentRatio": None,
            "trailingPE": 13.5, "forwardEps": 19.2, "trailingEps": 19.8,
            "pegRatio": 1.1, "recommendationMean": 2.1, "numberOfAnalystOpinions": 24,
            "fiftyTwoWeekHigh": 295.0, "fiftyTwoWeekLow": 196.0,
            "earningsTimestamp": 1752192000,
        },
        "analyst_price_targets": {"mean": 290.0, "low": 235.0, "high": 340.0},
        "revenue_growth_mock": 0.12,
        "rev_values": [162_406_000_000, 144_896_000_000, 131_946_000_000],
        "interest_coverage_mock": 8.5,
        "fcf_yield_mock": 0.06,
        "rev_cagr_mock": 0.11,
        "eps_growth_mock": -0.03,
        "recent_rec_score": 7,
    },
    "PFE": {
        "info": {
            "shortName": "Pfizer Inc.", "sector": "Healthcare",
            "currentPrice": 24.5, "marketCap": 139_000_000_000,
            "beta": 0.65, "debtToEquity": 60.0, "currentRatio": 1.4,
            "trailingPE": 45.0, "forwardEps": 2.60, "trailingEps": 0.54,
            "pegRatio": 8.2, "recommendationMean": 3.2, "numberOfAnalystOpinions": 19,
            "fiftyTwoWeekHigh": 32.0, "fiftyTwoWeekLow": 21.5,
            "earningsTimestamp": 1754697600,
        },
        "analyst_price_targets": {"mean": 28.5, "low": 22.0, "high": 38.0},
        "revenue_growth_mock": -0.41,
        "rev_values": [58_496_000_000, 100_330_000_000, 81_288_000_000],
        "interest_coverage_mock": 2.1,
        "fcf_yield_mock": 0.07,
        "rev_cagr_mock": -0.15,
        "eps_growth_mock": 3.8,
        "recent_rec_score": 4,
    },
    "XOM": {
        "info": {
            "shortName": "Exxon Mobil Corporation", "sector": "Energy",
            "currentPrice": 113.5, "marketCap": 455_000_000_000,
            "beta": 0.88, "debtToEquity": 18.0, "currentRatio": 1.5,
            "trailingPE": 14.2, "forwardEps": 8.50, "trailingEps": 7.98,
            "pegRatio": 1.6, "recommendationMean": 2.3, "numberOfAnalystOpinions": 26,
            "fiftyTwoWeekHigh": 126.0, "fiftyTwoWeekLow": 97.0,
            "earningsTimestamp": 1753660800,
        },
        "analyst_price_targets": {"mean": 128.0, "low": 108.0, "high": 155.0},
        "revenue_growth_mock": 0.05,
        "rev_values": [398_675_000_000, 398_675_000_000, 376_317_000_000],
        "interest_coverage_mock": 18.0,
        "fcf_yield_mock": 0.055,
        "rev_cagr_mock": 0.028,
        "eps_growth_mock": 0.065,
        "recent_rec_score": 7,
    },
}


class MockData:
    """Wraps mock values to simulate the fetcher output."""

    def __init__(self, ticker: str, mock: dict):
        self.ticker = ticker
        self.mock = mock

    def as_fetcher_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "info": self.mock["info"],
            "financials": None,
            "balance_sheet": None,
            "cashflow": None,
            "history": self._mock_history(),
            "recommendations": None,
            "analyst_price_targets": self.mock["analyst_price_targets"],
        }

    def _mock_history(self):
        import pandas as pd
        import numpy as np
        n = 252
        price_now = self.mock["info"]["currentPrice"]
        price_3m_ago = price_now / (1 + self.mock["revenue_growth_mock"] * 0.4)
        prices = np.linspace(price_3m_ago, price_now, n) * (1 + np.random.randn(n) * 0.01)
        idx = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="B")
        return pd.DataFrame({"Close": prices, "Volume": [1e7] * n}, index=idx)


def _patched_score_risk(data, mock):
    """Risk scorer with mock values injected for fields not derivable from info alone."""
    result = score_risk(data)
    # Override interest coverage from mock
    ic = mock.get("interest_coverage_mock")
    if ic is not None:
        if ic > 15:
            ic_score = 1
        elif ic > 5:
            ic_score = max(1, round(6 - (ic - 5) / 2))
        else:
            ic_score = min(9, round(9 - ic))
        result["breakdown"]["interest_coverage"] = ic_score
        result["notes"]["interest_coverage"] = f"{ic:.1f}x"
    return result


def _patched_score_horizons(data, mock):
    """Horizon scorer with mock injection for revenue/EPS/FCF."""
    result = score_horizons(data)

    # Medium: EPS growth
    eps_g = mock.get("eps_growth_mock", 0)
    result["medium"]["breakdown"]["eps_growth_fwd"] = min(10, max(1, round(5 + eps_g * 10)))

    # Medium: Revenue growth YoY
    rev_g = mock.get("revenue_growth_mock", 0)
    result["medium"]["breakdown"]["revenue_growth_yoy"] = min(10, max(1, round(5 + rev_g * 15)))

    # Long: Revenue CAGR
    cagr = mock.get("rev_cagr_mock", 0)
    result["long"]["breakdown"]["revenue_cagr_3y"] = min(10, max(1, round(5 + cagr * 20)))

    # Long: FCF yield
    fcf = mock.get("fcf_yield_mock")
    if fcf is not None:
        result["long"]["breakdown"]["fcf_yield"] = min(10, max(1, round(3 + fcf * 75)))

    # Short: analyst near-term
    result["short"]["breakdown"]["analyst_near_term"] = mock.get("recent_rec_score", 5)

    from config import HORIZON_WEIGHTS
    for h_key in ("short", "medium", "long"):
        w = HORIZON_WEIGHTS[h_key]
        sc = result[h_key]["breakdown"]
        total = sum(sc.get(k, 5) * w.get(k, 0) for k in w)
        result[h_key]["score"] = round(total, 1)

    return result


def run_demo():
    console.print(Rule("[bold cyan]Financial Analysis POC — DEMO MODE[/]"))
    console.print("[dim]Using mock data. Run `python main.py analyze AAPL` for live data.[/]\n")

    all_recs = []
    for ticker, mock in MOCK_STOCKS.items():
        md = MockData(ticker, mock)
        data = md.as_fetcher_dict()

        sec_filings = [{"form": "10-Q", "date": "2025-05-02"}, {"form": "10-K", "date": "2024-11-01"}]
        risk = _patched_score_risk(data, mock)
        horizons = _patched_score_horizons(data, mock)
        analysts = aggregate_analysts(data, sec_filings)
        rec = build_recommendation(ticker, mock["info"], risk, horizons, analysts)
        all_recs.append(rec)

        console.print(Rule(f"[bold]{ticker}[/]"))
        _print_full_report(rec)

    console.print(Rule("[bold green]FULL SUMMARY[/]"))
    all_recs.sort(key=lambda r: r["opportunity_score"], reverse=True)
    _print_summary_table(all_recs)


if __name__ == "__main__":
    run_demo()
