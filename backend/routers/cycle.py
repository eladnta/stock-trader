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
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
        import types
        from trader import cmd_run
        # cmd_run expects an args namespace with a 'universe' attribute
        args = types.SimpleNamespace(universe="mixed")
        await asyncio.to_thread(cmd_run, args)
    finally:
        _running = False


@router.post("/run")
async def trigger_cycle(background_tasks: BackgroundTasks):
    if _running:
        return {"status": "already_running"}
    background_tasks.add_task(_run_cycle)
    return {"status": "started"}
