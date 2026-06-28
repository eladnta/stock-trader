SP100_TICKERS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AVGO", "ORCL", "CRM",
    "AMD", "QCOM", "TXN", "INTC", "IBM", "NOW", "AMAT", "MU", "LRCX", "ADI",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "AXP", "SCHW", "COF",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    # Consumer
    "AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "COST", "WMT", "PG", "KO",
    "PEP", "PM", "MO", "CL", "EL",
    # Industrials
    "CAT", "DE", "GE", "HON", "RTX", "LMT", "BA", "UPS", "FDX", "MMM",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG",
    # Communication
    "NFLX", "DIS", "T", "VZ", "CMCSA",
    # Utilities & Real Estate
    "NEE", "DUK", "SO", "AMT", "PLD",
    # Materials & Misc
    "LIN", "APD", "ECL", "NEM", "FCX",
    # More large caps
    "V", "MA", "PYPL", "BRK-B", "ACN", "TJX", "LOW", "CVS", "CI", "HUM",
]

SP100_TICKERS = sorted(set(SP100_TICKERS))

RISK_WEIGHTS = {
    "beta": 0.25,
    "debt_to_equity": 0.20,
    "current_ratio": 0.15,
    "interest_coverage": 0.15,
    "pe_vs_sector": 0.15,
    "revenue_growth_stability": 0.10,
}

HORIZON_WEIGHTS = {
    "short": {
        "price_momentum_3m": 0.35,
        "analyst_near_term": 0.35,
        "earnings_proximity": 0.30,
    },
    "medium": {
        "analyst_price_target_upside": 0.40,
        "eps_growth_fwd": 0.35,
        "revenue_growth_yoy": 0.25,
    },
    "long": {
        "revenue_cagr_3y": 0.30,
        "fcf_yield": 0.30,
        "pe_relative_to_growth": 0.25,
        "analyst_consensus_strength": 0.15,
    },
}

ANALYST_SITE_WEIGHTS = {
    "yahoo_consensus": 0.50,
    "sec_filing_sentiment": 0.30,
    "news_sentiment": 0.20,
}

RISK_THRESHOLDS = {
    "low": (1, 3),
    "medium": (3, 6),
    "high": (6, 10),
}

HORIZON_LABELS = {
    "short": "1–3 months",
    "medium": "3–12 months",
    "long": "1–5 years",
}
