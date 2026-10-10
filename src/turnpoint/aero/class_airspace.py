"""FAA Class Airspace shapefile parsing and queries
(docs/specs/aero-data.md "Airspace", SOURCES.md S-019/S-020).

Same determinism discipline as ``nasr.py``: ``nasr_cycle`` is always
caller-supplied, named in every result, never read from the file or
inferred (decision 0011) -- the shapefile comes from the same dated
28-day subscription folder as the NASR CSVs, so the same cycle date
applies.

Faithful passthrough, same as ``nasr.py``'s ``site_type``/``facility_use``:
``upper_code``/``lower_code`` (MSL/STD/SFC/UNLTD) are kept as the FAA's
raw codes, never resolved to a single absolute-MSL altitude here --
``SFC`` is ground-relative (needs a terrain lookup to become absolute
MSL) and ``STD`` is pressure-referenced (needs an altimeter setting
Turnpoint doesn't model). See "Open gaps" in the spec.
"""

from __future__ import annotations

from pathlib import Path

import shapefile

from turnpoint.aero.models import Airspace
from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.geodesy import range_bearing

# The FAA's own not-applicable sentinel for UPPER_VAL/LOWER_VAL (e.g.
# -9998) is only meaningful alongside its UOM/CODE; when both are blank,
# there's no altitude value to parse, sentinel or not -- SOURCES.md S-020.
_NO_VALUE_UOM_CODE = ("", "")


def _parse_altitude(
    raw: str, uom: str, code: str, label: str, item: str, skipped: list[FidelityIssue]
) -> float | None:
    """``raw`` is a DBF text field (S-019: ``UPPER_VAL``/``LOWER_VAL`` are
    type C, not numeric), despite holding what's usually a number."""
    uom = (uom or "").strip()
    code = (code or "").strip()
    if (uom, code) == _NO_VALUE_UOM_CODE:
        return None
    raw = (raw or "").strip()
    try:
        return float(raw)
    except ValueError:
        skipped.append(FidelityIssue(item, f"non-numeric {label}: {raw!r}"))
        return None


def parse_class_airspace(
    path: str | Path, nasr_cycle: str
) -> tuple[list[Airspace], FidelityReport]:
    """Parse a Class Airspace shapefile (SOURCES.md S-020). ``path`` is the
    ``.shp`` file; pyshp finds the sibling ``.dbf``/``.shx`` by the same
    basename.
    """
    path = Path(path)
    airspaces: list[Airspace] = []
    skipped: list[FidelityIssue] = []
    with shapefile.Reader(str(path)) as sf:
        field_names = [f[0] for f in sf.fields[1:]]  # fields[0] is the DBF deletion flag
        for i in range(len(sf)):
            rec = dict(zip(field_names, sf.record(i), strict=False))
            ident = (rec.get("IDENT") or "").strip()
            name = (rec.get("NAME") or "").strip()
            item = f"record[{i}]: {name or ident or '?'}"
            shape = sf.shape(i)

            if not shape.points:
                skipped.append(FidelityIssue(item, "no boundary geometry"))
                continue
            if len(shape.parts) > 1:
                skipped.append(
                    FidelityIssue(
                        item,
                        f"{len(shape.parts)} polygon parts (holes/multiple rings) in "
                        "source, only the exterior ring is preserved",
                    )
                )
            # shape.parts holds each ring's start index into shape.points;
            # the exterior ring is always the first (shapefile convention).
            exterior_end = shape.parts[1] if len(shape.parts) > 1 else len(shape.points)
            exterior = shape.points[:exterior_end]
            boundary = [(lat, lon) for lon, lat in exterior]

            airspaces.append(
                Airspace(
                    ident=ident,
                    name=name,
                    airspace_class=(rec.get("CLASS") or "").strip(),
                    type_code=(rec.get("TYPE_CODE") or "").strip(),
                    local_type=(rec.get("LOCAL_TYPE") or "").strip(),
                    boundary=boundary,
                    upper_val=_parse_altitude(
                        rec.get("UPPER_VAL"),
                        rec.get("UPPER_UOM"),
                        rec.get("UPPER_CODE"),
                        "UPPER_VAL",
                        item,
                        skipped,
                    ),
                    upper_uom=(rec.get("UPPER_UOM") or "").strip(),
                    upper_code=(rec.get("UPPER_CODE") or "").strip(),
                    upper_desc=(rec.get("UPPER_DESC") or "").strip(),
                    lower_val=_parse_altitude(
                        rec.get("LOWER_VAL"),
                        rec.get("LOWER_UOM"),
                        rec.get("LOWER_CODE"),
                        "LOWER_VAL",
                        item,
                        skipped,
                    ),
                    lower_uom=(rec.get("LOWER_UOM") or "").strip(),
                    lower_code=(rec.get("LOWER_CODE") or "").strip(),
                    lower_desc=(rec.get("LOWER_DESC") or "").strip(),
                    exclusion=str(rec.get("EXCLUSION") or "0").strip() == "1",
                    nasr_cycle=nasr_cycle,
                )
            )

    return airspaces, FidelityReport(
        source_path=str(path),
        format="class-airspace-shapefile",
        imported_count=len(airspaces),
        skipped=skipped,
    )


def _boundary_centroid(boundary: list[tuple[float, float]]) -> tuple[float, float]:
    """Arithmetic mean of the ring's vertices -- a placement for the
    distance filter below, not a true geometric centroid (same caveat as
    the viewer's polygon label placement, decision carried from M27)."""
    n = len(boundary)
    return sum(lat for lat, _ in boundary) / n, sum(lon for _, lon in boundary) / n


def list_class_airspace_near(
    lat: float, lon: float, radius_nm: float, path: str | Path, nasr_cycle: str
) -> tuple[list[Airspace], FidelityReport]:
    """Class airspace whose boundary centroid is within ``radius_nm``
    great-circle distance of ``(lat, lon)`` -- a coarse filter (centroid
    distance, not true polygon-to-point distance), same precision
    tradeoff as the viewer's polygon label placement. Good enough to
    narrow a large nationwide file to a local area; not a substitute for
    real point-in-polygon containment.
    """
    airspaces, report = parse_class_airspace(path, nasr_cycle)
    nearby = [
        a
        for a in airspaces
        if range_bearing(lat, lon, *_boundary_centroid(a.boundary)).distance_nm <= radius_nm
    ]
    return nearby, report
