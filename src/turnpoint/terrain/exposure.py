"""Threat exposure: where along a route a notional threat's sensor can
see the aircraft (docs/PLAN.md Phase 3).

A route point is "exposed" to a threat when it is both within the
threat's ``engagement_radius_nm`` and not masked by terrain -- the same
line-of-sight check as ``turnpoint.terrain.los``, applied between the
threat's sensor and each route point instead of between two arbitrary
points. The threat's sensor sits at ground elevation under
``threat.lat``/``threat.lon`` plus ``threat.sensor_height_ft`` (an AGL
offset -- see ``line_of_sight``'s docstring), never a real system's
actual mounting height.

This answers exposure for one route against one threat; a scenario with
several threats calls it once per threat and combines the results.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import rasterio
from rasterio.io import DatasetReader

from turnpoint.core.route import Route
from turnpoint.core.threat import Threat
from turnpoint.geodesy import range_bearing
from turnpoint.terrain._sampling import DEFAULT_SAMPLE_INTERVAL_NM, sample_path
from turnpoint.terrain.dted import METERS_PER_FT, _sample


@dataclass(frozen=True)
class ExposureSample:
    lat: float
    lon: float
    distance_along_leg_nm: float
    altitude_ft: float
    range_from_threat_nm: float
    in_range: bool
    """True if within the threat's engagement_radius_nm."""
    masked: bool
    """True if terrain blocks line-of-sight between the threat's sensor and this point."""
    exposed: bool
    """in_range and not masked -- the threat's sensor can see this point."""


@dataclass(frozen=True)
class LegExposure:
    from_name: str
    to_name: str
    samples: list[ExposureSample]

    @property
    def exposed(self) -> bool:
        return any(s.exposed for s in self.samples)


@dataclass(frozen=True)
class ExposureReport:
    threat_id: str
    legs: list[LegExposure]
    dted_source: str

    @property
    def exposed(self) -> bool:
        return any(leg.exposed for leg in self.legs)

    @property
    def exposed_samples(self) -> list[ExposureSample]:
        return [s for leg in self.legs for s in leg.samples if s.exposed]


def _line_clear(
    ds: DatasetReader,
    lat1: float,
    lon1: float,
    height1_ft: float,
    lat2: float,
    lon2: float,
    height2_ft: float,
    sample_interval_nm: float,
) -> bool:
    """True if no terrain sample along the straight line rises above it."""
    return all(
        _sample(ds, lat, lon) / METERS_PER_FT <= los_height_ft
        for lat, lon, _, los_height_ft in sample_path(
            lat1, lon1, height1_ft, lat2, lon2, height2_ft, sample_interval_nm
        )
    )


def route_exposure(
    route: Route,
    threat: Threat,
    dted_source: str | Path,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> ExposureReport:
    """Where along ``route`` ``threat``'s sensor can see the aircraft.

    Every turnpoint must carry ``altitude_ft`` (absolute MSL, same
    requirement as ``terrain_clear``). A sample is exposed when it falls
    within ``threat.engagement_radius_nm`` of the threat's position AND
    terrain does not mask the straight line between the threat's sensor
    height and the sample's planned altitude.
    """
    if len(route.turnpoints) < 2:
        raise ValueError("a route needs at least two turnpoints")
    if sample_interval_nm <= 0:
        raise ValueError("sample_interval_nm must be positive")
    legs: list[LegExposure] = []
    with rasterio.open(dted_source) as ds:
        threat_ground_ft = _sample(ds, threat.lat, threat.lon) / METERS_PER_FT
        threat_height_ft = threat_ground_ft + threat.sensor_height_ft
        for a, b in zip(route.turnpoints, route.turnpoints[1:], strict=False):
            if a.altitude_ft is None or b.altitude_ft is None:
                raise ValueError(
                    "threat exposure requires altitude_ft on every turnpoint; "
                    f"missing on leg {a.name} -> {b.name}"
                )
            samples: list[ExposureSample] = []
            for lat, lon, dist_nm, altitude_ft in sample_path(
                a.lat, a.lon, a.altitude_ft, b.lat, b.lon, b.altitude_ft, sample_interval_nm
            ):
                range_nm = range_bearing(threat.lat, threat.lon, lat, lon).distance_nm
                in_range = range_nm <= threat.engagement_radius_nm
                masked = not _line_clear(
                    ds,
                    threat.lat,
                    threat.lon,
                    threat_height_ft,
                    lat,
                    lon,
                    altitude_ft,
                    sample_interval_nm,
                )
                samples.append(
                    ExposureSample(
                        lat=lat,
                        lon=lon,
                        distance_along_leg_nm=dist_nm,
                        altitude_ft=altitude_ft,
                        range_from_threat_nm=range_nm,
                        in_range=in_range,
                        masked=masked,
                        exposed=in_range and not masked,
                    )
                )
            legs.append(LegExposure(a.name, b.name, samples))
    return ExposureReport(threat_id=threat.id, legs=legs, dted_source=str(dted_source))
