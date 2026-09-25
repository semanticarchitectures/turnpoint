"""Line-of-sight ("masking") and raw terrain profile queries.

Line-of-sight samples the straight path between two points and checks
whether terrain rises above the line connecting them at any sample.
Both heights are caller-supplied MSL values -- never a default asserting
a real sensor or platform height (AGENTS.md section 2). Profile is the
same sampling with no pass/fail framing, for an agent that just wants
the terrain shape under a route.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import rasterio

from turnpoint.core.route import Route
from turnpoint.terrain._sampling import DEFAULT_SAMPLE_INTERVAL_NM, sample_path
from turnpoint.terrain.dted import METERS_PER_FT, _sample


@dataclass(frozen=True)
class LineOfSightSample:
    lat: float
    lon: float
    distance_nm: float
    terrain_elevation_ft: float
    los_height_ft: float
    """Height of the straight line between the two endpoints at this point."""
    clear: bool
    """True if terrain is below the line-of-sight height here."""


@dataclass(frozen=True)
class LineOfSightResult:
    samples: list[LineOfSightSample]
    dted_source: str

    @property
    def visible(self) -> bool:
        return all(s.clear for s in self.samples)

    @property
    def first_obstruction(self) -> LineOfSightSample | None:
        return next((s for s in self.samples if not s.clear), None)


def line_of_sight(
    lat1: float,
    lon1: float,
    height1_ft: float,
    lat2: float,
    lon2: float,
    height2_ft: float,
    dted_source: str | Path,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> LineOfSightResult:
    """Whether a straight line between two MSL-height points clears terrain.

    ``height1_ft``/``height2_ft`` are absolute MSL heights supplied by the
    caller -- for a threat, that's typically ground elevation plus a
    notional sensor height (``Threat.sensor_height_ft``); for a route
    point, its planned altitude.
    """
    if sample_interval_nm <= 0:
        raise ValueError("sample_interval_nm must be positive")
    samples: list[LineOfSightSample] = []
    with rasterio.open(dted_source) as ds:
        for lat, lon, dist_nm, los_height_ft in sample_path(
            lat1, lon1, height1_ft, lat2, lon2, height2_ft, sample_interval_nm
        ):
            terrain_ft = _sample(ds, lat, lon) / METERS_PER_FT
            samples.append(
                LineOfSightSample(
                    lat=lat,
                    lon=lon,
                    distance_nm=dist_nm,
                    terrain_elevation_ft=terrain_ft,
                    los_height_ft=los_height_ft,
                    clear=terrain_ft <= los_height_ft,
                )
            )
    return LineOfSightResult(samples=samples, dted_source=str(dted_source))


@dataclass(frozen=True)
class ProfileSample:
    lat: float
    lon: float
    distance_along_leg_nm: float
    terrain_elevation_ft: float
    planned_altitude_ft: float


@dataclass(frozen=True)
class LegProfile:
    from_name: str
    to_name: str
    samples: list[ProfileSample]


@dataclass(frozen=True)
class ProfileReport:
    legs: list[LegProfile]
    dted_source: str


def terrain_profile(
    route: Route,
    dted_source: str | Path,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> ProfileReport:
    """Raw elevation samples along each leg of a route -- no clearance
    margin, no pass/fail, just the terrain shape under the planned track.
    Every turnpoint must carry ``altitude_ft``, same as ``terrain_clear``.
    """
    if len(route.turnpoints) < 2:
        raise ValueError("a route needs at least two turnpoints")
    if sample_interval_nm <= 0:
        raise ValueError("sample_interval_nm must be positive")
    legs: list[LegProfile] = []
    with rasterio.open(dted_source) as ds:
        for a, b in zip(route.turnpoints, route.turnpoints[1:], strict=False):
            if a.altitude_ft is None or b.altitude_ft is None:
                raise ValueError(
                    "terrain profile requires altitude_ft on every turnpoint; "
                    f"missing on leg {a.name} -> {b.name}"
                )
            samples = [
                ProfileSample(
                    lat=lat,
                    lon=lon,
                    distance_along_leg_nm=dist_nm,
                    terrain_elevation_ft=_sample(ds, lat, lon) / METERS_PER_FT,
                    planned_altitude_ft=altitude_ft,
                )
                for lat, lon, dist_nm, altitude_ft in sample_path(
                    a.lat, a.lon, a.altitude_ft, b.lat, b.lon, b.altitude_ft, sample_interval_nm
                )
            ]
            legs.append(LegProfile(a.name, b.name, samples))
    return ProfileReport(legs=legs, dted_source=str(dted_source))
