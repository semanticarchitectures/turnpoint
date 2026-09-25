from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from turnpoint.core import Turnpoint
from turnpoint.store import OverlayStore, PlanStore, ThreatStore
from turnpoint.store.db import connect


class FakeClock:
    def __init__(self) -> None:
        self._t = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._t += timedelta(seconds=1)
        return self._t


def _store() -> ThreatStore:
    return ThreatStore(clock=FakeClock())


def test_create_and_get_threat():
    store = _store()
    threat = store.create_threat("test threat", "NOTIONAL-SAM-A", 38.0, -77.0, 20.0, actor="tester")
    assert threat.name == "test threat"
    assert threat.threat_type == "NOTIONAL-SAM-A"
    assert threat.engagement_radius_nm == 20.0
    assert threat.sensor_height_ft == 0.0  # default
    assert threat.sidc is None
    assert store.get_threat(threat.id) == threat


def test_create_threat_with_optional_fields():
    store = _store()
    threat = store.create_threat(
        "t",
        "NOTIONAL-SAM-B",
        38.0,
        -77.0,
        15.0,
        sensor_height_ft=50.0,
        sidc="10061000001211000000",
        actor="u",
    )
    assert threat.sensor_height_ft == 50.0
    assert threat.sidc == "10061000001211000000"


def test_create_threat_requires_actor():
    store = _store()
    with pytest.raises(TypeError):
        store.create_threat("t", "NOTIONAL-SAM-A", 38.0, -77.0, 20.0)  # type: ignore[call-arg]


def test_create_threat_rejects_empty_actor():
    store = _store()
    with pytest.raises(ValueError):
        store.create_threat("t", "NOTIONAL-SAM-A", 38.0, -77.0, 20.0, actor="")


def test_create_threat_rejects_non_positive_radius():
    store = _store()
    with pytest.raises(ValueError):
        store.create_threat("t", "NOTIONAL-SAM-A", 38.0, -77.0, 0.0, actor="u")


def test_get_missing_threat_raises():
    store = _store()
    with pytest.raises(KeyError):
        store.get_threat("does-not-exist")


def test_list_threats():
    store = _store()
    store.create_threat("t1", "NOTIONAL-SAM-A", 38.0, -77.0, 20.0, actor="u")
    store.create_threat("t2", "NOTIONAL-AAA-A", 39.0, -76.0, 5.0, actor="u")
    assert {t.name for t in store.list_threats()} == {"t1", "t2"}


def test_existing_plan_and_overlay_database_migrates_cleanly(tmp_path: Path):
    """A store opened by PlanStore/OverlayStore alone (schema v1/v2) must
    gain the threats table (schema v3) transparently when ThreatStore
    later opens the same file -- all three share one schema (store/db.py)."""
    db_path = tmp_path / "store.sqlite3"
    plan_store = PlanStore(db_path)
    plan_store.create_plan(
        "p", [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1)], actor="u", tool_call="create_plan"
    )
    plan_store.close()

    overlay_store = OverlayStore(db_path)
    overlay_store.create_overlay(
        "o", [], source_format="geojson", source_path="a.geojson", actor="u"
    )
    overlay_store.close()

    threat_store = ThreatStore(db_path)
    threat = threat_store.create_threat("t", "NOTIONAL-SAM-A", 38.0, -77.0, 20.0, actor="u")
    threat_store.close()

    conn = connect(db_path)
    plans = conn.execute("SELECT COUNT(*) AS n FROM plans").fetchone()["n"]
    overlays = conn.execute("SELECT COUNT(*) AS n FROM overlays").fetchone()["n"]
    threats = conn.execute("SELECT COUNT(*) AS n FROM threats").fetchone()["n"]
    conn.close()
    assert plans == 1
    assert overlays == 1
    assert threats == 1
    assert threat.name == "t"
