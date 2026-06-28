#!/usr/bin/env python3
"""
Financial Analysis POC — US Market
Usage:
  python main.py analyze AAPL
  python main.py analyze AAPL MSFT NVDA
  python main.py top [--n 10]
  python main.py scan [--tickers all|AAPL,MSFT,...]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

from config import SP100_TICKERS
from data.fetcher import fetch_stock_data, fetch_sec_recent_filings
from analysis.risk_scorer import score_risk
from analysis.horizon_scorer import score_horizons
from analysis.analyst_aggregator import aggregate_analysts
from analysis.recommender import build_recommendation

console = Console()


def analyze_ticker(ticker: str, verbose: bool = False) -> dict | None:
    ticker = ticker.upper()
    with console.status(f"Fetching [bold cyan]{ticker}[/]..."):
        try:
            data = fetch_stock_data(ticker)
        except Exception as e:
            console.print(f"[red]Error fetching {ticker}: {e}[/]")
            return None

    if data.get("error"):
        console.print(f"[red]{ticker}: {data['error']}[/]")
        return None

    info = data.get("info", {})
    if not info:
        console.print(f"[yellow]{ticker}: No data returned (delisted or invalid?)[/]")
        return None

    sec_filings = fetch_sec_recent_filings(ticker)
    risk = score_risk(data)
    horizons = score_horizons(data)
    analysts = aggregate_analysts(data, sec_filings)
    rec = build_recommendation(ticker, info, risk, horizons, analysts)

    if verbose:
        _print_full_report(rec)
    return rec


def _print_full_report(rec: dict):
    ticker = rec["ticker"]
    action_color = _action_color(rec["action"])

    header = Text()
    header.append(f"  {ticker} — {rec['name']}  ", style="bold white on dark_blue")
    console.print(Panel(header, expand=False))

    console.print(f"  [dim]Sector:[/] {rec['sector']}   "
                  f"[dim]Price:[/] ${rec['price']}   "
                  f"[dim]Market Cap:[/] {rec['market_cap']}")
    console.print()

    # Recommendation box
    console.print(Panel(
        f"[bold {action_color}]  {rec['action']}  [/]\n"
        f"Opportunity Score: [bold]{rec['opportunity_score']}/10[/]",
        title="[bold]RECOMMENDATION[/]",
        expand=False,
    ))
    console.print()

    # Risk
    risk_color = {"Low": "green", "Medium": "yellow", "High": "red"}.get(rec["risk"]["label"], "white")
    console.print(f"[bold]RISK[/]  Score: [{risk_color}]{rec['risk']['score']}/10[/]  "
                  f"Label: [{risk_color}]{rec['risk']['label']}[/]")
    for metric, note in rec["risk"]["breakdown"].items():
        console.print(f"  [dim]{metric}:[/] {note}")
    console.print()

    # Horizons
    console.print("[bold]TIME HORIZONS[/]")
    ht = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    ht.add_column("Horizon", style="dim")
    ht.add_column("Period")
    ht.add_column("Score", justify="center")
    ht.add_column("Signal")
    for key in ("short", "medium", "long"):
        h = rec["horizons"][key]
        score = h["score"]
        signal = _score_signal(score)
        ht.add_row(key.capitalize(), h["label"], str(score), signal)
    console.print(ht)

    # Analysts
    a = rec["analysts"]
    console.print(f"[bold]ANALYST CONSENSUS[/]  "
                  f"Score: {a['score']}/10   "
                  f"Rating: [bold]{a['rating']}[/]   "
                  f"({a['count']} analysts)")
    if a["price_target"]:
        console.print(f"  Price Target: ${a['price_target']:.2f}   "
                      f"Range: {a['price_target_range']}")
    console.print()


def cmd_analyze(args):
    tickers = [t.upper() for t in args.tickers]
    results = []
    for t in tickers:
        rec = analyze_ticker(t, verbose=len(tickers) == 1)
        if rec:
            results.append(rec)
    if len(tickers) > 1:
        _print_summary_table(results)


def cmd_top(args):
    n = args.n
    tickers = SP100_TICKERS
    console.print(f"[bold]Scanning {len(tickers)} tickers for top {n}...[/]")
    results = []
    for t in tickers:
        rec = analyze_ticker(t, verbose=False)
        if rec:
            results.append(rec)

    results.sort(key=lambda r: r["opportunity_score"], reverse=True)
    console.print(f"\n[bold green]Top {n} Opportunities[/]\n")
    _print_summary_table(results[:n])


def cmd_scan(args):
    raw = args.tickers
    if raw == "all" or raw is None:
        tickers = SP100_TICKERS
    else:
        tickers = [t.strip().upper() for t in raw.split(",")]

    console.print(f"[bold]Scanning {len(tickers)} tickers...[/]")
    results = []
    for t in tickers:
        rec = analyze_ticker(t, verbose=False)
        if rec:
            results.append(rec)

    results.sort(key=lambda r: r["opportunity_score"], reverse=True)
    _print_summary_table(results)


def _print_summary_table(results: list[dict]):
    t = Table(title="Financial Analysis Summary", box=box.ROUNDED, show_lines=False)
    t.add_column("Ticker", style="bold cyan", width=8)
    t.add_column("Name", width=22)
    t.add_column("Sector", width=18)
    t.add_column("Price", justify="right", width=8)
    t.add_column("Oppty", justify="center", width=6)
    t.add_column("Risk", justify="center", width=10)
    t.add_column("Short", justify="center", width=6)
    t.add_column("Mid", justify="center", width=6)
    t.add_column("Long", justify="center", width=6)
    t.add_column("Analysts", justify="center", width=12)
    t.add_column("Action", width=20)

    for r in results:
        risk_label = r["risk"]["label"]
        risk_color = {"Low": "green", "Medium": "yellow", "High": "red"}.get(risk_label, "white")
        action_color = _action_color(r["action"])
        t.add_row(
            r["ticker"],
            r["name"][:22],
            r["sector"][:18],
            f"${r['price']:.2f}" if r["price"] else "N/A",
            str(r["opportunity_score"]),
            f"[{risk_color}]{risk_label}[/]",
            str(r["horizons"]["short"]["score"]),
            str(r["horizons"]["medium"]["score"]),
            str(r["horizons"]["long"]["score"]),
            f"{r['analysts']['rating']} ({r['analysts']['count']})",
            f"[{action_color}]{r['action']}[/]",
        )

    console.print(t)


def _action_color(action: str) -> str:
    mapping = {
        "Strong Buy": "bright_green", "Buy": "green", "Buy (elevated risk)": "yellow",
        "Hold": "white", "Reduce": "orange3", "Sell": "red",
    }
    return mapping.get(action, "white")


def _score_signal(score: float) -> str:
    if score >= 7.5:
        return "[bright_green]Bullish[/]"
    elif score >= 5.5:
        return "[green]Positive[/]"
    elif score >= 4.5:
        return "[white]Neutral[/]"
    elif score >= 3.0:
        return "[orange3]Cautious[/]"
    else:
        return "[red]Bearish[/]"


def main():
    parser = argparse.ArgumentParser(description="Financial Analysis POC — US Market")
    sub = parser.add_subparsers(dest="command")

    p_analyze = sub.add_parser("analyze", help="Analyze one or more tickers")
    p_analyze.add_argument("tickers", nargs="+", help="Ticker symbols, e.g. AAPL MSFT")

    p_top = sub.add_parser("top", help="Find top opportunities across S&P 100")
    p_top.add_argument("--n", type=int, default=10, help="Number of top picks (default: 10)")

    p_scan = sub.add_parser("scan", help="Scan a set of tickers")
    p_scan.add_argument("--tickers", default="all",
                        help="'all' for S&P 100 or comma-separated: AAPL,MSFT,NVDA")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "top":
        cmd_top(args)
    elif args.command == "scan":
        cmd_scan(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
