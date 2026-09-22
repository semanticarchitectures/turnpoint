import asyncio
from pathlib import Path

import pytest

from turnpoint.mcp_server import server


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {
        "range_bearing",
        "destination_point",
        "compute_route_legs",
        "create_plan",
        "get_plan",
        "list_plans",
        "get_elevation",
        "check_terrain_clearance",
    } <= names


def test_every_response_names_its_models():
    out = server.range_bearing(0, 0, 0, 1)
    assert out["meta"]["datum"] == "WGS84"
    assert "Not for operational use" in out["meta"]["notice"]


def test_compute_route_legs():
    out = server.compute_route_legs(
        [{"name": "A", "lat": 0, "lon": 0}, {"name": "B", "lat": 0, "lon": 1}], 120
    )
    assert len(out["legs"]) == 1
    assert out["total_ete_min"] > 0


def _turnpoints() -> list[dict]:
    return [
        {"name": "A", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000.0},
        {"name": "B", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000.0},
    ]


def test_create_and_get_plan():
    created = server.create_plan("test plan", _turnpoints(), actor="test-agent")
    plan_id = created["plan"]["id"]
    fetched = server.get_plan(plan_id)
    assert fetched["plan"]["name"] == "test plan"
    assert len(fetched["legs"]) == 1


def test_list_plans_includes_created_plan():
    created = server.create_plan("listed plan", _turnpoints(), actor="test-agent")
    plans = server.list_plans()["plans"]
    assert created["plan"]["id"] in {p["id"] for p in plans}


def test_get_elevation_names_data_source(dem: Path):
    out = server.get_elevation(0.05, 0.05, str(dem))
    assert out["elevation_m"] == pytest.approx(100.0)
    assert out["meta"]["dted_source"] == str(dem)


def test_check_terrain_clearance_flags_violation(dem: Path):
    low = [
        {"name": "A", "lat": 0.5, "lon": 0.05, "altitude_ft": 1500.0},
        {"name": "B", "lat": 0.5, "lon": 0.95, "altitude_ft": 1500.0},
    ]
    created = server.create_plan("low plan", low, actor="test-agent")
    out = server.check_terrain_clearance(
        created["plan"]["id"], clearance_margin_ft=500.0, dted_source=str(dem)
    )
    assert out["clear"] is False
    assert out["violations"]
    assert out["meta"]["dted_source"] == str(dem)


def test_check_terrain_clearance_clear_route(dem: Path):
    created = server.create_plan("high plan", _turnpoints(), actor="test-agent")
    out = server.check_terrain_clearance(
        created["plan"]["id"], clearance_margin_ft=500.0, dted_source=str(dem)
    )
    assert out["clear"] is True
    assert out["violations"] == []
