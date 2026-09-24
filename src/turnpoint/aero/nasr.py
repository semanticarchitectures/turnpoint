"""FAA NASR (National Airspace System Resources) CSV parsing and queries.

See docs/specs/aero-data.md and decision 0011: ``nasr_cycle`` is always
caller-supplied, never read from the file or fetched live -- the same
discipline ``terrain.elevation_m``'s ``dted_source`` already follows.
"""

from __future__ import annotations

import csv
from pathlib import Path

from turnpoint.aero.models import Airport, Navaid
from turnpoint.core.fidelity import FidelityIssue, FidelityReport
from turnpoint.geodesy import range_bearing


def _extract_lat_lon(
    row: dict[str, str], item: str, skipped: list[FidelityIssue]
) -> tuple[float, float] | None:
    lat_raw, lon_raw = row.get("LAT_DECIMAL"), row.get("LONG_DECIMAL")
    if not lat_raw or not lon_raw:
        skipped.append(FidelityIssue(item, "missing LAT_DECIMAL/LONG_DECIMAL"))
        return None
    try:
        return float(lat_raw), float(lon_raw)
    except ValueError:
        skipped.append(FidelityIssue(item, f"non-numeric coordinates: {lat_raw!r}, {lon_raw!r}"))
        return None


def _extract_elevation(
    row: dict[str, str], item: str, skipped: list[FidelityIssue]
) -> float | None:
    raw = row.get("ELEV")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        skipped.append(FidelityIssue(item, f"non-numeric ELEV: {raw!r}"))
        return None


def parse_airports(path: str | Path, nasr_cycle: str) -> tuple[list[Airport], FidelityReport]:
    """Parse an APT_BASE.csv extract (docs/specs/aero-data.md)."""
    path = Path(path)
    airports: list[Airport] = []
    skipped: list[FidelityIssue] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            ident = (row.get("ARPT_ID") or "").strip()
            item = f"row[{i}]: {ident or '?'}"
            if not ident:
                skipped.append(FidelityIssue(item, "missing ARPT_ID"))
                continue
            coords = _extract_lat_lon(row, item, skipped)
            if coords is None:
                continue
            lat, lon = coords
            airports.append(
                Airport(
                    ident=ident,
                    icao_id=(row.get("ICAO_ID") or "").strip() or None,
                    name=(row.get("ARPT_NAME") or "").strip(),
                    lat=lat,
                    lon=lon,
                    elevation_ft=_extract_elevation(row, item, skipped),
                    site_type=(row.get("SITE_TYPE_CODE") or "").strip(),
                    facility_use=(row.get("FACILITY_USE_CODE") or "").strip(),
                    nasr_cycle=nasr_cycle,
                )
            )
    return airports, FidelityReport(
        source_path=str(path), format="nasr-apt", imported_count=len(airports), skipped=skipped
    )


def parse_navaids(path: str | Path, nasr_cycle: str) -> tuple[list[Navaid], FidelityReport]:
    """Parse a NAV_BASE.csv extract (docs/specs/aero-data.md)."""
    path = Path(path)
    navaids: list[Navaid] = []
    skipped: list[FidelityIssue] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            ident = (row.get("NAV_ID") or "").strip()
            item = f"row[{i}]: {ident or '?'}"
            if not ident:
                skipped.append(FidelityIssue(item, "missing NAV_ID"))
                continue
            coords = _extract_lat_lon(row, item, skipped)
            if coords is None:
                continue
            lat, lon = coords
            navaids.append(
                Navaid(
                    ident=ident,
                    name=(row.get("NAME") or "").strip(),
                    nav_type=(row.get("NAV_TYPE") or "").strip(),
                    lat=lat,
                    lon=lon,
                    elevation_ft=_extract_elevation(row, item, skipped),
                    nasr_cycle=nasr_cycle,
                )
            )
    return navaids, FidelityReport(
        source_path=str(path), format="nasr-nav", imported_count=len(navaids), skipped=skipped
    )


def list_airports_near(
    lat: float, lon: float, radius_nm: float, path: str | Path, nasr_cycle: str
) -> tuple[list[Airport], FidelityReport]:
    """Airports within radius_nm great-circle distance of (lat, lon)."""
    airports, report = parse_airports(path, nasr_cycle)
    nearby = [a for a in airports if range_bearing(lat, lon, a.lat, a.lon).distance_nm <= radius_nm]
    return nearby, report


def get_airport(ident: str, path: str | Path, nasr_cycle: str) -> Airport:
    airports, _ = parse_airports(path, nasr_cycle)
    for a in airports:
        if a.ident == ident or a.icao_id == ident:
            return a
    raise KeyError(f"no such airport: {ident}")


def get_navaid(ident: str, path: str | Path, nasr_cycle: str) -> Navaid:
    navaids, _ = parse_navaids(path, nasr_cycle)
    for n in navaids:
        if n.ident == ident:
            return n
    raise KeyError(f"no such navaid: {ident}")
