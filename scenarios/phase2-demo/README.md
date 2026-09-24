# Phase 2 demo: import overlays, query aero data, see it on the map

Walks through the Phase 2 exit criterion from `docs/PLAN.md`: *"Sample
files import with a fidelity report and an agent uses the imported
overlays."* Everything here is notional — self-made sample files, not
real chart data or a real place.

## Tasking

> Import a GeoJSON, GPX and KML overlay describing a notional boundary
> and checkpoint. Look up nearby notional airfields. Plan a route past
> them. Show the route and one imported overlay together on the map.

## 0. One-time setup

```bash
pip install -e ".[dev]"
python scenarios/phase2-demo/make_samples.py   # writes data/phase2-demo/
cd viewer && npm install && cd ..
```

## 1. Agent: import overlays and query aero data (MCP or REST)

Start the API from the repo root (so its default `data/` directory
resolves `phase2-demo/...` paths):

```bash
turnpoint-api &   # or: uvicorn turnpoint.api.app:app --port 8123
```

Import each format. All three go through the same generic overlay
surface (`import_overlay` over MCP, `POST /overlays/import` over REST)
built in M11 and extended by M12/M13:

```bash
curl -s -X POST http://127.0.0.1:8123/overlays/import -H 'Content-Type: application/json' -d '{
  "format": "geojson", "path": "phase2-demo/sample.geojson",
  "name": "GeoJSON overlay", "actor": "demo-agent"
}'

curl -s -X POST http://127.0.0.1:8123/overlays/import -H 'Content-Type: application/json' -d '{
  "format": "gpx", "path": "phase2-demo/sample.gpx",
  "name": "GPX overlay", "actor": "demo-agent"
}'

curl -s -X POST http://127.0.0.1:8123/overlays/import -H 'Content-Type: application/json' -d '{
  "format": "kml", "path": "phase2-demo/sample.kml",
  "name": "KML overlay", "actor": "demo-agent"
}'
```

Each response carries a `fidelity_report` with `fully_faithful: true` for
these clean samples — try feeding one of `tests/fixtures/*/edge_cases.*`
instead to see a `false` one with named reasons.

Query nearby notional airfields (M14, FAA NASR CSV):

```bash
curl -s "http://127.0.0.1:8123/aero/airports?lat=38.85&lon=-77.03&radius_nm=50&nasr_source=phase2-demo/apt_base_sample.csv&nasr_cycle=2026-08-06"
```

`nasr_cycle` is required and named in the response `meta` — decision
0011's determinism rule: never "whatever's current."

See the FalconView drawing importer's honesty about its own limits
(M16, decision 0012) without needing a real `.mdb` file — none can be
constructed, so this fakes the Access reader the same way the tests do:

```bash
python scenarios/phase2-demo/demo_fv_drawing.py
```

Expect `fully_faithful: False` — the sample's `OVAL` feature imports as
a point with an explicit fidelity issue naming exactly why (shape/size
not reconstructed), never a silent simplification.

Plan a route past the imported checkpoint (same M6/Phase-1 flow):

```bash
PLAN_ID=$(curl -s -X POST http://127.0.0.1:8123/plans -H 'Content-Type: application/json' -d '{
  "name": "Phase 2 demo route", "actor": "demo-agent",
  "turnpoints": [
    {"name": "ALPHA", "lat": 38.0, "lon": -77.0, "altitude_ft": 5000},
    {"name": "BRAVO", "lat": 38.9, "lon": -75.5, "altitude_ft": 5000}
  ]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['plan']['id'])")
echo "$PLAN_ID"
```

## 2. Human: see the route and an overlay together

With the API running, `$PLAN_ID` from above, and `$GEOJSON_ID` from the
GeoJSON import response:

```bash
cd viewer && npm run dev
```

Open
`http://localhost:5173/?plan=<PLAN_ID>&overlay=<GEOJSON_ID>&api=http://127.0.0.1:8123`
(M18) — the route renders as a blue line with red turnpoint markers, and
the GeoJSON overlay renders alongside it with distinct styling (amber
point, dashed violet line, teal polygon) so it never reads as part of
the flight plan. The status line names both.

## Expected result

- All three format imports (GeoJSON, GPX, KML) return
  `"fully_faithful": true` for the clean samples.
- The airport query returns both notional test airfields
  (`TP01`, `TP02`), with `nasr_cycle` named in `meta`.
- The FalconView drawing demo returns `fully_faithful: false`, with the
  `OVAL` feature's fidelity issue naming exactly what wasn't
  reconstructed and why (decision 0012).
- The viewer shows the route and the GeoJSON overlay together, fetched
  entirely through the REST API — never touching the store, formats,
  aero or tiles modules directly (decision 0003).
