"""Scenario file loading (docs/specs/scenario-format.md, decision 0013).

Plain JSON, parsed and validated by hand -- no schema-validation
dependency, same convention as ``turnpoint.formats.geojson``. Loading is
pure: one file read, no data-set lookups, no defaults invented beyond
what the format spec names explicitly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from turnpoint.terrain import DEFAULT_SAMPLE_INTERVAL_NM


@dataclass(frozen=True)
class ScenarioPoint:
    name: str
    lat: float
    lon: float
    altitude_ft: float


@dataclass(frozen=True)
class ScenarioThreat:
    name: str
    threat_type: str
    lat: float
    lon: float
    engagement_radius_nm: float
    sensor_height_ft: float = 0.0
    sidc: str | None = None


@dataclass(frozen=True)
class ScenarioObjective:
    start: ScenarioPoint
    end: ScenarioPoint
    clearance_margin_ft: float
    groundspeed_kt: float | None = None
    target_ete_min: float | None = None
    max_ete_min: float | None = None


@dataclass(frozen=True)
class Scenario:
    name: str
    dted_source: str
    objective: ScenarioObjective
    description: str = ""
    sample_interval_nm: float = DEFAULT_SAMPLE_INTERVAL_NM
    threats: list[ScenarioThreat] = field(default_factory=list)


def _require(data: dict[str, Any], key: str, what: str) -> Any:
    if key not in data:
        raise ValueError(f"{what} missing required field: {key}")
    return data[key]


def _point(data: dict[str, Any], what: str) -> ScenarioPoint:
    return ScenarioPoint(
        name=str(_require(data, "name", what)),
        lat=float(_require(data, "lat", what)),
        lon=float(_require(data, "lon", what)),
        altitude_ft=float(_require(data, "altitude_ft", what)),
    )


def _threat(data: dict[str, Any], index: int) -> ScenarioThreat:
    what = f"threats[{index}]"
    return ScenarioThreat(
        name=str(_require(data, "name", what)),
        threat_type=str(_require(data, "threat_type", what)),
        lat=float(_require(data, "lat", what)),
        lon=float(_require(data, "lon", what)),
        engagement_radius_nm=float(_require(data, "engagement_radius_nm", what)),
        sensor_height_ft=float(data.get("sensor_height_ft", 0.0)),
        sidc=data.get("sidc"),
    )


def _objective(data: dict[str, Any]) -> ScenarioObjective:
    what = "objective"
    return ScenarioObjective(
        start=_point(_require(data, "start", what), f"{what}.start"),
        end=_point(_require(data, "end", what), f"{what}.end"),
        clearance_margin_ft=float(_require(data, "clearance_margin_ft", what)),
        groundspeed_kt=(
            None if data.get("groundspeed_kt") is None else float(data["groundspeed_kt"])
        ),
        target_ete_min=(
            None if data.get("target_ete_min") is None else float(data["target_ete_min"])
        ),
        max_ete_min=(None if data.get("max_ete_min") is None else float(data["max_ete_min"])),
    )


def load_scenario(path: str | Path) -> Scenario:
    """Parse and validate a scenario JSON file (docs/specs/scenario-format.md)."""
    data = json.loads(Path(path).read_text())
    sample_interval_nm = float(data.get("sample_interval_nm", DEFAULT_SAMPLE_INTERVAL_NM))
    if sample_interval_nm <= 0:
        raise ValueError("sample_interval_nm must be positive")
    threats = [_threat(t, i) for i, t in enumerate(data.get("threats", []))]
    return Scenario(
        name=str(_require(data, "name", "scenario")),
        dted_source=str(_require(data, "dted_source", "scenario")),
        objective=_objective(_require(data, "objective", "scenario")),
        description=str(data.get("description", "")),
        sample_interval_nm=sample_interval_nm,
        threats=threats,
    )
