"""Tests use the synthetic DEM fixture from conftest.py (a flat plain
with a square hill), never real DTED files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from turnpoint.core.route import Route, Turnpoint
from turnpoint.scenario import (
    Scenario,
    ScenarioObjective,
    ScenarioPoint,
    ScenarioThreat,
    load_scenario,
    score_route,
)
from turnpoint.scenario.scorer import (
    CLEARANCE_VIOLATION_PENALTY_PER_LEG,
    LATE_ARRIVAL_PENALTY_PER_MIN,
    MAX_SCORE,
    OVER_MAX_ETE_PENALTY,
    THREAT_EXPOSURE_PENALTY_PER_THREAT,
)

START = ScenarioPoint("A", 0.5, 0.05, altitude_ft=15000.0)
END = ScenarioPoint("B", 0.5, 0.95, altitude_ft=15000.0)


def _scenario(dem: Path, **objective_overrides) -> Scenario:
    objective = ScenarioObjective(
        start=START, end=END, clearance_margin_ft=500.0, **objective_overrides
    )
    return Scenario(name="test scenario", dted_source=str(dem), objective=objective)


def _crossing_route(altitude_ft: float) -> Route:
    return Route(
        "test",
        [
            Turnpoint(START.name, START.lat, START.lon, altitude_ft=altitude_ft),
            Turnpoint(END.name, END.lat, END.lon, altitude_ft=altitude_ft),
        ],
    )


# --- load_scenario -----------------------------------------------------


def _write_scenario(tmp_path: Path, dem: Path, **overrides) -> Path:
    data = {
        "name": "test scenario",
        "dted_source": str(dem),
        "objective": {
            "start": {
                "name": START.name,
                "lat": START.lat,
                "lon": START.lon,
                "altitude_ft": START.altitude_ft,
            },
            "end": {
                "name": END.name,
                "lat": END.lat,
                "lon": END.lon,
                "altitude_ft": END.altitude_ft,
            },
            "clearance_margin_ft": 500.0,
        },
    }
    data.update(overrides)
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data))
    return path


def test_load_scenario_applies_defaults(tmp_path: Path, dem: Path):
    scenario = load_scenario(_write_scenario(tmp_path, dem))
    assert scenario.name == "test scenario"
    assert scenario.description == ""
    assert scenario.threats == []
    assert scenario.objective.groundspeed_kt is None


def test_load_scenario_parses_threats(tmp_path: Path, dem: Path):
    threats = [
        {
            "name": "SAM-1",
            "threat_type": "NOTIONAL-SAM-A",
            "lat": 0.5,
            "lon": 0.5,
            "engagement_radius_nm": 20.0,
        }
    ]
    scenario = load_scenario(_write_scenario(tmp_path, dem, threats=threats))
    assert len(scenario.threats) == 1
    assert scenario.threats[0].sensor_height_ft == 0.0
    assert scenario.threats[0].sidc is None


def test_load_scenario_missing_required_field_raises(tmp_path: Path, dem: Path):
    path = _write_scenario(tmp_path, dem)
    data = json.loads(path.read_text())
    del data["objective"]["clearance_margin_ft"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_scenario(path)


def test_load_scenario_rejects_bad_sample_interval(tmp_path: Path, dem: Path):
    with pytest.raises(ValueError):
        load_scenario(_write_scenario(tmp_path, dem, sample_interval_nm=0))


# --- score_route ---------------------------------------------------------


def test_clean_route_scores_max(dem: Path):
    report = score_route(_crossing_route(15000.0), _scenario(dem))
    assert report.reached_objective is True
    assert report.clear is True
    assert report.clearance_violation_legs == 0
    assert report.exposure == []
    assert report.airspace_checked is False
    assert report.score == MAX_SCORE


def test_clearance_violation_deducts_penalty(dem: Path):
    report = score_route(_crossing_route(1000.0), _scenario(dem))
    assert report.clear is False
    assert report.clearance_violation_legs == 1
    assert report.score == pytest.approx(MAX_SCORE - CLEARANCE_VIOLATION_PENALTY_PER_LEG)


def test_threat_exposure_deducts_penalty(dem: Path):
    threat = ScenarioThreat("SAM-1", "NOTIONAL-SAM-A", 0.5, 0.05, engagement_radius_nm=100.0)
    scenario = Scenario(
        name="threatened",
        dted_source=str(dem),
        objective=ScenarioObjective(start=START, end=END, clearance_margin_ft=500.0),
        threats=[threat],
    )
    report = score_route(_crossing_route(15000.0), scenario)
    assert len(report.exposure) == 1
    assert report.exposure[0].threat_name == "SAM-1"
    assert report.exposure[0].exposed is True
    assert report.score == pytest.approx(MAX_SCORE - THREAT_EXPOSURE_PENALTY_PER_THREAT)


def test_route_not_reaching_objective_scores_zero(dem: Path):
    off_course = Route(
        "off",
        [
            Turnpoint("X", 0.1, 0.1, altitude_ft=15000.0),
            Turnpoint("Y", 0.9, 0.9, altitude_ft=15000.0),
        ],
    )
    report = score_route(off_course, _scenario(dem))
    assert report.reached_objective is False
    assert report.score == 0.0
    # Diagnostics are still computed even though the score is zeroed.
    assert report.clear is True


def test_late_arrival_deducts_penalty(dem: Path):
    scenario = _scenario(dem, groundspeed_kt=300.0, target_ete_min=0.1)
    report = score_route(_crossing_route(15000.0), scenario)
    assert report.within_target_time is False
    assert report.ete_min is not None
    expected = MAX_SCORE - LATE_ARRIVAL_PENALTY_PER_MIN * (report.ete_min - 0.1)
    assert report.score == pytest.approx(expected)


def test_over_max_ete_deducts_flat_penalty(dem: Path):
    scenario = _scenario(dem, groundspeed_kt=300.0, max_ete_min=0.1)
    report = score_route(_crossing_route(15000.0), scenario)
    assert report.within_max_time is False
    assert report.score == pytest.approx(MAX_SCORE - OVER_MAX_ETE_PENALTY)


def test_score_never_goes_below_zero(dem: Path):
    # Five exposed threats (-15 each) plus a clearance violation (-25) plus
    # a blown max ETE (-30) sum to -130 against a 100-point ceiling.
    threats = [
        ScenarioThreat(f"SAM-{i}", "NOTIONAL-SAM-A", 0.5, 0.05, engagement_radius_nm=100.0)
        for i in range(5)
    ]
    scenario = Scenario(
        name="disaster",
        dted_source=str(dem),
        objective=ScenarioObjective(
            start=START, end=END, clearance_margin_ft=500.0, groundspeed_kt=300.0, max_ete_min=0.01
        ),
        threats=threats,
    )
    report = score_route(_crossing_route(1000.0), scenario)
    assert all(e.exposed for e in report.exposure)
    assert report.score == 0.0
