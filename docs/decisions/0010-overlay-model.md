# 0010. Overlay model: import-once geometry, separate from Plan

- Status: accepted
- Date: 2026-09-23

## Context
Phase 2 (`docs/PLAN.md`, "Exchange") needs to import KML, GPX, GeoJSON
and FalconView drawing/local-point files. The existing plan model
(`docs/specs/plan-model.md` v1) is route-shaped — an ordered,
altitude-bearing `Plan`/`Turnpoint` sequence meant to be flown. Most
imported content (arbitrary points, lines, polygons with style
properties) does not fit that shape, and forcing it in would mean either
inventing fake altitudes/ordering for non-route data or overloading
`Plan`'s per-mutation provenance event chain onto something that is
never mutated after import.

## Decision
Add a separate `Overlay` model: `id`, `name`, `source_format`,
`source_path`, `features: list[OverlayFeature]`, `actor`, `created_at`.
No altitude, no ordering semantics, no provenance event chain — just the
one `actor`/`created_at` at creation, since overlays are import-once.
Add a shared `FidelityReport` (`source_path`, `format`, `imported_count`,
`skipped: list[FidelityIssue]`) that every Phase 2 importer returns.
Full shapes are in `docs/specs/plan-model.md`.

## Consequences
Every Phase 2 importer (`src/turnpoint/formats/geojson.py`, `gpx.py`,
`kml.py`, `fvimport/drawing.py`, `fvimport/local_points.py`) targets one
shared model and one shared fidelity-report contract, set once here
rather than each importer inventing its own. `Plan`'s provenance
machinery (`docs/decisions/0007`) stays untouched and route-specific.

## Alternatives considered
Extend `Plan`/`Turnpoint` to cover arbitrary geometry (rejected: would
either force fake altitudes onto non-route points or make altitude
optional everywhere, weakening the terrain-clearance guarantee that
depends on it always being set on a route). A single per-feature
provenance event chain like `Plan`'s (rejected as premature: nothing in
Phase 2's scope mutates an overlay after import; add it if a concrete
editing need appears).
