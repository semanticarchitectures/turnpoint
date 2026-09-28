#!/usr/bin/env python3
"""Fetch a current FAA VFR sectional chart via the public APRA API
(docs/decisions/0015-chart-updates.md, SOURCES.md S-014/S-015).

A standalone operational tool, not part of turnpoint's importable
package or any MCP/REST/planning code path -- consistent with decision
0011 (NASR data: caller-supplied file and cycle, never fetched live
inside a planning computation). Run this by hand, whenever you want
fresh chart data; Turnpoint's own server code never calls the network.

Usage:
    python scripts/fetch_faa_chart.py --geoname Washington
    python scripts/fetch_faa_chart.py --geoname "Dallas-Ft Worth" --edition next

Writes data/charts/<geoname>_<edition_number>/ (git-ignored;
data/README.md's public-data-only rule already lists "FAA raster
charts" as an allowed source) with everything from the FAA's zip
extracted as-is -- the GeoTIFF and whatever else it ships with, never
cherry-picked, so nothing needed for georeferencing is silently
dropped (AGENTS.md section 4). Prints the edition date and number so
the operator can name the cycle the same way check_terrain_clearance's
dted_source or list_airports_near's nasr_cycle are already named in
every MCP/API response.

Network verification: the /vfr/sectional/info and /chart endpoints were
confirmed live on 2026-09-26 (SOURCES.md S-015), and the full
download-and-unzip path was exercised for real on 2026-09-28 -- a real
Washington sectional (a ~60MB GeoTIFF plus its .tfw and .htm) came back,
and rasterio opened it with its real Lambert Conformal Conic CRS.
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

API_BASE = "https://external-api.faa.gov/apra"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "charts"
_NS = {"a": "http://arpa.ait.faa.gov/arpa_response"}


class _Opener(Protocol):
    def __call__(self, url: str, timeout: float) -> io.BufferedIOBase: ...


@dataclass(frozen=True)
class ChartProduct:
    edition_date: str
    edition_number: str
    download_url: str


class ApraError(RuntimeError):
    pass


def parse_chart_response(xml_bytes: bytes) -> ChartProduct:
    """Parse an APRA ``/vfr/sectional/chart`` XML response
    (SOURCES.md S-015 for the confirmed response shape)."""
    root = ET.fromstring(xml_bytes)
    status = root.find("a:status", _NS)
    if status is None or status.get("code") != "200":
        message = status.get("message") if status is not None else "malformed response"
        raise ApraError(f"APRA request failed: {message}")

    edition_el = root.find("a:edition", _NS)
    if edition_el is None:
        raise ApraError("APRA response has no <edition> element")
    edition_date = edition_el.findtext("a:editionDate", namespaces=_NS)
    edition_number = edition_el.findtext("a:editionNumber", namespaces=_NS)
    product = edition_el.find("a:product", _NS)
    if edition_date is None or edition_number is None or product is None:
        raise ApraError("APRA response is missing edition date, number or product")
    download_url = product.get("url")
    if not download_url:
        raise ApraError("APRA response's product has no download url")

    return ChartProduct(
        edition_date=edition_date, edition_number=edition_number, download_url=download_url
    )


def _default_opener(url: str, timeout: float) -> io.BufferedIOBase:
    return urllib.request.urlopen(url, timeout=timeout)


def fetch_chart_product(
    geoname: str, edition: str, chart_format: str, *, opener: _Opener = _default_opener
) -> ChartProduct:
    query = urllib.parse.urlencode({"geoname": geoname, "edition": edition, "format": chart_format})
    url = f"{API_BASE}/vfr/sectional/chart?{query}"
    with opener(url, timeout=30) as resp:
        return parse_chart_response(resp.read())


def download_and_extract(
    product: ChartProduct, dest_dir: Path, *, opener: _Opener = _default_opener
) -> list[Path]:
    """Download the chart's zip and extract every file in it as-is into
    ``dest_dir`` -- never cherry-picked, so nothing the georeferencing
    depends on (a .tfw, an .aux.xml) is silently dropped."""
    with opener(product.download_url, timeout=120) as resp:
        zip_bytes = resp.read()
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            out_path = dest_dir / Path(name).name
            out_path.write_bytes(zf.read(name))
            written.append(out_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--geoname", required=True, help="FAA sectional chart region, e.g. Washington"
    )
    parser.add_argument("--edition", default="current", choices=["current", "next"])
    args = parser.parse_args()

    try:
        product = fetch_chart_product(args.geoname, args.edition, "tiff")
    except ApraError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"{args.geoname}: edition {product.edition_number}, dated {product.edition_date}")
    safe_name = args.geoname.replace(" ", "_").replace("-", "_")
    dest_dir = OUTPUT_DIR / f"{safe_name}_{product.edition_number}"
    written = download_and_extract(product, dest_dir)
    for path in written:
        print(f"Wrote {path}")
    print(
        f"Cycle: edition {product.edition_number}, dated {product.edition_date} -- "
        "name this alongside the file path wherever it's used as a dted_source or tiles source."
    )


if __name__ == "__main__":
    main()
