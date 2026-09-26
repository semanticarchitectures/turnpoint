# 0014. Plug-in API: an entry-point importer registry

- Status: accepted
- Date: 2026-09-26

## Context

`docs/PLAN.md` Phase 3 names a "plug-in API" as a deliverable. Decision
0002 already scoped what "compatible" means for this project:
"offering a REST and MCP API modeled on the concepts of the FalconView
SDK. No COM or plug-in binary parity." FalconView's SDK let third-party
code extend the application with new format handlers, without changing
FalconView itself. That's the concept worth keeping — a way for code
Turnpoint doesn't ship to add capability — not literal COM/DLL loading,
which decision 0002 already ruled out as out of scope.

The concrete surface that already exists and is already duplicated:
`_IMPORTERS`, a `dict[str, Importer]` mapping a format name to an
import function, defined identically in both
`src/turnpoint/mcp_server/server.py` and `src/turnpoint/api/routes.py`.
Adding a fifth importer today means editing both by hand and keeping
them in sync — exactly the kind of surface a plug-in registry should
own once, not twice.

Export is out of scope here: no exporter exists yet anywhere in
`turnpoint.formats` (only import, despite the package docstring's
"Import and export adapters" — stale wording, not a real gap to close
in this decision). Extending the registry to exporters, or to other
kinds of plug-in (overlay renderers, scoring rules), is deferred until
a concrete one is needed — same reasoning as every other "add it when
something needs it" call in this log (decisions 0010, 0013).

## Decision

One registry, `turnpoint.formats.registry`, replaces both `_IMPORTERS`
dicts:

- `register_importer(name, importer, *, replace=False)` — the four
  built-ins (`geojson`, `gpx`, `kml`, `fv-drawing`) register themselves
  this way at `turnpoint.formats` import time, same as before, just in
  one place. Registering an already-registered name without
  `replace=True` raises `ValueError` — a plug-in silently overwriting a
  built-in (or another plug-in) is a configuration error, not something
  to paper over (`AGENTS.md` section 4).
- `get_importer(name)` / `list_importers()` — what `import_overlay`
  (MCP) and `POST /overlays/import` (REST) call instead of indexing a
  local dict. `list_importers()` backs a new `list_import_formats`
  MCP tool and `GET /overlays/formats` REST route, so an agent can
  discover what's available without reading source (`AGENTS.md`'s
  agents-first framing, decision 0003).
- **Third-party discovery via Python entry points**, group
  `turnpoint.importers` (`docs/specs/plugin-api.md`). A pip-installed
  package declares
  `[project.entry-points."turnpoint.importers"]\nmyformat = "mypkg.importer:import_myformat"`
  and it becomes available through the same `import_overlay` surface
  Turnpoint's own importers use, with zero changes to Turnpoint code.
  Entry points are resolved lazily (on first `get_importer`/
  `list_importers` call, cached after) via `importlib.metadata` —
  stdlib on Python 3.11+, no new dependency (`AGENTS.md` rule 3).

An importer plug-in has the exact same contract as a built-in one:
`(path) -> (list[OverlayFeature], FidelityReport)`. No separate,
weaker-typed "plug-in" shape — a third-party importer is not a
second-class citizen.

## Consequences

`_IMPORTERS` is deleted from both `mcp_server/server.py` and
`api/routes.py`; both now call `turnpoint.formats.registry` instead.
Adding a built-in importer is a one-line `register_importer` call in
`turnpoint.formats.__init__`; adding a third-party one needs no
Turnpoint code change at all. `docs/specs/plugin-api.md` documents the
entry-point contract for anyone writing one.

## Alternatives considered

A bare registration function with no entry-point discovery (rejected:
that's an internal refactor, not a plug-in *API* — nothing outside
Turnpoint's own process could add a format without still being
imported and registered by Turnpoint's own startup code). A generic
plug-in system covering importers, exporters, scoring rules and overlay
renderers in one pass (rejected as premature: only importers have a
concrete, duplicated pain point today; the same `register_x`/`get_x`/
`list_x` shape extends cleanly to another kind of plug-in whenever one
is actually needed). `setuptools` plugin discovery via
`pkg_resources` (rejected: deprecated in favor of `importlib.metadata`,
which is already stdlib here).
