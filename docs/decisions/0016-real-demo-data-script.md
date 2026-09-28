# 0016. Real demo data script: compose chart + DEM fetch, NASR stays best-effort

- Status: accepted
- Date: 2026-09-28

## Context

`docs/real-data-setup.md` documents three real public data sources and
how to wire each into Turnpoint by hand: a FAA VFR sectional chart
(`scripts/fetch_faa_chart.py`, decision 0015), a USGS 3DEP terrain
raster (a verified but until now undocumented-as-code `curl` recipe),
and a FAA NASR airport/navaid CSV extract (manual browse-and-download,
no fetch script). Doing all three by hand for every new demo area is
exactly the kind of repetitive operator step `scripts/fetch_faa_chart.py`
already exists to remove for chart data alone.

Researched the other two pieces to the same standard as decision 0015:

- **USGS 3DEP**: the `3DEPElevation` `ImageServer`'s `exportImage`
  operation, confirmed live 2026-09-28 (SOURCES.md S-016) — one GET
  request with a bounding box returns JSON naming a direct GeoTIFF
  download URL (`href`). No authentication, same pattern as the FAA
  chart API.
- **FAA NASR**: no equivalent API. `www.faa.gov` (unlike
  `external-api.faa.gov`) returned HTTP 403 to every fetch attempt in
  this environment — the HTML listing page and a guessed direct zip URL
  alike. The zip's naming convention, `28DaySubscription_Effective_
  <cycle-date>.zip` under a dated `NASR_Subscription/<cycle-date>/`
  path, is **inferred** from a third-party GitHub project's file
  references (SOURCES.md S-017), never independently confirmed to
  resolve.

## Decision

`scripts/fetch_real_demo_data.py` — a standalone script, same shape and
same reasoning as `fetch_faa_chart.py`: not part of `src/turnpoint`,
never reachable from MCP/REST, Turnpoint's own code never touches the
network. It composes three independent steps, each reported and each
allowed to fail without aborting the others:

1. **Chart** — calls straight into `fetch_faa_chart`'s already-tested
   `fetch_chart_product`/`download_and_extract` (no duplicated logic).
2. **Terrain** — a new `fetch_dem`/`download_dem` pair against the 3DEP
   `exportImage` endpoint, parsing tested against the real captured
   response (`tests/fixtures/dem_export/export-image-response.json`).
3. **Airports/navaids** — `fetch_nasr_csvs` attempts the inferred zip
   URL and extracts `APT_BASE.csv`/`NAV_BASE.csv` if it works; on any
   failure (network error, non-zip response, missing files) it raises
   a typed `NasrFetchFailed` that `main()` catches and turns into the
   exact manual-download instructions `docs/real-data-setup.md`
   already gives, never a silent skip.

`--nasr-cycle` has no default and is always required — decision 0011's
rule (never infer "whatever's current") applies exactly as much to this
script as it does to `src/turnpoint` itself, even though this script
sits outside the determinism boundary that rule was written for.
`--geoname`/`--bbox` default to the Washington, DC area (matching
`scenarios/phase2-demo`'s existing non-synthetic coordinates) so a
zero-argument-beyond-`--nasr-cycle` run produces something immediately
usable, while both stay fully overridable.

## Consequences

One command stages real chart, terrain and (when the inferred URL
happens to be right) NASR data for a demo area, cutting
`docs/real-data-setup.md`'s three separate manual procedures down to
one script plus, possibly, one manual NASR download. The NASR piece's
honesty matters more than its convenience here: it either works or it
fails loudly with the same instructions a human would have followed
anyway, never a wrong silent success.

## Alternatives considered

Guessing harder at the NASR zip URL and shipping it as if confirmed
(rejected: `AGENTS.md` section 4 — flag the gap, don't invent; a
confidently wrong download step is worse than an honest manual
fallback). Skipping NASR from this script entirely (rejected: worth one
best-effort attempt since the pattern is a real, if unconfirmed, lead —
succeeding sometimes is strictly better than never trying, as long as
failure is loud and never mistaken for success).

## Verified, and one real bug found and fixed

Ran for real on 2026-09-28 (the user's own machine, not the sandbox
this was written in): the chart and terrain steps both downloaded real
files — a ~60MB Washington sectional GeoTIFF and a real ~4MB USGS DEM,
both opened correctly by `rasterio` with their real CRSes (Lambert
Conformal Conic/NAD83 for the chart, EPSG:4326 for the DEM, elevations
a plausible -0.6 to 77m for the DC-area test bbox). The NASR guess
reached the real server and got a real 404 — reachable, wrong path,
exactly the "fail loud, fall back to instructions" behavior this was
designed for.

The first real run also hit an actual bug this decision's own testing
missed: `from scripts.fetch_faa_chart import ...` only resolves under
`python -m` or pytest (which this repo sets `pythonpath = ["."]` for) —
plain `python scripts/fetch_real_demo_data.py`, the exact form this
file's own usage examples show, put only `scripts/`, not the repo root,
on `sys.path`, so the import failed immediately with
`ModuleNotFoundError`. Fixed by inserting the repo root onto `sys.path`
at the top of the script before that import, so it works exactly as
documented regardless of invocation style. Lesson: an injectable-opener
unit test suite proves the logic works, not that the file runs the way
its own docstring tells someone to run it — that needs an actual
subprocess invocation, which the test suite didn't have.
