import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from trading.portfolio import Portfolio
from trading.performance import full_report
import engine
import yfinance as yf


def get_portfolio_summary() -> dict:
    portfolio = Portfolio.load()
    tickers = list(portfolio.positions.keys())
    current_prices: dict[str, float] = {}
    if tickers:
        data = yf.download(tickers, period="1d", auto_adjust=True, progress=False)
        if len(tickers) > 1:
            close = data["Close"]
        else:
            close = {tickers[0]: data["Close"]}
        for t in tickers:
            try:
                current_prices[t] = float(close[t].dropna().iloc[-1])
            except Exception:
                current_prices[t] = portfolio.positions[t]["avg_cost"]
    report = full_report(portfolio, current_prices)
    return report


def analyze_ticker(symbol: str) -> dict | None:
    return engine.analyze(symbol)
