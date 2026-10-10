"""Airports, navaids and class airspace from public FAA data
(docs/specs/aero-data.md). Class airspace boundaries are imported and
queryable; route scoring against them (altitude-aware intersection) is
not built yet -- see decision 0017."""

from turnpoint.aero.class_airspace import list_class_airspace_near, parse_class_airspace
from turnpoint.aero.models import Airport, Airspace, Navaid
from turnpoint.aero.nasr import (
    get_airport,
    get_navaid,
    list_airports_near,
    parse_airports,
    parse_navaids,
)

__all__ = [
    "Airport",
    "Airspace",
    "Navaid",
    "get_airport",
    "get_navaid",
    "list_airports_near",
    "list_class_airspace_near",
    "parse_airports",
    "parse_class_airspace",
    "parse_navaids",
]
