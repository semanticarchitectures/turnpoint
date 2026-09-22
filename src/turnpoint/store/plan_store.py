"""SQLite-backed plan store with per-mutation provenance.

See docs/specs/plan-model.md for the model and docs/decisions/0007 for why
altitude and provenance events exist. Every mutating method requires an
explicit ``actor`` and ``tool_call`` — there is no default "system" actor —
because a plan change with no recorded author is exactly the silent
provenance loss this store exists to prevent (the "Provenance" agent
interface property in docs/PLAN.md).
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from turnpoint.core.route import Route, Turnpoint
from turnpoint.store.db import connect

Clock = Callable[[], datetime]

# The store the MCP server and API share, so a plan created via one is
# visible via the other (docs/PLAN.md Phase 1 exit criterion). Configurable
# via TURNPOINT_STORE_PATH; defaults to a local sqlite file, gitignored.
DEFAULT_STORE_PATH = Path(os.environ.get("TURNPOINT_STORE_PATH", ".turnpoint/store.sqlite3"))


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    turnpoints: list[Turnpoint]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ProvenanceEvent:
    id: str
    plan_id: str
    actor: str
    tool_call: str
    tool_call_args: dict[str, Any]
    created_at: str
    parent_event_id: str | None


class PlanStore:
    """SQLite-backed store for Plans (docs/specs/plan-model.md)."""

    def __init__(self, path: str | Path = ":memory:", *, clock: Clock = _utcnow) -> None:
        self._conn: sqlite3.Connection = connect(path)
        self._clock = clock

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PlanStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- reads ------------------------------------------------------

    def get_plan(self, plan_id: str) -> Plan:
        row = self._conn.execute(
            "SELECT id, name, created_at, updated_at FROM plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no such plan: {plan_id}")
        tps = self._conn.execute(
            "SELECT name, lat, lon, altitude_ft FROM turnpoints WHERE plan_id = ? ORDER BY seq",
            (plan_id,),
        ).fetchall()
        turnpoints = [Turnpoint(t["name"], t["lat"], t["lon"], t["altitude_ft"]) for t in tps]
        return Plan(row["id"], row["name"], turnpoints, row["created_at"], row["updated_at"])

    def list_plans(self) -> list[Plan]:
        rows = self._conn.execute("SELECT id FROM plans ORDER BY created_at").fetchall()
        return [self.get_plan(row["id"]) for row in rows]

    def events(self, plan_id: str) -> list[ProvenanceEvent]:
        rows = self._conn.execute(
            "SELECT id, plan_id, actor, tool_call, tool_call_args_json, created_at, "
            "parent_event_id FROM events WHERE plan_id = ? ORDER BY seq",
            (plan_id,),
        ).fetchall()
        return [
            ProvenanceEvent(
                r["id"],
                r["plan_id"],
                r["actor"],
                r["tool_call"],
                json.loads(r["tool_call_args_json"]),
                r["created_at"],
                r["parent_event_id"],
            )
            for r in rows
        ]

    def to_route(self, plan_id: str) -> Route:
        """Bridge to the pure leg-math value object (never duplicate leg math)."""
        plan = self.get_plan(plan_id)
        return Route(plan.name, plan.turnpoints)

    # -- mutations ----------------------------------------------------
    # Each wraps its writes and provenance event in one transaction: a
    # refused mutation (e.g. too few turnpoints) leaves no partial trace.

    def create_plan(
        self,
        name: str,
        turnpoints: list[Turnpoint],
        *,
        actor: str,
        tool_call: str,
        tool_call_args: dict[str, Any] | None = None,
    ) -> Plan:
        if len(turnpoints) < 2:
            raise ValueError("a plan needs at least two turnpoints")
        plan_id = str(uuid.uuid4())
        now = _iso(self._clock())
        with self._conn:
            self._conn.execute(
                "INSERT INTO plans (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (plan_id, name, now, now),
            )
            for seq, tp in enumerate(turnpoints):
                self._conn.execute(
                    "INSERT INTO turnpoints (plan_id, seq, name, lat, lon, altitude_ft) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (plan_id, seq, tp.name, tp.lat, tp.lon, tp.altitude_ft),
                )
            self._record_event(
                plan_id,
                actor=actor,
                tool_call=tool_call,
                tool_call_args=tool_call_args or {"name": name, "turnpoints": len(turnpoints)},
                now=now,
            )
        return self.get_plan(plan_id)

    def add_turnpoint(
        self,
        plan_id: str,
        turnpoint: Turnpoint,
        *,
        actor: str,
        tool_call: str,
        tool_call_args: dict[str, Any] | None = None,
    ) -> Plan:
        now = _iso(self._clock())
        with self._conn:
            next_seq = self._conn.execute(
                "SELECT COALESCE(MAX(seq), -1) + 1 AS next_seq FROM turnpoints WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()["next_seq"]
            self._conn.execute(
                "INSERT INTO turnpoints (plan_id, seq, name, lat, lon, altitude_ft) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    plan_id,
                    next_seq,
                    turnpoint.name,
                    turnpoint.lat,
                    turnpoint.lon,
                    turnpoint.altitude_ft,
                ),
            )
            self._record_event(
                plan_id,
                actor=actor,
                tool_call=tool_call,
                tool_call_args=tool_call_args or {"turnpoint": turnpoint.name},
                now=now,
            )
        return self.get_plan(plan_id)

    def update_turnpoint(
        self,
        plan_id: str,
        seq: int,
        turnpoint: Turnpoint,
        *,
        actor: str,
        tool_call: str,
        tool_call_args: dict[str, Any] | None = None,
    ) -> Plan:
        now = _iso(self._clock())
        with self._conn:
            cur = self._conn.execute(
                "UPDATE turnpoints SET name = ?, lat = ?, lon = ?, altitude_ft = ? "
                "WHERE plan_id = ? AND seq = ?",
                (turnpoint.name, turnpoint.lat, turnpoint.lon, turnpoint.altitude_ft, plan_id, seq),
            )
            if cur.rowcount == 0:
                raise KeyError(f"no turnpoint at seq {seq} in plan {plan_id}")
            self._record_event(
                plan_id,
                actor=actor,
                tool_call=tool_call,
                tool_call_args=tool_call_args or {"seq": seq, "turnpoint": turnpoint.name},
                now=now,
            )
        return self.get_plan(plan_id)

    def delete_turnpoint(
        self,
        plan_id: str,
        seq: int,
        *,
        actor: str,
        tool_call: str,
        tool_call_args: dict[str, Any] | None = None,
    ) -> Plan:
        now = _iso(self._clock())
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM turnpoints WHERE plan_id = ? AND seq = ?", (plan_id, seq)
            )
            if cur.rowcount == 0:
                raise KeyError(f"no turnpoint at seq {seq} in plan {plan_id}")
            remaining = self._conn.execute(
                "SELECT id, seq FROM turnpoints WHERE plan_id = ? AND seq > ? ORDER BY seq",
                (plan_id, seq),
            ).fetchall()
            for row in remaining:
                self._conn.execute(
                    "UPDATE turnpoints SET seq = ? WHERE id = ?", (row["seq"] - 1, row["id"])
                )
            remaining_count = self._conn.execute(
                "SELECT COUNT(*) AS n FROM turnpoints WHERE plan_id = ?", (plan_id,)
            ).fetchone()["n"]
            if remaining_count < 2:
                raise ValueError("a plan needs at least two turnpoints; refusing to delete")
            self._record_event(
                plan_id,
                actor=actor,
                tool_call=tool_call,
                tool_call_args=tool_call_args or {"seq": seq},
                now=now,
            )
        return self.get_plan(plan_id)

    def _record_event(
        self,
        plan_id: str,
        *,
        actor: str,
        tool_call: str,
        tool_call_args: dict[str, Any],
        now: str,
    ) -> None:
        if not actor:
            raise ValueError("actor is required")
        if not tool_call:
            raise ValueError("tool_call is required")
        last = self._conn.execute(
            "SELECT id, seq FROM events WHERE plan_id = ? ORDER BY seq DESC LIMIT 1",
            (plan_id,),
        ).fetchone()
        parent_id = last["id"] if last else None
        seq = (last["seq"] + 1) if last else 0
        self._conn.execute(
            "INSERT INTO events (id, plan_id, seq, actor, tool_call, tool_call_args_json, "
            "created_at, parent_event_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                plan_id,
                seq,
                actor,
                tool_call,
                json.dumps(tool_call_args),
                now,
                parent_id,
            ),
        )
        self._conn.execute("UPDATE plans SET updated_at = ? WHERE id = ?", (now, plan_id))


def open_default_store() -> PlanStore:
    """The store the MCP server and API both open, at DEFAULT_STORE_PATH."""
    DEFAULT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return PlanStore(DEFAULT_STORE_PATH)
