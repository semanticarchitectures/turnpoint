# 0008. SQLite, not GeoPackage, for the Phase 1 plan store

- Status: accepted
- Date: 2026-09-22

## Context
Decision 0004 left native plan storage as "SQLite or GeoPackage" open. The
Phase 1 plan store only needs to persist an ordered list of turnpoints and
per-mutation provenance events per plan (`docs/specs/plan-model.md`) — no
spatial queries and no geometry beyond point lat/lon.

## Decision
Use SQLite via Python's stdlib `sqlite3`; no new dependency. Schema and
migrations are hand-rolled in `src/turnpoint/store/db.py` as a small,
numbered list of migration scripts rather than adopting a migration
framework.

## Consequences
Phase 1 persistence needs no GDAL/OGR dependency. Revisit GeoPackage when
Phase 2/3 overlays (imported drawings, airspace polygons, notional threat
rings) need real spatial indexing — GeoPackage is itself SQLite-based, so a
later store can add GeoPackage-backed overlay tables alongside these plan
tables rather than replacing them.

## Alternatives considered
GeoPackage now (rejected: pulls in GDAL/OGR for no present benefit; Phase 1
geometry is fully representable as plain lat/lon columns). Alembic-style
migrations (rejected: the migration surface is small enough that hand-rolled
numbered scripts are simpler and keep the dependency list unchanged).
