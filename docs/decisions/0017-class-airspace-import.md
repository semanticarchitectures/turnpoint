# 0017. Class airspace: real FAA shapefile import, no scoring integration yet

- Status: accepted
- Date: 2026-10-10

## Context

`docs/PLAN.md` Phase 2's exit note and Phase 3's status both flag the
same gap: no class airspace overlay exists, so `turnpoint.scenario`'s
scorer reports `airspace_checked: false` and means it. `turnpoint.aero`'s
own `__init__.py` docstring already said "Airspace (class B/C/D/etc,
SUA) is deferred."

Researched what FAA data actually contains before deciding anything,
per `CLEAN_ROOM.md`'s procedure:

- The NASR CSV subscription's `CLS_ARSP.csv` table (same 28-day
  subscription the airport/navaid CSVs come from) is **not** boundary
  geometry — it's a flat airport-to-class-flag table (does Class
  B/C/D/E airspace exist near this airport: Y/blank), no coordinates,
  no floor/ceiling. A dead end for anything spatial.
- The FAA separately publishes a **Class Airspace shapefile**
  (`class_airspace_shape_files.zip`, confirmed live at `nfdc.faa.gov`,
  SOURCES.md S-020) — real polygon boundaries, 5612 nationwide records,
  NAD83 geographic, with genuine floor/ceiling attributes
  (`UPPER_VAL`/`UPPER_UOM`/`UPPER_CODE`, `LOWER_VAL`/`LOWER_UOM`/
  `LOWER_CODE`) and a `CLASS` field (B/C/D/E). Confirmed against the
  FAA's own published field dictionary (SOURCES.md S-019) and by
  inspecting real sample records (New Orleans Class B: 1000–7000 ft
  MSL; Flint Class C: SFC–4800 ft MSL; a Class E5 surface extension
  with `UPPER_DESC: AA` — "and above," no explicit ceiling).

## Decision

**Import and model only, this decision.** `src/turnpoint/aero/
class_airspace.py` parses the real shapefile (`parse_class_airspace`,
`list_class_airspace_near` — same shape as `nasr.py`'s airport/navaid
functions, same `nasr_cycle` determinism discipline since the shapefile
comes from the same dated subscription folder) into a new `Airspace`
model (`src/turnpoint/aero/models.py`). Faithful passthrough of the raw
FAA fields, same precedent as `site_type`/`facility_use` in
`docs/specs/aero-data.md`: `upper_code`/`lower_code` (MSL/STD/SFC/UNLTD)
are kept as-is, never resolved to a single absolute-MSL number here.

**Not decided or built here: resolving floor/ceiling to absolute MSL,
or wiring this into `turnpoint.scenario`'s scorer.** Two real
unresolved problems block that, found during this research, not
invented to justify deferring:

- `LOWER_CODE: SFC` means the floor is ground-relative, not a fixed
  sea-level value — resolving it to absolute MSL needs a terrain/DEM
  lookup at the boundary's location (`turnpoint.terrain.elevation_m`
  could do this, but nothing wires it up).
- `UPPER_CODE`/`LOWER_CODE: STD` references standard atmospheric
  pressure (29.92 inHg), not true MSL — the two diverge with the local
  altimeter setting, which Turnpoint has no weather data to supply.

Guessing at these (e.g., treating `STD` as exactly `MSL`, or `SFC` as
always `0` MSL) would be exactly the kind of invented precision
`AGENTS.md` section 4 forbids. Better to ship a correct, honest import
now and solve altitude resolution as its own, later decision once
there's a concrete design for it (route-vs-3D-volume intersection is
real work beyond this decision's scope regardless).

**Dependency: `pyshp` (MIT), not Fiona/GDAL's vector API.** The
shapefile is a simple polygon dataset — pure-Python `pyshp` reads it
correctly (verified against the real file: `PolygonZ` shape type, Z
always `0` across all 5612 records and not preserved — same "not
meaningful, not kept" treatment as `OverlayFeature`'s existing 2D-only
polygon handling). No new GDAL/OGR binding needed, unlike `rasterio`
(decision 0009), which is for raster, not vector, data.

**Multi-part polygons (holes/multiple rings): only the exterior ring is
kept**, flagged in the `FidelityReport` — identical precedent to
`turnpoint.formats.geojson`'s existing "polygon holes present in source
but not preserved" handling. 9 of 5612 real records are multi-part
(confirmed by scanning the whole file); rare, but real, so it's
exercised in the test fixture (`tests/fixtures/class_airspace/`, a
genuine ~5-record excerpt of the real file, not synthetic).

**No persistence, no spatial index** — `list_class_airspace_near`
re-parses the file on every call, same as `nasr.py`'s
`list_airports_near`. Explicitly accepted there already
(`docs/specs/aero-data.md` "Open gaps": "fine for Phase 2's small,
self-made fixture CSVs; a real 28-day extract would want an index
before this is anything but a demonstration") — same tradeoff, same
reasoning, now extended to a dataset an order of magnitude larger
(5612 polygons, up to tens of thousands of vertices each) where it
matters more. Revisit together if either becomes a real problem.

## Consequences

An agent (or the viewer) can now ask "what controlled airspace is near
this point" against real, current FAA data and get real polygons with
real floor/ceiling attributes back — closing the "no class airspace
overlay exists" gap `docs/PLAN.md` has flagged since Phase 2. The
scorer still can't check a route against it; that's the next decision,
once altitude resolution has an actual design.

## Alternatives considered

Resolving `SFC`/`STD` to approximate absolute-MSL numbers now, with a
documented caveat (rejected: a documented wrong number in a safety-
adjacent field is worse than an honestly unresolved one — the same
judgment this project already made for `AGENTS.md` section 2's "no
real aircraft/threat performance data" rule, applied to airspace
altitudes instead). Fiona for shapefile reading (rejected: pulls in a
full GDAL vector binding for a plain polygon format `pyshp` reads
correctly on its own, no new system dependency either way, but more
surface area than needed). Parsing `CLS_ARSP.csv` instead of the
shapefile (rejected: it has no boundary geometry at all — a dead end
for anything spatial, confirmed by reading its real data before
deciding).
