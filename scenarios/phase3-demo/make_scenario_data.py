#!/usr/bin/env python3
"""Generate the DEM and scenario file for the Phase 3 demo.

Writes a synthetic elevation raster (the same flat-plain-with-a-hill
shape as scenarios/phase1-demo/make_dem.py) and a scenario JSON
(docs/specs/scenario-format.md) to data/phase3-demo/ (git-ignored;
data/README.md's public-data-only rule). Not real DTED, or a real
threat, or a real place. Run once before following
scenarios/phase3-demo/README.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

BASELINE_ELEVATION_M = 100.0
HILL_ELEVATION_M = 3000.0
RESOLUTION_DEG = 0.01
GRID_SIZE = 100  # 1deg x 1deg at 0.01deg resolution

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "phase3-demo"
DEM_PATH = OUTPUT_DIR / "dem.tif"
SCENARIO_PATH = OUTPUT_DIR / "scenario.json"

# Referenced from the scenario file as a path relative to the repo root
# (dted_source is used exactly as every other Turnpoint dted_source
# argument -- opened directly, never sandboxed under DATA_DIR; decision
# 0013). Demos are meant to be run from the repo root.
DTED_SOURCE_FOR_SCENARIO = "data/phase3-demo/dem.tif"

SCENARIO = {
    "name": "Phase 3 demo: ALPHA to BRAVO past a notional SAM",
    "description": (
        "Fly from notional airfield ALPHA to BRAVO. There is a terrain "
        "feature between the two fields and a notional SAM near the "
        "direct track. Clear the terrain by 500 ft and reach BRAVO "
        "within 15 minutes at 300 kt."
    ),
    "dted_source": DTED_SOURCE_FOR_SCENARIO,
    "objective": {
        "start": {"name": "ALPHA", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000.0},
        "end": {"name": "BRAVO", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000.0},
        "clearance_margin_ft": 500.0,
        "groundspeed_kt": 300.0,
        "target_ete_min": 11.0,
        "max_ete_min": 15.0,
    },
    "threats": [
        {
            "name": "SAM-1",
            "threat_type": "NOTIONAL-SAM-A",
            "lat": 0.5,
            "lon": 0.35,
            "engagement_radius_nm": 10.0,
            "sensor_height_ft": 0.0,
            "sidc": "10061000001211000000",
        }
    ],
}


def main() -> None:
    lats = 1.0 - (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lons = (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    data = np.full((GRID_SIZE, GRID_SIZE), BASELINE_ELEVATION_M, dtype="float32")
    hill = (lat_grid >= 0.45) & (lat_grid <= 0.55) & (lon_grid >= 0.45) & (lon_grid <= 0.55)
    data[hill] = HILL_ELEVATION_M

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    transform = from_origin(0.0, 1.0, RESOLUTION_DEG, RESOLUTION_DEG)
    with rasterio.open(
        DEM_PATH,
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
    print(f"Wrote {DEM_PATH}")

    SCENARIO_PATH.write_text(json.dumps(SCENARIO, indent=2) + "\n")
    print(f"Wrote {SCENARIO_PATH}")


if __name__ == "__main__":
    main()
