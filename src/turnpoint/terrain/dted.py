"""Elevation queries via GDAL (DTED, GeoTIFF, or any other GDAL raster format).

Turnpoint targets DTED (MIL-PRF-89020, per data/README.md) in production,
but the reader is format-agnostic: GDAL, via rasterio, exposes the same API
whether the underlying file is DTED, a GeoTIFF DEM, or a COG (decision
0009). Tests use synthetic GeoTIFF fixtures rather than DTED's restrictive
1x1-degree tiling rules.
"""

from __future__ import annotations

from pathlib import Path

import rasterio
from rasterio.io import DatasetReader

METERS_PER_FT = 0.3048


def _sample(ds: DatasetReader, lat: float, lon: float) -> float:
    row, col = ds.index(lon, lat)
    if not (0 <= row < ds.height and 0 <= col < ds.width):
        raise ValueError(f"({lat}, {lon}) is outside the raster extent")
    value = float(ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
    if ds.nodata is not None and value == ds.nodata:
        raise ValueError(f"no elevation data at ({lat}, {lon})")
    return value


def elevation_m(lat: float, lon: float, dted_source: str | Path) -> float:
    """Elevation in meters at (lat, lon) from a single-band elevation raster."""
    with rasterio.open(dted_source) as ds:
        return _sample(ds, lat, lon)
