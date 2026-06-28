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

from backend.routers.portfolio import router as portfolio_router
from backend.routers.positions import router as positions_router
from backend.routers.analysis import router as analysis_router
from backend.routers.signals import router as signals_router
from backend.routers.cycle import router as cycle_router

app.include_router(portfolio_router, prefix="/api")
app.include_router(positions_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(signals_router, prefix="/api")
app.include_router(cycle_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
