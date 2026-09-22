# Turnpoint

Open aircrew mission planning software, built for AI agents first and humans second.

Turnpoint is a headless mission planning engine with a Model Context Protocol (MCP)
server and a web map viewer. Agents plan routes, check terrain and airspace, and
produce standard artifacts through an API. Humans watch and verify on the map.

**Status: pre-alpha scaffold.** Nothing here is fit for operational use.

## Why it exists

1. To show what AI-assisted software development can do. The full history of this
   repository, including specs, decisions and the rules given to AI assistants, is
   part of the product.
2. To give agentic systems a shared, deterministic, scoreable environment for
   demonstrating mission planning.

## What it is not

- Not FalconView, not a fork of it, and not affiliated with GTRI. FalconView is a
  registered trademark of the Georgia Tech Research Corporation. Turnpoint aims to
  *import* FalconView drawing and local point files; it does not write them.
- Not for operational flight planning. Routes use generic parametric aircraft, threat
  overlays take notional user-supplied values, and outputs are not certified.
- Not a home for controlled data. Public, unclassified data only. See `AGENTS.md`.

## Layout

| Path | Purpose |
| --- | --- |
| `src/turnpoint/core` | Plan model: routes, points, drawings, constraints |
| `src/turnpoint/geodesy` | Range and bearing, coordinate formats, magnetic variation |
| `src/turnpoint/terrain` | Elevation queries, profiles, line-of-sight |
| `src/turnpoint/formats` | Import and export adapters (KML, GeoJSON, GPX, FalconView import) |
| `src/turnpoint/aero` | Airports, navaids, airspace from public FAA data |
| `src/turnpoint/tiles` | Raster tile service over GDAL |
| `src/turnpoint/store` | SQLite / GeoPackage plan store with provenance |
| `src/turnpoint/mcp_server` | MCP tool surface for agents |
| `src/turnpoint/api` | REST and WebSocket API for the viewer |
| `viewer/` | MapLibre GL JS web viewer (TypeScript) |
| `scenarios/` | Scenario definitions and scoring for agent evaluation |
| `docs/` | Plan, decision records, format specs |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m turnpoint.mcp_server   # starts the MCP server over stdio
```

## Ground rules

Read these before contributing, whether you are a person or an AI assistant:

- [`AGENTS.md`](AGENTS.md): rules for AI assistants and the people directing them
- [`CLEAN_ROOM.md`](CLEAN_ROOM.md): what may and may not be consulted
- [`SOURCES.md`](SOURCES.md): log of every external source used
- [`docs/PLAN.md`](docs/PLAN.md): scope, phasing and open decisions

## License

Apache 2.0. See `LICENSE` and `NOTICE`.
