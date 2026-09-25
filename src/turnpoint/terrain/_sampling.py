"""Shared path sampling: interpolate lat/lon/height between two points
at a fixed interval. Used by clearance.py, los.py and exposure.py so
this logic exists in exactly one place, not duplicated per module.
"""

from __future__ import annotations

import math

from turnpoint.geodesy import METERS_PER_NM, destination_point, range_bearing

DEFAULT_SAMPLE_INTERVAL_NM = 1.0


def sample_path(
    lat1: float,
    lon1: float,
    height1_ft: float,
    lat2: float,
    lon2: float,
    height2_ft: float,
    sample_interval_nm: float,
) -> list[tuple[float, float, float, float]]:
    """(lat, lon, distance_along_path_nm, interpolated height_ft) samples
    between two points; height is interpolated linearly by distance."""
    g = range_bearing(lat1, lon1, lat2, lon2)
    path_nm = g.distance_nm
    n_samples = 1 if path_nm == 0 else max(2, math.ceil(path_nm / sample_interval_nm) + 1)
    samples: list[tuple[float, float, float, float]] = []
    for i in range(n_samples):
        frac = i / (n_samples - 1) if n_samples > 1 else 0.0
        dist_nm = frac * path_nm
        if i == 0:
            lat, lon = lat1, lon1
        elif i == n_samples - 1:
            lat, lon = lat2, lon2
        else:
            lat, lon = destination_point(lat1, lon1, g.initial_bearing_deg, dist_nm * METERS_PER_NM)
        height_ft = height1_ft + frac * (height2_ft - height1_ft)
        samples.append((lat, lon, dist_nm, height_ft))
    return samples
