import asyncio
import json
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
        while True:
            summary = get_portfolio_summary()
            yield f"data: {json.dumps(summary)}\n\n"
            await asyncio.sleep(30)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
