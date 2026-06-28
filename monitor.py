#!/usr/bin/env python3
"""
Market Monitor — continuous signal collection and alerting.

Runs in a loop, collecting signals at appropriate intervals:
  - Alternatives (gold, oil, crypto, bonds): every 15 min
  - Macro (VIX, yields, dollar):             every 30 min
  - News (per portfolio ticker):             every 60 min
  - Full analysis cycle:                     every 4-6 hours

Usage:
  python monitor.py run              — start monitoring loop (Ctrl+C to stop)
  python monitor.py signals          — show current signal snapshot
  python monitor.py news AAPL        — news analysis for one ticker
  python monitor.py events           — recent logged events
  python monitor.py db               — database stats
"""
import sys, os, time, argparse
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

from signals.news_analyzer import analyze_global_news
from signals.stock_impact import compute_signal_overlay
from signals.event_db import db_summary, get_recent_events
from signals.collector import get_macro, get_alternatives, get_news
from trading.portfolio import Portfolio

console = Console()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_signals(args):
    console.print(Rule("[bold cyan]Signal Snapshot[/]"))

    with console.status("Fetching macro signals..."):
        macro = get_macro()
    with console.status("Fetching alternatives..."):
        alt = get_alternatives()
    with console.status("Fetching global news..."):
        global_news = analyze_global_news()

    # Regime
    regime = macro.get("regime", {})
    vix = macro.get("vix", {})
    yields = macro.get("yields", {})
    dollar = macro.get("dollar", {})

    regime_color = {"crisis": "red", "risk_off": "yellow", "risk_on": "green",
                    "late_cycle": "orange3", "neutral": "white"}.get(regime.get("regime"), "white")

    console.print(Panel(
        f"[bold {regime_color}]Regime: {regime.get('regime', 'N/A').upper()}[/]\n"
        f"{regime.get('description', '')}",
        title="Market Regime",
    ))
    console.print()

    # VIX + Yields + Dollar
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    t.add_column("Signal", style="cyan")
    t.add_column("Value")
    t.add_column("Direction")
    t.add_column("Label")

    vix_color = "red" if vix.get("value", 20) > 30 else "yellow" if vix.get("value", 20) > 20 else "green"
    t.add_row("VIX (Fear)", f"[{vix_color}]{vix.get('value', 'N/A')}[/]",
              vix.get("direction", ""), vix.get("label", ""))
    t.add_row("10Y Yield", f"{yields.get('ten_year', 'N/A')}%",
              yields.get("direction", ""), f"Curve: {yields.get('curve', 'N/A')}")
    t.add_row("Dollar (DXY)", f"{dollar.get('value', 'N/A')}",
              dollar.get("direction", ""), f"1M: {dollar.get('change_1m_pct', 'N/A')}%")
    console.print(t)

    # Alternative assets
    console.print("\n[bold]Alternative Assets:[/]")
    at = Table(box=box.SIMPLE)
    at.add_column("Asset", style="cyan"); at.add_column("Price")
    at.add_column("1D%", justify="right"); at.add_column("1M%", justify="right")
    at.add_column("Signal")

    for key in ("gold", "oil_wti", "copper", "bitcoin", "long_bond", "dollar", "reits", "nat_gas"):
        a = alt.get(key, {})
        if not a or not a.get("price"):
            continue
        d1 = a.get("change_1d_pct", 0)
        d1m = a.get("change_1m_pct", 0)
        dc = "green" if d1 > 0 else "red"
        mc = "green" if d1m > 0 else "red"
        signal = a.get("signal", {}).get("interpretation", "")[:60]
        at.add_row(a["name"][:22], f"${a['price']:,.2f}",
                   f"[{dc}]{d1:+.2f}%[/]", f"[{mc}]{d1m:+.2f}%[/]", signal)

    console.print(at)

    # Alt snapshot
    snap = alt.get("snapshot", {})
    snap_color = "green" if snap.get("risk_regime") == "risk_on" else "red" if snap.get("risk_regime") == "risk_off" else "white"
    console.print(f"\n  [{snap_color}]Alternatives signal: {snap.get('label', 'N/A')}[/]  (score {snap.get('score', 'N/A')}/10)")

    # Global macro news events
    active = global_news.get("active_macro_events", [])
    if active:
        console.print(f"\n[bold]Active Macro Event Tags:[/] {', '.join(active).replace('_', ' ')}")


def cmd_news(args):
    ticker = args.ticker.upper()
    console.print(Rule(f"[bold]News Analysis — {ticker}[/]"))
    with console.status(f"Analyzing {ticker} news..."):
        data = get_news(ticker, force=True)

    score = data.get("news_score", 5)
    score_color = "green" if score >= 6.5 else "red" if score <= 3.5 else "white"
    console.print(f"  News Score: [{score_color}]{score}/10[/]   Articles: {data.get('article_count', 0)}")
    console.print(f"  {data.get('sentiment_summary', '')}")

    tags = data.get("event_tags", [])
    if tags:
        console.print(f"  Event Tags: [bold]{', '.join(tags).replace('_', ' ')}[/]")

    if data.get("top_positive"):
        console.print("\n  [green]Positive headlines:[/]")
        for h in data["top_positive"]:
            console.print(f"    + {h}")

    if data.get("top_negative"):
        console.print("\n  [red]Negative headlines:[/]")
        for h in data["top_negative"]:
            console.print(f"    - {h}")

    if args.verbose and data.get("articles"):
        console.print("\n  [bold]All articles:[/]")
        for a in data["articles"]:
            sc = a.get("net_score", 0)
            c = "green" if sc > 0 else "red" if sc < 0 else "dim"
            console.print(f"  [{c}]{a['published']} | {a['title'][:80]}[/]")


def cmd_stock_signals(args):
    """Full signal overlay for a specific stock."""
    ticker = args.ticker.upper()
    console.print(Rule(f"[bold]Signal Overlay — {ticker}[/]"))

    with console.status("Collecting signals..."):
        macro = get_macro()
        alt = get_alternatives()
        news = get_news(ticker)

    # Need sector — fetch from yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "Technology")
        price = info.get("currentPrice", 0)
    except Exception:
        sector, price = "Technology", 0

    overlay = compute_signal_overlay(ticker, sector, news, macro, alt, base_opportunity=5.0)

    console.print(f"  Sector: {sector}   Price: ${price}")
    console.print(f"  Base Score: {overlay['base_score']}  →  [bold]Adjusted: {overlay['adjusted_score']}/10[/]")
    console.print(f"  {overlay['signal_narrative']}")
    console.print()

    for adj_key, adj_data in overlay.get("adjustments", {}).items():
        total = adj_data.get("total", 0)
        color = "green" if total > 0.1 else "red" if total < -0.1 else "dim"
        console.print(f"  {adj_key:12s}  [{color}]{total:+.2f}[/]")


def cmd_events(args):
    days = getattr(args, 'days', 30)
    ticker = getattr(args, 'ticker', None)
    events = get_recent_events(ticker=ticker, days=days)
    if not events:
        console.print("[dim]No events logged yet.[/]")
        return
    t = Table(title=f"Events (last {days} days)", box=box.ROUNDED)
    t.add_column("Date", width=10); t.add_column("Type", width=20)
    t.add_column("Ticker", width=6); t.add_column("Description")
    for e in events:
        t.add_row(e["event_date"][:10], e["event_type"].replace("_", " "),
                  e.get("ticker") or "", e.get("description", "")[:70])
    console.print(t)


def cmd_modules(args):
    """List all registered signal modules and their metadata."""
    import signals.modules  # noqa: F401  registers all signals
    from signals.registry import registry_summary

    rows = registry_summary()
    t = Table(title="Registered Signal Modules", box=box.ROUNDED)
    t.add_column("Signal", style="cyan")
    t.add_column("Cost")
    t.add_column("Applies to")
    t.add_column("Weight", justify="center")
    t.add_column("Enabled", justify="center")
    t.add_column("Description")
    for r in rows:
        cost_color = {"free": "green", "paid": "yellow", "llm": "magenta"}.get(r["cost"], "white")
        enabled = "[green]✓[/]" if r["enabled"] else "[dim]✗[/]"
        t.add_row(
            r["name"], f"[{cost_color}]{r['cost']}[/]",
            ", ".join(r["applies_to"]), str(r["weight"]),
            enabled, r["description"][:55],
        )
    console.print(t)
    console.print("\n[dim]Only FREE-tier signals run by default. "
                  "Add PAID/LLM tiers to SignalConfig.allowed_costs to enable more.[/]")


def cmd_db(args):
    stats = db_summary()
    console.print(Panel(
        f"Events logged:      {stats['events_logged']}\n"
        f"Outcomes measured:  {stats['outcomes_measured']}\n"
        f"Accuracy patterns:  {stats['accuracy_patterns']}\n"
        f"\nCache: {stats['cache']}",
        title="Event Database Stats",
    ))


def cmd_run(args):
    """Continuous monitoring loop."""
    interval = getattr(args, 'interval', 30)
    console.print(Rule(f"[bold cyan]Monitor — refreshing every {interval} min[/]"))
    console.print("[dim]Ctrl+C to stop[/]\n")

    while True:
        try:
            now = datetime.now().strftime("%H:%M:%S")
            console.print(f"[dim]{now}[/] Refreshing signals...")

            macro = get_macro(force=True)
            alt = get_alternatives(force=True)

            regime = macro.get("regime", {}).get("regime", "?")
            vix = macro.get("vix", {}).get("value", 0)
            vix_color = "red" if vix > 30 else "yellow" if vix > 20 else "green"
            snap = alt.get("snapshot", {}).get("risk_regime", "?")

            console.print(
                f"  Regime: [bold]{regime}[/]  "
                f"VIX: [{vix_color}]{vix:.1f}[/]  "
                f"Alt signal: {snap}"
            )

            # Refresh news for portfolio positions
            portfolio = Portfolio.load()
            for ticker in portfolio.positions:
                try:
                    news = get_news(ticker, force=True)
                    score = news.get("news_score", 5)
                    tags = news.get("event_tags", [])
                    if score < 3 or score > 7.5 or tags:
                        color = "green" if score > 7.5 else "red"
                        console.print(
                            f"  [{color}]ALERT {ticker}[/]: score={score}  "
                            f"tags={', '.join(tags[:3]).replace('_', ' ')}"
                        )
                except Exception:
                    pass

            console.print(f"  [dim]Next refresh in {interval} min[/]")
            time.sleep(interval * 60)

        except KeyboardInterrupt:
            console.print("\n[dim]Monitor stopped.[/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            time.sleep(60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Market Monitor")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("signals", help="Current macro + alternatives snapshot")

    p_news = sub.add_parser("news", help="News analysis for a ticker")
    p_news.add_argument("ticker"); p_news.add_argument("-v", "--verbose", action="store_true")

    p_stock = sub.add_parser("stock", help="Full signal overlay for a stock")
    p_stock.add_argument("ticker")

    p_ev = sub.add_parser("events", help="Recent logged events")
    p_ev.add_argument("--days", type=int, default=30)
    p_ev.add_argument("--ticker", default=None)

    sub.add_parser("modules", help="List registered signal modules")
    sub.add_parser("db", help="Database stats")

    p_run = sub.add_parser("run", help="Start continuous monitoring loop")
    p_run.add_argument("--interval", type=int, default=30, help="Minutes between refreshes")

    args = parser.parse_args()
    dispatch = {
        "signals": cmd_signals, "news": cmd_news, "stock": cmd_stock_signals,
        "events": cmd_events, "db": cmd_db, "run": cmd_run,
        "modules": cmd_modules,
    }
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
