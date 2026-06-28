#!/usr/bin/env python3
"""
Paper Trader — $10,000 virtual portfolio
==========================================
Commands:
  python trader.py run              — analyze + execute pending orders + snapshot
  python trader.py status           — portfolio snapshot + P&L
  python trader.py performance      — full stats vs SPY/QQQ
  python trader.py conviction       — prediction accuracy report
  python trader.py pending          — show pending orders
  python trader.py orders           — full order history
  python trader.py positions        — current holdings
  python trader.py reset            — wipe state and start fresh (asks confirmation)
  python trader.py demo             — dry-run with mock data, no state written
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

import universe
import engine
from config import SP100_TICKERS
from trading.portfolio import Portfolio, INITIAL_CASH
from trading.position_sizer import calc_position_size
from trading.order_engine import submit_order, get_due_orders, get_pending_orders
from trading.conviction_tracker import record_prediction, update_checkpoints, accuracy_report, pending_checkpoints
from trading import benchmark, performance

console = Console()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_and_analyze(ticker: str) -> dict | None:
    """Delegate to the central engine — routes by asset class + applies signals."""
    rec = engine.analyze(ticker, with_signals=True)
    if rec and rec.get("error"):
        console.print(f"[dim red]{ticker}: {rec['error']}[/]")
        return None
    return rec


def _current_prices(portfolio: Portfolio, extra: list[str] | None = None) -> dict[str, float]:
    tickers = list(portfolio.positions.keys()) + (extra or []) + ["SPY", "QQQ"]
    prices = {}
    for t in set(tickers):
        try:
            import yfinance as yf
            info = yf.Ticker(t).info
            p = info.get("currentPrice") or info.get("regularMarketPrice")
            if p:
                prices[t] = float(p)
        except Exception:
            pass
    return prices


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_run(args):
    """Full cycle: analyze → size → submit → execute due → snapshot."""
    portfolio = Portfolio.load()
    console.print(Rule("[bold cyan]Paper Trader — Run Cycle[/]"))

    # 1. Process pending orders that are now due
    console.print("\n[bold]1. Processing due orders...[/]")
    prices_for_execution = _current_prices(portfolio)
    due = get_due_orders(prices_for_execution)
    for o in due:
        try:
            if o["action"] == "BUY":
                portfolio.buy(o["ticker"], o["shares"], o["exec_price"],
                              f"Auto-execute (delay {o['delay_minutes']}m, slippage {o['slippage_pct']}%)")
                console.print(f"  [green]✓ BUY  {o['ticker']}  {o['shares']:.2f} @ ${o['exec_price']:.2f}[/]")
            elif o["action"] == "SELL":
                portfolio.sell(o["ticker"], o["shares"], o["exec_price"],
                               f"Auto-execute (delay {o['delay_minutes']}m, slippage {o['slippage_pct']}%)")
                console.print(f"  [red]✓ SELL {o['ticker']}  {o['shares']:.2f} @ ${o['exec_price']:.2f}[/]")
        except Exception as e:
            console.print(f"  [red]✗ {o['action']} {o['ticker']}: {e}[/]")

    if not due:
        console.print("  [dim]No orders due[/]")

    # 2. Update conviction checkpoints
    console.print("\n[bold]2. Updating conviction checkpoints...[/]")
    measured = update_checkpoints(prices_for_execution)
    for m in measured:
        icon = "[green]✓[/]" if m["correct"] else "[red]✗[/]"
        console.print(f"  {icon} {m['ticker']} {m['checkpoint']}: {m['return_pct']:+.1f}%")
    if not measured:
        console.print("  [dim]No checkpoints due[/]")

    # 3. Analyze tickers and generate new signals
    console.print("\n[bold]3. Analyzing universe...[/]")
    universe_choice = getattr(args, "universe", "mixed")
    if universe_choice == "equities":
        tickers = SP100_TICKERS[:30]
    elif universe_choice == "cross-asset":
        tickers = universe.get_diversified_universe()
    else:  # mixed: top equities + full cross-asset
        tickers = SP100_TICKERS[:20] + universe.get_diversified_universe()
    console.print(f"  [dim]Universe: {universe_choice} ({len(tickers)} instruments)[/]")
    new_orders = []

    for ticker in tickers:
        rec = _fetch_and_analyze(ticker)
        if not rec:
            continue

        current_prices_all = {**prices_for_execution, ticker: rec.get("price", 0)}
        sizing = calc_position_size(rec, portfolio, current_prices_all)

        if sizing["action"] in ("BUY", "SELL"):
            order = submit_order(
                sizing["action"], ticker, sizing["shares"],
                rec.get("price", 0),
                note=f"Signal: {rec['action']} (score={rec['opportunity_score']}) | {sizing['reason']}",
            )
            new_orders.append((rec, order, sizing))

            # Record conviction prediction
            if sizing["action"] == "BUY":
                record_prediction(rec, entry_price=rec.get("price", 0))

            color = "green" if sizing["action"] == "BUY" else "red"
            console.print(
                f"  [{color}]{sizing['action']}[/] {ticker:6s} "
                f"${sizing['value_usd']:.0f}  →  executes in ~{order['delay_minutes']:.0f}m  "
                f"| {rec['action']} (opp={rec['opportunity_score']})"
            )

    if not new_orders:
        console.print("  [dim]No new signals[/]")

    # 4. Snapshot benchmark
    console.print("\n[bold]4. Benchmark snapshot...[/]")
    prices_now = _current_prices(portfolio)
    pv = portfolio.total_value(prices_now)
    spy_p = prices_now.get("SPY")
    qqq_p = prices_now.get("QQQ")
    if spy_p and qqq_p:
        benchmark.initialize(spy_p, qqq_p)
        benchmark.snapshot(pv, prices_now)
        console.print(f"  Portfolio: ${pv:,.2f}  SPY: ${spy_p:.2f}  QQQ: ${qqq_p:.2f}")

    console.print(Rule("[dim]Cycle complete[/]"))


def cmd_status(args):
    portfolio = Portfolio.load()
    prices = _current_prices(portfolio)
    pv = portfolio.total_value(prices)
    pnl = pv - INITIAL_CASH
    pnl_pct = pnl / INITIAL_CASH * 100

    pnl_color = "green" if pnl >= 0 else "red"
    console.print(Panel(
        f"Portfolio Value:  [bold]${pv:,.2f}[/]\n"
        f"P&L:             [{pnl_color}]{'+' if pnl>=0 else ''}{pnl:.2f} ({pnl_pct:+.1f}%)[/]\n"
        f"Cash:             ${portfolio.cash:,.2f} ({portfolio.cash/pv*100:.1f}%)\n"
        f"Positions:        {len(portfolio.positions)}",
        title="Portfolio Status",
    ))

    if portfolio.positions:
        t = Table(box=box.SIMPLE)
        t.add_column("Ticker", style="cyan")
        t.add_column("Shares", justify="right")
        t.add_column("Avg Cost", justify="right")
        t.add_column("Current", justify="right")
        t.add_column("Value", justify="right")
        t.add_column("P&L", justify="right")
        t.add_column("P&L%", justify="right")
        t.add_column("Weight", justify="right")

        for ticker, pos in sorted(portfolio.positions.items()):
            price = prices.get(ticker, pos["avg_cost"])
            val = pos["shares"] * price
            upnl = (price - pos["avg_cost"]) * pos["shares"]
            upnl_pct = (price - pos["avg_cost"]) / pos["avg_cost"] * 100
            color = "green" if upnl >= 0 else "red"
            t.add_row(
                ticker,
                f"{pos['shares']:.2f}",
                f"${pos['avg_cost']:.2f}",
                f"${price:.2f}",
                f"${val:,.2f}",
                f"[{color}]{upnl:+.2f}[/]",
                f"[{color}]{upnl_pct:+.1f}%[/]",
                f"{val/pv*100:.1f}%",
            )
        console.print(t)


def cmd_performance(args):
    portfolio = Portfolio.load()
    prices = _current_prices(portfolio)
    report = performance.full_report(portfolio, prices)

    console.print(Rule("[bold]Performance Report[/]"))
    console.print(f"  As of: {report['as_of']}   Running: {report['days_running']} days")
    console.print()

    # Returns
    ret = report["total_return_pct"]
    color = "green" if ret >= 0 else "red"
    console.print(f"  Portfolio Return:   [{color}]{ret:+.1f}%[/]")
    console.print(f"  vs SPY (alpha):     {report['vs_spy_alpha']:+.1f}%" if report.get("vs_spy_alpha") is not None else "  vs SPY: N/A")
    console.print(f"  vs QQQ (alpha):     {report['vs_qqq_alpha']:+.1f}%" if report.get("vs_qqq_alpha") is not None else "  vs QQQ: N/A")
    console.print()

    bench = report.get("benchmark", {}).get("benchmarks", {})
    for b, bd in bench.items():
        bret = bd.get("return_pct", 0)
        bc = "green" if bret >= 0 else "red"
        console.print(f"  {b}:  ${bd['value']:,.2f}  [{bc}]{bret:+.1f}%[/]")
    console.print()

    # Risk metrics
    console.print(f"  Sharpe Ratio:     {report['sharpe_ratio'] or 'N/A (need 10+ snapshots)'}")
    console.print(f"  Max Drawdown:     {('-' + str(report['max_drawdown_pct']) + '%') if report['max_drawdown_pct'] else 'N/A'}")
    console.print()

    # Trade stats
    ts = report["trades"]
    console.print(f"  Total Trades:     {ts['total_trades']}  Completed: {ts.get('completed_trades', 0)}")
    if ts.get("completed_trades", 0) > 0:
        console.print(f"  Win Rate:         {ts['win_rate_pct']}%")
        console.print(f"  Avg Win/Loss:     ${ts['avg_win_usd']:+.2f} / ${ts['avg_loss_usd']:+.2f}")
        if ts.get("profit_factor"):
            console.print(f"  Profit Factor:    {ts['profit_factor']:.2f}")
        console.print(f"  Realized P&L:     ${ts['total_realized_pnl']:+.2f}")


def cmd_conviction(args):
    report = accuracy_report()
    console.print(Rule("[bold]Conviction Accuracy Report[/]"))

    if report.get("total_predictions", 0) == 0:
        console.print("[dim]No predictions recorded yet. Run `python trader.py run` first.[/]")
        return

    console.print(f"  Total Predictions: {report['total_predictions']}")
    console.print(f"  Measured:          {report['total_measured']}")

    if report.get("overall"):
        o = report["overall"]
        console.print(f"\n  Overall Win Rate:  {o['win_rate_pct']}%  (n={o['n']})")
        console.print(f"  Avg Return:        {o['avg_return_pct']:+.2f}%")

    if report.get("by_horizon"):
        console.print("\n  [bold]By Horizon:[/]")
        for h, s in report["by_horizon"].items():
            if s:
                console.print(f"    {h:4s}  Win={s['win_rate_pct']}%  Avg={s['avg_return_pct']:+.2f}%  n={s['n']}")

    if report.get("by_sector"):
        console.print("\n  [bold]By Sector:[/]")
        for sec, s in report["by_sector"].items():
            if s:
                console.print(f"    {sec[:22]:22s}  Win={s['win_rate_pct']}%  Avg={s['avg_return_pct']:+.2f}%  n={s['n']}")

    if report.get("by_risk"):
        console.print("\n  [bold]By Risk Tier:[/]")
        for risk, s in report["by_risk"].items():
            if s:
                console.print(f"    {risk:8s}  Win={s['win_rate_pct']}%  Avg={s['avg_return_pct']:+.2f}%  n={s['n']}")

    # Upcoming checkpoints
    upcoming = pending_checkpoints()[:10]
    if upcoming:
        console.print(f"\n  [bold]Next {len(upcoming)} Checkpoints:[/]")
        for cp in upcoming:
            console.print(f"    {cp['ticker']:6s} {cp['checkpoint']:4s} → {cp['due_date']}  ({cp['days_left']}d)  entry ${cp['entry_price']:.2f}")


def cmd_pending(args):
    orders = get_pending_orders()
    if not orders:
        console.print("[dim]No pending orders.[/]")
        return
    t = Table(title="Pending Orders", box=box.ROUNDED)
    t.add_column("Ticker"); t.add_column("Action"); t.add_column("Shares", justify="right")
    t.add_column("Submit Price", justify="right"); t.add_column("Exec At"); t.add_column("Note")
    for o in orders:
        color = "green" if o["action"] == "BUY" else "red"
        t.add_row(o["ticker"], f"[{color}]{o['action']}[/]", f"{o['shares']:.2f}",
                  f"${o['submitted_price']:.2f}", o["execute_at"][:16], o.get("note", "")[:60])
    console.print(t)


def cmd_orders(args):
    portfolio = Portfolio.load()
    if not portfolio.orders:
        console.print("[dim]No orders yet.[/]")
        return
    t = Table(title="Order History", box=box.ROUNDED)
    t.add_column("#"); t.add_column("Date"); t.add_column("Action")
    t.add_column("Ticker"); t.add_column("Shares", justify="right")
    t.add_column("Price", justify="right"); t.add_column("Value", justify="right")
    t.add_column("P&L", justify="right")
    for o in portfolio.orders[-50:]:
        color = "green" if o["action"] == "BUY" else "red"
        pnl_str = f"{o['pnl']:+.2f}" if "pnl" in o else ""
        pnl_color = "green" if o.get("pnl", 0) >= 0 else "red"
        t.add_row(str(o["id"]), o["timestamp"][:10], f"[{color}]{o['action']}[/]",
                  o["ticker"], f"{o['shares']:.2f}", f"${o['price']:.2f}",
                  f"${o['value']:.2f}", f"[{pnl_color}]{pnl_str}[/]")
    console.print(t)


def cmd_reset(args):
    import glob
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    files = glob.glob(os.path.join(state_dir, "*.json"))
    if not files:
        console.print("[dim]Nothing to reset.[/]")
        return
    console.print(f"[bold red]This will delete all state: {[os.path.basename(f) for f in files]}[/]")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    if confirm == "yes":
        for f in files:
            os.remove(f)
        console.print("[green]State cleared. Fresh $10,000 portfolio ready.[/]")
    else:
        console.print("[dim]Cancelled.[/]")


def cmd_demo(args):
    """Dry-run with mock data — shows what the trader would do without touching state."""
    from demo import MOCK_STOCKS, MockData, _patched_score_risk, _patched_score_horizons
    from analysis.analyst_aggregator import aggregate_analysts
    from analysis.recommender import build_recommendation

    console.print(Rule("[bold cyan]Paper Trader DEMO — No state written[/]"))
    console.print("[dim]Using mock data. Simulates one full trading cycle.[/]\n")

    portfolio = Portfolio()  # fresh, in-memory only
    prices_mock = {t: m["info"]["currentPrice"] for t, m in MOCK_STOCKS.items()}
    prices_mock["SPY"] = 538.0
    prices_mock["QQQ"] = 466.0

    for ticker, mock in MOCK_STOCKS.items():
        md = MockData(ticker, mock)
        data = md.as_fetcher_dict()
        risk = _patched_score_risk(data, mock)
        horizons = _patched_score_horizons(data, mock)
        analysts = aggregate_analysts(data, [{"form": "10-Q", "date": "2025-05-02"}])
        rec = build_recommendation(ticker, mock["info"], risk, horizons, analysts)

        sizing = calc_position_size(rec, portfolio, prices_mock)
        console.print(
            f"  [cyan]{ticker:6s}[/]  Signal: [bold]{rec['action']:22s}[/]  "
            f"Opp={rec['opportunity_score']}  Risk={rec['risk']['label']:6s}  →  "
            f"[{'green' if sizing['action']=='BUY' else 'yellow'}]{sizing['action']:4s}[/] "
            f"${sizing['value_usd']:.0f}  |  {sizing['reason']}"
        )

        if sizing["action"] == "BUY":
            portfolio.buy(ticker, sizing["shares"], prices_mock[ticker], "demo")

    console.print()
    pv = portfolio.total_value(prices_mock)
    console.print(f"  [bold]Portfolio after cycle:[/]  ${pv:,.2f}  |  Cash: ${portfolio.cash:,.2f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Paper Trader — $10,000 virtual portfolio")
    sub = parser.add_subparsers(dest="command")
    p_run = sub.add_parser("run", help="Full analysis + order cycle")
    p_run.add_argument("--universe", choices=["mixed", "equities", "cross-asset"],
                       default="mixed", help="Which universe to trade (default: mixed)")
    sub.add_parser("status",      help="Portfolio snapshot")
    sub.add_parser("performance", help="Full stats vs SPY/QQQ")
    sub.add_parser("conviction",  help="Prediction accuracy report")
    sub.add_parser("pending",     help="Show pending orders")
    sub.add_parser("orders",      help="Full order history")
    sub.add_parser("positions",   help="Current holdings (alias for status)")
    sub.add_parser("reset",       help="Wipe all state and start fresh")
    sub.add_parser("demo",        help="Dry-run with mock data")

    args = parser.parse_args()
    dispatch = {
        "run": cmd_run, "status": cmd_status, "performance": cmd_performance,
        "conviction": cmd_conviction, "pending": cmd_pending,
        "orders": cmd_orders, "positions": cmd_status,
        "reset": cmd_reset, "demo": cmd_demo,
    }
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
