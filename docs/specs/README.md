# Format and model specs

Language-neutral specifications, one file per format or model. Each lists its
sources (by `SOURCES.md` ID), the mapping to the Turnpoint plan model, and open gaps.

- [`plan-model.md`](plan-model.md): the `Turnpoint`/`Route`/`Plan`/`Overlay`
  model, provenance events and fidelity reports.
- [`route-schema.md`](route-schema.md): JSON Schema for the wire/storage
  representation of the plan model.
- [`aero-data.md`](aero-data.md): `Airport`/`Navaid` model and FAA NASR
  CSV parsing.
- [`fv-drawing-import.md`](fv-drawing-import.md): FalconView drawing file
  import — a best-effort importer built from partial public
  documentation, with every undocumented piece flagged as an explicit,
  numbered assumption rather than invented silently (decision 0012).
- [`scenario-format.md`](scenario-format.md): scenario file format and
  score report shape for `turnpoint.scenario` (decision 0013).
- [`plugin-api.md`](plugin-api.md): the import-format plug-in registry
  and entry-point contract (decision 0014).

`fv-local-points-import.md` is not written and no importer exists for
that file: no public documentation of its structure was found at all
(see `fv-drawing-import.md`'s research), so there is nothing
non-invented to spec. Revisit if that changes.

`fv-route-import.md` is not written either, same reason: researched
2026-09-26 (`docs/PLAN.md`'s Phase 4, "Route file (.rte) import" open
item) and no public documentation of FalconView/PFPS's `.rte` route
file structure was found — checked the FME FalconView reader docs
(covers drawing and threat databases only, not routes), GPSBabel's
format list and mailing list (no PFPS/FalconView `.rte` support or
format notes), and generic file-extension reference sites (list other
programs' unrelated `.rte` formats, nothing FalconView-specific). One
forum thread linked a `PFPS400-ShapeFilePreferences-ICD.doc` — an ICD,
not opened, forbidden without written permission (`CLEAN_ROOM.md`), and
about shapefile import preferences, not routes, anyway. Revisit if
documentation surfaces; Turnpoint's own route schema
(`route-schema.md`) is unaffected and remains the primary format.
