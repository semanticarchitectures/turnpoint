# Aero data (FAA NASR and Class Airspace)

Airport, navaid and class airspace data from FAA public sources. Not
FalconView-derived — this is Turnpoint's own mapping onto public
government data formats, so `CLEAN_ROOM.md`'s FalconView-specific
sourcing procedure does not apply, but the general "cite your sources"
discipline (`AGENTS.md` §3) does.

## Sources

- `SOURCES.md` S-009: the FAA NASR subscription page, cycle effective
  **2026-08-06** — pinned deliberately (see "Determinism" below).
- `SOURCES.md` S-010: `APT_BASE.csv` column layout (openNASR).
- `SOURCES.md` S-011: `NAV_BASE.csv` column layout (openNASR).
- `SOURCES.md` S-019: FAA AIS Open Data Dictionary — `Boundary Airspace`
  feature class field schema.
- `SOURCES.md` S-020: the Class Airspace shapefile itself, live
  download, real sample records.

Both `APT_BASE.csv` and `NAV_BASE.csv` have far more columns than
Turnpoint models (106 for `APT_BASE.csv` alone) — only what's needed for
"an agent uses the imported overlays" (`docs/PLAN.md`'s Phase 2 exit
criterion) is modeled. See "Open gaps."

## Model (`src/turnpoint/aero/models.py`)

**Airport** — one row of `APT_BASE.csv`:

- `ident: str` — `ARPT_ID`, the FAA's 3-4 character identifier.
- `icao_id: str | None` — `ICAO_ID`.
- `name: str` — `ARPT_NAME`.
- `lat: float`, `lon: float` — `LAT_DECIMAL`/`LONG_DECIMAL`, WGS84,
  consistent with `turnpoint.geodesy`.
- `elevation_ft: float | None` — `ELEV`, already feet MSL in the source.
- `site_type: str` — `SITE_TYPE_CODE` (e.g. airport vs. heliport), kept
  as the FAA's own code rather than translated, since the full code
  table isn't modeled (see "Open gaps").
- `facility_use: str` — `FACILITY_USE_CODE` (e.g. public vs. private
  use), same reasoning.
- `nasr_cycle: str` — **caller-supplied**, e.g. `"2026-08-06"`. Never
  read from the file or inferred from "whatever's current" — determinism
  means every result names the exact data version used (`AGENTS.md` §6),
  the same discipline `terrain.elevation_m`'s `dted_source` already
  follows.

**Navaid** — one row of `NAV_BASE.csv`: `ident` (`NAV_ID`), `name`
(`NAME`), `nav_type` (`NAV_TYPE`, e.g. `"VOR"`, `"NDB"`), `lat`, `lon`,
`elevation_ft` (`ELEV`), `nasr_cycle` — same shape and rationale as
`Airport`.

**Airspace** — one record of the Class Airspace shapefile
(`SOURCES.md` S-019/S-020, decision 0017):

- `ident: str`, `name: str` — `IDENT`/`NAME`.
- `airspace_class: str` — `CLASS` (`"B"`/`"C"`/`"D"`/`"E"`), FAA's raw
  value.
- `type_code: str`, `local_type: str` — `TYPE_CODE` (always `"CLASS"`
  for this shapefile), `LOCAL_TYPE` (e.g. `"CLASS_E5"` for a
  surface-based Class E extension).
- `boundary: list[tuple[float, float]]` — `(lat, lon)` ring, the
  exterior ring only (see "Open gaps").
- `upper_val`/`lower_val: float | None`, `upper_uom`/`lower_uom: str`,
  `upper_code`/`lower_code: str`, `upper_desc`/`lower_desc: str` —
  `UPPER_VAL`/`UPPER_UOM`/`UPPER_CODE`/`UPPER_DESC` and the `LOWER_*`
  equivalents, **kept as the FAA's raw fields, not resolved to a single
  absolute-MSL number** (same "keep raw codes" precedent as
  `site_type`/`facility_use` above) — `*_code` is one of `MSL`/`STD`/
  `SFC`/`UNLTD`, `*_uom` is `FT`/`FL`, `*_desc` qualifies how the value
  applies (`TI` "to and including," `AA` "and above," etc. — the full
  domain is in S-019). `*_val` is `None` when the source's `*_uom` and
  `*_code` are both blank — the FAA's own placeholder for "not
  applicable" (observed as a `-9998` sentinel in the raw shapefile,
  SOURCES.md S-020), not a real altitude.
- `exclusion: bool` — `EXCLUSION`; `true` means this polygon is an
  excluded area *within* another airspace record, not controlled
  airspace in its own right.
- `nasr_cycle: str` — same caller-supplied, never-inferred convention as
  `Airport`/`Navaid`, since the shapefile comes from the same dated
  28-day subscription folder.

## Parsing (`src/turnpoint/aero/nasr.py`, `class_airspace.py`)

`parse_airports(path, nasr_cycle)` and `parse_navaids(path, nasr_cycle)`
each return `(list[Airport | Navaid], FidelityReport)`. A row missing
its identifier, missing `LAT_DECIMAL`/`LONG_DECIMAL`, or with non-numeric
coordinates or elevation is skipped and named in the `FidelityReport`
(`format` `"nasr-apt"`/`"nasr-nav"`) rather than silently dropped
(`AGENTS.md` §4) — real NASR extracts do have occasional blank/malformed
fields, seen even in the self-made test fixtures's edge-case rows.

`list_airports_near(lat, lon, radius_nm, path, nasr_cycle)` filters
`parse_airports`'s result by great-circle distance
(`turnpoint.geodesy.range_bearing`). `get_airport(ident, ...)` and
`get_navaid(ident, ...)` look up by `ident` (or `icao_id` for airports),
raising `KeyError` if not found — the same not-found convention as
`PlanStore.get_plan`/`OverlayStore.get_overlay`.

`parse_class_airspace(path, nasr_cycle)` reads the Class Airspace
shapefile (`path` is the `.shp` file; `pyshp` finds the sibling
`.dbf`/`.shx` by the same basename) into `(list[Airspace],
FidelityReport)` (`format` `"class-airspace-shapefile"`). A record with
no boundary geometry is skipped. A record with more than one polygon
part (a hole, or multiple disjoint rings under one `NAME`) keeps only
the first (exterior) ring and is named in the `FidelityReport` — same
precedent as `turnpoint.formats.geojson`'s polygon-hole handling, never
a silent simplification (`AGENTS.md` §4). `list_class_airspace_near(lat,
lon, radius_nm, path, nasr_cycle)` filters by great-circle distance to
each boundary's arithmetic-mean centroid — a coarse placement, not true
point-in-polygon distance (same approximation the viewer already makes
for overlay polygon labels, M27).

## Determinism

Real NASR data refreshes every 28 days. Every parse call takes
`nasr_cycle` as a required argument and every MCP/API response names it,
so a result is always reproducible against the stated data version — the
caller supplies the file *and* asserts which cycle it is; Turnpoint does
not read a date out of the CSV and does not fetch anything over the
network itself.

## Open gaps

- Only 8 of `APT_BASE.csv`'s 106 columns and a similarly small slice of
  `NAV_BASE.csv` are modeled. `site_type`/`facility_use`/`nav_type` keep
  the FAA's raw codes rather than a translated enum — revisit if a
  concrete consumer needs runway data, frequencies, or the full code
  tables.
- `parse_airports`/`parse_navaids`/`parse_class_airspace` re-parse the
  whole file on every call, with no caching or spatial index. Fine for
  Phase 2's small, self-made fixture CSVs and decision 0017's
  reasoning; a real 28-day extract or the real 5612-record Class
  Airspace shapefile would want an index before this is anything but a
  demonstration.
- Class airspace boundaries are imported and queryable (decision 0017)
  but not resolved to a single absolute-MSL floor/ceiling, and nothing
  in `turnpoint.scenario`'s scorer checks a route against them yet —
  `ScoreReport.airspace_checked` stays `false`. Two real problems block
  that: `LOWER_CODE: SFC` needs a terrain lookup to become absolute MSL
  (ground elevation varies), and `STD`-referenced altitudes need an
  altimeter setting Turnpoint has no weather data to supply. Revisit
  once there's an actual design for route-vs-3D-volume intersection,
  not before.
- `parse_class_airspace` keeps only each record's exterior ring; 9 of
  5612 real nationwide records are multi-part (a hole or a second
  disjoint ring under the same `NAME`) and lose that detail, flagged in
  the `FidelityReport` each time.
