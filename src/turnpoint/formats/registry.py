"""Import-format plug-in registry (docs/specs/plugin-api.md, decision 0014).

Third-party format importers register here -- via ``register_importer``
directly, or by declaring a ``turnpoint.importers`` entry point -- and
become available through the same ``import_overlay`` MCP tool /
``POST /overlays/import`` REST route as Turnpoint's own built-in
importers, with no code change to ``turnpoint.mcp_server`` or
``turnpoint.api``. One registry, not the two hand-duplicated
``_IMPORTERS`` dicts this replaces.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path

from turnpoint.core.fidelity import FidelityReport
from turnpoint.core.overlay import OverlayFeature

Importer = Callable[[str | Path], "tuple[list[OverlayFeature], FidelityReport]"]

ENTRY_POINT_GROUP = "turnpoint.importers"

_registry: dict[str, Importer] = {}
_entry_points_loaded = False


def register_importer(name: str, importer: Importer, *, replace: bool = False) -> None:
    """Register ``importer`` under ``name`` (docs/specs/plugin-api.md).

    Raises ``ValueError`` if ``name`` is already registered, unless
    ``replace=True`` -- a plug-in silently overwriting a built-in or
    another plug-in is a configuration error, not something to paper
    over (AGENTS.md section 4).
    """
    if not replace and name in _registry:
        raise ValueError(f"importer already registered: {name}")
    _registry[name] = importer


def _load_entry_points() -> None:
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        register_importer(ep.name, ep.load())
    _entry_points_loaded = True


def get_importer(name: str) -> Importer:
    """The importer registered under ``name``, built-in or plug-in alike.

    Raises ``KeyError`` if nothing is registered under ``name``.
    """
    _load_entry_points()
    try:
        return _registry[name]
    except KeyError:
        raise KeyError(f"unsupported format: {name}") from None


def list_importers() -> list[str]:
    """Every registered format name, built-in and plug-in alike, sorted."""
    _load_entry_points()
    return sorted(_registry)
