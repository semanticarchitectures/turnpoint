"""GPX import (GPS Exchange Format) via gpxpy (Apache-2.0, see
docs/THIRD_PARTY.md; ``fastkml`` was considered and rejected for KML on
license grounds -- see ``formats/kml.py``).

Waypoints map to point features; routes and track segments map to line
features. GPX elevation is present but ``OverlayFeature`` is 2D
(docs/specs/plan-model.md), so a present elevation is flagged in the
``FidelityReport`` rather than silently dropped.
"""

from __future__ import annotations

from pathlib import Path

import gpxpy
import gpxpy.gpx

from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.core.overlay import OverlayFeature

_ELEVATION_DROPPED = "elevation present in source but not preserved (2D overlay)"


def import_gpx(path: str | Path) -> tuple[list[OverlayFeature], FidelityReport]:
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
    except gpxpy.gpx.GPXException as exc:
        raise ValueError(f"malformed GPX: {exc}") from exc

    features: list[OverlayFeature] = []
    skipped: list[FidelityIssue] = []

    for i, wpt in enumerate(gpx.waypoints):
        item = f"waypoints[{i}]"
        properties = {"name": wpt.name} if wpt.name else {}
        features.append(OverlayFeature("point", [(wpt.latitude, wpt.longitude)], properties))
        if wpt.elevation is not None:
            skipped.append(FidelityIssue(item, _ELEVATION_DROPPED))

    for i, route in enumerate(gpx.routes):
        item = f"routes[{i}]"
        if len(route.points) < 2:
            skipped.append(
                FidelityIssue(item, f"route has fewer than 2 points ({len(route.points)})")
            )
            continue
        coords = [(p.latitude, p.longitude) for p in route.points]
        properties = {"name": route.name} if route.name else {}
        features.append(OverlayFeature("line", coords, properties))
        if any(p.elevation is not None for p in route.points):
            skipped.append(FidelityIssue(item, _ELEVATION_DROPPED))

    for i, track in enumerate(gpx.tracks):
        for j, segment in enumerate(track.segments):
            item = f"tracks[{i}].segments[{j}]"
            if len(segment.points) < 2:
                skipped.append(
                    FidelityIssue(item, f"segment has fewer than 2 points ({len(segment.points)})")
                )
                continue
            coords = [(p.latitude, p.longitude) for p in segment.points]
            properties = {"name": track.name} if track.name else {}
            features.append(OverlayFeature("line", coords, properties))
            if any(p.elevation is not None for p in segment.points):
                skipped.append(FidelityIssue(item, _ELEVATION_DROPPED))

    return features, FidelityReport(
        source_path=str(path), format="gpx", imported_count=len(features), skipped=skipped
    )
