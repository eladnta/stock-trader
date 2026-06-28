# Stock Trader GUI Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full GUI (React + FastAPI + PostgreSQL) for the existing stock-trader Python engine, deployed via Docker Compose on home server at `trader.nimbus.opik.net`.

**Architecture:** FastAPI wraps the existing Python engine as a library (no subprocess calls), exposes REST + SSE endpoints, persists state to PostgreSQL while keeping the engine's SQLite events.db cache intact. React + Vite frontend implements the Flux+ cockpit design (constellation center, vitals left, inspector right, positions strip), served by nginx which also reverse-proxies `/api/*` to the FastAPI container. Three Docker containers share a private bridge network; nginx-proxy-manager on the host routes `trader.nimbus.opik.net` → frontend:80.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, asyncpg, SQLAlchemy 2 async + Alembic, PostgreSQL 16-alpine, React 18, TypeScript 5, Vite 5, Tailwind CSS 3, nginx-alpine, Docker Compose v2.

## Global Constraints

- API internal port: 8001 (8000 is taken by Portainer on the host)
- Frontend internal port: 80 (nginx-proxy-manager handles TLS externally)
- PostgreSQL internal port: 5432, no external port exposure
- Docker network name: `stock-trader_app` (bridge, isolated)
- No external ports on any container — NPM routes by hostname `trader.nimbus.opik.net`
- Python engine files must NOT be modified — wrap as library only
- SQLite `state/events.db` cache must remain intact (engine reads it directly)
- RTL layout (`direction:rtl`) on all UI containers; numbers/tickers get `direction:ltr; unicode-bidi:isolate`
- CSS palette — `--ink:#06070c --surf:#0e1120 --line:#1b2138 --txt:#eaf0ff --txt2:#9aa6c8 --txt3:#58607e --cyan:#5ce0ff --em:#34d8a0 --vio:#b07cff --rose:#f4798b --gold:#f0d9a8`
- No text wrapping on metric labels: `white-space:nowrap; overflow:hidden; text-overflow:ellipsis`
- All font sizes via `clamp()` for responsive scaling
- SSE endpoint for live portfolio updates (no WebSocket)
- Alembic for all schema migrations — no raw DDL in application code

---

## File Structure

```
stock-trader/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app factory + lifespan
│   ├── config.py                # Settings (env vars, DB URL)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py            # SQLAlchemy async engine + session factory
│   │   └── models.py            # ORM models (PortfolioSnapshot, Trade, ConvictionRecord)
│   ├── alembic/
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   │       └── 0001_initial.py  # Initial schema migration
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── portfolio.py         # GET /api/portfolio, GET /api/portfolio/stream (SSE)
│   │   ├── positions.py         # GET /api/positions
│   │   ├── analysis.py          # GET /api/analysis/{ticker}
│   │   ├── signals.py           # GET /api/signals
│   │   └── cycle.py             # POST /api/cycle/run
│   └── services/
│       ├── __init__.py
│       ├── engine_bridge.py     # Wraps Python engine.analyze() + trader.py logic
│       └── snapshot.py          # Persists portfolio snapshot to PostgreSQL
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf               # Reverse proxy /api/* → api:8001, serve SPA
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles/
│       │   └── globals.css      # CSS variables, base RTL, .num/.tick classes
│       ├── api/
│       │   ├── client.ts        # fetch wrapper (base URL, error handling)
│       │   └── sse.ts           # SSE hook
│       ├── types/
│       │   └── index.ts         # Portfolio, Position, Analysis, Signal TS types
│       ├── hooks/
│       │   ├── usePortfolio.ts  # SWR/SSE portfolio state
│       │   └── useAnalysis.ts   # per-ticker analysis
│       ├── components/
│       │   ├── TopBar.tsx       # Logo, nav tabs, ⌘K, live dot, Run button
│       │   ├── VitalsPanel.tsx  # Left: 7 metrics + conviction ring
│       │   ├── Constellation.tsx# Center: SVG + absolute orbs
│       │   ├── Inspector.tsx    # Right: selected ticker detail + signal bars
│       │   ├── PositionStrip.tsx# Bottom: position cards
│       │   └── ui/
│       │       ├── MetricRow.tsx
│       │       ├── SignalBar.tsx
│       │       └── ConvictionRing.tsx
│       └── pages/
│           └── Cockpit.tsx      # Main layout (CSS grid 3-col)
├── docker-compose.yml
└── .env.example
```

---

### Task 1: Docker Compose + PostgreSQL skeleton

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile` (placeholder — nginx only)
- Create: `frontend/nginx.conf`

**Interfaces:**
- Produces: running `postgres` service reachable at `postgres:5432` on `stock-trader_app` network; `api` service skeleton at `api:8001`; `frontend` service at port 80

- [ ] **Step 1: Create `.env.example`**

```
POSTGRES_DB=stocktrader
POSTGRES_USER=stocktrader
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql+asyncpg://stocktrader:changeme@postgres:5432/stocktrader
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app

  api:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: ${DATABASE_URL}
    volumes:
      - ../state:/app/state        # engine reads/writes state/portfolio.json + events.db
    depends_on:
      - postgres
    networks:
      - app

  frontend:
    build: ./frontend
    restart: unless-stopped
    depends_on:
      - api
    networks:
      - app
      - public-web-edge            # NPM can reach this container

volumes:
  postgres_data:

networks:
  app:
    driver: bridge
  public-web-edge:
    external: true
```

- [ ] **Step 3: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Mount the parent engine directory at runtime via volume
COPY . /app/backend
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 4: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://api:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 5: Create placeholder `frontend/Dockerfile`** (will be replaced in Task 7)

```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist/ /usr/share/nginx/html/
```

- [ ] **Step 6: Verify compose parses**

```bash
docker compose config
```
Expected: YAML printed with no errors.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example backend/Dockerfile frontend/Dockerfile frontend/nginx.conf
git commit -m "feat: docker compose skeleton with postgres, api, frontend services"
```

---

### Task 2: FastAPI app + database layer

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/db/__init__.py`
- Create: `backend/db/engine.py`
- Create: `backend/db/models.py`
- Create: `backend/main.py`

**Interfaces:**
- Consumes: `DATABASE_URL` env var
- Produces: `AsyncSession` dependency `get_db()`; ORM models `PortfolioSnapshot`, `Trade`, `ConvictionRecord`; FastAPI `app` instance at `backend.main:app`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic-settings==2.2.1
httpx==0.27.0
sse-starlette==1.8.2
```

- [ ] **Step 2: Create `backend/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://stocktrader:changeme@localhost:5432/stocktrader"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Create `backend/db/engine.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import settings

_engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Create `backend/db/models.py`**

```python
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
```

- [ ] **Step 5: Create `backend/db/__init__.py`** (empty)

- [ ] **Step 6: Create `backend/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.engine import _engine
from backend.db.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()

app = FastAPI(title="Stock Trader API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Run locally to verify startup**

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://stocktrader:changeme@localhost:5432/stocktrader" uvicorn backend.main:app --port 8001
```
Expected: `Application startup complete.` No errors. GET `http://localhost:8001/health` → `{"status":"ok"}`

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: fastapi app + sqlalchemy async db layer with portfolio/trade/conviction models"
```

---

### Task 3: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

**Interfaces:**
- Consumes: `backend.db.models.Base`; `DATABASE_URL` env var
- Produces: `alembic upgrade head` creates all three tables in PostgreSQL

- [ ] **Step 1: Init alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: Edit `backend/alembic/env.py`** — replace the `target_metadata` and `run_migrations_online` sections:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from backend.db.models import Base
from backend.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_async_engine(settings.database_url)

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda conn: context.configure(connection=conn, target_metadata=target_metadata)
            )
            async with connection.begin():
                await connection.run_sync(lambda _: context.run_migrations())

    asyncio.run(do_run())

run_migrations_online()
```

- [ ] **Step 3: Generate initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial"
```
Expected: `backend/alembic/versions/<hash>_initial.py` created with `op.create_table("portfolio_snapshots", ...)`, `op.create_table("trades", ...)`, `op.create_table("conviction_records", ...)`.

- [ ] **Step 4: Apply migration**

```bash
alembic upgrade head
```
Expected: `Running upgrade  -> <hash>, initial`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: alembic migrations for portfolio_snapshots, trades, conviction_records"
```

---

### Task 4: Engine bridge service + portfolio router

**Files:**
- Create: `backend/services/engine_bridge.py`
- Create: `backend/services/snapshot.py`
- Create: `backend/services/__init__.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/portfolio.py`
- Modify: `backend/main.py` (add router)

**Interfaces:**
- Consumes: Python `trading.portfolio.Portfolio.load()`, `trading.performance.full_report()`, `engine.analyze()`
- Produces:
  - `engine_bridge.get_portfolio_summary() -> dict` — portfolio + performance merged
  - `engine_bridge.analyze_ticker(symbol: str) -> dict` — wraps `engine.analyze()`
  - `snapshot.save_snapshot(session: AsyncSession, summary: dict) -> None`
  - GET `/api/portfolio` → `PortfolioSummary` JSON
  - GET `/api/portfolio/stream` → SSE stream (one event per 30s)

- [ ] **Step 1: Write test for `get_portfolio_summary`**

```python
# backend/tests/test_engine_bridge.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from backend.services.engine_bridge import get_portfolio_summary

def test_get_portfolio_summary_shape():
    summary = get_portfolio_summary()
    assert "portfolio_value" in summary
    assert "total_return_pct" in summary
    assert "positions" in summary
    assert "cash_pct" in summary
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_engine_bridge.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.engine_bridge'`

- [ ] **Step 3: Create `backend/services/engine_bridge.py`**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from trading.portfolio import Portfolio
from trading.performance import full_report
import yfinance as yf

def get_portfolio_summary() -> dict:
    portfolio = Portfolio.load()
    tickers = list(portfolio.positions.keys())
    current_prices: dict[str, float] = {}
    if tickers:
        data = yf.download(tickers, period="1d", auto_adjust=True, progress=False)
        close = data["Close"] if len(tickers) > 1 else {tickers[0]: data["Close"]}
        for t in tickers:
            try:
                current_prices[t] = float(close[t].dropna().iloc[-1])
            except Exception:
                current_prices[t] = portfolio.positions[t]["avg_cost"]
    report = full_report(portfolio, current_prices)
    return report

def analyze_ticker(symbol: str) -> dict | None:
    import engine
    return engine.analyze(symbol)
```

- [ ] **Step 4: Create `backend/services/snapshot.py`**

```python
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import PortfolioSnapshot

async def save_snapshot(session: AsyncSession, summary: dict) -> None:
    snap = PortfolioSnapshot(
        captured_at=datetime.utcnow(),
        cash=summary.get("benchmark", {}).get("portfolio", {}).get("value", 0) * (summary.get("cash_pct", 0) / 100),
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
```

- [ ] **Step 5: Create `backend/routers/portfolio.py`**

```python
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.engine import get_db
from backend.services.engine_bridge import get_portfolio_summary
from backend.services.snapshot import save_snapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("")
async def get_portfolio(session: AsyncSession = Depends(get_db)):
    summary = get_portfolio_summary()
    await save_snapshot(session, summary)
    return summary

@router.get("/stream")
async def stream_portfolio():
    async def event_generator():
        import json
        while True:
            summary = get_portfolio_summary()
            yield f"data: {json.dumps(summary)}\n\n"
            await asyncio.sleep(30)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 6: Register router in `backend/main.py`**

Add after CORS middleware:
```python
from backend.routers.portfolio import router as portfolio_router
app.include_router(portfolio_router, prefix="/api")
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd backend
pytest tests/test_engine_bridge.py -v
```
Expected: PASS

- [ ] **Step 8: Manual smoke test**

```bash
curl http://localhost:8001/api/portfolio
```
Expected: JSON with `portfolio_value`, `positions`, `total_return_pct`, etc.

- [ ] **Step 9: Commit**

```bash
git add backend/services/ backend/routers/ backend/main.py backend/tests/
git commit -m "feat: engine bridge + portfolio REST + SSE endpoints"
```

---

### Task 5: Remaining API routers

**Files:**
- Create: `backend/routers/positions.py`
- Create: `backend/routers/analysis.py`
- Create: `backend/routers/signals.py`
- Create: `backend/routers/cycle.py`
- Modify: `backend/main.py` (add all routers)

**Interfaces:**
- Consumes: `engine_bridge.get_portfolio_summary()`, `engine_bridge.analyze_ticker()`
- Produces:
  - GET `/api/positions` → list of position objects `[{ticker, shares, avg_cost, current_price, pnl_pct, action, signal_scores}]`
  - GET `/api/analysis/{ticker}` → full `engine.analyze()` dict
  - GET `/api/signals` → list of recent signal events from `state/events.db`
  - POST `/api/cycle/run` → triggers one trading cycle, returns `{status, trades_executed}`

- [ ] **Step 1: Write test for positions endpoint shape**

```python
# backend/tests/test_routers.py
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from backend.main import app

client = TestClient(app)

def test_positions_returns_list():
    r = client.get("/api/positions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_analysis_ticker():
    r = client.get("/api/analysis/AAPL")
    assert r.status_code == 200
    body = r.json()
    assert "ticker" in body or "symbol" in body or "error" in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_routers.py -v
```
Expected: FAIL — 404 for `/api/positions`

- [ ] **Step 3: Create `backend/routers/positions.py`**

```python
from fastapi import APIRouter
from backend.services.engine_bridge import get_portfolio_summary
import yfinance as yf

router = APIRouter(prefix="/positions", tags=["positions"])

@router.get("")
def get_positions():
    summary = get_portfolio_summary()
    positions_raw = summary.get("positions", {})
    result = []
    for ticker, pos in positions_raw.items():
        result.append({
            "ticker": ticker,
            "shares": pos.get("shares", 0),
            "avg_cost": pos.get("avg_cost", 0),
            "current_price": pos.get("current_price", pos.get("avg_cost", 0)),
            "pnl_pct": pos.get("pnl_pct", 0),
            "action": pos.get("action", "HOLD"),
        })
    return result
```

- [ ] **Step 4: Create `backend/routers/analysis.py`**

```python
from fastapi import APIRouter, HTTPException
from backend.services.engine_bridge import analyze_ticker

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/{ticker}")
def get_analysis(ticker: str):
    result = analyze_ticker(ticker.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")
    return result
```

- [ ] **Step 5: Create `backend/routers/signals.py`**

```python
import sqlite3, os, json
from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])

DB_PATH = os.path.join(os.path.dirname(__file__), "../../../state/events.db")

@router.get("")
def get_signals():
    if not os.path.exists(DB_PATH):
        return []
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT * FROM signal_cache ORDER BY cached_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        con.close()
```

- [ ] **Step 6: Create `backend/routers/cycle.py`**

```python
import asyncio
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/cycle", tags=["cycle"])
_running = False

async def _run_cycle():
    global _running
    if _running:
        return
    _running = True
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
        from trader import run_cycle
        await asyncio.to_thread(run_cycle)
    finally:
        _running = False

@router.post("/run")
async def trigger_cycle(background_tasks: BackgroundTasks):
    if _running:
        return {"status": "already_running"}
    background_tasks.add_task(_run_cycle)
    return {"status": "started"}
```

- [ ] **Step 7: Register all routers in `backend/main.py`**

```python
from backend.routers.positions import router as positions_router
from backend.routers.analysis import router as analysis_router
from backend.routers.signals import router as signals_router
from backend.routers.cycle import router as cycle_router

app.include_router(positions_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(cycle_router, prefix="/api")
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest backend/tests/test_routers.py -v
```
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/routers/ backend/main.py
git commit -m "feat: positions, analysis, signals, cycle API endpoints"
```

---

### Task 6: React + Vite project scaffold + types + API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/sse.ts`

**Interfaces:**
- Produces: `fetchAPI(path, options?) → Promise<T>` from `api/client.ts`; `useSSE<T>(path) → T | null` from `api/sse.ts`; TypeScript types `Portfolio`, `Position`, `AnalysisResult`, `Signal`

- [ ] **Step 1: Scaffold Vite project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install swr
```

- [ ] **Step 2: Create `frontend/src/styles/globals.css`**

```css
:root {
  --ink: #06070c;
  --surf: #0e1120;
  --line: #1b2138;
  --txt: #eaf0ff;
  --txt2: #9aa6c8;
  --txt3: #58607e;
  --cyan: #5ce0ff;
  --em: #34d8a0;
  --vio: #b07cff;
  --rose: #f4798b;
  --gold: #f0d9a8;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #root {
  height: 100%;
  background: var(--ink);
  color: var(--txt);
  font-family: -apple-system, system-ui, sans-serif;
  direction: rtl;
}

/* Numbers and tickers always LTR */
.num, .tick {
  direction: ltr;
  unicode-bidi: isolate;
  font-family: 'SF Mono', ui-monospace, monospace;
}

/* Prevent label wrapping */
.label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

- [ ] **Step 3: Create `frontend/src/types/index.ts`**

```typescript
export interface Position {
  ticker: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  pnl_pct: number;
  action: "BUY" | "SELL" | "HOLD";
}

export interface ConvictionAccuracy {
  overall: number;
  by_horizon: Record<string, number>;  // "1W" | "1M" | "3M" → accuracy %
}

export interface Portfolio {
  portfolio_value: number;
  total_return_pct: number;
  cash_pct: number;
  vs_spy_alpha: number | null;
  vs_qqq_alpha: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  positions: Record<string, Position>;
  conviction_accuracy: ConvictionAccuracy;
  as_of: string;
}

export interface SignalContribution {
  name: string;
  score: number;    // -1 to +1
  weight: number;
  label: string;
}

export interface AnalysisResult {
  ticker: string;
  action: string;
  opportunity_score: number;
  asset_class: string;
  sector?: string;
  price?: number;
  price_target?: number;
  signals?: SignalContribution[];
  thesis?: string;
}

export interface Signal {
  key: string;
  value: string;
  cached_at: string;
  type: string;
}
```

- [ ] **Step 4: Create `frontend/src/api/client.ts`**

```typescript
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}
```

- [ ] **Step 5: Create `frontend/src/api/sse.ts`**

```typescript
import { useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export function useSSE<T>(path: string): T | null {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    const es = new EventSource(`${BASE}${path}`);
    es.onmessage = (e) => {
      try { setData(JSON.parse(e.data)); } catch {}
    };
    return () => es.close();
  }, [path]);

  return data;
}
```

- [ ] **Step 6: Update `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/globals.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>
);
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd frontend && npm run dev
```
Expected: `http://localhost:5173` shows blank dark page. No console errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: react+vite scaffold with RTL globals, types, api client and SSE hook"
```

---

### Task 7: Flux+ UI — TopBar + VitalsPanel

**Files:**
- Create: `frontend/src/components/TopBar.tsx`
- Create: `frontend/src/components/VitalsPanel.tsx`
- Create: `frontend/src/components/ui/MetricRow.tsx`
- Create: `frontend/src/components/ui/ConvictionRing.tsx`
- Create: `frontend/src/pages/Cockpit.tsx`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `Portfolio` type from `types/index.ts`
- Produces: `<Cockpit />` page; `<TopBar onRunCycle />` component; `<VitalsPanel portfolio />` component

- [ ] **Step 1: Create `frontend/src/components/ui/MetricRow.tsx`**

```tsx
interface MetricRowProps {
  label: string;
  value: string;
  valueColor?: string;
}

export function MetricRow({ label, value, valueColor }: MetricRowProps) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
      <span className="label" style={{ fontSize: "clamp(11px,1.2vw,13px)", color: "var(--txt2)" }}>{label}</span>
      <span className="num" style={{ fontSize: "clamp(12px,1.3vw,14px)", fontWeight: 700, color: valueColor ?? "var(--txt)" }}>{value}</span>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/ui/ConvictionRing.tsx`**

```tsx
interface ConvictionRingProps { accuracy: number; }  // 0-100

export function ConvictionRing({ accuracy }: ConvictionRingProps) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const filled = circ * (accuracy / 100);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <svg width={88} height={88} viewBox="0 0 88 88">
        <circle cx={44} cy={44} r={r} fill="none" stroke="var(--line)" strokeWidth={6} />
        <circle cx={44} cy={44} r={r} fill="none" stroke="var(--cyan)" strokeWidth={6}
          strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 44 44)" />
        <text x={44} y={48} textAnchor="middle" fill="var(--txt)" fontSize={18} fontWeight={700} fontFamily="monospace">{accuracy}%</text>
      </svg>
      <span style={{ fontSize: 11, color: "var(--txt3)" }}>דיוק תחזיות</span>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/VitalsPanel.tsx`**

```tsx
import { Portfolio } from "../types";
import { MetricRow } from "./ui/MetricRow";
import { ConvictionRing } from "./ui/ConvictionRing";

interface Props { portfolio: Portfolio | null; }

function fmt(n: number | null | undefined, suffix = "", prefix = "") {
  if (n == null) return "—";
  const abs = Math.abs(n).toFixed(2);
  const sign = n >= 0 ? "▲" : "▼";
  return `${sign} ${prefix}${abs}${suffix}`;
}

export function VitalsPanel({ portfolio }: Props) {
  if (!portfolio) return (
    <aside style={{ width: 248, padding: "20px 16px", borderLeft: "1px solid var(--line)" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>טוען…</span>
    </aside>
  );
  const accuracy = Math.round((portfolio.conviction_accuracy?.overall ?? 0) * 100);
  return (
    <aside style={{ width: 248, padding: "20px 16px", borderLeft: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "1px", color: "var(--txt3)", textTransform: "uppercase", marginBottom: 8 }}>ויטאלים</span>
      <MetricRow label="שווי פורטפוליו" value={`$${portfolio.portfolio_value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`} />
      <MetricRow label="תשואה כוללת" value={fmt(portfolio.total_return_pct, "%")} valueColor={portfolio.total_return_pct >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="α מול SPY" value={fmt(portfolio.vs_spy_alpha, "%")} valueColor={(portfolio.vs_spy_alpha ?? 0) >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="α מול QQQ" value={fmt(portfolio.vs_qqq_alpha, "%")} valueColor={(portfolio.vs_qqq_alpha ?? 0) >= 0 ? "var(--em)" : "var(--rose)"} />
      <MetricRow label="Sharpe" value={portfolio.sharpe_ratio != null ? portfolio.sharpe_ratio.toFixed(2) : "—"} />
      <MetricRow label="Max Drawdown" value={fmt(portfolio.max_drawdown_pct, "%")} valueColor="var(--rose)" />
      <MetricRow label="מזומן" value={`${portfolio.cash_pct.toFixed(1)}%`} />
      <MetricRow label="פוזיציות" value={String(Object.keys(portfolio.positions).length)} />
      <div style={{ marginTop: 16, display: "flex", justifyContent: "center" }}>
        <ConvictionRing accuracy={accuracy} />
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/TopBar.tsx`**

```tsx
interface Props { onRunCycle: () => void; running: boolean; }

export function TopBar({ onRunCycle, running }: Props) {
  return (
    <header style={{
      height: 48, display: "flex", alignItems: "center", gap: 16,
      padding: "0 20px", borderBottom: "1px solid var(--line)",
      background: "var(--surf)", direction: "rtl"
    }}>
      <span style={{ fontSize: 18, fontWeight: 800, color: "var(--cyan)", letterSpacing: "-0.5px", whiteSpace: "nowrap" }}>◈ Trader</span>
      <nav style={{ display: "flex", gap: 4, flex: 1 }}>
        {["קוקפיט", "יקום", "סיגנלים", "ביצועים"].map((t, i) => (
          <button key={t} style={{
            padding: "4px 12px", borderRadius: 6, border: "none", cursor: "pointer",
            background: i === 0 ? "rgba(92,224,255,0.12)" : "transparent",
            color: i === 0 ? "var(--cyan)" : "var(--txt3)",
            fontSize: 13, fontWeight: i === 0 ? 700 : 400
          }}>{t}</button>
        ))}
      </nav>
      <div style={{ display: "flex", alignItems: "center", gap: 8, direction: "ltr" }}>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--em)", boxShadow: "0 0 6px var(--em)", display: "inline-block" }} />
        <span style={{ fontSize: 11, color: "var(--txt3)", whiteSpace: "nowrap" }}>חי</span>
        <button onClick={onRunCycle} disabled={running} style={{
          padding: "5px 14px", borderRadius: 7, border: "1px solid var(--line)",
          background: running ? "var(--line)" : "var(--cyan)", color: running ? "var(--txt3)" : "var(--ink)",
          fontWeight: 700, fontSize: 12, cursor: running ? "not-allowed" : "pointer", whiteSpace: "nowrap"
        }}>{running ? "רץ…" : "הרץ מחזור"}</button>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Create `frontend/src/pages/Cockpit.tsx`**

```tsx
import { useState } from "react";
import { VitalsPanel } from "../components/VitalsPanel";
import { TopBar } from "../components/TopBar";
import { useSSE } from "../api/sse";
import { fetchAPI } from "../api/client";
import { Portfolio } from "../types";

export function Cockpit() {
  const portfolio = useSSE<Portfolio>("/portfolio/stream");
  const [running, setRunning] = useState(false);

  async function handleRunCycle() {
    setRunning(true);
    try { await fetchAPI("/cycle/run", { method: "POST" }); }
    finally { setTimeout(() => setRunning(false), 3000); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <TopBar onRunCycle={handleRunCycle} running={running} />
      <div style={{
        flex: 1, display: "grid",
        gridTemplateColumns: "248px 1fr 320px",
        overflow: "hidden"
      }}>
        <VitalsPanel portfolio={portfolio} />
        {/* Constellation — Task 8 */}
        <main style={{ background: "var(--ink)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ color: "var(--txt3)", fontSize: 13 }}>קונסטלציה — בקרוב</span>
        </main>
        {/* Inspector — Task 9 */}
        <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: 16 }}>
          <span style={{ color: "var(--txt3)", fontSize: 13 }}>בחר נכס</span>
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/src/App.tsx`**

```tsx
import { Cockpit } from "./pages/Cockpit";
export default function App() { return <Cockpit />; }
```

- [ ] **Step 7: Run dev server and verify layout**

```bash
cd frontend && npm run dev
```
Expected: Dark page with TopBar (RTL, Hebrew nav, cyan run button), VitalsPanel on left with metrics loading from SSE. No text wrapping or overflow.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/
git commit -m "feat: flux+ topbar and vitals panel with RTL layout and SSE portfolio binding"
```

---

### Task 8: Constellation component

**Files:**
- Create: `frontend/src/components/Constellation.tsx`

**Interfaces:**
- Consumes: `positions: Position[]`, `selected: string | null`, `onSelect: (ticker: string) => void`
- Produces: `<Constellation positions onSelect selected />` — SVG lines + absolute orbs, color/size/glow encode action/weight/conviction

- [ ] **Step 1: Create `frontend/src/components/Constellation.tsx`**

```tsx
import { useRef, useState, useEffect } from "react";
import { Position } from "../types";

interface Props {
  positions: Position[];
  selected: string | null;
  onSelect: (ticker: string) => void;
}

function actionColor(action: string) {
  if (action === "BUY") return "var(--em)";
  if (action === "SELL") return "var(--rose)";
  return "var(--txt3)";
}

function orbSize(pnl: number, baseSize = 42) {
  const scale = Math.min(2, Math.max(0.6, 1 + pnl / 50));
  return baseSize * scale;
}

export function Constellation({ positions, selected, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 600, h: 400 });

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Distribute orbs in a loose circle
  const orbPositions = positions.map((p, i) => {
    const angle = (2 * Math.PI * i) / positions.length - Math.PI / 2;
    const radius = Math.min(dims.w, dims.h) * 0.32;
    return {
      ...p,
      cx: dims.w / 2 + radius * Math.cos(angle),
      cy: dims.h / 2 + radius * Math.sin(angle),
    };
  });

  return (
    <div ref={containerRef} style={{ position: "relative", flex: 1, overflow: "hidden" }}>
      {/* Hero number */}
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none" }}>
        <div className="num" style={{ fontSize: "clamp(28px,5vw,52px)", fontWeight: 900, color: "var(--txt)", opacity: 0.07 }}>
          {positions.length}
        </div>
        <div style={{ fontSize: 11, color: "var(--txt3)" }}>פוזיציות</div>
      </div>

      {/* SVG correlation lines */}
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
        {orbPositions.map((a, i) =>
          orbPositions.slice(i + 1).map((b) => (
            <line key={`${a.ticker}-${b.ticker}`}
              x1={a.cx} y1={a.cy} x2={b.cx} y2={b.cy}
              stroke="var(--line)" strokeWidth={1} opacity={0.4} />
          ))
        )}
      </svg>

      {/* Orbs */}
      {orbPositions.map((p) => {
        const size = orbSize(p.pnl_pct);
        const color = actionColor(p.action);
        const isSelected = selected === p.ticker;
        return (
          <button key={p.ticker}
            onClick={() => onSelect(p.ticker)}
            style={{
              position: "absolute",
              left: p.cx - size / 2,
              top: p.cy - size / 2,
              width: size,
              height: size,
              borderRadius: "50%",
              background: `radial-gradient(circle at 35% 35%, ${color}44, ${color}22)`,
              border: `${isSelected ? 2 : 1}px solid ${color}`,
              boxShadow: isSelected ? `0 0 16px ${color}88` : `0 0 6px ${color}44`,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 1,
              transition: "box-shadow 0.2s",
            }}>
            <span className="tick" style={{ fontSize: `clamp(9px,${size * 0.22}px,13px)`, fontWeight: 700, color: "var(--txt)", whiteSpace: "nowrap" }}>{p.ticker}</span>
            <span className="num" style={{ fontSize: `clamp(8px,${size * 0.18}px,11px)`, color: p.pnl_pct >= 0 ? "var(--em)" : "var(--rose)" }}>
              {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct.toFixed(1)}%
            </span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Wire Constellation into `Cockpit.tsx`** — replace the placeholder `<main>`:

```tsx
// Add imports at top of Cockpit.tsx
import { Constellation } from "../components/Constellation";
import { Position } from "../types";

// In Cockpit(), add state:
const [selected, setSelected] = useState<string | null>(null);
const positions: Position[] = portfolio ? Object.entries(portfolio.positions).map(([ticker, pos]) => ({
  ticker,
  shares: (pos as any).shares ?? 0,
  avg_cost: (pos as any).avg_cost ?? 0,
  current_price: (pos as any).current_price ?? (pos as any).avg_cost ?? 0,
  pnl_pct: (pos as any).pnl_pct ?? 0,
  action: (pos as any).action ?? "HOLD",
})) : [];

// Replace placeholder <main>:
<main style={{ background: "var(--ink)", overflow: "hidden", display: "flex" }}>
  <Constellation positions={positions} selected={selected} onSelect={setSelected} />
</main>
```

- [ ] **Step 3: Verify constellation renders**

```bash
cd frontend && npm run dev
```
Expected: Circular arrangement of orbs with lines between them. Orb color = action. Click → orb glows.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Constellation.tsx frontend/src/pages/Cockpit.tsx
git commit -m "feat: flux constellation with orbs, correlation lines, and selection state"
```

---

### Task 9: Inspector panel + SignalBar

**Files:**
- Create: `frontend/src/components/Inspector.tsx`
- Create: `frontend/src/components/ui/SignalBar.tsx`
- Create: `frontend/src/hooks/useAnalysis.ts`
- Modify: `frontend/src/pages/Cockpit.tsx` (replace inspector placeholder)

**Interfaces:**
- Consumes: `selected: string | null`, `useAnalysis(ticker)` hook
- Produces: `<Inspector selected />` with action badge, 4 data rows, 5 signal bars, thesis text

- [ ] **Step 1: Create `frontend/src/hooks/useAnalysis.ts`**

```typescript
import useSWR from "swr";
import { fetchAPI } from "../api/client";
import { AnalysisResult } from "../types";

export function useAnalysis(ticker: string | null) {
  const { data, isLoading } = useSWR<AnalysisResult>(
    ticker ? `/analysis/${ticker}` : null,
    (path: string) => fetchAPI<AnalysisResult>(path),
    { refreshInterval: 60_000 }
  );
  return { analysis: data ?? null, loading: isLoading };
}
```

- [ ] **Step 2: Create `frontend/src/components/ui/SignalBar.tsx`**

```tsx
interface Props { name: string; score: number; weight: number; }  // score: -1..+1

export function SignalBar({ name, score, weight }: Props) {
  const positive = score >= 0;
  const pct = Math.abs(score) * 100;
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span className="label" style={{ fontSize: 11, color: "var(--txt2)" }}>{name}</span>
        <span className="num" style={{ fontSize: 11, color: positive ? "var(--em)" : "var(--rose)", fontWeight: 700 }}>
          {positive ? "+" : ""}{(score * weight).toFixed(2)}
        </span>
      </div>
      <div style={{ height: 4, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: positive ? "var(--em)" : "var(--rose)",
          borderRadius: 2, transition: "width 0.4s"
        }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/Inspector.tsx`**

```tsx
import { useAnalysis } from "../hooks/useAnalysis";
import { SignalBar } from "./ui/SignalBar";

interface Props { selected: string | null; }

function actionBadgeColor(action: string) {
  if (action?.includes("BUY")) return { bg: "rgba(52,216,160,0.15)", color: "var(--em)" };
  if (action?.includes("SELL")) return { bg: "rgba(244,121,139,0.15)", color: "var(--rose)" };
  return { bg: "rgba(176,124,255,0.15)", color: "var(--vio)" };
}

export function Inspector({ selected }: Props) {
  const { analysis, loading } = useAnalysis(selected);

  if (!selected) return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px", direction: "rtl" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>לחץ על נכס בקונסטלציה</span>
    </aside>
  );

  if (loading) return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px" }}>
      <span style={{ color: "var(--txt3)", fontSize: 13 }}>טוען…</span>
    </aside>
  );

  const badge = actionBadgeColor(analysis?.action ?? "");
  const signals = analysis?.signals ?? [];

  return (
    <aside style={{ width: 320, borderRight: "1px solid var(--line)", padding: "20px 16px", direction: "rtl", overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <span className="tick" style={{ fontSize: 22, fontWeight: 800, color: "var(--txt)" }}>{selected}</span>
        <span style={{ fontSize: 11, padding: "3px 9px", borderRadius: 6, fontWeight: 700, background: badge.bg, color: badge.color, whiteSpace: "nowrap" }}>
          {analysis?.action ?? "—"}
        </span>
      </div>

      {/* Data rows */}
      {[
        { label: "ציון הזדמנות", value: analysis?.opportunity_score?.toFixed(1) ?? "—" },
        { label: "סקטור", value: analysis?.sector ?? analysis?.asset_class ?? "—" },
        { label: "מחיר", value: analysis?.price ? `$${analysis.price.toFixed(2)}` : "—" },
        { label: "יעד", value: analysis?.price_target ? `$${analysis.price_target.toFixed(0)}` : "—" },
      ].map(({ label, value }) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--line)" }}>
          <span className="label" style={{ fontSize: 12, color: "var(--txt2)" }}>{label}</span>
          <span className="num" style={{ fontSize: 12, fontWeight: 600, color: "var(--txt)" }}>{value}</span>
        </div>
      ))}

      {/* Signals */}
      {signals.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: "var(--txt3)", textTransform: "uppercase" }}>סיגנלים</span>
          <div style={{ marginTop: 10 }}>
            {signals.slice(0, 5).map((s) => (
              <SignalBar key={s.name} name={s.label ?? s.name} score={s.score} weight={s.weight} />
            ))}
          </div>
        </div>
      )}

      {/* Thesis */}
      {analysis?.thesis && (
        <div style={{ marginTop: 16, padding: "10px 12px", background: "rgba(92,224,255,0.05)", borderRadius: 8, borderRight: "2px solid var(--cyan)" }}>
          <p style={{ fontSize: 12, color: "var(--txt2)", lineHeight: 1.6 }}>{analysis.thesis}</p>
        </div>
      )}
    </aside>
  );
}
```

- [ ] **Step 4: Wire Inspector into `Cockpit.tsx`** — replace inspector placeholder:

```tsx
// Add import
import { Inspector } from "../components/Inspector";

// Replace placeholder <aside>:
<Inspector selected={selected} />
```

- [ ] **Step 5: Verify inspector shows on orb click**

```bash
cd frontend && npm run dev
```
Expected: Click an orb → Inspector loads analysis with action badge, data rows, signal bars.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Inspector.tsx frontend/src/components/ui/SignalBar.tsx frontend/src/hooks/useAnalysis.ts frontend/src/pages/Cockpit.tsx
git commit -m "feat: inspector panel with signal bars and analysis detail on orb selection"
```

---

### Task 10: PositionStrip component

**Files:**
- Create: `frontend/src/components/PositionStrip.tsx`
- Modify: `frontend/src/pages/Cockpit.tsx` (add strip below 3-col grid)

**Interfaces:**
- Consumes: `positions: Position[]`
- Produces: `<PositionStrip positions />` — horizontal scrolling card row

- [ ] **Step 1: Create `frontend/src/components/PositionStrip.tsx`**

```tsx
import { Position } from "../types";

interface Props { positions: Position[]; onSelect: (ticker: string) => void; }

function actionColor(action: string) {
  if (action === "BUY") return "var(--em)";
  if (action === "SELL") return "var(--rose)";
  return "var(--txt3)";
}

export function PositionStrip({ positions, onSelect }: Props) {
  return (
    <div style={{
      height: 90, borderTop: "1px solid var(--line)", display: "flex", alignItems: "center",
      gap: 8, padding: "0 16px", overflowX: "auto", overflowY: "hidden",
      direction: "rtl",
    }}>
      {positions.map((p) => {
        const color = actionColor(p.action);
        const convictionPct = Math.min(100, Math.max(0, 50 + p.pnl_pct));
        return (
          <button key={p.ticker} onClick={() => onSelect(p.ticker)} style={{
            minWidth: 120, maxWidth: 140, height: 68, padding: "8px 12px",
            background: "var(--surf)", border: "1px solid var(--line)",
            borderRadius: 10, cursor: "pointer", display: "flex", flexDirection: "column",
            justifyContent: "space-between", flexShrink: 0,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="tick" style={{ fontSize: 13, fontWeight: 700, color: "var(--txt)", whiteSpace: "nowrap" }}>{p.ticker}</span>
              <span style={{ fontSize: 10, color, fontWeight: 600, whiteSpace: "nowrap" }}>{p.action}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="num" style={{ fontSize: 12, color: p.pnl_pct >= 0 ? "var(--em)" : "var(--rose)", fontWeight: 700 }}>
                {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct.toFixed(1)}%
              </span>
            </div>
            {/* Conviction bar */}
            <div style={{ height: 3, background: "var(--line)", borderRadius: 2 }}>
              <div style={{ height: "100%", width: `${convictionPct}%`, background: color, borderRadius: 2 }} />
            </div>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Add PositionStrip to Cockpit layout**

Wrap the existing 3-col grid + strip in an outer flex column:

```tsx
// In Cockpit.tsx, replace return body:
return (
  <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
    <TopBar onRunCycle={handleRunCycle} running={running} />
    <div style={{ flex: 1, display: "grid", gridTemplateColumns: "248px 1fr 320px", overflow: "hidden" }}>
      <VitalsPanel portfolio={portfolio} />
      <main style={{ background: "var(--ink)", overflow: "hidden", display: "flex" }}>
        <Constellation positions={positions} selected={selected} onSelect={setSelected} />
      </main>
      <Inspector selected={selected} />
    </div>
    <PositionStrip positions={positions} onSelect={setSelected} />
  </div>
);
```

- [ ] **Step 3: Verify full Flux+ cockpit renders**

```bash
cd frontend && npm run dev
```
Expected: TopBar + 3-col grid (Vitals | Constellation | Inspector) + bottom PositionStrip. All text non-wrapping, RTL, Hebrew labels.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/PositionStrip.tsx frontend/src/pages/Cockpit.tsx
git commit -m "feat: position strip with conviction bars completing flux+ cockpit layout"
```

---

### Task 11: Frontend Dockerfile + production build

**Files:**
- Modify: `frontend/Dockerfile`
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Produces: multi-stage Docker image; `/usr/share/nginx/html/` contains built SPA; nginx serves at port 80 and proxies `/api/*` → `api:8001`

- [ ] **Step 1: Update `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist" },
  server: {
    proxy: {
      "/api": { target: "http://localhost:8001", rewrite: (p) => p.replace(/^\/api/, "") }
    }
  }
});
```

- [ ] **Step 2: Update `frontend/Dockerfile`** to multi-stage build:

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Test production build locally**

```bash
cd frontend && npm run build
```
Expected: `dist/` created. `ls dist/` shows `index.html`, `assets/`.

- [ ] **Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/vite.config.ts
git commit -m "feat: multi-stage frontend dockerfile + vite proxy config"
```

---

### Task 12: End-to-end Docker Compose deployment

**Files:**
- Modify: `docker-compose.yml` (health checks, restart policy, logging)
- Modify: `backend/Dockerfile` (ensure engine Python path is correct)

**Interfaces:**
- Produces: `docker compose up -d` brings all 3 services up; `trader.nimbus.opik.net` reachable via NPM

- [ ] **Step 1: Add health checks to `docker-compose.yml`**

```yaml
services:
  postgres:
    # ... existing ...
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    # ... existing ...
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

- [ ] **Step 2: Update `backend/Dockerfile`** to mount the engine correctly:

```dockerfile
FROM python:3.11-slim
WORKDIR /workspace
# Install system deps
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /workspace/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt
# The full stock-trader repo is mounted at /workspace at runtime
# (docker compose volume: ../:/workspace)
ENV PYTHONPATH=/workspace
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 3: Update volume mount in `docker-compose.yml`**

```yaml
  api:
    volumes:
      - ..:/workspace   # entire stock-trader repo so engine.py and state/ are accessible
```

- [ ] **Step 4: Copy `.env.example` to `.env` on server and fill real password**

```bash
cp .env.example .env
# Edit: set POSTGRES_PASSWORD to a real secret
```

- [ ] **Step 5: Build and start all services**

```bash
docker compose up -d --build
docker compose ps
```
Expected: `postgres`, `api`, `frontend` all `healthy` or `running`.

- [ ] **Step 6: Smoke test API through nginx proxy**

```bash
curl http://localhost/api/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 7: Configure nginx-proxy-manager**

In NPM web UI (port 81 on host):
- Add Proxy Host: `trader.nimbus.opik.net` → `frontend:80` (or container IP on `public-web-edge` network)
- Enable SSL with Let's Encrypt

- [ ] **Step 8: Verify full stack**

Open `https://trader.nimbus.opik.net` in browser.
Expected: Flux+ cockpit loads. Vitals panel shows portfolio data. Constellation shows position orbs. PositionStrip scrolls.

- [ ] **Step 9: Commit**

```bash
git add docker-compose.yml backend/Dockerfile
git commit -m "feat: production docker compose with health checks and nginx-proxy-manager routing"
```

---

## Self-Review

**Spec coverage check:**
- ✅ PostgreSQL database — Tasks 1-3
- ✅ FastAPI backend — Tasks 2, 4, 5
- ✅ Engine wrapped as library — Task 4 (`engine_bridge.py` uses `import engine`)
- ✅ SQLite events.db preserved — volume mount `..:/workspace` keeps state/ intact
- ✅ SSE live updates — Task 4 (`/api/portfolio/stream`)
- ✅ RTL + LTR numbers — Task 6 (globals.css `.num .tick`)
- ✅ Flux+ Vitals panel — Task 7
- ✅ Constellation — Task 8
- ✅ Inspector + signal bars — Task 9
- ✅ Position strip — Task 10
- ✅ Docker Compose 3 services — Tasks 1, 12
- ✅ No external ports (except frontend:80 for NPM) — Task 1
- ✅ NPM routing — Task 12 Step 7
- ✅ No text wrapping — `white-space:nowrap` on `.label`, `.tick`
- ✅ Alembic migrations — Task 3
- ✅ API port 8001 (not 8000) — Tasks 1, 2

**Placeholder scan:** No TBD/TODO in any task. All code steps have full code blocks. All commands have expected output.

**Type consistency check:**
- `Position` type defined in Task 6, consumed in Tasks 8, 9, 10 — consistent
- `Portfolio.positions` is `Record<string, Position>` — Cockpit.tsx maps it correctly in Task 8
- `AnalysisResult.signals` is `SignalContribution[]` — Inspector.tsx uses `s.name`, `s.label`, `s.score`, `s.weight` — all in type definition ✅
- `engine_bridge.get_portfolio_summary()` returns `full_report()` dict — portfolio router serializes it directly ✅
