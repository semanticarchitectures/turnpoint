"""SQLite-backed threat store.

Threats are import-once (same rationale as OverlayStore, decision 0010):
a scenario defines them, nothing iteratively mutates one, so there's no
per-mutation provenance event chain -- just the actor and timestamp of
creation.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from turnpoint.core.threat import Threat
from turnpoint.store.db import connect
from turnpoint.store.plan_store import DEFAULT_STORE_PATH

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ThreatStore:
    """SQLite-backed store for Threats (docs/PLAN.md Phase 3)."""

    def __init__(self, path: str | Path = ":memory:", *, clock: Clock = _utcnow) -> None:
        self._conn: sqlite3.Connection = connect(path)
        self._clock = clock

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ThreatStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def create_threat(
        self,
        name: str,
        threat_type: str,
        lat: float,
        lon: float,
        engagement_radius_nm: float,
        *,
        sensor_height_ft: float = 0.0,
        sidc: str | None = None,
        actor: str,
    ) -> Threat:
        if not actor:
            raise ValueError("actor is required")
        if engagement_radius_nm <= 0:
            raise ValueError("engagement_radius_nm must be positive")
        threat_id = str(uuid.uuid4())
        now = self._clock().isoformat()
        with self._conn:
            self._conn.execute(
                "INSERT INTO threats (id, name, threat_type, lat, lon, "
                "engagement_radius_nm, sensor_height_ft, sidc, actor, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    threat_id,
                    name,
                    threat_type,
                    lat,
                    lon,
                    engagement_radius_nm,
                    sensor_height_ft,
                    sidc,
                    actor,
                    now,
                ),
            )
        return self.get_threat(threat_id)

    def get_threat(self, threat_id: str) -> Threat:
        row = self._conn.execute(
            "SELECT id, name, threat_type, lat, lon, engagement_radius_nm, "
            "sensor_height_ft, sidc, actor, created_at FROM threats WHERE id = ?",
            (threat_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"no such threat: {threat_id}")
        return Threat(
            row["id"],
            row["name"],
            row["threat_type"],
            row["lat"],
            row["lon"],
            row["engagement_radius_nm"],
            row["sensor_height_ft"],
            row["sidc"],
            row["actor"],
            row["created_at"],
        )

    def list_threats(self) -> list[Threat]:
        rows = self._conn.execute("SELECT id FROM threats ORDER BY created_at").fetchall()
        return [self.get_threat(row["id"]) for row in rows]


def open_default_threat_store() -> ThreatStore:
    """The threat store the MCP server and API both open.

    Same physical sqlite file as turnpoint.store.open_default_store
    (DEFAULT_STORE_PATH) -- threats are a separate table in the one
    schema (src/turnpoint/store/db.py), not a separate database.
    """
    DEFAULT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return ThreatStore(DEFAULT_STORE_PATH)
