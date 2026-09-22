import asyncio

from turnpoint.mcp_server import server


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {"range_bearing", "destination_point", "compute_route_legs"} <= names


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
