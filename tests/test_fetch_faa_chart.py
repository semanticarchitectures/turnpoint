"""Tests for scripts/fetch_faa_chart.py (docs/decisions/0015-chart-updates.md).

parse_chart_response is tested against a real captured FAA APRA response
(SOURCES.md S-015). fetch_chart_product and download_and_extract take an
injectable opener so these tests never touch the network -- consistent
with the rest of the suite (synthetic fixtures only, AGENTS.md section 6:
no network calls inside computations, and that includes test runs).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
import scripts.fetch_faa_chart as fetch_faa_chart
from scripts.fetch_faa_chart import (
    ApraError,
    ChartProduct,
    download_and_extract,
    fetch_chart_product,
    parse_chart_response,
)

FIXTURE = Path(__file__).parent / "fixtures" / "apra" / "sectional-chart-response.xml"


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def test_parse_chart_response_against_real_capture():
    product = parse_chart_response(FIXTURE.read_bytes())
    assert product == ChartProduct(
        edition_date="09/03/2026",
        edition_number="98",
        download_url="https://aeronav.faa.gov/visual/09-03-2026/sectional-files/Washington.zip",
    )


def test_parse_chart_response_rejects_non_200_status():
    # Synthetic -- the real API's error shape was not independently
    # confirmed (only a successful request was made, SOURCES.md S-015);
    # this only exercises parse_chart_response's own status check.
    xml = (
        b'<?xml version="1.0"?><productSet xmlns="http://arpa.ait.faa.gov/arpa_response">'
        b'<status code="400" message="Invalid geoname"/></productSet>'
    )
    with pytest.raises(ApraError, match="Invalid geoname"):
        parse_chart_response(xml)


def test_parse_chart_response_rejects_missing_edition():
    xml = (
        b'<?xml version="1.0"?><productSet xmlns="http://arpa.ait.faa.gov/arpa_response">'
        b'<status code="200" message="OK"/></productSet>'
    )
    with pytest.raises(ApraError, match="edition"):
        parse_chart_response(xml)


def test_fetch_chart_product_builds_query_and_parses_response():
    captured_urls = []

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        captured_urls.append(url)
        return _FakeResponse(FIXTURE.read_bytes())

    product = fetch_chart_product("Washington", "current", "tiff", opener=fake_opener)

    assert product.edition_number == "98"
    assert len(captured_urls) == 1
    assert "geoname=Washington" in captured_urls[0]
    assert "edition=current" in captured_urls[0]
    assert "format=tiff" in captured_urls[0]


def test_fetch_chart_product_url_encodes_geoname():
    captured_urls = []

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        captured_urls.append(url)
        return _FakeResponse(FIXTURE.read_bytes())

    fetch_chart_product("Dallas-Ft Worth", "current", "tiff", opener=fake_opener)
    assert "Dallas-Ft+Worth" in captured_urls[0] or "Dallas-Ft%20Worth" in captured_urls[0]


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_download_and_extract_writes_every_file(tmp_path: Path):
    zip_bytes = _make_zip(
        {"Washington.tif": b"fake-tiff-bytes", "Washington.tfw": b"fake-worldfile"}
    )

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(zip_bytes)

    product = ChartProduct(
        edition_date="09/03/2026", edition_number="98", download_url="https://example/x.zip"
    )
    written = download_and_extract(product, tmp_path / "out", opener=fake_opener)

    names = {p.name for p in written}
    assert names == {"Washington.tif", "Washington.tfw"}
    assert (tmp_path / "out" / "Washington.tif").read_bytes() == b"fake-tiff-bytes"
    assert (tmp_path / "out" / "Washington.tfw").read_bytes() == b"fake-worldfile"


def test_download_and_extract_ignores_directory_entries(tmp_path: Path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subdir/", b"")
        zf.writestr("subdir/Washington.tif", b"fake-tiff-bytes")

    def fake_opener(url: str, timeout: float) -> _FakeResponse:
        return _FakeResponse(buf.getvalue())

    product = ChartProduct(
        edition_date="09/03/2026", edition_number="98", download_url="https://example/x.zip"
    )
    written = download_and_extract(product, tmp_path / "out", opener=fake_opener)

    assert [p.name for p in written] == ["Washington.tif"]


def test_main_writes_into_edition_named_directory(tmp_path: Path, monkeypatch, capsys):
    product = ChartProduct(
        edition_date="09/03/2026", edition_number="98", download_url="https://example/x.zip"
    )
    monkeypatch.setattr(fetch_faa_chart, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(fetch_faa_chart, "fetch_chart_product", lambda *a, **k: product)
    monkeypatch.setattr(
        fetch_faa_chart,
        "download_and_extract",
        lambda p, dest_dir, **k: [dest_dir / "Washington.tif"],
    )
    monkeypatch.setattr("sys.argv", ["fetch_faa_chart.py", "--geoname", "Washington"])

    fetch_faa_chart.main()

    out = capsys.readouterr().out
    assert "edition 98" in out
    assert str(tmp_path / "Washington_98" / "Washington.tif") in out


def test_main_exits_nonzero_on_apra_error(monkeypatch, capsys):
    def raising_fetch(*a, **k):
        raise ApraError("boom")

    monkeypatch.setattr(fetch_faa_chart, "fetch_chart_product", raising_fetch)
    monkeypatch.setattr("sys.argv", ["fetch_faa_chart.py", "--geoname", "Nowhere"])

    with pytest.raises(SystemExit) as exc_info:
        fetch_faa_chart.main()
    assert exc_info.value.code == 1
    assert "boom" in capsys.readouterr().err
