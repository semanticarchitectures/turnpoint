"""API tests use FastAPI's TestClient (dev-only httpx dependency) and
synthetic fixtures — never real chart or elevation data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

from turnpoint.api import routes
from turnpoint.api.app import app
from turnpoint.store import OverlayStore, PlanStore

FIXTURES = Path(__file__).parent / "fixtures" / "geojson"
GPX_FIXTURES = Path(__file__).parent / "fixtures" / "gpx"


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    monkeypatch.setattr(routes, "_store", PlanStore())
    monkeypatch.setattr(routes, "_overlay_store", OverlayStore())


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(routes, "DATA_DIR", tmp_path.resolve())
    return TestClient(app)


def _turnpoints() -> list[dict]:
    return [
        {"name": "A", "lat": 0.5, "lon": 0.05, "altitude_ft": 15000.0},
        {"name": "B", "lat": 0.5, "lon": 0.95, "altitude_ft": 15000.0},
    ]


def test_root(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "not for operational use" in resp.json()["notice"].lower()


def test_create_and_get_plan(client: TestClient):
    resp = client.post("/plans", json={"name": "t", "turnpoints": _turnpoints(), "actor": "u"})
    assert resp.status_code == 201
    plan_id = resp.json()["plan"]["id"]
    fetched = client.get(f"/plans/{plan_id}")
    assert fetched.status_code == 200
    assert fetched.json()["plan"]["name"] == "t"
    assert len(fetched.json()["legs"]) == 1


def test_create_plan_requires_two_turnpoints(client: TestClient):
    resp = client.post("/plans", json={"name": "t", "turnpoints": [_turnpoints()[0]], "actor": "u"})
    assert resp.status_code == 422


def test_get_missing_plan_404(client: TestClient):
    assert client.get("/plans/does-not-exist").status_code == 404


def test_list_plans(client: TestClient):
    client.post("/plans", json={"name": "t1", "turnpoints": _turnpoints(), "actor": "u"})
    resp = client.get("/plans")
    assert resp.status_code == 200
    assert any(p["name"] == "t1" for p in resp.json()["plans"])


def test_elevation(client: TestClient, dem: Path):
    resp = client.get(
        "/terrain/elevation", params={"lat": 0.05, "lon": 0.05, "dted_source": str(dem)}
    )
    assert resp.status_code == 200
    assert resp.json()["elevation_m"] == pytest.approx(100.0)


def test_clearance(client: TestClient, dem: Path):
    created = client.post(
        "/plans", json={"name": "t", "turnpoints": _turnpoints(), "actor": "u"}
    ).json()
    resp = client.get(
        f"/plans/{created['plan']['id']}/clearance",
        params={"clearance_margin_ft": 500.0, "dted_source": str(dem)},
    )
    assert resp.status_code == 200
    assert resp.json()["clear"] is True
    assert resp.json()["meta"]["dted_source"] == str(dem)


def _write_tile_fixture(path: Path) -> None:
    size = 64
    data = np.tile(np.linspace(0, 255, size, dtype="uint8"), (size, 1))
    transform = from_origin(0.0, 0.1, 0.1 / size, 0.1 / size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    ) as ds:
        ds.write(data, 1)


def test_tile(client: TestClient, tmp_path: Path):
    _write_tile_fixture(tmp_path / "basemap.tif")
    resp = client.get("/tiles/basemap.tif/0/0/0.png")
    assert resp.status_code == 200
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_tile_missing_source_404(client: TestClient):
    assert client.get("/tiles/nope.tif/0/0/0.png").status_code == 404


def test_resolve_data_path_rejects_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(routes, "DATA_DIR", tmp_path.resolve())
    with pytest.raises(HTTPException):
        routes._resolve_data_path("../outside.tif")


def test_import_geojson_overlay(client: TestClient, tmp_path: Path):
    (tmp_path / "sample.geojson").write_text((FIXTURES / "sample.geojson").read_text())
    resp = client.post(
        "/overlays/import",
        json={"format": "geojson", "path": "sample.geojson", "name": "test overlay", "actor": "u"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["overlay"]["name"] == "test overlay"
    assert body["fidelity_report"]["fully_faithful"] is True
    assert body["fidelity_report"]["imported_count"] == 3

    overlay_id = body["overlay"]["id"]
    fetched = client.get(f"/overlays/{overlay_id}")
    assert fetched.status_code == 200
    assert fetched.json()["overlay"]["id"] == overlay_id

    listed = client.get("/overlays").json()["overlays"]
    assert any(o["id"] == overlay_id for o in listed)


def test_import_gpx_overlay(client: TestClient, tmp_path: Path):
    (tmp_path / "sample.gpx").write_text((GPX_FIXTURES / "sample.gpx").read_text())
    resp = client.post(
        "/overlays/import",
        json={"format": "gpx", "path": "sample.gpx", "name": "gpx overlay", "actor": "u"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["overlay"]["source_format"] == "gpx"
    assert body["fidelity_report"]["imported_count"] == 3


def test_import_overlay_unsupported_format(client: TestClient):
    resp = client.post(
        "/overlays/import",
        json={"format": "nope", "path": "x.nope", "name": "t", "actor": "u"},
    )
    assert resp.status_code == 400


def test_import_overlay_missing_file_404(client: TestClient):
    resp = client.post(
        "/overlays/import",
        json={"format": "geojson", "path": "missing.geojson", "name": "t", "actor": "u"},
    )
    assert resp.status_code == 404


def test_get_missing_overlay_404(client: TestClient):
    assert client.get("/overlays/does-not-exist").status_code == 404
