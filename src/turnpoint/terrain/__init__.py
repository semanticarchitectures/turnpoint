"""Elevation queries and terrain clearance (Phase 1). Profile, line-of-sight
and masking are Phase 3 (docs/PLAN.md)."""

from turnpoint.terrain.clearance import (
    ClearanceReport,
    ClearanceSample,
    LegClearance,
    terrain_clear,
)
from turnpoint.terrain.dted import elevation_m

__all__ = [
    "ClearanceReport",
    "ClearanceSample",
    "LegClearance",
    "elevation_m",
    "terrain_clear",
]
