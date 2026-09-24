"""FalconView drawing file import -- BEST EFFORT.

Built from partial public documentation only (SOURCES.md S-004, S-012,
S-013); everything marked ASSUMED below is this project's own invention,
not sourced, flagged for review the moment real documentation or written
GTRI permission becomes available. See docs/specs/fv-drawing-import.md
for the full DOCUMENTED-vs-ASSUMED breakdown and decision 0012 for why
this approach was chosen over leaving the milestone unwritten.

A "FalconView Drawing File Format Interface Control Document" was found
in public search results and was deliberately not opened or used --
FalconView SDK/ICD material, forbidden by AGENTS.md section 1 without
written permission, which is not on file (SOURCES.md S-013).

Uses access-parser (Apache-2.0, pure Python, no mdbtools dependency --
docs/THIRD_PARTY.md) to read the .mdb/.accdb ``Main`` table.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.core.overlay import GeometryType, OverlayFeature

# ASSUMED (spec item 1): literal Main table column names are not
# documented -- try these candidates, case-insensitively.
_FEATURE_NUM_CANDIDATES = ("FEATURE_NUM", "FEATURE_NUMBER")
_TYPE_CANDIDATES = ("TYPE", "FEATURE_TYPE")
_DATA_CANDIDATES = ("DATA",)

# ASSUMED (spec item 2): the `type` field holds the type name itself,
# uppercase, not a numeric or other code.
_GEOMETRY_TYPES: dict[str, GeometryType] = {
    "LINE": "line",
    "OVAL": "point",
    "TEXT": "point",
    "BULLSEYE": "point",
    "RECTANGLE": "point",
    "AXIS": "point",
}

# spec item 4: these types lose real 2D extent because no attribute name
# is documented for their radii/height-width/ring-count/width-ratio.
_SHAPE_NOT_RECONSTRUCTED = {"OVAL", "RECTANGLE", "BULLSEYE", "AXIS"}

_COORD_RE = re.compile(r"^([NS])(\d+(?:\.\d+)?)([EW])(\d+(?:\.\d+)?)$")


def _find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    upper_map = {c.upper(): c for c in columns}
    for cand in candidates:
        if cand in upper_map:
            return upper_map[cand]
    return None


def _parse_coord(text: str) -> tuple[float, float] | None:
    """Parse 'N50.123456W85.123456' (DOCUMENTED format, SOURCES.md S-013)
    into (lat, lon)."""
    m = _COORD_RE.match(text.strip())
    if not m:
        return None
    ns, lat_raw, ew, lon_raw = m.groups()
    lat = float(lat_raw) * (1 if ns == "N" else -1)
    lon = float(lon_raw) * (1 if ew == "E" else -1)
    return lat, lon


def _parse_data_field(data: str) -> dict[str, str]:
    """ASSUMED (spec item 3): semicolon-delimited KEY=VALUE pairs, using
    the DOCUMENTED DATA_TYPE_* attribute names as keys."""
    attrs: dict[str, str] = {}
    for part in data.split(";"):
        if "=" in part:
            key, _, value = part.partition("=")
            attrs[key.strip()] = value.strip()
    return attrs


def _extract_coords(
    raw_type: str, attrs: dict[str, str], item: str, skipped: list[FidelityIssue]
) -> list[tuple[float, float]] | None:
    if raw_type == "LINE":
        start, end = attrs.get("DATA_TYPE_MOVETO"), attrs.get("DATA_TYPE_LINETO")
        if not start or not end:
            skipped.append(FidelityIssue(item, "line missing DATA_TYPE_MOVETO/DATA_TYPE_LINETO"))
            return None
        p1, p2 = _parse_coord(start), _parse_coord(end)
        if p1 is None or p2 is None:
            skipped.append(FidelityIssue(item, f"unparseable coordinates: {start!r}, {end!r}"))
            return None
        return [p1, p2]

    center = attrs.get("DATA_TYPE_CENTER")
    if not center:
        skipped.append(FidelityIssue(item, f"{raw_type} missing DATA_TYPE_CENTER"))
        return None
    p = _parse_coord(center)
    if p is None:
        skipped.append(FidelityIssue(item, f"unparseable coordinates: {center!r}"))
        return None
    return [p]


def _parse_main_rows(
    table: dict[str, list[Any]],
) -> tuple[list[OverlayFeature], list[FidelityIssue]]:
    """Pure logic over a Main-table-shaped dict (column -> list of row
    values, matching access_parser.AccessParser.parse_table()'s return
    shape) -- fully unit-testable without a real .mdb file, since no
    permissively-licensed Python library can write one. See
    docs/specs/fv-drawing-import.md "Testing strategy"."""
    columns = list(table.keys())
    feature_num_col = _find_column(columns, _FEATURE_NUM_CANDIDATES)
    type_col = _find_column(columns, _TYPE_CANDIDATES)
    data_col = _find_column(columns, _DATA_CANDIDATES)

    if type_col is None or data_col is None:
        return [], [
            FidelityIssue(
                "Main table",
                f"expected TYPE/DATA-like columns (assumed names), found {columns!r} -- "
                "see docs/specs/fv-drawing-import.md assumption 1",
            )
        ]

    features: list[OverlayFeature] = []
    skipped: list[FidelityIssue] = []
    row_count = len(table[type_col])
    for i in range(row_count):
        feature_num = table[feature_num_col][i] if feature_num_col else i
        item = f"row[{i}] (feature {feature_num})"
        raw_type = str(table[type_col][i] or "").strip().upper()
        raw_data = str(table[data_col][i] or "")

        gtype = _GEOMETRY_TYPES.get(raw_type)
        if gtype is None:
            skipped.append(
                FidelityIssue(item, f"unrecognized/unassumed feature type: {raw_type!r}")
            )
            continue

        attrs = _parse_data_field(raw_data)
        coords = _extract_coords(raw_type, attrs, item, skipped)
        if coords is None:
            continue

        properties = {k: v for k, v in attrs.items() if k != "DATA_TYPE_CENTER"}
        properties["fv_feature_type"] = raw_type
        try:
            features.append(OverlayFeature(gtype, coords, properties))
        except ValueError as exc:
            skipped.append(FidelityIssue(item, f"malformed geometry: {exc}"))
            continue

        if raw_type in _SHAPE_NOT_RECONSTRUCTED:
            skipped.append(
                FidelityIssue(
                    item,
                    f"{raw_type} imported as a point at its center only -- shape/size not "
                    "reconstructed, see docs/specs/fv-drawing-import.md assumption 4",
                )
            )

    return features, skipped


def import_fv_drawing(path: str | Path) -> tuple[list[OverlayFeature], FidelityReport]:
    """Open a FalconView drawing file (.mdb/.accdb) and import its Main
    table. Untested against a real file -- see
    docs/specs/fv-drawing-import.md "Testing strategy"."""
    from access_parser import AccessParser

    path = Path(path)
    db = AccessParser(str(path))

    if "Main" not in db.catalog:
        reason = f"no 'Main' table found; tables: {list(db.catalog)!r}"
        return [], FidelityReport(
            source_path=str(path),
            format="fv-drawing",
            imported_count=0,
            skipped=[FidelityIssue("database", reason)],
        )

    table = db.parse_table("Main")
    features, skipped = _parse_main_rows(table)
    return features, FidelityReport(
        source_path=str(path), format="fv-drawing", imported_count=len(features), skipped=skipped
    )
