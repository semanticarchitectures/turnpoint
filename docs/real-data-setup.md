# Setting up Turnpoint against real public data

Turnpoint ships with **no data at all** (`data/` is git-ignored by
design — decision 0011) and never fetches anything automatically except
when you explicitly run one of the fetch scripts below. Every demo in
`scenarios/` uses synthetic coordinates and a synthetic terrain raster.
This guide is for pointing Turnpoint at a real place with real public
data instead, to get as close as this project gets to operational
realism.

**It still does not get you to operational realism.** Read
["What stays simulated"](#what-stays-simulated-even-with-all-of-this) at
the end before you trust anything it produces. The banner on every
surface — "Not for operational use" — is accurate, not boilerplate.

## Quick path: one command for all three

`scripts/fetch_real_demo_data.py` (decision 0016) runs the chart, DEM
and NASR steps below in one go, defaulting to the Washington, DC area:

```bash
python scripts/fetch_real_demo_data.py --nasr-cycle 2026-09-03   # use the actual current cycle
```

Or a different area:

```bash
python scripts/fetch_real_demo_data.py \
  --geoname "San Francisco" --bbox -122.6,37.6,-122.3,37.9 \
  --nasr-cycle 2026-09-03
```

`--nasr-cycle` has no default — browse the [NASR subscription
page](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/)
to find the real current one (decision 0011: never guess). Everything
lands in `data/real-demo/`. The NASR step is best-effort — its download
URL was inferred, not confirmed (see the script's own docstring); if it
fails, it prints the exact manual steps from section 3 below. Read on
for what each step does and how to do it by hand.

## What you'll assemble

| Need | Real source | What Turnpoint does with it |
| --- | --- | --- |
| Basemap imagery | FAA VFR sectional chart (GeoTIFF) | `viewer`'s `?tiles=` raster layer |
| Terrain elevation | USGS 3DEP DEM (GeoTIFF) | `dted_source` for clearance/LOS/exposure checks |
| Airports and navaids | FAA NASR 28-day CSV subscription | `nasr_source`/`nasr_cycle` for airport/navaid lookup |

All three are real, current, public data. None of it ships with the
repo or gets downloaded without you running a command.

## 1. Chart imagery

`scripts/fetch_faa_chart.py` (added M29, decision 0015) calls the FAA's
own public Aeronautic Product Release API and downloads a current VFR
sectional chart:

```bash
python scripts/fetch_faa_chart.py --geoname Washington
```

It prints the edition date/number, then writes every file from the
FAA's zip — the GeoTIFF and anything that ships alongside it — into
`data/charts/Washington_<edition>/`. `ls` that directory to find the
`.tif` filename; pass it to the viewer as a relative path under `data/`:

```
http://localhost:5173/?plan=<id>&tiles=charts/Washington_<edition>/<whatever.tif>&api=http://127.0.0.1:8123
```

`--geoname` must be one of the FAA's ~54 named sectional regions:
Albuquerque, Anchorage, Atlanta, Bethel, Billings, Brownsville, Cape
Lisburne, Charlotte, Cheyenne, Chicago, Cincinnati, Cold Bay,
Dallas-Ft Worth, Dawson, Denver, Detroit, Dutch Harbor, El Paso,
Fairbanks, Great Falls, Green Bay, Halifax, Hawaiian Islands, Houston,
Jacksonville, Juneau, Kansas City, Ketchikan, Klamath Falls, Kodiak,
Lake Huron, Las Vegas, Los Angeles, McGrath, Memphis, Miami, Montreal,
New Orleans, New York, Nome, Omaha, Phoenix, Point Barrow, Salt Lake
City, San Antonio, San Francisco, Seattle, Seward, St Louis, Twin
Cities, Washington, Western Aleutian Islands, Whitehorse, Wichita.

**Caveat carried over from decision 0015:** this download path was
verified against the live API but never exercised end to end in
Turnpoint's own development sandbox (no general network access there).
If it doesn't work cleanly, that's the likeliest place — check the
printed edition info and the zip contents before assuming your route is
wrong.

## 2. Terrain elevation

Nothing in Turnpoint fetches elevation data — you get it from USGS
directly. Two ways:

**Point and click:** [The National Map downloader](https://apps.nationalmap.gov/downloader/) —
draw a box around your area of interest, pick "1/3 arc-second DEM"
(~10m posts), download as GeoTIFF.

**Scriptable, verified working:** the 3DEP elevation ImageServer's
`exportImage` operation returns a GeoTIFF for a bounding box in one
request:

```bash
curl -s "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage\
?bbox=-77.1,38.7,-77.0,38.8&bboxSR=4326&size=1024,1024&imageSR=4326\
&format=tiff&pixelType=F32&f=json"
```

`bbox` is `west,south,east,north` in decimal degrees (EPSG:4326). The
JSON response's `"href"` field is a direct download link to the
GeoTIFF — `curl -o data/dem.tif <href>`. Verified live on 2026-09-27:
returned a real ~4MB GeoTIFF with WGS84 georeferencing for a box over
Washington, DC.

Use the downloaded file as `dted_source` anywhere Turnpoint takes one —
`check_terrain_clearance`, `line_of_sight`, `check_threat_exposure`, or
a scenario file's `dted_source` field. Every turnpoint's `altitude_ft`
is still something *you* supply; Turnpoint never infers a safe altitude
from the terrain, only checks the one you gave it.

## 3. Airports and navaids

Real airport/navaid data comes from the FAA's own [28-Day NASR
Subscription](https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/) —
browse to the current dated folder (it refreshes every 28 days; decision
0011 is explicit that Turnpoint never guesses which cycle is "current,"
so neither should you — read the date off the page) and download the
CSV data set. Inside it, `turnpoint.aero.nasr` reads exactly two files
by name:

- `APT_BASE.csv` — airports (`turnpoint.aero.parse_airports`)
- `NAV_BASE.csv` — navaids (`turnpoint.aero.parse_navaids`)

Point `nasr_source` at either file's path and `nasr_cycle` at the
folder's date (e.g. `"2026-08-06"`, whatever the current one actually
is) — both are required on every call, never inferred, and both are
named back in every response's `meta`:

```bash
curl -s "http://127.0.0.1:8123/aero/airports?lat=38.85&lon=-77.03&radius_nm=50&nasr_source=APT_BASE.csv&nasr_cycle=2026-XX-XX"
```

(`nasr_source` here is a filename resolved under `data/` — put
`APT_BASE.csv` there, or pass a path like `real/APT_BASE.csv` if you
keep it in a subfolder.)

Only 8 of `APT_BASE.csv`'s 106 real columns are modeled
(`docs/specs/aero-data.md`'s "Open gaps") — runway data, frequencies and
full FAA code tables aren't read. Don't expect a complete airport
record back, just identity, position, elevation and a couple of type
codes.

## Putting it together

1. Pick a real, non-sensitive area you have chart/DEM coverage for.
2. Run the two fetch steps above (chart, elevation) for that area; get a
   real NASR extract and locate `APT_BASE.csv`/`NAV_BASE.csv` in it.
3. Start the API (`turnpoint-api`) and create a plan with real
   coordinates and altitudes for that area.
4. `check_terrain_clearance` against the real DEM.
5. `list_airports_near` against the real NASR CSV.
6. Open the viewer with `?plan=<id>&tiles=<your chart .tif>&api=...` —
   real chart imagery under a route checked against real terrain.

Every MCP/API response still names exactly which files and cycle it
used (`AGENTS.md` section 6) — if you come back to this next month with
a fresh NASR cycle or a new chart edition, old results stay traceable to
what produced them.

## What stays simulated even with all of this

- **No airspace.** No class B/C/D/E polygons, no import, nothing scored.
  A "clear" route from Turnpoint says nothing about airspace legality.
- **No weather, no NOTAMs, no TFRs.** Nothing time-sensitive is checked,
  ever — real data or not.
- **No aircraft performance modeling.** Legs use plain geodesic
  distance/time; nothing about climb rates, fuel burn, or a specific
  airframe.
- **True bearings only.** `turnpoint.geodesy` computes true, not
  magnetic, courses — there's no WMM/declination model
  (`pyproj`/`mgrs` are listed "planned, not yet added" in
  `docs/THIRD_PARTY.md`). Convert to magnetic yourself if you need it.
- **Decimal degrees only.** No MGRS or UTM input — convert coordinates
  from a chart yourself before typing them into a plan.
- **Threats stay notional, always.** Even against a real chart, any
  threat you add is a made-up ring with a made-up name — `AGENTS.md`
  forbids real threat system parameters outright, no exception for a
  real place.
- **Nothing here is certified.** Determinism and provenance
  (`AGENTS.md` section 6) mean a result is *reproducible*, not that
  it's *correct* for real-world flight planning.
