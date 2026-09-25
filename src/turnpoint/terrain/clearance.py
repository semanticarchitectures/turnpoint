"""Terrain clearance checking for a route (docs/specs/plan-model.md).

Samples elevation along each leg's geodesic and compares it against the
planned altitude (interpolated linearly between the leg's two turnpoints,
see "Altitude along a leg" in the plan-model spec) minus a caller-supplied
clearance margin. ``clearance_margin_ft`` is always supplied by the
caller, never a hardcoded "real" obstacle-clearance constant — Turnpoint
is not for operational use.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import rasterio
from rasterio.io import DatasetReader

from turnpoint.core.route import Route, Turnpoint
from turnpoint.terrain._sampling import DEFAULT_SAMPLE_INTERVAL_NM, sample_path
from turnpoint.terrain.dted import METERS_PER_FT, _sample


@dataclass(frozen=True)
class ClearanceSample:
    lat: float
    lon: float
    distance_along_leg_nm: float
    terrain_elevation_ft: float
    planned_altitude_ft: float
    clearance_ft: float
    clear: bool


@dataclass(frozen=True)
class LegClearance:
    from_name: str
    to_name: str
    samples: list[ClearanceSample]

    @property
    def min_clearance_ft(self) -> float:
        return min(s.clearance_ft for s in self.samples)

    @property
    def clear(self) -> bool:
        return all(s.clear for s in self.samples)


@dataclass(frozen=True)
class ClearanceReport:
    legs: list[LegClearance]
    clearance_margin_ft: float
    dted_source: str

    @property
    def clear(self) -> bool:
        return all(leg.clear for leg in self.legs)

    @property
    def violations(self) -> list[ClearanceSample]:
        return [s for leg in self.legs for s in leg.samples if not s.clear]


def _leg_samples(
    from_tp: Turnpoint, to_tp: Turnpoint, sample_interval_nm: float
) -> list[tuple[float, float, float, float]]:
    """(lat, lon, distance_along_leg_nm, interpolated planned altitude_ft)."""
    if from_tp.altitude_ft is None or to_tp.altitude_ft is None:
        raise ValueError(
            "terrain clearance requires altitude_ft on every turnpoint; "
            f"missing on leg {from_tp.name} -> {to_tp.name}"
        )
    return sample_path(
        from_tp.lat,
        from_tp.lon,
        from_tp.altitude_ft,
        to_tp.lat,
        to_tp.lon,
        to_tp.altitude_ft,
        sample_interval_nm,
    )


def _sample_clearance(
    ds: DatasetReader, lat: float, lon: float, altitude_ft: float, dist_nm: float, margin_ft: float
) -> ClearanceSample:
    terrain_ft = _sample(ds, lat, lon) / METERS_PER_FT
    clearance_ft = altitude_ft - terrain_ft
    return ClearanceSample(
        lat=lat,
        lon=lon,
        distance_along_leg_nm=dist_nm,
        terrain_elevation_ft=terrain_ft,
        planned_altitude_ft=altitude_ft,
        clearance_ft=clearance_ft,
        clear=clearance_ft >= margin_ft,
    )


def terrain_clear(
    route: Route,
    *,
    clearance_margin_ft: float,
    dted_source: str | Path,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> ClearanceReport:
    """Check whether ``route`` clears terrain by at least ``clearance_margin_ft``.

    Every turnpoint in ``route`` must carry ``altitude_ft``; altitude is
    interpolated linearly along each leg by distance.
    """
    if len(route.turnpoints) < 2:
        raise ValueError("a route needs at least two turnpoints")
    if sample_interval_nm <= 0:
        raise ValueError("sample_interval_nm must be positive")
    legs: list[LegClearance] = []
    with rasterio.open(dted_source) as ds:
        for a, b in zip(route.turnpoints, route.turnpoints[1:], strict=False):
            samples = [
                _sample_clearance(ds, lat, lon, altitude_ft, dist_nm, clearance_margin_ft)
                for lat, lon, dist_nm, altitude_ft in _leg_samples(a, b, sample_interval_nm)
            ]
            legs.append(LegClearance(a.name, b.name, samples))
    return ClearanceReport(
        legs=legs, clearance_margin_ft=clearance_margin_ft, dted_source=str(dted_source)
    )
