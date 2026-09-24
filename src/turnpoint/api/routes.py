"""REST API routes (docs/specs/route-schema.md).

The viewer talks only to this API, never directly to the store, terrain
or tiles modules (decision 0003).
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from turnpoint.core import fidelity_report_dict, meta
from turnpoint.core.route import Turnpoint
from turnpoint.formats import import_geojson, import_gpx
from turnpoint.store import open_default_overlay_store, open_default_store
from turnpoint.terrain import DEFAULT_SAMPLE_INTERVAL_NM, elevation_m, terrain_clear
from turnpoint.tiles import open_source

router = APIRouter()
_store = open_default_store()
_overlay_store = open_default_overlay_store()

_IMPORTERS = {"geojson": import_geojson, "gpx": import_gpx}

# Tile sources are resolved under this directory only (data/README.md:
# public, local data). TURNPOINT_DATA_DIR overrides it, mainly for tests.
DATA_DIR = Path(os.environ.get("TURNPOINT_DATA_DIR", "data")).resolve()


class TurnpointIn(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    altitude_ft: float | None = None


class PlanCreate(BaseModel):
    name: str
    turnpoints: list[TurnpointIn] = Field(min_length=2)
    actor: str


class OverlayImport(BaseModel):
    format: str
    path: str
    name: str
    actor: str


def _plan_response(plan_id: str) -> dict[str, Any]:
    try:
        plan = _store.get_plan(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    legs = _store.to_route(plan_id).legs()
    return {"plan": asdict(plan), "legs": [leg.__dict__ for leg in legs], "meta": meta()}


def _resolve_data_path(name: str) -> Path:
    """Resolve a filename under DATA_DIR only -- used by both tile sources
    and overlay imports, since both accept a filename from a client."""
    candidate = (DATA_DIR / name).resolve()
    if not candidate.is_relative_to(DATA_DIR):
        raise HTTPException(status_code=400, detail="invalid path")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"no such file: {name}")
    return candidate


@router.post("/plans", status_code=201)
def create_plan(body: PlanCreate) -> dict[str, Any]:
    turnpoints = [Turnpoint(tp.name, tp.lat, tp.lon, tp.altitude_ft) for tp in body.turnpoints]
    try:
        plan = _store.create_plan(body.name, turnpoints, actor=body.actor, tool_call="create_plan")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_response(plan.id)


@router.get("/plans")
def list_plans() -> dict[str, Any]:
    return {"plans": [asdict(p) for p in _store.list_plans()], "meta": meta()}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str) -> dict[str, Any]:
    return _plan_response(plan_id)


@router.get("/plans/{plan_id}/clearance")
def get_clearance(
    plan_id: str,
    clearance_margin_ft: float,
    dted_source: str,
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM,
) -> dict[str, Any]:
    try:
        route = _store.to_route(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        report = terrain_clear(
            route,
            clearance_margin_ft=clearance_margin_ft,
            dted_source=dted_source,
            sample_interval_nm=sample_interval_nm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@router.get("/terrain/elevation")
def get_elevation(lat: float, lon: float, dted_source: str) -> dict[str, Any]:
    try:
        value_m = elevation_m(lat, lon, dted_source)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "elevation_m": value_m,
        "elevation_ft": value_m / 0.3048,
        "meta": meta(dted_source=dted_source),
    }


@router.get("/tiles/{source}/{z}/{x}/{y}.png")
def get_tile(source: str, z: int, x: int, y: int) -> Response:
    path = _resolve_data_path(source)
    try:
        png = open_source(path).tile(z, x, y)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


def _overlay_response(overlay_id: str) -> dict[str, Any]:
    try:
        overlay = _overlay_store.get_overlay(overlay_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"overlay": asdict(overlay), "meta": meta()}


@router.post("/overlays/import", status_code=201)
def import_overlay(body: OverlayImport) -> dict[str, Any]:
    importer = _IMPORTERS.get(body.format)
    if importer is None:
        raise HTTPException(status_code=400, detail=f"unsupported format: {body.format}")
    path = _resolve_data_path(body.path)
    try:
        features, fidelity_report = importer(path)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    overlay = _overlay_store.create_overlay(
        body.name, features, source_format=body.format, source_path=str(path), actor=body.actor
    )
    return {
        "overlay": asdict(overlay),
        "fidelity_report": fidelity_report_dict(fidelity_report),
        "meta": meta(),
    }


@router.get("/overlays")
def list_overlays() -> dict[str, Any]:
    return {"overlays": [asdict(o) for o in _overlay_store.list_overlays()], "meta": meta()}


@router.get("/overlays/{overlay_id}")
def get_overlay(overlay_id: str) -> dict[str, Any]:
    return _overlay_response(overlay_id)
