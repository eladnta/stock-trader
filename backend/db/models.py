from datetime import datetime
from sqlalchemy import String, Float, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cash: Mapped[float] = mapped_column(Float)
    total_value: Mapped[float] = mapped_column(Float)
    total_return_pct: Mapped[float] = mapped_column(Float)
    positions: Mapped[dict] = mapped_column(JSON)   # {ticker: {shares, avg_cost, current_price, pnl}}
    metrics: Mapped[dict] = mapped_column(JSON)     # sharpe, drawdown, alpha_spy, alpha_qqq

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ticker: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(8))   # BUY | SELL
    shares: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(512), default="")

class ConvictionRecord(Base):
    __tablename__ = "conviction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    horizon: Mapped[str] = mapped_column(String(8))   # 1W | 1M | 3M | 6M | 12M
    predicted_action: Mapped[str] = mapped_column(String(8))
    correct: Mapped[bool | None] = mapped_column(default=None)
    accuracy_pct: Mapped[float | None] = mapped_column(Float, default=None)
