"""Elevation queries and terrain clearance (Phase 1). Profile, line-of-sight
and masking are Phase 3 (docs/PLAN.md)."""

from turnpoint.terrain.clearance import (
    DEFAULT_SAMPLE_INTERVAL_NM,
    ClearanceReport,
    ClearanceSample,
    LegClearance,
    terrain_clear,
)
from turnpoint.terrain.dted import METERS_PER_FT, elevation_m

__all__ = [
    "DEFAULT_SAMPLE_INTERVAL_NM",
    "METERS_PER_FT",
    "ClearanceReport",
    "ClearanceSample",
    "LegClearance",
    "elevation_m",
    "terrain_clear",
]
