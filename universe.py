"""
Tradeable Universe — the full registry of instruments the system can trade.

Key insight: indices, commodities, and currencies are NOT just signals —
they are tradeable via ETFs. This also solves multi-country exposure:
trade Japan/Germany/India/Israel via country ETFs on US exchanges, in USD,
with no foreign data feeds.

Each instrument is classified by asset_class, which determines WHICH
analysis pipeline runs:
  - equity        → fundamental (risk/horizon/analyst) + signal overlay
  - index_etf     → technical (trend/momentum/RS) + macro overlay
  - sector_etf    → technical + sector rotation
  - country_etf   → technical + country macro
  - commodity     → technical + supply/macro + alternatives overlay
  - currency      → technical + rate-differential/macro
  - bond          → technical + rate regime
  - crypto        → technical + risk-appetite
"""

EQUITY = "equity"
INDEX_ETF = "index_etf"
SECTOR_ETF = "sector_etf"
COUNTRY_ETF = "country_etf"
COMMODITY = "commodity"
CURRENCY = "currency"
BOND = "bond"
CRYPTO = "crypto"

# ── Tradeable non-equity instruments ──────────────────────────────────────────

INSTRUMENTS: dict[str, dict] = {
    # ── Broad market indices (tradeable via ETF) ──
    "SPY":  {"name": "S&P 500",            "asset_class": INDEX_ETF, "region": "US",     "category": "Index"},
    "QQQ":  {"name": "Nasdaq 100",         "asset_class": INDEX_ETF, "region": "US",     "category": "Index"},
    "DIA":  {"name": "Dow Jones 30",       "asset_class": INDEX_ETF, "region": "US",     "category": "Index"},
    "IWM":  {"name": "Russell 2000",       "asset_class": INDEX_ETF, "region": "US",     "category": "Index"},
    "VTI":  {"name": "US Total Market",    "asset_class": INDEX_ETF, "region": "US",     "category": "Index"},

    # ── Country ETFs (multi-market exposure from US exchange) ──
    "EWJ":  {"name": "Japan",              "asset_class": COUNTRY_ETF, "region": "Japan",   "category": "Country"},
    "EWG":  {"name": "Germany",            "asset_class": COUNTRY_ETF, "region": "Germany", "category": "Country"},
    "INDA": {"name": "India",              "asset_class": COUNTRY_ETF, "region": "India",   "category": "Country"},
    "EIS":  {"name": "Israel",             "asset_class": COUNTRY_ETF, "region": "Israel",  "category": "Country"},
    "MCHI": {"name": "China",              "asset_class": COUNTRY_ETF, "region": "China",   "category": "Country"},
    "EFA":  {"name": "Developed ex-US",    "asset_class": COUNTRY_ETF, "region": "Global",  "category": "Country"},
    "EEM":  {"name": "Emerging Markets",   "asset_class": COUNTRY_ETF, "region": "Global",  "category": "Country"},

    # ── Sector ETFs (sector rotation) ──
    "XLK":  {"name": "Technology Sector",  "asset_class": SECTOR_ETF, "region": "US", "category": "Technology"},
    "XLF":  {"name": "Financials Sector",  "asset_class": SECTOR_ETF, "region": "US", "category": "Financial Services"},
    "XLE":  {"name": "Energy Sector",      "asset_class": SECTOR_ETF, "region": "US", "category": "Energy"},
    "XLV":  {"name": "Healthcare Sector",  "asset_class": SECTOR_ETF, "region": "US", "category": "Healthcare"},
    "XLI":  {"name": "Industrials Sector", "asset_class": SECTOR_ETF, "region": "US", "category": "Industrials"},
    "XLY":  {"name": "Cons. Discretionary","asset_class": SECTOR_ETF, "region": "US", "category": "Consumer Cyclical"},
    "XLP":  {"name": "Cons. Staples",      "asset_class": SECTOR_ETF, "region": "US", "category": "Consumer Defensive"},
    "XLU":  {"name": "Utilities Sector",   "asset_class": SECTOR_ETF, "region": "US", "category": "Utilities"},
    "XLB":  {"name": "Materials Sector",   "asset_class": SECTOR_ETF, "region": "US", "category": "Basic Materials"},
    "XLRE": {"name": "Real Estate Sector", "asset_class": SECTOR_ETF, "region": "US", "category": "Real Estate"},
    "XLC":  {"name": "Communication Svcs", "asset_class": SECTOR_ETF, "region": "US", "category": "Communication Services"},

    # ── Commodities (tradeable via ETF) ──
    "GLD":  {"name": "Gold",               "asset_class": COMMODITY, "region": "Global", "category": "Precious Metals"},
    "SLV":  {"name": "Silver",             "asset_class": COMMODITY, "region": "Global", "category": "Precious Metals"},
    "USO":  {"name": "Crude Oil",          "asset_class": COMMODITY, "region": "Global", "category": "Energy"},
    "UNG":  {"name": "Natural Gas",        "asset_class": COMMODITY, "region": "Global", "category": "Energy"},
    "CPER": {"name": "Copper",             "asset_class": COMMODITY, "region": "Global", "category": "Industrial Metals"},
    "DBC":  {"name": "Broad Commodities",  "asset_class": COMMODITY, "region": "Global", "category": "Broad"},
    "DBA":  {"name": "Agriculture",        "asset_class": COMMODITY, "region": "Global", "category": "Agriculture"},

    # ── Currencies (tradeable via ETF) ──
    "UUP":  {"name": "US Dollar Bull",     "asset_class": CURRENCY, "region": "US",     "category": "USD"},
    "UDN":  {"name": "US Dollar Bear",     "asset_class": CURRENCY, "region": "US",     "category": "USD"},
    "FXE":  {"name": "Euro",               "asset_class": CURRENCY, "region": "Europe", "category": "EUR"},
    "FXY":  {"name": "Japanese Yen",       "asset_class": CURRENCY, "region": "Japan",  "category": "JPY"},
    "FXB":  {"name": "British Pound",      "asset_class": CURRENCY, "region": "UK",     "category": "GBP"},

    # ── Bonds (tradeable via ETF) ──
    "TLT":  {"name": "20Y Treasury",       "asset_class": BOND, "region": "US", "category": "Long Treasury"},
    "IEF":  {"name": "7-10Y Treasury",     "asset_class": BOND, "region": "US", "category": "Mid Treasury"},
    "SHY":  {"name": "1-3Y Treasury",      "asset_class": BOND, "region": "US", "category": "Short Treasury"},
    "HYG":  {"name": "High Yield Bonds",   "asset_class": BOND, "region": "US", "category": "Credit"},
    "LQD":  {"name": "Investment Grade",   "asset_class": BOND, "region": "US", "category": "Credit"},
    "TIP":  {"name": "Inflation Protected","asset_class": BOND, "region": "US", "category": "TIPS"},

    # ── Crypto ──
    "BTC-USD": {"name": "Bitcoin",         "asset_class": CRYPTO, "region": "Global", "category": "Crypto"},
    "ETH-USD": {"name": "Ethereum",        "asset_class": CRYPTO, "region": "Global", "category": "Crypto"},
}


def classify(symbol: str) -> dict:
    """Return instrument metadata. Unknown symbols default to equity."""
    symbol = symbol.upper()
    if symbol in INSTRUMENTS:
        return {"symbol": symbol, **INSTRUMENTS[symbol]}
    # Default: treat as US equity
    return {"symbol": symbol, "name": symbol, "asset_class": EQUITY,
            "region": "US", "category": "Equity"}


def is_equity(symbol: str) -> bool:
    return classify(symbol)["asset_class"] == EQUITY


def get_by_class(asset_class: str) -> list[str]:
    return [s for s, m in INSTRUMENTS.items() if m["asset_class"] == asset_class]


def get_non_equity_universe() -> list[str]:
    """All tradeable non-equity instruments."""
    return list(INSTRUMENTS.keys())


def get_diversified_universe() -> list[str]:
    """
    A balanced cross-asset universe for the trader:
    broad indices + countries + sectors + commodities + currencies + bonds + crypto.
    """
    return [
        # Indices
        "SPY", "QQQ", "IWM",
        # Countries
        "EWJ", "EWG", "INDA", "EIS", "EEM",
        # Sectors
        "XLK", "XLF", "XLE", "XLV", "XLU",
        # Commodities
        "GLD", "SLV", "USO", "CPER", "DBC",
        # Currencies
        "UUP", "FXE", "FXY",
        # Bonds
        "TLT", "IEF", "HYG", "TIP",
        # Crypto
        "BTC-USD", "ETH-USD",
    ]


def asset_class_summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in INSTRUMENTS.values():
        counts[m["asset_class"]] = counts.get(m["asset_class"], 0) + 1
    return counts
