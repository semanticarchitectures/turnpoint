import asyncio
from pathlib import Path

import pytest

from turnpoint.mcp_server import server
from turnpoint.store import OverlayStore, PlanStore

FIXTURES = Path(__file__).parent / "fixtures" / "geojson"
GPX_FIXTURES = Path(__file__).parent / "fixtures" / "gpx"
KML_FIXTURES = Path(__file__).parent / "fixtures" / "kml"
NASR_FIXTURES = Path(__file__).parent / "fixtures" / "nasr"
NASR_CYCLE = "2026-08-06"


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    """Each test gets its own in-memory store, never the shared on-disk
    default (turnpoint.store.open_default_store) the server module-level
    _store normally points at."""
    monkeypatch.setattr(server, "_store", PlanStore())
    monkeypatch.setattr(server, "_overlay_store", OverlayStore())


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
        "import_overlay",
        "get_overlay",
        "list_overlays",
        "list_airports_near",
        "get_airport",
        "get_navaid",
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


def test_import_overlay_and_get_and_list():
    imported = server.import_overlay(
        "geojson", str(FIXTURES / "sample.geojson"), "test overlay", actor="test-agent"
    )
    assert imported["fidelity_report"]["fully_faithful"] is True
    overlay_id = imported["overlay"]["id"]

    fetched = server.get_overlay(overlay_id)
    assert fetched["overlay"]["name"] == "test overlay"

    listed = server.list_overlays()["overlays"]
    assert overlay_id in {o["id"] for o in listed}


def test_import_gpx_overlay():
    imported = server.import_overlay(
        "gpx", str(GPX_FIXTURES / "sample.gpx"), "test gpx overlay", actor="test-agent"
    )
    assert imported["fidelity_report"]["fully_faithful"] is True
    assert imported["fidelity_report"]["imported_count"] == 3
    assert imported["overlay"]["source_format"] == "gpx"


def test_import_kml_overlay():
    imported = server.import_overlay(
        "kml", str(KML_FIXTURES / "sample.kml"), "test kml overlay", actor="test-agent"
    )
    assert imported["fidelity_report"]["fully_faithful"] is True
    assert imported["fidelity_report"]["imported_count"] == 3
    assert imported["overlay"]["source_format"] == "kml"


def test_import_overlay_unsupported_format_raises():
    with pytest.raises(ValueError):
        server.import_overlay("nope", "x.nope", "t", actor="test-agent")


def test_list_airports_near_names_nasr_cycle():
    out = server.list_airports_near(
        38.85, -77.03, 50.0, str(NASR_FIXTURES / "apt_base_sample.csv"), NASR_CYCLE
    )
    assert {a["ident"] for a in out["airports"]} == {"TP01", "TP02"}
    assert out["meta"]["nasr_cycle"] == NASR_CYCLE


def test_get_airport():
    out = server.get_airport("TP01", str(NASR_FIXTURES / "apt_base_sample.csv"), NASR_CYCLE)
    assert out["airport"]["name"] == "TURNPOINT TEST FIELD ONE"


def test_get_airport_missing_raises():
    with pytest.raises(KeyError):
        server.get_airport("NOPE", str(NASR_FIXTURES / "apt_base_sample.csv"), NASR_CYCLE)


def test_get_navaid():
    out = server.get_navaid("TPV", str(NASR_FIXTURES / "nav_base_sample.csv"), NASR_CYCLE)
    assert out["navaid"]["nav_type"] == "VOR"


class _FakeAccessParser:
    """No real .mdb fixture is possible -- no permissively-licensed
    Python library can write one (docs/specs/fv-drawing-import.md)."""

    def __init__(self, path: str) -> None:
        self.catalog = {"Main": 1}

    def parse_table(self, name: str) -> dict[str, list]:
        return {
            "FEATURE_NUM": [1],
            "TYPE": ["LINE"],
            "DATA": ["DATA_TYPE_MOVETO=N38.000000W77.000000;DATA_TYPE_LINETO=N39.000000W76.000000"],
        }


def test_import_fv_drawing_overlay(monkeypatch):
    monkeypatch.setattr("access_parser.AccessParser", _FakeAccessParser)
    imported = server.import_overlay(
        "fv-drawing", "fake.mdb", "test fv drawing overlay", actor="test-agent"
    )
    assert imported["overlay"]["source_format"] == "fv-drawing"
    assert imported["fidelity_report"]["imported_count"] == 1
