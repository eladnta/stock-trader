import asyncio
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/cycle", tags=["cycle"])
_cycle_lock = asyncio.Lock()


async def _run_cycle():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
    from trader import cmd_run
    from types import SimpleNamespace
    await asyncio.to_thread(cmd_run, SimpleNamespace(universe="mixed"))


async def _run_cycle_with_lock():
    async with _cycle_lock:
        await _run_cycle()


@router.post("/run")
async def trigger_cycle(background_tasks: BackgroundTasks):
    if _cycle_lock.locked():
        return {"status": "already_running"}
    background_tasks.add_task(_run_cycle_with_lock)
    return {"status": "started"}
