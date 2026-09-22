"""XYZ raster tile service over local GDAL-readable rasters (decision 0009).

Serves only local files already present under `data/` (git-ignored, public
data only per data/README.md); there is no outbound network fetch of
remote tiles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rio_tiler.io import Reader


class TileSource(Protocol):
    def tile(self, z: int, x: int, y: int) -> bytes: ...


def render_tile(path: str, z: int, x: int, y: int) -> bytes:
    """Render one XYZ tile as PNG bytes from any GDAL-readable raster.

    Shared by every ``TileSource`` backend (``turnpoint.tiles.geotiff``,
    ``turnpoint.tiles.cadrg``) — rio-tiler's reader is format-agnostic, so
    the rendering step is identical regardless of the underlying format.
    """
    with Reader(path) as reader:
        if not reader.tile_exists(x, y, z):
            raise ValueError(f"tile z={z} x={x} y={y} is outside {path}'s extent")
        return reader.tile(x, y, z).render(img_format="PNG")


def open_source(path: str | Path) -> TileSource:
    """Pick a ``TileSource`` backend by file extension."""
    from turnpoint.tiles.cadrg import CadrgSource
    from turnpoint.tiles.geotiff import GeoTIFFSource

    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        return GeoTIFFSource(p)
    if suffix == ".toc":
        return CadrgSource(p)
    raise ValueError(f"unrecognized tile source format: {p}")


def tile(source: TileSource, z: int, x: int, y: int) -> bytes:
    """Render one XYZ tile (PNG bytes) from an already-opened TileSource."""
    return source.tile(z, x, y)
