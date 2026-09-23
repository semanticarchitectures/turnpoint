# Phase 1 demo: plan a terrain-clear route

Walks through the Phase 1 exit criterion from `docs/PLAN.md`: *"An agent
plans a terrain-clear route between two airfields from a one-paragraph
tasking; a human sees it on the map."* Everything here is notional —
synthetic coordinates and a synthetic elevation raster, not a real place
(`data/README.md`'s public-data-only rule; see `make_dem.py`).

## Tasking

> Plan a route from notional airfield ALPHA (0.5N, 0.05E) to notional
> airfield BRAVO (0.5N, 0.95E). There is a terrain feature between the two
> fields. Check the route clears it by at least 500 ft, and show the
> result on the map.

## 0. One-time setup

```bash
pip install -e ".[dev]"
python scenarios/phase1-demo/make_dem.py       # writes data/phase1-demo-dem.tif
cd viewer && npm install && cd ..
```

## 1. Agent: plan and check (MCP)

An agent drives this over MCP (`python -m turnpoint.mcp_server`) with two
tool calls. First, a naive plan at 1500 ft — plausible if you only look at
the two endpoints, since 1500 ft clears the flat terrain around them:

```
create_plan(
  name="ALPHA-BRAVO low",
  actor="demo-agent",
  turnpoints=[
    {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 1500},
    {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 1500},
  ],
)
# -> {"plan": {"id": "<plan-id>", ...}, ...}

check_terrain_clearance(
  plan_id="<plan-id>",
  clearance_margin_ft=500,
  dted_source="data/phase1-demo-dem.tif",
)
# -> {"clear": false, "violations": [...], "meta": {"dted_source": "data/phase1-demo-dem.tif", ...}}
```

`check_terrain_clearance` flags it: the direct leg crosses the hill in the
middle. The agent revises to a safe altitude and checks again:

```
create_plan(
  name="ALPHA-BRAVO high",
  actor="demo-agent",
  turnpoints=[
    {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000},
    {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000},
  ],
)
check_terrain_clearance(plan_id="<new-plan-id>", clearance_margin_ft=500, dted_source="data/phase1-demo-dem.tif")
# -> {"clear": true, "violations": [], ...}
```

Without a live MCP client, the same two calls work over the REST API and
exercise the identical `store`/`terrain` code paths:

```bash
turnpoint-api &   # or: uvicorn turnpoint.api.app:app --port 8123

PLAN_ID=$(curl -s -X POST http://127.0.0.1:8123/plans -H 'Content-Type: application/json' -d '{
  "name": "ALPHA-BRAVO high", "actor": "demo-agent",
  "turnpoints": [
    {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000},
    {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000}
  ]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['plan']['id'])")

curl -s "http://127.0.0.1:8123/plans/$PLAN_ID/clearance?clearance_margin_ft=500&dted_source=data/phase1-demo-dem.tif"
echo "$PLAN_ID"
```

## 2. Human: see it on the map

With the API running and `$PLAN_ID` from above:

```bash
cd viewer && npm run dev
```

Open `http://localhost:5173/?plan=<plan-id>&api=http://127.0.0.1:8123` — the
route renders as a line between ALPHA and BRAVO with turnpoint markers, and
the status line shows the plan name and leg count. The permanent "not for
operational use" banner is always visible.

## Expected result

- The 1500 ft plan's `check_terrain_clearance` call returns `"clear": false`
  with a violation whose `terrain_elevation_ft` matches the synthetic
  hill (~9843 ft, i.e. 3000 m).
- The 15000 ft plan returns `"clear": true` with no violations.
- The viewer shows the (15000 ft) route on the map, fetched entirely
  through the REST API — never touching the store, terrain or tiles
  modules directly (decision 0003).
