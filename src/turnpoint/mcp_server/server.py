"""Turnpoint MCP server.

Every tool response carries a ``meta`` block naming the datum, models and data set
versions used, so that agent plans can be replayed and audited (AGENTS.md, section 6).
"""

from __future__ import annotations

import base64
from dataclasses import asdict
from typing import Any

from mcp.server.mcpserver import MCPServer

from turnpoint import NOT_FOR_OPERATIONAL_USE, __version__
from turnpoint.aero import get_airport as _get_airport
from turnpoint.aero import get_navaid as _get_navaid
from turnpoint.aero import list_airports_near as _list_airports_near
from turnpoint.core import Route, Turnpoint, fidelity_report_dict, meta
from turnpoint.formats import get_importer as _get_importer
from turnpoint.formats import list_importers as _list_importers
from turnpoint.geodesy import METERS_PER_NM
from turnpoint.geodesy import destination_point as _destination_point
from turnpoint.geodesy import range_bearing as _range_bearing
from turnpoint.products import build_route_card as _build_route_card
from turnpoint.scenario import load_scenario as _load_scenario
from turnpoint.scenario import score_route as _score_route
from turnpoint.store import (
    open_default_overlay_store,
    open_default_store,
    open_default_threat_store,
)
from turnpoint.terrain import DEFAULT_SAMPLE_INTERVAL_NM, METERS_PER_FT
from turnpoint.terrain import elevation_m as _elevation_m
from turnpoint.terrain import line_of_sight as _line_of_sight
from turnpoint.terrain import route_exposure as _route_exposure
from turnpoint.terrain import terrain_clear as _terrain_clear
from turnpoint.terrain import terrain_profile as _terrain_profile

mcp = MCPServer("turnpoint", instructions=NOT_FOR_OPERATIONAL_USE, version=__version__)

# Shared with the API (src/turnpoint/api) so a plan/overlay/threat created
# via one is visible via the other — see turnpoint.store.open_default_store.
_store = open_default_store()
_overlay_store = open_default_overlay_store()
_threat_store = open_default_threat_store()


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
def create_route_card(plan_id: str, groundspeed_kt: float | None = None) -> dict[str, Any]:
    """A one-page printable PDF (base64-encoded) summarizing a persisted
    plan's turnpoints and legs -- distance, true course and, with
    groundspeed_kt, ETE per leg (docs/PLAN.md Phase 4, "print products").
    Deterministic: the same plan and groundspeed always produce the same
    PDF bytes (AGENTS.md section 6). A table of turnpoints and legs, not
    a plotted chart image.
    """
    plan = _store.get_plan(plan_id)
    legs = _store.to_route(plan_id).legs(groundspeed_kt)
    pdf_bytes = _build_route_card(plan, legs)
    return {"pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"), "meta": meta()}


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
def line_of_sight(
    lat1: float,
    lon1: float,
    height1_ft: float,
    lat2: float,
    lon2: float,
    height2_ft: float,
    dted_source: str,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> dict[str, Any]:
    """Whether a straight line between two MSL-height points clears terrain
    ("masking", docs/PLAN.md Phase 3). Heights are absolute MSL, always
    caller-supplied — never a default real sensor/platform height.
    """
    result = _line_of_sight(
        lat1, lon1, height1_ft, lat2, lon2, height2_ft, dted_source, sample_interval_nm
    )
    return {
        "visible": result.visible,
        "first_obstruction": (
            asdict(result.first_obstruction) if result.first_obstruction else None
        ),
        "samples": [asdict(s) for s in result.samples],
        "meta": meta(dted_source=result.dted_source),
    }


@mcp.tool()
def terrain_profile(
    plan_id: str, dted_source: str, sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM
) -> dict[str, Any]:
    """Raw elevation samples along a persisted plan's route — terrain shape
    under the planned track, no clearance-margin pass/fail framing.
    """
    route = _store.to_route(plan_id)
    report = _terrain_profile(route, dted_source, sample_interval_nm)
    return {
        "legs": [
            {
                "from_name": leg.from_name,
                "to_name": leg.to_name,
                "samples": [asdict(s) for s in leg.samples],
            }
            for leg in report.legs
        ],
        "meta": meta(dted_source=report.dted_source),
    }


@mcp.tool()
def import_overlay(format: str, path: str, name: str, actor: str) -> dict[str, Any]:
    """Import a file as an Overlay (docs/specs/plan-model.md "v2 additions").

    ``format`` is one of ``list_import_formats()``'s names -- the four
    built-in ones (geojson, gpx, kml, fv-drawing) plus any installed
    plug-in (docs/specs/plugin-api.md, decision 0014). Returns the
    persisted overlay and a fidelity report naming anything the importer
    could not fully interpret — never silent data loss (AGENTS.md
    section 4). fv-drawing is a best-effort importer built from partial
    public documentation (docs/specs/fv-drawing-import.md, decision
    0012) — expect a low-fidelity result on a real file.
    """
    try:
        importer = _get_importer(format)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
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
def list_import_formats() -> dict[str, Any]:
    """Every format name ``import_overlay`` accepts -- built-in and any
    installed plug-in alike, indistinguishable in this list by design
    (docs/specs/plugin-api.md, decision 0014)."""
    return {"formats": _list_importers(), "meta": meta()}


@mcp.tool()
def create_threat(
    name: str,
    threat_type: str,
    lat: float,
    lon: float,
    engagement_radius_nm: float,
    actor: str,
    sensor_height_ft: float = 0.0,
    sidc: str | None = None,
) -> dict[str, Any]:
    """Create and persist a notional threat (docs/PLAN.md Phase 3).

    Never a real threat system's actual parameters (AGENTS.md section 2)
    — ``threat_type`` should be a notional label like "NOTIONAL-SAM-A",
    and ``engagement_radius_nm`` a caller-chosen notional ring, not a real
    system's actual range. ``sidc`` is an optional MIL-STD-2525 Symbol
    Identification Code for the viewer to render (M23); Turnpoint does
    not validate or interpret it.
    """
    threat = _threat_store.create_threat(
        name,
        threat_type,
        lat,
        lon,
        engagement_radius_nm,
        sensor_height_ft=sensor_height_ft,
        sidc=sidc,
        actor=actor,
    )
    return {"threat": asdict(threat), "meta": meta()}


@mcp.tool()
def get_threat(threat_id: str) -> dict[str, Any]:
    """Fetch a persisted threat by id."""
    threat = _threat_store.get_threat(threat_id)
    return {"threat": asdict(threat), "meta": meta()}


@mcp.tool()
def list_threats() -> dict[str, Any]:
    """List every persisted threat."""
    return {"threats": [asdict(t) for t in _threat_store.list_threats()], "meta": meta()}


@mcp.tool()
def check_threat_exposure(
    plan_id: str,
    threat_id: str,
    dted_source: str,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> dict[str, Any]:
    """Where along a persisted plan a persisted threat's sensor can see the aircraft.

    A sample is exposed when it is within the threat's engagement_radius_nm
    AND terrain does not mask line-of-sight between the threat's sensor
    (ground elevation at the threat's position plus its notional
    sensor_height_ft) and the sample's planned altitude. Call once per
    threat for a scenario with several.
    """
    route = _store.to_route(plan_id)
    threat = _threat_store.get_threat(threat_id)
    report = _route_exposure(route, threat, dted_source, sample_interval_nm)
    return {
        "exposed": report.exposed,
        "threat_id": report.threat_id,
        "legs": [
            {"from_name": leg.from_name, "to_name": leg.to_name, "exposed": leg.exposed}
            for leg in report.legs
        ],
        "exposed_samples": [asdict(s) for s in report.exposed_samples],
        "meta": meta(dted_source=report.dted_source),
    }


@mcp.tool()
def score_plan(plan_id: str, scenario_path: str) -> dict[str, Any]:
    """Score a persisted plan against a scenario file (docs/specs/scenario-format.md).

    Checks terrain clearance, timing and threat exposure — never
    airspace, which has no data source yet (``airspace_checked`` is
    always false, decision 0013). A route whose start/end doesn't reach
    the scenario's objective scores 0, but every other field is still
    computed so the caller can see why.
    """
    route = _store.to_route(plan_id)
    scenario = _load_scenario(scenario_path)
    report = _score_route(route, scenario)
    return {
        "scenario_name": report.scenario_name,
        "score": report.score,
        "max_score": report.max_score,
        "reached_objective": report.reached_objective,
        "clear": report.clear,
        "clearance_violation_legs": report.clearance_violation_legs,
        "exposure": [asdict(e) for e in report.exposure],
        "ete_min": report.ete_min,
        "within_target_time": report.within_target_time,
        "within_max_time": report.within_max_time,
        "airspace_checked": report.airspace_checked,
        "meta": meta(dted_source=scenario.dted_source, scenario_path=scenario_path),
    }


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
