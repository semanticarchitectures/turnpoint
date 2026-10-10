"""Tests for scripts/fetch_real_demo_data.py
(docs/decisions/0016-real-demo-data-script.md).

parse_dem_export_response is tested against a real captured USGS 3DEP
response (SOURCES.md S-016). Every network call takes an injectable
opener so these tests never touch the network, same convention as
test_fetch_faa_chart.py.

test_direct_invocation_does_not_crash_on_import is a real subprocess
run, deliberately not using an injected import path -- decision 0016's
own postmortem: the unit tests below all passed while the script's own
documented `python scripts/fetch_real_demo_data.py` invocation raised
ModuleNotFoundError, because nothing exercised the actual command line.
"""

from __future__ import annotations

import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import scripts.fetch_real_demo_data as fetch_real_demo_data
from scripts.fetch_real_demo_data import (
    DemError,
    DemExport,
    NasrFetchFailed,
    download_dem,
    fetch_dem,
    fetch_nasr_csvs,
    nasr_table_zip_url,
    parse_dem_export_response,
)

FIXTURE = Path(__file__).parent / "fixtures" / "dem_export" / "export-image-response.json"


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# --- DEM -------------------------------------------------------------


def test_parse_dem_export_response_against_real_capture():
    export = parse_dem_export_response(FIXTURE.read_bytes())
    assert export == DemExport(
        href=(
            "https://elevation.nationalmap.gov/arcgis/rest/directories/elevation_output/"
            "3DEPElevation_ImageServer/_ags_3e0bbf1e_60c8_42cc_b790_cd5677cd4010.tif"
        ),
        width=512,
        height=512,
    )


def test_parse_dem_export_response_rejects_missing_href():
    with pytest.raises(DemError, match="href"):
        parse_dem_export_response(b'{"width": 512, "height": 512}')


def test_fetch_dem_builds_query_and_parses_response():
    captured_urls = []

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        captured_urls.append(url)
        return _FakeResponse(FIXTURE.read_bytes())

    export = fetch_dem((-77.1, 38.7, -77.0, 38.8), opener=fake_opener)

    assert export.width == 512
    assert len(captured_urls) == 1
    assert "bbox=-77.1%2C38.7%2C-77.0%2C38.8" in captured_urls[0]
    assert "f=json" in captured_urls[0]


def test_download_dem_writes_bytes(tmp_path: Path):
    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(b"fake-tiff-bytes")

    export = DemExport(href="https://example/dem.tif", width=512, height=512)
    dest = download_dem(export, tmp_path / "out" / "dem.tif", opener=fake_opener)

    assert dest.read_bytes() == b"fake-tiff-bytes"


# --- NASR --------------------------------------------------------------
#
# Confirmed live 2026-10-10 (SOURCES.md S-018) by fetching the real NASR
# subscription page with curl and finding its actual per-table zip links
# -- the original guessed URL (a different host entirely) 404'd.


def test_nasr_table_zip_url_pattern():
    assert nasr_table_zip_url("2026-09-03", "APT") == (
        "https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip"
    )
    assert nasr_table_zip_url("2026-09-03", "NAV") == (
        "https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_NAV_CSV.zip"
    )


def test_nasr_table_zip_url_rejects_bad_cycle_format():
    with pytest.raises(NasrFetchFailed, match="YYYY-MM-DD"):
        nasr_table_zip_url("09/03/2026", "APT")


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_fetch_nasr_csvs_fetches_one_zip_per_table(tmp_path: Path):
    apt_zip = _make_zip({"APT DATA LAYOUT.pdf": b"pdf", "APT_BASE.csv": b"apt-data"})
    nav_zip = _make_zip({"NAV_BASE.csv": b"nav-data", "NAV_RMK.csv": b"rmk-data"})
    zips_by_url = {
        nasr_table_zip_url("2026-09-03", "APT"): apt_zip,
        nasr_table_zip_url("2026-09-03", "NAV"): nav_zip,
    }

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(zips_by_url[url])

    written = fetch_nasr_csvs("2026-09-03", tmp_path / "nasr", opener=fake_opener)

    names = {p.name for p in written}
    assert names == {"APT_BASE.csv", "NAV_BASE.csv"}
    assert (tmp_path / "nasr" / "APT_BASE.csv").read_bytes() == b"apt-data"
    assert (tmp_path / "nasr" / "NAV_BASE.csv").read_bytes() == b"nav-data"


def test_fetch_nasr_csvs_raises_on_network_failure():
    def raising_opener(url: str, timeout: float):
        raise OSError("connection refused")

    with pytest.raises(NasrFetchFailed, match="could not fetch"):
        fetch_nasr_csvs("2026-09-03", Path("/tmp/unused"), opener=raising_opener)


def test_fetch_nasr_csvs_raises_on_bad_zip():
    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(b"not a zip file")

    with pytest.raises(NasrFetchFailed, match="valid zip"):
        fetch_nasr_csvs("2026-09-03", Path("/tmp/unused"), opener=fake_opener)


def test_fetch_nasr_csvs_raises_when_file_missing_from_zip():
    zip_bytes = _make_zip({"readme.txt": b"nothing useful here"})

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(zip_bytes)

    with pytest.raises(NasrFetchFailed, match="did not contain"):
        fetch_nasr_csvs("2026-09-03", Path("/tmp/unused"), opener=fake_opener)


# --- main orchestration --------------------------------------------------


def test_main_reports_all_three_sections(tmp_path: Path, monkeypatch, capsys):
    from scripts.fetch_faa_chart import ChartProduct

    monkeypatch.setattr(fetch_real_demo_data, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        fetch_real_demo_data,
        "fetch_chart_product",
        lambda *a, **k: ChartProduct(
            edition_date="09/03/2026", edition_number="98", download_url="https://example/x.zip"
        ),
    )
    monkeypatch.setattr(
        fetch_real_demo_data,
        "download_and_extract",
        lambda p, dest_dir, **k: [dest_dir / "Washington.tif"],
    )
    monkeypatch.setattr(
        fetch_real_demo_data,
        "fetch_dem",
        lambda *a, **k: DemExport(href="https://example/dem.tif", width=512, height=512),
    )
    monkeypatch.setattr(fetch_real_demo_data, "download_dem", lambda export, dest, **k: dest)
    monkeypatch.setattr(
        fetch_real_demo_data,
        "fetch_nasr_csvs",
        lambda cycle, dest_dir, **k: [dest_dir / "APT_BASE.csv", dest_dir / "NAV_BASE.csv"],
    )
    monkeypatch.setattr("sys.argv", ["fetch_real_demo_data.py", "--nasr-cycle", "2026-09-03"])

    fetch_real_demo_data.main()

    out = capsys.readouterr().out
    assert "Chart:" in out
    assert "edition 98" in out
    assert "Terrain:" in out
    assert "512x512" in out
    assert "Airports/navaids:" in out
    assert "APT_BASE.csv" in out


# --- real subprocess invocation (the class of bug the unit tests above miss) ---


def test_direct_invocation_does_not_crash_on_import(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "fetch_real_demo_data.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,  # not the repo root -- the bug didn't care, the fix shouldn't either
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    assert "usage:" in result.stdout


def test_main_nasr_failure_prints_manual_fallback(tmp_path: Path, monkeypatch, capsys):
    from scripts.fetch_faa_chart import ChartProduct

    monkeypatch.setattr(fetch_real_demo_data, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        fetch_real_demo_data,
        "fetch_chart_product",
        lambda *a, **k: ChartProduct(
            edition_date="09/03/2026", edition_number="98", download_url="https://example/x.zip"
        ),
    )
    monkeypatch.setattr(fetch_real_demo_data, "download_and_extract", lambda p, dest_dir, **k: [])
    monkeypatch.setattr(
        fetch_real_demo_data,
        "fetch_dem",
        lambda *a, **k: DemExport(href="https://example/dem.tif", width=512, height=512),
    )
    monkeypatch.setattr(fetch_real_demo_data, "download_dem", lambda export, dest, **k: dest)

    def raising_nasr(cycle, dest_dir, **k):
        raise NasrFetchFailed("boom")

    monkeypatch.setattr(fetch_real_demo_data, "fetch_nasr_csvs", raising_nasr)
    monkeypatch.setattr("sys.argv", ["fetch_real_demo_data.py", "--nasr-cycle", "2026-09-03"])

    fetch_real_demo_data.main()

    out = capsys.readouterr().out
    assert "Automated fetch failed: boom" in out
    assert "download APT_BASE.csv/NAV_BASE.csv yourself" in out
