"""Tests for positions, analysis, signals, and cycle routers."""
import sys
import os
import types
import unittest.mock as mock

# Set DATABASE_URL env var before any imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# Insert repo root so 'backend' package resolves correctly
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


# Stub SQLAlchemy (broken on Python 3.14)
_stub("sqlalchemy")
_stub("sqlalchemy.ext")
sa_async = _stub(
    "sqlalchemy.ext.asyncio",
    create_async_engine=mock.MagicMock(return_value=mock.MagicMock()),
    AsyncSession=object,
    async_sessionmaker=mock.MagicMock(return_value=mock.MagicMock()),
)

# Stub pydantic_settings
class _BaseSettings:
    def __init_subclass__(cls, **kw): pass
    def __init__(self, **kw): pass

_stub("pydantic_settings", BaseSettings=_BaseSettings)

# Stub backend.config so settings.database_url resolves
class _Settings:
    database_url = "sqlite+aiosqlite:///:memory:"

_stub("backend.config", settings=_Settings())

# Build a fake async engine
_fake_engine = mock.MagicMock()
_fake_engine.dispose = mock.AsyncMock()

class _FakeCtx:
    async def __aenter__(self): return mock.MagicMock()
    async def __aexit__(self, *a): pass

_fake_engine.begin = mock.MagicMock(return_value=_FakeCtx())

# Stub backend.db.*
_stub("backend.db")
_stub(
    "backend.db.engine",
    _engine=_fake_engine,
    get_db=mock.MagicMock(),
    AsyncSessionLocal=mock.MagicMock(),
)

class _FakeMeta:
    def create_all(self, bind): pass

class _FakeBase:
    metadata = _FakeMeta()

class _FakePortfolioSnapshot:
    pass

_stub("backend.db.models", Base=_FakeBase, PortfolioSnapshot=_FakePortfolioSnapshot)

# Now import the app — lifespan will try to use our stubbed engine
from backend.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_positions_returns_list():
    with mock.patch(
        "backend.routers.positions.get_portfolio_summary",
        return_value={"positions": {}},
    ):
        r = client.get("/api/positions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_positions_with_data():
    fake_positions = {
        "AAPL": {"shares": 10, "avg_cost": 150.0, "pnl_pct": 5.0},
    }
    with mock.patch(
        "backend.routers.positions.get_portfolio_summary",
        return_value={"positions": fake_positions},
    ):
        r = client.get("/api/positions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["shares"] == 10


def test_analysis_ticker():
    fake_result = {"ticker": "AAPL", "action": "BUY", "opportunity_score": 7}
    with mock.patch(
        "backend.routers.analysis.analyze_ticker",
        return_value=fake_result,
    ):
        r = client.get("/api/analysis/AAPL")
    assert r.status_code == 200
    body = r.json()
    assert "ticker" in body or "symbol" in body or "error" in body


def test_analysis_ticker_not_found():
    with mock.patch(
        "backend.routers.analysis.analyze_ticker",
        return_value=None,
    ):
        r = client.get("/api/analysis/FAKE123")
    assert r.status_code == 404


def test_signals_returns_list():
    # events.db won't exist in test env — router should return []
    r = client.get("/api/signals")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_cycle_run_returns_started():
    r = client.post("/api/cycle/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("started", "already_running")
