"""Tests for the import-format plug-in registry (docs/specs/plugin-api.md,
decision 0014)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from turnpoint.core.fidelity import FidelityReport
from turnpoint.formats import registry


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    """Each test gets its own registry, isolated from the real built-ins
    turnpoint.formats registers at import time."""
    monkeypatch.setattr(registry, "_registry", {})
    monkeypatch.setattr(registry, "_entry_points_loaded", False)


def _dummy_importer(path):
    return [], FidelityReport(source_path=str(path), format="dummy", imported_count=0)


def test_register_and_get():
    registry.register_importer("dummy", _dummy_importer)
    assert registry.get_importer("dummy") is _dummy_importer


def test_register_duplicate_raises():
    registry.register_importer("dummy", _dummy_importer)
    with pytest.raises(ValueError):
        registry.register_importer("dummy", _dummy_importer)


def test_register_duplicate_with_replace_overrides():
    registry.register_importer("dummy", _dummy_importer)

    def other(path):
        return [], FidelityReport(source_path=str(path), format="dummy2", imported_count=1)

    registry.register_importer("dummy", other, replace=True)
    assert registry.get_importer("dummy") is other


def test_get_missing_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get_importer("does-not-exist")


def test_list_importers_sorted():
    registry.register_importer("zeta", _dummy_importer)
    registry.register_importer("alpha", _dummy_importer)
    assert registry.list_importers() == ["alpha", "zeta"]


@dataclass
class _FakeEntryPoint:
    name: str
    fn: Any

    def load(self) -> Any:
        return self.fn


def test_entry_point_plugin_is_discovered(monkeypatch):
    monkeypatch.setattr(
        registry,
        "entry_points",
        lambda group: [_FakeEntryPoint("plugin-format", _dummy_importer)],
    )
    assert registry.get_importer("plugin-format") is _dummy_importer
    assert "plugin-format" in registry.list_importers()


def test_entry_points_loaded_once(monkeypatch):
    calls: list[str] = []

    def fake_entry_points(group):
        calls.append(group)
        return [_FakeEntryPoint("plugin-format", _dummy_importer)]

    monkeypatch.setattr(registry, "entry_points", fake_entry_points)
    registry.list_importers()
    registry.get_importer("plugin-format")
    assert calls == [registry.ENTRY_POINT_GROUP]


def test_entry_point_conflicting_with_built_in_raises(monkeypatch):
    registry.register_importer("geojson", _dummy_importer)
    monkeypatch.setattr(
        registry,
        "entry_points",
        lambda group: [_FakeEntryPoint("geojson", _dummy_importer)],
    )
    with pytest.raises(ValueError):
        registry.list_importers()
