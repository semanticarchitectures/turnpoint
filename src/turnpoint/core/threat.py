"""Notional threat model (docs/PLAN.md Phase 3).

No real threat system parameters, ever (AGENTS.md section 2): every
field is a caller-supplied, notional value -- e.g. threat_type
"NOTIONAL-SAM-A", a 20 nm engagement_radius_nm, never a real system's
actual range or performance figures.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Threat:
    id: str
    name: str
    threat_type: str
    lat: float
    lon: float
    engagement_radius_nm: float
    sensor_height_ft: float
    sidc: str | None
    actor: str
    created_at: str
