# 0015. Chart updates: a standalone fetch script, no network in Turnpoint itself

- Status: accepted
- Date: 2026-09-26

## Context

`docs/PLAN.md` Phase 4 names "chart updates" as a demand-driven item: a
pipeline for refreshing public raster chart data on a cycle.
`data/README.md` already lists "FAA raster charts" as an allowed public
data source. Decision 0011 already settled the adjacent question for
NASR airport/navaid data: caller-supplied file and cycle, no live
fetch, because `AGENTS.md` section 6 forbids network calls inside
planning computations and "current" is not a reproducible answer. The
same reasoning applies here — nothing changes about how
`src/turnpoint/tiles` or `terrain.elevation_m` consume a raster file;
what's missing is a way to *obtain* a current one without hand-browsing
the FAA site.

Researched what's actually available: the FAA publishes VFR sectional
charts as georeferenced GeoTIFF, zipped, through its own public
Aeronautic Product Release API (APRA) — a work of the US government, in
the public domain and additionally CC0-licensed (SOURCES.md S-014).
Confirmed live at `https://external-api.faa.gov/apra` on 2026-09-26,
no authentication required (S-015) — the API's older documented base,
`soa.smext.faa.gov`, is dead (DNS failure). `GET /vfr/sectional/chart
?geoname=<region>&edition=current|next&format=tiff` returns the current
edition's date, edition number and a download URL for the zip.

## Decision

`scripts/fetch_faa_chart.py` — a standalone script, not part of
`src/turnpoint` and not reachable from any MCP tool or REST route. It
calls the FAA's APRA API, downloads the current (or next) edition's
zip for a named region, and extracts everything in it as-is into
`data/charts/<region>_<edition_number>/` — never cherry-picking just
the `.tif`, so a companion `.tfw` or `.aux.xml` the georeferencing
might depend on is never silently dropped (`AGENTS.md` section 4). It
prints the edition date and number so the operator can name the cycle
the same way `dted_source`/`nasr_cycle` are already named in every
MCP/API response — Turnpoint's own code still never reads a version out
of a file or infers "whatever's current."

No new runtime dependency: `urllib.request`, `xml.etree.ElementTree`
and `zipfile` (all stdlib) are enough for one API call, one download
and one unzip. Parsing (`parse_chart_response`) is a pure function
tested against a real captured response (S-015's fixture,
`tests/fixtures/apra/sectional-chart-response.xml`); the network calls
(`fetch_chart_product`, `download_and_extract`) take an injectable
`opener` so tests never touch the network, consistent with the rest of
the suite.

**Verification gap, stated plainly:** this development environment has
no general outbound network access (confirmed: a direct `curl` to the
API failed at the DNS/connect level; only the sandboxed `WebFetch`/
`WebSearch` tools could reach it). The API calls and XML parsing were
verified against real, live responses fetched through those tools. The
actual download-and-unzip path was **not** exercised against a real FAA
zip file — the script's docstring says so. Run it once for real and
check the output before relying on it operationally.

## Consequences

Chart data acquisition is a one-command operator step, the same shape
as `scenarios/phase1-demo/make_dem.py` or manually obtaining a NASR
CSV extract — outside `src/turnpoint`, outside determinism's reach
because it never runs as part of a planning computation. Extending this
to other APRA product types (IFR enroute, TAC, helicopter charts) is a
small, mechanical follow-up if a concrete need appears — same
`fetch_x_product`/`download_and_extract` shape.

## Alternatives considered

Fetching inside `src/turnpoint/tiles` or a new MCP tool (rejected:
exactly the network-call-inside-a-planning-computation problem decision
0011 already ruled out, plus every re-run would silently pick up
whatever edition happens to be current that day). Vendoring a
downloaded chart into the repo (rejected: `data/` is git-ignored by
design, and a chart file is large and license-refreshed on a cycle —
nothing to commit). Building against the older `soa.smext.faa.gov`
base URL some third-party tooling still references (rejected: dead,
confirmed by DNS failure — `external-api.faa.gov` is what's actually
live).
