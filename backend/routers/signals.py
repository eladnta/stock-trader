import sqlite3
import os
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
