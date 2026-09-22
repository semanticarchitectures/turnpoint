"""Geodesic range, bearing and destination point on WGS 84.

Computation is delegated to GeographicLib (SOURCES S-005, Karney 2013), which is
accurate to nanometres and, unlike Vincenty's method, converges for near-antipodal
points. All bearings are true, in degrees clockwise from north, in [0, 360).
"""

from __future__ import annotations

from dataclasses import dataclass

from geographiclib.geodesic import Geodesic

DATUM = "WGS84"
# International nautical mile, exact by definition (1929 International
# Extraordinary Hydrographic Conference).
METERS_PER_NM = 1852.0

_WGS84 = Geodesic.WGS84


@dataclass(frozen=True)
class GeodesicLeg:
    """Result of the geodesic inverse problem between two points."""

    distance_m: float
    initial_bearing_deg: float
    final_bearing_deg: float
    datum: str = DATUM

    @property
    def distance_nm(self) -> float:
        return self.distance_m / METERS_PER_NM


def _check(lat: float, lon: float) -> None:
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude {lat} outside [-90, 90]")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude {lon} outside [-180, 180]")


def _norm360(deg: float) -> float:
    return deg % 360.0


def range_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> GeodesicLeg:
    """Distance and true bearings from point 1 to point 2 (decimal degrees)."""
    _check(lat1, lon1)
    _check(lat2, lon2)
    g = _WGS84.Inverse(lat1, lon1, lat2, lon2)
    return GeodesicLeg(
        distance_m=g["s12"],
        initial_bearing_deg=_norm360(g["azi1"]),
        final_bearing_deg=_norm360(g["azi2"]),
    )


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Point reached from (lat, lon) along a true bearing for a distance in metres."""
    _check(lat, lon)
    if distance_m < 0:
        raise ValueError("distance must be non-negative")
    g = _WGS84.Direct(lat, lon, bearing_deg, distance_m)
    return g["lat2"], g["lon2"]
