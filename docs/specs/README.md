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

`fv-local-points-import.md` is not written and no importer exists for
that file: no public documentation of its structure was found at all
(see `fv-drawing-import.md`'s research), so there is nothing
non-invented to spec. Revisit if that changes.

Planned: `scenario-format.md`.
