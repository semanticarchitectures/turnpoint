"""Airport and navaid models from FAA NASR data (docs/specs/aero-data.md)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    ident: str
    icao_id: str | None
    name: str
    lat: float
    lon: float
    elevation_ft: float | None
    site_type: str
    facility_use: str
    nasr_cycle: str


@dataclass(frozen=True)
class Navaid:
    ident: str
    name: str
    nav_type: str
    lat: float
    lon: float
    elevation_ft: float | None
    nasr_cycle: str
