"""Overlay model: arbitrary imported geometry, distinct from a route Plan.

See docs/specs/plan-model.md ("v2 additions") and decision 0010.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GeometryType = Literal["point", "line", "polygon"]

_MIN_COORDS: dict[GeometryType, int] = {"point": 1, "line": 2, "polygon": 3}


@dataclass(frozen=True)
class OverlayFeature:
    geometry_type: GeometryType
    coordinates: list[tuple[float, float]]  # (lat, lon) pairs, WGS84
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        minimum = _MIN_COORDS[self.geometry_type]
        if len(self.coordinates) < minimum:
            raise ValueError(
                f"{self.geometry_type} needs at least {minimum} coordinate(s), "
                f"got {len(self.coordinates)}"
            )


@dataclass(frozen=True)
class Overlay:
    id: str
    name: str
    source_format: str
    source_path: str
    features: list[OverlayFeature]
    actor: str
    created_at: str
