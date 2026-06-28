"""
Performance Analyzer — computes portfolio statistics.

Metrics:
  - Total return vs benchmark (alpha)
  - Sharpe ratio (risk-adjusted return)
  - Max drawdown
  - Win rate (% of trades that were profitable)
  - Avg win / avg loss
  - Conviction accuracy (from conviction_tracker)
"""
import math
from datetime import datetime

from trading.benchmark import compare, get_snapshots, days_since_start
from trading.conviction_tracker import accuracy_report


RISK_FREE_RATE = 0.045  # ~4.5% US T-bill yield (2025)


def full_report(portfolio, current_prices: dict[str, float]) -> dict:
    portfolio_value = portfolio.total_value(current_prices)
    orders = portfolio.orders

    bench = compare(portfolio_value, current_prices)
    conviction = accuracy_report()
    snapshots = get_snapshots()

    trade_stats = _trade_stats(orders)
    drawdown = _max_drawdown(snapshots)
    sharpe = _sharpe(snapshots)

    return {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "days_running": days_since_start(),
        "portfolio_value": round(portfolio_value, 2),
        "total_return_pct": bench.get("portfolio", {}).get("return_pct", 0),
        "vs_spy_alpha": bench.get("alpha", {}).get("SPY"),
        "vs_qqq_alpha": bench.get("alpha", {}).get("QQQ"),
        "benchmark": bench,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": drawdown,
        "trades": trade_stats,
        "positions": len(portfolio.positions),
        "cash_pct": round(portfolio.cash / portfolio_value * 100, 1) if portfolio_value else 100,
        "conviction_accuracy": conviction,
    }


def _trade_stats(orders: list[dict]) -> dict:
    sells = [o for o in orders if o["action"] == "SELL" and "pnl" in o]
    if not sells:
        return {"total_trades": len(orders), "completed_trades": 0}

    wins = [o["pnl"] for o in sells if o["pnl"] > 0]
    losses = [o["pnl"] for o in sells if o["pnl"] <= 0]
    total_pnl = sum(o["pnl"] for o in sells)

    return {
        "total_trades": len(orders),
        "completed_trades": len(sells),
        "win_rate_pct": round(len(wins) / len(sells) * 100, 1) if sells else 0,
        "avg_win_usd": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss_usd": round(sum(losses) / len(losses), 2) if losses else 0,
        "profit_factor": round(abs(sum(wins) / sum(losses)), 2) if losses and sum(losses) != 0 else None,
        "total_realized_pnl": round(total_pnl, 2),
    }


def _max_drawdown(snapshots: list[dict]) -> float | None:
    if len(snapshots) < 2:
        return None
    values = [s["portfolio_value"] for s in snapshots]
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def _sharpe(snapshots: list[dict]) -> float | None:
    """Annualized Sharpe using daily portfolio values from snapshots."""
    if len(snapshots) < 10:
        return None
    values = [s["portfolio_value"] for s in snapshots]
    returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
    if len(returns) < 2:
        return None
    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return None
    daily_rf = RISK_FREE_RATE / 252
    sharpe = (mean_r - daily_rf) / std_r * math.sqrt(252)
    return round(sharpe, 2)
