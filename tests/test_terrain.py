"""Terrain tests use the synthetic DEM fixture from conftest.py, never
real DTED files, per the roadmap's clean-data intent (docs/decisions/0009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from turnpoint.core.route import Route, Turnpoint
from turnpoint.terrain import elevation_m, terrain_clear

# Must match conftest.py's synthetic DEM fixture.
BASELINE_M = 100.0
HILL_M = 3000.0


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
