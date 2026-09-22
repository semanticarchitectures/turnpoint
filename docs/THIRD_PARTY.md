# Third-party components and data

Add a row **before** adding the dependency. Verify the license at the pinned version.

| Component | Purpose | License | Verified | Notes |
| --- | --- | --- | --- | --- |
| geographiclib | Geodesic calculations | MIT | 2026-09-21, from package metadata | Runtime |
| mcp (Python SDK) 2.x | MCP server | MIT | 2026-09-21, from package metadata | Runtime; pinned >=2,<3 |
| pytest, ruff | Test and lint | MIT | 2026-09-21 | Dev only |

Planned, not yet added: GDAL/Rasterio, pyproj, Shapely, mgrs, FastAPI, rio-tiler,
access-parser, MapLibre GL JS, milsymbol. Do not add GPL or LGPL components, or
non-commercial data such as openAIP, without a decision record.
