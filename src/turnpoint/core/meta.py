"""Shared response metadata (docs/specs/route-schema.md, "Meta block").

Every API and MCP response carries this so agent plans can be replayed and
audited (AGENTS.md, section 6: "every MCP tool response names the data sets
and versions it used").
"""

from __future__ import annotations

from typing import Any

from turnpoint import NOT_FOR_OPERATIONAL_USE, __version__
from turnpoint.geodesy import DATUM

GEODESIC_MODEL = "GeographicLib (Karney 2013)"


def meta(**extra: Any) -> dict[str, Any]:
    """The base meta block, extended with response-specific provenance.

    ``extra`` lets a caller add fields beyond the base set — for example the
    DTED source and version a terrain-clearance check used — without every
    module re-deriving the base fields itself.
    """
    return {
        "turnpoint_version": __version__,
        "datum": DATUM,
        "geodesic_model": GEODESIC_MODEL,
        "bearings": "degrees true",
        "notice": NOT_FOR_OPERATIONAL_USE,
        **extra,
    }
