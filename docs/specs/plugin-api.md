# Plug-in API: import-format registry

How to add an import format to Turnpoint without changing Turnpoint's
own code (decision 0014). This is the one plug-in surface that exists
today — extending the same pattern to exporters, scoring rules or
overlay renderers is deferred until a concrete need appears.

## The contract

An importer is any callable with this signature:

```python
def import_myformat(path: str | Path) -> tuple[list[OverlayFeature], FidelityReport]: ...
```

`OverlayFeature` and `FidelityReport` are `turnpoint.core.overlay`/
`turnpoint.core.fidelity` — the same shapes every built-in importer
(`turnpoint.formats.geojson.import_geojson` and friends) already
returns. A plug-in importer follows the same rules a built-in one does:
never silently drop data (`AGENTS.md` section 4) — anything it can't
represent goes in the `FidelityReport`'s `skipped` list, named and
explained, not dropped.

## Registering in-process

```python
from turnpoint.formats.registry import register_importer

register_importer("myformat", import_myformat)
```

Raises `ValueError` if `"myformat"` is already registered (a built-in
or another plug-in) — pass `replace=True` to override deliberately.

## Registering as an installable plug-in

Declare an entry point in the plug-in package's `pyproject.toml`, group
`turnpoint.importers`:

```toml
[project.entry-points."turnpoint.importers"]
myformat = "my_package.importer:import_myformat"
```

Once the package is installed in the same environment as Turnpoint (`pip
install my-turnpoint-plugin`), `"myformat"` is available through
`import_overlay` (MCP) and `POST /overlays/import` (REST) exactly like
`geojson`, `gpx`, `kml` or `fv-drawing` — no Turnpoint code change, no
restart-order dependency beyond both packages being importable.
Discovery happens lazily, on first use, via `importlib.metadata`
(stdlib) and is cached for the process's lifetime.

## Discovering what's registered

```
list_import_formats()          # MCP tool
GET /overlays/formats           # REST route
```

Both return every registered format name — built-in and plug-in alike,
there's no way to tell them apart from the response, by design (decision
0014: a plug-in importer is not a second-class citizen).

## Open gaps

- Export, overlay rendering and scoring-rule plug-ins don't exist —
  only import formats are extensible today (decision 0014).
- No sandboxing: a plug-in importer runs with Turnpoint's own
  permissions, in-process, same as a built-in one. Only install
  plug-ins you trust, same as any Python dependency.
