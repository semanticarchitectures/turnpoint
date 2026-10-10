#!/usr/bin/env python3
"""Fetch real public data for a demo area: a FAA VFR sectional chart, a
USGS 3DEP terrain raster and a FAA NASR airport/navaid CSV extract
(docs/real-data-setup.md, docs/decisions/0016-real-demo-data-script.md).

A standalone operational tool, same shape and same reasoning as
scripts/fetch_faa_chart.py (decision 0015): not part of turnpoint's
importable package, never reachable from any MCP tool or REST route.
Run this by hand, whenever you want a real area's data staged for a
demo; Turnpoint's own server code never calls the network.

Usage:
    python scripts/fetch_real_demo_data.py --nasr-cycle 2026-09-03
    python scripts/fetch_real_demo_data.py \
        --geoname "San Francisco" --bbox -122.6,37.6,-122.3,37.9 \
        --nasr-cycle 2026-09-03

--geoname/--bbox default to the Washington, DC area (matching
scenarios/phase2-demo's existing non-synthetic coordinates).
--nasr-cycle has no default and is always required -- decision 0011:
never infer "whatever's current" NASR cycle, even from an operational
script outside Turnpoint's own determinism boundary. Browse
https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/
to find the current one.

Writes into data/real-demo/:
    chart/<geoname>_<edition>/...   -- from fetch_faa_chart
    dem.tif                          -- USGS 3DEP terrain (GeoTIFF)
    nasr/APT_BASE.csv, NAV_BASE.csv  -- FAA NASR per-table CSV extracts

Verification: all three steps call APIs/URLs confirmed live and
exercised end to end on 2026-09-28/2026-10-10 (SOURCES.md S-015/S-016/
S-018) -- including the NASR per-table zip URLs, found by fetching the
real subscription page with curl (not guessed) after the original
guessed URL in this script turned out to 404.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# `python scripts/fetch_real_demo_data.py` (not `python -m ...`) puts only
# scripts/ on sys.path, not the repo root -- add it so the cross-script
# import below resolves regardless of how this is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fetch_faa_chart import (  # noqa: E402
    ApraError,
    _default_opener,
    _Opener,
    download_and_extract,
    fetch_chart_product,
)

DEM_API_BASE = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
)
NASR_PAGE_BASE = "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription"
# The per-table CSV zips (SOURCES.md S-018) -- small (single-digit MB),
# unlike the ~250MB full 28-day subscription zip that page also links.
NASR_CSV_BASE = "https://nfdc.faa.gov/webContent/28DaySub/extra"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "real-demo"

DEFAULT_GEONAME = "Washington"
DEFAULT_BBOX = "-77.1,38.7,-77.0,38.8"
# filename -> FAA's short table code, used in the per-table zip's name
NASR_TABLES = {"APT_BASE.csv": "APT", "NAV_BASE.csv": "NAV"}


class DemError(RuntimeError):
    pass


class NasrFetchFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class DemExport:
    href: str
    width: int
    height: int


def parse_dem_export_response(json_bytes: bytes) -> DemExport:
    """Parse a 3DEP ``exportImage`` JSON response (SOURCES.md S-016)."""
    data = json.loads(json_bytes)
    href = data.get("href")
    if not href:
        raise DemError(f"3DEP export response has no href: {data}")
    return DemExport(href=href, width=data.get("width", 0), height=data.get("height", 0))


def fetch_dem(
    bbox: tuple[float, float, float, float],
    *,
    size: tuple[int, int] = (1024, 1024),
    opener: _Opener = _default_opener,
) -> DemExport:
    west, south, east, north = bbox
    query = urllib.parse.urlencode(
        {
            "bbox": f"{west},{south},{east},{north}",
            "bboxSR": 4326,
            "size": f"{size[0]},{size[1]}",
            "imageSR": 4326,
            "format": "tiff",
            "pixelType": "F32",
            "f": "json",
        }
    )
    url = f"{DEM_API_BASE}?{query}"
    with opener(url, timeout=60) as resp:
        return parse_dem_export_response(resp.read())


def download_dem(export: DemExport, dest_path: Path, *, opener: _Opener = _default_opener) -> Path:
    with opener(export.href, timeout=120) as resp:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.read())
    return dest_path


def nasr_table_zip_url(cycle: str, table: str) -> str:
    """URL for one NASR table's standalone CSV zip (SOURCES.md S-018).

    ``cycle`` is ``YYYY-MM-DD``; ``table`` is the FAA's short table code
    (e.g. ``"APT"``, ``"NAV"``). Raises ``NasrFetchFailed`` if ``cycle``
    isn't a valid date.
    """
    try:
        date = datetime.strptime(cycle, "%Y-%m-%d").strftime("%d_%b_%Y")
    except ValueError as exc:
        raise NasrFetchFailed(f"--nasr-cycle must be YYYY-MM-DD, got {cycle!r}") from exc
    return f"{NASR_CSV_BASE}/{date}_{table}_CSV.zip"


def _fetch_one_nasr_table(
    cycle: str, filename: str, table: str, dest_dir: Path, *, opener: _Opener
) -> Path:
    url = nasr_table_zip_url(cycle, table)
    try:
        with opener(url, timeout=60) as resp:
            zip_bytes = resp.read()
    except OSError as exc:
        raise NasrFetchFailed(f"could not fetch {url}: {exc}") from exc

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            matches = [n for n in zf.namelist() if Path(n).name == filename]
            if not matches:
                raise NasrFetchFailed(f"{url} did not contain {filename}")
            dest_dir.mkdir(parents=True, exist_ok=True)
            out_path = dest_dir / filename
            out_path.write_bytes(zf.read(matches[0]))
    except zipfile.BadZipFile as exc:
        raise NasrFetchFailed(f"{url} did not return a valid zip: {exc}") from exc
    return out_path


def fetch_nasr_csvs(cycle: str, dest_dir: Path, *, opener: _Opener = _default_opener) -> list[Path]:
    """Download APT_BASE.csv and NAV_BASE.csv for ``cycle``, one small
    per-table zip each (confirmed live, SOURCES.md S-018) rather than the
    FAA's ~250MB full 28-day subscription zip.

    Raises ``NasrFetchFailed`` on any network problem, malformed zip, or
    a zip that doesn't contain the file it was fetched for -- never a
    silent partial result.
    """
    return [
        _fetch_one_nasr_table(cycle, filename, table, dest_dir, opener=opener)
        for filename, table in NASR_TABLES.items()
    ]


def _fetch_chart(geoname: str, edition: str) -> None:
    print(f"=== Chart: {geoname} ({edition}) ===")
    try:
        product = fetch_chart_product(geoname, edition, "tiff")
    except ApraError as exc:
        print(f"  FAILED: {exc}", file=sys.stderr)
        return
    print(f"  edition {product.edition_number}, dated {product.edition_date}")
    safe_name = geoname.replace(" ", "_").replace("-", "_")
    chart_dir = OUTPUT_DIR / "chart" / f"{safe_name}_{product.edition_number}"
    for path in download_and_extract(product, chart_dir):
        print(f"  wrote {path}")


def _fetch_dem(bbox_arg: str) -> None:
    print(f"\n=== Terrain: bbox {bbox_arg} ===")
    try:
        west, south, east, north = (float(v) for v in bbox_arg.split(","))
    except ValueError:
        print(f"  FAILED: --bbox must be west,south,east,north (got {bbox_arg!r})", file=sys.stderr)
        return
    try:
        export = fetch_dem((west, south, east, north))
        dem_path = download_dem(export, OUTPUT_DIR / "dem.tif")
    except (DemError, OSError) as exc:
        print(f"  FAILED: {exc}", file=sys.stderr)
        return
    print(f"  wrote {dem_path} ({export.width}x{export.height})")


def _fetch_nasr(cycle: str) -> None:
    print(f"\n=== Airports/navaids: NASR cycle {cycle} ===")
    nasr_dir = OUTPUT_DIR / "nasr"
    try:
        for path in fetch_nasr_csvs(cycle, nasr_dir):
            print(f"  wrote {path}")
    except NasrFetchFailed as exc:
        print(f"  Automated fetch failed: {exc}")
        print(
            f"  Browse {NASR_PAGE_BASE}/{cycle}/ to confirm that cycle date is "
            f"real, then download APT_BASE.csv/NAV_BASE.csv yourself into {nasr_dir}/"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--geoname", default=DEFAULT_GEONAME, help="FAA sectional chart region")
    parser.add_argument(
        "--bbox", default=DEFAULT_BBOX, help="west,south,east,north in decimal degrees"
    )
    parser.add_argument("--edition", default="current", choices=["current", "next"])
    parser.add_argument(
        "--nasr-cycle",
        required=True,
        help=f"NASR cycle date, e.g. 2026-09-03 -- browse {NASR_PAGE_BASE}/",
    )
    args = parser.parse_args()

    _fetch_chart(args.geoname, args.edition)
    _fetch_dem(args.bbox)
    _fetch_nasr(args.nasr_cycle)

    print("\nSee docs/real-data-setup.md for how to point Turnpoint at all of this.")


if __name__ == "__main__":
    main()
