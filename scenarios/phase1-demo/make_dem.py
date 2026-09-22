#!/usr/bin/env python3
"""Generate the synthetic elevation raster for the Phase 1 demo.

Writes a small, notional GeoTIFF -- a flat plain with a square hill --
to data/phase1-demo-dem.tif (git-ignored; data/README.md's public-data-
only rule). Not real DTED or terrain of any real place. Run once before
following scenarios/phase1-demo/README.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

BASELINE_ELEVATION_M = 100.0
HILL_ELEVATION_M = 3000.0
RESOLUTION_DEG = 0.01
GRID_SIZE = 100  # 1deg x 1deg at 0.01deg resolution

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "phase1-demo-dem.tif"


def main() -> None:
    lats = 1.0 - (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lons = (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    data = np.full((GRID_SIZE, GRID_SIZE), BASELINE_ELEVATION_M, dtype="float32")
    hill = (lat_grid >= 0.45) & (lat_grid <= 0.55) & (lon_grid >= 0.45) & (lon_grid <= 0.55)
    data[hill] = HILL_ELEVATION_M

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(0.0, 1.0, RESOLUTION_DEG, RESOLUTION_DEG)
    with rasterio.open(
        OUTPUT_PATH,
        "w",
        driver="GTiff",
        height=GRID_SIZE,
        width=GRID_SIZE,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=-9999.0,
    ) as ds:
        ds.write(data, 1)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
