"""SQLite schema and migrations for the plan store.

Schema is applied via a numbered list of migrations rather than a migration
framework (decision 0008: SQLite, no new dependency) — the store is small,
so hand-rolled migrations in this module are simpler than adding Alembic.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS: list[str] = [
    # 1: initial schema (docs/specs/plan-model.md, docs/specs/route-schema.md)
    """
    CREATE TABLE plans (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE turnpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
        seq INTEGER NOT NULL,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        altitude_ft REAL,
        UNIQUE (plan_id, seq)
    );

    CREATE TABLE events (
        id TEXT PRIMARY KEY,
        plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
        seq INTEGER NOT NULL,
        actor TEXT NOT NULL,
        tool_call TEXT NOT NULL,
        tool_call_args_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        parent_event_id TEXT REFERENCES events(id),
        UNIQUE (plan_id, seq)
    );
    """,
    # 2: overlays (docs/specs/plan-model.md "v2 additions", decision 0010).
    # Import-once, so one row per overlay with features serialized as JSON
    # rather than a normalized features table -- see the spec's open gap.
    """
    CREATE TABLE overlays (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        source_format TEXT NOT NULL,
        source_path TEXT NOT NULL,
        features_json TEXT NOT NULL,
        actor TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
    # 3: threats (docs/PLAN.md Phase 3). Import-once like overlays -- a
    # scenario defines them, nothing iteratively mutates one.
    """
    CREATE TABLE threats (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        threat_type TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        engagement_radius_nm REAL NOT NULL,
        sensor_height_ft REAL NOT NULL,
        sidc TEXT,
        actor TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
]


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and migrations applied.

    ``check_same_thread=False`` because the API (src/turnpoint/api) runs
    each sync request handler in a worker-pool thread, not the thread that
    opened the connection. This is safe: Python's sqlite3 module links
    against SQLite's default "serialized" threading mode, which allows a
    single connection to be used from multiple threads with SQLite doing
    its own internal locking.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    existing = conn.execute("SELECT version FROM schema_version").fetchone()
    current = existing["version"] if existing else 0
    for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
        conn.executescript(script)
        current = version
    if existing is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
    elif current != existing["version"]:
        conn.execute("UPDATE schema_version SET version = ?", (current,))
    conn.commit()
