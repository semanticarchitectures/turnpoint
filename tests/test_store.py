from datetime import UTC, datetime, timedelta

import pytest

from turnpoint.core import Turnpoint
from turnpoint.store import PlanStore


class FakeClock:
    """Deterministic, monotonically increasing clock for tests."""

    def __init__(self) -> None:
        self._t = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        self._t += timedelta(seconds=1)
        return self._t


def _store() -> PlanStore:
    return PlanStore(clock=FakeClock())


def _turnpoints() -> list[Turnpoint]:
    return [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1, altitude_ft=5500.0)]


def test_create_and_get_plan():
    store = _store()
    plan = store.create_plan("test", _turnpoints(), actor="test-user", tool_call="create_plan")
    assert plan.name == "test"
    assert [tp.name for tp in plan.turnpoints] == ["A", "B"]
    assert plan.turnpoints[1].altitude_ft == 5500.0
    assert store.get_plan(plan.id) == plan


def test_create_plan_requires_two_turnpoints():
    store = _store()
    with pytest.raises(ValueError):
        store.create_plan("t", [Turnpoint("A", 0, 0)], actor="u", tool_call="create_plan")


def test_create_plan_requires_actor_and_tool_call():
    store = _store()
    with pytest.raises(TypeError):
        store.create_plan("t", _turnpoints(), tool_call="create_plan")  # type: ignore[call-arg]


def test_mutation_records_provenance_event():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="agent-1", tool_call="create_plan")
    events = store.events(plan.id)
    assert len(events) == 1
    assert events[0].actor == "agent-1"
    assert events[0].tool_call == "create_plan"
    assert events[0].parent_event_id is None


def test_events_chain_via_parent_id():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="agent-1", tool_call="create_plan")
    store.add_turnpoint(plan.id, Turnpoint("C", 0, 2), actor="agent-1", tool_call="add_turnpoint")
    events = store.events(plan.id)
    assert len(events) == 2
    assert events[1].parent_event_id == events[0].id


def test_add_turnpoint_appends():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="u", tool_call="create_plan")
    updated = store.add_turnpoint(
        plan.id, Turnpoint("C", 0, 2), actor="u", tool_call="add_turnpoint"
    )
    assert [tp.name for tp in updated.turnpoints] == ["A", "B", "C"]


def test_update_turnpoint():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="u", tool_call="create_plan")
    updated = store.update_turnpoint(
        plan.id, 0, Turnpoint("A2", 1, 1), actor="u", tool_call="update_turnpoint"
    )
    assert updated.turnpoints[0].name == "A2"


def test_update_turnpoint_bad_seq_raises():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="u", tool_call="create_plan")
    with pytest.raises(KeyError):
        store.update_turnpoint(
            plan.id, 99, Turnpoint("X", 0, 0), actor="u", tool_call="update_turnpoint"
        )


def test_delete_turnpoint_resequences():
    store = _store()
    plan = store.create_plan(
        "t",
        [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1), Turnpoint("C", 0, 2)],
        actor="u",
        tool_call="create_plan",
    )
    updated = store.delete_turnpoint(plan.id, 1, actor="u", tool_call="delete_turnpoint")
    assert [tp.name for tp in updated.turnpoints] == ["A", "C"]


def test_delete_turnpoint_refuses_below_minimum():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="u", tool_call="create_plan")
    with pytest.raises(ValueError):
        store.delete_turnpoint(plan.id, 0, actor="u", tool_call="delete_turnpoint")
    assert len(store.get_plan(plan.id).turnpoints) == 2


def test_to_route_reuses_leg_math():
    store = _store()
    plan = store.create_plan(
        "t", [Turnpoint("A", 0, 0), Turnpoint("B", 0, 1)], actor="u", tool_call="create_plan"
    )
    legs = store.to_route(plan.id).legs()
    assert legs[0].from_name == "A"
    assert legs[0].distance_nm > 0


def test_list_plans():
    store = _store()
    store.create_plan("t1", _turnpoints(), actor="u", tool_call="create_plan")
    store.create_plan("t2", _turnpoints(), actor="u", tool_call="create_plan")
    assert {p.name for p in store.list_plans()} == {"t1", "t2"}


def test_get_missing_plan_raises():
    store = _store()
    with pytest.raises(KeyError):
        store.get_plan("does-not-exist")


def test_deterministic_timestamps_from_injected_clock():
    store = _store()
    plan = store.create_plan("t", _turnpoints(), actor="u", tool_call="create_plan")
    assert plan.created_at == plan.updated_at
