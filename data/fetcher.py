import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime, timedelta


def fetch_stock_data(ticker: str) -> dict:
    """Fetch all data for a single ticker. Returns structured dict or raises."""
    stock = yf.Ticker(ticker)

    info = _safe(stock.info) or {}
    financials = _safe(stock.financials)
    balance_sheet = _safe(stock.balance_sheet)
    cashflow = _safe(stock.cashflow)
    history = _safe(lambda: stock.history(period="1y"))
    recommendations = _safe(stock.recommendations)
    analyst_price_targets = _safe(stock.analyst_price_targets) or {}

    return {
        "ticker": ticker,
        "info": info,
        "financials": financials,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "history": history,
        "recommendations": recommendations,
        "analyst_price_targets": analyst_price_targets,
        "fetched_at": datetime.utcnow().isoformat(),
    }


def fetch_instrument(symbol: str, period: str = "1y") -> dict:
    """
    Light fetch for non-equity instruments (ETFs, commodities, currencies, crypto).
    Returns info + price history. No fundamentals needed.
    """
    t = yf.Ticker(symbol)
    info = _safe(t.info) or {}
    history = _safe(lambda: t.history(period=period))
    return {
        "symbol": symbol,
        "info": info,
        "history": history,
    }


def fetch_history(symbol: str, period: str = "1y"):
    """Fetch just the price history for a symbol (used for benchmarks/RS)."""
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return None


def fetch_sec_recent_filings(ticker: str) -> list[dict]:
    """Pull recent 10-K/10-Q metadata from SEC EDGAR (no auth required)."""
    try:
        cik = _get_cik(ticker)
        if not cik:
            return []
        url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        resp = requests.get(url, headers={"User-Agent": "FinPOC/1.0 research@example.com"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        results = []
        for form, date, acc in zip(forms, dates, accessions):
            if form in ("10-K", "10-Q", "8-K"):
                results.append({"form": form, "date": date, "accession": acc})
        return results[:20]
    except Exception:
        return []


def _get_cik(ticker: str) -> str | None:
    try:
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
        resp = requests.get(url, headers={"User-Agent": "FinPOC/1.0 research@example.com"}, timeout=8)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        for hit in hits:
            entity = hit.get("_source", {})
            if entity.get("ticker", "").upper() == ticker.upper():
                return str(entity.get("entity_id", "")).lstrip("0")
        return None
    except Exception:
        return None


def _safe(source):
    try:
        if callable(source):
            return source()
        return source
    except Exception:
        return None


def batch_fetch(tickers: list[str], delay: float = 0.5) -> dict[str, dict]:
    """Fetch data for multiple tickers with a small delay to avoid rate limits."""
    results = {}
    for i, ticker in enumerate(tickers, 1):
        try:
            results[ticker] = fetch_stock_data(ticker)
        except Exception as e:
            results[ticker] = {"ticker": ticker, "error": str(e)}
        if i < len(tickers):
            time.sleep(delay)
    return results
