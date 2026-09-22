"""Shared fixtures. Rasters here are synthetic, generated in a temp
directory — never real DTED or chart data (data/README.md)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

BASELINE_ELEVATION_M = 100.0
HILL_ELEVATION_M = 3000.0
DEM_RESOLUTION_DEG = 0.01
DEM_GRID_SIZE = 100  # 1deg x 1deg at 0.01deg resolution


def _write_synthetic_dem(path: Path) -> Path:
    """A 1x1 degree flat plain with a square hill in the middle."""
    lats = 1.0 - (np.arange(DEM_GRID_SIZE) + 0.5) * DEM_RESOLUTION_DEG
    lons = (np.arange(DEM_GRID_SIZE) + 0.5) * DEM_RESOLUTION_DEG
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    data = np.full((DEM_GRID_SIZE, DEM_GRID_SIZE), BASELINE_ELEVATION_M, dtype="float32")
    hill = (lat_grid >= 0.45) & (lat_grid <= 0.55) & (lon_grid >= 0.45) & (lon_grid <= 0.55)
    data[hill] = HILL_ELEVATION_M
    transform = from_origin(0.0, 1.0, DEM_RESOLUTION_DEG, DEM_RESOLUTION_DEG)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=DEM_GRID_SIZE,
        width=DEM_GRID_SIZE,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as ds:
        ds.write(data, 1)
    return path


@pytest.fixture
def dem(tmp_path: Path) -> Path:
    return _write_synthetic_dem(tmp_path / "dem.tif")
