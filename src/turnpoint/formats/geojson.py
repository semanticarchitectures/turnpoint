"""GeoJSON import/export (RFC 7946). Plain JSON -- no new dependency.

GeoJSON coordinates are ``(lon, lat[, altitude])`` (RFC 7946 section
3.1.1); swapped to ``(lat, lon)`` to match ``OverlayFeature`` and
``turnpoint.geodesy``'s convention. ``OverlayFeature`` is 2D
(docs/specs/plan-model.md), so a present altitude is flagged in the
``FidelityReport`` rather than silently dropped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.core.overlay import GeometryType, OverlayFeature

_GEOMETRY_MAP: dict[str, GeometryType] = {
    "Point": "point",
    "LineString": "line",
    "Polygon": "polygon",
}


def import_geojson(path: str | Path) -> tuple[list[OverlayFeature], FidelityReport]:
    """Parse a GeoJSON FeatureCollection, Feature or bare geometry."""
    path = Path(path)
    data = json.loads(path.read_text())
    raw_features = _extract_raw_features(data)

    features: list[OverlayFeature] = []
    skipped: list[FidelityIssue] = []
    for i, raw in enumerate(raw_features):
        item = f"features[{i}]"
        geometry = raw.get("geometry")
        if not geometry:
            skipped.append(FidelityIssue(item, "no geometry"))
            continue
        gtype = geometry.get("type")
        mapped = _GEOMETRY_MAP.get(gtype)
        if mapped is None:
            skipped.append(FidelityIssue(item, f"unsupported geometry type: {gtype}"))
            continue
        try:
            coords, had_altitude = _extract_coordinates(mapped, geometry["coordinates"])
            feature = OverlayFeature(mapped, coords, dict(raw.get("properties") or {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            skipped.append(FidelityIssue(item, f"malformed geometry: {exc}"))
            continue
        features.append(feature)
        if had_altitude:
            skipped.append(
                FidelityIssue(item, "altitude present in source but not preserved (2D overlay)")
            )
        if mapped == "polygon" and len(geometry["coordinates"]) > 1:
            skipped.append(FidelityIssue(item, "polygon holes present in source but not preserved"))

    return features, FidelityReport(
        source_path=str(path), format="geojson", imported_count=len(features), skipped=skipped
    )


def _extract_raw_features(data: dict[str, Any]) -> list[dict[str, Any]]:
    t = data.get("type")
    if t == "FeatureCollection":
        return data.get("features", [])
    if t == "Feature":
        return [data]
    if t in _GEOMETRY_MAP:
        return [{"type": "Feature", "geometry": data, "properties": {}}]
    raise ValueError(f"unrecognized top-level GeoJSON type: {t}")


def _extract_coordinates(
    geometry_type: GeometryType, raw_coords: Any
) -> tuple[list[tuple[float, float]], bool]:
    def point(c: list[float]) -> tuple[float, float]:
        return (float(c[1]), float(c[0]))

    had_altitude = False

    if geometry_type == "point":
        had_altitude = len(raw_coords) > 2
        return [point(raw_coords)], had_altitude

    if geometry_type == "line":
        had_altitude = any(len(c) > 2 for c in raw_coords)
        return [point(c) for c in raw_coords], had_altitude

    # polygon: first (exterior) ring only -- holes are out of v2 scope,
    # per docs/specs/plan-model.md's "no holes and no multi-ring polygons".
    ring = raw_coords[0]
    had_altitude = any(len(c) > 2 for c in ring)
    return [point(c) for c in ring], had_altitude
