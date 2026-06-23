"""SQLite helper for job metadata storage.

A tiny wrapper that creates ``jobs.db`` under ``data/`` and ensures the
``jobs`` table exists.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            area TEXT,
            trip_count INTEGER,
            seed INTEGER,
            status TEXT,
            processed INTEGER,
            total INTEGER,
            created_at TEXT
        )
    """)
    return conn
