"""SQLite-backed overlay store.

Overlays are import-once (decision 0010): unlike PlanStore, there is no
per-mutation provenance event chain -- just the actor and timestamp of
the import itself.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from turnpoint.core.overlay import Overlay, OverlayFeature
from turnpoint.store.db import connect
from turnpoint.store.plan_store import DEFAULT_STORE_PATH

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class OverlayStore:
    """SQLite-backed store for Overlays (docs/specs/plan-model.md)."""

    def __init__(self, path: str | Path = ":memory:", *, clock: Clock = _utcnow) -> None:
        self._conn: sqlite3.Connection = connect(path)
        self._clock = clock

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> OverlayStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def create_overlay(
        self,
        name: str,
        features: list[OverlayFeature],
        *,
        source_format: str,
        source_path: str,
        actor: str,
    ) -> Overlay:
        if not actor:
            raise ValueError("actor is required")
        overlay_id = str(uuid.uuid4())
        now = self._clock().isoformat()
        features_json = json.dumps([asdict(f) for f in features])
        with self._conn:
            self._conn.execute(
                "INSERT INTO overlays (id, name, source_format, source_path, "
                "features_json, actor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (overlay_id, name, source_format, source_path, features_json, actor, now),
            )
        return self.get_overlay(overlay_id)

    def get_overlay(self, overlay_id: str) -> Overlay:
        row = self._conn.execute(
            "SELECT id, name, source_format, source_path, features_json, actor, "
            "created_at FROM overlays WHERE id = ?",
            (overlay_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"no such overlay: {overlay_id}")
        return Overlay(
            row["id"],
            row["name"],
            row["source_format"],
            row["source_path"],
            _features_from_json(row["features_json"]),
            row["actor"],
            row["created_at"],
        )

    def list_overlays(self) -> list[Overlay]:
        rows = self._conn.execute("SELECT id FROM overlays ORDER BY created_at").fetchall()
        return [self.get_overlay(row["id"]) for row in rows]


def _features_from_json(features_json: str) -> list[OverlayFeature]:
    return [
        OverlayFeature(
            f["geometry_type"],
            [tuple(c) for c in f["coordinates"]],
            f["properties"],
        )
        for f in json.loads(features_json)
    ]


def open_default_overlay_store() -> OverlayStore:
    """The overlay store the MCP server and API both open.

    Same physical sqlite file as turnpoint.store.open_default_store
    (DEFAULT_STORE_PATH) -- overlays and plans are separate tables in one
    schema (src/turnpoint/store/db.py), not separate databases.
    """
    DEFAULT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return OverlayStore(DEFAULT_STORE_PATH)
