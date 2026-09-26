# Third-party components and data

Add a row **before** adding the dependency. Verify the license at the pinned version.

| Component | Purpose | License | Verified | Notes |
| --- | --- | --- | --- | --- |
| geographiclib | Geodesic calculations | MIT | 2026-09-21, from package metadata | Runtime |
| mcp (Python SDK) 2.x | MCP server | MIT | 2026-09-21, from package metadata | Runtime; pinned >=2,<3 |
| pytest, ruff | Test and lint | MIT | 2026-09-21 | Dev only |
| rasterio 1.4.x | GeoTIFF/raster reads for `tiles`, `terrain` | BSD-3 | 2026-09-22, from package metadata (`License: BSD`, OSI BSD classifier) | Runtime; see decision 0009 |
| GDAL 3.10.x | Bundled inside the rasterio wheel; reads GeoTIFF, DTED, NITF/CADRG | MIT-style | 2026-09-22, from `rasterio/gdal_data/LICENSE.TXT` shipped in the installed wheel ("GDAL/OGR is licensed under an MIT style license"), read directly, not from memory | Not a separate dependency — no system GDAL install needed on the wheel platforms we target; see decision 0009 |
| rio-tiler 7.x/9.x | XYZ tile rendering from GeoTIFF/COG for `tiles` | BSD-3 | 2026-09-22, from package metadata | Runtime; see decision 0009 |
| numpy | Raster array access (rasterio's own array type); used directly by `terrain` and test fixtures | BSD-3 | 2026-09-22, from `LICENSE.txt` in the installed wheel, read directly | Runtime; already a transitive rasterio dependency, logged here because it is imported directly |
| fastapi | REST API for `src/turnpoint/api` | MIT | 2026-09-22, from `License-Expression: MIT` in the installed wheel's dist-info METADATA, read directly | Runtime |
| starlette | ASGI toolkit underlying FastAPI | BSD-3-Clause | 2026-09-22, from dist-info METADATA, read directly | Runtime; transitive via fastapi |
| uvicorn | ASGI server to run the API | BSD-3-Clause | 2026-09-22, from dist-info METADATA, read directly | Runtime |
| httpx | HTTP client used by FastAPI's TestClient | BSD-3-Clause | 2026-09-22, from package metadata | Dev/test only |
| maplibre-gl | Web map rendering for `viewer/` | BSD-3-Clause | 2026-09-22, `npm view maplibre-gl license` | Runtime (browser) |
| vite | Viewer dev server/bundler | MIT | 2026-09-22, `npm view vite license` | Dev only |
| typescript | Viewer language/build | Apache-2.0 | 2026-09-22, `npm view typescript license` | Dev only |
| gpxpy | GPX import for `src/turnpoint/formats/gpx.py` | Apache-2.0 | 2026-09-24, from package metadata (`License: Apache License, Version 2.0`) | Runtime; `fastkml` (LGPL) considered and rejected for KML, see decision 0010's Phase 2 research notes |
| access-parser | Reads `.mdb`/`.accdb` for `src/turnpoint/formats/fvimport/drawing.py` | Apache-2.0 | 2026-09-24, from `LICENSE` in the installed wheel's dist-info, read directly | Runtime; pure Python, no dependency on `mdbtools` (GPL, forbidden by `AGENTS.md`) — see decision 0012 |
| milsymbol 3.0.4 | MIL-STD-2525/APP6 symbol rendering for `viewer/` (threat `sidc`, M23) | MIT | 2026-09-26, from `license` field and `LICENSE`-equivalent in the installed package's own `package.json`, read directly | Runtime (browser); logged after the fact — should have been added before `npm install`, see `AGENTS.md` rule 3 |
| reportlab 5.0.x | PDF rendering for `src/turnpoint/products` (route card, Phase 4 "print products") | BSD-3-Clause-style | 2026-09-26, from `licenses/LICENSE` in the installed wheel's dist-info, read directly, not from the `METADATA` summary line alone | Runtime; built with `invariant=1` for byte-reproducible output (AGENTS.md section 6) |
| Pillow 12.x | Image handling; a transitive dependency reportlab imports directly (`reportlab.lib.utils`) | MIT-CMU | 2026-09-26, from `License-Expression: MIT-CMU` and `licenses/LICENSE` in the installed wheel's dist-info, read directly | Runtime; not imported by Turnpoint code itself, logged because reportlab cannot run without it |

Planned, not yet added: pyproj, Shapely, mgrs.
Do not add GPL or LGPL components, or non-commercial data such as
openAIP, without a decision record.
