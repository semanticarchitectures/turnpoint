"""Turnpoint MCP server.

Every tool response carries a ``meta`` block naming the datum, models and data set
versions used, so that agent plans can be replayed and audited (AGENTS.md, section 6).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mcp.server.mcpserver import MCPServer

from turnpoint import NOT_FOR_OPERATIONAL_USE, __version__
from turnpoint.aero import get_airport as _get_airport
from turnpoint.aero import get_navaid as _get_navaid
from turnpoint.aero import list_airports_near as _list_airports_near
from turnpoint.core import Route, Turnpoint, fidelity_report_dict, meta
from turnpoint.formats import import_geojson, import_gpx, import_kml
from turnpoint.geodesy import METERS_PER_NM
from turnpoint.geodesy import destination_point as _destination_point
from turnpoint.geodesy import range_bearing as _range_bearing
from turnpoint.store import open_default_overlay_store, open_default_store
from turnpoint.terrain import DEFAULT_SAMPLE_INTERVAL_NM, METERS_PER_FT
from turnpoint.terrain import elevation_m as _elevation_m
from turnpoint.terrain import terrain_clear as _terrain_clear

mcp = MCPServer("turnpoint", instructions=NOT_FOR_OPERATIONAL_USE, version=__version__)

# Shared with the API (src/turnpoint/api) so a plan/overlay created via one
# is visible via the other — see turnpoint.store.open_default_store.
_store = open_default_store()
_overlay_store = open_default_overlay_store()

_IMPORTERS = {"geojson": import_geojson, "gpx": import_gpx, "kml": import_kml}


def _turnpoints_from_dicts(turnpoints: list[dict[str, Any]]) -> list[Turnpoint]:
    """Parse ``{"name", "lat", "lon", "altitude_ft"}`` dicts into Turnpoints."""
    return [
        Turnpoint(
            str(t["name"]),
            float(t["lat"]),
            float(t["lon"]),
            None if t.get("altitude_ft") is None else float(t["altitude_ft"]),
        )
        for t in turnpoints
    ]


@mcp.tool()
def range_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> dict[str, Any]:
    """Geodesic distance and true bearings between two points in decimal degrees."""
    g = _range_bearing(lat1, lon1, lat2, lon2)
    return {
        "distance_m": g.distance_m,
        "distance_nm": g.distance_nm,
        "initial_bearing_deg": g.initial_bearing_deg,
        "final_bearing_deg": g.final_bearing_deg,
        "meta": meta(),
    }


@mcp.tool()
def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_nm: float
) -> dict[str, Any]:
    """Point reached from a start point along a true bearing for a distance in NM."""
    lat2, lon2 = _destination_point(lat, lon, bearing_deg, distance_nm * METERS_PER_NM)
    return {"lat": lat2, "lon": lon2, "meta": meta()}


@mcp.tool()
def compute_route_legs(
    turnpoints: list[dict[str, Any]], groundspeed_kt: float | None = None
) -> dict[str, Any]:
    """Leg distances, true courses and times for an ordered list of turnpoints.

    Each turnpoint is ``{"name": str, "lat": float, "lon": float,
    "altitude_ft": float | None}``; ``altitude_ft`` is optional. Stateless —
    does not persist a plan; use ``create_plan`` for that.
    """
    if len(turnpoints) < 2:
        raise ValueError("a route needs at least two turnpoints")
    route = Route("adhoc", _turnpoints_from_dicts(turnpoints))
    legs = route.legs(groundspeed_kt)
    return {
        "legs": [leg.__dict__ for leg in legs],
        "total_distance_nm": sum(leg.distance_nm for leg in legs),
        "total_ete_min": (
            None if groundspeed_kt is None else sum(leg.ete_min or 0.0 for leg in legs)
        ),
        "meta": meta(),
    }


@mcp.tool()
def create_plan(name: str, turnpoints: list[dict[str, Any]], actor: str) -> dict[str, Any]:
    """Create and persist a plan (docs/specs/plan-model.md).

    Each turnpoint is ``{"name": str, "lat": float, "lon": float,
    "altitude_ft": float | None}``. ``actor`` is required and recorded on
    the plan's provenance event — never inferred.
    """
    plan = _store.create_plan(
        name, _turnpoints_from_dicts(turnpoints), actor=actor, tool_call="create_plan"
    )
    return {"plan": asdict(plan), "meta": meta()}


@mcp.tool()
def get_plan(plan_id: str) -> dict[str, Any]:
    """Fetch a persisted plan by id, with its computed legs."""
    plan = _store.get_plan(plan_id)
    legs = _store.to_route(plan_id).legs()
    return {"plan": asdict(plan), "legs": [leg.__dict__ for leg in legs], "meta": meta()}


@mcp.tool()
def list_plans() -> dict[str, Any]:
    """List every persisted plan."""
    return {"plans": [asdict(p) for p in _store.list_plans()], "meta": meta()}


@mcp.tool()
def get_elevation(lat: float, lon: float, dted_source: str) -> dict[str, Any]:
    """Elevation at a point from a named elevation raster (DTED, GeoTIFF or COG)."""
    value_m = _elevation_m(lat, lon, dted_source)
    return {
        "elevation_m": value_m,
        "elevation_ft": value_m / METERS_PER_FT,
        "meta": meta(dted_source=dted_source),
    }


@mcp.tool()
def check_terrain_clearance(
    plan_id: str,
    clearance_margin_ft: float,
    dted_source: str,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> dict[str, Any]:
    """Check whether a persisted plan clears terrain by clearance_margin_ft.

    Every turnpoint on the plan must have ``altitude_ft`` set (see
    ``create_plan``). ``clearance_margin_ft`` is required — Turnpoint
    asserts no real-world minimum-obstacle-clearance value of its own.
    """
    route = _store.to_route(plan_id)
    report = _terrain_clear(
        route,
        clearance_margin_ft=clearance_margin_ft,
        dted_source=dted_source,
        sample_interval_nm=sample_interval_nm,
    )
    return {
        "clear": report.clear,
        "clearance_margin_ft": report.clearance_margin_ft,
        "legs": [
            {
                "from_name": leg.from_name,
                "to_name": leg.to_name,
                "min_clearance_ft": leg.min_clearance_ft,
                "clear": leg.clear,
            }
            for leg in report.legs
        ],
        "violations": [asdict(v) for v in report.violations],
        "meta": meta(dted_source=report.dted_source),
    }


@mcp.tool()
def import_overlay(format: str, path: str, name: str, actor: str) -> dict[str, Any]:
    """Import a file as an Overlay (docs/specs/plan-model.md "v2 additions").

    ``format`` is currently one of: geojson, gpx, kml. Returns the persisted overlay
    and a fidelity report naming anything the importer could not fully
    interpret — never silent data loss (AGENTS.md section 4).
    """
    importer = _IMPORTERS.get(format)
    if importer is None:
        raise ValueError(f"unsupported format: {format}")
    features, fidelity_report = importer(path)
    overlay = _overlay_store.create_overlay(
        name, features, source_format=format, source_path=path, actor=actor
    )
    return {
        "overlay": asdict(overlay),
        "fidelity_report": fidelity_report_dict(fidelity_report),
        "meta": meta(),
    }


@mcp.tool()
def get_overlay(overlay_id: str) -> dict[str, Any]:
    """Fetch a persisted overlay by id."""
    overlay = _overlay_store.get_overlay(overlay_id)
    return {"overlay": asdict(overlay), "meta": meta()}


@mcp.tool()
def list_overlays() -> dict[str, Any]:
    """List every persisted overlay."""
    return {"overlays": [asdict(o) for o in _overlay_store.list_overlays()], "meta": meta()}


@mcp.tool()
def list_airports_near(
    lat: float, lon: float, radius_nm: float, nasr_source: str, nasr_cycle: str
) -> dict[str, Any]:
    """Airports within radius_nm of (lat, lon), from a named NASR APT_BASE.csv
    extract. ``nasr_cycle`` (e.g. "2026-08-06") is required and named in
    every result -- never inferred, per decision 0011."""
    airports, fidelity_report = _list_airports_near(lat, lon, radius_nm, nasr_source, nasr_cycle)
    return {
        "airports": [asdict(a) for a in airports],
        "fidelity_report": fidelity_report_dict(fidelity_report),
        "meta": meta(nasr_source=nasr_source, nasr_cycle=nasr_cycle),
    }


@mcp.tool()
def get_airport(ident: str, nasr_source: str, nasr_cycle: str) -> dict[str, Any]:
    """Look up one airport by ARPT_ID or ICAO_ID in a named NASR extract."""
    airport = _get_airport(ident, nasr_source, nasr_cycle)
    return {
        "airport": asdict(airport),
        "meta": meta(nasr_source=nasr_source, nasr_cycle=nasr_cycle),
    }


@mcp.tool()
def get_navaid(ident: str, nasr_source: str, nasr_cycle: str) -> dict[str, Any]:
    """Look up one navaid by NAV_ID in a named NASR NAV_BASE.csv extract."""
    navaid = _get_navaid(ident, nasr_source, nasr_cycle)
    return {"navaid": asdict(navaid), "meta": meta(nasr_source=nasr_source, nasr_cycle=nasr_cycle)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
