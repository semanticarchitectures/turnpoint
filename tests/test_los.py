"""Tests use the synthetic DEM fixture from conftest.py (a flat plain
with a square hill), never real DTED files."""

from __future__ import annotations

from pathlib import Path

import pytest

from turnpoint.core.route import Route, Turnpoint
from turnpoint.terrain import line_of_sight, terrain_profile

# Must match conftest.py's synthetic DEM fixture.
BASELINE_M = 100.0
HILL_M = 3000.0
HILL_FT = HILL_M / 0.3048  # ~9843


def test_low_los_blocked_by_hill(dem: Path):
    # Both ends at 1000 ft, well under the ~9843 ft hill between them.
    result = line_of_sight(0.5, 0.05, 1000.0, 0.5, 0.95, 1000.0, dem, sample_interval_nm=2.0)
    assert not result.visible
    obstruction = result.first_obstruction
    assert obstruction is not None
    assert obstruction.terrain_elevation_ft == pytest.approx(HILL_FT)


def test_high_los_clears_hill(dem: Path):
    result = line_of_sight(0.5, 0.05, 15000.0, 0.5, 0.95, 15000.0, dem, sample_interval_nm=2.0)
    assert result.visible
    assert result.first_obstruction is None


def test_los_reports_data_source(dem: Path):
    result = line_of_sight(0.5, 0.05, 15000.0, 0.5, 0.95, 15000.0, dem)
    assert result.dted_source == str(dem)


def test_los_rejects_bad_sample_interval(dem: Path):
    with pytest.raises(ValueError):
        line_of_sight(0.5, 0.05, 1000.0, 0.5, 0.95, 1000.0, dem, sample_interval_nm=0)


def test_los_same_point_is_trivially_visible(dem: Path):
    result = line_of_sight(0.5, 0.5, 15000.0, 0.5, 0.5, 15000.0, dem)
    assert result.visible
    assert len(result.samples) == 1


def _crossing_route(altitude_ft: float) -> Route:
    return Route(
        "over-the-hill",
        [
            Turnpoint("A", 0.5, 0.05, altitude_ft=altitude_ft),
            Turnpoint("B", 0.5, 0.95, altitude_ft=altitude_ft),
        ],
    )


def test_profile_samples_baseline_and_hill(dem: Path):
    report = terrain_profile(_crossing_route(15000.0), dem, sample_interval_nm=2.0)
    assert len(report.legs) == 1
    elevations = [s.terrain_elevation_ft for s in report.legs[0].samples]
    assert min(elevations) == pytest.approx(BASELINE_M / 0.3048)
    assert max(elevations) == pytest.approx(HILL_FT)


def test_profile_reports_planned_altitude_per_sample(dem: Path):
    report = terrain_profile(_crossing_route(15000.0), dem, sample_interval_nm=2.0)
    assert all(s.planned_altitude_ft == pytest.approx(15000.0) for s in report.legs[0].samples)


def test_profile_requires_altitude(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05), Turnpoint("B", 0.5, 0.95)])
    with pytest.raises(ValueError):
        terrain_profile(route, dem)


def test_profile_requires_two_turnpoints(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05, altitude_ft=1000.0)])
    with pytest.raises(ValueError):
        terrain_profile(route, dem)


def test_profile_reports_data_source(dem: Path):
    report = terrain_profile(_crossing_route(15000.0), dem)
    assert report.dted_source == str(dem)
