# Aero data (FAA NASR)

Airport and navaid data from the FAA's public 28-Day NASR Subscription
CSV files. Not FalconView-derived — this is Turnpoint's own mapping onto
a public government data format, so `CLEAN_ROOM.md`'s FalconView-specific
sourcing procedure does not apply, but the general "cite your sources"
discipline (`AGENTS.md` §3) does.

## Sources

- `SOURCES.md` S-009: the FAA NASR subscription page, cycle effective
  **2026-08-06** — pinned deliberately (see "Determinism" below).
- `SOURCES.md` S-010: `APT_BASE.csv` column layout (openNASR).
- `SOURCES.md` S-011: `NAV_BASE.csv` column layout (openNASR).

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

## Parsing (`src/turnpoint/aero/nasr.py`)

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
- `parse_airports`/`parse_navaids` re-parse the whole file on every call,
  with no caching or spatial index. Fine for Phase 2's small, self-made
  fixture CSVs; a real 28-day extract (tens of thousands of rows) would
  want an index before this is anything but a demonstration.
- Class airspace (`docs/decisions/0010`'s Phase 2 research notes) is
  explicitly out of scope here — recommended for Phase 3.
