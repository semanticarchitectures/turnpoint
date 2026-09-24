from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from turnpoint.core import OverlayFeature, Turnpoint
from turnpoint.store import OverlayStore, PlanStore
from turnpoint.store.db import connect


class FakeClock:
    def __init__(self) -> None:
        self._t = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._t += timedelta(seconds=1)
        return self._t


def _store() -> OverlayStore:
    return OverlayStore(clock=FakeClock())


def _features() -> list[OverlayFeature]:
    return [
        OverlayFeature("point", [(0.0, 0.0)], {"name": "A"}),
        OverlayFeature("line", [(0.0, 0.0), (0.0, 1.0)]),
    ]


def test_create_and_get_overlay():
    store = _store()
    overlay = store.create_overlay(
        "test overlay",
        _features(),
        source_format="geojson",
        source_path="test.geojson",
        actor="tester",
    )
    assert overlay.name == "test overlay"
    assert len(overlay.features) == 2
    assert overlay.features[0].properties["name"] == "A"
    assert store.get_overlay(overlay.id) == overlay


def test_create_overlay_requires_actor():
    store = _store()
    with pytest.raises(TypeError):
        store.create_overlay(  # type: ignore[call-arg]
            "t", _features(), source_format="geojson", source_path="t.geojson"
        )


def test_create_overlay_rejects_empty_actor():
    store = _store()
    with pytest.raises(ValueError):
        store.create_overlay(
            "t", _features(), source_format="geojson", source_path="t.geojson", actor=""
        )


def test_get_missing_overlay_raises():
    store = _store()
    with pytest.raises(KeyError):
        store.get_overlay("does-not-exist")


def test_list_overlays():
    store = _store()
    store.create_overlay(
        "o1", _features(), source_format="geojson", source_path="a.geojson", actor="u"
    )
    store.create_overlay("o2", _features(), source_format="gpx", source_path="b.gpx", actor="u")
    assert {o.name for o in store.list_overlays()} == {"o1", "o2"}


def test_polygon_roundtrips_through_json():
    store = _store()
    polygon = OverlayFeature(
        "polygon", [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 0.0)], {"fill": "red"}
    )
    overlay = store.create_overlay(
        "poly", [polygon], source_format="kml", source_path="a.kml", actor="u"
    )
    fetched = store.get_overlay(overlay.id)
    assert fetched.features[0].geometry_type == "polygon"
    assert fetched.features[0].coordinates == polygon.coordinates
    assert fetched.features[0].properties == {"fill": "red"}


def test_existing_plan_only_database_migrates_cleanly(tmp_path: Path):
    """A store opened by PlanStore alone (schema v1) must gain the
    overlays table (schema v2) transparently when OverlayStore later
    opens the same file -- both stores share one schema (store/db.py)."""
    db_path = tmp_path / "store.sqlite3"
    plan_store = PlanStore(db_path)
    plan_store.create_plan(
        "p",
        [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1)],
        actor="u",
        tool_call="create_plan",
    )
    plan_store.close()

    overlay_store = OverlayStore(db_path)
    overlay = overlay_store.create_overlay(
        "o", _features(), source_format="geojson", source_path="a.geojson", actor="u"
    )
    overlay_store.close()

    conn = connect(db_path)
    plans = conn.execute("SELECT COUNT(*) AS n FROM plans").fetchone()["n"]
    overlays = conn.execute("SELECT COUNT(*) AS n FROM overlays").fetchone()["n"]
    conn.close()
    assert plans == 1
    assert overlays == 1
    assert overlay.name == "o"
