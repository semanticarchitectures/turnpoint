"""Scenario scoring (docs/specs/scenario-format.md, decision 0013).

Four axes named in docs/PLAN.md Phase 3: terrain clearance, airspace,
timing and threat exposure. Airspace is not scored -- Turnpoint has no
class-airspace overlay yet (docs/specs/aero-data.md "Open gaps");
``airspace_checked`` is always ``False``, named rather than silently
omitted (AGENTS.md section 4).

Scoring is a fixed-penalty rubric, not a weighted or learned score --
see decision 0013 for why each constant has the value it does. These are
Turnpoint's own rubric, not a claim about real-world severity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from turnpoint.core.route import Route
from turnpoint.core.threat import Threat
from turnpoint.geodesy import range_bearing
from turnpoint.scenario.scenario import Scenario
from turnpoint.terrain import route_exposure, terrain_clear

MAX_SCORE = 100.0
OBJECTIVE_TOLERANCE_NM = 1.0
CLEARANCE_VIOLATION_PENALTY_PER_LEG = 25.0
THREAT_EXPOSURE_PENALTY_PER_THREAT = 15.0
LATE_ARRIVAL_PENALTY_PER_MIN = 1.0
OVER_MAX_ETE_PENALTY = 30.0


@dataclass(frozen=True)
class ThreatExposureScore:
    threat_name: str
    exposed: bool


@dataclass(frozen=True)
class ScoreReport:
    scenario_name: str
    score: float
    max_score: float
    reached_objective: bool
    clear: bool
    clearance_violation_legs: int
    exposure: list[ThreatExposureScore]
    ete_min: float | None
    within_target_time: bool | None
    within_max_time: bool | None
    airspace_checked: bool = field(default=False)


def _reaches(route: Route, point_lat: float, point_lon: float, *, at_start: bool) -> bool:
    if not route.turnpoints:
        return False
    tp = route.turnpoints[0] if at_start else route.turnpoints[-1]
    return range_bearing(tp.lat, tp.lon, point_lat, point_lon).distance_nm <= OBJECTIVE_TOLERANCE_NM


def score_route(route: Route, scenario: Scenario) -> ScoreReport:
    """Score ``route`` against ``scenario`` (docs/specs/scenario-format.md).

    Every turnpoint in ``route`` must carry ``altitude_ft`` -- the same
    requirement as ``terrain_clear``/``route_exposure``, which this
    delegates to for two of the four scored axes.
    """
    objective = scenario.objective
    reached_objective = _reaches(
        route, objective.start.lat, objective.start.lon, at_start=True
    ) and _reaches(route, objective.end.lat, objective.end.lon, at_start=False)

    clearance = terrain_clear(
        route,
        clearance_margin_ft=objective.clearance_margin_ft,
        dted_source=scenario.dted_source,
        sample_interval_nm=scenario.sample_interval_nm,
    )
    clearance_violation_legs = sum(1 for leg in clearance.legs if not leg.clear)

    exposure: list[ThreatExposureScore] = []
    for t in scenario.threats:
        threat = Threat(
            id=t.name,
            name=t.name,
            threat_type=t.threat_type,
            lat=t.lat,
            lon=t.lon,
            engagement_radius_nm=t.engagement_radius_nm,
            sensor_height_ft=t.sensor_height_ft,
            sidc=t.sidc,
            actor="scenario",
            created_at="",
        )
        report = route_exposure(route, threat, scenario.dted_source, scenario.sample_interval_nm)
        exposure.append(ThreatExposureScore(t.name, report.exposed))

    ete_min: float | None = None
    within_target_time: bool | None = None
    within_max_time: bool | None = None
    if objective.groundspeed_kt is not None:
        ete_min = sum(leg.ete_min or 0.0 for leg in route.legs(objective.groundspeed_kt))
        if objective.target_ete_min is not None:
            within_target_time = ete_min <= objective.target_ete_min
        if objective.max_ete_min is not None:
            within_max_time = ete_min <= objective.max_ete_min

    score = MAX_SCORE
    score -= CLEARANCE_VIOLATION_PENALTY_PER_LEG * clearance_violation_legs
    score -= THREAT_EXPOSURE_PENALTY_PER_THREAT * sum(1 for e in exposure if e.exposed)
    if within_target_time is False and ete_min is not None and objective.target_ete_min is not None:
        score -= LATE_ARRIVAL_PENALTY_PER_MIN * (ete_min - objective.target_ete_min)
    if within_max_time is False:
        score -= OVER_MAX_ETE_PENALTY
    score = max(0.0, score) if reached_objective else 0.0

    return ScoreReport(
        scenario_name=scenario.name,
        score=score,
        max_score=MAX_SCORE,
        reached_objective=reached_objective,
        clear=clearance.clear,
        clearance_violation_legs=clearance_violation_legs,
        exposure=exposure,
        ete_min=ete_min,
        within_target_time=within_target_time,
        within_max_time=within_max_time,
    )
