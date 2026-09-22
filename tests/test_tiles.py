"""Tile service tests use a small synthetic GeoTIFF, generated in a temp
directory, never real chart or elevation data. CADRG is untested here —
see the open gap documented in turnpoint/tiles/cadrg.py."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from turnpoint.tiles.geotiff import GeoTIFFSource
from turnpoint.tiles.service import open_source

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _synthetic_geotiff(path: Path) -> Path:
    size = 64
    data = np.tile(np.linspace(0, 255, size, dtype="uint8"), (size, 1))
    transform = from_origin(0.0, 0.1, 0.1 / size, 0.1 / size)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=1,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    ) as ds:
        ds.write(data, 1)
    return path


@pytest.fixture
def geotiff(tmp_path: Path) -> Path:
    return _synthetic_geotiff(tmp_path / "basemap.tif")


def test_tile_renders_valid_png(geotiff: Path):
    png = GeoTIFFSource(geotiff).tile(0, 0, 0)
    assert png[:8] == PNG_MAGIC


def test_tile_out_of_extent_raises(geotiff: Path):
    with pytest.raises(ValueError):
        GeoTIFFSource(geotiff).tile(10, 0, 0)


def test_open_source_dispatches_geotiff_by_extension(geotiff: Path):
    assert isinstance(open_source(geotiff), GeoTIFFSource)


def test_open_source_rejects_unknown_extension(tmp_path: Path):
    with pytest.raises(ValueError):
        open_source(tmp_path / "chart.xyz")
