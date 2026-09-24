"""KML import (OGC KML 2.3, a public standard listed among
CLEAN_ROOM.md's allowed sources; see SOURCES.md S-008) via Python's stdlib
``xml.etree.ElementTree``. Not ``fastkml``: LGPL, forbidden (AGENTS.md;
see docs/THIRD_PARTY.md).

Only ``Placemark``/``Point``/``LineString``/``Polygon``/``MultiGeometry``
(first part only) are supported -- the subset Turnpoint needs. KML
coordinates are ``lon,lat[,alt]`` tuples (OGC KML spec); swapped to
``(lat, lon)`` to match ``OverlayFeature``. A present altitude or
polygon holes (``innerBoundaryIs``) are flagged in the
``FidelityReport`` rather than silently dropped, same pattern as
``formats/geojson.py``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.core.overlay import GeometryType, OverlayFeature

_GEOMETRY_TAGS: dict[str, GeometryType] = {
    "Point": "point",
    "LineString": "line",
    "Polygon": "polygon",
}


def import_kml(path: str | Path) -> tuple[list[OverlayFeature], FidelityReport]:
    path = Path(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"malformed KML: {exc}") from exc

    placemarks = [e for e in root.iter() if _local(e.tag) == "Placemark"]
    features: list[OverlayFeature] = []
    skipped: list[FidelityIssue] = []

    for i, placemark in enumerate(placemarks):
        name_el = _child(placemark, "name")
        label = name_el.text if name_el is not None and name_el.text else None
        item = f"Placemark[{i}]" + (f" ({label})" if label else "")
        properties = {"name": label} if label else {}

        geometries = _placemark_geometries(placemark)
        if not geometries:
            skipped.append(FidelityIssue(item, "no supported geometry (Point/LineString/Polygon)"))
            continue
        if len(geometries) > 1:
            skipped.append(
                FidelityIssue(
                    item, f"MultiGeometry has {len(geometries)} parts; only the first is imported"
                )
            )
        gtype, geom_el = geometries[0]
        try:
            coords, had_altitude, had_holes = _extract_geometry(gtype, geom_el)
            feature = OverlayFeature(gtype, coords, properties)
        except ValueError as exc:
            skipped.append(FidelityIssue(item, f"malformed geometry: {exc}"))
            continue
        features.append(feature)
        if had_altitude:
            skipped.append(
                FidelityIssue(item, "altitude present in source but not preserved (2D overlay)")
            )
        if had_holes:
            skipped.append(FidelityIssue(item, "polygon holes present in source but not preserved"))

    return features, FidelityReport(
        source_path=str(path), format="kml", imported_count=len(features), skipped=skipped
    )


def _local(tag: str) -> str:
    """Strip the XML namespace: '{http://...}Placemark' -> 'Placemark'."""
    return tag.rsplit("}", 1)[-1]


def _child(elem: ET.Element, name: str) -> ET.Element | None:
    """A direct child with this local tag name, or None."""
    for c in elem:
        if _local(c.tag) == name:
            return c
    return None


def _placemark_geometries(placemark: ET.Element) -> list[tuple[GeometryType, ET.Element]]:
    """Direct geometry children of a Placemark, expanding MultiGeometry
    one level (its direct children only -- nested MultiGeometry is not
    supported, would show up as "no supported geometry" on that part)."""
    results: list[tuple[GeometryType, ET.Element]] = []
    for child in placemark:
        local = _local(child.tag)
        if local in _GEOMETRY_TAGS:
            results.append((_GEOMETRY_TAGS[local], child))
        elif local == "MultiGeometry":
            for sub in child:
                sub_local = _local(sub.tag)
                if sub_local in _GEOMETRY_TAGS:
                    results.append((_GEOMETRY_TAGS[sub_local], sub))
    return results


def _extract_geometry(
    gtype: GeometryType, elem: ET.Element
) -> tuple[list[tuple[float, float]], bool, bool]:
    """Returns (coordinates, had_altitude, had_holes)."""
    had_holes = False
    if gtype == "polygon":
        outer = _child(elem, "outerBoundaryIs")
        ring = _child(outer, "LinearRing") if outer is not None else None
        coords_el = _child(ring, "coordinates") if ring is not None else None
        had_holes = _child(elem, "innerBoundaryIs") is not None
    else:
        coords_el = _child(elem, "coordinates")
    if coords_el is None or not coords_el.text:
        raise ValueError("no <coordinates> found")
    coords, had_altitude = _parse_coordinates(coords_el.text)
    return coords, had_altitude, had_holes


def _parse_coordinates(text: str) -> tuple[list[tuple[float, float]], bool]:
    """KML coordinates: whitespace-separated 'lon,lat[,alt]' tuples."""
    points: list[tuple[float, float]] = []
    had_altitude = False
    for tup in text.split():
        parts = tup.split(",")
        lon, lat = float(parts[0]), float(parts[1])
        if len(parts) > 2:
            had_altitude = True
        points.append((lat, lon))
    return points, had_altitude
