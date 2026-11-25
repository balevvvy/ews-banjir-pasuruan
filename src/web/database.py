"""
Modul Database SQLite untuk EWS Banjir.
Menyimpan riwayat pembacaan ketinggian air dan log alert.
"""

import os
import sqlite3
import threading
import time

from src.config import DB_PATH

# Lock untuk thread-safety (thread detektor dan FastAPI menulis bersamaan)
_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS log_ketinggian_air (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            water_y INTEGER,
            water_pct REAL,
            status TEXT NOT NULL,
            timestamp REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS log_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            pesan TEXT,
            timestamp REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ketinggian_timestamp ON log_ketinggian_air(timestamp);
        CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON log_alert(timestamp);
    """)
    conn.commit()
    conn.close()
    print(f"[Database] Inisialisasi selesai: {DB_PATH}")


def insert_reading(water_y: int | None, water_pct: float | None, status: str):
    with _lock:
        conn = get_connection()
        conn.execute(
            "INSERT INTO log_ketinggian_air (water_y, water_pct, status, timestamp) VALUES (?, ?, ?, ?)",
            (water_y, water_pct, status, time.time())
        )
        conn.commit()
        conn.close()


def insert_alert(status: str, pesan: str):
    with _lock:
        conn = get_connection()
        conn.execute(
            "INSERT INTO log_alert (status, pesan, timestamp) VALUES (?, ?, ?)",
            (status, pesan, time.time())
        )
        conn.commit()
        conn.close()


def get_history(minutes: float = 60, limit: int = 2000) -> list[dict]:
    since = time.time() - minutes * 60
    conn = get_connection()
    rows = conn.execute(
        "SELECT water_y, water_pct, status, timestamp FROM log_ketinggian_air "
        "WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT ?",
        (since, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_alerts(hours: float = 24, limit: int = 100) -> list[dict]:
    since = time.time() - hours * 3600
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, pesan, timestamp FROM log_alert "
        "WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
        (since, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
