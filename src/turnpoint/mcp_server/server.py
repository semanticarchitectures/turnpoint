"""Turnpoint MCP server.

Every tool response carries a ``meta`` block naming the datum, models and data set
versions used, so that agent plans can be replayed and audited (AGENTS.md, section 6).
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from turnpoint import NOT_FOR_OPERATIONAL_USE, __version__
from turnpoint.core import Route, Turnpoint
from turnpoint.geodesy import DATUM, METERS_PER_NM
from turnpoint.geodesy import destination_point as _destination_point
from turnpoint.geodesy import range_bearing as _range_bearing

mcp = MCPServer("turnpoint", instructions=NOT_FOR_OPERATIONAL_USE, version=__version__)


def _meta() -> dict[str, Any]:
    return {
        "turnpoint_version": __version__,
        "datum": DATUM,
        "geodesic_model": "GeographicLib (Karney 2013)",
        "bearings": "degrees true",
        "notice": NOT_FOR_OPERATIONAL_USE,
    }


@mcp.tool()
def range_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> dict[str, Any]:
    """Geodesic distance and true bearings between two points in decimal degrees."""
    g = _range_bearing(lat1, lon1, lat2, lon2)
    return {
        "distance_m": g.distance_m,
        "distance_nm": g.distance_nm,
        "initial_bearing_deg": g.initial_bearing_deg,
        "final_bearing_deg": g.final_bearing_deg,
        "meta": _meta(),
    }


@mcp.tool()
def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_nm: float
) -> dict[str, Any]:
    """Point reached from a start point along a true bearing for a distance in NM."""
    lat2, lon2 = _destination_point(lat, lon, bearing_deg, distance_nm * METERS_PER_NM)
    return {"lat": lat2, "lon": lon2, "meta": _meta()}


@mcp.tool()
def compute_route_legs(
    turnpoints: list[dict[str, Any]], groundspeed_kt: float | None = None
) -> dict[str, Any]:
    """Leg distances, true courses and times for an ordered list of turnpoints.

    Each turnpoint is ``{"name": str, "lat": float, "lon": float,
    "altitude_ft": float | None}``; ``altitude_ft`` is optional.
    """
    if len(turnpoints) < 2:
        raise ValueError("a route needs at least two turnpoints")
    route = Route(
        "adhoc",
        [
            Turnpoint(
                str(t["name"]),
                float(t["lat"]),
                float(t["lon"]),
                None if t.get("altitude_ft") is None else float(t["altitude_ft"]),
            )
            for t in turnpoints
        ],
    )
    legs = route.legs(groundspeed_kt)
    return {
        "legs": [leg.__dict__ for leg in legs],
        "total_distance_nm": sum(leg.distance_nm for leg in legs),
        "total_ete_min": (
            None if groundspeed_kt is None else sum(leg.ete_min or 0.0 for leg in legs)
        ),
        "meta": _meta(),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
