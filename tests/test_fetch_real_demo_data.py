"""Tests for scripts/fetch_real_demo_data.py
(docs/decisions/0016-real-demo-data-script.md).

parse_dem_export_response is tested against a real captured USGS 3DEP
response (SOURCES.md S-016). Every network call takes an injectable
opener so these tests never touch the network, same convention as
test_fetch_faa_chart.py.
"""

from __future__ import annotations

import io
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
    nasr_zip_url,
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


def test_nasr_zip_url_pattern():
    assert nasr_zip_url("2026-09-03") == (
        "https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/"
        "NASR_Subscription/2026-09-03/28DaySubscription_Effective_2026-09-03.zip"
    )


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_fetch_nasr_csvs_extracts_only_the_two_files(tmp_path: Path):
    zip_bytes = _make_zip(
        {
            "CSV_Data/APT_BASE.csv": b"apt-data",
            "CSV_Data/NAV_BASE.csv": b"nav-data",
            "CSV_Data/FRQ_BASE.csv": b"frq-data",
            "readme.txt": b"readme",
        }
    )

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(zip_bytes)

    written = fetch_nasr_csvs("2026-09-03", tmp_path / "nasr", opener=fake_opener)

    names = {p.name for p in written}
    assert names == {"APT_BASE.csv", "NAV_BASE.csv"}
    assert (tmp_path / "nasr" / "APT_BASE.csv").read_bytes() == b"apt-data"


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


def test_fetch_nasr_csvs_raises_when_files_missing():
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
    assert "Download it yourself" in out
