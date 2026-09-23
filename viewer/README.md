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

- `plan` (required) — the plan id to display.
- `api` — the API base URL (default `http://127.0.0.1:8123`).
- `tiles` — a tile source name to layer in as a raster basemap from the
  API's `/tiles` endpoint (optional; Phase 1 ships no bundled chart data,
  so the map shows just the route on a plain background without it).
