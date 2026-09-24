# viewer/

Minimal MapLibre GL JS web viewer (TypeScript, Vite). Talks only to the
Turnpoint REST API (`src/turnpoint/api`); it has no private access to the
planning core (decision 0003).

## Run

```bash
npm install
npm run dev
```

Then open `http://localhost:5173/?plan=<id>&api=http://127.0.0.1:8123`
with the API running (`turnpoint-api`, or `uvicorn turnpoint.api.app:app`).

Query params:

- `plan` and/or `overlay` — the plan id and/or overlay id to display; at
  least one is needed to show anything, and both may be given together
  (e.g. a route alongside an imported KML/GeoJSON/GPX/FalconView-drawing
  overlay from `docs/specs/plan-model.md`'s `Overlay` model). A route
  renders as a blue line with red turnpoint markers; overlay features
  render distinctly by geometry type (amber points, dashed violet lines,
  teal polygons) so an imported overlay never reads as a flight plan.
- `api` — the API base URL (default `http://127.0.0.1:8123`).
- `tiles` — a tile source name to layer in as a raster basemap from the
  API's `/tiles` endpoint (optional; Phase 1/2 ship no bundled chart
  data, so the map shows just the plan/overlay on a plain background
  without it).
