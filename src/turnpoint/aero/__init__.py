"""Airports and navaids from public FAA NASR data (docs/specs/aero-data.md).
Airspace (class B/C/D/etc, SUA) is deferred -- see decision 0010's research
notes and docs/PLAN.md Phase 3."""

from turnpoint.aero.models import Airport, Navaid
from turnpoint.aero.nasr import (
    get_airport,
    get_navaid,
    list_airports_near,
    parse_airports,
    parse_navaids,
)

__all__ = [
    "Airport",
    "Navaid",
    "get_airport",
    "get_navaid",
    "list_airports_near",
    "parse_airports",
    "parse_navaids",
]
