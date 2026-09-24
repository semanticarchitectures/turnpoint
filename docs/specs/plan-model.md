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

### Altitude along a leg

`terrain_clear` (`src/turnpoint/terrain/clearance.py`) interpolates
altitude **linearly by distance** between a leg's two turnpoints — the
standard assumption absent a separate climb/descent profile, and the plan
model has none in v1 (see below). Every turnpoint on a route being
clearance-checked must have `altitude_ft` set; a `None` anywhere raises,
rather than being silently treated as ground level or skipped.

## v2 additions

### Overlay

A `Plan` is route-shaped: an ordered, altitude-bearing sequence meant to
be flown. Imported KML, GPX, GeoJSON and FalconView *drawing* content is
usually not a route — it is arbitrary points, lines and polygons with
style/properties, closer to what `README.md`'s layout table already
called "drawings." `Overlay` is that shape:

- `id: str` — opaque identifier assigned by the store on creation (UUID4).
- `name: str`
- `source_format: str` — e.g. `"geojson"`, `"gpx"`, `"kml"`,
  `"fv-drawing"`, `"fv-local-points"`.
- `source_path: str` — the file the overlay was imported from.
- `features: list[OverlayFeature]` — see below.
- `actor: str` — who or what ran the import. Required, same rationale as
  a `Plan`'s provenance `actor` (never inferred).
- `created_at` — from the store's injected clock.

An `OverlayFeature` is one geometry:

- `geometry_type: "point" | "line" | "polygon"`.
- `coordinates: list[tuple[float, float]]` — `(lat, lon)` pairs, WGS84,
  consistent with `Turnpoint`. Exactly one pair for `"point"`, two or
  more for `"line"`, three or more for `"polygon"` (a single ring: first
  and last coordinate equal, no holes and no multi-ring polygons in v2 —
  revisit only if an importer produces one and needs it).
- `properties: dict` — free-form, importer-specific (name, style,
  original attributes), JSON-serializable.

Unlike a `Plan`, an `Overlay` is **import-once**: there is no
add/update/remove operation and so no per-mutation provenance event
chain — just the one `actor`/`created_at` recorded at creation. If a
concrete need for editing an imported overlay shows up later, extend
this rather than retrofit `Plan`'s event-chain machinery onto something
that doesn't need it. See `docs/decisions/0010-overlay-model.md`.

### FidelityReport

Every importer (`src/turnpoint/formats/*`) returns one alongside
whatever `Overlay`(s) it produces:

- `source_path: str`
- `format: str`
- `imported_count: int` — features successfully imported.
- `skipped: list[FidelityIssue]` — everything the importer could not
  fully interpret. Covers both a feature dropped entirely *and* a
  feature imported but with some information not carried over (e.g. a
  GeoJSON altitude value, since `OverlayFeature` is 2D — the point
  itself still imports, but the altitude is flagged, not silently
  dropped). Empty means fully faithful. Never silently drop data
  (`AGENTS.md` §4: "silent data loss is a bug").

A `FidelityIssue` is `item: str` (what was affected — a name, index or
other identifier from the source file) and `reason: str` (why).

## Open gaps

- No units-of-measure abstraction: altitude is hardcoded feet, distance
  hardcoded nautical miles, matching `geodesy`'s existing convention
  (`METERS_PER_NM`). Revisit only if a format import needs a different
  unit natively.
- Overlay storage schema (single JSON blob per overlay vs. a normalized
  features table) is decided in `src/turnpoint/store`, not here — this
  spec fixes the in-memory shape, not the on-disk one.
