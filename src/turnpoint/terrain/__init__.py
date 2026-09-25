"""Elevation queries, terrain clearance, line-of-sight and terrain profile.
Full viewshed/raster masking products are out of scope -- "masking" here
means line-of-sight between two named points (docs/PLAN.md Phase 3)."""

from turnpoint.terrain._sampling import DEFAULT_SAMPLE_INTERVAL_NM
from turnpoint.terrain.clearance import (
    ClearanceReport,
    ClearanceSample,
    LegClearance,
    terrain_clear,
)
from turnpoint.terrain.dted import METERS_PER_FT, elevation_m
from turnpoint.terrain.los import (
    LegProfile,
    LineOfSightResult,
    LineOfSightSample,
    ProfileReport,
    ProfileSample,
    line_of_sight,
    terrain_profile,
)

__all__ = [
    "DEFAULT_SAMPLE_INTERVAL_NM",
    "METERS_PER_FT",
    "ClearanceReport",
    "ClearanceSample",
    "LegClearance",
    "LegProfile",
    "LineOfSightResult",
    "LineOfSightSample",
    "ProfileReport",
    "ProfileSample",
    "elevation_m",
    "line_of_sight",
    "terrain_clear",
    "terrain_profile",
]
