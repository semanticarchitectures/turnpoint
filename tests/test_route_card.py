"""Tests for the route card PDF (docs/PLAN.md Phase 4, "print products")."""

from __future__ import annotations

import pytest

from turnpoint.core.route import Leg, Turnpoint
from turnpoint.products import build_route_card
from turnpoint.store import Plan


def _plan(turnpoints: list[Turnpoint]) -> Plan:
    return Plan(
        id="test-plan-id",
        name="demo route",
        turnpoints=turnpoints,
        created_at="2026-09-26T00:00:00+00:00",
        updated_at="2026-09-26T00:01:00+00:00",
    )


def _turnpoints() -> list[Turnpoint]:
    return [
        Turnpoint("ALPHA", 38.0, -77.0, altitude_ft=5000.0),
        Turnpoint("BRAVO", 38.5, -76.6, altitude_ft=6000.0),
    ]


def _legs() -> list[Leg]:
    return [Leg("ALPHA", "BRAVO", 34.2, 47.5, None)]


def test_returns_pdf_bytes():
    pdf = build_route_card(_plan(_turnpoints()), _legs())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")


def test_deterministic_for_same_input():
    plan = _plan(_turnpoints())
    legs = _legs()
    assert build_route_card(plan, legs) == build_route_card(plan, legs)


def test_different_plan_names_produce_different_bytes():
    turnpoints = _turnpoints()
    legs = _legs()
    a = build_route_card(_plan(turnpoints), legs)
    other = Plan(
        id="test-plan-id",
        name="a different name",
        turnpoints=turnpoints,
        created_at="2026-09-26T00:00:00+00:00",
        updated_at="2026-09-26T00:01:00+00:00",
    )
    b = build_route_card(other, legs)
    assert a != b


def test_handles_turnpoint_without_altitude():
    turnpoints = [Turnpoint("ALPHA", 38.0, -77.0), Turnpoint("BRAVO", 38.5, -76.6)]
    pdf = build_route_card(_plan(turnpoints), _legs())
    assert pdf.startswith(b"%PDF")


def test_handles_leg_without_ete():
    pdf = build_route_card(_plan(_turnpoints()), _legs())
    assert pdf.startswith(b"%PDF")


def test_handles_leg_with_ete():
    legs = [Leg("ALPHA", "BRAVO", 34.2, 47.5, 8.2)]
    pdf = build_route_card(_plan(_turnpoints()), legs)
    assert pdf.startswith(b"%PDF")


def test_handles_empty_legs():
    turnpoints = [Turnpoint("ALPHA", 38.0, -77.0, altitude_ft=5000.0)]
    pdf = build_route_card(_plan(turnpoints), [])
    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize("num_legs", [1, 3, 10])
def test_scales_with_number_of_legs(num_legs):
    turnpoints = [
        Turnpoint(f"TP{i}", 38.0 + i * 0.1, -77.0 + i * 0.1, altitude_ft=5000.0)
        for i in range(num_legs + 1)
    ]
    legs = [Leg(f"TP{i}", f"TP{i + 1}", 10.0, 90.0, None) for i in range(num_legs)]
    pdf = build_route_card(_plan(turnpoints), legs)
    assert pdf.startswith(b"%PDF")
