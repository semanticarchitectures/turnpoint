"""Tests use the synthetic DEM fixture from conftest.py (a flat plain
with a square hill), never real DTED files."""

from __future__ import annotations

from pathlib import Path

import pytest

from turnpoint.core.route import Route, Turnpoint
from turnpoint.core.threat import Threat
from turnpoint.terrain import route_exposure


def _threat(engagement_radius_nm: float, *, lat: float = 0.5, lon: float = 0.05) -> Threat:
    return Threat(
        id="t1",
        name="test threat",
        threat_type="NOTIONAL-SAM-A",
        lat=lat,
        lon=lon,
        engagement_radius_nm=engagement_radius_nm,
        sensor_height_ft=0.0,
        sidc=None,
        actor="test-agent",
        created_at="2026-09-26T00:00:00+00:00",
    )


def _crossing_route(altitude_ft: float) -> Route:
    return Route(
        "over-the-hill",
        [
            Turnpoint("A", 0.5, 0.05, altitude_ft=altitude_ft),
            Turnpoint("B", 0.5, 0.95, altitude_ft=altitude_ft),
        ],
    )


def test_low_route_far_side_of_hill_is_masked(dem: Path):
    # Threat sits at A's end of the route (0.5, 0.05); at 1000 ft, its
    # line-of-sight to anything past the hill (which spans lon 0.45-0.55)
    # is blocked, even though the near side (before the hill) is visible.
    report = route_exposure(_crossing_route(1000.0), _threat(100.0), dem, sample_interval_nm=2.0)
    far_side = [s for leg in report.legs for s in leg.samples if s.distance_along_leg_nm > 30.0]
    assert far_side
    assert all(s.in_range and s.masked and not s.exposed for s in far_side)


def test_high_route_over_hill_is_exposed(dem: Path):
    report = route_exposure(_crossing_route(15000.0), _threat(100.0), dem, sample_interval_nm=2.0)
    assert report.exposed is True
    assert report.exposed_samples
    assert all(s.in_range and not s.masked for s in report.exposed_samples)


def test_out_of_range_point_never_exposed_even_when_visible(dem: Path):
    threat = _threat(5.0, lat=0.1, lon=0.1)
    report = route_exposure(_crossing_route(15000.0), threat, dem, sample_interval_nm=2.0)
    assert report.exposed is False
    assert all(not s.in_range for leg in report.legs for s in leg.samples)


def test_reports_threat_id_and_data_source(dem: Path):
    report = route_exposure(_crossing_route(15000.0), _threat(100.0), dem)
    assert report.threat_id == "t1"
    assert report.dted_source == str(dem)


def test_requires_altitude(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05), Turnpoint("B", 0.5, 0.95)])
    with pytest.raises(ValueError):
        route_exposure(route, _threat(100.0), dem)


def test_requires_two_turnpoints(dem: Path):
    route = Route("t", [Turnpoint("A", 0.5, 0.05, altitude_ft=1000.0)])
    with pytest.raises(ValueError):
        route_exposure(route, _threat(100.0), dem)


def test_rejects_bad_sample_interval(dem: Path):
    with pytest.raises(ValueError):
        route_exposure(_crossing_route(15000.0), _threat(100.0), dem, sample_interval_nm=0)
