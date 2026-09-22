# Plan model

This is Turnpoint's own model, not an external format — the clean-room
sourcing procedure in `CLEAN_ROOM.md` does not apply. It still follows
`AGENTS.md`'s "flag gaps, don't invent" convention: open questions are
listed at the end rather than guessed at.

## v0 (current, `src/turnpoint/core/route.py`)

- **Turnpoint** — `name: str`, `lat: float`, `lon: float`. A named point on
  the earth, decimal degrees, WGS84 (`turnpoint.geodesy.DATUM`).
- **Leg** — `from_name`, `to_name`, `distance_nm`, `true_course_deg`,
  `ete_min: float | None`. Always *derived*, never stored: computed from a
  pair of turnpoints via `turnpoint.geodesy.range_bearing`.
- **Route** — `name: str`, `turnpoints: list[Turnpoint]`. An ordered
  sequence with `.legs(groundspeed_kt)` and `.total_distance_nm()`.

v0 has no altitude, no identity beyond `name`, and no persistence or
provenance — it is a pure in-memory value object, exactly matching what
`compute_route_legs` in the MCP server needs for a stateless calculation.

## v1 additions

### Altitude

`Turnpoint` gains `altitude_ft: float | None = None` — the planned altitude
at that turnpoint, feet MSL. `None` means unspecified (legal for a route
used only for distance/course math; required wherever terrain clearance is
checked). This is the only v0 field change; it is additive and backward
compatible with existing `Route` construction. See
`docs/decisions/0007-plan-model-v1-altitude.md`.

Deliberately out of v1: climb/descent profiles, groundspeed changes
mid-route, fuel state. These stay in scope for a later revision once a
concrete consumer (aero performance, Phase 2+) needs them — no speculative
fields.

### Plan

A `Plan` is the persisted, identified wrapper around a `Route`:

- `id: str` — opaque identifier assigned by the store on creation (UUID4).
- `name: str`
- `turnpoints: list[Turnpoint]` — same shape as `Route.turnpoints`; a
  `Plan` converts to a `Route` via `PlanStore.to_route(plan_id)` for leg
  math, so leg math is never duplicated between `core` and `store`.
- `created_at`, `updated_at` — timestamps from the store's injected clock,
  never wall-clock time read directly by planning code (`AGENTS.md` §6,
  determinism).

A `Plan` does not carry legs; legs are always recomputed from its
turnpoints, so there is never a stored value that can drift from the
computed one.

### Provenance event

Every mutation to a `Plan` (create, add/update/remove turnpoint) is
recorded as an append-only event, never overwritten or deleted:

- `id` — event id (monotonic per-plan sequence number, or UUID4).
- `plan_id`
- `actor: str` — who or what made the change (an MCP client identity, a
  human user id, etc.). Required; no default. Determinism and
  auditability depend on this never being inferred or guessed by the
  planning code itself.
- `tool_call: str` — the name of the operation that produced this event
  (e.g. `"create_plan"`, `"add_turnpoint"`). Matches the MCP tool name
  where the mutation came from MCP.
- `tool_call_args: dict` — the arguments of that call, JSON-serializable.
- `created_at` — from the injected clock.
- `parent_event_id: str | None` — the previous event for this plan, so the
  event log forms a chain and out-of-order or concurrent writes are
  detectable.

This satisfies the "Provenance" agent-interface property in
`docs/PLAN.md`: "every plan change records the actor and the tool call
that made it."

## Open gaps

- Multi-leg altitude changes (climb/descent between two turnpoints with
  different altitudes) are not modeled in v1 — `terrain_clear` (Phase 1,
  `src/turnpoint/terrain`) will need to decide whether to interpolate
  altitude linearly along a leg or treat the leg's altitude as the lower
  (more conservative) endpoint until a real requirement forces the choice.
  Flagging here rather than guessing; resolve when `terrain.clearance` is
  implemented.
- No units-of-measure abstraction: altitude is hardcoded feet, distance
  hardcoded nautical miles, matching `geodesy`'s existing convention
  (`METERS_PER_NM`). Revisit only if a format import needs a different
  unit natively.
