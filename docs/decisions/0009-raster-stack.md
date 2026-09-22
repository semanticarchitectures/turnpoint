# 0009. Raster stack: rasterio + rio-tiler, GDAL vendored not separate

- Status: accepted
- Date: 2026-09-22

## Context
`docs/PLAN.md`'s Phase 1 scope needs GeoTIFF/CADRG tile rendering
(`src/turnpoint/tiles`) and DTED elevation queries (`src/turnpoint/terrain`).
`docs/THIRD_PARTY.md` listed "GDAL/Rasterio" and "rio-tiler" as planned but
not verified, and `AGENTS.md` §3 requires a verified license entry before a
dependency is added.

## Decision
Add `rasterio` (BSD-3, verified 2026-09-22 from installed package metadata)
and `rio-tiler` (BSD-3, verified the same way) as runtime dependencies.
Neither needs a separate system GDAL install: rasterio's PyPI wheels for
the platforms we target (Linux manylinux, macOS) vendor `libgdal` inside
the wheel. GDAL/OGR's own license — read directly from
`rasterio/gdal_data/LICENSE.TXT` as shipped in the installed wheel, not
from memory — states: "In general GDAL/OGR is licensed under an MIT style
license," with a handful of individually-licensed files (also permissive:
BSD/MIT-style, e.g. `port/cpl_float.cpp`). This clears the Apache
2.0/MIT/BSD bar in `AGENTS.md` §3.

## Consequences
`src/turnpoint/tiles` (GeoTIFF via `rio-tiler`, CADRG via direct
`rasterio`/GDAL NITF/RPF driver reads) and `src/turnpoint/terrain`
(DTED via GDAL's native driver) can now be implemented. No CI or
contributor machine needs a system GDAL install for the platforms covered
by upstream wheels; a from-source build (e.g. an unsupported platform)
would need to separately verify whatever system GDAL is linked there.

## Alternatives considered
A separate top-level `GDAL` PyPI binding (rejected: its wheels are less
consistently available across platforms than rasterio's, and rasterio
already exposes what Phase 1 needs). Pure-Python DTED/GeoTIFF parsing
(rejected: reinvents a well-tested, permissively licensed reader for no
Phase 1 benefit).
