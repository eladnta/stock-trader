"""
Event Database — SQLite cache for all signals and events.

Philosophy: The system gets FASTER and SMARTER over time.
  - First time: fetch everything live (slow, 30-60s per ticker)
  - Subsequent runs: serve from cache, only refresh stale data
  - Over months: the DB accumulates event→outcome history
    → the system can learn which event types historically led to
      what actual price moves for specific stocks

Tables:
  signal_cache     — cached macro/alt/news signals with TTL
  event_history    — every significant event logged with ticker impact
  accuracy_events  — event type → actual outcome tracking

Cache TTLs:
  macro signals:  30 minutes
  news:           1 hour
  alternatives:   15 minutes
  financials:     6 hours
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "events.db")

TTL_MINUTES = {
    "macro":   30,
    "news":    60,
    "alt":     15,
    "financials": 360,
    "risk":    120,
    "horizon": 120,
}


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS signal_cache (
        key         TEXT NOT NULL,
        ticker      TEXT,
        signal_type TEXT NOT NULL,
        data        TEXT NOT NULL,
        created_at  TEXT NOT NULL,
        expires_at  TEXT NOT NULL,
        PRIMARY KEY (key, ticker)
    );

    CREATE TABLE IF NOT EXISTS event_history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date  TEXT NOT NULL,
        event_type  TEXT NOT NULL,
        ticker      TEXT,
        sector      TEXT,
        description TEXT,
        price_at_event  REAL,
        tags        TEXT,
        macro_regime    TEXT,
        vix_at_event    REAL
    );

    CREATE TABLE IF NOT EXISTS event_outcomes (
        event_id    INTEGER REFERENCES event_history(id),
        horizon     TEXT NOT NULL,   -- 1W, 1M, 3M
        measure_date TEXT,
        price       REAL,
        return_pct  REAL,
        correct_direction INTEGER,
        PRIMARY KEY (event_id, horizon)
    );

    CREATE TABLE IF NOT EXISTS signal_accuracy (
        signal_type TEXT NOT NULL,
        event_tag   TEXT NOT NULL,
        sector      TEXT,
        n_measured  INTEGER DEFAULT 0,
        n_correct   INTEGER DEFAULT 0,
        avg_return  REAL DEFAULT 0,
        last_updated TEXT,
        PRIMARY KEY (signal_type, event_tag, sector)
    );
    """)
    conn.commit()


# ── Cache operations ──────────────────────────────────────────────────────────

def cache_get(signal_type: str, ticker: str = "") -> dict | None:
    key = _make_key(signal_type, ticker)
    with get_db() as conn:
        row = conn.execute(
            "SELECT data, expires_at FROM signal_cache WHERE key=? AND ticker=?",
            (key, ticker)
        ).fetchone()
        if not row:
            return None
        if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
            conn.execute("DELETE FROM signal_cache WHERE key=? AND ticker=?", (key, ticker))
            return None
        return json.loads(row["data"])


def cache_set(signal_type: str, data: dict, ticker: str = ""):
    key = _make_key(signal_type, ticker)
    ttl = TTL_MINUTES.get(signal_type, 60)
    now = datetime.utcnow()
    expires = now + timedelta(minutes=ttl)
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO signal_cache (key, ticker, signal_type, data, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key, ticker, signal_type, json.dumps(data), now.isoformat(), expires.isoformat()))
        conn.commit()


def cache_stats() -> dict:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT signal_type, COUNT(*) as n,
                   SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END) as valid
            FROM signal_cache GROUP BY signal_type
        """, (datetime.utcnow().isoformat(),)).fetchall()
        return {r["signal_type"]: {"total": r["n"], "valid": r["valid"]} for r in rows}


# ── Event logging ─────────────────────────────────────────────────────────────

def log_event(
    event_type: str,
    description: str,
    ticker: str = None,
    sector: str = None,
    price: float = None,
    tags: list[str] = None,
    macro_regime: str = None,
    vix: float = None,
) -> int:
    """Log a significant market event. Returns event_id."""
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO event_history
              (event_date, event_type, ticker, sector, description, price_at_event, tags, macro_regime, vix_at_event)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(), event_type, ticker, sector,
            description, price, json.dumps(tags or []), macro_regime, vix,
        ))
        conn.commit()
        return cur.lastrowid


def record_outcome(event_id: int, horizon: str, price: float, return_pct: float, correct: bool):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO event_outcomes
              (event_id, horizon, measure_date, price, return_pct, correct_direction)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_id, horizon, datetime.utcnow().isoformat(), price, return_pct, int(correct)))
        conn.commit()

    # Update accuracy stats
    _update_accuracy(event_id, horizon, return_pct, correct)


def _update_accuracy(event_id: int, horizon: str, return_pct: float, correct: bool):
    with get_db() as conn:
        row = conn.execute(
            "SELECT event_type, sector FROM event_history WHERE id=?", (event_id,)
        ).fetchone()
        if not row:
            return
        event_type = row["event_type"]
        sector = row["sector"] or "all"

        existing = conn.execute(
            "SELECT n_measured, n_correct, avg_return FROM signal_accuracy WHERE signal_type=? AND event_tag=? AND sector=?",
            ("event", event_type, sector)
        ).fetchone()

        if existing:
            n = existing["n_measured"] + 1
            nc = existing["n_correct"] + (1 if correct else 0)
            avg = (existing["avg_return"] * existing["n_measured"] + return_pct) / n
            conn.execute("""
                UPDATE signal_accuracy SET n_measured=?, n_correct=?, avg_return=?, last_updated=?
                WHERE signal_type=? AND event_tag=? AND sector=?
            """, (n, nc, avg, datetime.utcnow().isoformat(), "event", event_type, sector))
        else:
            conn.execute("""
                INSERT INTO signal_accuracy (signal_type, event_tag, sector, n_measured, n_correct, avg_return, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("event", event_type, sector, 1, int(correct), return_pct, datetime.utcnow().isoformat()))
        conn.commit()


def get_historical_accuracy(event_type: str, sector: str = "all") -> dict | None:
    with get_db() as conn:
        row = conn.execute("""
            SELECT n_measured, n_correct, avg_return FROM signal_accuracy
            WHERE signal_type='event' AND event_tag=? AND sector=?
        """, (event_type, sector)).fetchone()
        if not row or row["n_measured"] == 0:
            return None
        return {
            "n": row["n_measured"],
            "win_rate": round(row["n_correct"] / row["n_measured"] * 100, 1),
            "avg_return_pct": round(row["avg_return"], 2),
        }


def get_recent_events(ticker: str = None, days: int = 30, limit: int = 20) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        if ticker:
            rows = conn.execute("""
                SELECT * FROM event_history WHERE ticker=? AND event_date > ?
                ORDER BY event_date DESC LIMIT ?
            """, (ticker, cutoff, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM event_history WHERE event_date > ?
                ORDER BY event_date DESC LIMIT ?
            """, (cutoff, limit)).fetchall()
        return [dict(r) for r in rows]


def db_summary() -> dict:
    with get_db() as conn:
        events = conn.execute("SELECT COUNT(*) as n FROM event_history").fetchone()["n"]
        outcomes = conn.execute("SELECT COUNT(*) as n FROM event_outcomes WHERE correct_direction IS NOT NULL").fetchone()["n"]
        accuracy_rows = conn.execute("SELECT COUNT(*) as n FROM signal_accuracy WHERE n_measured > 0").fetchone()["n"]
        cache = cache_stats()
        return {
            "events_logged": events,
            "outcomes_measured": outcomes,
            "accuracy_patterns": accuracy_rows,
            "cache": cache,
        }


def _make_key(signal_type: str, ticker: str) -> str:
    return f"{signal_type}:{ticker or 'global'}"
