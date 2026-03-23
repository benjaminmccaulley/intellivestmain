"""
SQLite cache for OHLCV bars so the app retains history across restarts.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stock_history.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol TEXT NOT NULL,
            bar_time TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            PRIMARY KEY (symbol, bar_time)
        )
        """
    )
    c.commit()
    return c


def store_bars(symbol: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    sym = symbol.upper()
    with _conn() as c:
        c.executemany(
            """
            INSERT OR REPLACE INTO ohlcv (symbol, bar_time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    sym,
                    str(r["date"]),
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    int(r["volume"]),
                )
                for r in rows
            ],
        )
        c.commit()


def load_bars(symbol: str, limit: int = 5000) -> List[Dict[str, Any]]:
    sym = symbol.upper()
    with _conn() as c:
        cur = c.execute(
            """
            SELECT bar_time, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = ?
            ORDER BY bar_time ASC
            LIMIT ?
            """,
            (sym, limit),
        )
        rows = cur.fetchall()
    return [
        {
            "date": t,
            "open": o,
            "high": h,
            "low": l,
            "close": cl,
            "volume": v,
        }
        for (t, o, h, l, cl, v) in rows
    ]


def latest_bars(symbol: str, max_points: int = 2000) -> List[Dict[str, Any]]:
    """Most recent cached bars (newest last), for offline / API-failure fallback."""
    all_rows = load_bars(symbol, limit=50000)
    if len(all_rows) <= max_points:
        return all_rows
    return all_rows[-max_points:]
