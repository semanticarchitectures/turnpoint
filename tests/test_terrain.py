"""Terrain tests use small synthetic GeoTIFF fixtures, never real DTED
files, per the roadmap's clean-data intent (docs/decisions/0009)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from turnpoint.core.route import Route, Turnpoint
from turnpoint.terrain import elevation_m, terrain_clear

BASELINE_M = 100.0
HILL_M = 3000.0
RESOLUTION_DEG = 0.01
GRID_SIZE = 100  # 1deg x 1deg at 0.01deg resolution


def _synthetic_dem(path: Path) -> Path:
    """A 1x1 degree flat plain with a square hill in the middle."""
    lats = 1.0 - (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lons = (np.arange(GRID_SIZE) + 0.5) * RESOLUTION_DEG
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    data = np.full((GRID_SIZE, GRID_SIZE), BASELINE_M, dtype="float32")
    hill = (lat_grid >= 0.45) & (lat_grid <= 0.55) & (lon_grid >= 0.45) & (lon_grid <= 0.55)
    data[hill] = HILL_M
    transform = from_origin(0.0, 1.0, RESOLUTION_DEG, RESOLUTION_DEG)
    with rasterio.open(
        path,
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
    return path


@pytest.fixture
def dem(tmp_path: Path) -> Path:
    return _synthetic_dem(tmp_path / "dem.tif")


def test_elevation_on_flat_ground(dem: Path):
    assert elevation_m(0.05, 0.05, dem) == pytest.approx(BASELINE_M)


def test_elevation_on_hill(dem: Path):
    assert elevation_m(0.5, 0.5, dem) == pytest.approx(HILL_M)


def test_elevation_outside_extent_raises(dem: Path):
    with pytest.raises(ValueError):
        elevation_m(5.0, 5.0, dem)


def _crossing_route(altitude_ft: float) -> Route:
    # A due-east leg at lat 0.5 that passes straight through the hill.
    return Route(
        "over-the-hill",
        [
            Turnpoint("A", 0.5, 0.05, altitude_ft=altitude_ft),
            Turnpoint("B", 0.5, 0.95, altitude_ft=altitude_ft),
        ],
    )


def test_low_route_is_not_clear(dem: Path):
    # 1500 ft clears the 100 m baseline (~328 ft) by 500 ft margin, but
    # not the 3000 m hill (~9843 ft) in the middle of the leg.
    report = terrain_clear(
        _crossing_route(1500.0),
        clearance_margin_ft=500.0,
        dted_source=dem,
        sample_interval_nm=2.0,
    )
    assert not report.clear
    assert report.violations
    assert all(v.terrain_elevation_ft == pytest.approx(HILL_M / 0.3048) for v in report.violations)


def test_high_route_is_clear(dem: Path):
    # 15000 ft ~ 4572 m clears the 3000 m hill with margin to spare.
    report = terrain_clear(
        _crossing_route(15000.0),
        clearance_margin_ft=500.0,
        dted_source=dem,
        sample_interval_nm=2.0,
    )
    assert report.clear
    assert report.violations == []


def test_terrain_clear_reports_data_source(dem: Path):
    report = terrain_clear(_crossing_route(15000.0), clearance_margin_ft=500.0, dted_source=dem)
    assert report.dted_source == str(dem)
    assert report.clearance_margin_ft == 500.0


def test_terrain_clear_requires_altitude(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05), Turnpoint("B", 0.5, 0.95)])
    with pytest.raises(ValueError):
        terrain_clear(route, clearance_margin_ft=500.0, dted_source=dem)


def test_terrain_clear_requires_two_turnpoints(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05, altitude_ft=1000.0)])
    with pytest.raises(ValueError):
        terrain_clear(route, clearance_margin_ft=500.0, dted_source=dem)
