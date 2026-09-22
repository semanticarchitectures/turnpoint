"""GeoTIFF/Cloud-Optimized GeoTIFF tile rendering (decision 0009)."""

from __future__ import annotations

from pathlib import Path

from turnpoint.tiles.service import render_tile


class GeoTIFFSource:
    """A single GeoTIFF or Cloud-Optimized GeoTIFF raster."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    def tile(self, z: int, x: int, y: int) -> bytes:
        return render_tile(self.path, z, x, y)
