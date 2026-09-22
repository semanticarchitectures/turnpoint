"""CADRG tile rendering via GDAL's RPFTOC driver.

CADRG (MIL-STD-2411, a public standard listed among CLEAN_ROOM.md's
allowed sources) is read entirely by GDAL's existing, independently
maintained RPFTOC/NITF driver — Turnpoint writes no CADRG decoding of its
own, so this is a permissively licensed third-party library reading a
public standard, not format code subject to clean-room sourcing.

Open gap: untested against a real CADRG frame collection. No public,
freely redistributable CADRG sample is on hand yet (data/README.md:
tests may only use public, unclassified, freely redistributable data).
Flagging this per AGENTS.md "flag gaps, don't invent" rather than
fabricating a synthetic CADRG/A.TOC fixture, which risks not matching
the on-disk structure GDAL's RPFTOC driver actually expects.
"""

from __future__ import annotations

from pathlib import Path

from turnpoint.tiles.service import render_tile


class CadrgSource:
    """A CADRG frame collection, opened via its A.TOC index file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    def tile(self, z: int, x: int, y: int) -> bytes:
        return render_tile(self.path, z, x, y)
