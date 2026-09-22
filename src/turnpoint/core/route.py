"""Route model: an ordered list of turnpoints and the legs between them.

See docs/specs/plan-model.md for the full model, including the persisted
``Plan`` wrapper and provenance events (src/turnpoint/store). Timing, fuel
and constraints beyond altitude remain out of scope until a concrete
consumer needs them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from turnpoint.geodesy import METERS_PER_NM, range_bearing


@dataclass(frozen=True)
class Turnpoint:
    name: str
    lat: float
    lon: float
    altitude_ft: float | None = None


@dataclass(frozen=True)
class Leg:
    from_name: str
    to_name: str
    distance_nm: float
    true_course_deg: float
    ete_min: float | None  # None when no groundspeed is given


@dataclass
class Route:
    name: str
    turnpoints: list[Turnpoint] = field(default_factory=list)

    def legs(self, groundspeed_kt: float | None = None) -> list[Leg]:
        """Leg distance, initial true course and, given a groundspeed, time en route."""
        if groundspeed_kt is not None and groundspeed_kt <= 0:
            raise ValueError("groundspeed must be positive")
        out: list[Leg] = []
        for a, b in zip(self.turnpoints, self.turnpoints[1:], strict=False):
            g = range_bearing(a.lat, a.lon, b.lat, b.lon)
            nm = g.distance_m / METERS_PER_NM
            ete = None if groundspeed_kt is None else nm / groundspeed_kt * 60.0
            out.append(Leg(a.name, b.name, nm, g.initial_bearing_deg, ete))
        return out

    def total_distance_nm(self) -> float:
        return sum(leg.distance_nm for leg in self.legs())
