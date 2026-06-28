from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import PortfolioSnapshot


async def save_snapshot(session: AsyncSession, summary: dict) -> None:
    snap = PortfolioSnapshot(
        captured_at=datetime.utcnow(),
        cash=summary.get("portfolio_value", 0) * (summary.get("cash_pct", 0) / 100),
        total_value=summary.get("portfolio_value", 0),
        total_return_pct=summary.get("total_return_pct", 0),
        positions=summary.get("positions", {}),
        metrics={
            "sharpe_ratio": summary.get("sharpe_ratio"),
            "max_drawdown_pct": summary.get("max_drawdown_pct"),
            "vs_spy_alpha": summary.get("vs_spy_alpha"),
            "vs_qqq_alpha": summary.get("vs_qqq_alpha"),
        },
    )
    session.add(snap)
    await session.commit()
